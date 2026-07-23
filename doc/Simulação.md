# NOBLENARA SIM

Tutorial de como utilizar a cadeira de rodas autônoma "NARA" em um ambiente virtual chamado "Gazebo". Atualmente, está incluso no projeto o uso de mapeamento e a navegação autônoma, além da possibilidade de se inicializar múltiplos robôs


1 - O projeto ainda está em desenvolvimento, severas atualizações são esperadas ao longo deste tempo.

2 - Incluiu-se também, [neste arquivo](/doc/Tutoriais/Container_ROS1.md), um tutorial para o uso do container da simulação da NARA no ROS1


## 1 - Primeiros Passos 📋

É necessário instalar bibliotecas e diferentes dependências para o correto funcionamento das simulações e pacotes. Vale considerar que o projeto foi construído utilizando o Ubuntu 24.04 e o ROS2 Jazzy, logo, possivelmente não funcionará em um sistema alternativo

Primeiramente faça a instalação do ROS2 Jazzy, seguindo o seguinte tutorial: (https://docs.ros.org/en/jazzy/Installation.html)

### 1.1 - Instalando Dependências Iniciais

Posteriormente, abra o terminal e cole as seguintes linhas de código

``` shell
sudo apt install python3-colcon-* \
    ros-jazzy-ros-gz \
    ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-gz-ros2-control \
    ros-jazzy-laser-filters \
    ros-jazzy-slam-toolbox \
    ros-jazzy-nav2-map-server \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup
```

### 1.2 - Set - Preparando o Workspace

Com os arquivos baixados deste github, mova a pasta "noblenara-main" para o diretório padrão do seu computador, e em ***um novo terminal*** use os seguintes comandos para compilar a simulação:

``` shell
cd ~/noblenara-main/nara-sim && \
    colcon build --symlink-install
```

Agora devemos permitir que nosso pacote seja encontrado pelo sistema, juntamente com o ROS. Para isso, rode os seguintes comandos:

``` shell
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && \
    echo "source ~/noblenara-main/nara-sim/install/setup.bash" >> ~/.bashrc && \
    # Comandos opcionais && \
    echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc && \
    echo "echo "Terminal Ativado no Domínio do ROS: '"${ROS_DOMAIN_ID}"'"" >> ~/.bashrc && \
    echo "echo "Caso queira modificá-lo, modifique o comando no arquivo .bashrc"" >> ~/.bashrc
```

Obs: O .bashrc é um arquivo que roda toda vez que um novo terminal é aberto, por isso, os próximos comandos só funcionarão se um ***outro terminal*** ser aberto novamente

## 2 - Simulação 🌎

### 2.1 - Abrindo o Mundo com a Cadeira

Estes são os comandos básicos para rodar a simulação via terminal, primeiramente rode o mundo

``` shell
ros2 launch smartwheelchair worldmuseum.launch.py
```

Em outro terminal inicialize a cadeira

``` shell
ros2 launch smartwheelchair noblenara.launch.py
```

Também podemos inicializar o Teleoperador para controle pelo Teclado ou Joystick (Opcional), [clique aqui](/doc/Tutoriais/Teleoperador.md) para ver o tutorial de como utilizá-lo

``` shell
ros2 run smartwheelchair teleop_keyboard.py
```

### 2.2 - Inicializando o Slam

Para inicializar o slam de um dos robôs juntamente com o rviz2, simplesmente rode o comando: 

``` shell
ros2 launch smartwheelchair slam_rviz.launch.py
```

*Caso queira*, o mapa pode ser salvo diretamente pelo slam_toolbox

``` shell
ros2 service call /noblenara/alfa/slam_toolbox/save_map slam_toolbox/srv/SaveMap "name: {data: 'my_map'}" # Troque "alfa" pelo codenome do robô especifico
```

### 2.3 - Inicializando a Navegação Autônoma 🗺️

#### 2.3.1 - Utilizando a Navegação Autônoma com SLAM

A navegação autônoma pode ser realizada de duas formas. Na primeira, com o SLAM ativado (seção 2.2), podemos inicializar a navegação autônoma enquanto fazemos o mapeamento e localização em tempo real por meio do slam_toolbox, rodando posteriormente o seguinte launch

``` shell
ros2 launch smartwheelchair nav2_launch.py
```

#### 2.3.2 - Inicializando o nav2 com um Mapa previamente salvo

Por outro lado, quando temos um mapa previamente gerado e salvo no computador, podemos incializar o nav2 sem o SLAM

``` shell
ros2 launch smartwheelchair nav2_launch.py map_file:=/coloque/o/caminho/do/arquivo/aqui/nome_do_seu_mapa.yaml
```

Nota: o nav2 espera que a localização inicial do robô sejam as coordenadas (0, 0) do mapa, mas, caso não for, podemos chamar o serviço 'ros2 service call /noblenara/alfa/reinitialize_global_localization std_srvs/srv/Empty {}', mas, é geralmente necessário mover o robô por um tempo até que consiga se localizar corretamente

Por fim, podemos inicializar o rviz separadamente

``` shell
ros2 launch smartwheelchair rviz_nav2_launch.py
```

### 3 - Múltiplos Robôs

Para inicializar múltiplos robôs, faça os comandos anteriores novamente, adicionando "robot_codename:=nome_do_robo" no final de cada um. Todos devem possuir o mesmo parâmetro *robot_codename:=* e o mesmo nome definido em "nome_do_robo".

***Atenção:*** Tenha certeza que o primeiro modelo não esteja na área inicial e que os nomes de cada robô sejam diferentes entre si. O nome pode ser definido pela troca da linha "nome_do_robo" do comando robot_codename:=

Exemplo de Código utilizando a navegação autônoma *com* o SLAM:

``` shell
ros2 launch smartwheelchair noblenara.launch.py robot_codename:=naranobre # Lembre-se que é necessário ter um mundo ativo, como descrito na seção 2.1
ros2 launch smartwheelchair slam_rviz.launch.py robot_codename:=naranobre
ros2 launch smartwheelchair nav2_launch.py robot_codename:=naranobre
```

Exemplo de Código utilizando a navegação autônoma *sem* o SLAM e com um mapa previamente gerado:

``` shell
ros2 launch smartwheelchair noblenara.launch.py robot_codename:=naranobre
ros2 launch smartwheelchair nav2_launch.py map_file:=/coloque/o/caminho/do/arquivo/aqui/nome_do_seu_mapa.yaml robot_codename:=naranobre
ros2 launch smartwheelchair rviz_nav2_launch.py robot_codename:=naranobre
```

Para inicializar mais modelos, faça o mesmo processo anterior, mas, certifique-se de modificar o codename para cada robô

#### 3.1 - Noblenara e Turtlebot4 (Em Desenvolvimento)

A noblenara e o Turtlebot4 podem ser inicializados conjuntamente, para ler o tutorial descritivo sobre todos os processos, [Clique aqui](/doc/Tutoriais/AlongTurtlebot.md)