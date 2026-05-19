# Mehrere Commits

Repositório para inclusão de múltiplos robôs em uma única simulação do gazebo

## Mehrere Third Commit - Slam

Permitido o uso de múltiplos Slam's de forma conjunta

### Slam Launch

Modificado funcionamento do slam launch e adicionado robot_codename para permitir inicialização do slam para um robô em específico

Um código em python no slam_rviz.launch.py foi adicionado para ler o arquivo de config do rviz e modifica as linhas com o codenome do robô

ros2 launch smartwheelchair slam_rviz.launch.py robot_codename:=alfa #ou
ros2 launch smartwheelchair slam.launch.py robot_codename:=alfa

### Slam Params

Trocado header name para /**:  # Permite o reconhecimento das configurações independente do nome do nó do slam

### Rviz Config File

Modificado arquivo de configurações, adicionando-se os prefixos em cada tópico

## Mehrere Second Commit - Nodes

Isolado o nome dos nós

### Launchs

Modificado nome do nó no worldmuseum.launch (do bridge global)

Adicionado namespace ou name nos nós do noblenara.launch.py, aceitando o codename do robô

### Laser Filter

Modificado top level heading para

/**: em vez de scan_to_scan_filter_chain

Sem esta modificação, quando modificamos o nome do nó ele não consegue ler o yaml

## Mehrere First Commit - Topics and Frames | General

Commit que permite o funcionamento inicial de múltiplos robôs

Foi necessário isolar o nome de tópicos e frames

Notas:

1. Ainda é necessário verificar se a separação de nós também se aplica

2. Apenas funciona o launch padrão do robô por enquanto, o slam e o nav2 não estão inclusos

### URDF e Gazebo

#### .xacro

Adicionado parâmetro denomidado robot_name, o xacro pode receber esse valor externamente

<xacro:arg name="robot_name" default="alfa"/>

#### .gazebo

O .gazebo recebe o argumento robot_name do xacro diretamente, adicionando-se então o namespace com a seguinte linha:

<xacro:property name="namespace" value="$(arg robot_name)" />

A partir dela, criamos uma espécie de parâmetro/variavel que armazena uma string, parametrizado o código. Fazendo-se então:

1. Adição de radical para os frames e tópicos, para o gazebo publicá-los com nomes diferentes

    Nota: parte da diferenciação dos frames é feita pelo Robot State Publisher (RSP) no launch da cadeira

2. Removido linhas do plugin do sistema para os sensores, ao qual, tentava rodar o gazebo novamente com o launch de mais de uma cadeira

#### .world

Plugins adicionados no .world para correto funcionamento do sistema

    Nota: talvez futuramente seja necessário modificar esta arquitetura, caso, utilizarmos diferentes renderizadores dos plugins, no entanto, provavelmente não será necessário, visto que isto é apenas para a simulação e não para os robos físicos

### Launchs Files

#### worldmuseum.launch.py

Adicionado nó para pontes globais, o clock agora foi ponteado aqui

#### noblenara.launch.py

Adicionado codenome para o robô e alterado os parâmetros e tópicos para aceitarem um radical, os nós receberam remappings dos seus tópicos par isolação (menos para tf e alguns outros)

Podemos dar launch e trocar o código do robô para spawn múltiplo:

ros2 launch smartwheelchair noblenara.launch.py robot_codename:=apelido

##### Laser filter

Nova linha no laser filter para modificar o box_frame, caso contrário, o frame do laser filter mantem-se no padrão e não funciona

{'filter1.params.box_frame': ['noblenara/', robot_codename, '/robot_footprint']}

##### Robot State Publisher - RSP

1. Adicionado frame prefix, ele le os links do urdf e adiciona um prefixo antes de publicar, contudo, apenas não funciona para o diffdrive, que já foi configurado para se auto nomear no próprio .gazebo

{'frame_prefix': ['noblenara/', robot_codename, '/']},
