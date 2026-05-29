# Serviços do Projeto NARA (Systemd e Scripts)

> Este documento centraliza a configuração dos serviços `systemd` da NVIDIA Jetson responsáveis pela inicialização automática e monitorização do ecossistema NARA. O sistema gere o relógio do hardware, os contentores Docker, a comunicação micro-ROS e a captura de vídeo (tablet e ZED 2i).

---

## 🔄 Ordem de Inicialização no Boot

O `systemd` gere as dependências na seguinte ordem:

| Ordem | Serviço | Descrição | Dependências |
|-------|---------|-----------|-------------|
| 1️⃣ | `nara-time.service` | Executa primeiro. Depende da rede para corrigir o relógio. | `network-online.target` |
| 2️⃣ | `noblenara-container.service` | Aguarda o Docker e o `nara-time.service`. Levanta o ambiente base. | `docker.service`, `nara-time.service` |
| 3️⃣ | `microros-nara.service` | Aguarda o `noblenara-container.service`. Estabelece a ligação série com o ESP32. | `docker.service`, `noblenara-container.service` |
| 4️⃣ | `tablet-nara.service` | Aguarda o `noblenara-container.service`. Inicia o processamento de imagem do tablet. | `docker.service`, `noblenara-container.service` |
| 🔷 | `zed2i-nara.service` | Serviço independente do ecossistema principal. Requer apenas o `docker.service` e o contentor `main_zed` existente. | `docker.service` |

---

## 1. Sincronização de Relógio (`nara-time.service`)

> ⚠️ **Atenção:** Como o RTC (*Real Time Clock*) da placa não possui bateria/está inoperante, o sistema arranca com a data incorreta, o que inviabiliza conexões SSL (HTTPS) e corrompe os *timestamps* do ROS 2. Este serviço força a atualização via rede.

### 📄 Código do Serviço  
`/etc/systemd/system/nara-time.service`

```ini
[Unit]
Description=Sincronizacao de Hora do Projeto NARA
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/home/jetson-nara/sync_nara_time.sh
User=root
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

### 📜 Código do Script  
`/home/jetson-nara/sync_nara_time.sh`

```bash
#!/bin/bash
echo "NARA: Iniciando sincronizacao de tempo..."
sleep 10

echo "NARA: Corrigindo DNS..."
rm -f /etc/resolv.conf
echo "nameserver 192.168.0.1" > /etc/resolv.conf
sleep 2

