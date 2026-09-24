#!/usr/bin/env python3
"""
NOBLE CONFIG - Dashboard de Simulação
Cada clique aplica a configuração NO CÓDIGO da NARA automaticamente
(com backup em .backup_configurador/ para restaurar).
"""

import os
import re
import shutil
import sys
import time
import pygame
import psutil
from pathlib import Path

# ============================================================
# NÚCLEO - Aplicação de configurações no código da NARA
# (backup + reaplicação idempotente a partir do original)
# ============================================================
PACOTE_SRC = Path(__file__).resolve().parent.parent  # .../src/smartwheelchair
URDF_DIR = PACOTE_SRC / "urdf"
LAUNCH_DIR = PACOTE_SRC / "launch"
CONFIG_DIR = PACOTE_SRC / "config"

BACKUP_DIR = PACOTE_SRC / ".backup_configurador"
ARQUIVOS_MODIFICAVEIS = [
    "urdf/narawheelchair.gazebo",
    "urdf/narawheelchair.xacro",
    "launch/noblenara.launpy",
    "config/nav2_params.yaml",
]

MAP_ZED_RES = {
    "640x480": (640, 480),
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
}
MAP_PARTICULAS = {  # max_particles -> (min_particles, max_particles)
    200: (100, 200),
    800: (200, 800),
    2000: (500, 2000),
}


def _caminho_backup(arquivo: str) -> Path:
    return BACKUP_DIR / arquivo.replace("/", "__")


