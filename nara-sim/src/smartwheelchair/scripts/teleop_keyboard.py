#!/usr/bin/env python3
import pygame
import sys
import random
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
 
pygame.init()
rclpy.init()
node = Node('nara_controller')
 
current_topic = '/noblenara/cmd_vel'
pub = node.create_publisher(Twist, current_topic, 10)
 
pygame.joystick.init()
joy = None
if pygame.joystick.get_count() > 0:
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Joystick detectado: {joy.get_name()}")
else:
    print("Nenhum joystick detectado. Use teclado (WASD).")
 
tela = pygame.display.set_mode((800, 600))
pygame.display.set_caption("NARA WHEELCHAIR - Teleoperador")
 
# Fontes
fonte_titulo = pygame.font.SysFont("monospace", 48, bold=True)
fonte_sub = pygame.font.SysFont("monospace", 16, bold=True)
fonte = pygame.font.SysFont("monospace", 20, bold=True)
fonte_desc = pygame.font.SysFont("monospace", 15, bold=True)
fonte_tecla = pygame.font.SysFont("monospace", 24, bold=True)
fonte_pequena = pygame.font.SysFont("monospace", 15, bold=True)
fonte_accel = pygame.font.SysFont("monospace", 11, bold=True)  # fonte menor p/ botão RAMPA
 
clock = pygame.time.Clock()
 
current_linear = 0.0
current_angular = 0.0
linear_speed = 1.5
angular_speed = 0.8
acceleration_rate = 0.02
deceleration_rate = 0.08
 
# ==================== TOGGLE DE ACELERAÇÃO/DESACELERAÇÃO ====================
# Default: DESLIGADO -> resposta linear/instantânea (sem rampa)
usar_aceleracao = False
 
# Linhas de fundo
linhas = []
for _ in range(22):
    linhas.append({
        'x': random.randint(0, 800),
        'y': random.randint(90, 510),
        'length': random.randint(18, 40),
        'speed': random.uniform(1.2, 2.8),
    })
 
modo = "TECLADO"
modo_velocidade = "Normal"
menu_modos_aberto = False
editando_topico = False
topico_input = current_topic
 
# Cor neon mais pura (menos verde)
AZUL_NARA = (0, 245, 255)
 
VELOCIDADES = {
    "Seguranca": {"linear": 1.0, "angular": 0.4, "accel": 0.01, "decel": 0.01,
                  "cor": AZUL_NARA, "cor_escura": (0, 60, 100), "label": "SEGURANÇA"},
    "Normal": {"linear": 1.5, "angular": 0.8, "accel": 0.02, "decel": 0.02,
               "cor": AZUL_NARA, "cor_escura": (0, 60, 100), "label": "NORMAL"},
    "Rapido": {"linear": 2.0, "angular": 1.2, "accel": 0.02, "decel": 0.02,
               "cor": AZUL_NARA, "cor_escura": (0, 60, 100), "label": "RÁPIDO"},
}
 
JOYSTICK_DEADZONE = 0.15
 
# Posição do botão de aceleração (canto superior esquerdo, agora menor para não
# invadir o título "NARA WHEELCHAIR")
ACCEL_BTN_X = 15
ACCEL_BTN_Y = 12
ACCEL_BTN_W = 110
ACCEL_BTN_H = 26
 
 
def desenhar_tecla(tela, letra, x, y, pressionada):
    cor = (0, 255, 255) if pressionada else (50, 50, 50)
    pygame.draw.rect(tela, cor, (x, y, 50, 50), border_radius=8)
    txt = fonte_tecla.render(letra, True, (0, 0, 0) if pressionada else (200, 200, 200))
    tela.blit(txt, (x + 15, y + 12))
 
 
