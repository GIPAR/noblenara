#!/bin/bash

while true; do
clear
echo "=============================="
echo "        MENU PRINCIPAL        "
echo "=============================="
echo "1  - Iniciar simulação no Museu"
echo "2  - Utilizar cadeira de rodas autonoma"
echo "3  - Teleop"
echo "4  - Iniciar SLAM"
echo "5  - Salvar Mapa"
echo "6  - Iniciar Navegacao Autonoma"
echo "7  - Iniciar simulação no Museu com pessoas"
echo "8  - Iniciar Finder"
echo "9  - Instalar dependencias da cadeira de rodas"
echo "10 - Instalar dependencias do Finder"
echo "11 - Sair"
echo "=============================="
echo -n "Escolha uma opção: "
read opcao

case $opcao in
    1)
        gnome-terminal -- bash -c "
            cd ../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            cd src/smartwheelchair/launch
            ros2 launch worldmuseum.launch.py
            exec bash
        "
        ;;

    2)
        gnome-terminal -- bash -c "
            cd ../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            cd src/smartwheelchair/launch
            ros2 launch chair.launch.py
            exec bash
        "
        ;;

    3)
        gnome-terminal -- bash -c "
            cd ../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            ros2 run teleop_twist_keyboard teleop_twist_keyboard
            exec bash
        "
        ;;


    4)
        gnome-terminal -- bash -c "
            cd ../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            cd src/smartwheelchair/launch
            ros2 launch slam_rviz.launch.py
            exec bash
        "
        ;;

    5)
        gnome-terminal -- bash -c "
            cd ../../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            ros2 run nav2_map_server map_saver_cli -f ~/map
            exec bash
        "
        ;;

    6)
        # Terminal do SLAM
        gnome-terminal -- bash -c "
            cd ../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            cd src/smartwheelchair/launch
            ros2 launch slam.launch.py
            exec bash
        "

        # Terminal da Navegação Autônoma
        gnome-terminal -- bash -c "
            cd ../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            ros2 launch smartwheelchair nav2_launch.py use_sim_time:=True
            exec bash
        "
        ;;

    7)
        gnome-terminal -- bash -c "
            cd ../../
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            cd src/smartwheelchair/launch
            ros2 launch worldmuseum_finder.launch.py
            exec bash
        "
        ;;

    8)
        gnome-terminal -- bash -c "
            cd
            source /opt/ros/jazzy/setup.bash
            source install/setup.bash
            cd finder_ws
            ros2 run finder_perception yolo_node
            exec bash
        "
        ;;

    9)
        gnome-terminal -- bash -c "
            cd
            source /opt/ros/jazzy/setup.bash
            source install/setup.bashpip3 install pynput
            sudo apt install python3-colcon-* &&
            sudo apt install ros-jazzy-ros-gz &&
            sudo apt install ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge &&
            sudo apt-get install ros-jazzy-robot-state-publisher &&
            sudo apt install ros-jazzy-gz-ros2-control &&
            sudo apt install ros-jazzy-laser-filters &&
            sudo apt install ros-jazzy-slam-toolbox &&
            sudo apt install ros-jazzy-nav2-map-server &&
            exec bash 
        "
        ;;

    10)
        gnome-terminal -- bash -c "
            cd

            exec bash
        "
        ;;

    11)
        echo "Saindo..."
        break
        ;;

    *)
        echo "Opção inválida!"
        sleep 1
        ;;
esac
done
