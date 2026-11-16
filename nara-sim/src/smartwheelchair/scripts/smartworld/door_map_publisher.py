#!/usr/bin/env python3
"""
door_map_publisher.py  —  Bridge MQTT → Nav2 Costmap (100% Python, ZERO hardcoded)

Publica map_with_doors no namespace da cadeira: uma cópia do mapa base
com o estado das portas aplicado ANTES do StaticLayer do Nav2.
/noblenara/door_map continua disponível para inspecionar somente as portas.

DESCOBERTA DINÂMICA:
  - Assina anúncios retidos em nara/porta/+/anuncio
  - A infraestrutura anuncia: sala, x, y, width, thickness, estado
  - Este nó aprende automaticamente onde estão as portas e suas geometrias

LÓGICA DE PINTURA:
  - Porta FECHADA  → custo 100 (LETAL) no retângulo do vão
  - Porta ABERTA   → custo 0   (LIVRE)  no retângulo do vão
  - Resto do mapa  → preserva integralmente o mapa base
"""
import json
import math
import time
from queue import SimpleQueue

import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from nav_msgs.msg import OccupancyGrid
from tf2_ros import Buffer, TransformListener, TransformException
from service_routes import Anchor, Grid, portal_cells


BROKER = "localhost"
PORT = 1883


