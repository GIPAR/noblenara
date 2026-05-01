import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    pkg_share = get_package_share_directory('smartwheelchair')
    slam_pkg = get_package_share_directory('slam_toolbox')

    config_file = os.path.join(
        pkg_share,
        'config',
        'mapper_params_online_async.yaml'
    )

    rviz_config_file = os.path.join(
        pkg_share,
        'config',
        'slam_config.rviz'
    )

    slam_launch = os.path.join(
        slam_pkg,
        'launch',
        'online_async_launch.py'
    )

    return LaunchDescription([

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(slam_launch),
            launch_arguments={
                'slam_params_file': config_file,
                'use_sim_time': 'true'
            }.items()
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': True}],
            output='screen'
        )

    ])