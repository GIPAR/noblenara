import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration

def rviz_configurer(context, *args, **kwargs):
    
    # Setup Inicial do Configurador
    pkg_share = get_package_share_directory('smartwheelchair')
    codename = LaunchConfiguration('robot_codename').perform(context)
    rviz_config_file = os.path.join( pkg_share, 'config', 'slam_config.rviz' )
    rviz_rewrited_config_file = '/tmp/slam_rewrited_config.rviz'
    
    # Ações para leitura e substituição no arquivo
    with open(rviz_config_file, 'r') as f:
        content = f.read()
        content = content.replace('alfa', codename)
    
    with open(rviz_rewrited_config_file, 'w') as f:
        f.write(content)
    
    rviz_launch_node = Node(
        package='rviz2',
        executable='rviz2',
        name=['noblenara_', codename, '_rviz2'],
        arguments=['-d', rviz_rewrited_config_file],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )
    
    return [rviz_launch_node]

def generate_launch_description():

    # Setup Inicial
    pkg_share = get_package_share_directory('smartwheelchair')
    
    config_file = os.path.join( pkg_share, 'config', 'mapper_params_online_async.yaml' )
    
    robot_codename = LaunchConfiguration("robot_codename")
    slam_node_name = ['noblenara/', robot_codename, '/slam_toolbox']
    
    # Configuração dos Nós
    slam_launch_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        namespace=['noblenara/', robot_codename],
        parameters=[
            config_file,
            {
                'use_sim_time': True,
                'odom_frame': ['noblenara/', robot_codename, '/odom'],
                'base_frame': ['noblenara/', robot_codename, '/robot_footprint'],
                'scan_topic': ['/noblenara/', robot_codename, '/scan_filtered'],
                'map_frame':  ['noblenara/', robot_codename, '/map'],
            }
        ],
        remappings=[ ('/map', ['/noblenara/', robot_codename, '/map']), ('/map_metadata', ['/noblenara/', robot_codename, '/map_metadata']) ],
        output='screen'
    )
    
    # Slam Lifecycle para ativação automática
    slam_lifecycle = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name=['noblenara_', robot_codename, '_lifecycle_manager_slam_toolbox'],
        parameters=[{
            'autostart': True,
            'node_names': [slam_node_name],
            'bond_timeout': 0.0                         # Não verifica o estado da nó periodicamente
        }]
    )
    

    return LaunchDescription([
        slam_launch_node,
        DeclareLaunchArgument('robot_codename', default_value='alfa'),
        slam_lifecycle,
        OpaqueFunction(function=rviz_configurer)
        ])