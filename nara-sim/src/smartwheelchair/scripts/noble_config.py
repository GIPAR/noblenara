#!/usr/bin/env python3
"""
NOBLE CONFIG - Dashboard de Simulação
Dark limpo & profissional - Ciano & Preto
Cada clique aplica a configuração NO CÓDIGO da NARA automaticamente
(com backup em .backup_configurador/ para restaurar).
Botão "CAMARO" no cabeçalho abre o dashboard original do CAMARO.
"""

import atexit
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import pygame
import psutil
from pathlib import Path

# ============================================================
# NÚCLEO - Aplicação de configurações no código da NARA
# (backup + reaplicação idempotente a partir do original)
# ============================================================
def _resolver_pacote_src() -> Path:
    """Resolve .../src/smartwheelchair mesmo quando o dashboard roda
    a partir do install/ (colcon build SEM --symlink-install).

    Com --symlink-install o __file__ já aponta para o src (via symlink).
    Sem symlink, o __file__ é uma cópia em
    <ws>/install/smartwheelchair/share/smartwheelchair/scripts/ — nesse
    caso remapeia para <ws>/src/smartwheelchair. Se não achar, cai no
    comportamento antigo (parent.parent)."""
    resolvido = Path(__file__).resolve()
    partes = resolvido.parts
    if "install" in partes:
        i = partes.index("install")
        ws = Path(*partes[:i])
        for cand in (ws / "src" / "smartwheelchair",
                     ws / "src" / "nara-sim" / "src" / "smartwheelchair"):
            if (cand / "urdf" / "narawheelchair.gazebo").exists():
                return cand
        # fallback: troca install/.../share/<pkg> por src/<pkg>
        try:
            j = partes.index("share", i)
            cand = ws / "src" / partes[j + 2] if len(partes) > j + 2 else None
            if cand is not None and (cand / "package.xml").exists():
                return cand
        except ValueError:
            pass
    return resolvido.parent.parent


PACOTE_SRC = _resolver_pacote_src()  # .../src/smartwheelchair
URDF_DIR = PACOTE_SRC / "urdf"
LAUNCH_DIR = PACOTE_SRC / "launch"
CONFIG_DIR = PACOTE_SRC / "config"

