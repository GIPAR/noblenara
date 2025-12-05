FROM stereolabs/zed:5.1-devel-jetson-jp6.1.0

SHELL ["/bin/bash", "-c"]

RUN sudo apt update && sudo apt upgrade -y && \
    sudo apt install curl -y && \
    sudo apt install git -y

RUN export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}') && \
    curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
RUN sudo dpkg -i /tmp/ros2-apt-source.deb && \
    sudo apt update && \
    sudo DEBIAN_FRONTEND=noninteractive apt install ros-humble-ros-base -y

WORKDIR /home/Zed/src

RUN git clone https://github.com/stereolabs/zed-ros2-wrapper.git

WORKDIR /home/Zed

RUN sudo apt install python3-rosdep -y && \
    sudo apt install python3-colcon-common-extensions -y && \
    source /opt/ros/humble/setup.bash && \
    sudo apt update && sudo rosdep init && sudo rosdep update && rosdep install --from-paths src --ignore-src -y && \
    colcon build --symlink-install --cmake-args=-DCMAKE_BUILD_TYPE=Release

WORKDIR /home/Zed

RUN sudo apt install ros-humble-rosbridge-suite -y && \
    sudo apt install ros-humble-web-video-server -y

# Sourcing the environment
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc && \
    echo "source /home/Zed/install/setup.bash" >> /root/.bashrc

CMD ["/bin/bash"]