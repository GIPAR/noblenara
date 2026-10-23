#!/usr/bin/env python3
"""No solicitante da cadeira (agente movel, camada MQTT).

Le a odometria pronta em /noblenara/<codename>/odom, calcula a distancia
ate cada ancora de servico (porta) e, ao chegar perto, publica UM pedido
de abertura no broker. Ao se afastar, publica FECHAR apos carencia.
Nao envia odometria ao broker: so evento discreto.
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

# Ancoras de servico: centro de cada vao (x, y) no mapa
DOORS = {
    "blue": (11.0, 2.0),
    "green": (11.0, -2.0),
    "orange": (18.0, 2.0),
    "pink": (18.0, -2.0),
}


class DoorRequester(Node):
    def __init__(self):
        super().__init__("door_requester")
        self.declare_parameter("robot_codename", "alfa")
        self.declare_parameter("request_radius", 3.0)
        self.declare_parameter("release_radius", 3.5)
        self.declare_parameter("close_delay", 5.0)
        cod = self.get_parameter("robot_codename").value
        self.radius = float(self.get_parameter("request_radius").value)
        self.release = float(self.get_parameter("release_radius").value)
        self.close_delay = float(self.get_parameter("close_delay").value)

        self.requested = {d: False for d in DOORS}
        self.closing_since = {}
        self.last_dist = {}
        self.t0 = {}

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
        client.subscribe("nara/porta/+/status", qos=1)
        self.get_logger().info("assinando nara/porta/+/status")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except ValueError:
            self.get_logger().warn(f"status invalido em {msg.topic}")
            return
        sala = data.get("sala", "?")
        estado = data.get("estado", "?")
        self.get_logger().info(f"status {sala}: {estado}")
        if estado == "ABERTA" and sala in self.t0:
            lat = time.time() - self.t0.pop(sala)
            self.get_logger().info(f"latencia pedido->abertura sala {sala}: {lat:.3f}s")

    def publish(self, sala, acao):
        payload = json.dumps({"acao": acao, "sala": sala, "t": time.time()})
        self.mqtt.publish(f"nara/porta/{sala}/request", payload, qos=1)

    def on_odom(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        now = time.time()
        for sala, (dx, dy) in DOORS.items():
            dist = math.hypot(x - dx, y - dy)
            self.last_dist[sala] = dist
            self.evaluate(sala, dist, now)

    def check_closing(self):
        now = time.time()
        for sala, dist in self.last_dist.items():
            self.evaluate(sala, dist, now)

    def evaluate(self, sala, dist, now):
            if not self.requested[sala] and dist < self.radius:
                self.t0[sala] = now
                self.publish(sala, "ABRIR")
                self.requested[sala] = True
                self.closing_since.pop(sala, None)
                self.get_logger().info(
                    f"pedido ABRIR sala {sala} (dist {dist:.2f}m)"
                )
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
