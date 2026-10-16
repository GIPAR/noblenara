import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('smartwheelchair')
    rviz_config_file = os.path.join(pkg_share, 'config', 'nav2_config.rviz')

    rviz_launch_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': False}],
        output='screen'
    )

    return LaunchDescription([
        rviz_launch_node
    ])