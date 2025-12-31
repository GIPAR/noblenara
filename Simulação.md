# NOBLE NARA SIMULATOR
Tutorial de como utilizar a cadeira de rodas autônoma no projeto "noblenara", que é focado no desenvolvimento e migração de pacotes para uma versão atualizada e eficiente em um ambiente de simulação conhecido como "gazebo"

```
1 - O projeto ainda está na fase inicial de desenvolvimento, severas atualizações são esperadas ao longo deste tempo.
2 - É usado como base inicial os arquivos presentes no repositório b400wheelchair_ws do ramo att_06/2025
3 - Incluiu-se também, na pasta "nara-sim", um tutorial para o uso do container da simulação da NARA no ROS1
```

## 1 - Como utilizar a simulação
É necessário instalar bibliotecas e diferentes dependências para o correto funcionamento das simulações e pacotes, sendo que o projeto está sendo testado e construido no seguinte sistema:
* Ubuntu 24.04
* ROS2 Jazzy

Para a instalação do ROS2 Jazzy, segue-se o tutorial encontrado no seguinte link (https://docs.ros.org/en/jazzy/Installation.html)

### 1.1 - Instalando Dependências Iniciais

```
bash
$ sudo apt install python3-colcon-*
$ sudo apt install ros-jazzy-nav2-map-server
$ sudo apt install ros-jazzy-ros-gz
$ sudo apt install ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge
$ sudo apt-get install ros-jazzy-robot-state-publisher
$ sudo apt install ros-jazzy-gz-ros2-control
```

### 1.2 - Set - Preparando o Workspace

Com s arquivos baixados deste github, mova a pasta "nara-sim" para o diretório padrão do seu computador, navegue até ela com ***um novo terminal*** e rode o seguinte comando:

```
bash
$ colcon build
```

Agora devemos permitir que nosso pacote seja encontrado pelo sistema, juntamente com o ROS. Para isso, rode os seguintes comandos e abra um novo terminal novamente:

```
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
echo "source /home/noblegipar/nara-sim/install/setup.bash" >> ~/.bashrc
```

Obs: **Troque "noblegipar" pelo nome de usuário do seu computador**

## 2 - Simulação

### Abrindo o Mundo com a Cadeira
```
bash
$ ros2 launch smartwheelchair worldmuseum.launch.py
# Em outro terminal:
$ ros2 launch smartwheelchair chair.launch.py
```
