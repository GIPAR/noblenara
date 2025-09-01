import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, FindPackageShare
from launch_ros.actions import Node

def generate_launch_description():
    # Define the package name where your .xacro file is located
    pkg_share = FindPackageShare('smartwheelchair').find('smartwheelchair')

    # Define the path to the xacro file using FindPackageShare and PathJoinSubstitution
    urdf_file = PathJoinSubstitution([pkg_share, 'urdf', 'b400wheelchair.xacro'])

    # Define the spawn model node for spawning the wheelchair model in the ROS 2 simulation
    spawn_model_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': urdf_file
        }]
    )

    return LaunchDescription([
        # Add a log info to confirm that the launch file has been executed
        LogInfo(
            condition=LaunchConfiguration('print_info'),
            msg="Wheelchair model spawn launch started."
        ),
        # Run the robot_state_publisher to spawn the model
        spawn_model_node,
    ])
