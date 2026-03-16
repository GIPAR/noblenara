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
    
    # XACRO file setup
    xacro_file = os.path.join(pkg_share, 'urdf', 'narawheelchair.xacro')
    robot_description_command = Command(['xacro ', xacro_file])
    
    # Laser Filter Setup
    filter_config = os.path.join(pkg_share, 'config', 'laser_filter.yaml')
    
    laser_filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        parameters=[filter_config],
        remappings=[ ('scan', '/noblenara/scan'), ('scan_filtered', '/noblenara/scan_filtered') 
        ],
        output='screen'
    )
    
    # Robot state publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {'robot_description': robot_description_command},
            {'use_sim_time': True}],
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
    
    
    # ROS_GZ_BRIDGE NODE : Faz a ponte entre os tópicos do gazebo e do ROS2
    # O Gazebo que lida com os tópicos, diferentemente do ROS1, a ponte é necessária
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Bridge ROS 2's /cmd_vel to Gazebo's /noblenara/cmd_vel
            '/noblenara/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',

            # Bridge Gazebo's /noblenara/odom to ROS 2's /noblenara/odom
            '/noblenara/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            
            # Bridge Lidar Scan (Gazebo -> ROS2)
            '/noblenara/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
        
            # Clock bridge
            '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock',

            # tf bridge
            '/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',

            # Joint States bridge
            '/world/default/model/wheelchair/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model',
            
            # ZED 2i Camera (RGB-D): RGB image
            '/noblenara/camera_link/image@sensor_msgs/msg/Image@gz.msgs.Image',
            
            # ZED 2i Camera (RGB-D): Depth image
            '/noblenara/camera_link/depth_image@sensor_msgs/msg/Image@gz.msgs.Image',
            
            # ZED 2i Camera (RGB-D): 3D point cloud data
            '/noblenara/camera_link/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked', #PointCLoudPacked é a versão comprimida
        
            # Câmera de Usuário: RGB image only | Câmera da Interface/Que aponta pro usuário da cadeira sentado
            '/noblenara/camera_user@sensor_msgs/msg/Image@gz.msgs.Image', 
            
            #Parâmetros das Câmeras | Parâmetros da Câmera do usuário, caso tivesse mais de uma câmera com o msm plugin todas as info ficariam neste mesmo tópico (10/09)
            '/noblenara/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
            
            #Parâmetros da Câmera ZED | Camera Navegação/Link
            '/noblenara/camera_link/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo'
          ],
        remappings=[
            ('/world/default/model/wheelchair/joint_state', '/joint_states'),
        ],
        output='screen'
    )
    
    return LaunchDescription([
        gazebo_resource_path,
        robot_state_publisher_node,
        spawn_entity,
        bridge,
        laser_filter_node
    ])
