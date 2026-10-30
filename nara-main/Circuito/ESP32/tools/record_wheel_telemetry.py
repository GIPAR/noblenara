#!/usr/bin/env python3
"""Grava WheelTelemetry em CSV; executar com ROS Jazzy e a interface carregados."""

import argparse
import csv
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from noblenara_interface.msg import WheelTelemetry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="Arquivo CSV novo (nao sobrescreve)")
    parser.add_argument("--duration", type=float, default=0, help="Segundos; zero grava ate Ctrl+C")
    parser.add_argument("--topic", default="/noblenara/wheel_telemetry")
    args = parser.parse_args()
    if args.duration < 0:
        parser.error("--duration deve ser positivo ou zero")

    fields = WheelTelemetry.get_fields_and_field_types()
    arrays = {name for name, kind in fields.items() if "[2]" in kind}
    columns = ["received_unix_ns", "stamp_sec", "stamp_nanosec"]
    for name in fields:
        if name == "stamp":
            continue
        columns.extend([f"{name}_left", f"{name}_right"] if name in arrays else [name])

    rclpy.init()
    node = Node("record_wheel_telemetry")
    try:
        with open(args.output, "x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()

            def receive(msg):
                row = {"received_unix_ns": time.time_ns(), "stamp_sec": msg.stamp.sec,
                       "stamp_nanosec": msg.stamp.nanosec}
                for name in fields:
                    if name == "stamp":
                        continue
                    value = getattr(msg, name)
                    if name in arrays:
                        row[f"{name}_left"], row[f"{name}_right"] = value
                    else:
                        row[name] = value
                writer.writerow(row)
                stream.flush()

            subscription = node.create_subscription(
                WheelTelemetry, args.topic, receive, qos_profile_sensor_data)
            node.get_logger().info(f"Gravando {args.topic} em {args.output}")
            start = time.monotonic()
            while rclpy.ok() and (not args.duration or time.monotonic() - start < args.duration):
                rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
