#!/usr/bin/env python3
"""Infraestrutura MQTT das portas, com confirmação pela junta real do Gazebo."""
import json
import math
import time
from queue import SimpleQueue
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory

import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

BROKER = "localhost"
PORT = 1883
NAO_NEGAR = True


def load_services(path):
    data = yaml.safe_load(Path(path).read_text()) or {}
    services = data.get("services", {})
    if not isinstance(services, dict):
        raise ValueError("services deve ser um dicionário de identificadores")
    required = ("x", "y", "width", "thickness", "open_angle", "closed_angle")
    for name, service in services.items():
        for field in required:
            service[field] = float(service[field])
            if not math.isfinite(service[field]):
                raise ValueError(f"Valor não finito em {name}.{field}")
        service["yaw"] = float(service.get("yaw", 0.0))
        if service["width"] <= 0 or service["thickness"] <= 0:
            raise ValueError(f"Dimensões inválidas em {name}")
        for field in ("joint_name", "command_topic", "feedback_topic"):
            if not isinstance(service.get(field), str) or not service[field]:
                raise ValueError(f"Campo ausente em {name}.{field}")
    return data.get("frame_id", "map"), services


class DoorInfra(Node):
    def __init__(self, **node_options):
        super().__init__("door_infra", **node_options)
        default_services = str(Path(get_package_share_directory("smartwheelchair")) / "config" / "smartworld_services.yaml")
        self.declare_parameter("services_file", default_services)
        self.frame_id, self.actuators = load_services(self.get_parameter("services_file").value)
        self.declare_parameter("mapping_mode", False)
        self.declare_parameter("angle_tolerance", 0.05)
        self.declare_parameter("feedback_timeout", 2.0)
        self.declare_parameter("command_retry", 1.0)
        self.mapping_mode = self.get_parameter("mapping_mode").value
        self.tolerance = float(self.get_parameter("angle_tolerance").value)
        self.feedback_timeout = float(self.get_parameter("feedback_timeout").value)
        self.command_retry = float(self.get_parameter("command_retry").value)
        self.pending = SimpleQueue()
        self.estado = {s: "DESCONHECIDA" for s in self.actuators}
        self.desired = {s: "ABRIR" if self.mapping_mode else "FECHAR" for s in self.actuators}
        self.feedback_at = {s: None for s in self.actuators}
        self.command_at = {s: None for s in self.actuators}
        self.last_announcement = None
        self.last_tick = None
        self.pubs = {s: self.create_publisher(Float64, d["command_topic"], 10)
                     for s, d in self.actuators.items()}
        self.feedback_subs = [
            self.create_subscription(
                JointState, d["feedback_topic"],
                lambda msg, sala=s: self.on_joint(sala, msg), 10)
            for s, d in self.actuators.items()
        ]
        self.create_timer(0.1, self.tick)
        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message
        self.mqtt.reconnect_delay_set(min_delay=1, max_delay=10)
        self.mqtt.connect_async(BROKER, PORT, 60)
        self.mqtt.loop_start()
        if self.mapping_mode:
            self.get_logger().info("Modo mapeamento: todas as portas permanecerão abertas")

    def now(self):
        """Relógio monotônico de parede, imune a `use_sim_time` congelado.

        O tempo de simulação só avança enquanto `/clock` é publicado. Antes de o
        Gazebo subir (ou se a ponte do clock cair), `get_clock().now()` devolve
        0.0 para sempre: os prazos de reenvio e de expiração do feedback nunca
        venceriam e o estado ficaria preso em "DESCONHECIDA". Por isso a infra
        usa o relógio de parede, que é monotônico e sempre avança.
        """
        return time.monotonic()

    def on_connect(self, client, userdata, flags, rc):
        for kind in ("request", "pedido"):
            client.subscribe(f"nara/porta/+/{kind}", qos=1)
        self.pending.put(None)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except (ValueError, UnicodeError):
            return
        if isinstance(data, dict):
            self.pending.put(data)

    def feedback_fresh(self, sala, now):
        """Feedback da junta recente o bastante para o estado ser confiável?"""
        last = self.feedback_at[sala]
        return last is not None and now - last <= self.feedback_timeout

    def anunciar(self, sala):
        service = self.actuators[sala]
        geometry = {key: service[key] for key in ("x", "y", "yaw", "width", "thickness")}
        now = self.now()
        fresh = self.feedback_fresh(sala, now)
        payload = {"sala": sala, "tipo": "porta", **geometry,
                   "frame_id": self.frame_id, "capabilities": ["PERGUNTA", "ABRIR", "FECHAR"],
                   "estado": self.estado[sala],
                   # Explicita se `estado` veio de medição recente. Sem isso, um
                   # "DESCONHECIDA" por ausência de feedback (ex.: ponte tardia ou
                   # relógio parado) seria lido pelo robô como se a porta
                   # estivesse fechada, bloqueando o goal.
                   "feedback_fresh": fresh,
                   "mapping_mode": self.mapping_mode, "t": now}
        self.mqtt.publish(f"nara/porta/{sala}/anuncio", json.dumps(payload),
                          qos=1, retain=True)

    def set_state(self, sala, state):
        # Não rebaixa um estado medido para DESCONHECIDA se a medição ainda é
        # recente: evita que uma única janela sem feedback apague um "ABERTA" já
        # confirmado, o que faria o robô desistir da travessia.
        if state == "DESCONHECIDA" and self.feedback_fresh(sala, self.now()):
            return
        if self.estado[sala] == state:
            return
        self.estado[sala] = state
        self.anunciar(sala)
        self.mqtt.publish(f"nara/porta/{sala}/status",
                          json.dumps({"sala": sala, "estado": state,
                                      "feedback_fresh": state != "DESCONHECIDA",
                                      "t": self.now()}),
                          qos=1, retain=True)
        self.get_logger().info(f"{sala}: estado medido {state}")

    def on_joint(self, sala, msg):
        for index, name in enumerate(msg.name):
            if name.rsplit("::", 1)[-1] != self.actuators[sala]["joint_name"] or index >= len(msg.position):
                continue
            angle = msg.position[index]
            if not math.isfinite(angle):
                return
            self.feedback_at[sala] = self.now()
            if abs(angle - self.actuators[sala]["open_angle"]) <= self.tolerance:
                state = "ABERTA"
            elif abs(angle - self.actuators[sala]["closed_angle"]) <= self.tolerance:
                state = "FECHADA"
            else:
                state = "ABRINDO" if self.desired[sala] == "ABRIR" else "FECHANDO"
            self.set_state(sala, state)
            return

    def pode_atender(self, sala):
        return (True, "mapeamento" if self.mapping_mode else "livre") if (
            self.mapping_mode or NAO_NEGAR) else (False, "politica nao configurada")

    def receive(self, data):
        if data is None:
            self.last_announcement = None
            return
        sala, action = data.get("sala"), data.get("acao")
        if sala not in self.actuators:
            return
        if action == "PERGUNTA":
            allowed, reason = self.pode_atender(sala)
            payload = {"sala": sala, "pode": allowed, "motivo": reason,
                       "estado": self.estado[sala], "t": self.now(),
                       "pedido_t": data.get("t")}
            self.mqtt.publish(f"nara/porta/{sala}/resposta", json.dumps(payload), qos=1)
        elif action in ("ABRIR", "FECHAR"):
            if self.mapping_mode:
                action = "ABRIR"
            if action == "ABRIR" and not self.pode_atender(sala)[0]:
                return
            if self.desired[sala] != action:
                self.desired[sala] = action
                self.command_at[sala] = None
                self.get_logger().info(f"{sala}: alvo {action}")

    def tick(self):
        while not self.pending.empty():
            self.receive(self.pending.get())
        now = self.now()
        if self.last_tick is not None and now < self.last_tick:
            for sala in self.actuators:
                self.command_at[sala] = self.feedback_at[sala] = None
            self.last_announcement = None
        self.last_tick = now
        for sala in self.actuators:
            last = self.feedback_at[sala]
            if last is None or now - last > self.feedback_timeout:
                self.set_state(sala, "DESCONHECIDA")
            # Reenvia o alvo: recupera ponte tardia, comando perdido e reset da junta.
            last = self.command_at[sala]
            if last is None or now - last >= self.command_retry:
                target = self.actuators[sala]["open_angle"] if self.desired[sala] == "ABRIR" else self.actuators[sala]["closed_angle"]
                self.pubs[sala].publish(Float64(data=target))
                self.command_at[sala] = now
        first_announce = self.last_announcement is None
        if first_announce or now - self.last_announcement >= 2.0:
            for sala in self.actuators:
                self.anunciar(sala)
                if first_announce:
                    state = self.estado[sala]
                    self.mqtt.publish(
                        f"nara/porta/{sala}/status",
                        json.dumps({"sala": sala, "estado": state,
                                    "feedback_fresh": self.feedback_fresh(sala, now),
                                    "t": now}),
                        qos=1, retain=True)
            self.last_announcement = now


def main():
    rclpy.init()
    node = DoorInfra()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        for sala in node.actuators:
            for kind in ("anuncio", "status"):
                node.mqtt.publish(f"nara/porta/{sala}/{kind}", "", qos=1, retain=True)
        node.mqtt.loop_stop()
        node.mqtt.disconnect()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