BACKUP_DIR = PACOTE_SRC / ".backup_configurador"
ARQUIVOS_MODIFICAVEIS = [
    "urdf/narawheelchair.gazebo",
    "urdf/narawheelchair.xacro",
    "launch/noblenara.launch.py",
    "launch/worldmuseum.launch.py",
    "launch/worldmuseum_finder.launch.py",
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


MAP_URDF_TAXA = {  # nível URDF -> update_rate dos plugins proprioceptivos
    "low": 10,
    "medium": 20,
    "high": 30,
}


def _ajustar_plugins_urdf(gazebo_content: str, nivel: str) -> str:
    """Aplica o nível URDF (leve/médio/pesado) nas taxas de publicação
    do DiffDrive e do JointStatePublisher em narawheelchair.gazebo.

    (As malhas STL somam ~1.5 MB — o custo real de CPU está nas taxas
    de odom/joints, por isso o nível URDF atua aqui.)"""
    taxa = MAP_URDF_TAXA.get(nivel)
    if taxa is None:
        return gazebo_content

    def _transform(bloco):
        return re.sub(r'<update_rate>[\d.]+</update_rate>',
                      f'<update_rate>{taxa}</update_rate>', bloco)

    conteudo = _editar_bloco_gazebo(gazebo_content, 'DiffDrive', _transform)
    conteudo = _editar_bloco_gazebo(conteudo, 'JointStatePublisher', _transform)
    return conteudo


MAP_MUNDO_ARQUIVO = {
    "light": "museum_light.world",
    "default": "museum_default.world",
    "finder": "museum_finder.world",
}


def _ajustar_world_launch(launch_content: str, mundo: str) -> str:
    """Troca o mundo padrão (museum_*.world) nos launches de mundo de
    forma idempotente. O launch já aceita override via
    world_file:=..., então isso só define o padrão."""
    arquivo = MAP_MUNDO_ARQUIVO.get(mundo)
    if arquivo is None:
        return launch_content
    return re.sub(r"'worlds',\s*'museum_\w+\.world'",
                  f"'worlds', '{arquivo}'", launch_content)


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

    # ============ GAZEBO (sensores + taxas URDF) ============
    base_gazebo = _ler_base("urdf/narawheelchair.gazebo")
    conteudo = aplicar_sensor_nivel(base_gazebo, config.get("sensor_quality", "medium"))

    if "urdf_quality" in config:
        conteudo = _ajustar_plugins_urdf(conteudo, config["urdf_quality"])

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

    # ============ MUNDO (padrão dos launches de mundo) ============
    # Aceita tanto a chave do modo iniciante ("world") quanto a do
    # modo desenvolvedor ("mundo").
    mundo = config.get("world", config.get("mundo"))
    if mundo in MAP_MUNDO_ARQUIVO:
        for launch_rel in ("launch/worldmuseum.launch.py",
                           "launch/worldmuseum_finder.launch.py"):
            base_launch = _ler_base(launch_rel)
            novo_launch = _ajustar_world_launch(base_launch, mundo)
            with open(PACOTE_SRC / launch_rel, "w") as f:
                f.write(novo_launch)

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

    m = re.search(r'DiffDrive.*?<update_rate>([\d.]+)</update_rate>', gazebo, re.DOTALL)
    info["diffdrive_rate"] = float(m.group(1)) if m else 20.0

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
    mundo = config.get("world", config.get("mundo", "default"))
    world_file = MAP_MUNDO_ARQUIVO.get(mundo, "museum_default.world")

    c = (nav2_codename or CODENAME_PADRAO).strip().lower() or CODENAME_PADRAO
    mapa = nav2_mapa if nav2_amcl else None
    map_arg = f"map_file:=${{PKG_SHARE}}/maps/{mapa}.yaml" if mapa else "map_file:=none"

    with open(caminho, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# NOBLE NARA - Simulação configurada pelo dashboard\n")
        f.write(f"# URDF: {config.get('urdf_quality','medium')} | Sensores: {config.get('sensor_quality','medium')} | Mundo: {mundo} | Cadeira: {c} RViz:{nav2_rviz} SLAM:{nav2_slam} AMCL:{nav2_amcl} Mapa:{mapa}\n\n")
        f.write('PKG_SHARE="$(ros2 pkg prefix smartwheelchair)/share/smartwheelchair"\n\n')
        f.write("echo '>> Iniciando mundo (Gazebo)...'\n")
        f.write(f'ros2 launch smartwheelchair worldmuseum.launch.py "world_file:=${{PKG_SHARE}}/worlds/{world_file}" &\n')
        f.write("sleep 5\n")
        f.write(f"echo '>> Iniciando cadeira {c}...'\n")
        f.write(f"ros2 launch smartwheelchair noblenara.launch.py robot_codename:={c} x:=0.0 y:=0.0 yaw:=0.0 &\n")
        if nav2_slam and not nav2_amcl:
            f.write("sleep 3\n")
            f.write("echo '>> Iniciando SLAM...'\n")
            f.write(f"ros2 launch smartwheelchair slam.launch.py robot_codename:={c} &\n")
        f.write("sleep 3\n")
        f.write("echo '>> Iniciando Nav2...'\n")
        f.write(f"ros2 launch smartwheelchair nav2_launch.py robot_codename:={c} {map_arg} rviz:={'true' if nav2_rviz else 'false'} &\n")
        f.write("\necho '>> Simulação iniciada! CTRL+C para encerrar.'\n")
        f.write("wait\n")

    os.chmod(caminho, 0o755)
    return caminho

# ============================================================
# CONTROLE DA SIMULAÇÃO — SIM (mundo) + NAV2 OPTIONS (cadeiras)
# ============================================================
# O botão SIM sobe SÓ o mundo (worldmuseum.launch.py). Cada cadeira sobe
# pelo painel NAV2 OPTIONS num grupo próprio: robô (noblenara.launch.py)
# + [SLAM] + [Nav2], todos com o mesmo robot_codename:=<prefixo>.
# Filhos usam start_new_session para permitir killpg em grupo;
# encerrar_tudo_ao_sair() mata mundo + todas as cadeiras ao fechar.
proc_sim = None    # Popen do mundo (worldmuseum.launch.py)
_log_sim = None
LOG_SIM = Path("/tmp/noble_sim.log")
robos = {}         # codename -> {"proc": Popen|None, "log": file|None, "opts": dict}
CODENAME_PADRAO = "alfa"
MAPA_PADRAO = "museu"
ESPACEJAMENTO_SPAWN = 2.0  # metros em +x entre cadeiras (auto-offset)

# Opções do painel NAV2 OPTIONS (persistidas em ultima_config.json)
nav2_rviz = False
nav2_slam = True
nav2_amcl = False
nav2_codename = CODENAME_PADRAO
nav2_mapa = MAPA_PADRAO


def _processo_vivo(proc):
    return proc is not None and proc.poll() is None


def sim_rodando():
    return _processo_vivo(proc_sim)


def _entrada_robo(codename):
    return robos.get(codename)


def cadeira_rodando(codename):
    ent = _entrada_robo(codename)
    return ent is not None and _processo_vivo(ent.get("proc"))


def nav2_rodando(codename=None):
    """Sem codename: True se QUALQUER cadeira estiver no ar (compat)."""
    if codename is not None:
        return cadeira_rodando(codename)
    return any(cadeira_rodando(c) for c in list(robos.keys()))


def cadeiras_rodando():
    return sorted(c for c in robos.keys() if cadeira_rodando(c))


def _grupo_vivo(pgid):
    """True se ainda existe ALGUM processo no grupo (sinal 0 só checa)."""
    try:
        os.killpg(pgid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _encerrar(proc, timeout=8):
    """Mata o GRUPO inteiro (pai + filhos + netos): SIGINT gracioso,
    depois SIGTERM e por fim SIGKILL. Retorna True se o grupo sumiu.

    Por que a cascata? Jobs em background no bash ignoram SIGINT/SIGQUIT
    por padrão — só matar o pai deixava os filhos órfãos em 2º plano."""
    if not _processo_vivo(proc):
        return True
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, PermissionError):
        return True
    for sig, espera in ((signal.SIGINT, timeout),
                        (signal.SIGTERM, 3),
                        (signal.SIGKILL, 2)):
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):
            return True
        try:
            proc.wait(timeout=espera)
        except subprocess.TimeoutExpired:
            pass
        except ChildProcessError:
            pass
        if not _grupo_vivo(pgid):
            return True
    return not _grupo_vivo(pgid)


def _fechar_log(which):
    global _log_sim
    try:
        if which == "sim" and _log_sim is not None:
            _log_sim.close()
        elif which.startswith("robo:"):
            codename = which.split(":", 1)[1]
            ent = _entrada_robo(codename)
            if ent is not None and ent.get("log") is not None:
                try:
                    ent["log"].close()
                except Exception:
                    pass
                ent["log"] = None
    except Exception:
        pass
    finally:
        if which == "sim":
            _log_sim = None


def _log_path_robo(codename):
    return Path(f"/tmp/noble_robo_{codename}.log")


RE_CODENAME = re.compile(r'^[a-z0-9_]{1,16}$')


def listar_mapas() -> list:
    """Nomes (prefixos) de mapas disponíveis em <pacote>/maps/*.yaml."""
    try:
        pasta = PACOTE_SRC / "maps"
        if not pasta.exists():
            return []
        return sorted(p.stem for p in pasta.glob("*.yaml"))
    except Exception:
        return []


def validar_codename(codename: str):
    """Retorna (ok, msg). Prefixo vira namespace /noblenara/<codename>/..."""
    c = (codename or "").strip().lower()
    if not c:
        return False, "prefixo da cadeira vazio"
    if not RE_CODENAME.match(c):
        return False, "use só a-z, 0-9 e _ (máx. 16)"
    return True, ""


def validar_mapa(nome: str):
    """Retorna (ok, msg). Exige <nome>.yaml + o .pgm apontado no image:."""
    n = (nome or "").strip()
    if not n or "/" in n or n.startswith("."):
        return False, "nome de mapa inválido"
    yml = PACOTE_SRC / "maps" / f"{n}.yaml"
    if not yml.exists():
        return False, f"maps/{n}.yaml não encontrado"
    try:
        conteudo = yml.read_text()
        m = re.search(r'image:\s*"?([^"\s]+\.pgm)"?', conteudo)
        if m and not (PACOTE_SRC / "maps" / m.group(1)).exists():
            return False, f"{m.group(1)} não encontrado em maps/"
    except Exception:
        pass
    return True, ""


def _offset_spawn(indice: int):
    """Auto-offset: cadeira i nasce em x=2.0*i (evita sobreposição em 0,0)."""
    return (ESPACEJAMENTO_SPAWN * indice, 0.0, 0.0)


def _montar_cmd_sim(cfg: dict, visual: bool = True) -> str:
    """Sobe SÓ o mundo. visual=True abre o Gazebo; False só o servidor."""
    mundo = cfg.get("world", cfg.get("mundo", "default"))
    world_file = MAP_MUNDO_ARQUIVO.get(mundo, "museum_default.world")
    gui = "true" if visual else "false"
    return (
        'PKG_SHARE="$(ros2 pkg prefix smartwheelchair)/share/smartwheelchair"; '
        f'ros2 launch smartwheelchair worldmuseum.launch.py "world_file:=${{PKG_SHARE}}/worlds/{world_file}" gui:={gui} & '
        "wait"
    )


def _montar_cmd_nav2(codename: str, rviz: bool = False, mapa: str = None) -> list:
    """Nav2 da cadeira <codename>. mapa=None -> sem AMCL (map_file:=none)."""
    cmd = ["ros2", "launch", "smartwheelchair", "nav2_launch.py",
           f"robot_codename:={codename}"]
    if mapa:
        cmd.append(f"map_file:=$PKG_SHARE/maps/{mapa}.yaml")
    else:
        cmd.append("map_file:=none")
    cmd.append("rviz:=true" if rviz else "rviz:=false")
    return cmd


def _montar_cmd_cadeira(codename: str, x: float, y: float, yaw: float,
                        rviz: bool, slam: bool, mapa: str = None) -> str:
    """Um grupo bash por cadeira: robô + [SLAM] + [Nav2]. Prefixos
    /noblenara/<codename>/... vêm dos launch args (já existem na NARA)."""
    partes = [
        'PKG_SHARE="$(ros2 pkg prefix smartwheelchair)/share/smartwheelchair"; ',
        f"ros2 launch smartwheelchair noblenara.launch.py robot_codename:={codename} x:={x} y:={y} yaw:={yaw} & ",
        "sleep 5; ",
    ]
    if slam:
        partes.append(f"ros2 launch smartwheelchair slam.launch.py robot_codename:={codename} & ")
        partes.append("sleep 3; ")
    nav = " ".join(_montar_cmd_nav2(codename, rviz=rviz, mapa=mapa))
    partes.append(nav + " & ")
    partes.append("wait")
    return "".join(partes)


def iniciar_cadeira(codename: str, rviz: bool = False, slam: bool = True,
                    amcl: bool = False, mapa: str = None):
    """Sobe robô + [SLAM] + Nav2 ([AMCL+mapa] ou sem mapa). Um grupo só."""
    global msg, msg_ts
    c = (codename or "").strip().lower()
    ok, err = validar_codename(c)
    if not ok:
        msg = f"[CADEIRA] prefixo inválido: {err}"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    if amcl:
        okm, errm = validar_mapa(mapa or "")
        if not okm:
            msg = f"[CADEIRA] AMCL precisa de mapa: {errm}"
            msg_ts = time.strftime("%H:%M:%S")
            return False
    else:
        mapa = None
    if slam and amcl:
        # Exclusão automática: AMCL (mapa pronto) x SLAM (mapeando) brigam
        slam = False
        msg_extra = " (SLAM auto-desligado: conflita com AMCL)"
    else:
        msg_extra = ""
    if not sim_rodando():
        msg = "[CADEIRA] inicie o MUNDO (SIM) primeiro"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    if cadeira_rodando(c):
        msg = f"[CADEIRA] '{c}' já está rodando"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    x, y, yaw = _offset_spawn(len(robos))
    cmd = _montar_cmd_cadeira(c, x, y, yaw, rviz=rviz, slam=slam, mapa=mapa)
    try:
        fh = open(_log_path_robo(c), "a")
        proc = subprocess.Popen(
            ["bash", "-c", cmd],
            start_new_session=True, stdout=fh, stderr=subprocess.STDOUT)
    except Exception as e:
        msg = f"[CADEIRA] falhou ao iniciar '{c}': {e}"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    robos[c] = {"proc": proc, "log": fh,
                "opts": {"rviz": rviz, "slam": slam, "amcl": amcl,
                         "mapa": mapa, "x": x, "y": y}}
    partes = [f"robô '{c}' em ({x:.0f},{y:.0f})"]
    partes.append("SLAM ON" if slam else "SLAM OFF")
    partes.append(f"AMCL+{mapa}" if amcl else "sem AMCL")
    partes.append("RViz" if rviz else "sem RViz")
    msg = "[CADEIRA] " + " | ".join(partes) + msg_extra + f" — log: {_log_path_robo(c)}"
    msg_ts = time.strftime("%H:%M:%S")
    return True


def parar_cadeira(codename: str):
    """Para UMA cadeira (robô+SLAM+Nav2 dela)."""
    global msg, msg_ts
    c = (codename or "").strip().lower()
    ent = _entrada_robo(c)
    if ent is None or not _processo_vivo(ent.get("proc")):
        if c in robos:
            robos.pop(c, None)
        msg = f"[CADEIRA] '{c}' não está rodando"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    ok = _encerrar(ent["proc"])
    robos.pop(c, None)
    _fechar_log(f"robo:{c}")
    msg = f"[CADEIRA] '{c}' parada" if ok else f"[CADEIRA] '{c}' parada forçada (SIGKILL)"
    msg_ts = time.strftime("%H:%M:%S")
    return True


def parar_todas_cadeiras():
    """Para todas as cadeiras. Retorna nº de cadeiras paradas."""
    n = 0
    for c in list(robos.keys()):
        ent = _entrada_robo(c)
        try:
            if ent is not None and _processo_vivo(ent.get("proc")):
                _encerrar(ent["proc"])
                n += 1
        except Exception:
            pass
        robos.pop(c, None)
        _fechar_log(f"robo:{c}")
    return n


def iniciar_simulacao(visual: bool = True):
    """Sobe SÓ o mundo. Retorna True se iniciou."""
    global proc_sim, _log_sim, msg, msg_ts
    if sim_rodando():
        msg = "[SIM] simulação já está rodando"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    cmd = _montar_cmd_sim(coletar_config(), visual=visual)
    try:
        _log_sim = open(LOG_SIM, "a")
        proc_sim = subprocess.Popen(
            ["bash", "-c", cmd],
            start_new_session=True, stdout=_log_sim, stderr=subprocess.STDOUT)
    except Exception as e:
        msg = f"[SIM] falhou ao iniciar: {e}"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    modo_txt = "com visual" if visual else "headless (só terminal)"
    if visual:
        msg = f"[SIM] simulação iniciada ({modo_txt}) — log: {LOG_SIM}"
    else:
        msg = f"[SIM] simulação iniciada ({modo_txt}) — mantenha o dashboard aberto; fechar ENCERRA — log: {LOG_SIM}"
    msg_ts = time.strftime("%H:%M:%S")
    return True


def parar_simulacao():
    """Para todas as cadeiras e depois o mundo."""
    global proc_sim, msg, msg_ts
    n = parar_todas_cadeiras() if robos else 0
    # parar_todas_cadeiras já definiu msg; guarda e continua p/ o mundo
    if not sim_rodando():
        if n:
            msg = f"[SIM] {n} cadeira(s) parada(s); mundo já estava parado"
        else:
            msg = "[SIM] nada rodando"
        msg_ts = time.strftime("%H:%M:%S")
        return bool(n)
    ok = _encerrar(proc_sim)
    proc_sim = None
    _fechar_log("sim")
    extra = f" + {n} cadeira(s)" if n else ""
    msg = f"[SIM] mundo parado{extra}" if ok else f"[SIM] parada forçada (SIGKILL){extra}"
    msg_ts = time.strftime("%H:%M:%S")
    return True


def encerrar_tudo_ao_sair():
    """Mata mundo + todas as cadeiras ao fechar (idempotente, sem UI).

    Evita processo eterno no modo headless (SEM VISUAL / SEM RVIZ),
    que não tem janela do Gazebo/RViz para o usuário perceber que
    a simulação continua rodando. Chamado nos caminhos de saída do
    main() e via atexit/sinais como rede de segurança."""
    global proc_sim
    for c in list(robos.keys()):
        try:
            ent = _entrada_robo(c)
            if ent is not None and _processo_vivo(ent.get("proc")):
                _encerrar(ent["proc"])
        except Exception:
            pass
        finally:
            robos.pop(c, None)
            try:
                _fechar_log(f"robo:{c}")
            except Exception:
                pass
    try:
        if sim_rodando():
            _encerrar(proc_sim)
    except Exception:
        pass
    finally:
        proc_sim = None
        try:
            _fechar_log("sim")
        except Exception:
            pass


def _tratar_sinal_saida(signum, frame):
    """Handler SIGINT/SIGTERM: garante cleanup e sai sem rastro."""
    try:
        encerrar_tudo_ao_sair()
    finally:
        # sys.exit dispara o atexit (idempotente) e fecha o interpretador
        sys.exit(0)


pygame.init()

# ============================================================
# TROCA DE ROBÔ — botão "CAMARO" no cabeçalho
# ============================================================
# Abre o camaro_config.py ORIGINAL do CAMARO (visual e configurações
# 100% do CAMARO) e fecha este dashboard. O dashboard do CAMARO tem o
# botão simétrico "NARA". Nada é duplicado: cada dashboard continua
# dono do seu próprio robô.
# Override manual (testes): CAMARO_DASHBOARD_PATH=/caminho/camaro_config.py
CAMARO_DASHBOARD_ENV = "CAMARO_DASHBOARD_PATH"
COR_CAMARO = (255, 199, 0)  # amarelo Rally do CAMARO (destaque do botão de destino)


def localizar_dashboard_camaro():
    """Procura o camaro_config.py do CAMARO. Retorna Path ou None."""
    override = os.environ.get(CAMARO_DASHBOARD_ENV)
    if override:
        p = Path(override)
        return p if p.exists() else None
    rel = Path("noblecamaro-main") / "src" / "camaro_description" / "scripts" / "camaro_config.py"
    candidatos = [Path.home() / rel]
    atual = Path(__file__).resolve().parent
    for _ in range(6):
        candidatos.append(atual / rel)
        atual = atual.parent
    for c in candidatos:
        if c.exists():
            return c
    return None


def _robot_btn_rect() -> pygame.Rect:
    """Retângulo do botão CAMARO (à esquerda do badge de status)."""
    return pygame.Rect(LARGURA - 256, 14, 110, 26)


def desenhar_botao_robo():
    destino = localizar_dashboard_camaro()
    r = _robot_btn_rect()
    cor = COR_CAMARO if destino else SUAVE2
    pygame.draw.rect(tela, CARD, r, border_radius=13)
    pygame.draw.rect(tela, cor, r, border_radius=13, width=2)
    t = f_opc.render("CAMARO", True, cor)
    tela.blit(t, t.get_rect(center=r.center))


def alternar_dashboard():
    """Abre o dashboard do CAMARO. Retorna True se abriu (chamador fecha este)."""
    global msg, msg_ts
    destino = localizar_dashboard_camaro()
    if destino is None:
        msg = "[ERRO] Dashboard CAMARO não encontrado (noblecamaro-main)"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    try:
        subprocess.Popen([sys.executable, str(destino)])
    except Exception as e:
        msg = f"[ERRO] não abri o dashboard CAMARO: {e}"
        msg_ts = time.strftime("%H:%M:%S")
        return False
    return True


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

f_logo = _fonte(38, bold=True)
f_sub = _fonte(12)
f_tit = _fonte(14, bold=True)
f_opc = _fonte(13, bold=True)
f_btn = _fonte(14, bold=True)
f_rod = _fonte(12)
f_mini = _fonte(11)
f_status = _fonte(15, bold=True)
# Variantes grossas p/ o painel NAV2 OPTIONS (layout mais encorpado)
f_rod_b = _fonte(13, bold=True)
f_mini_b = _fonte(11, bold=True)
f_tit_g = _fonte(16, bold=True)

clock = pygame.time.Clock()

# ============================================================
# CPU SUAVIZADO (corrige oscilação)
# ============================================================
# Problemas do cálculo antigo: psutil.cpu_percent(interval=None) retorna
# sempre 0.0 na 1ª chamada (sem referência anterior) e era amostrado a
# cada frame (~16ms), gerando ruído. Correção: prime no startup, amostra
# no máximo 1x a cada 0.5s e média móvel das últimas 6 (~3s de janela).
_cpu_fila = []
_cpu_media = 0.0
_ultima_tick = 0.0
_CPU_JANELA = 6       # nº de amostras na média móvel
_CPU_PERIODO = 0.5    # segundos entre amostras
psutil.cpu_percent(interval=None)  # prime: descarta a 1ª leitura (sempre 0.0)


def ler_cpu_suave():
    """CPU estável: 1 amostra a cada 0.5s + média móvel das últimas 6 (~3s)."""
    global _cpu_media, _ultima_tick
    agora = time.time()
    if agora - _ultima_tick >= _CPU_PERIODO:
        _ultima_tick = agora
        v = psutil.cpu_percent(interval=None)
        if v is not None:
            _cpu_fila.append(v)
            if len(_cpu_fila) > _CPU_JANELA:
                _cpu_fila.pop(0)
            _cpu_media = sum(_cpu_fila) / len(_cpu_fila)
    return _cpu_media


def ler_ram():
    v = psutil.virtual_memory()
    return v.used / 1e9, v.total / 1e9, v.percent


# ============================================================
# EFEITO NEON (texto com brilho + contorno de luz)
# ============================================================

def _texto_grosso(texto, fonte, centro, cor=ACENTO):
    """Texto único tom: traço bem cheio (contorno nas 8 direções)"""
    base = fonte.render(texto, True, cor)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1),
                   (-1, -1), (1, -1), (-1, 1), (1, 1)):
        tela.blit(base, base.get_rect(center=(centro[0] + dx, centro[1] + dy)))
    tela.blit(base, base.get_rect(center=centro))


