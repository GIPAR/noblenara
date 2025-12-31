#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node


def generate_launch_description():
    # Get package share directory for smartwheelchair
    pkg_share = FindPackageShare('smartwheelchair').find('smartwheelchair')

    # Declare launch arguments for map and rviz files
    map_yaml_file = DeclareLaunchArgument(
        'map_yaml_file',
        default_value=PathJoinSubstitution([pkg_share, 'maps', 'office.yaml']),
        description='Full path to map yaml file to load'
    )
    
    rviz_config_file = DeclareLaunchArgument(
        'rviz_config_file',
        default_value=PathJoinSubstitution([pkg_share, 'config', 'smartwheelchair.rviz']),
        description='Full path to rviz config file to use'
    )
    
    use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )
    
    # Map server node
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'yaml_filename': LaunchConfiguration('map_yaml_file'),
            'frame_id': 'map',
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }]
    )
    
    # Configure map server lifecycle
    configure_map_server = ExecuteProcess(
        cmd=['ros2', 'lifecycle', 'set', '/map_server', 'configure'],
        output='screen'
    )
    
    # Activate map server lifecycle
    activate_map_server = ExecuteProcess(
        cmd=['ros2', 'lifecycle', 'set', '/map_server', 'activate'],
        output='screen'
    )
    
    # RViz2 node with configuration file
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', LaunchConfiguration('rviz_config_file')],
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }],
        output='screen'
    )
    
    return LaunchDescription([
        map_yaml_file,
        rviz_config_file,
        use_sim_time,
        
        # Start map server
        map_server_node,
        
        # Configure map server after 2 seconds
        TimerAction(
            period=2.0,
            actions=[configure_map_server]
        ),
        
        # Activate map server after 3 seconds
        TimerAction(
            period=3.0,
            actions=[activate_map_server]
        ),
        
        # Start RViz2 after 4 seconds to ensure map server is ready
        TimerAction(
            period=4.0,
            actions=[rviz_node]
        )
    ])
