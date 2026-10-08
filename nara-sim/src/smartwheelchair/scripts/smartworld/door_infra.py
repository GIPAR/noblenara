#!/usr/bin/env python3
"""No da infra fixa (passo 3 da camada MQTT): finge ser o ESP32 da parede.

Assina pedidos em nara/porta/+/request, publica o angulo na ponte
ROS->GZ (/smartdoor/<sala>/cmd_pos) e confirma em nara/porta/<sala>/status.
"""
import json
import time

import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

BROKER = "localhost"
PORT = 1883
TRANSIT_TIME = 2.0  # provisório: sem leitura da junta ainda, estima o giro

OPEN = {"blue": 1.55, "green": -1.55, "orange": 1.55, "pink": -1.55}


class DoorInfra(Node):
    def __init__(self):
        super().__init__("door_infra")
        self.pubs = {
            s: self.create_publisher(Float64, f"/smartdoor/{s}/cmd_pos", 10)
            for s in OPEN
        }
        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message
        self.mqtt.connect(BROKER, PORT, 60)
        self.mqtt.loop_start()
        self.get_logger().info(f"infra no ar, broker {BROKER}:{PORT}")

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe("nara/porta/+/request", qos=1)
        self.get_logger().info("assinando nara/porta/+/request")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except ValueError:
            self.get_logger().warn(f"pedido invalido em {msg.topic}")
            return
        sala = data.get("sala")
        acao = data.get("acao")
        if sala not in OPEN or acao not in ("ABRIR", "FECHAR"):
            self.get_logger().warn(f"pedido ignorado: {msg.payload.decode()}")
            return
        target = OPEN[sala] if acao == "ABRIR" else 0.0
        self.pubs[sala].publish(Float64(data=target))
        self.get_logger().info(f"sala {sala}: {acao} -> junta {target}")
        time.sleep(TRANSIT_TIME)
        estado = "ABERTA" if acao == "ABRIR" else "FECHADA"
        status = json.dumps(
            {"sala": sala, "estado": estado, "t": time.time(),
             "pedido_t": data.get("t")}
        )
        self.mqtt.publish(f"nara/porta/{sala}/status", status, qos=1)
        self.get_logger().info(f"sala {sala}: status {estado}")


def main():
    rclpy.init()
    node = DoorInfra()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.mqtt.loop_stop()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