def fazer_backup_originais():
    """Salva cópia dos arquivos originais da NARA antes de qualquer modificação"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups_criados = []
    for arquivo in ARQUIVOS_MODIFICAVEIS:
        origem = PACOTE_SRC / arquivo
        destino = _caminho_backup(arquivo)
        if origem.exists() and not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)
            backups_criados.append(arquivo)
    return backups_criados


def restaurar_originais():
    """Restaura os arquivos originais da NARA a partir do backup"""
    restaurados = []
    for arquivo in ARQUIVOS_MODIFICAVEIS:
        destino = PACOTE_SRC / arquivo
        origem_backup = _caminho_backup(arquivo)
        if origem_backup.exists():
            shutil.copy2(origem_backup, destino)
            restaurados.append(arquivo)
    return restaurados


def _ler_base(arquivo: str) -> str:
    """Lê a versão ORIGINAL do arquivo (backup) para reaplicação idempotente"""
    backup = _caminho_backup(arquivo)
    fonte = backup if backup.exists() else PACOTE_SRC / arquivo
    return fonte.read_text()


def _remover_sensor_por_nome(gazebo_content: str, nome_sensor: str) -> str:
    """Remove blocos <gazebo>...</gazebo> que contenham <sensor name="nome">"""
    padrao_bloco = re.compile(r'<gazebo[^>]*>.*?</gazebo>', re.DOTALL)
    return padrao_bloco.sub(
        lambda m: '' if nome_sensor in m.group(0) else m.group(0),
        gazebo_content)


def _editar_bloco_gazebo(gazebo_content: str, marcador: str, transform) -> str:
    """Aplica `transform` apenas nos blocos <gazebo>...</gazebo> que contenham `marcador`"""
    padrao_bloco = re.compile(r'<gazebo[^>]*>.*?</gazebo>', re.DOTALL)

    def _repl(m):
        bloco = m.group(0)
        if marcador in bloco:
            return transform(bloco)
        return bloco

    return padrao_bloco.sub(_repl, gazebo_content)


def _ajustar_lidar(gazebo_content: str, samples=None, rate=None, max_range=None) -> str:
    """Ajusta parâmetros do sensor LIDAR (head_hokuyo_sensor)"""
    def _transform(bloco):
        if samples is not None:
            bloco = re.sub(r'<samples>\d+</samples>', f'<samples>{samples}</samples>', bloco)
        if rate is not None:
            bloco = re.sub(r'<update_rate>[\d.]+</update_rate>', f'<update_rate>{rate}</update_rate>', bloco)
        if max_range is not None:
            bloco = re.sub(r'<range>\s*<min>[\d.]+</min>\s*<max>[\d.]+</max>',
                           lambda m: f'<range>\n          <min>0.10</min>\n          <max>{max_range}</max>',
                           bloco, count=1)
        return bloco

    return _editar_bloco_gazebo(gazebo_content, 'head_hokuyo_sensor', _transform)


def _ajustar_zed(gazebo_content: str, resolucao: tuple = None, rate=None) -> str:
    """Ajusta resolução/rate da câmera ZED2i (camera_link_zed2i)"""
    def _transform(bloco):
        if resolucao is not None:
            w, h = resolucao
            bloco = re.sub(r'<width>\d+</width>', f'<width>{w}</width>', bloco)
            bloco = re.sub(r'<height>\d+</height>', f'<height>{h}</height>', bloco)
        if rate is not None:
            bloco = re.sub(r'<update_rate>[\d.]+</update_rate>', f'<update_rate>{rate}</update_rate>', bloco)
        return bloco

    return _editar_bloco_gazebo(gazebo_content, 'camera_link_zed2i', _transform)


def _ajustar_camera_user(gazebo_content: str, rate=None) -> str:
    """Ajusta o framerate da câmera de interface (camera_user)"""
    def _transform(bloco):
        if rate is not None:
            bloco = re.sub(r'<update_rate>[\d.]+</update_rate>', f'<update_rate>{rate}</update_rate>', bloco)
        return bloco

    return _editar_bloco_gazebo(gazebo_content, 'name="camera_user"', _transform)


def _ajustar_nav2(nav2_content: str, amcl_particles=None, mppi_batch=None,
                  controller_frequency=None) -> str:
    """Ajusta parâmetros do nav2_params.yaml"""
    nova = nav2_content
    if amcl_particles is not None:
        minima, maxima = MAP_PARTICULAS.get(int(amcl_particles), (500, 2000))
        nova = re.sub(r'min_particles: \d+', f'min_particles: {minima}', nova)
        nova = re.sub(r'max_particles: \d+', f'max_particles: {maxima}', nova)
    if mppi_batch is not None:
        nova = re.sub(r'batch_size: \d+', f'batch_size: {int(mppi_batch)}', nova)
    if controller_frequency is not None:
        nova = re.sub(r'controller_frequency: [\d.]+',
                      f'controller_frequency: {float(controller_frequency)}', nova)
    return nova


def aplicar_sensor_nivel(gazebo: str, nivel: str) -> str:
    """Aplica configuração de qualidade dos sensores no arquivo gazebo (low/medium/high)"""
    conteudo = gazebo
    if nivel == "low":
        conteudo = _remover_sensor_por_nome(conteudo, 'name="camera_link_zed2i"')
        conteudo = _remover_sensor_por_nome(conteudo, '<sensor type="camera" name="camera_user"')
        conteudo = _ajustar_lidar(conteudo, samples=360, rate=10, max_range=10.0)
    elif nivel == "high":
        conteudo = _ajustar_zed(conteudo, resolucao=(1280, 720), rate=30)
    return conteudo


def aplicar_config(config: dict):
    """
    Aplica as configurações selecionadas nos arquivos da NARA.
    Reaplica SEMPRE a partir do backup original (idempotente).
    """
    fazer_backup_originais()

    # ============ GAZEBO (sensores) ============
    base_gazebo = _ler_base("urdf/narawheelchair.gazebo")
    conteudo = aplicar_sensor_nivel(base_gazebo, config.get("sensor_quality", "medium"))

    if "lidar_samples" in config:
        conteudo = _ajustar_lidar(conteudo, samples=int(config["lidar_samples"]))
    if "lidar_rate" in config:
        conteudo = _ajustar_lidar(conteudo, rate=float(config["lidar_rate"]))
    if "zed_enabled" in config and not config["zed_enabled"]:
        conteudo = _remover_sensor_por_nome(conteudo, 'name="camera_link_zed2i"')
    if config.get("zed_res") in MAP_ZED_RES:
        conteudo = _ajustar_zed(conteudo, resolucao=MAP_ZED_RES[config["zed_res"]])
    if "camera_user" in config and not config["camera_user"]:
        conteudo = _remover_sensor_por_nome(conteudo, '<sensor type="camera" name="camera_user"')
    if config.get("camera_user") and "camera_user_rate" in config:
        conteudo = _ajustar_camera_user(conteudo, rate=float(config["camera_user_rate"]))
    if "lidar_range" in config:
        conteudo = _ajustar_lidar(conteudo, max_range=float(config["lidar_range"]))

    with open(URDF_DIR / "narawheelchair.gazebo", "w") as f:
        f.write(conteudo)

    # ============ NAV2 (params) ============
    base_nav2 = _ler_base("config/nav2_params.yaml")
    nav2 = _ajustar_nav2(base_nav2,
                         amcl_particles=config.get("amcl_particles"),
                         mppi_batch=config.get("mppi_batch"),
                         controller_frequency=config.get("controller_frequency"))
    with open(CONFIG_DIR / "nav2_params.yaml", "w") as f:
        f.write(nav2)

    return _caminho_backup


def ler_config_atual() -> dict:
    """Lê os valores ATUAIS reais no código da NARA para sincronizar a interface"""
    info = {}

    gazebo = (URDF_DIR / "narawheelchair.gazebo").read_text()
    bloco_lidar = re.search(r'<sensor[^>]*head_hokuyo_sensor.*?</sensor>', gazebo, re.DOTALL)
    if bloco_lidar:
        m = re.search(r'<samples>(\d+)</samples>', bloco_lidar.group(0))
        info["lidar_samples"] = int(m.group(1)) if m else 720
        m = re.search(r'<update_rate>([\d.]+)</update_rate>', bloco_lidar.group(0))
        info["lidar_rate"] = float(m.group(1)) if m else 20.0
        m = re.search(r'<range>.*?<max>([\d.]+)</max>', bloco_lidar.group(0), re.DOTALL)
        info["lidar_range"] = float(m.group(1)) if m else 30.0
    else:
        info["lidar_samples"], info["lidar_rate"] = 720, 20.0
        info["lidar_range"] = 30.0

    bloco_cam = re.search(r'<sensor[^>]*name="camera_user".*?</sensor>', gazebo, re.DOTALL)
    if bloco_cam:
        m = re.search(r'<update_rate>([\d.]+)</update_rate>', bloco_cam.group(0))
        info["camera_user_rate"] = float(m.group(1)) if m else 30.0
    else:
        info["camera_user_rate"] = 30.0

    bloco_zed = re.search(r'<sensor[^>]*name="camera_link_zed2i".*?</sensor>', gazebo, re.DOTALL)
    if bloco_zed:
        mw = re.search(r'<width>(\d+)</width>', bloco_zed.group(0))
        mh = re.search(r'<height>(\d+)</height>', bloco_zed.group(0))
        w = int(mw.group(1)) if mw else 640
        h = int(mh.group(1)) if mh else 480
        info["zed_res"] = f"{w}x{h}"
        info["zed_width"] = w
    else:
        info["zed_res"] = None
        info["zed_width"] = 0

    info["camera_user"] = 'name="camera_user"' in gazebo

    nav2 = (CONFIG_DIR / "nav2_params.yaml").read_text()
    m = re.search(r'min_particles: (\d+)', nav2)
    info["amcl_min"] = int(m.group(1)) if m else 500
    m = re.search(r'max_particles: (\d+)', nav2)
    info["amcl_max"] = int(m.group(1)) if m else 2000
    m = re.search(r'batch_size: (\d+)', nav2)
    info["mppi_batch"] = int(m.group(1)) if m else 800

    return info


def gerar_script_inicializacao(config: dict, caminho: Path):
    """Gera script bash com os comandos de inicialização"""
    cmd_robo = ["ros2", "launch", "smartwheelchair", "noblenara.launpy", "robot_codename:=alfa"]
    mundo_map = {
        "light": "museum_light.world",
        "default": "museum_default.world",
        "finder": "museum_finder.world",
    }
    world_file = mundo_map.get(config.get("world", "default"), "museum_default.world")

    with open(caminho, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# NOBLE NARA - Simulação configurada pelo dashboard\n")
        f.write(f"# URDF: {config.get('urdf_quality','medium')} | Sensores: {config.get('sensor_quality','medium')} | SLAM: {config.get('slam_enabled',True)} | Nav2: {config.get('nav2_enabled',True)} | Mundo: {config.get('world','default')}\n\n")
        f.write("echo '>> Iniciando Gazebo...'\n")
        f.write(f"ros2 launch smartwheelchair worldmuseum.launpy world_file:={world_file} &\n")
        f.write("sleep 5\n")
        f.write("echo '>> Iniciando robô NARA...'\n")
        f.write(" ".join(cmd_robo) + " &\n")
        if config.get("slam_enabled", True):
            f.write("sleep 3\n")
            f.write("echo '>> Iniciando SLAM...'\n")
            f.write("ros2 launch smartwheelchair slam.launpy robot_codename:=alfa &\n")
        if config.get("nav2_enabled", True):
            f.write("sleep 3\n")
            f.write("echo '>> Iniciando Nav2...'\n")
            f.write("ros2 launch smartwheelchair nav2_launpy robot_codename:=alfa &\n")
        f.write("\necho '>> Simulação iniciada! CTRL+C para encerrar.\n")
        f.write("wait\n")

    os.chmod(caminho, 0o755)
    return caminho

pygame.init()

# ============================================================
# TEMA - Mude a COR do dashboard inteiro aqui
# ============================================================
# Troque a linha ativada no dicionário abaixo (descomente 1 por vez).
# ACENTO       = cor principal (logo, botões, títulos)
# ACENTO_FONTE = cor do texto claro do acento (badges, rótulos)
# ACENTO_SUAVE = tom escuro sutil (linha divisória do cabeçalho)
# FIO          = destaque fino (fio do topo dos cards, bordas)
TEMA = "ciano"   # <-- escolha: "ciano" | "vermelho" | "cinza"

_TEMAS = {
    # >>> CIANO (padrão original da NARA) <<<
    "ciano": {
        "ACENTO":       (0, 190, 210),
        "ACENTO_FONTE": (88, 198, 212),
        "ACENTO_SUAVE": (13, 38, 45),
        "FIO":          (0, 132, 146),
    },
    # >>> VERMELHO NEON <<<
    "vermelho": {
        "ACENTO":       (255, 36, 58),
        "ACENTO_FONTE": (255, 36, 58),
        "ACENTO_SUAVE": (40, 12, 16),
        "FIO":          (255, 36, 58),
    },
    # >>> CINZA (neutro) <<<
    "cinza": {
        "ACENTO":       (160, 175, 190),
        "ACENTO_FONTE": (200, 210, 220),
        "ACENTO_SUAVE": (30, 36, 42),
        "FIO":          (140, 155, 170),
    },
}

ACENTO = _TEMAS[TEMA]["ACENTO"]
ACENTO_FONTE = _TEMAS[TEMA]["ACENTO_FONTE"]
ACENTO_SUAVE = _TEMAS[TEMA]["ACENTO_SUAVE"]
FIO = _TEMAS[TEMA]["FIO"]

# ============================================================
# PALETA - Dark profundo
# ============================================================
PRETO = (2, 3, 4)
CARD = (7, 10, 12)
CARD_ALT = (10, 13, 16)
LINHA = (22, 29, 34)
BRANCO = (206, 216, 225)
SUAVE = (120, 134, 145)
SUAVE2 = (88, 102, 113)
VERDE = (60, 210, 130)
AMBAR = (255, 170, 60)

# ============================================================
# JANELA
# ============================================================
LARGURA, ALTURA = 980, 900
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("NOBLE CONFIG - Dashboard de Simulação")

# Fontes profissionais (sem serifa)
def _fonte(tam, bold=False):
    nome = ['ubuntusemibold', 'ubuntubold', 'ubuntu'] if bold else ['ubuntu', 'notosans', 'dejavusans']
    return pygame.font.SysFont(nome, tam, bold=bold)

f_logo = _fonte(34, bold=True)
f_sub = _fonte(12)
f_tit = _fonte(14, bold=True)
f_opc = _fonte(13, bold=True)
f_btn = _fonte(14, bold=True)
f_rod = _fonte(12)
f_mini = _fonte(11)
f_status = _fonte(15, bold=True)

clock = pygame.time.Clock()

# ============================================================
# CPU SUAVIZADO (corrige oscilação)
# ============================================================
_cpu_fila = [0.0]
_ultima_tick = time.time()


def ler_cpu_suave():
    """CPU estável: amostra média a cada 0.5s + média móvel de 6 leituras"""
    global _ultima_cpu, _ultima_tick
    v = psutil.cpu_percent(interval=None)
    if v is not None:
        _cpu_fila.append(v)
        if len(_cpu_fila) > 6:
            _cpu_fila.pop(0)
    return sum(_cpu_fila) / len(_cpu_fila)


def ler_ram():
    v = psutil.virtual_memory()
    return v.used / 1e9, v.total / 1e9, v.percent


# ============================================================
# EFEITO NEON (texto com brilho + contorno de luz)
# ============================================================

def _texto_grosso(texto, fonte, centro, cor=ACENTO):
    """Texto único tom: traço grosso (sem brilho branco)"""
    base = fonte.render(texto, True, cor)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        tela.blit(base, base.get_rect(center=(centro[0] + dx, centro[1] + dy)))
    tela.blit(base, base.get_rect(center=centro))


# ============================================================
# COMPONENTE - Card com opções exclusivas + descrição
# ============================================================

class Card:
    """Card com botões de seleção EXCLUSIVA (clica 1, apaga o resto)"""

    def __init__(self, titulo, categoria, opcoes, descricao, x, y, w, h):
        self.titulo = titulo
        self.categoria = categoria
        self.opcoes = opcoes          # [(texto, valor), ...]
        self.descricao = descricao
        self.x, self.y, self.w, self.h = x, y, w, h
        self.ativo = 0

        pad, gap = 16, 10
        n = len(opcoes)
        bw = (w - 2 * pad - gap * (n - 1)) // n
        self.rects = [
            pygame.Rect(x + pad + i * (bw + gap), y + 46, bw, h - 56)
            for i in range(n)
        ]

    def desenhar(self, sup):
        # Sombra sutil de profundidade
        pygame.draw.rect(sup, (3, 4, 6), (self.x + 3, self.y + 4, self.w, self.h), border_radius=14)
        pygame.draw.rect(sup, CARD, (self.x, self.y, self.w, self.h), border_radius=14)
        pygame.draw.rect(sup, LINHA, (self.x, self.y, self.w, self.h), border_radius=14, width=1)

        # Fio neon no topo do card
        s_fio = pygame.Surface((self.w, 1), pygame.SRCALPHA)
        pygame.draw.line(s_fio, (FIO[0], FIO[1], FIO[2], 150), (18, -4), (self.w - 18, 9), width=2)
        sup.blit(s_fio, (self.x, self.y + 2))

        # Título com marcador
        pygame.draw.circle(sup, ACENTO, (self.x + 22, self.y + 20), 4)
        txt = f_tit.render(self.titulo, True, ACENTO)
        sup.blit(txt, (self.x + 36, self.y + 12))

        # Descrição
        d = f_mini.render(self.descricao, True, SUAVE2)
        sup.blit(d, (self.x + 36, self.y + 31))

        # Botões
        for i, (texto, _v) in enumerate(self.opcoes):
            rect = self.rects[i]
            if i == self.ativo:
                pygame.draw.rect(sup, ACENTO, rect, border_radius=9)
                pygame.draw.rect(sup, FIO, rect, border_radius=9, width=2)
                cor = PRETO
            else:
                pygame.draw.rect(sup, CARD_ALT, rect, border_radius=9)
                pygame.draw.rect(sup, LINHA, rect, border_radius=9, width=1)
                cor = BRANCO
            t = f_opc.render(texto, True, cor)
            sup.blit(t, t.get_rect(center=rect.center))

    def clicar(self, pos):
        for i, rect in enumerate(self.rects):
            if rect.collidepoint(pos):
                if i != self.ativo:
                    self.ativo = i
                    return True
        return False

    def valor(self):
        return self.opcoes[self.ativo][1]

    def definir(self, valor):
        for i, (_t, v) in enumerate(self.opcoes):
            if v == valor:
                self.ativo = i
                return True
        return False


def _quebrar_linhas(texto, fonte, larg_max):
    """Quebra o texto em linhas para caber na largura"""
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = atual + (" " if atual else "") + palavra
        if fonte.size(teste)[0] > larg_max:
            if atual:
                linhas.append(atual)
            atual = palavra
        else:
            atual = teste
    if atual:
        linhas.append(atual)
    return linhas


class InfoCard:
    """Card informativo (sem opções) com texto guia organizado"""

    def __init__(self, titulo, descricao, linhas, x, y, w, h):
        self.titulo = titulo
        self.descricao = descricao
        self.linhas = linhas          # lista de tuplas (simbolo, texto)
        self.x, self.y, self.w, self.h = x, y, w, h

    def desenhar(self, sup):
        pygame.draw.rect(sup, (3, 4, 6), (self.x + 3, self.y + 4, self.w, self.h), border_radius=14)
        pygame.draw.rect(sup, CARD, (self.x, self.y, self.w, self.h), border_radius=14)
        pygame.draw.rect(sup, LINHA, (self.x, self.y, self.w, self.h), border_radius=14, width=1)

        s_fio = pygame.Surface((self.w, 1), pygame.SRCALPHA)
        pygame.draw.line(s_fio, (FIO[0], FIO[1], FIO[2], 150), (18, -4), (self.w - 18, 9), width=2)
        sup.blit(s_fio, (self.x, self.y + 2))

        # Cabeçalho "O QUE MUDA" + subtítulo curto
        pygame.draw.circle(sup, ACENTO, (self.x + 22, self.y + 20), 4)
        t = f_tit.render("O QUE MUDA", True, ACENTO)
        sup.blit(t, (self.x + 36, self.y + 14))
        d = f_mini.render(self.descricao, True, SUAVE)
        sup.blit(d, (self.x + 36, self.y + 32))
        pygame.draw.line(sup, LINHA, (self.x + 24, self.y + 48), (self.x + self.w - 24, self.y + 48), width=1)

        # Níveis organizados (nome em acento numa coluna + explicação alinhada)
        col_nome = max(f_rod.size(sim)[0] for sim, _ in self.linhas) + 16
        texto_x = self.x + 24 + col_nome
        larg_texto = self.w - 24 - col_nome - 8
        y = self.y + 62
        esp = 24
        for simbolo, texto in self.linhas:
            t = f_rod.render(simbolo, True, ACENTO)
            sup.blit(t, (self.x + 24, y))
            linhas_queb = _quebrar_linhas(texto, f_rod, larg_texto)
            for i, linha in enumerate(linhas_queb):
                t = f_rod.render(linha, True, BRANCO)
                sup.blit(t, (texto_x, y + i * 11))
            y += esp + (len(linhas_queb) - 1) * 11


# ============================================================
# LAYOUT - Colunas
# ============================================================
COL_X = [20, 345, 670]
CW, CH = 290, 150
LINHA_Y = [148, 320, 492]

def novo_card(linha, col, titulo, categoria, opcoes, descricao):
    return Card(titulo, categoria, opcoes, descricao, COL_X[col], LINHA_Y[linha], CW, CH)

# --- Cards do Modo Iniciante ---
cards_ini = [
    novo_card(0, 0, "URDF", "urdf", [("LEVE", "low"), ("MÉDIO", "medium"), ("PESADO", "high")],
              "Qualidade dos modelos 3D e meshes"),
    novo_card(0, 1, "SENSORES", "sensores", [("LEVE", "low"), ("MÉDIO", "medium"), ("PESADO", "high")],
              "Câmeras, LIDAR e resolução"),
    novo_card(0, 2, "MUNDO", "mundo", [("LEVE", "light"), ("PADRÃO", "default"), ("COMPLETO", "finder")],
              "Carga do cenário, sombras e agentes"),
]

# --- Cartões informativos do Modo Iniciante (o que muda em cada nível) ---
info_cards_ini = [
    InfoCard("URDF",
             "nos modelos 3D (meshes)",
             [("LEVE", "formas simples e leves"),
              ("MÉDIO", "malhas com visual equilibrado"),
              ("PESADO", "qualidade visual máxima")],
             COL_X[0], LINHA_Y[1], CW, CH),
    InfoCard("SENSORES",
             "em câmeras e no LIDAR",
             [("LEVE", "menos câmeras, LIDAR 360"),
              ("MÉDIO", "equilíbrio câmeras/resolução"),
              ("PESADO", "todas câmeras, ZED 1280")],
             COL_X[1], LINHA_Y[1], CW, CH),
    InfoCard("MUNDO",
             "na carga do cenário",
             [("LEVE", "museum_light, mais leve"),
              ("PADRÃO", "museum_default, estável"),
              ("COMPLETO", "museum_finder, completo")],
             COL_X[2], LINHA_Y[1], CW, CH),
]

# --- Cards do Modo Desenvolvedor (granulares) ---
cards_dev = [
    novo_card(0, 0, "LIDAR SAMPLES", "lidar_samples", [("360", 360), ("720", 720)],
              "Pontos por varredura"),
    novo_card(0, 1, "LIDAR RATE", "lidar_rate", [("10 Hz", 10), ("20 Hz", 20)],
              "Varreduras por segundo"),
    novo_card(0, 2, "ZED2i", "zed_res", [("640x480", "640x480"), ("1280x720", "1280x720"), ("OFF", None)],
              "Câmera frontal RGB-D"),
    novo_card(1, 0, "CAM USUÁRIO", "camera_user", [("ON", True), ("OFF", False)],
              "Câmera de interface do operador"),
    novo_card(1, 1, "CAM USUÁRIO RATE", "camera_user_rate", [("10 Hz", 10), ("20 Hz", 20), ("30 Hz", 30)],
              "Quadros por segundo da câmera"),
    novo_card(1, 2, "AMCL PARTÍCULAS", "amcl_particles", [("200", 200), ("800", 800), ("2000", 2000)],
              "Hipóteses de localização no mapa"),
    novo_card(2, 0, "MUNDO", "mundo", [("LEVE", "light"), ("PADRÃO", "default"), ("COMPLETO", "finder")],
              "Carga do cenário, sombras e agentes"),
    novo_card(2, 1, "MPPI BATCH", "mppi_batch", [("200", 200), ("400", 400), ("800", 800)],
              "Simulações de trajetória por ciclo"),
    novo_card(2, 2, "LIDAR RANGE", "lidar_range", [("10 m", 10), ("30 m", 30), ("50 m", 50)],
              "Alcance máximo do LIDAR"),
]

# --- Estado ---
modo = "iniciante"
msg = "PRONTO - selecione uma opção"
msg_ts = time.strftime("%H:%M:%S")

# ============================================================
# SINCRONIZAÇÃO COM O CÓDIGO REAL DA NARA
# ============================================================

def _mundo_atual():
    cards = cards_dev if modo == "desenvolvedor" else cards_ini
    for c in cards:
        if c.categoria == "mundo":
            return c.valor()
    return "default"


def sincronizar_do_codigo():
    """Alinha botões com os valores realmente aplicados no código da NARA"""
    atual = ler_config_atual()

    for c in cards_dev:
        if c.categoria == "lidar_samples":
            c.definir(atual["lidar_samples"])
        elif c.categoria == "lidar_rate":
            c.definir(atual["lidar_rate"])
        elif c.categoria == "zed_res":
            c.definir(atual["zed_res"] if atual["zed_res"] else None)
        elif c.categoria == "camera_user":
            c.definir(atual["camera_user"])
        elif c.categoria == "camera_user_rate":
            c.definir(int(round(atual["camera_user_rate"])))
        elif c.categoria == "amcl_particles":
            c.definir(atual["amcl_max"])
        elif c.categoria == "mppi_batch":
            c.definir(atual["mppi_batch"])
        elif c.categoria == "lidar_range":
            c.definir(int(round(atual["lidar_range"])))

    # Nível de sensores derivado do código
    if atual["zed_res"] is None or atual["lidar_samples"] == 360:
        nivel_sensor = "low"
    elif atual["zed_width"] == 1280:
        nivel_sensor = "high"
    else:
        nivel_sensor = "medium"
    for c in cards_ini:
        if c.categoria == "sensores":
            c.definir(nivel_sensor)


def coletar_config() -> dict:
    """Monta dict de configuração a partir dos botões ativos"""
    if modo == "iniciante":
        return {
            "urdf_quality": cards_ini[0].valor(),
            "sensor_quality": cards_ini[1].valor(),
            "world": cards_ini[2].valor(),
            "slam_enabled": True,
            "nav2_enabled": True,
        }

    cfg = {}
    for c in cards_dev:
        v = c.valor()
        if c.categoria == "zed_res":
            cfg["zed_enabled"] = v is not None
            if v is not None:
                cfg["zed_res"] = v
        else:
            cfg[c.categoria] = v
    return cfg


def aplicar_atual():
    """Aplica a configuração atual NO CÓDIGO real da NARA"""
    global msg, msg_ts
    cfg = coletar_config()
    aplicar_config(cfg)

    script = Path(__file__).resolve().parent / "iniciar_simulacao.sh"
    gerar_script_inicializacao(cfg, script)

    resumo = " / ".join(f"{k.upper()}: {v}" for k, v in cfg.items())
    msg = "[APLICADO] " + resumo
    msg_ts = time.strftime("%H:%M:%S")
    return cfg


def restaurar():
    """Restaura o código original e reseta os botões"""
    global msg, msg_ts
    restaurar_originais()
    restaurar_ui_padrao()
    msg = "[RESTAURADO] código original da NARA restaurado"
    msg_ts = time.strftime("%H:%M:%S")


def restaurar_ui_padrao():
    for c in cards_ini:
        if c.categoria in ("urdf", "sensores"):
            c.definir("medium")
        elif c.categoria == "mundo":
            c.definir("default")
        else:
            c.definir(True)
    for c in cards_dev:
        if c.categoria == "zed_res":
            c.definir("640x480")
        elif c.categoria == "amcl_particles":
            c.definir(2000)
        elif c.categoria == "mppi_batch":
            c.definir(800)
        elif c.categoria == "mundo":
            c.definir("default")
        elif c.categoria in ("slam", "nav2", "camera_user"):
            c.definir(True)
        elif c.categoria == "lidar_samples":
            c.definir(720)
        elif c.categoria == "lidar_rate":
            c.definir(20)


# ============================================================
# DADOS PARA O PAINEL DE RESUMO
# ============================================================

def dados_resumo() -> list:
    """Lista de (rotulo, valor) refletindo o código real aplicado"""
    a = ler_config_atual()
    mundo = {"light": "museum_light", "default": "museum_default", "finder": "museum_finder"}[_mundo_atual()]
    cam_user = f"ativa @ {a['camera_user_rate']:.0f} Hz" if a["camera_user"] else "desativada"

    linhas = [
        ("LIDAR", f"{a['lidar_samples']} pontos / {a['lidar_rate']:.0f} Hz   ·   RANGE {a['lidar_range']:.0f} m"),
        ("CÂMERA ZED2i", f"{a['zed_res']} @ RGB-D" if a["zed_res"] else "desativada"),
        ("CÂMERA USUÁRIO", cam_user),
        ("AMCL", f"{a['amcl_min']}–{a['amcl_max']} partículas"),
        ("MPPI BATCH", f"{a['mppi_batch']} simulações/ciclo"),
        ("MUNDO", f"{mundo} .world"),
        ("SLAM / NAV2", "sempre ativos (fixos)"),
        ("SEGURANÇA", "Collision Monitor ON   ·   Planner SmacPlannerHybrid fixo"),
    ]
    return linhas


def _valor_card(categoria):
    cards = cards_dev if modo == "desenvolvedor" else cards_ini
    for c in cards:
        if c.categoria == categoria:
            return c.valor()
    return True


# ============================================================
# DESENHO
# ============================================================

def desenhar_cabecalho():
    _texto_grosso("NOBLECONFIG", f_logo, (LARGURA // 2, 34))
    pygame.draw.line(tela, ACENTO_SUAVE, (0, 76), (LARGURA, 76), width=2)

    # Badge de versão com indicador (à esquerda)
    b = pygame.Rect(18, 12, 150, 28)
    pygame.draw.rect(tela, CARD, b, border_radius=14)
    pygame.draw.rect(tela, LINHA, b, border_radius=14, width=1)
    pygame.draw.circle(tela, ACENTO, (b.x + 18, b.centery), 4)
    t = f_mini.render("NOBLE CONFIG", True, ACENTO)
    tela.blit(t, t.get_rect(center=(b.x + 94, b.centery)))

    # Status conectado (à direita)
    s = pygame.Rect(LARGURA - 138, 14, 120, 26)
    pygame.draw.rect(tela, CARD, s, border_radius=13)
    pygame.draw.rect(tela, LINHA, s, border_radius=13, width=1)
    pygame.draw.circle(tela, VERDE, (s.x + 16, s.centery), 4)
    t = f_mini.render("CÓDIGO NARA", True, SUAVE)
    tela.blit(t, t.get_rect(center=(s.x + 78, s.centery)))

    t = f_sub.render("Configurador de desempenho - aplica no código em tempo real", True, SUAVE2)
    tela.blit(t, t.get_rect(center=(LARGURA // 2, 62)))


def desenhar_toggle():
    larg = 340
    x0 = LARGURA // 2 - larg // 2
    y = 92
    # Container pill
    pygame.draw.rect(tela, CARD_ALT, (x0 - 4, y - 4, larg + 8, 42), border_radius=12)
    pygame.draw.rect(tela, LINHA, (x0 - 4, y - 4, larg + 8, 42), border_radius=12, width=1)
    for i, nome in enumerate(["INICIANTE", "DESENVOLVEDOR"]):
        ativo = (modo == "desenvolvedor" and i == 1) or (modo == "iniciante" and i == 0)
        rect = pygame.Rect(x0 + i * (larg // 2), y, larg // 2, 34)
        if ativo:
            pygame.draw.rect(tela, ACENTO, rect, border_radius=9)
            pygame.draw.rect(tela, FIO, rect, border_radius=9, width=1)
            cor = PRETO
        else:
            cor = BRANCO
        t = f_opc.render(nome, True, cor)
        tela.blit(t, t.get_rect(center=rect.center))


def desenhar_cards():
    cards = cards_dev if modo == "desenvolvedor" else cards_ini
    for c in cards:
        c.desenhar(tela)
    if modo == "iniciante":
        for ic in info_cards_ini:
            ic.desenhar(tela)


def _fim_cards():
    mont = cards_dev if modo == "desenvolvedor" else cards_ini + info_cards_ini
    return max(c.y + c.h for c in mont)


def desenhar_faixa_estado(by, subtitulo=None):
    """Faixa de estado destacada (mensagem grande)"""
    r = pygame.Rect(60, by - 30, LARGURA - 120, 56)
    pygame.draw.rect(tela, CARD_ALT, r, border_radius=12)
    pygame.draw.rect(tela, LINHA, r, border_radius=12, width=1)
    cor_est = VERDE if msg.startswith("[APLICADO]") else (ACENTO if msg.startswith("[RESTAURADO]") else SUAVE)
    pygame.draw.circle(tela, cor_est, (98, by - 4), 5)
    texto_estado = msg
    while texto_estado and f_status.size(texto_estado)[0] > LARGURA - 240:
        texto_estado = texto_estado[:-1]
    t = f_status.render(texto_estado, True, cor_est)
    tela.blit(t, t.get_rect(center=(LARGURA // 2 + 18, by - 4)))
    if subtitulo and f_mini.size(subtitulo)[0] <= LARGURA - 240:
        t = f_mini.render(subtitulo, True, SUAVE2)
        tela.blit(t, t.get_rect(center=(LARGURA // 2 + 18, by + 22)))


def desenhar_painel_resumo():
    """Painel de resumo quando cabe; senão None (modo dev usa faixa solta)"""
    fim = _fim_cards()
    y = fim + 24
    h = (ALTURA - 165) - y
    if h < 210:
        return None

    pygame.draw.rect(tela, CARD, (20, y, LARGURA - 40, h), border_radius=14)
    pygame.draw.rect(tela, LINHA, (20, y, LARGURA - 40, h), border_radius=14, width=1)

    # Título do painel
    pygame.draw.circle(tela, ACENTO, (46, y + 28), 5)
    t = f_tit.render("CONFIGURAÇÃO APLICADA NO CÓDIGO DA NARA", True, ACENTO)
    tela.blit(t, (62, y + 18))

    # Timestamp
    t = f_mini.render("atualizado " + msg_ts, True, SUAVE)
    tela.blit(t, t.get_rect(midright=(LARGURA - 50, y + 22)))

    # Divisória abaixo do título
    pygame.draw.line(tela, LINHA, (46, y + 42), (LARGURA - 46, y + 42), width=1)

    # Linhas em 2 colunas
    linhas = dados_resumo()
    margem = 62
    espa = (LARGURA - 40 - 2 * margem) // 2
    larg_rot = 140
    for i, (rotulo, valor) in enumerate(linhas):
        col = i // 4
        lin = i % 4
        x0 = 20 + margem + col * (espa + 60)
        yy = y + 58 + lin * 27
        t = f_mini.render(rotulo.upper(), True, SUAVE2)
        tela.blit(t, (x0, yy + 2))
        t = f_rod.render(valor, True, BRANCO)
        tela.blit(t, (x0 + larg_rot + 16, yy))

    # Faixa de estado
    desenhar_faixa_estado(y + h - 46)
    return y + h


def desenhar_acoes(y):
    rect = pygame.Rect(LARGURA // 2 - 170, y, 340, 46)
    pygame.draw.rect(tela, CARD, rect, border_radius=12)
    pygame.draw.rect(tela, ACENTO, rect, border_radius=12, width=2)
    txt = f_btn.render("RESTAURAR PADRÃO", True, ACENTO)
    tela.blit(txt, txt.get_rect(center=rect.center))
    return rect


def desenhar_rodape():
    hbar = 44
    pygame.draw.rect(tela, CARD_ALT, (0, ALTURA - hbar, LARGURA, hbar))
    pygame.draw.line(tela, LINHA, (0, ALTURA - hbar), (LARGURA, ALTURA - hbar), width=1)
    y = ALTURA - hbar // 2

    ram_used, ram_total, ram_pct = ler_ram()
    cpu = ler_cpu_suave()

    # RAM à esquerda
    t = f_rod.render(f"RAM  {ram_used:.1f}/{ram_total:.1f} GB  ({ram_pct:.0f}%)", True, SUAVE)
    tela.blit(t, t.get_rect(midleft=(20, y)))

    # Stack ao centro
    t = f_mini.render("ROS2 JAZZY  ·  GAZEBO HARMONIC  ·  NOBLE", True, SUAVE2)
    tela.blit(t, t.get_rect(center=(LARGURA // 2, y)))

    # CPU com barra à direita
    t = f_rod.render(f"CPU  {cpu:4.1f}%", True, BRANCO)
    tela.blit(t, t.get_rect(midright=(LARGURA - 300, y)))
    barra = pygame.Rect(LARGURA - 290, y - 10, 130, 20)
    pygame.draw.rect(tela, CARD, barra, border_radius=6)
    pygame.draw.rect(tela, LINHA, barra, border_radius=6, width=1)
    cor_cpu = VERDE if cpu < 50 else (AMBAR if cpu > 80 else ACENTO)
    pygame.draw.rect(tela, cor_cpu,
                     (barra.x + 2, barra.y + 3, int(126 * min(cpu, 100) / 100), 14), border_radius=5)

    # Assinatura discreta (canto inferior direito)
    t = f_mini.render("Pedro Augusto", True, (74, 86, 96))
    tela.blit(t, t.get_rect(midright=(LARGURA - 40, ALTURA - 21)))


def renderizar():
    tela.fill(PRETO)
    desenhar_cabecalho()
    desenhar_toggle()
    desenhar_cards()
    pb = desenhar_painel_resumo()
    if pb is None:
        fim = _fim_cards()
        desenhar_faixa_estado(fim + 56, subtitulo="As mudanças são aplicadas automaticamente no código da NARA")
        ret = desenhar_acoes(fim + 116)
    else:
        ret = desenhar_acoes(pb + 34)
    desenhar_rodape()
    return ret


# ============================================================
# MAIN
# ============================================================

def main():
    global modo, msg
    sincronizar_do_codigo()

    ret_restaurar = None
    rodando = True
    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                continue

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos = evento.pos

                # Toggle modo
                larg = 340
                x0 = LARGURA // 2 - larg // 2
                if 88 <= pos[1] <= 130:
                    if x0 <= pos[0] <= x0 + larg // 2:
                        modo = "iniciante"
                        msg = "PRONTO - selecione uma opção"
                    elif x0 + larg // 2 <= pos[0] <= x0 + larg:
                        modo = "desenvolvedor"
                        sincronizar_do_codigo()
                        msg = "MODO DESENVOLVEDOR - selecione valores específicos"
                    msg_ts = time.strftime("%H:%M:%S")
                    continue

                # Cards do modo atual
                cards = cards_dev if modo == "desenvolvedor" else cards_ini
                clicou_card = False
                for c in cards:
                    if c.clicar(pos):
                        clicou_card = True
                        break
                if clicou_card:
                    aplicar_atual()
                    continue

                # Botão restaurar
                if ret_restaurar is not None and ret_restaurar.collidepoint(pos):
                    restaurar()
                    sincronizar_do_codigo()
                    continue

        ret_restaurar = renderizar()
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()