def desenhar_botao_aceleracao(tela, ativo):
    cor = AZUL_NARA if ativo else (90, 90, 90)
    # fundo levemente preenchido quando ativo, para reforçar o estado "ligado"
    if ativo:
        pygame.draw.rect(tela, (0, 40, 45), (ACCEL_BTN_X, ACCEL_BTN_Y, ACCEL_BTN_W, ACCEL_BTN_H), border_radius=6)
    else:
        pygame.draw.rect(tela, (25, 25, 30), (ACCEL_BTN_X, ACCEL_BTN_Y, ACCEL_BTN_W, ACCEL_BTN_H), border_radius=6)
    pygame.draw.rect(tela, cor, (ACCEL_BTN_X, ACCEL_BTN_Y, ACCEL_BTN_W, ACCEL_BTN_H), border_radius=6, width=2)
    estado_txt = "ON" if ativo else "OFF"
    simbolo = "▶" if ativo else "○"
    txt = fonte_accel.render(f"{simbolo} RAMPA: {estado_txt}", True, cor)
    tela.blit(txt, (ACCEL_BTN_X + ACCEL_BTN_W // 2 - txt.get_width() // 2,
                     ACCEL_BTN_Y + ACCEL_BTN_H // 2 - txt.get_height() // 2))
 
 
while True:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            msg = Twist()
            pub.publish(msg)
            pygame.quit()
            rclpy.shutdown()
            sys.exit()
 
        if evento.type == pygame.MOUSEBUTTONDOWN:
            mx, my = evento.pos
 
            # Toggle do botão de aceleração/desaceleração
            if ACCEL_BTN_X <= mx <= ACCEL_BTN_X + ACCEL_BTN_W and ACCEL_BTN_Y <= my <= ACCEL_BTN_Y + ACCEL_BTN_H:
                usar_aceleracao = not usar_aceleracao
                if not usar_aceleracao:
                    # ao desligar, zera qualquer rampa acumulada para evitar "arrasto" residual
                    current_linear = 0.0
                    current_angular = 0.0
 
            if 645 <= mx <= 780 and 15 <= my <= 48:
                menu_modos_aberto = not menu_modos_aberto
 
            if menu_modos_aberto:
                for i, nome_modo in enumerate(["Seguranca", "Normal", "Rapido"]):
                    y_item = 60 + i * 32
                    if 645 <= mx <= 780 and y_item <= my <= y_item + 30:
                        modo_velocidade = nome_modo
                        menu_modos_aberto = False
                        config = VELOCIDADES[modo_velocidade]
                        linear_speed = config["linear"]
                        angular_speed = config["angular"]
                        acceleration_rate = config["accel"]
                        deceleration_rate = config["decel"]
 
            if 120 <= mx <= 520 and 535 <= my <= 577:
                editando_topico = True
            else:
                editando_topico = False
 
        if evento.type == pygame.KEYDOWN and editando_topico:
            if evento.key == pygame.K_RETURN:
                editando_topico = False
                if topico_input != current_topic and topico_input.startswith('/'):
                    current_topic = topico_input
                    pub = node.create_publisher(Twist, current_topic, 10)
                    print(f"Tópico alterado para: {current_topic}")
            elif evento.key == pygame.K_BACKSPACE:
                topico_input = topico_input[:-1]
            elif len(topico_input) < 50:
                topico_input += evento.unicode
 
    # ==================== INPUTS ====================
    teclas = pygame.key.get_pressed()
    teclado_ativo = any([teclas[pygame.K_w], teclas[pygame.K_s], teclas[pygame.K_a], teclas[pygame.K_d]])
    joystick_ativo = False
 
    eixo_linear_joy = eixo_angular_joy = 0.0
    if joy is not None:
        try:
            ax_lin = -joy.get_axis(1)
            ax_ang = -joy.get_axis(0)
            if abs(ax_lin) < JOYSTICK_DEADZONE: ax_lin = 0.0
            if abs(ax_ang) < JOYSTICK_DEADZONE * 1.15: ax_ang = 0.0
            if abs(ax_lin) > 0.01 or abs(ax_ang) > 0.01:
                joystick_ativo = True
            eixo_linear_joy = ax_lin
            eixo_angular_joy = ax_ang
        except:
            pass
 
    if teclado_ativo and not joystick_ativo:
        modo = "TECLADO"
    elif joystick_ativo and not teclado_ativo:
        modo = "JOYSTICK"
 
    eixo_linear = eixo_angular = 0.0
    if modo == "JOYSTICK":
        eixo_linear = eixo_linear_joy
        eixo_angular = eixo_angular_joy
    else:
        if teclas[pygame.K_w]: eixo_linear = 1.0
        if teclas[pygame.K_s]: eixo_linear = -1.0
        if teclas[pygame.K_a]: eixo_angular = 1.0
        if teclas[pygame.K_d]: eixo_angular = -1.0
 
    target_linear = eixo_linear * linear_speed
    target_angular = eixo_angular * angular_speed
 
    if teclas[pygame.K_SPACE]:
        current_linear = current_angular = 0.0
 
    # ==================== RAMPA (ACELERAÇÃO/DESACELERAÇÃO) ====================
    if usar_aceleracao:
        if not teclas[pygame.K_SPACE]:
            if target_linear > current_linear:
                current_linear = min(target_linear, current_linear + acceleration_rate)
            elif target_linear < current_linear:
                current_linear = max(target_linear, current_linear - deceleration_rate)
 
            if target_angular > current_angular:
                current_angular = min(target_angular, current_angular + acceleration_rate)
            elif target_angular < current_angular:
                current_angular = max(target_angular, current_angular - deceleration_rate)
    else:
        # Modo padrão: resposta instantânea, sem rampa
        if not teclas[pygame.K_SPACE]:
            current_linear = target_linear
            current_angular = target_angular
 
    linear = current_linear
    angular = current_angular
    if abs(linear) < 0.01: linear = 0.0
    if abs(angular) < 0.01: angular = 0.0
 
    # ==================== DESENHO ====================
    tela.fill((0, 0, 0))
 
    # Linhas de fundo
    intensidade = abs(linear) / linear_speed
    velocidade = 1.2 + 3.8 * intensidade
    for linha in linhas:
        linha['x'] += linha['speed'] * velocidade * (1 if linear >= 0 else -1)
        if linha['x'] > 850: linha['x'] = -50
        if linha['x'] < -50: linha['x'] = 850
        pygame.draw.line(tela, AZUL_NARA, (linha['x'], linha['y']), (linha['x'] + linha['length'], linha['y']), 2)
 
    # Títulos
    titulo = fonte_titulo.render("NARA WHEELCHAIR", True, AZUL_NARA)
    subtitulo = fonte_sub.render("CONTROLADOR DE VELOCIDADE - GAZEBO HARMONIC", True, AZUL_NARA)
    tela.blit(titulo, (400 - titulo.get_width()//2, 8))
    tela.blit(subtitulo, (400 - subtitulo.get_width()//2, 58))
 
    status = fonte.render(f"Linear: {linear:.2f}   Angular: {angular:.2f}", True, (255, 255, 255))
    tela.blit(status, (400 - status.get_width()//2, 105))
 
    # Barra de velocidade
    largura_barra = int(abs(linear) / linear_speed * 280)
    barra_x = 260
    pygame.draw.rect(tela, (30, 30, 30), (barra_x, 140, 280, 18), border_radius=6)
    pygame.draw.rect(tela, AZUL_NARA, (barra_x, 140, largura_barra, 18), border_radius=6)
    lbl_barra = fonte_desc.render("VELOCIDADE LINEAR", True, (100, 100, 100))
    tela.blit(lbl_barra, (400 - lbl_barra.get_width()//2, 162))
 
    # ==================== TECLADO ====================
    tx = 165
    teclas_vis = pygame.key.get_pressed()
    mostra_pressionado = (modo == "TECLADO")
    
    desenhar_tecla(tela, "W", tx + 30, 265, mostra_pressionado and teclas_vis[pygame.K_w])
    desenhar_tecla(tela, "A", tx - 30, 325, mostra_pressionado and teclas_vis[pygame.K_a])
    desenhar_tecla(tela, "S", tx + 30, 325, mostra_pressionado and teclas_vis[pygame.K_s])
    desenhar_tecla(tela, "D", tx + 90, 325, mostra_pressionado and teclas_vis[pygame.K_d])
 
    # TECLADO centralizado corretamente
    label_teclado = fonte_desc.render("TECLADO", True, (255, 255, 255))
    tela.blit(label_teclado, (tx + 48, 390))   # Ajustado para centralizar
 
    # ==================== JOYSTICK ====================
    jx, jy = 570, 325
    pygame.draw.circle(tela, (40, 40, 40), (jx, jy), 78)
    pygame.draw.circle(tela, (80, 80, 80), (jx, jy), 78, 3)
 
    if modo == "JOYSTICK":
        joy_x = jx - int((angular / angular_speed) * 55)
        joy_y = jy - int((linear / linear_speed) * 55)
    else:
        joy_x, joy_y = jx, jy
 
    pygame.draw.circle(tela, AZUL_NARA, (joy_x, joy_y), 24)
 
    label_joy = fonte_desc.render("JOYSTICK", True, (255, 255, 255))
    tela.blit(label_joy, (jx - label_joy.get_width()//2, jy + 95))
 
    # ==================== RODAPÉ CENTRALIZADO ====================
    y_base = 535
    largura_total = 290 + 195 + 15
    bloco_x = (800 - largura_total) // 2
 
    # Tópico
    pygame.draw.rect(tela, (25, 25, 30), (bloco_x, y_base, 290, 43), border_radius=10)
    pygame.draw.rect(tela, (0, 200, 255) if editando_topico else (80, 80, 90),
                     (bloco_x, y_base, 290, 43), border_radius=10, width=2)
    txt_topico = fonte_pequena.render(f"Tópico: {topico_input}", True, (220, 220, 220))
    tela.blit(txt_topico, (bloco_x + 10, y_base + 13))
 
    # Entrada
    cor_modo = AZUL_NARA if modo == "JOYSTICK" else (200, 200, 0)
    pygame.draw.rect(tela, (20, 20, 20), (bloco_x + 305, y_base, 195, 43), border_radius=10)
    pygame.draw.rect(tela, cor_modo, (bloco_x + 305, y_base, 195, 43), border_radius=10, width=2)
    txt_entrada = fonte_desc.render(f"ENTRADA: {modo}", True, cor_modo)
    tela.blit(txt_entrada, (bloco_x + 400 - txt_entrada.get_width()//2, y_base + 13))
 
    # Botão Modo (velocidade)
    config = VELOCIDADES[modo_velocidade]
    btn_x = 645
    pygame.draw.rect(tela, (45, 45, 50), (btn_x, 15, 135, 36), border_radius=8)
    pygame.draw.rect(tela, AZUL_NARA, (btn_x, 15, 135, 36), border_radius=8, width=3)
    txt_vel = fonte_desc.render(f"▶ {config['label']}", True, AZUL_NARA)
    tela.blit(txt_vel, (btn_x + 67 - txt_vel.get_width()//2, 23))
 
    if menu_modos_aberto:
        pygame.draw.rect(tela, (15, 15, 20), (btn_x, 56, 135, 115), border_radius=8)
        for i, nome_modo in enumerate(["Seguranca", "Normal", "Rapido"]):
            y_item = 63 + i * 32
            cfg = VELOCIDADES[nome_modo]
            selecionado = nome_modo == modo_velocidade
            cor_item = cfg["cor"] if selecionado else (160, 160, 160)
            txt_item = fonte_desc.render(("▶ " if selecionado else " ") + cfg["label"], True, cor_item)
            tela.blit(txt_item, (btn_x + 67 - txt_item.get_width()//2, y_item + 6))
 
    # Botão de Aceleração/Desaceleração (canto superior esquerdo)
    desenhar_botao_aceleracao(tela, usar_aceleracao)
 
    # Publicar
    msg = Twist()
    msg.linear.x = float(linear)
    msg.angular.z = float(angular)
    pub.publish(msg)
 
    rclpy.spin_once(node, timeout_sec=0)
    pygame.display.flip()
    clock.tick(60)