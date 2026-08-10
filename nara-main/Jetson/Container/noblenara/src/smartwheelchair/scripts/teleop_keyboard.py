#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from pynput import keyboard
import time

class TeleopKeyboard(Node):
    def __init__(self):
        super().__init__('teleop_keyboard')

        self.publisher = self.create_publisher(Twist, '/noblenara/cmd_vel', 10)

        self.keys_pressed = set()

        self.linear_speed = 3.0
        self.angular_speed = 0.6
        self.acceleration_rate = 0.06
        self.deceleration_rate = 0.20

        self.current_linear = 0.0
        self.current_angular = 0.0

        self.acceleration_timer = self.create_timer(0.05, self.update_velocity)

        self.listener_running = True

        print('\n' + '='*50)
        print('🎮 CONTROLADOR NARA - MODO SEGURAR TECLA')
        print('='*50)
        print('\n📋 CONTROLES:')
        print('  W → Frente (segure para acelerar)')
        print('  S → Trás (segure para acelerar)')
        print('  A → Girar Esquerda (segure para girar)')
        print('  D → Girar Direita (segure para girar)')
        print('  W+A/D → Curva para frente')
        print('  S+A/D → Curva para trás')
        print('  ESPAÇO → Parar')
        print('  ESC → Sair')
        print('\n💡 SOLTE a tecla para desacelerar!')
        print('='*50 + '\n')

    def update_velocity(self):
        target_linear = 0.0
        target_angular = 0.0

        if 'w' in self.keys_pressed:
            target_angular = -self.linear_speed
        if 's' in self.keys_pressed:
            target_angular = self.linear_speed
        if 'a' in self.keys_pressed:
            target_linear = -self.angular_speed
        if 'd' in self.keys_pressed:
            target_linear = self.angular_speed

        if target_linear > self.current_linear:
            self.current_linear += self.acceleration_rate
            self.current_linear = min(target_linear, self.current_linear)
        elif target_linear < self.current_linear:
            self.current_linear -= self.acceleration_rate
            self.current_linear = max(target_linear, self.current_linear)

        if target_angular > self.current_angular:
            self.current_angular += self.acceleration_rate
            self.current_angular = min(target_angular, self.current_angular)
        elif target_angular < self.current_angular:
            self.current_angular -= self.acceleration_rate
            self.current_angular = max(target_angular, self.current_angular)

        if target_linear == 0.0 and abs(self.current_linear) > 0.01:
            if self.current_linear > 0:
                self.current_linear = max(0, self.current_linear - self.deceleration_rate)
            else:
                self.current_linear = min(0, self.current_linear + self.deceleration_rate)

        if target_angular == 0.0 and abs(self.current_angular) > 0.01:
            if self.current_angular > 0:
                self.current_angular = max(0, self.current_angular - self.deceleration_rate)
            else:
                self.current_angular = min(0, self.current_angular + self.deceleration_rate)

        self.publish_current_velocity()

    def publish_current_velocity(self):
        msg = Twist()
        msg.linear.x = float(self.current_linear)
        msg.angular.z = float(self.current_angular)
        self.publisher.publish(msg)

        if hasattr(self, 'last_displayed_vel'):
            if (abs(self.last_displayed_vel[0] - self.current_linear) > 0.15 or
                abs(self.last_displayed_vel[1] - self.current_angular) > 0.15):
                self.display_status()
                self.last_displayed_vel = (self.current_linear, self.current_angular)
        else:
            self.last_displayed_vel = (self.current_linear, self.current_angular)

    def display_status(self):
        direction = "🛑 Parado"
        if self.current_angular < -0.1:
            direction = "⬆️ Frente"
        elif self.current_angular > 0.1:
            direction = "⬇️ Trás"
        
        rotation = ""
        if self.current_linear < -0.1:
            rotation = "↺ Esquerda"
        elif self.current_linear > 0.1:
            rotation = "↻ Direita"

        status = f"{direction}"
        if rotation:
            status += f" + {rotation}"
        
        angular_pct = abs(self.current_angular / self.linear_speed * 100) if self.linear_speed > 0 else 0
        linear_pct = abs(self.current_linear / self.angular_speed * 100) if self.angular_speed > 0 else 0
        
        def progress_bar(pct, width=10):
            filled = int(pct / 10)
            return '█' * filled + '░' * (width - filled)
        
        print(f'\r{status:<25} │ Vel: {progress_bar(angular_pct)} {angular_pct:3.0f}% │ Rot: {progress_bar(linear_pct)} {linear_pct:3.0f}%', end='', flush=True)

    def emergency_stop(self):
        self.keys_pressed.clear()
        self.current_linear = 0.0
        self.current_angular = 0.0
        self.publish_current_velocity()
        print('\n\n🛑 PARADA DE EMERGÊNCIA!\n')

    def on_press(self, key):
        try:
            k = key.char.lower()
            if k in ['w', 'a', 's', 'd']:
                self.keys_pressed.add(k)
        except AttributeError:
            if key == keyboard.Key.space:
                self.emergency_stop()
            elif key == keyboard.Key.esc:
                print('\n\n👋 ESC pressionado. Saindo...\n')
                self.listener_running = False
                return False

    def on_release(self, key):
        try:
            k = key.char.lower()
            if k in ['w', 'a', 's', 'd']:
                self.keys_pressed.discard(k)
        except AttributeError:
            if key == keyboard.Key.esc:
                return False

def main(args=None):
    rclpy.init(args=args)
    node = TeleopKeyboard()
    
    listener = keyboard.Listener(
        on_press=node.on_press,
        on_release=node.on_release,
        suppress=True
    )
    listener.start()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.emergency_stop()
        listener.stop()
        node.destroy_node()
        rclpy.shutdown()
        print('\n✅ Controlador finalizado!\n')

if __name__ == '__main__':
    main()
