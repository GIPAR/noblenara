#!/usr/bin/env python3
"""Coordena metas ROS com âncoras MQTT descobertas, sem conhecer salas ou mapas."""
import copy
import json
import math
import time
from dataclasses import dataclass
from queue import SimpleQueue

import paho.mqtt.client as mqtt
import rclpy
from action_msgs.msg import GoalStatusArray
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from tf2_ros import Buffer, TransformListener, TransformException

from service_routes import Anchor, Grid, find_service_route

BROKER = "localhost"
PORT = 1883


@dataclass
class Door:
    anchor: Anchor
    frame_id: str = "map"
    estado: str = "DESCONHECIDA"
    confirmed_at: float | None = None
    permission: bool | None = None
    query_at: float | None = None
    command: str | None = None
    command_at: float | None = None
    closing_since: float | None = None
    seen_at: float = 0.0


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class DoorRequester(Node):
    def __init__(self, **node_options):
        super().__init__("door_requester", **node_options)
        defaults = {"robot_codename": "alfa", "request_radius": 4.0,
                    "release_radius": 4.5, "close_delay": 5.0,
                    "consulta_timeout": 2.0, "command_retry": 3.0,
                    "odom_timeout": 1.0, "access_timeout": 15.0,
                    "announcement_timeout": 6.0, "route_clearance": 0.45,
                    "passage_clearance": 1.3, "handoff_delay": 0.5}
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        cod = self.get_parameter("robot_codename").value
        self.settings = {k: self.get_parameter(k).value for k in defaults}
        if not 0 < self.settings["request_radius"] < self.settings["release_radius"]:
            raise ValueError("request_radius deve ser positivo e menor que release_radius")
        self.global_frame = f"noblenara/{cod}/map"
        self.base_frame = f"noblenara/{cod}/robot_footprint"
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.doors = {}
        self.pending = SimpleQueue()
        self.odom_at = self.last_check = None
        self.map_msg = self.grid = None
        self.goal = self.route = None
        self.phase = "idle"
        self.required, self.passed, self.denied = [], set(), set()
        self.preparing_at = self.ready_at = None
        self.nav_seen = self.nav_active = False
        self.state_future = None
        self.state_query_at = None
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(OccupancyGrid, f"/noblenara/{cod}/map", self.on_map, qos)
        self.create_subscription(Odometry, f"/noblenara/{cod}/odom", self.on_odom, 10)
        self.create_subscription(PoseStamped, f"/noblenara/{cod}/goal_pose", self.on_goal, 10)
        self.create_subscription(GoalStatusArray, f"/noblenara/{cod}/navigate_to_pose/_action/status",
                                 self.on_nav_status, qos)
        self.goal_pub = self.create_publisher(PoseStamped, f"/noblenara/{cod}/navigation_goal", 10)
        self.cancel_client = self.create_client(CancelGoal, f"/noblenara/{cod}/navigate_to_pose/_action/cancel_goal")
        self.state_client = self.create_client(GetState, f"/noblenara/{cod}/bt_navigator/get_state")
        self.create_timer(0.2, self.tick)
        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message
        self.mqtt.reconnect_delay_set(min_delay=1, max_delay=10)
        self.mqtt.connect_async(BROKER, PORT, 60)
        self.mqtt.loop_start()

    def now(self):
        """Relógio monotônico de parede para todos os prazos internos.

        `use_sim_time` só avança com `/clock`; antes do Gazebo subir ele fica em
        0.0 e nenhum prazo (consulta, reenvio, timeout de acesso) venceria, o que
        prendia o goal em "preparing" para sempre. Os timestamps das mensagens
        continuam usando o tempo de simulação, como o Nav2 espera.
        """
        return time.monotonic()

    def on_connect(self, client, userdata, flags, rc):
        for kind in ("anuncio", "status", "resposta"):
            client.subscribe(f"nara/porta/+/{kind}", qos=1)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except (ValueError, UnicodeError):
            return
        if isinstance(data, dict) and data.get("sala"):
            self.pending.put((msg.topic.rsplit("/", 1)[-1], data))

    def receive(self, kind, data):
        name = data["sala"]
        if not isinstance(name, str) or not name:
            return
        if kind == "anuncio":
            try:
                a = Anchor(str(name), *(float(data[k]) for k in ("x", "y", "width", "thickness")),
                           float(data.get("yaw", 0.0)))
                if a.width <= 0 or a.thickness <= 0 or not all(math.isfinite(v) for v in (
                        a.x, a.y, a.width, a.thickness, a.yaw)):
                    raise ValueError("geometria inválida")
            except (KeyError, TypeError, ValueError):
                self.get_logger().warning(f"Anúncio inválido: {name}")
                return
            if name not in self.doors:
                self.doors[name] = Door(a)
                self.get_logger().info(f"Âncora descoberta: {name}")
                if self.phase == "preparing":
                    self.route = None
            d = self.doors[name]
            d.anchor = a
            frame = data.get("frame_id", "map")
            d.frame_id = frame.lstrip("/") if isinstance(frame, str) else "map"
            d.seen_at = self.now()
        if name not in self.doors:
            return
        d = self.doors[name]
        now = self.now()
        d.seen_at = now
        if kind in ("anuncio", "status"):
            estado = data.get("estado", "DESCONHECIDA")
            fresh = data.get("feedback_fresh")
            if fresh is True or estado != "DESCONHECIDA":
                d.estado = estado
                if fresh is True:
                    d.confirmed_at = now
            elif d.confirmed_at is None or now - d.confirmed_at > self.settings["announcement_timeout"]:
                d.estado = "DESCONHECIDA"
        elif kind == "resposta" and d.query_at is not None and data.get("pedido_t") == d.query_at:
            d.permission = data.get("pode") is True

    def on_map(self, msg):
        if (msg.info.resolution <= 0 or not msg.info.width or not msg.info.height
                or len(msg.data) != msg.info.width * msg.info.height):
            return
        info = msg.info
        grid = Grid(info.width, info.height, info.resolution, info.origin.position.x,
                    info.origin.position.y, yaw_of(info.origin.orientation))
        # Só invalida a rota candidata se a geometria do grid mudou (primeiro
        # mapa ou redimensionamento no SLAM). Republicações periódicas do mesmo
        # mapa zeravam `route` e `ready_at` a cada ciclo, impedindo que
        # `now - ready_at` atingisse `handoff_delay` e bloqueando o envio ao Nav2.
        if self.phase == "preparing" and grid != self.grid:
            self.route = None
        self.map_msg = msg
        self.grid = grid

    def on_odom(self, msg):
        self.odom_at = self.now()

    def reset_mission(self):
        self.goal = self.route = None
        self.required, self.passed, self.denied = [], set(), set()
        self.ready_at = None
        self.phase = "idle"

    def on_goal(self, msg):
        previous = self.phase
        self.reset_mission()
        if previous == "navigating" and self.cancel_client.service_is_ready():
            self.cancel_client.call_async(CancelGoal.Request())
        goal = copy.deepcopy(msg)
        frame = goal.header.frame_id.lstrip("/")
        if frame == "map":
            frame = self.global_frame
        try:
            if frame != self.global_frame:
                tf = self.tf_buffer.lookup_transform(self.global_frame, frame, rclpy.time.Time())
                yaw = yaw_of(tf.transform.rotation)
                x, y = goal.pose.position.x, goal.pose.position.y
                goal.pose.position.x = tf.transform.translation.x + math.cos(yaw) * x - math.sin(yaw) * y
                goal.pose.position.y = tf.transform.translation.y + math.sin(yaw) * x + math.cos(yaw) * y
                angle = yaw + yaw_of(goal.pose.orientation)
                goal.pose.orientation.x = goal.pose.orientation.y = 0.0
                goal.pose.orientation.z, goal.pose.orientation.w = math.sin(angle / 2), math.cos(angle / 2)
        except TransformException:
            self.get_logger().error("Meta recusada: falta transformação para o frame do mapa")
            return
        if not all(math.isfinite(v) for v in (goal.pose.position.x, goal.pose.position.y)):
            return
        goal.header.frame_id = self.global_frame
        self.goal = goal
        self.phase = "preparing"
        self.preparing_at = self.now()
        for d in self.doors.values():
            d.permission = d.query_at = None
        self.get_logger().info("Preparando acesso às âncoras necessárias antes de enviar a meta ao Nav2")

    def on_nav_status(self, msg):
        if self.phase != "navigating":
            return
        if any(s.status in (1, 2, 3) for s in msg.status_list):
            self.nav_seen = True
        elif self.nav_seen and msg.status_list:
            self.reset_mission()

    def send(self, name, action, now):
        kind = "pedido" if action == "PERGUNTA" else "request"
        payload = json.dumps({"acao": action, "sala": name, "t": now})
        self.mqtt.publish(f"nara/porta/{name}/{kind}", payload, qos=1)
        self.get_logger().info(f"{name}: {action}")

    def anchors_in_map(self):
        result = {}
        for name, d in self.doors.items():
            a = d.anchor
            if d.frame_id in ("map", self.global_frame):
                result[name] = a
            else:
                tf = self.tf_buffer.lookup_transform(self.global_frame, d.frame_id, rclpy.time.Time())
                angle = yaw_of(tf.transform.rotation)
                x = tf.transform.translation.x + math.cos(angle) * a.x - math.sin(angle) * a.y
                y = tf.transform.translation.y + math.sin(angle) * a.x + math.cos(angle) * a.y
                result[name] = Anchor(name, x, y, a.width, a.thickness, a.yaw + angle)
        return result

    def fail(self, reason):
        self.get_logger().error(reason)
        self.reset_mission()

    def prepare(self, now, position, anchors):
        if self.route is None:
            if anchors and self.grid is None:
                return
            prev_required = self.required
            if anchors:
                target = (self.goal.pose.position.x, self.goal.pose.position.y)
                self.route = find_service_route(self.map_msg.data, self.grid, position, target,
                                                list(anchors.values()), self.denied,
                                                self.settings["route_clearance"])
                if self.route is None:
                    self.fail("Sem rota candidata pelas âncoras disponíveis; meta não enviada ao Nav2")
                    return
                self.required = self.route.services
            else:
                self.required = []
                self.route = True
            if self.required != prev_required:
                self.ready_at = None
            self.get_logger().info("Serviços selecionados: " + (", ".join(self.required) or "nenhum"))
        # Só uma recusa explícita justifica procurar outra rota. Um anúncio apenas
        # antigo (infra reiniciando, MQTT reconectando) não significa que a porta
        # esteja inacessível: tratá-lo como negação descartava a passagem
        # obrigatória e mandava a meta por um caminho impossível.
        blocked = [name for name in self.required if self.doors[name].permission is False]
        missing = [name for name in self.required
                   if now - self.doors[name].seen_at > self.settings["announcement_timeout"]]
        if missing and not blocked:
            self.fail("Âncoras sem anúncio recente (%s); meta não enviada ao Nav2" % ", ".join(missing))
            return
        if blocked:
            self.denied.update(blocked)
            self.route = None
            self.required = []
            self.ready_at = None
            self.preparing_at = now
            self.get_logger().warning("Recalculando acesso sem serviços negados/indisponíveis: " + ", ".join(blocked))
            return
        ready = all(self.doors[name].permission is True and self.doors[name].estado == "ABERTA"
                    for name in self.required)
        if ready:
            if self.ready_at is None:
                self.ready_at = now
            delay = self.settings["handoff_delay"] if self.required else 0.0
            if (self.nav_active and self.goal_pub.get_subscription_count()
                    and now - self.ready_at >= delay):
                self.goal.header.stamp = self.get_clock().now().to_msg()
                self.goal_pub.publish(self.goal)
                self.phase, self.nav_seen = "navigating", False
                self.get_logger().info("Acesso confirmado; meta encaminhada ao Nav2")
        else:
            self.ready_at = None
        if self.phase == "preparing" and now - self.preparing_at > self.settings["access_timeout"]:
            # Negar o serviço que simplesmente demorou a abrir era um erro: isso
            # removia a única passagem exigida e o goal era enviado ao Nav2 por um
            # caminho que o robô não pode atravessar. Só marcamos como negado o que
            # a infraestrutura recusou explicitamente; falha de abertura/timeout
            # aborta a missão com aviso claro, sem encaminhar a meta.
            refused = [name for name in self.required if self.doors[name].permission is False]
            if refused:
                self.denied.update(refused)
                self.route, self.required, self.ready_at = None, [], None
                self.preparing_at = now
                self.get_logger().warning("Acesso recusado pela infraestrutura; buscando alternativa: "
                                          + ", ".join(refused))
            else:
                pending = [name for name in self.required if (
                    self.doors[name].permission is not True or self.doors[name].estado != "ABERTA")]
                if pending:
                    self.fail("Serviço não abriu dentro do prazo (%s); meta não enviada ao Nav2"
                              % ", ".join(pending))
                else:
                    self.fail("Nav2 não ficou disponível para receber a meta")

    def drive_door(self, name, d, position, now, held):
        a = self.current_anchors[name]
        distance = math.hypot(position[0] - a.x, position[1] - a.y)
        if held or distance <= self.settings["request_radius"]:
            d.closing_since = None
            if d.estado == "ABERTA" and not held:
                return
            if d.permission is not True:
                if d.query_at is None or now - d.query_at >= self.settings["consulta_timeout"]:
                    d.query_at = now
                    self.send(name, "PERGUNTA", now)
                return
            if d.estado != "ABERTA" and (d.command != "ABRIR" or d.command_at is None
                    or now - d.command_at >= self.settings["command_retry"]):
                self.send(name, "ABRIR", now)
                d.command, d.command_at = "ABRIR", now
        elif distance >= self.settings["release_radius"]:
            d.permission = d.query_at = None
            if d.estado in ("FECHADA", "DESCONHECIDA"):
                d.closing_since = None
                return
            if d.closing_since is None:
                d.closing_since = now
            if now - d.closing_since >= self.settings["close_delay"] and (
                    d.command != "FECHAR" or d.command_at is None
                    or now - d.command_at >= self.settings["command_retry"]):
                self.send(name, "FECHAR", now)
                d.command, d.command_at = "FECHAR", now
        else:
            d.closing_since = None

    def tick(self):
        while not self.pending.empty():
            self.receive(*self.pending.get())
        now = self.now()
        if self.last_check is not None and now < self.last_check:
            self.reset_mission()
            self.nav_active = False
            self.state_query_at = self.state_future = None
            for d in self.doors.values():
                d.query_at = d.command_at = d.closing_since = None
                d.permission = None
        self.last_check = now
        if self.phase == "idle":
            stale = [name for name, d in self.doors.items()
                     if now - d.seen_at > self.settings["announcement_timeout"]]
            for name in stale:
                del self.doors[name]
        if self.state_future is not None and self.state_future.done():
            try:
                self.nav_active = self.state_future.result().current_state.id == 3
            except Exception:
                self.nav_active = False
            self.state_future = None
        if self.state_future is None and (self.state_query_at is None or now - self.state_query_at >= 1):
            if self.state_client.service_is_ready():
                self.state_future = self.state_client.call_async(GetState.Request())
                self.state_query_at = now
        if not self.doors:
            if self.phase == "preparing":
                self.prepare(now, (0.0, 0.0), {})
            return
        if self.odom_at is None or not 0 <= now - self.odom_at <= self.settings["odom_timeout"]:
            for d in self.doors.values():
                d.closing_since = None
            return
        try:
            tr = self.tf_buffer.lookup_transform(self.global_frame, self.base_frame, rclpy.time.Time())
            # A idade é medida pela chegada da odometria (relógio monotônico), não
            # pelo header.stamp: com use_sim_time o stamp está no domínio da
            # simulação e compará-lo com o relógio de parede nunca fecharia. O
            # stamp continua sendo validado quanto a saltos para trás pelo
            # watchdog de `last_check` e por `on_odom`.
            position = (tr.transform.translation.x, tr.transform.translation.y)
            self.current_anchors = self.anchors_in_map()
        except TransformException:
            return
        if self.phase == "preparing":
            self.prepare(now, position, self.current_anchors)
        if self.phase == "navigating" and self.route is not True:
            for name in self.required:
                side = self.current_anchors[name].side(position)
                if side * self.route.entry_sides[name] < 0 and abs(side) >= self.settings["passage_clearance"]:
                    self.passed.add(name)
        held = set(self.required) - self.passed if self.phase in ("preparing", "navigating") else set()
        for name, d in self.doors.items():
            self.drive_door(name, d, position, now, name in held)


def main():
    rclpy.init()
    node = DoorRequester()
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
