import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.conditions import IfCondition
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node, PushROSNamespace, SetParameter
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    # Setup Inicial
    pkg_share = get_package_share_directory('smartwheelchair')
    #robot_codename = LaunchConfiguration("robot_codename")
    params_file = LaunchConfiguration('params_file')
    map_file = LaunchConfiguration('map_file')
    
    condition=IfCondition(PythonExpression(["'", map_file, "' != 'none'"]))
    notcondition=IfCondition(PythonExpression(["'", map_file, "' == 'none'"]))

    # Quando implementar múltiplos robôs colocar o rewritten YamL aqui (da mesma forma que está no launch da simulação)
    configured_file = params_file

    # Nós - Nav2
    Nav2_Nodes = GroupAction(
        actions=[
            SetParameter('use_sim_time', False),
            #PushROSNamespace(namespace=['/noblenara/', robot_codename]),
            
            # Publica o mapa salvo no tópico /map, para o AMCL e o costmap global
            Node(
                condition=condition,
                package='nav2_map_server',
                executable='map_server',
                output='screen',
                parameters=[configured_file, {'yaml_filename': map_file}],
            ),

            # Estima a pose do robô dentro do mapa publicado pelo map_server
            Node(
                condition=condition,
                package='nav2_amcl',
                executable='amcl',
                output='screen',
                parameters=[configured_file],
            ),

            Node(
                package='nav2_controller',
                executable='controller_server',
                output='screen',
                parameters=[configured_file],
                remappings=[('cmd_vel', '/noblenara/cmd_vel/raw')],
            ),
            
            Node(
                package='nav2_planner',
                executable='planner_server',
                output='screen',
                parameters=[configured_file],
            ),
            
            Node(
                package='nav2_bt_navigator',
                executable='bt_navigator',
                output='screen',
                parameters=[configured_file],
            ),
            
            Node(
                package='nav2_behaviors',
                executable='behavior_server',
                output='screen',
                parameters=[configured_file],
                remappings=[('cmd_vel', '/noblenara/cmd_vel/raw')],
            ),
            
            Node(
                package='nav2_collision_monitor',
                executable='collision_monitor',
                output='screen',
                parameters=[configured_file],
            ),
            
            # Lifecycle manager com SLAM
            Node(
                condition=notcondition,
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_navigation',
                output='screen',
                parameters=[
                            {'autostart': True},
                            {'use_sim_time': False},
                            {'node_names': [
                                'controller_server',
                                'planner_server',
                                'bt_navigator',
                                'behavior_server',
                                'collision_monitor',
                            ]}],
            ),
            
            # Lifecycle manager com AMCL
            Node(
                condition=condition,
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_navigation',
                output='screen',
                parameters=[
                            {'autostart': True},
                            {'use_sim_time': False},
                            {'node_names': [
                                'map_server',
                                'amcl',
                                'controller_server',
                                'planner_server',
                                'bt_navigator',
                                'behavior_server',
                                'collision_monitor',
                            ]}],
            )
            
            
        ]
    )

    return LaunchDescription([
        #DeclareLaunchArgument('robot_codename', default_value='alfa'),
        DeclareLaunchArgument( 'params_file', default_value=os.path.join(pkg_share, 'config', 'nav2_params.yaml'), description='Caminho completo para o arquivo de parâmetros do Nav2'),
        DeclareLaunchArgument( 'map_file', default_value=os.path.join('none'), description='Caminho completo para o .yaml do mapa salvo (gerado pelo map_saver_cli)'),
        Nav2_Nodes,
    ])
