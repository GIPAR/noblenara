# Hardware Development

## Mapeamento e Análise de Hardware

### Hardware

b400 Ottobock Motorized Wheelchair

- Jetson AGX Orin 64GB Dev Kit
- Arduino Mega 2560
- Arduino Uno
- IMU MPU6050
- 2 H Bridge BTS 7960
- 2 Encoders zkp3808
- Zed 2i
- RPLidar A2

### Software

- Ubuntu 22 - Jammy
- Jetpack 6.2.1 (rev. 1)
    Adicionado DeepStream
- Container Micro-ROS
- Container Zed2i

## Firmware da ESP32

### Main-files

ESP32
  main.cpp micro-ROS file || Subscribes to /cmd_vel || serial transport config || main loop with executor spin
    publishes to /odom (odom from encoders) and /imu/data (imu readings) possibly /join_states or motor feedback
  Local tasks: Read encoders (via interrupts) IMU (12C, ~100Hz?), control motors, safety checks (timeouts, limits)
  Other files: Hardware interfaces (githubs), config/parameters file noblenara.config

Libraries
  IMU: Jeff Rowberg's I2Cdev
  Encoders: <https://github.com/madhephaestus/ESP32Encoder>

### Planning

Jetson Pins: <https://developer.nvidia.com/embedded/learn/jetson-agx-orin-devkit-user-guide/developer_kit_layout.html#automation-header-j42>

## Docker

ls /dev/ttyUSB*

### Agent MICRO-ROS

docker run -it \                            # -it Interactive terminal          ---> Removed the --rm (which removes it when it stops)
  --net=host \                              #Share network with host (Agent can communicate with ROS2 nodes)
  -v /dev:/dev \                            #Gives the container access to ALL devices on the host
  --privileged \                            #Give container full device access (alternative to individual --device)
  --name nomezaotopprocontainer \
  your_image_name

ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200

### Zed2i Container

sudo xhost +si:localuser:root               #"First of all, allow the container to access EGL display resources (required only once):" - Stereolabs

docker run --runtime nvidia -it --privileged --network=host --ipc=host --pid=host \
  --gpus all \
  -v /tmp/.X11-unix/:/tmp/.X11-unix \
  -v /dev:/dev \
  -v /dev/shm:/dev/shm \
  -v /usr/local/zed/resources/:/usr/local/zed/resources/ \
  -v /usr/local/zed/settings/:/usr/local/zed/settings/ \
  --name third_zed \
  <docker_image_tag>

## Real Chair

### Development

- Feito código básico para ESP32; Encoder, IMU, Ponte H + Controle Básico de Velocidade (falta tunar)
- Solucionado problema de tensão esperada no Encoder (In: Jetson 5V --- Out: DDT Temporário)

#### ROS1 Code

Motor control loop (20Hz): Reads encoder RPM, calculates PID output, sends PWM to motors
Safety watchdog: Stops motors if no cmd_vel received for 400ms
