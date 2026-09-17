# Dashboard NOBLE CONFIG — Guia de Instalação e Referência

Dashboard gráfico (pygame) que configura o desempenho da simulação NARA
(SLAM + Nav2 + Gazebo) e aplica as mudanças **diretamente nos arquivos do
código da NARA**, com backup automático e restauração de padrão.

---

## 1. Respondendo a dúvida: "o que o dashboard altera?"

Quando você clica em um card, o dashboard **edita os arquivos reais do
pacote** no seu computador (não é uma cópia virtual):

| Arquivo editado | O que ele muda |
|---|---|
| `src/smartwheelchair/urdf/narawheelchair.gazebo` | LIDAR (samples, taxa, alcance), câmeras ZED2i e `camera_user` (resolução/rate), remoção de sensores |
| `src/smartwheelchair/urdf/narawheelchair.xacro` | Qualidade de malhas/modelos (LEVE/MÉDIO/PESADO) |
| `src/smartwheelchair/launch/noblenara.launch.py` | Carga do mundo (museum_light/default/finder) e flags SLAM/Nav2 |
| `src/smartwheelchair/config/nav2_params.yaml` | Partículas do AMCL e `batch_size` do MPPI |

- Antes de mexer, ele salva os originais em
  `src/smartwheelchair/.backup_configurador/`.
- Toda alteração parte **sempre do backup original** (reaplicação
  idempotente) — nunca acumula edições sobre edições.
- O botão **RESTAURAR PADRÃO** devolve os arquivos originais salvos no
  backup.

> IMPORTANTE: o pacote precisa ter sido compilado com
> `colcon build --symlink-install`. Com isso, o que o ROS/Gazebo carrega
> aponta direto para o arquivo-fonte, e a alteração vale **na hora, sem
> rebuild**. Se compilar sem `--symlink-install`, o dashboard ainda salva
> no arquivo-fonte, mas o ROS pode ficar usando a cópia de `install/` —
> por isso use sempre o symlink.

---

## 2. O que é preciso baixar/instalar

### Obrigatório
- **Ubuntu 24.04** (testado com ROS 2 Jazzy).
- **ROS 2 Jazzy** + **Gazebo Harmonic**:
  ```bash
  sudo apt install ros-jazzy-desktop
  ```
- **Python 3, pygame e psutil**:
  ```bash
  sudo apt install python3-pygame python3-psutil
  ```
  (ou, se preferir: `pip install pygame psutil`)
- **A workspace da NARA** — a raiz do repositório com o pacote
  `smartwheelchair` dentro de `src/`.

### O que copiar de um PC para outro
Para levar o dashboard, copie o pacote inteiro `smartwheelchair`
(especialmente `scripts/noble_config.py` + `launch/noble_config.launch.py` +
`urdf/`, `launch/`, `config/`, `worlds/`, `maps/`, `meshes/`, `models/`).
Tudo isso fica em:

```
<SUA_WORKSPACE>/src/smartwheelchair/
```

> Não copie a pasta `.backup_configurador/` (criada automaticamente) nem
> a pasta `install/`/`build/` (geradas pelo colcon).

---

## 3. Como referenciar a pasta (importante!)

O dashboard **não tem caminhos fixos**. Ele se localiza sozinho:

```python
PACOTE_SRC = Path(__file__).resolve().parent.parent
# noble_config.py está em:  .../<algo>/src/smartwheelchair/scripts/
# PACOTE_SRC =               .../<algo>/src/smartwheelchair/
```

Ou seja:

- O **nome da pasta raiz** não importa. Se a sua é `noblenara-main`
  (com subpasta `nara-sim`), na de outra pessoa pode ser `nara-ws`,
  `projeto_nara`, etc. — **funciona do mesmo jeito**.
