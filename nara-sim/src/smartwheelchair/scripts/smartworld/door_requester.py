#!/usr/bin/env python3
"""No solicitante da cadeira (agente movel, camada MQTT).

Le a odometria pronta em /noblenara/<codename>/odom, calcula a distancia
ate cada ancora de servico (porta) e, ao chegar perto, publica UM pedido
de abertura no broker. Ao se afastar, publica FECHAR apos carencia.
Nao envia odometria ao broker: so evento discreto.

As portas NAO sao hardcoded: o no assina nara/porta/+/anuncio (retido) e
descobre sozinho quais portas existem, onde ficam e o estado atual. Quem
sabe isso e a infraestrutura, que se apresenta no broker.
"""
import json
import math
import time

import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

BROKER = "localhost"
PORT = 1883


class DoorRequester(Node):
    def __init__(self):
        super().__init__("door_requester")
        self.declare_parameter("robot_codename", "alfa")
        self.declare_parameter("request_radius", 3.0)
        self.declare_parameter("release_radius", 3.5)
        self.declare_parameter("close_delay", 5.0)
        self.declare_parameter("consulta_timeout", 2.0)
        cod = self.get_parameter("robot_codename").value
        self.radius = float(self.get_parameter("request_radius").value)
        self.release = float(self.get_parameter("release_radius").value)
        self.close_delay = float(self.get_parameter("close_delay").value)
        self.consulta_timeout = float(
            self.get_parameter("consulta_timeout").value
        )

        # Portas descobertas via anuncio: {sala: (x, y)}
        self.portas = {}
        self.requested = {}
        self.closing_since = {}
        self.last_dist = {}
        self.t0 = {}
        # Negociacao: resultado da ultima consulta e marca temporal
        self.consultas = {}
        self.t_consulta = {}

        self.create_subscription(
            Odometry, f"/noblenara/{cod}/odom", self.on_odom, 10
        )
        # Timer avalia fechamentos pendentes mesmo se a odom parar de chegar
        self.create_timer(1.0, self.check_closing)

        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message
        self.mqtt.connect(BROKER, PORT, 60)
        self.mqtt.loop_start()
        self.get_logger().info(f"conectado ao broker {BROKER}:{PORT}")

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe("nara/porta/+/anuncio", qos=1)
        client.subscribe("nara/porta/+/status", qos=1)
        client.subscribe("nara/porta/+/resposta", qos=1)
        self.get_logger().info(
            "assinando nara/porta/+/anuncio, +/status e +/resposta"
        )

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except ValueError:
            self.get_logger().warn(f"mensagem invalida em {msg.topic}")
            return
        tipo = msg.topic.rsplit("/", 1)[-1]
        if tipo == "anuncio":
            self.on_anuncio(data)
        elif tipo == "resposta":
            self.on_resposta(data)
        else:
            self.on_status(data)

    def on_anuncio(self, data):
        """Descobre (ou atualiza) uma porta a partir do anuncio da infra."""
        sala = data.get("sala")
        if sala is None or "x" not in data or "y" not in data:
            self.get_logger().warn(f"anuncio incompleto: {data}")
            return
        novo = (float(data["x"]), float(data["y"]))
        if sala not in self.portas:
            self.portas[sala] = novo
            self.requested[sala] = False
            self.consultas[sala] = None
            self.get_logger().info(
                f"descobri porta '{sala}' em {novo} "
                f"(estado {data.get('estado', '?')})"
            )
        else:
            self.portas[sala] = novo

    def on_status(self, data):
        sala = data.get("sala", "?")
        estado = data.get("estado", "?")
        self.get_logger().info(f"status {sala}: {estado}")
        if estado == "ABERTA" and sala in self.t0:
            lat = time.time() - self.t0.pop(sala)
            self.get_logger().info(f"latencia pedido->abertura sala {sala}: {lat:.3f}s")

    def on_resposta(self, data):
        """Resposta da infra a uma consulta 'posso passar?'."""
        sala = data.get("sala", "?")
        pode = data.get("pode", False)
        self.consultas[sala] = bool(pode)
        lat = ""
        if sala in self.t_consulta:
            lat = f" ({(time.time() - self.t_consulta.pop(sala)) * 1000:.0f} ms)"
        estado = "LIBERADA" if pode else "NEGADA"
        self.get_logger().info(
            f"consulta sala {sala}: {estado} "
            f"motivo={data.get('motivo', '?')}{lat}"
        )

    def consultar(self, sala):
        """Pergunta a infra se a porta pode ser usada. Nao move a junta."""
        self.t_consulta[sala] = time.time()
        payload = json.dumps({"acao": "PERGUNTA", "sala": sala, "t": time.time()})
        self.mqtt.publish(f"nara/porta/{sala}/pedido", payload, qos=1)
        self.get_logger().info(f"consultando sala {sala} (pode passar?)")

    def publish(self, sala, acao):
        payload = json.dumps({"acao": acao, "sala": sala, "t": time.time()})
        self.mqtt.publish(f"nara/porta/{sala}/request", payload, qos=1)

    def on_odom(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        now = time.time()
        for sala, (dx, dy) in self.portas.items():
            dist = math.hypot(x - dx, y - dy)
            self.last_dist[sala] = dist
            self.evaluate(sala, dist, now)

    def check_closing(self):
        now = time.time()
        for sala, dist in self.last_dist.items():
            self.evaluate(sala, dist, now)

    def evaluate(self, sala, dist, now):
            if not self.requested[sala] and dist < self.radius:
                # 1) pergunta a infra se pode passar (negociacao)
                if self.consultas.get(sala) is None:
                    enviada = self.t_consulta.get(sala)
                    if enviada is None:
                        self.consultar(sala)
                    elif now - enviada >= self.consulta_timeout:
                        # infra nao respondeu: reconsulta em vez de travar
                        self.get_logger().warn(
                            f"sala {sala}: sem resposta ha "
                            f"{now - enviada:.1f}s, reconsultando"
                        )
                        self.consultar(sala)
                    return
                # 2) so pede abertura se a infra liberou
                if not self.consultas[sala]:
                    self.get_logger().warn(
                        f"sala {sala}: passagem negada pela infra, "
                        f"nao pedindo abertura"
                    )
                    return
                self.t0[sala] = now
                self.publish(sala, "ABRIR")
                self.requested[sala] = True
                self.closing_since.pop(sala, None)
                self.get_logger().info(
                    f"pedido ABRIR sala {sala} (dist {dist:.2f}m)"
                )
            elif not self.requested[sala] and dist > self.release:
                # longe e sem pedido: descarta a negociacao anterior para
                # que uma nova aproximacao consulte a infra de novo
                if sala in self.t_consulta:
                    self.t_consulta.pop(sala, None)
                if self.consultas.get(sala) is False:
                    self.consultas[sala] = None
            elif self.requested[sala] and dist > self.release:
                if sala not in self.closing_since:
                    self.closing_since[sala] = now
                    self.get_logger().info(
                        f"sala {sala} fechando em {self.close_delay:.0f}s "
                        f"(dist {dist:.2f}m)"
                    )
                elif now - self.closing_since[sala] >= self.close_delay:
                    self.publish(sala, "FECHAR")
                    self.requested[sala] = False
                    self.consultas[sala] = None   # nova aproximacao reconsulta
                    self.closing_since.pop(sala, None)
                    self.get_logger().info(f"pedido FECHAR sala {sala}")
            elif self.requested[sala] and sala in self.closing_since:
                # voltou para perto antes da carencia: cancela o fechamento
                self.closing_since.pop(sala, None)
                self.get_logger().info(
                    f"fechamento da sala {sala} cancelado (voltou p/ perto)"
                )


def main():
    rclpy.init()
    node = DoorRequester()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.mqtt.loop_stop()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
