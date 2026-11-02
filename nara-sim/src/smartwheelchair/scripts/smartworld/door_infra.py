#!/usr/bin/env python3
"""No da infra fixa (passo 3 da camada MQTT): finge ser o ESP32 da parede.

Assina pedidos em nara/porta/+/request, publica o angulo na ponte
ROS->GZ (/smartdoor/<sala>/cmd_pos) e confirma em nara/porta/<sala>/status.

Alem disso, ao subir, ANUNCIA cada porta num topico RETIDO
(nara/porta/<sala>/anuncio): nome, posicao e estado. Quem chegar depois
(o robo) recebe o anuncio do broker sem precisar de lista hardcoded.

Negociacao: o robo consulta antes de atravessar, publicando em
nara/porta/<sala>/pedido {"acao": "PERGUNTA"}. A infra responde em
nara/porta/<sala>/resposta {"pode": true/false, ...}. Hoje a infra sempre
aceita (NAO_NEGAR=True); o "nao" fica como gancho para o futuro.
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

# Por enquanto a infra nunca nega uma passagem. Vire para False e
# implemente a regra em pode_atender() para testar o caminho do "nao".
NAO_NEGAR = True

# Angulo da junta que abre cada porta
OPEN = {"blue": 1.55, "green": -1.55, "orange": 1.55, "pink": -1.55}

# Capacidades da infra: onde cada porta fica (x, y) no mundo.
# E a infra que sabe isso (ela foi instalada ali), nao a cadeira.
POSITION = {
    "blue": (11.0, 2.0),
    "green": (11.0, -2.0),
    "orange": (18.0, 2.0),
    "pink": (18.0, -2.0),
}


class DoorInfra(Node):
    def __init__(self):
        super().__init__("door_infra")
        self.pubs = {
            s: self.create_publisher(Float64, f"/smartdoor/{s}/cmd_pos", 10)
            for s in OPEN
        }
        # Estado que cada porta anuncia (comeca fechada)
        self.estado = {s: "FECHADA" for s in OPEN}
        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message
        self.mqtt.connect(BROKER, PORT, 60)
        self.mqtt.loop_start()
        self.get_logger().info(f"infra no ar, broker {BROKER}:{PORT}")

    def anunciar(self, sala):
        """Publica o anuncio RETIDO da porta: quem se inscrever depois recebe."""
        x, y = POSITION[sala]
        payload = json.dumps({
            "sala": sala, "tipo": "porta", "x": x, "y": y,
            "estado": self.estado[sala], "t": time.time(),
        })
        self.mqtt.publish(f"nara/porta/{sala}/anuncio", payload,
                          qos=1, retain=True)

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe("nara/porta/+/request", qos=1)
        client.subscribe("nara/porta/+/pedido", qos=1)
        self.get_logger().info("assinando nara/porta/+/request e +/pedido")
        # Anuncia todas as portas assim que o broker aceita a conexao
        for sala in OPEN:
            self.anunciar(sala)
        self.get_logger().info(f"anunciadas {len(OPEN)} portas (retido)")

    def pode_atender(self, sala):
        """Politica de acesso da porta. Hoje so aceita; gancho p/ regras futuras.

        Exemplos do que entraria aqui: porta ocupada por outra cadeira,
        modo manutencao, horario, autorizacao por ala.
        """
        if NAO_NEGAR:
            return True, "livre"
        return False, "politica nao configurada"

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except ValueError:
            self.get_logger().warn(f"pedido invalido em {msg.topic}")
            return
        sala = data.get("sala")
        acao = data.get("acao")
        if sala not in OPEN:
            self.get_logger().warn(f"pedido ignorado: {msg.payload.decode()}")
            return
        if acao == "PERGUNTA":
            self.responder_pergunta(sala, data)
            return
        if acao not in ("ABRIR", "FECHAR"):
            self.get_logger().warn(f"pedido ignorado: {msg.payload.decode()}")
            return
        target = OPEN[sala] if acao == "ABRIR" else 0.0
        self.pubs[sala].publish(Float64(data=target))
        self.get_logger().info(f"sala {sala}: {acao} -> junta {target}")
        time.sleep(TRANSIT_TIME)
        estado = "ABERTA" if acao == "ABRIR" else "FECHADA"
        self.estado[sala] = estado
        # Anuncio retido reflete o novo estado para quem chegar depois
        self.anunciar(sala)
        status = json.dumps(
            {"sala": sala, "estado": estado, "t": time.time(),
             "pedido_t": data.get("t")}
        )
        self.mqtt.publish(f"nara/porta/{sala}/status", status, qos=1)
        self.get_logger().info(f"sala {sala}: status {estado}")

    def responder_pergunta(self, sala, data):
        """Consulta da cadeira: 'posso passar por voce?'. Nao move a junta."""
        pode, motivo = self.pode_atender(sala)
        resposta = json.dumps({
            "sala": sala, "pode": pode, "motivo": motivo,
            "estado": self.estado[sala], "t": time.time(),
            "pedido_t": data.get("t"),
        })
        self.mqtt.publish(f"nara/porta/{sala}/resposta", resposta, qos=1)
        self.get_logger().info(
            f"sala {sala}: consulta -> pode={pode} ({motivo})"
        )


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