class DoorMapPublisher(Node):
    def __init__(self):
        super().__init__("door_map_publisher")
        self.declare_parameter("robot_codename", "alfa")
        self.declare_parameter("announcement_timeout", 6.0)
        self.codename = self.get_parameter("robot_codename").value
        self.announcement_timeout = float(self.get_parameter("announcement_timeout").value)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # QoS TRANSIENT_LOCAL obrigatório para o StaticLayer do Nav2 e SLAM
        qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )

        self.map_pub = self.create_publisher(OccupancyGrid, "/noblenara/door_map", qos)
        self.merged_pub = self.create_publisher(OccupancyGrid, "map_with_doors", qos)
        self.pending_messages = SimpleQueue()
        # MQTT roda em outra thread. Só o executor ROS altera portas e mapas.
        self.create_timer(0.1, self.process_pending_messages)

        # Aguarda o mapa base (/noblenara/<codename>/map) publicado pelo SLAM ou map_server
        base_map_topic = f"/noblenara/{self.codename}/map"
        self.create_subscription(OccupancyGrid, base_map_topic, self.on_base_map, qos)

        self.base_map_info = None
        self.base_map_data = None
        self.base_map_frame = f"noblenara/{self.codename}/map"
        
        # Portas descobertas dinamicamente: {sala: {x, y, width, thickness, estado}}
        self.doors = {}
        self.seen_at = {}
        
        # Cliente MQTT
        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message

        try:
            self.mqtt.connect(BROKER, PORT, 60)
            self.mqtt.loop_start()
            self.get_logger().info(f"MQTT conectado em {BROKER}:{PORT}")
        except Exception as e:
            self.get_logger().error(f"Falha ao conectar MQTT: {e}")

        self.get_logger().info(
            f"door_map_publisher iniciado. Aguardando {base_map_topic} e anúncios de portas..."
        )

    # --------------------------------------------------------
    # MQTT CALLBACKS
    # --------------------------------------------------------
    def on_connect(self, client, userdata, flags, rc):
        # Assina anúncios (descoberta + estado) e status (confirmação de abertura/fechamento)
        client.subscribe("nara/porta/+/anuncio", qos=1)
        client.subscribe("nara/porta/+/status", qos=1)
        self.get_logger().info("Assinando nara/porta/+/anuncio (descoberta) e +/status")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except ValueError:
            return

        if isinstance(data, dict) and data.get("sala"):
            self.pending_messages.put((msg.topic.rsplit("/", 1)[-1], data))

    def process_pending_messages(self):
        while not self.pending_messages.empty():
            topic_suffix, data = self.pending_messages.get()
            if topic_suffix == "anuncio":
                self.on_anuncio(data["sala"], data)
            elif topic_suffix == "status":
                self.on_status(data["sala"], data)
        now = time.monotonic()
        stale = [s for s, t in self.seen_at.items() if now - t > self.announcement_timeout]
        if stale:
            for s in stale:
                self.seen_at.pop(s, None)
                self.doors.pop(s, None)
            self.publish_door_map()

    def on_anuncio(self, sala, data):
        """Descobre ou atualiza uma porta a partir do anúncio da infraestrutura."""
        # Extrai geometria do anúncio (enviado pela door_infra)
        x = data.get("x")
        y = data.get("y")
        width = data.get("width")
        thickness = data.get("thickness")
        estado = data.get("estado", "FECHADA")

        if x is None or y is None or width is None or thickness is None:
            self.get_logger().warn(f"Anúncio incompleto da porta '{sala}': {data}")
            return

        is_new = sala not in self.doors
        old_estado = None if is_new else self.doors[sala]["estado"]
        self.seen_at[sala] = time.monotonic()

        entry = {
            "x": float(x),
            "y": float(y),
            "width": float(width),
            "thickness": float(thickness),
            "estado": estado,
            "yaw": float(data.get("yaw", 0.0)),
            "frame_id": data.get("frame_id", "map").lstrip("/")
        }
        changed = is_new or self.doors[sala] != entry
        self.doors[sala] = entry

        if is_new:
            self.get_logger().info(
                f"🚪 Nova porta descoberta: '{sala}' em ({x:.2f}, {y:.2f}) "
                f"[{width:.2f}m x {thickness:.2f}m] estado={estado}"
            )
        elif old_estado != estado:
            self.get_logger().info(f"Porta '{sala}' mudou estado: {old_estado} -> {estado}")

        if changed:
            self.publish_door_map()

    def on_status(self, sala, data):
        """Atualiza estado via confirmação de status (abertura/fechamento concluída)."""
        estado = data.get("estado", "FECHADA")
        if sala in self.doors:
            self.seen_at[sala] = time.monotonic()
            if self.doors[sala]["estado"] != estado:
                self.get_logger().info(f"Porta '{sala}' confirmou: {self.doors[sala]['estado']} -> {estado}")
                self.doors[sala]["estado"] = estado
                self.publish_door_map()

    # --------------------------------------------------------
    # MAP BASE CALLBACK
    # --------------------------------------------------------
    def on_base_map(self, msg):
        if msg.info.resolution <= 0 or len(msg.data) != msg.info.width * msg.info.height:
            self.get_logger().error("Mapa base inválido; atualização ignorada")
            return
        first = self.base_map_info is None
        resized = (
            not first and (
                self.base_map_info.width != msg.info.width or
                self.base_map_info.height != msg.info.height or
                self.base_map_info.origin.position.x != msg.info.origin.position.x or
                self.base_map_info.origin.position.y != msg.info.origin.position.y
            )
        )

        # Atualiza sempre (no SLAM o mapa cresce e muda de origem dinamicamente)
        self.base_map_info = msg.info
        self.base_map_data = list(msg.data)
        if msg.header.frame_id:
            self.base_map_frame = msg.header.frame_id.lstrip("/")

        if first or resized:
            self.get_logger().info(
                f"Mapa base atualizado: {msg.info.width}x{msg.info.height} "
                f"@ {msg.info.resolution:.3f}m (frame: {self.base_map_frame})"
            )

        # Sem anúncios/MQTT, entrega o mapa base intacto ao Nav2.
        self.publish_door_map()

    # --------------------------------------------------------
    # UTILITÁRIOS DE COORDENADAS
    # --------------------------------------------------------
    def world_to_grid(self, wx, wy):
        """Converte coordenadas mundo (metros) -> índices de grid (col, row)."""
        info = self.base_map_info
        ox = info.origin.position.x
        oy = info.origin.position.y
        res = info.resolution
        q = info.origin.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
        dx, dy = wx - ox, wy - oy
        col = math.floor((math.cos(yaw) * dx + math.sin(yaw) * dy) / res)
        row = math.floor((-math.sin(yaw) * dx + math.cos(yaw) * dy) / res)
        return col, row

    # --------------------------------------------------------
    # PUBLICAÇÃO DO MAPA DE PORTAS
    # --------------------------------------------------------
    def publish_door_map(self):
        if self.base_map_info is None:
            return
        info = self.base_map_info
        q = info.origin.orientation
        yaw = math.atan2(2 * (q.w*q.z + q.x*q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
        grid = Grid(info.width, info.height, info.resolution,
                    info.origin.position.x, info.origin.position.y, yaw)
        overlay = [-1] * (info.width * info.height)
        merged_data = list(self.base_map_data)
        for name, d in self.doors.items():
            anchor = Anchor(name, d["x"], d["y"], d["width"], d["thickness"], d["yaw"])
            if d["frame_id"] not in ("map", self.base_map_frame):
                try:
                    tf = self.tf_buffer.lookup_transform(
                        self.base_map_frame, d["frame_id"], rclpy.time.Time())
                except TransformException:
                    self.get_logger().warning(f"Âncora {name}: aguardando transformação de coordenadas")
                    continue
                q = tf.transform.rotation
                angle = math.atan2(2 * (q.w*q.z + q.x*q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
                x = tf.transform.translation.x + math.cos(angle) * anchor.x - math.sin(angle) * anchor.y
                y = tf.transform.translation.y + math.sin(angle) * anchor.x + math.cos(angle) * anchor.y
                anchor = Anchor(name, x, y, anchor.width, anchor.thickness, anchor.yaw + angle)
            # Somente uma abertura fisicamente confirmada libera o mapa real.
            value = 0 if d["estado"] == "ABERTA" else 100
            for index in portal_cells(grid, anchor):
                overlay[index] = merged_data[index] = value
        out = OccupancyGrid()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = self.base_map_frame
        out.info = info
        out.data = overlay
        self.map_pub.publish(out)
        merged = OccupancyGrid()
        merged.header = out.header
        merged.info = info
        merged.data = merged_data
        self.merged_pub.publish(merged)


def main(args=None):
    rclpy.init(args=args)
    node = DoorMapPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.mqtt.loop_stop()
        node.mqtt.disconnect()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
