# Implementação do SLAM para a NobleNara

## Dependências básicas

Instale o **ROS 2 Jazzy Base** seguindo o tutorial oficial do ROS:

https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

> Não é necessário instalar a versão Desktop, visto que a máquina de instalação é diferente da máquina de operação.

---

## Configuração de acesso SSH

Para configurar o projeto, primeiramente você deve ser membro do GitHub organizacional do GIPAR e possuir uma chave SSH configurada no computador.

### Gerar uma chave SSH

Siga o tutorial oficial do GitHub:

https://docs.github.com/pt/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

### Adicionar a chave SSH à conta do GitHub

https://docs.github.com/pt/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account

---

## Instalação das dependências necessárias

Para permitir que a máquina acesse as portas USB do LiDAR e do ESP32 sem utilizar `sudo`:

```bash
sudo usermod -aG dialout $USER
sudo usermod -aG tty $USER
```

Após executar os comandos, reinicie a sessão do usuário ou reinicie o computador.

### Dependências ROS necessárias

```bash
sudo apt update && sudo apt install -y \
  ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher \
  ros-jazzy-laser-filters \
  ros-jazzy-robot-localization \
  ros-jazzy-slam-toolbox
```

---

## Criação e configuração do workspace ROS

Tutorial oficial:

https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html

### 1. Criar o workspace

```bash
mkdir -p ~/noblenara_ws/src
cd ~/noblenara_ws/src
```

### 2. Clonar o repositório do SLAM

```bash
git clone --single-branch --branch Slam-main https://github.com/GIPAR/noblenara.git
```

### 3. Compilar os pacotes

```bash
cd ~/noblenara_ws/
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

### 4. Configurar o ambiente

```bash
source ~/noblenara_ws/install/setup.bash
```

---

## Configuração de acesso USB

Permita leitura e gravação na porta USB utilizada pelo LiDAR:

```bash
sudo chmod 777 /dev/ttyUSB<X>
```

> Substitua `<X>` pelo número correspondente à porta USB do LiDAR.

---

## Inicialização do sistema

### 1. Iniciar a cadeira

```bash
ros2 launch smartwheelchair chair.launch.py
```

### 2. Iniciar o SLAM

```bash
ros2 launch smartwheelchair slam.launch.py
```

---

## Controle da cadeira

Para mover a cadeira, utilize o repositório da HMI:

```text
[NobleNara HMI](https://github.com/GIPAR/noblenara-ihm)
```