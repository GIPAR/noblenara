# Smart Wheelchair Simulation (Nara-sim)

Este pacote contém a simulação completa da Cadeira de Rodas Inteligente (Projeto Nara) utilizando **ROS 2 Jazzy** e **Gazebo Harmonic**. O projeto abrange desde a modelagem URDF, integração de sensores (LiDAR), filtragem de dados para remoção do chassi e mapeamento de ambientes (SLAM).

## 📋 Pré-requisitos

Certifique-se de que o ambiente possui as seguintes configurações:
* **Sistema Operacional:** Ubuntu 24.04 (Noble Numbat)
* **ROS 2:** Jazzy Jalisco
* **Simulador:** Gazebo Harmonic (pacote `ros_gz`)

### Instalação de Dependências
Execute o comando abaixo para instalar todos os pacotes necessários para simulação, controle e navegação:

```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz \
                 ros-jazzy-xacro \
                 ros-jazzy-joint-state-publisher-gui \
                 ros-jazzy-teleop-twist-keyboard \
                 ros-jazzy-laser-filters \
                 ros-jazzy-slam-toolbox \
                 ros-jazzy-navigation2 \
                 ros-jazzy-nav2-bringup \
                 ros-jazzy-nav2-map-server
```

### Instalação e compilação do projeto
Clone ou copie o pacote para o workspace: Certifique-se de que a pasta smartwheelchair está dentro de ~/Nara-sim/src/.

Compile o workspace: Sempre execute estes comandos a partir da raiz do workspace (~/Nara-sim):

```bash
cd ~/Nara-sim
# Limpa compilações antigas para garantir atualização de arquivos
rm -rf build install log

# Compila com links simbólicos (facilita edição de scripts Python/Launch)
colcon build --symlink-install

# Carrega as variáveis de ambiente do projeto
source install/setup.bash
```

### Como usar
#### Iniciar a Simulação
Este comando carrega o robô no ambiente de museu (museum.world), inicia o LiDAR, o filtro de dados (para ignorar a cadeira) e abre o RViz configurado.

```bash
ros2 launch smartwheelchair display.launch.py
```
Em um novo terminal, abra o RViz

```bash
ros2 run rviz2 rviz2
```
No RViz, no menu a esquerda, faça os seguintes passos:

Add -> Map
Após, VER QUAL A PROXIMA PARTE

#### Controlar o Robô (Teleoperação)
Em um novo terminal, execute o nó de teleoperação para controlar a cadeira com o teclado:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

#### Mapeamento (SLAM)
Para criar um mapa novo do ambiente usando o SLAM Toolbox:

Inicie a simulação (passo 1).

Em um novo terminal, inicie o SLAM:

```bash
ros2 launch smartwheelchair slam.launch.py
```

Utilize o teleop (passo 2) para dirigir o robô por todo o cenário. Acompanhe a construção do mapa no RViz (tópico /map).

4. Salvar o Mapa Gerado
Após mapear todo o ambiente desejado, execute o comando abaixo para salvar os arquivos do mapa (.pgm e .yaml):

```bash
ros2 run nav2_map_server map_saver_cli -f ~/Nara-sim/src/smartwheelchair/maps/nome_do_mapa
```