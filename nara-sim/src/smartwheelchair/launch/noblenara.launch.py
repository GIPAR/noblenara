import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Pega o diretório compartilhado do pacote
    pkg_share = get_package_share_directory('smartwheelchair')
    
    # Namespace do Robo
    robot_codename = LaunchConfiguration("robot_codename")
    
    # Setta o resource path do Gazebo
    gazebo_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=pkg_share
    )
    
    # Setup do arquivo XACRO
    xacro_file = os.path.join(pkg_share, 'urdf', 'narawheelchair.xacro')
    robot_description_command = Command([
        'xacro ', xacro_file,
        ' robot_name:=', robot_codename
    ])
    
    # Setup do Filtro de Laser
    filter_config = os.path.join(pkg_share, 'config', 'laser_filter.yaml')
    
    laser_filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        parameters=[
            filter_config,
            {'filter1.params.box_frame': ['noblenara/', robot_codename, '/robot_footprint']}
        ],
        remappings=[ 
            ('scan', ['/noblenara/', robot_codename ,'/scan']),
            ('scan_filtered', ['/noblenara/', robot_codename,'/scan_filtered']) 
        ],
        output='screen'
    )
    

    # Robot state publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {'robot_description': robot_description_command},
            {'use_sim_time': True},
            {'frame_prefix': ['noblenara/', robot_codename, '/']}],
        remappings=[ ('/joint_states', ['/noblenara/', robot_codename ,'/joint_states']), ('/robot_description', ['/noblenara/', robot_codename ,'/robot_description']) ],
        output='screen'
    )
    
    
    # Criar o robô no gazebo
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', 
                  '-name', ['noblenara/' , robot_codename],
                  '-x', '0.0', 
                  '-y', '0.0', 
                  '-z', '0.1'],
        remappings=[ ('/robot_description', ['/noblenara/', robot_codename ,'/robot_description']) ],
        output='screen'
    )
    
    
    # ROS_GZ_BRIDGE NODE : Faz a ponte entre os tópicos do gazebo e do ROS2
    # O Gazebo que lida com os tópicos, diferentemente do ROS1, a ponte é necessária
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Pontes Globais
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            
            # Pontes do Joint States
            ['/noblenara/', robot_codename,'/joint_states@sensor_msgs/msg/JointState@gz.msgs.Model'],
            
            # Ponte do cmd_vel
            ['/noblenara/', robot_codename,'/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist'],

            # Ponte dos Sensores
            ['/noblenara/', robot_codename,'/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry'],
            ['/noblenara/', robot_codename,'/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'],
            
            # Ponte das Câmeras
            ['/noblenara/', robot_codename,'/camera_link/image@sensor_msgs/msg/Image[gz.msgs.Image'],
            ['/noblenara/', robot_codename,'/camera_link/depth_image@sensor_msgs/msg/Image[gz.msgs.Image'],
            ['/noblenara/', robot_codename,'/camera_link/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked'], #PointCLoudPacked é a versão comprimida
            ['/noblenara/', robot_codename,'/camera_user@sensor_msgs/msg/Image[gz.msgs.Image'], 
            ['/noblenara/', robot_codename,'/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'],
            ['/noblenara/', robot_codename,'/camera_link/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'],
          ],
        output='screen'
    )
    
    return LaunchDescription([
        gazebo_resource_path,
        DeclareLaunchArgument('robot_codename', default_value='alfa'),
        robot_state_publisher_node,
        spawn_entity,
        bridge,
        laser_filter_node
    ])
