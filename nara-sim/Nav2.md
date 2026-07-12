# Inicialização do Nav2 — Passo a Passo
 
Pré-requisito: já ter um mapa salvo, gerado previamente com o `slam_launch.py`.

## 1. Simulação

### Mapa
 
```bash
ros2 launch smartwheelchair worldmuseum.launch.py
```
 
### 1. Cadeira
 
```bash
ros2 launch smartwheelchair noblenara.launch.py
```
 
## 2. Nav2
 
```bash
ros2 launch smartwheelchair nav2_launch.py map_file:=/caminho/completo/para/meu_mapa.yaml
```
 
## 3. RViz
 
```bash
ros2 launch smartwheelchair nav2_rviz_launch.py
```
 
Se estiver usando outro `robot_codename` (padrão é `alfa`), passe o mesmo argumento nos três comandos:
 
```bash
robot_codename:=beta
```