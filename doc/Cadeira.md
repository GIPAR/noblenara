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

Segundamente, precisamos preparar a parte elétrica, contudo, vale ressaltar que quando trabalhamos com o ROS2 não ha suporte oficial para Arduino, não sendo recomendado utilizá-lo devido ás suas limitações inerentes, por isso, utiliza-se a ESP32 que possui suporte oficial, especificamente por meio de uma biblioteca chamada micro-ros. Para o nosos projeto, O micro-controlador é responsável por controlar o motor (via Ponte-H) e ler as informações dos encoders e do imu, sendo essencial para o nosso robô

Esta preparação é dividida em duas etapas:

1. Montar o Circuito
2. Colocar o Código na ESP32

#### 2.1 - Montando o Circuito Elétrico

#### 2.2 - Reescrever o Código da ESP32

O projeto do código da ESP32 pode ser encontrado em /nara-main/Circuito/ESP32, esta pasta pode ser aberta utilizando a extensão do Platform.io no vscode, ao qual, pode ser feito upload para o microcontrolador via micro-usb<->usb. [Neste link](https://docs.platformio.org/en/latest/integration/ide/vscode.html) há um tutorial básico de setup inicial do platform.io, contudo, em vez de criar um novo projeto, abra o arquivo da ESP32 existente. Para isso, com a extensão instalada, clicke na figura do platform.io na barra lateral do editor (a figura de uma formiga) e selecione a opção "Pick a folder", podendo fazer o build e upload por intermedio das opções ofericidas na barra inferior esquerda

Vale ressaltar que apenas com estas etapas não é possível utilizar a ESP32 diretamente, neste tipo de código que esta sendo utilizado (micro-ros), ele necessita de um agente que vai intermediar a comunicação entre a ESP32 e a Jetson. Geralmente este agente é preparado em um workspace, contudo, já foi feito todos os processos necessários em um container, que será explicado na próxima etapa

### 3 - Instação dos Containers

Agora, instalaremos os containers principais que permitem o funcionamento dos diferentes sensores e componentes da cadeira

#### 3.1 - Instalação do Docker

Para utilizarmos os containers, precisamos baixar o administrador que vai instalar, ministrar e organizar os nossos containers, denominado docker. Para isso, conecte-se na **Jetson** remotamente (ssh) ou diretamente (teclado, mouse e monitor) e abra o terminal, rodando o seguinte comando:

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

Agora faremos a construção da imagem dos containers (a "forma" que faz os containers tomarem um formato específico)

``` shell
docker build -t noblenara_main ./noblenara/nara-main/Jetson/Container/noblenara # Troque "Jetson" pelo nome de Usuário, caso este for diferente
```

Por último, criaremos o container a partir da imagem construiída

``` shell
docker run --runtime=nvidia -it --privileged --network=host --ipc=host --name=noblenara --pid=host --restart=unless-stopped -v /dev:/dev noblenara_main
```

Vale ressaltar que o domínio do ROS2 que está sendo usado pela ESP32 e pelo container é o 77

#### 3.3 - Automatizando o Sistema

Três partes são necessárias para automatizar o sistema...

Tutorial Em progresso.
