#!/usr/bin/env python3
"""
NOBLE NARA - Dashboard de Configuração
Inicia o dashboard gráfico para configurar a simulação
"""

import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory('smartwheelchair')
    
    # Script do dashboard instalado no share do pacote
    configurador_script = os.path.join(pkg_share, 'scripts', 'noble_config.py')
    
    configurador = ExecuteProcess(
        cmd=['python3', configurador_script],
        output='screen',
    )
    
    info = LogInfo(msg=[
        'NOBLE NARA - Dashboard de Configuração\n',
        'Selecione as configurações de desempenho na interface.'
    ])
    
    return LaunchDescription([
        info,
        configurador,
    ])
