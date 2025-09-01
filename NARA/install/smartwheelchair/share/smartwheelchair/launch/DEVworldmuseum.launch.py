#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
import os

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
        default_value=PathJoinSubstitution([pkg_share, 'worlds', 'museum.world']),
        description='Full path to world file'
    )
    
    # Get the world file path
    world_file = LaunchConfiguration('world_file')
    
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
    
    return LaunchDescription([
        gazebo_resource_path,
        world_file_arg,
        gazebo_server,
        gazebo_client,
    ])
