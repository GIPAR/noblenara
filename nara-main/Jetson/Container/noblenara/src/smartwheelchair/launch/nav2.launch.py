import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('smartwheelchair')
    params_file = LaunchConfiguration('params_file')
    use_slam = LaunchConfiguration('use_slam')

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(pkg_share, 'config', 'nav2_params.yaml'),
            description='Caminho completo para o arquivo de parâmetros do Nav2 '
                         '(o caminho do mapa já vem definido dentro dele, em map_server.yaml_filename)'
        ),
        DeclareLaunchArgument(
            'use_slam',
            default_value='false',
            description='Se true, não sobe map_server/amcl — assume que o slam_toolbox '
                         'já está fornecendo /map ao vivo (rode slam.launch.py junto)'
        ),

        # --- Localização (mapa fixo) ---
        Node(
            package='nav2_map_server',
            executable='map_server',
            output='screen',
            parameters=[params_file],
            condition=UnlessCondition(use_slam),
        ),
        Node(
            package='nav2_amcl',
            executable='amcl',
            output='screen',
            parameters=[params_file],
            condition=UnlessCondition(use_slam),
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_localization',
            output='screen',
            parameters=[params_file],
            condition=UnlessCondition(use_slam),
        ),

        # --- Navegação ---
        Node(
            package='nav2_controller',
            executable='controller_server',
            output='screen',
            parameters=[params_file],
            remappings=[('cmd_vel', '/noblenara/cmd_vel/raw')],
        ),
        Node(
            package='nav2_planner',
            executable='planner_server',
            output='screen',
            parameters=[params_file],
        ),
        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            output='screen',
            parameters=[params_file],
        ),
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            output='screen',
            parameters=[params_file],
            remappings=[('cmd_vel', '/noblenara/cmd_vel/raw')],
        ),
        Node(
            package='nav2_collision_monitor',
            executable='collision_monitor',
            output='screen',
            parameters=[params_file],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[params_file],
        ),
    ])
