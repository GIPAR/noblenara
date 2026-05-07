import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node


def generate_launch_description():
    # Paths
    pkg_share = get_package_share_directory('smartwheelchair')
    params_file = LaunchConfiguration('params_file')

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_share, 'config', 'nav2_params.yaml'),
        description='Full path to the ROS2 parameters file'
    )

    # Nodes that you need
    controller_server = LifecycleNode(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[params_file],
        namespace='',
        remappings=[('/cmd_vel', '/noblenara/cmd_vel/raw')]
    )

    planner_server = LifecycleNode(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        namespace='',
        parameters=[params_file]
    )

    bt_navigator = LifecycleNode(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        namespace='',
        parameters=[params_file]
    )

    behavior_server = LifecycleNode(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        namespace='',
        parameters=[params_file],
        remappings=[('/cmd_vel', '/noblenara/cmd_vel/raw')]
    )

    collision_monitor = LifecycleNode(
        package='nav2_collision_monitor',
        executable='collision_monitor',
        name='collision_monitor',
        output='screen',
        namespace='',
        parameters=[params_file]
    )

    # Lifecycle manager – make sure the node_name matches ros__parameters key
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        namespace='',
        parameters=[params_file,
                    {'autostart': True},
                    {'node_names': [
                        'controller_server',
                        'planner_server',
                        'bt_navigator',
                        'behavior_server',
                        'collision_monitor'
                    ]}]
    )

    return LaunchDescription([
        declare_params_file_cmd,
        controller_server,
        planner_server,
        bt_navigator,
        behavior_server,
        collision_monitor,
        lifecycle_manager
    ])