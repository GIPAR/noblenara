#!/usr/bin/env python3
"""SmartWorld: mundo + camada V2I/MQTT das portas num launch so.

Sobe Gazebo (server+GUI), ponte do /clock, ponte ROS->GZ das juntas e os
nos door_requester (cadeira) e door_infra (parede). O Mosquitto e a cadeira
(noblenara.launch.py) continuam por fora: broker e robo sobem a parte.
"""

from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument, SetEnvironmentVariable, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
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
        default_value=PathJoinSubstitution([pkg_share, 'worlds', 'smartworld.sdf']),
        description='Full path to world file'
    )
    robot_codename_arg = DeclareLaunchArgument(
        'robot_codename',
        default_value='alfa',
        description='Codename do robo (namespace da odometria)'
    )

    # Get the world file path
    world_file = LaunchConfiguration('world_file')
    robot_codename = LaunchConfiguration('robot_codename')

    # Launch Gazebo with the world
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', '--verbose', '4', world_file],
        name='gazebo_server',
        output='screen'
    )

    # Launch Gazebo client (GUI)
    gazebo_client = ExecuteProcess(
        cmd=['gz', 'sim', '-g'],
        name='gazebo_client',
        output='screen'
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

    # Ponte ROS->GZ das juntas (atrasada: precisa do servidor no ar)
    joint_bridge = Node(
        package='ros_gz_bridge',
        executable='bridge_node',
        name='smartdoor_bridge',
        parameters=[{
            'config_file': PathJoinSubstitution([pkg_share, 'config', 'smartdoor_bridge.yaml']),
            'use_sim_time': True,
        }],
        output='screen',
    )

    requester = Node(
        package='smartwheelchair',
        executable='door_requester.py',
        name='door_requester',
        parameters=[{'robot_codename': robot_codename, 'use_sim_time': True}],
        output='screen',
    )

    infra = Node(
        package='smartwheelchair',
        executable='door_infra.py',
        name='door_infra',
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    smart_delayed = TimerAction(
        period=8.0,
        actions=[joint_bridge, requester, infra],
    )

    return LaunchDescription([
        gazebo_resource_path,
        world_file_arg,
        robot_codename_arg,
        gazebo_server,
        gazebo_client,
        global_bridge,
        smart_delayed,
    ])
