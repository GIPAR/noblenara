# NOBLE NARA

Desenvolvimento e unificação dos pacotes na cadeira física "NARA" em uma versão mais atualizada do ROS2

## Progresso

O desenvolvimento inicial desta atualização foi marcada por duas frontes principais

### 1 - Circuito Elétrico

Foi necessário a mudança da parte elétrica/lógica da cadeira devido á limitação do Arduino, ao qual foi substituido por uma ESP32
* Foi feito o código básico da ESP32 que inclui os diferentes sensores
* Montado e testado um circuito temporário para validação em um ambiente real

### 2 - Containers Essenciais

Dois containers principais foram preparados para serem utilizados na Jetson (Computador próprio do robô NARA)
* Agente de Comunicação: ESP32 <-> Jetson
* Inicializador da câmera com comunicação direta no ROS2 com o pacote "zed_ros2_wrapper"

### 3 - Progressões Diversas:

1. Trocado o suporte do Encoder que havia quebrado, ao qual o arquivo 3D pode ser encontrado na pasta "nara-main/Drive/3D/"
2. Atualizado a Jetson para uma versão mais recente com Ubuntu 22

## Planos

Os planos de curto/médio prazo pra cadeira física são diversos, que focam na consolidação do que já foi criado
1. Solidificação e finalização da parte inicial básica, isto é, solidificar a navegação básica que utiliza da teleoperação, montar o circuito fixo da cadeira e resolução de problemas encontrados.
2. Preparar diferentes sistemas de segurança para a realização de testes de forma segura e responsável
3. Realização de testes em diferentes ambientes