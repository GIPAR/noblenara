import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_name = 'smartwheelchair'
    pkg_share = get_package_share_directory(pkg_name)
    
    world_file = os.path.join(pkg_share, 'worlds', 'museum.world')

    models_path = os.path.join(pkg_share, 'models')

    filter_config = os.path.join(pkg_share, 'config', 'laser_filter.yaml')

    laser_filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        parameters=[filter_config],
        remappings=[
            ('scan', '/scan'),                
            ('scan_filtered', '/scan_filtered') 
        ],
        output='screen'
    )

    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=':'.join([
            os.path.join(pkg_share, '..'), 
            models_path                    
        ])
    )

    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    robot_desc = xacro.process_file(xacro_file).toxml()

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),

        launch_arguments={'gz_args': f'-r "{world_file}" -v 4'}.items(),
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'smartwheelchair',
            '-x', '0.0',  
            '-y', '0.0',
            '-z', '0.3'   
        ],
        output='screen'
    )

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}]
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'
        ],
        output='screen'
    )

    tf_fix = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments = ['0', '0', '0', '0', '0', '0', 'hokuyo_link', 'smartwheelchair/base_footprint/gpu_lidar'],
        output='screen'
    )

    return LaunchDescription([
        gz_resource_path,
        gazebo,
        rsp,
        spawn,
        bridge,
        tf_fix,
        laser_filter_node 
    ])