import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def rviz_configurer(context, *args, **kwargs):

    pkg_share = get_package_share_directory('smartwheelchair')
    codename = LaunchConfiguration('robot_codename').perform(context)
    rviz_config_file = os.path.join(pkg_share, 'config', 'nav2_config.rviz')
    rviz_rewrited_config_file = '/tmp/nav2_rewrited_config.rviz'

    with open(rviz_config_file, 'r') as f:
        content = f.read()
        content = content.replace('alfa', codename)

    with open(rviz_rewrited_config_file, 'w') as f:
        f.write(content)

    rviz_launch_node = Node(
        package='rviz2',
        executable='rviz2',
        name=['noblenara_', codename, '_rviz2'],
        arguments=['-d', rviz_rewrited_config_file],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    return [rviz_launch_node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('robot_codename', default_value='alfa'),
        OpaqueFunction(function=rviz_configurer)
    ])