- O que importa é a **estrutura relativa**:
  ```
  <QUALQUER_NOME>/src/smartwheelchair/
      scripts/  noble_config.py      <- dashboard
      urdf/     narawheelchair.gazebo / narawheelchair.xacro
      launch/   noblenara.launch.py / noble_config.launch.py / weldtaker.launch.py...
      config/   nav2_params.yaml
      worlds/ maps/ meshes/ models/
  ```
- Se um dia os arquivos que o dashboard edita forem **renomeados ou
  movidos**, ajuste a lista no topo do script:

  ```python
  ARQUIVOS_MODIFICAVEIS = [
      "urdf/narawheelchair.gazebo",
      "urdf/narawheelchair.xacro",
      "launch/noblenara.launch.py",
      "config/nav2_params.yaml",
  ]
  ```

- A cor de destaque também é configurável no topo do script:

  ```python
  TEMA = "ciano"   # "ciano" | "vermelho" | "cinza"
  ```

---

## 4. Instalação passo a passo (máquina nova)

```bash
# 1) Pasta da workspace (nome livre, ex.: nara-ws)
mkdir -p ~/nara-ws/src
cd ~/nara-ws/src

# 2) Cole aqui o pacote smartwheelchair (git clone ou cópia via pendrive/zip)

# 3) Fonte do ROS 2
source /opt/ros/jazzy/setup.bash

# 4) Compile com symlink (IMPORTANTE)
cd ~/nara-ws
colcon build --symlink-install --packages-select smartwheelchair

# 5) Rode o dashboard
source install/setup.bash
ros2 launch smartwheelchair noble_config.launch.py
```

> Também dá para rodar direto, sem ROS, só pra ver a interface:
> ```bash
> python3 src/smartwheelchair/scripts/noble_config.py
> ```

---

## 5. Como funciona (resumo)

1. **Iniciante** — 3 cards (`URDF`, `SENSORES`, `MUNDO`) com LEVE/MÉDIO/PESADO.
   Abaixo, cartões informativos explicam o que muda em cada nível.
2. **Desenvolvedor** — grade granular 3x3: LIDAR SAMPLES / LIDAR RATE /
   ZED2i / CAM USUÁRIO / CAM USUÁRIO RATE / AMCL PARTÍCULAS / MUNDO /
   MPPI BATCH / LIDAR RANGE.
3. SLAM e Nav2 ficam **sempre ativos** (fixos) nos dois modos.
4. Cada clique salva a mudança no código da NARA na hora (apply-on-click).
5. `RESTAURAR PADRÃO` volta aos originais salvos em `.backup_configurador/`.

### Estrutura interna (para quem for mexer no código)
```
scripts/noble_config.py     <- dashboard único (interface + aplicação)
  . backup:  .backup_configurador/ (criado em runtime, não versionar)
  . aplicar_config(config)      -> edita gazebo + nav2_params idempotente
  . ler_config_atual()          -> lê os valores reais do código p/ sync
  . restaurar_originais()       -> RESTAURAR PADRÃO
launch/noble_config.launch.py         <- launch único que abre o dashboard
```

---

## 6. Problemas comuns

| Sintoma | Causa / solução |
|---|---|
| "import psutil/pygame não encontrado" | instalar: `sudo apt install python3-pygame python3-psutil` |
| Muda no dashboard mas o Gazebo não muda | compilar com `colcon build --symlink-install` e reiniciar a simulação |
| Não acha `urdf/narawheelchair.gazebo` | conferir a estrutura `.../src/smartwheelchair/...` (seção 3) |
| Botão RESTAURAR não restaura | a pasta `.backup_configurador/` foi apagada; excluir e reaplicar um card gera backup novo |
| Interface não abre (sem display) | dashboard é gráfico; requer ambiente com tela (ou `export SDL_VIDEODRIVER=dummy` só p/ teste) |

---

*Parte do projeto NOBLE — dashboard mantido dentro do pacote `smartwheelchair`.*
*Ainda em Desenvolvimento e Testes, não foi totalmente validado!*