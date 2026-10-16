import os
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('smartwheelchair')

    # 1. XACRO/URDF
    xacro_file = os.path.join(pkg_share, 'urdf', 'narawheelchair.xacro')
    robot_description_command = Command(['xacro ', xacro_file])

    # 2. Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {'robot_description': robot_description_command},
            {'use_sim_time': False}
        ],
        output='screen'
    )

    # 3. RPLiDAR
    sllidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        parameters=[
            {'serial_port': '/dev/lidar'},
            {'frame_id': 'hokuyo_link'},
            {'serial_baudrate': 256000},
            {'angle_compensate': True}
        ],
        remappings=[('scan', '/noblenara/scan')],
        output='screen'
    )

    # 4. Filtro RPLiDAR
    filter_config = os.path.join(pkg_share, 'config', 'laser_filter.yaml')

    laser_filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        parameters=[filter_config],
        remappings=[
            ('scan', '/noblenara/scan'),
            ('scan_filtered', '/noblenara/scan_filtered')
        ],
        output='screen'
    )

    # 5. EKF (robot_localization) — funde /noblenara/odom (encoder) + /noblenara/imu/data
    # Publica em /odometry/filtered, que é o que o nav2_params.yaml espera.
    # ATENÇÃO: depende de um nó (fora deste pacote) publicando /noblenara/odom
    # e /noblenara/imu/data a partir do ESP32 — confirme que ele está sendo lançado
    # em algum outro launch file antes deste, ou adicione aqui.
    ekf_config = os.path.join(pkg_share, 'config', 'ekf.yaml')

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config, {'use_sim_time': False}],
    )

    return LaunchDescription([
        robot_state_publisher_node,
        sllidar_node,
        laser_filter_node,
        ekf_node,
    ])
