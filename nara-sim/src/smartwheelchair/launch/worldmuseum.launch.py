#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

def generate_launch_description():
    # Get package share directory
    pkg_share = FindPackageShare('smartwheelchair').find('smartwheelchair')
    
    # Set Gazebo resource path - be more explicit
    gazebo_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=PathJoinSubstitution([pkg_share, 'models'])
    )
    
    # Declare launch arguments
    world_file_arg = DeclareLaunchArgument(
        'world_file',
        default_value=PathJoinSubstitution([pkg_share, 'worlds', 'museum_default.world']),
        description='Full path to world file'
    )

    # COM VISUAL (gui:=true, padrão) abre a janela do Gazebo;
    # SEM VISUAL (gui:=false) roda só o servidor (terminal)
    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Abrir janela do Gazebo (true) ou rodar só o servidor (false)'
    )
    
    # Get the world file path
    world_file = LaunchConfiguration('world_file')
    
    # Launch Gazebo with the world
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', '--verbose', '4', world_file],
        name='gazebo_server',
        output='screen'
    )
    
    # Launch Gazebo client (GUI) — só quando gui:=true
    gazebo_client = ExecuteProcess(
        cmd=['gz', 'sim', '-g'],
        name='gazebo_client',
        output='screen',
        condition=IfCondition(PythonExpression(["'", LaunchConfiguration('gui'), "' == 'true'"])),
    )
    
    global_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
        ],
        name='ros_gz_global_bridge',
        output='screen',
    )
    
    return LaunchDescription([
        gazebo_resource_path,
        world_file_arg,
        gui_arg,
        gazebo_server,
        gazebo_client,
        global_bridge,
    ])
