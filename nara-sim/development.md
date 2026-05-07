# Navegação Autônoma - Development Notes

## Navigation Dev

### nav2_params

Modificações de performance e eficiencia

### slam params

mode: lifelong #Para possibilitar novas informações de vias externas

Correções de código

Adicionado as linhas de processamento
    minimum_travel_distance: 0.0 #Processa melhor o mapa não necessitando de metros percorridos para atualizar
    minimum_travel_heading: 0.0

### .gazebo

Modificado o angulo do lidar para não se limitar a 180º, como Caio adicionou o filtro do laser, automaticamente o espaço 3d da cadeira é filtrado

<!-- Updated Hokuyo Link ROS2 -->
 <!-- <gazebo reference="hokuyo_link"> -->
    ...
        ...
            <min_angle>-3.14</min_angle>
            <max_angle>3.14</max_angle> 

### Laser Filters

Modificado box de filtro, antes, estava considerando um ponto lateral da carcaça como obstáculo

### nav2_launch.py

Adicionado Remapping de tópico no behavior server, no default ele publica no /cmd_vel mas não há parametros para o yaml para trocar o tópico publicador

remappings=[('/cmd_vel', '/noblenara/cmd_vel')]
