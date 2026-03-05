# SLAM Commit 05/03/2026

1 - Adicionado os dois config files da simulação de Caio + Modificado nome do tópico em mapper params

2 - Adicionado as linhas no chair.launch.py e modificado os comentários

``` Filter Setup ```

    filter_config = os.path.join(pkg_share, 'config', 'laser_filter.yaml')

    laser_filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        parameters=[filter_config],
        remappings=[
            ('scan', '/noblenara/scan'),
            ('scan_filtered', '/noblenara/scan_filtered')
        ],
        output='screen'
    )

3 - Adicionado arquivo slam.launch.py de Caio

4 - Pacotes Instalados

    ros-jazzy-laser-filters \
    ros-jazzy-slam-toolbox \

5 - Erro:

[scan_to_scan_filter_chain-4] [WARN] [1772724221.509093578] [laser_scan_box_filter]: Could not get transform, irgnoring laser scan! Invalid frame ID "wheelchair/robot_footprint/head_hokuyo_sensor" passed to canTransform argument source_frame - frame does not exist. canTransform returned after 1.01113 timeout was 1.

Caio utilizou um nó para fazer um remmapping do frame id

Solução alternativa proposta:

O laser filter pega o frame id do gazebo **diretamente**, então se mudarmos o frame id no gazebo para o esperado, ele encontrará

Adicionado a linha no .gazebo:
<gazebo reference="hokuyo_link">
    <sensor type="gpu_lidar" name="head_hokuyo_sensor">
      <gz_frame_id>hokuyo_link</gz_frame_id>

O erro desapareceu!

Uma segunda solução que poderia ser possível:
    Em laser_filter.yaml trocar o frame id para o esperado do gazebo em
        params:
            box_frame: base_link