def _texto_grosso_em(sup, texto, fonte, centro, cor):
    """Igual ao _texto_grosso, mas blita em qualquer Surface (modais)."""
    base = fonte.render(texto, True, cor)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1),
                   (-1, -1), (1, -1), (-1, 1), (1, 1)):
        sup.blit(base, base.get_rect(center=(centro[0] + dx, centro[1] + dy)))
    sup.blit(base, base.get_rect(center=centro))


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
              "Taxa de publicação odom/juntas (10/20/30 Hz)"),
    novo_card(0, 1, "SENSORES", "sensores", [("LEVE", "low"), ("MÉDIO", "medium"), ("PESADO", "high")],
              "Câmeras, LIDAR e resolução"),
    novo_card(0, 2, "MUNDO", "mundo", [("LEVE", "light"), ("PADRÃO", "default"), ("COMPLETO", "finder")],
              "Carga do cenário, sombras e agentes"),
]

# --- Cartões informativos do Modo Iniciante (o que muda em cada nível) ---
info_cards_ini = [
    InfoCard("URDF",
             "na taxa odom/juntas",
             [("LEVE", "plugins a 10 Hz (leve)"),
              ("MÉDIO", "plugins a 20 Hz (padrão)"),
              ("PESADO", "plugins a 30 Hz (máximo)")],
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
confirmar_saida = False
_modal_imagem = None

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
    # Nível URDF derivado da taxa dos plugins (10/20/30 Hz)
    taxa = atual.get("diffdrive_rate", 20.0)
    nivel_urdf = "low" if taxa <= 10 else ("high" if taxa >= 30 else "medium")
    for c in cards_ini:
        if c.categoria == "sensores":
            c.definir(nivel_sensor)
        elif c.categoria == "urdf":
            c.definir(nivel_urdf)


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
    salvar_estado_ui()

    resumo = " / ".join(f"{k.upper()}: {v}" for k, v in cfg.items())
    msg = "[APLICADO] " + resumo
    msg_ts = time.strftime("%H:%M:%S")
    return cfg


def _caminho_estado():
    return BACKUP_DIR / "ultima_config.json"


def salvar_estado_ui():
    """Persiste a última configuração aplicada p/ reabrir o painel igual"""
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        _caminho_estado().write_text(
            json.dumps({"modo": modo, "config": coletar_config(),
                        "nav2": {"rviz": nav2_rviz, "slam": nav2_slam,
                                 "amcl": nav2_amcl, "codename": nav2_codename,
                                 "mapa": nav2_mapa}}, indent=2))
    except Exception:
        pass


def _card_por_chave(chave: str):
    if chave == "urdf_quality":
        for c in cards_ini:
            if c.categoria == "urdf":
                return c
    elif chave == "sensor_quality":
        for c in cards_ini:
            if c.categoria == "sensores":
                return c
    elif chave in ("world", "mundo"):
        cards_atual = cards_dev if modo == "desenvolvedor" else cards_ini
        for c in cards_atual:
            if c.categoria == "mundo":
                return c
        for c in (cards_ini if cards_atual is cards_dev else cards_dev):
            if c.categoria == "mundo":
                return c
    else:
        for c in cards_dev:
            if c.categoria == chave and c.categoria != "mundo":
                return c
    return None


def aplicar_estado_salvo():
    """Restaura no painel a última configuração aplicada (se existir)"""
    global modo, nav2_rviz, nav2_slam, nav2_amcl, nav2_codename, nav2_mapa
    caminho = _caminho_estado()
    if not caminho.exists():
        return
    try:
        dados = json.loads(caminho.read_text())
    except Exception:
        return
    modo = dados.get("modo", "iniciante")
    for chave, valor in dados.get("config", {}).items():
        c = _card_por_chave(chave)
        if c is not None:
            c.definir(valor)
    nv = dados.get("nav2", {})
    if isinstance(nv, dict):
        nav2_rviz = bool(nv.get("rviz", nav2_rviz))
        nav2_slam = bool(nv.get("slam", nav2_slam))
        nav2_amcl = bool(nv.get("amcl", nav2_amcl))
        if isinstance(nv.get("codename"), str) and nv["codename"]:
            nav2_codename = nv["codename"].strip().lower() or nav2_codename
        if isinstance(nv.get("mapa"), str) and nv["mapa"]:
            nav2_mapa = nv["mapa"].strip() or nav2_mapa
        if nav2_amcl and nav2_slam:
            nav2_slam = False  # exclusão: AMCL x SLAM brigam pelo mapa


def restaurar():
    """Restaura o código original e reseta os botões"""
    global msg, msg_ts
    restaurar_originais()
    restaurar_ui_padrao()
    salvar_estado_ui()
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
    global nav2_rviz, nav2_slam, nav2_amcl, nav2_codename, nav2_mapa
    nav2_rviz, nav2_slam, nav2_amcl = False, True, False
    nav2_codename, nav2_mapa = CODENAME_PADRAO, MAPA_PADRAO


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
        ("MUNDO", f"{mundo} · {'rodando' if sim_rodando() else 'parado'}"),
        ("CADEIRAS NO AR", (", ".join(cadeiras_rodando())[:30] if cadeiras_rodando() else "nenhuma")),
        ("PAINEL NAV2", f"{nav2_codename[:12]} · R{'ON' if nav2_rviz else 'OFF'} S{'ON' if nav2_slam else 'OFF'} A{'ON' if nav2_amcl else 'OFF'}"),
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

    # Badge com o nome + versão (sem ícone, texto centralizado)
    b = pygame.Rect(18, 12, 175, 28)
    pygame.draw.rect(tela, CARD, b, border_radius=14)
    pygame.draw.rect(tela, LINHA, b, border_radius=14, width=1)
    t = f_mini.render("NOBLE CONFIG V2.0", True, ACENTO)
    tela.blit(t, t.get_rect(center=b.center))

    # Status conectado (à direita)
    s = pygame.Rect(LARGURA - 138, 14, 120, 26)
    pygame.draw.rect(tela, CARD, s, border_radius=13)
    pygame.draw.rect(tela, LINHA, s, border_radius=13, width=1)
    pygame.draw.circle(tela, VERDE, (s.x + 16, s.centery), 4)
    t = f_mini.render("CÓDIGO NARA", True, SUAVE)
    tela.blit(t, t.get_rect(center=(s.x + 78, s.centery)))

    # Botão de troca de robô (CAMARO)
    desenhar_botao_robo()

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
    """Três botões: SIMULAÇÃO | NAV2 | RESTAURAR. Retorna dict de rects."""
    bw, bh, gap = 220, 46, 16
    x0 = LARGURA // 2 - (3 * bw + 2 * gap) // 2
    rects = {
        "sim": pygame.Rect(x0, y, bw, bh),
        "nav2": pygame.Rect(x0 + bw + gap, y, bw, bh),
        "restaurar": pygame.Rect(x0 + 2 * (bw + gap), y, bw, bh),
    }
    # SIM — igual ao RESTAURAR PADRÃO quando parado (contorno azul),
    # todo preenchido azul com letra preta quando rodando
    if sim_rodando():
        pygame.draw.rect(tela, ACENTO, rects["sim"], border_radius=12)
        txt = f_btn.render("PARAR SIM", True, PRETO)
    else:
        pygame.draw.rect(tela, CARD, rects["sim"], border_radius=12)
        pygame.draw.rect(tela, ACENTO, rects["sim"], border_radius=12, width=2)
        txt = f_btn.render("INICIAR SIM", True, ACENTO)
    tela.blit(txt, txt.get_rect(center=rects["sim"].center))
    # NAV2 OPTIONS — abre o painel da cadeira; mostra nº no ar
    n = len(cadeiras_rodando())
    rot = f"NAV2 OPTIONS ({n})" if n else "NAV2 OPTIONS"
    pygame.draw.rect(tela, CARD, rects["nav2"], border_radius=12)
    pygame.draw.rect(tela, ACENTO if n else LINHA, rects["nav2"], border_radius=12, width=2 if n else 1)
    txt = f_btn.render(rot, True, ACENTO if n else SUAVE)
    tela.blit(txt, txt.get_rect(center=rects["nav2"].center))
    # RESTAURAR
    pygame.draw.rect(tela, CARD, rects["restaurar"], border_radius=12)
    pygame.draw.rect(tela, ACENTO, rects["restaurar"], border_radius=12, width=2)
    txt = f_btn.render("RESTAURAR PADRÃO", True, ACENTO)
    tela.blit(txt, txt.get_rect(center=rects["restaurar"].center))
    return rects


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

# Popup COM VISUAL / SEM VISUAL (None | "sim" | "nav2").
# Abre ao clicar INICIAR SIM ou NAV2 parados; a escolha vale para essa vez.
modal_visual = None


def _modal_visual_rects():
    janela = pygame.Rect(0, 0, 520, 350)
    janela.center = (LARGURA // 2, ALTURA // 2)
    return {
        "com": pygame.Rect(janela.x + 40, janela.y + 178, 200, 52),
        "sem": pygame.Rect(janela.x + 280, janela.y + 178, 200, 52),
        "cancelar": pygame.Rect(janela.centerx - 70, janela.y + 258, 140, 40),
    }


def desenhar_modal_visual():
    # Popup do SIM (mundo): COM VISUAL abre o Gazebo, SEM VISUAL só servidor.
    img = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    img.fill((0, 0, 0, 150))

    janela = pygame.Rect(0, 0, 520, 350)
    janela.center = (LARGURA // 2, ALTURA // 2)
    pygame.draw.rect(img, CARD, janela, border_radius=14)
    pygame.draw.rect(img, ACENTO, janela, border_radius=14, width=2)

    t = f_tit.render("INICIAR MUNDO?", True, ACENTO)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 44)))
    t = f_rod.render("Abrir a janela do Gazebo? (só o mundo, sem robô)", True, BRANCO)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 76)))
    t = f_mini.render("A escolha vale para esta vez.", True, SUAVE)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 100)))
    t = f_mini.render("SEM VISUAL roda só no terminal — mantenha o dashboard aberto.", True, AMBAR)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 126)))
    t = f_mini.render("Fechar o dashboard vai ENCERRAR a simulação.", True, AMBAR)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 144)))

    rets = _modal_visual_rects()
    for chave, rot in (("com", "COM VISUAL"), ("sem", "SEM VISUAL")):
        r = rets[chave]
        pygame.draw.rect(img, ACENTO, r, border_radius=10)
        t = f_btn.render(rot, True, PRETO)
        img.blit(t, t.get_rect(center=r.center))

    r = rets["cancelar"]
    pygame.draw.rect(img, CARD_ALT, r, border_radius=10)
    pygame.draw.rect(img, LINHA, r, border_radius=10, width=1)
    t = f_btn.render("CANCELAR", True, SUAVE)
    img.blit(t, t.get_rect(center=r.center))

    tela.blit(img, (0, 0))


