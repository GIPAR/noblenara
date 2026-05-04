# Navegação Autônoma - Development Notes

## Navigation Dev

### Desenvolvimento da Navegação Autônoma

1. Copiado o arquivo nav2_params do repositório de giovanne (navegacao_autonoma)

2. Instalado os pacotes
sudo apt install ros-jazzy-navigation2
sudo apt install ros-jazzy-nav2-bringup

3. Modificado nav2_params e mapper_params (trocado o test_map para "", remove uma mensagem de avizo )

4. Criado nav2_launch.py
Necessário, usando o launch base do nav2 ele chama todos os nós possíveis


### Modificado narawheelchair.xacro

<joint name="robot_footprint_joint" type="fixed"
  <origin xyz="0.25395 0 0" rpy="0 0 0"

trocado a origim para que robot_footprint esteja no centro do differential_drive, em vez de estar um pouco na frente

Aparentemente, é o melhor lugar possivel para que os calculos da navegação autonoma funcionem eficientemente
