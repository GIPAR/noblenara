# Noblenara e Turtlebot4 (Necessário Completar)

O processo de desenvolvimento para permitir a utilização da NARA + Turtlebot4 está em processo de finalização, alguns comandos precisam de revisão:

Para executarmos os dois robos de serviço no mesmo mundo, primeiro precisamos instalar os pacotes do turtlebot:

## Pacotes para o Ubuntu 24.04

```
sudo apt update
```

```
sudo apt install ros-jazzy-turtlebot4-desktop
```

## Pacotes para a Simulação do Turtlebot4

```
sudo apt install ros-jazzy-turtlebot4-simulator
```

### (Opcional) Caso queira compilar o projeto de forma manual ou não consiga executar os passos acima:

Verifique no repositorio oficial:

https://github.com/turtlebot/turtlebot4_simulator

Documentação do Turtlebot4 no Ros2 Jazzy

https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html

## Iniciando e testando Turtlebot4

O projeto do turtlebot 4 é bem completo e por isso acaba sendo pesado para ser executado, ele já possui sua propria IHM e seus cenarios de teste são bem detalhados, exigindo bastante poder de processamento

O Turtlebot 4 possui duas versões e três mundos para teste, podemos escolher diferentes mundos e versões mudando os parametros no comando de inicialização, os paramentros para o turtlebot são:

* model:=standard
* model:=lite

Os parametros para escolher os cenarios são:

* world:=maze
* world:=warehouse

* world:=depot


Inicie a simulação em um labirinto, ele foi construido para testar metodos de navegação autonoma:

```
ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py model:=standard world:=maze
```

![1781965064894](image/Simulação/1781965112954.png)

```
ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py model:=standard world:=warehouse
```

![1781965096065](image/Simulação/1781965064894.png)

```
ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py model:=standard world:=depot
```

![1781965112954](image/Simulação/1781965096065.png)

## Mapeamento (Nav2) no turtlebot4


**Mapeamento (SLAM):**

```
ros2 launch turtlebot4_navigation slam.launch.py
```


**Visualização no RViz:**

```
ros2 launch turtlebot4_viz view_navigation.launch.py
```

## Noblenara e Turtlebot4 no museu

Agora que temos tudo testado e instalado na noblenara e no turtlebot4, vamos inicialos no museu, para isso iremos executar um launch que faz o spawn do museu, porém carrega os pacotes necessarios para futuramente fazer o spawn da noblenara e do turtlebot4, execute:

```
ros2 launch smartwheelchair worldMuseumTurtlebot.launch.py
```

![1781966440081](image/Simulação/1781966440081.png)

A versão desse museu acima possui uma pessoa, ela será essencial para testarmos o sistema Finder

Agora vamos iniciar a noblenara:

```
ros2 launch smartwheelchair noblenara.launch.py robot_codename:=alfa
```

![1781966669668](image/Simulação/1781966669668.png)

A cadeira ira iniciar nas coordenadas (0,0,0), mova-a manualmente para outro local para 'spawnarmos' o turtlebot4, execute: 

```
ros2 launch smartwheelchair spawn_turtlebot4.launch_.py
```

![1781966848633](image/Simulação/1781966848633.png)

Agora temos o museu com os dois robos de serviço e com cenario adequado para testar as tecnologias desenvolvidas
