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
    
    
    # 3. ROS_GZ_BRIDGE NODE
    # ==================================
    # This is the new part. It connects Gazebo topics to ROS 2 topics.
    # Tenha certeza que os links estão os mesmos que o .gazebo
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
        output='screen'
)
    
    return LaunchDescription([
        gazebo_resource_path,
        robot_state_publisher_node,
        spawn_entity,
        bridge #for the ros2 bridge of topics from Gazebo
    ])
