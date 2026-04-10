# NOBLENARA SIM
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
$ sudo apt install ros-jazzy-ros-gz
$ sudo apt install ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge
$ sudo apt-get install ros-jazzy-robot-state-publisher
$ sudo apt install ros-jazzy-gz-ros2-control
$ sudo apt install ros-jazzy-laser-filters
$ sudo apt install ros-jazzy-slam-toolbox
$ sudo apt install ros-jazzy-nav2-map-server
```

### 1.2 - Set - Preparando o Workspace

Com os arquivos baixados deste github, mova a pasta "noblenara-main" para o diretório padrão do seu computador, e em ***um novo terminal*** use os seguintes comandos para compilar a simulação:

```
bash
$ cd ~/noblenara-main/nara-sim
$ colcon build --symlink-install
```

Agora devemos permitir que nosso pacote seja encontrado pelo sistema, juntamente com o ROS. Para isso, rode os seguintes comandos:

```
bash
$ echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
$ echo "source ~/noblenara-main/nara-sim/install/setup.bash" >> ~/.bashrc
# Comandos opcionais
$ echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc
$ echo "echo "Terminal Ativado no Domínio do ROS: '"${ROS_DOMAIN_ID}"'"" >> ~/.bashrc
$ echo "echo "Caso queira modificá-lo, modifique o comando no arquivo .bashrc"" >> ~/.bashrc
```

Obs: O .bashrc é um arquivo que roda toda vez que um novo terminal é aberto, por isso, os próximos comandos só funcionarão se um ***outro terminal*** ser aberto novamente

## 2 - Simulação

### Abrindo o Mundo com a Cadeira

Estes são os comandos básicos para rodar a simulação via terminal

```
bash
$ ros2 launch smartwheelchair worldmuseum.launch.py
# Em outro terminal:
$ ros2 launch smartwheelchair chair.launch.py
```

### Inicializando o Slam

Para inicializar o slam, simplesmente rode o comando: 

```
bash
$ ros2 launch smartwheelchair slam.launch.py
```

Podemos vizualisar o mapa que está sendo gerado pelo rviz2, que pode ser aberto em outro terminal

```
bash
$ ros2 run rviz2 rviz2
```

Por fim, o mapa pode ser salvo diretamente pelo slam_toolbox

```
bash
$ ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap "name: {data: 'my_map'}"
```
