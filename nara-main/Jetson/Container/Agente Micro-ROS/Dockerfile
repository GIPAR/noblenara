FROM ros:jazzy-ros-base

SHELL ["/bin/bash", "-c"]

RUN apt update && rosdep update && apt upgrade -y

WORKDIR /microros_ws

#------------PHASE 01--------------/// microROS Agent
#Line to copy the Agent to microros_ws (WORKDIR = mkdir + cd)
RUN git clone -b jazzy https://github.com/micro-ROS/micro_ros_setup.git src/micro_ros_setup && \
    rosdep install --from-paths src --ignore-src -y && \
    source /opt/ros/jazzy/setup.bash && \
    colcon build

#Profile that makes the communication between host and container possible (fastdds bug because of --net=host)
COPY fastdds_profile.xml /microros_ws/

#Command to build and create the agent
RUN source /opt/ros/jazzy/setup.bash && \
    source /microros_ws/install/setup.bash && \
    ros2 run micro_ros_setup create_agent_ws.sh && \
    ros2 run micro_ros_setup build_agent.sh

#------------PHASE 02--------------/// NARA WorkSpace Setup (Developing)
WORKDIR /NARA

RUN sudo apt install ros-jazzy-nav2-map-server && \
    sudo apt-get install ros-jazzy-robot-state-publisher

#Setting the workspaces (it only works for execution but not for building)
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "source /microros_ws/install/setup.bash" >> /root/.bashrc && \
    echo 'export FASTRTPS_DEFAULT_PROFILES_FILE=/microros_ws/fastdds_profile.xml' >> ~/.bashrc

CMD ["/bin/bash"]