# ============================================================
# PAINEL NAV2 OPTIONS — toggles + prefixo + mapa (modal)
# ============================================================
# Cada INICIAR sobe 1 cadeira: robô + [SLAM] + Nav2 ([AMCL+mapa] ou sem
# mapa), tudo com robot_codename:=<prefixo> -> tópicos
# /noblenara/<prefixo>/... (plumbing já existe nos launches da NARA).
modal_nav2 = False
campo_foco = None  # "codename" | "mapa" | None


def _modal_nav2_rects():
    janela = pygame.Rect(0, 0, 680, 600)
    janela.center = (LARGURA // 2, ALTURA // 2)
    x = janela.x
    return {
        "janela": janela,
        # áreas de clique das fileiras (rótulo + switch compacto)
        "rviz": pygame.Rect(x + 30, janela.y + 92, 420, 52),
        "slam": pygame.Rect(x + 30, janela.y + 146, 420, 52),
        "amcl": pygame.Rect(x + 30, janela.y + 200, 420, 52),
        "codename": pygame.Rect(x + 270, janela.y + 268, 350, 44),
        "mapa": pygame.Rect(x + 270, janela.y + 322, 350, 44),
        "iniciar": pygame.Rect(x + 40, janela.y + 452, 290, 52),
        "parar": pygame.Rect(x + 350, janela.y + 452, 290, 52),
        "fechar": pygame.Rect(janela.centerx - 90, janela.y + 516, 180, 44),
    }


# Progresso da animação de cada switch (0.0=OFF à esquerda, 1.0=ON à direita)
_anim_toggle = {"rviz": 0.0, "slam": 0.0, "amcl": 0.0}
_LARG_SWITCH, _ALT_SWITCH = 76, 34


def _lerp_cor(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _desenhar_switch_nav2(img, base_x, centery, progresso):
    """Chavinha deslizante: botão corre p/ direita e o trilho acende no ON."""
    track = pygame.Rect(base_x, centery - _ALT_SWITCH // 2, _LARG_SWITCH, _ALT_SWITCH)
    cor_trilho = _lerp_cor((45, 54, 63), ACENTO, progresso)
    pygame.draw.rect(img, cor_trilho, track, border_radius=_ALT_SWITCH // 2)
    if progresso < 0.5:
        pygame.draw.rect(img, LINHA, track, border_radius=_ALT_SWITCH // 2, width=1)
    raio = 13
    kx = track.x + raio + 4 + progresso * (_LARG_SWITCH - 2 * (raio + 4))
    pygame.draw.circle(img, BRANCO, (int(kx), int(centery)), raio)


def _desenhar_campo_nav2(img, rect, texto, focado, ativo=True):
    cor_borda = ACENTO if focado else (LINHA if ativo else SUAVE2)
    pygame.draw.rect(img, CARD_ALT, rect, border_radius=10)
    pygame.draw.rect(img, cor_borda, rect, border_radius=10, width=2 if focado else 1)
    vis = texto + ("_" if focado else "")
    while vis and f_rod.size(vis)[0] > rect.w - 24:
        vis = vis[1:]
    t = f_rod_b.render(vis if vis else ("digite..." if focado else texto), True,
                      BRANCO if ativo else SUAVE2)
    img.blit(t, (rect.x + 12, rect.centery - t.get_height() // 2))


def desenhar_modal_nav2():
    img = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    img.fill((0, 0, 0, 150))

    rets = _modal_nav2_rects()
    janela = rets["janela"]
    x = janela.x
    pygame.draw.rect(img, CARD, janela, border_radius=14)
    pygame.draw.rect(img, ACENTO, janela, border_radius=14, width=2)

    _texto_grosso_em(img, "NAV2 OPTIONS — CADEIRA", f_tit_g,
                      (janela.centerx, janela.y + 40), ACENTO)
    t = f_mini_b.render("Cada INICIAR sobe 1 cadeira (robô + SLAM/Nav2) com o prefixo.", True, SUAVE)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 66)))

    for chave, rot, ligado in (
            ("rviz", "RVIZ", nav2_rviz),
            ("slam", "SLAM", nav2_slam),
            ("amcl", "AMCL (mapa pronto)", nav2_amcl)):
        r = rets[chave]
        t = f_rod_b.render(rot, True, BRANCO)
        img.blit(t, (r.x + 10, r.centery - t.get_height() // 2))
        # anima o botão deslizando até o estado atual
        alvo = 1.0 if ligado else 0.0
        p = _anim_toggle[chave] + max(-0.25, min(0.25, alvo - _anim_toggle[chave]))
        _anim_toggle[chave] = max(0.0, min(1.0, p))
        sx = r.x + 250
        _desenhar_switch_nav2(img, sx, r.centery, _anim_toggle[chave])
        st = f_mini_b.render("ON" if ligado else "OFF", True,
                            ACENTO if ligado else SUAVE2)
        img.blit(st, (sx + _LARG_SWITCH + 10, r.centery - st.get_height() // 2))

    t = f_rod_b.render("CADEIRA (prefixo):", True, BRANCO)
    img.blit(t, (x + 40, janela.y + 268 + 22 - t.get_height() // 2))
    _desenhar_campo_nav2(img, rets["codename"], nav2_codename or "", campo_foco == "codename")

    t = f_rod_b.render("MAPA (maps/):", True, BRANCO if nav2_amcl else SUAVE2)
    img.blit(t, (x + 40, janela.y + 322 + 22 - t.get_height() // 2))
    _desenhar_campo_nav2(img, rets["mapa"], nav2_mapa or "", campo_foco == "mapa", ativo=nav2_amcl)

    mapas = listar_mapas()
    prox_x, _, _ = _offset_spawn(len(robos))
    t = f_mini_b.render(f"mapas: {', '.join(mapas) if mapas else '—'}    ·    próx. spawn: ({prox_x:.0f}, 0)", True, SUAVE2)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 384)))
    t = f_mini_b.render("AMCL desliga o SLAM sozinho (brigam pelo mapa) · fechar o dashboard ENCERRA tudo.", True, AMBAR)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 406)))
    no_ar = ", ".join(cadeiras_rodando()) if cadeiras_rodando() else "nenhuma"
    t = f_mini_b.render(f"cadeiras no ar: {no_ar}", True, SUAVE)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 428)))

    r = rets["iniciar"]
    pygame.draw.rect(img, ACENTO, r, border_radius=10)
    t = f_btn.render("INICIAR CADEIRA", True, PRETO)
    img.blit(t, t.get_rect(center=r.center))

    r = rets["parar"]
    pygame.draw.rect(img, CARD, r, border_radius=10)
    pygame.draw.rect(img, AMBAR, r, border_radius=10, width=2)
    t = f_btn.render(f"PARAR '{nav2_codename[:10].upper()}'", True, AMBAR)
    img.blit(t, t.get_rect(center=r.center))

    r = rets["fechar"]
    pygame.draw.rect(img, CARD_ALT, r, border_radius=10)
    pygame.draw.rect(img, LINHA, r, border_radius=10, width=1)
    t = f_btn.render("FECHAR", True, SUAVE)
    img.blit(t, t.get_rect(center=r.center))

    tela.blit(img, (0, 0))


def _modal_saida_rects():
    janela = pygame.Rect(0, 0, 600, 330)
    janela.center = (LARGURA // 2, ALTURA // 2)
    larg_btn = 250
    xb = janela.centerx - larg_btn // 2
    return {
        "manter": pygame.Rect(xb, janela.y + 128, larg_btn, 46),
        "restaurar": pygame.Rect(xb, janela.y + 184, larg_btn, 46),
        "cancelar": pygame.Rect(xb, janela.y + 246, 140, 40),
    }


def construir_modal_saida():
    global _modal_imagem

    img = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    img.fill((0, 0, 0, 150))

    janela = pygame.Rect(0, 0, 600, 330)
    janela.center = (LARGURA // 2, ALTURA // 2)
    pygame.draw.rect(img, CARD, janela, border_radius=14)
    pygame.draw.rect(img, ACENTO, janela, border_radius=14, width=2)
    pygame.draw.rect(img, ACENTO, (janela.x, janela.y, janela.w, 5),
                     border_top_left_radius=14, border_top_right_radius=14)

    t = f_tit.render("FECHAR DASHBOARD?", True, ACENTO)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 42)))
    t = f_rod.render("As alterações aplicadas no código da NARA ficam salvas.", True, BRANCO)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 74)))
    t = f_mini.render("Escolha manter as mudanças ou restaurar os originais antes de fechar.", True, SUAVE)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 96)))
    t = f_mini.render("SIM/NAV2 em execução serão encerrados ao fechar.", True, AMBAR)
    img.blit(t, t.get_rect(center=(janela.centerx, janela.y + 114)))

    rets = _modal_saida_rects()

    r = rets["manter"]
    pygame.draw.rect(img, ACENTO, r, border_radius=10)
    t = f_btn.render("FECHAR E MANTER", True, PRETO)
    img.blit(t, t.get_rect(center=r.center))

    r = rets["restaurar"]
    pygame.draw.rect(img, CARD, r, border_radius=10)
    pygame.draw.rect(img, AMBAR, r, border_radius=10, width=2)
    t = f_btn.render("RESTAURAR E FECHAR", True, AMBAR)
    img.blit(t, t.get_rect(center=r.center))

    r = rets["cancelar"]
    pygame.draw.rect(img, CARD_ALT, r, border_radius=10)
    pygame.draw.rect(img, LINHA, r, border_radius=10, width=1)
    t = f_btn.render("CANCELAR", True, SUAVE)
    img.blit(t, t.get_rect(center=r.center))

    _modal_imagem = img


