import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    my_pkg_share = get_package_share_directory('smartwheelchair')
    slam_pkg_share = get_package_share_directory('slam_toolbox')
    
    config_file = os.path.join(my_pkg_share, 'config', 'mapper_params_online_async.yaml')

    start_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(slam_pkg_share, 'launch', 'online_async_launch.py')),
        launch_arguments={
            'slam_params_file': config_file,
            'use_sim_time': 'true'
        }.items()
    )

    return LaunchDescription([
        start_slam
    ])