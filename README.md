# NOBLE NARA
Projeto em desenvolvimento que busca migrar, criar e unificar tecnologias da cadeira de rodas autônoma NARA no ROS2.

```
1 - O projeto ainda está na fase inicial de desenvolvimento, severas atualizações são esperadas ao longo deste tempo.
2 - É usado como base inicial os arquivos presentes no repositório b400wheelchair_ws do ramo att_06/2025
3 - Incluiu-se também neste repositório um tutorial para o uso do container da NARA no ROS1
```

## 1 - Pré-requisitos
É necessário instalar bibliotecas e diferentes dependências para o correto funcionamento das simulações e pacotes, sendo que o projeto está sendo testado e construido no seguinte sistema:
* Ubuntu 24.04
* ROS2 Jazzy

Para a instalação do ROS2 Jazzy, segue-se o tutorial encontrado no seguinte link (https://docs.ros.org/en/jazzy/Installation.html)

### 1.1 - Instalando Dependências Iniciais

```
bash
$ sudo apt install ros-jazzy-nav2-map-server
$ sudo apt install ros-jazzy-ros-gz
$ sudo apt install ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge
$ sudo apt-get install ros-jazzy-robot-state-publisher
$ sudo apt install ros-jazzy-gz-ros2-control>
```


## 2 - Simulação

### Abrindo o Mundo com a Cadeira
```
bash
$ ros2 launch smartwheelchair worldmuseum.launch
# Em outro terminal:
$ ros2 launch smartwheelchair chairlaunch.launch
```