def desenhar_modal_saida():
    if _modal_imagem is None:
        construir_modal_saida()
    tela.blit(_modal_imagem, (0, 0))


def main():
    global modo, msg, msg_ts, confirmar_saida, modal_visual
    global nav2_rviz, nav2_slam, nav2_amcl, nav2_codename, nav2_mapa
    global modal_nav2, campo_foco
    # Rede de segurança: garante que SIM/NAV2 headless não fiquem órfãos
    # se o dashboard for fechado pelo X, SIGINT (Ctrl+C) ou SIGTERM.
    # Idempotente: pode ser chamado várias vezes sem efeito colateral.
    atexit.register(encerrar_tudo_ao_sair)
    try:
        signal.signal(signal.SIGINT, _tratar_sinal_saida)
        signal.signal(signal.SIGTERM, _tratar_sinal_saida)
        # Fechar o terminal manda SIGHUP: sem handler, o dashboard morreria
        # sem cleanup e o headless ficava órfão (filhos estão em outra sessão
        # por causa do start_new_session, então nem o SIGHUP os atinge).
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, _tratar_sinal_saida)
    except Exception:
        pass
    sincronizar_do_codigo()
    aplicar_estado_salvo()

    ret_acoes = None
    rodando = True
    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                if not confirmar_saida:
                    confirmar_saida = True
                continue

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos = evento.pos

                if confirmar_saida:
                    rets = _modal_saida_rects()
                    if rets["manter"].collidepoint(pos):
                        encerrar_tudo_ao_sair()
                        rodando = False
                    elif rets["restaurar"].collidepoint(pos):
                        encerrar_tudo_ao_sair()
                        restaurar()
                        rodando = False
                    elif rets["cancelar"].collidepoint(pos):
                        confirmar_saida = False
                    continue

                # Botão de troca de robô (CAMARO): abre o dashboard
                # original do CAMARO e fecha este
                if _robot_btn_rect().collidepoint(pos):
                    if alternar_dashboard():
                        encerrar_tudo_ao_sair()
                        rodando = False
                    continue

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

                # Painel NAV2 OPTIONS (toggles + campos + iniciar/parar)
                if modal_nav2:
                    rets = _modal_nav2_rects()
                    if rets["rviz"].collidepoint(pos):
                        nav2_rviz = not nav2_rviz
                        msg_ts = time.strftime("%H:%M:%S")
                    elif rets["slam"].collidepoint(pos):
                        nav2_slam = not nav2_slam
                        if nav2_slam and nav2_amcl:
                            nav2_amcl = False
                            msg = "[NAV2] SLAM ON -> AMCL OFF (brigam pelo mapa)"
                            msg_ts = time.strftime("%H:%M:%S")
                        salvar_estado_ui()
                    elif rets["amcl"].collidepoint(pos):
                        nav2_amcl = not nav2_amcl
                        if nav2_amcl and nav2_slam:
                            nav2_slam = False
                            msg = "[NAV2] AMCL ON -> SLAM OFF (brigam pelo mapa)"
                            msg_ts = time.strftime("%H:%M:%S")
                        salvar_estado_ui()
                    elif rets["codename"].collidepoint(pos):
                        campo_foco = "codename"
                    elif rets["mapa"].collidepoint(pos):
                        campo_foco = "mapa" if nav2_amcl else None
                    elif rets["iniciar"].collidepoint(pos):
                        campo_foco = None
                        iniciar_cadeira(nav2_codename, rviz=nav2_rviz,
                                        slam=nav2_slam, amcl=nav2_amcl,
                                        mapa=nav2_mapa if nav2_amcl else None)
                        salvar_estado_ui()
                    elif rets["parar"].collidepoint(pos):
                        campo_foco = None
                        parar_cadeira(nav2_codename)
                    elif rets["fechar"].collidepoint(pos):
                        campo_foco = None
                        modal_nav2 = False
                    else:
                        campo_foco = None
                    continue

                # Popup COM/SEM VISUAL (mundo, aberto pelo SIM)
                if modal_visual is not None:
                    rets = _modal_visual_rects()
                    if rets["com"].collidepoint(pos):
                        iniciar_simulacao(visual=True)
                        modal_visual = None
                    elif rets["sem"].collidepoint(pos):
                        iniciar_simulacao(visual=False)
                        modal_visual = None
                    elif rets["cancelar"].collidepoint(pos):
                        modal_visual = None
                    continue

                # Botões de ação: sim / nav2 options / restaurar
                if ret_acoes is not None:
                    if ret_acoes["sim"].collidepoint(pos):
                        if sim_rodando():
                            parar_simulacao()
                        else:
                            modal_visual = "sim"
                        continue
                    if ret_acoes["nav2"].collidepoint(pos):
                        campo_foco = None
                        modal_nav2 = True
                        continue
                    if ret_acoes["restaurar"].collidepoint(pos):
                        restaurar()
                        sincronizar_do_codigo()
                        continue

            if evento.type == pygame.KEYDOWN and modal_nav2 and campo_foco:
                if evento.key == pygame.K_ESCAPE:
                    campo_foco = None
                elif evento.key == pygame.K_RETURN:
                    campo_foco = None
                    salvar_estado_ui()
                elif evento.key == pygame.K_BACKSPACE:
                    if campo_foco == "codename":
                        nav2_codename = nav2_codename[:-1]
                    else:
                        nav2_mapa = nav2_mapa[:-1]
                else:
                    ch = evento.unicode.lower()
                    if campo_foco == "codename":
                        if ch in "abcdefghijklmnopqrstuvwxyz0123456789_" and len(nav2_codename) < 16:
                            nav2_codename += ch
                    else:
                        if ch in "abcdefghijklmnopqrstuvwxyz0123456789_-" and len(nav2_mapa) < 32:
                            nav2_mapa += ch
                continue

        ret_acoes = renderizar()
        if confirmar_saida:
            desenhar_modal_saida()
        if modal_visual is not None:
            desenhar_modal_visual()
        if modal_nav2:
            desenhar_modal_nav2()
        pygame.display.flip()
        clock.tick(60)

    # Caminho normal de saída (X + FECHAR... ou CAMARO): atexit também
    # chamaria, mas encerrar aqui garante que o Gazebo/RViz morram antes
    # do pygame.quit(), sem deixar órfão headless.
    try:
        encerrar_tudo_ao_sair()
    finally:
        pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()