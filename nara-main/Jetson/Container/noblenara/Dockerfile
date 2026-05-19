# ================================================================
#  Imagem base: ROS 2 Jazzy (versão mínima, sem GUI)
#  Fornece: ROS 2, rosdep, colcon, Python 3 e dependências base.
# ================================================================
FROM ros:jazzy-ros-base

# ================================================================
#  Define o interpretador padrão para todos os comandos RUN.
#  Por padrão o Docker usa /bin/sh, que NÃO entende "source".
#  Trocamos para /bin/bash com -c para poder usar source
#  e todas as features do bash normalmente.
# ================================================================
SHELL ["/bin/bash", "-c"]

# ================================================================
#  FASE 00 — Dependências base do sistema
# ================================================================
RUN apt-get update && apt-get upgrade -y && \
    rosdep update && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ================================================================
#  FASE 01 — micro-ROS Agent
# ================================================================
WORKDIR /microros_ws

RUN git clone -b jazzy \
        https://github.com/micro-ROS/micro_ros_setup.git \
        src/micro_ros_setup && \
    apt-get update && \
    rosdep install --from-paths src --ignore-src -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    source /opt/ros/jazzy/setup.bash && \
    colcon build

COPY fastdds_profile.xml /microros_ws/

RUN source /opt/ros/jazzy/setup.bash && \
    source /microros_ws/install/setup.bash && \
    ros2 run micro_ros_setup create_agent_ws.sh && \
    ros2 run micro_ros_setup build_agent.sh

# ================================================================
#  FASE 02 — Projeto NARA
# ================================================================
WORKDIR /NARA

# Instala o OpenCV para o tablet_cam_node.py
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-opencv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /NARA/scripts

COPY tablet_cam_node.py .
RUN chmod +x tablet_cam_node.py

WORKDIR /NARA

# ================================================================
#  FASE 03 — Ambiente e Entrypoint
# ================================================================

# .bashrc → garante o ambiente em sessões interativas (quando você
# entra no container manualmente e usa o terminal).
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "source /microros_ws/install/setup.bash" >> /root/.bashrc && \
    echo 'export FASTRTPS_DEFAULT_PROFILES_FILE=/microros_ws/fastdds_profile.xml' >> /root/.bashrc

# entrypoint → garante o ambiente em QUALQUER situação, inclusive
# quando um serviço externo dispara o container sem abrir terminal.
# Os dois juntos cobrem todos os casos.
RUN echo '#!/bin/bash'                                                              > /ros_entrypoint.sh && \
    echo 'set -e'                                                                  >> /ros_entrypoint.sh && \
    echo 'source /opt/ros/jazzy/setup.bash'                                        >> /ros_entrypoint.sh && \
    echo 'source /microros_ws/install/setup.bash'                                  >> /ros_entrypoint.sh && \
    echo 'export FASTRTPS_DEFAULT_PROFILES_FILE=/microros_ws/fastdds_profile.xml'  >> /ros_entrypoint.sh && \
    echo 'exec "$@"'                                                               >> /ros_entrypoint.sh && \
    chmod +x /ros_entrypoint.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]