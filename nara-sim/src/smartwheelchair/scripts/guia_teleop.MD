# 🎮 NARA Wheelchair Teleop — Guia de Uso e Customização

Controlador visual desenvolvido em Python com **Pygame + ROS2** para teleoperação da cadeira de rodas NARA no Gazebo Harmonic. Publica comandos no tópico `/cmd_vel` com interface gráfica, suporte a teclado/joystick, 3 perfis de velocidade e suavização de movimento que simula a inércia de um veículo real.

---

## 📦 Instalação de Dependências

**1. Python 3.8+** — já incluso no Ubuntu 22.04 / ROS2 Humble

**2. Pygame:**
```bash
pip3 install pygame
```

**3. Pacotes ROS2** (normalmente já instalados):
```bash
sudo apt install ros-$ROS_DISTRO-ros-base python3-rclpy python3-geometry-msgs
# substitua $ROS_DISTRO por humble, iron ou jazzy
```

---

## 🚀 Como Executar

**1.** Inicie o Gazebo com o modelo da NARA:

**2.** Em outro terminal, rode o controlador:
```bash
ros2 run smartwheelchair nara_teleop.py
```

**3.** A janela abrirá. Use WASD ou joystick para controlar.

---

## ⚙️ Como Funciona

| Componente | Descrição |
|---|---|
| **ROS2 Node** | Cria o nó `nara_controller` e publica `geometry_msgs/Twist` em `/cmd_vel` a ~30Hz |
| **Entrada** | Lê teclado (`pygame.key.get_pressed`) ou eixos do joystick (`pygame.joystick`) |
| **Suavização** | Incrementa/decrementa gradualmente com `acceleration_rate` e `deceleration_rate` |
| **Modos de Velocidade** | Dicionário `VELOCIDADES` troca dinamicamente limites e taxas de aceleração |
| **Inversão A/D** | `angular.z > 0 = esquerda` no ROS2 padrão — invertido no código para controle intuitivo |

---

## 🕹️ Controles e Interface

| Tecla / Elemento | Ação |
|---|---|
| `W` / `S` | Frente / Ré |
| `A` / `D` | Gira Esquerda / Direita (invertido para o modelo NARA) |
| Botão **MODO: JOYSTICK/TECLADO** | Alterna entre as entradas |
| Botão **MODOS ▼** | Abre menu para trocar perfil de velocidade |
| Barra central | Velocidade linear atual (🔴 ré / 🟢 frente) |
| Visualização joystick/teclado | Mostra em tempo real o que está pressionado |

---

## 🔧 Como Personalizar

### 1. Alterar limites e suavidade dos modos
Edite o dicionário `VELOCIDADES` no topo do script:
```python
"Seguranca": {"linear": 1.0, "angular": 0.2, "accel": 0.02, "decel": 0.08}
# linear/angular → velocidade máxima
# accel/decel    → quanto o valor sobe/cai por frame (menor = mais suave)
```

### 2. Trocar tópico ROS2
```python
pub = node.create_publisher(Twist, '/nara/cmd_vel', 10)  # exemplo com namespace
```

### 3. Ajustar taxa de atualização
```python
clock.tick(30)  # mude para 60 (mais fluido) ou 20 (menos CPU)
```

### 4. Inverter joystick
```python
eixo_angular = -joy.get_axis(0)  # adicione o sinal negativo
```

### 5. Adicionar/remover teclas
```python
if teclas[pygame.K_q]:
    eixo_angular = 0.5  # exemplo de tecla customizada
```

### 6. Cores e fontes
```python
# Substitua qualquer tupla RGB:
(0, 255, 255)  # ciano → ex: (255, 100, 0) para laranja

# Fontes:
pygame.font.SysFont("monospace", tamanho, bold=True)
```

---

## ⚠️ Solução de Problemas

**`IndentationError`** — Python exige 4 espaços, não tabs. Valide com:
```bash
python3 -m py_compile nara_teleop.py
```

**Joystick não aparece** — Normal, o código faz fallback automático para teclado. Para debug:
```bash
ls /dev/input/js*
jstest /dev/input/js0
```

**Robô não se move no Gazebo:**
- Verifique se o plugin `diff_drive` está escutando `/cmd_vel`
- Teste com: `ros2 topic echo /cmd_vel` (deve mostrar valores ao pressionar W)
- Confira se o modelo não tem joint travado ou massa infinita

**A/D ainda invertidos?** — Inverta os sinais no bloco de teclado ou ajuste no URDF/SDF.

---

## 💡 Dicas Extras

- **Modo servidor (sem janela):** remova as chamadas `pygame.display` e use apenas a lógica de input ROS.
- **Salvar logs de telemetria:** adicione `open("log.csv","a")` e escreva `f"{linear},{angular}\n"` a cada frame.
- **Múltiplos robôs:** duplique o nó, mude `node_name`, tópico do publisher e adicione seletor de ID na UI.
- O código é **100% autocontido** — não requer launch files ou packages ROS complexos.

---

## 📋 Informações

| Campo | Valor |
|---|---|
| Versão | 1.2 (NARA Teleop) |
| ROS2 | Humble / Iron / Jazzy |
| Simulador | Gazebo Harmonic |
| Licença | Uso acadêmico/pessoal — modifique à vontade |