HTTP_DATE=$(curl -sI --connect-timeout 5 http://www.google.com | grep -i '^Date:' | sed 's/^[Dd]ate: //I' | tr -d '\r')

if [ -n "$HTTP_DATE" ]; then
    date -s "$HTTP_DATE"
    echo "NARA: Relogio sincronizado com sucesso via Google!"
    exit 0
fi

echo "NARA: Sem internet. Setando data de seguranca."
date -s "Wed Apr 29 12:00:00 -03 2026"
```

---

## 2. Contentor Principal (`noblenara-container.service`)

> Mantém a imagem base do projeto em execução. Se este contentor falhar, todo o ecossistema ROS 2 Jazzy cai em cascata.

### 📄 Código do Serviço  
`/etc/systemd/system/noblenara-container.service`

```ini
[Unit]
Description=Container Principal NARA (noblenara)
Requires=docker.service
After=docker.service nara-time.service

[Service]
Type=simple
TimeoutStartSec=0
Restart=always
RestartSec=5
ExecStart=/usr/bin/docker start -a noblenara
ExecStop=/usr/bin/docker stop -t 10 noblenara

[Install]
WantedBy=multi-user.target
```

---

## 3. Agente Micro-ROS (`microros-nara.service`)

> Gere a comunicação série entre a Jetson (ROS 2) e o microcontrolador ESP32 através de hardware físico.

### 📄 Código do Serviço  
`/etc/systemd/system/microros-nara.service`

```ini
[Unit]
Description=Agente Micro-ROS NARA
Requires=docker.service
After=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker exec noblenara bash -c "source /opt/ros/jazzy/setup.bash && source /microros_ws/install/setup.bash && ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/esp_nara -b 115200"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 4. Nó de Visão do Tablet (`tablet-nara.service`)

> Responsável por capturar o ecrã do tablet via ADB (*Android Debug Bridge*), canalizá-lo para uma câmara virtual e publicar o fluxo num tópico ROS.

### 📄 Código do Serviço  
`/etc/systemd/system/tablet-nara.service`

```ini
[Unit]
Description=Nó de Visão do Tablet NARA
Requires=docker.service noblenara-container.service
After=docker.service nara-time.service noblenara-container.service

[Service]
Type=simple
KillMode=mixed
ExecStart=/usr/local/bin/nara-vision.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 📜 Código do Script  
`/usr/local/bin/nara-vision.sh`

```bash
#!/bin/bash
export SDL_VIDEODRIVER=dummy
export SDL_RENDER_DRIVER=software

echo "Limpando processos fantasmas..."
pkill -f "scrcpy.*v4l2-sink" 2>/dev/null
sleep 1

if [ -e /dev/video7 ]; then
  echo "Removendo /dev/video7 antigo..."
  modprobe -r v4l2loopback 2>/dev/null
  sleep 1
fi

echo "Configurando v4l2loopback..."
modprobe v4l2loopback exclusive_caps=1 video_nr=7 card_label="Tablet_Nara"

echo "Iniciando scrcpy..."
scrcpy \
  --video-source=camera \
  --camera-id=1 \
  --video-codec=h264 \
  --video-encoder='OMX.Exynos.AVC.Encoder' \
  --max-size=1280 \
  --max-fps=30 \
  --v4l2-sink=/dev/video7 \
  --no-audio \
  --no-window &
SCRCPY_PID=$!

echo "Aguardando /dev/video7..."
TIMEOUT=30
ELAPSED=0
while [ ! -e /dev/video7 ] && [ $ELAPSED -lt $TIMEOUT ]; do
  sleep 1
  ELAPSED=$((ELAPSED + 1))
done

if [ ! -e /dev/video7 ]; then
  echo "ERRO: /dev/video7 nao apareceu em ${TIMEOUT}s. Abortando."
  kill $SCRCPY_PID 2>/dev/null
  exit 1
fi

echo "/dev/video7 pronto! Aguardando stream estabilizar..."
sleep 5
echo "Iniciando no Docker..."
docker exec noblenara bash -c \
  'source /opt/ros/jazzy/setup.bash && \
   python3 /noblenara_ws/tablet_cam_node.py'
```

---

## 5. Câmera Estereoscópica ZED 2i (`zed2i-nara.service`)

> Este serviço lida com a visão 3D principal. Isola a ZED num ambiente ROS 2 Humble por dependências de pacotes da Stereolabs.

### 📄 Código do Serviço  
`/etc/systemd/system/zed2i-nara.service`

```ini
[Unit]
Description=ZED 2i Camera ROS2 Node NARA
Requires=docker.service
After=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker exec main_zed bash -c "source /opt/ros/humble/setup.bash && source /home/Zed/install/setup.bash && ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zed2i"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 🛠️ Comandos Úteis para Gestão dos Serviços

```bash
# Recarregar daemon após alterar ficheiros .service
sudo systemctl daemon-reload

# Ativar serviços para iniciar no boot
sudo systemctl enable nara-time.service
sudo systemctl enable noblenara-container.service
sudo systemctl enable microros-nara.service
sudo systemctl enable tablet-nara.service
sudo systemctl enable zed2i-nara.service

# Iniciar/Parar/Reiniciar serviços individualmente
sudo systemctl start <nome-do-servico>
sudo systemctl stop <nome-do-servico>
sudo systemctl restart <nome-do-servico>

# Verificar estado e logs
sudo systemctl status <nome-do-servico>
journalctl -u <nome-do-servico> -f  # Follow logs em tempo real
journalctl -u <nome-do-servico> --since "10 minutes ago"  # Logs recentes
```

---

> 📌 **Nota:** Certifique-se de que os scripts possuem permissão de execução:
> ```bash
> chmod +x /home/jetson-nara/sync_nara_time.sh
> chmod +x /usr/local/bin/nara-vision.sh
> ```
