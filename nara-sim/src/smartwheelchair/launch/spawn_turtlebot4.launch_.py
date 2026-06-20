from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

from launch.substitutions import PathJoinSubstitution


def generate_launch_description():

    turtlebot4_description_launch = PathJoinSubstitution([
        get_package_share_directory('turtlebot4_description'),
        'launch',
        'robot_description.launch.py'
    ])

    turtlebot4_bridge_launch = PathJoinSubstitution([
        get_package_share_directory('turtlebot4_gz_bringup'),
        'launch',
        'ros_gz_bridge.launch.py'
    ])

    turtlebot4_nodes_launch = PathJoinSubstitution([
        get_package_share_directory('turtlebot4_gz_bringup'),
        'launch',
        'turtlebot4_nodes.launch.py'
    ])

    return LaunchDescription([

        # Publica robot_description
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                turtlebot4_description_launch
            ),
            launch_arguments={
                'model': 'standard',
                'use_sim_time': 'true'
            }.items()
        ),

        # Spawn do robô
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', 'turtlebot4',
                '-x', '0.0',
                '-y', '0.0',
                '-z', '0.10',
                '-Y', '0.0',
                '-topic', 'robot_description'
            ],
            output='screen'
        ),

        # Bridge ROS <-> Gazebo
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                turtlebot4_bridge_launch
            ),
            launch_arguments={
                'model': 'standard',
                'robot_name': 'turtlebot4',
                'dock_name': 'standard_dock',
                'namespace': ''
            }.items()
        ),

        # Nós do TurtleBot4
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                turtlebot4_nodes_launch
            ),
            launch_arguments={
                'model': 'standard'
            }.items()
        ),
    ])
