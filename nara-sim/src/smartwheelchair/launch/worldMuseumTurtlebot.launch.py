#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # =========================
    # Package share directories
    # =========================
    pkg_smartwheelchair = get_package_share_directory('smartwheelchair')
    pkg_turtlebot4_description = get_package_share_directory('turtlebot4_description')
    pkg_turtlebot4_gz_bringup = get_package_share_directory('turtlebot4_gz_bringup')
    pkg_irobot_create_description = get_package_share_directory('irobot_create_description')
    pkg_irobot_create_gz_bringup = get_package_share_directory('irobot_create_gz_bringup')

    # =========================
    # Gazebo resource paths
    # =========================
    resource_paths = [
        os.path.join(pkg_smartwheelchair, 'models'),
        os.path.join(pkg_smartwheelchair, 'worlds'),
        pkg_turtlebot4_description,
        pkg_turtlebot4_gz_bringup,
        pkg_irobot_create_description,
        pkg_irobot_create_gz_bringup,
    ]

    existing_gz_path = os.environ.get('GZ_SIM_RESOURCE_PATH')
    if existing_gz_path:
        resource_paths.append(existing_gz_path)

    gazebo_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=':'.join(resource_paths)
    )

    # =========================
    # Launch arguments
    # =========================
    world_file_arg = DeclareLaunchArgument(
        'world_file',
        default_value=os.path.join(pkg_smartwheelchair, 'worlds', 'museum_finder.world'),
        description='Full path to world file'
    )

    world_file = LaunchConfiguration('world_file')

    # =========================
    # Gazebo server
    # =========================
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', '--verbose', '4', world_file],
        name='gazebo_server',
        output='screen'
    )

    # =========================
    # Gazebo client (GUI)
    # =========================
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