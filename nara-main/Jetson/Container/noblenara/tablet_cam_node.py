#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import cv2
import numpy as np
import sys

class TabletCameraPublisher(Node):
    def __init__(self):
        super().__init__('tablet_camera_publisher')
        # TÓPICO ATUALIZADO AQUI 👇
        self.publisher_ = self.create_publisher(CompressedImage, '/noblenara/camera_usuario/compressed', 10)
        self.cap = cv2.VideoCapture(7)
        self.timer = self.create_timer(0.033, self.timer_callback)
        self.failed_frames = 0
        self.get_logger().info("Nó iniciado na NARA! 🚀")

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            self.failed_frames = 0
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE) 
            frame_resized = cv2.resize(frame, (720, 1280))
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
            success, encoded_image = cv2.imencode('.jpg', frame_resized, encode_param)

            if success:
                msg = CompressedImage()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.format = "jpeg"
                msg.data = np.array(encoded_image).tobytes()
                self.publisher_.publish(msg)
        else:
            self.failed_frames += 1
            if self.failed_frames >= 90:
                self.get_logger().error("Fluxo de vídeo perdido! Encerrando...")
                self.cap.release()
                sys.exit(1)

def main(args=None):
    rclpy.init(args=args)
    node = TabletCameraPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
