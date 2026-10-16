#!/bin/bash

# ===== CONFIGURAÇÃO =====
ROS_DOMAIN_ID_NARA=77
# =========================

export SDL_VIDEODRIVER=dummy
export SDL_RENDER_DRIVER=software

echo "Limpando processos fantasmas..."
pkill -f "scrcpy.*v4l2-sink" 2>/dev/null
docker exec noblenara bash -c "pkill -f tablet_cam_node.py" 2>/dev/null
sleep 2

if [ -e /dev/video7 ]; then
  echo "Removendo /dev/video7 antigo..."
  modprobe -r v4l2loopback 2>/dev/null
  sleep 1
fi

echo "Configurando v4l2loopback..."
modprobe v4l2loopback exclusive_caps=1 video_nr=7 card_label="Tablet_Nara"
sleep 1

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

echo "Iniciando no Docker (ROS_DOMAIN_ID=${ROS_DOMAIN_ID_NARA})..."
docker exec -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID_NARA}" noblenara bash -c \
  'source /opt/ros/jazzy/setup.bash && \
   [ -f /noblenara_ws/install/setup.bash ] && source /noblenara_ws/install/setup.bash; \
   python3 /noblenara_ws/src/smartwheelchair/scripts/tablet_cam_node.py' &

NODE_PID=$!

echo "Vigiando conexão do tablet (watchdog)..."
while true; do
  # Se o scrcpy morreu (tablet desconectou), aborta tudo e deixa o systemd reiniciar
  if ! kill -0 "$SCRCPY_PID" 2>/dev/null; then
    echo "ERRO: scrcpy morreu (tablet desconectado?). Encerrando para reiniciar o ciclo."
    docker exec noblenara bash -c "pkill -f tablet_cam_node.py" 2>/dev/null
    kill "$NODE_PID" 2>/dev/null
    exit 1
  fi
  # Se o nó ROS morreu por conta própria, também aborta
  if ! kill -0 "$NODE_PID" 2>/dev/null; then
    echo "ERRO: nó ROS encerrou inesperadamente. Encerrando para reiniciar o ciclo."
    kill "$SCRCPY_PID" 2>/dev/null
    exit 1
  fi
  sleep 3
done
