import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Get package directory
    pkg_share = get_package_share_directory('smartwheelchair')
    
    # Set Gazebo resource path
    gazebo_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=pkg_share
    )
    
    # Path to XACRO file
    xacro_file = os.path.join(pkg_share, 'urdf', 'b400wheelchair.xacro')
    
    # Process XACRO file
    robot_description_command = Command(['xacro ', xacro_file])
    
    # Robot state publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description_command}],
        output='screen'
    )
    
    # Spawn entity in Gazebo
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', 
                  '-name', 'wheelchair',
                  '-x', '0.0', 
                  '-y', '0.0', 
                  '-z', '0.1'],
        output='screen'
    )
    
    return LaunchDescription([
        gazebo_resource_path,
        robot_state_publisher_node,
        spawn_entity
    ])
