import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, FindPackageShare
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackage

def generate_launch_description():
    return LaunchDescription([
        # Arguments
        DeclareLaunchArgument('x', default_value='0'),
        DeclareLaunchArgument('y', default_value='0'),
        DeclareLaunchArgument('z', default_value='0'),
        DeclareLaunchArgument('roll', default_value='0'),
        DeclareLaunchArgument('pitch', default_value='0'),
        DeclareLaunchArgument('yaw', default_value='0'),
        DeclareLaunchArgument('verbose', default_value='true'),

        # Include other launch files
        IncludeLaunchDescription(
            FindPackageShare('smartwheelchair').find('launch') + '/b400_description.launch.py'
        ),

        # World File for Gazebo
        DeclareLaunchArgument('world_file', default_value=FindPackageShare('smartwheelchair').find('worlds/museum.world')),

        # Launch Gazebo with World
        IncludeLaunchDescription(
            FindPackageShare('gazebo_ros').find('launch') + '/gzserver.launch.py',
            launch_arguments={'world_name': LaunchConfiguration('world_file'),
                              'use_sim_time': 'true',
                              'debug': 'false',
                              'gui': 'true'}.items()
        ),

        # Robot Description
        Node(
            package='xacro',
            executable='xacro',
            name='xacro',
            output='screen',
            arguments=['--inorder', FindPackageShare('smartwheelchair').find('urdf/b400wheelchair.xacro')],
        ),

        # Spawn Robot in Gazebo
        Node(
            package='gazebo_ros',
            executable='spawn_model',
            name='urdf_spawner',
            respawn=False,
            output='screen',
            arguments=['-urdf', '-param', 'robot_description', '-model', 'b400wheelchair',
                       '-x', LaunchConfiguration('x'),
                       '-y', LaunchConfiguration('y'),
                       '-z', LaunchConfiguration('z'),
                       '-R', LaunchConfiguration('roll'),
                       '-P', LaunchConfiguration('pitch'),
                       '-Y', LaunchConfiguration('yaw')]
        ),
    ])

