# Implementação do Slam para a Noble Nara

## Dependências básicas

Instale o **ROS2 Jazzy Base** seguindo o tutorial oficial em [Ros.org](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).
**Não é necessário instalar a versão Desktop, visto que a máquina de instalação é diferente da máquina de operação.**

## Configuração de acesso SSH

Para conseguir configurar o projeto, primeiramente você deve ser membro do Github organizacional do GIPAR e ter a chave SSH configurada no seu computador.

### Para Gerar a chave SSH siga o tutorial oficial do Github:
https://docs.github.com/pt/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

### Para adicionar a chave gerada a conta online:
https://docs.github.com/pt/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account

## Instalação de dependências necessárias

Para que a máquina tenha permissão para ler as portas USB do LiDAR e do ESP32 sem precisar de sudo:
´´´
sudo usermod -aG dialout $USER
sudo usermod -aG tty $USER
´´´

Dependências ROS necessárias:
´´´
sudo apt update && sudo apt install -y \
  ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher \
  ros-jazzy-laser-filters \
  ros-jazzy-robot-localization \
  ros-jazzy-slam-toolbox \
´´´
## Criação e configuração do workspace ROS 

[ROS2 - Criando workspace](https://docs.ros.org/en/foxy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html)

1. Crie a pasta do workspace:
´´´
mkdir ~/ros2_ws/src
cd ~/ros2_ws/src
´´´

2. Clone o repositório do Slam:
´´´
git clone --single-branch --branch Slam-main https://github.com/GIPAR/noblenara.git
´´´

3. Compile os pacotes:
´´´
cd ~/ros2_ws/
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
´´´

4. Configure o ambiente dos pacotes:
´´´
source ./install/setup.bash
´´´

5. Permita a leitura e gravação dos dispositivos USB:
´´´
sudo chmod 777 /dev/ttyUSB<X>
´´´
*Substitua o <X> pelo número que representa a porta USB do seu LiDAR.*

6. Inicie a cadeira:
´´´
ros2 launch smartwheelchair chair.launch.py
´´´

7. Inicie o Slam
´´´
ros2 launch smartwheelchair slam.launch.py
´´´
Para mover a cadeira, utilize o repositório <INSERIR REPOSITÓRIO DA HMI>