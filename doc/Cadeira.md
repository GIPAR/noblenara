# noblenara

Desenvolvimento e unificação dos pacotes na cadeira física "NARA" em uma versão mais atualizada do ROS2

Atualmente foi implementado os sensores e tópicos essenciais da cadeira, enquanto que o slam está em processo de aprimoramento

## Instalação da Cadeira de Rodas Autônoma

Esta etapa representa todo o processo de preparação e instalação da NARA, ao qual utiliza o hardware descrito [neste arquivo](/doc/Documentos/mapeamento.md)

*Vale ressaltar que este tutorial ainda está em processo de desenvolvimento

### 1 - Preparação Inicial da Jetson

Inicialmente, é necessário atualizar o sistema operacional da Jetson, que é o computador presente na NARA. Vale ressaltar que essa operação irá reescrever todos os dados presentes no SSD, por isso, salve os arquivos importantes primeiramente antes de continuar

1. A NVidea dispõe de tutoriais iniciais específicos para cada versão da Jetson, podendo ser encontrados facilmente via internet. No caso da NARA, utiliza-se a Jetson Orin AGX Developer Kit, podendo ser acessado [clickando aqui](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/quick_start.html#step-2-update-bsp-with-jetson-iso)
2. A forma recomendada de instalação é por meio do ISO oficial da nvidea, ao qual podemos baixar [por este link disposto no site oficial](https://developer.nvidia.com/downloads/embedded/L4T/r39_Release_v2.0/iso/jetsoninstaller-r39.2.0-2026-06-01-23-53-13-arm64.iso), neste caso, é necessário criar um usb bootável a partir desse arquivo e atualizar o sistema por meio dele
3. Por fim, com a Jetson atualizada, instale e atualize os componentes principais da Jetson, [seguindo este tutorial simples](https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/setup_jetpack.html)

### 2 - Circuito Elétrico

Segundamente, precisamos preparar a parte elétrica, contudo, vale ressaltar que quando trabalhamos com o ROS2 não ha suporte oficial para Arduino, não sendo recomendado utilizá-lo devido ás suas limitações inerentes, por isso, utiliza-se a ESP32 que possui suporte oficial, especificamente por meio de uma biblioteca chamada micro-ros. Para o nosso projeto, O micro-controlador é responsável por controlar o motor (via Ponte-H) e ler as informações dos encoders e do imu, sendo essencial para o nosso robô

Esta preparação é dividida em duas etapas:

1. Montar o Circuito
2. Colocar o Código na ESP32

#### 2.1 - Montando o Circuito Elétrico

#### 2.2 - Reescrever o Código da ESP32

O projeto do código da ESP32 pode ser encontrado em /nara-main/Circuito/ESP32, que pode ser aberta pela extensão do Platform.io do vscode. Para isso, com ela instalada, basta selecionar a figura da referida extensão na barra lateral do editor (Uma formiga), selecionando a opção "Pick a folder" ("Selecione uma pasta" em português). Por fim, o código pode ser enviado para a esp32 via micro-usb<->usb, selecionando o ícone de upload na barra inferior esquerda do editor (uma seta pra a direita). Adicionalmente, caso queira um tutorial mais aprofundado, [acesse este Link](https://docs.platformio.org/en/latest/integration/ide/vscode.html) das documentações oficiais da Platform.io

Vale ressaltar que apenas com estas etapas não é possível utilizar a ESP32 diretamente. Neste tipo de código que esta sendo utilizado (micro-ros), ele necessita de um agente que vai intermediar a comunicação entre a ESP32 e a Jetson. Neste projeto, esse agente será preparado nos passos a seguir por meio de um *container*

### 3 - Instalação dos Containers

Um container é um pacote que inclúi todas as dependências necessárias para rodar uma aplicação. Ele é preparado por meio da plataforma denominada [Docker](https://docs.docker.com/get-started/get-docker/), sendo recomendado o seu entendimento antes de prosseguir com os próximos passos

O projeto utiliza de containers para conter todas as dependências, pacotes, códigos e funcionalidades principais, permitindo a replicação de forma eficiente e prática. A seguir, instalaremos os principais containers, responsáveis por permitir o funcionamento dos pacotes da cadeira

#### 3.1 - Instalação do Docker

Para essa instalação, é necessário instalar o ***Docker***, que tem o papel essencial de instalar, administrar e organizar os nossos containers. Para isso, conecte-se na **Jetson** remotamente (via ssh) ou diretamente (teclado, mouse e monitor), abrindo o terminal e rodando o seguinte comando:

``` shell
sudo apt install docker.io
```

Para rodar os comandos sem usar sudo, podemos adicionar o usuário ao grupo "docker"

``` shell
sudo usermod -aG docker $USER # Reinicie a sessão após rodar o comando
```

#### 3.2 - Construindo a Imagem

Ainda no terminal da Jetson, baixe o repositório com git clone

``` shell
git clone https://github.com/GIPAR/noblenara/ 
```

Agora faremos a construção da imagem dos containers (a "base" para a criação dos containers)

``` shell
docker build -t noblenara_main ./noblenara/nara-main/Jetson/Container/noblenara # Troque "Jetson" pelo nome de Usuário, caso este for diferente
```

Por último, criaremos o container a partir da imagem construida

``` shell
docker run --runtime=nvidia -it --privileged --network=host --ipc=host --name=noblenara --pid=host --restart=unless-stopped -v /dev:/dev noblenara_main
```

Vale ressaltar que o domínio do ROS2 que está sendo usado pela ESP32 e pelo container é o 77

#### 3.3 - Automatizando o Sistema

Três partes são necessárias para automatizar todo o sistema

##### Padronizando os nomes dos dispositivos conectados ás portas USB

Primeiramente, vale comentar que os códigos e pacotes da NARA esperam que os dispostivos externos — como o Lidar e o microcontrolador — tenham uma nomeação específica de identificação. Normalmente eles possuem nomes diversos de acordo com o vendedor e o produto, portanto, devemos manualmente nomeá-los de acordo com o esperado. Para essa finalidade, no terminal da ***Jetson***, encontre os ids da ESP e do Lidar por meio do seguinte comando

``` shell
for dev in /dev/serial/by-id/*; do echo -e "\n=== $dev ==="; udevadm info -a -n "$dev" | grep -m 1 'ATTRS{idVendor}'; udevadm info -a -n "$dev" | grep -m 1 'ATTRS{idProduct}'; udevadm info -a -n "$dev" | grep -m 1 'ATTRS{serial}'; done
```

Identifique o idVendor, idProduct e o serial de cada dispostivo. Conecte apenas um por vez na Jetson para isolá-los, caso necessário. Com o Lidar identificado, rode o seguinte comando, substituindo <VENDOR_ID_LIDAR>, <PRODUCT_ID_LIDAR> e <SERIAL_LIDAR> com os respectivos valores encontrados

``` shell
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="<VENDOR_ID_LIDAR>", ATTRS{idProduct}=="<PRODUCT_ID_LIDAR>", ATTRS{serial}=="<SERIAL_LIDAR>", SYMLINK+="lidar"' | sudo tee /etc/udev/rules.d/99-lidar.rules # Exemplo: ATTRS{serial}=="0001"
```

Agora faça o mesmo para a esp32

``` shell
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="<VENDOR_ID_ESP32>", ATTRS{idProduct}=="<PRODUCT_ID_ESP32>", ATTRS{serial}=="<SERIAL_ESP32>", SYMLINK+="esp_nara"' | sudo tee /etc/udev/rules.d/99-esp32.rules # Faça o comando "sudo udevadm control --reload-rules && sudo udevadm trigger" para não precisar reiniciar a Jetson para aplicar as modificações
```

Exemplo de substituição

``` shell
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0001", SYMLINK+="esp_nara"' | sudo tee /etc/udev/rules.d/99-esp32.rules 
```

##### Serviços

Os serviços são programas que operam em segundo plano, iniciados automaticamente junto com o sistema. A NARA usa quatro: `nara-time` (corrige o relógio via rede), `microros-nara` (liga a Jetson ao ESP32 via micro-ROS), `tablet-nara` (captura a câmera do tablet via ADB/scrcpy) e `zed2i-nara` (Iniciar visão 3D da ZED 2i).

Antes de instalar os serviços, instale as dependências:

```bash
# Dependências do tablet-nara
sudo apt install adb v4l2loopback-dkms -y

# Dependências de build do scrcpy v2.7 (versão da apt é desatualizada)
sudo apt install ffmpeg libsdl2-2.0-0 wget gcc git pkg-config meson ninja-build \
  libsdl2-dev libavcodec-dev libavdevice-dev libavformat-dev libavutil-dev \
  libswresample-dev libusb-1.0-0 libusb-1.0-0-dev -y

cd ~ && git clone https://github.com/Genymobile/scrcpy
cd scrcpy && git checkout v2.7 && ./install_release.sh
scrcpy --version   # confirma a instalação

# Dependência do nó Python dentro do container
docker exec -it noblenara bash -c "apt update && apt install -y ros-jazzy-cv-bridge"

# Remove dependências de build, não são mais necessárias
sudo apt remove gcc pkg-config meson ninja-build libsdl2-dev libavcodec-dev \
  libavdevice-dev libavformat-dev libavutil-dev libswresample-dev libusb-1.0-0-dev -y
sudo apt autoremove -y && rm -rf ~/scrcpy
```

Copie os arquivos da pasta do repositório para a jetson e dê permissões de execução para os scripts.

```bash
cd ~/noblenara/nara-main/Jetson/Services
sudo cp *.service /etc/systemd/system/
sudo cp *.sh /usr/bin/
sudo chmod +x /usr/bin/sync_nara_time.sh /usr/bin/nara-vision.sh
```

Recarregue o systemd e habilite todos os serviços no boot

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nara-time.service microros-nara.service tablet-nara.service zed2i-nara.service
```

Para mais informações sobre os serviços e seus conteúdos acesse [services.md](/doc/Tutoriais/services.md).
