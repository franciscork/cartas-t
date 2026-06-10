#!/usr/bin/env bash
# =============================================================================
# SIMMOON — Launch Jarvis (Web UI + Gateway + CLI)
# Inicia el backend gateway + frontend web de OpenJarvis
#
# Uso:
#   bash launch_jarvis.sh              # Iniciar todo
#   bash launch_jarvis.sh status       # Ver estado
#   bash launch_jarvis.sh stop         # Detener todo
#   bash launch_jarvis.sh update       # Actualizar OpenJarvis
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

JARVIS_DIR="$HOME/OpenJarvis"
LOG_DIR="$HOME/.simmoon-logs"
FRONTEND_PORT=5173

mkdir -p "$LOG_DIR"

OK="${GREEN}✅${NC}"
FAIL="${RED}❌${NC}"
WARN="${YELLOW}⚠️${NC}"
INFO="${CYAN}ℹ️${NC}"

check_http() { curl -sf --max-time 3 "$1" &>/dev/null && echo "OK" || echo "FAIL"; }

banner() {
  echo -e "${CYAN}"
  echo '  ╔══════════════════════════════════════════════╗'
  echo '  ║      ☾  SIMMOON  —  LAUNCH JARVIS           ║'
  echo '  ║                                              ║'
  echo '  ║  OpenJarvis v0.1.1 · Web UI + Gateway + CLI ║'
  echo '  ╚══════════════════════════════════════════════╝'
  echo -e "${NC}"
}

show_status() {
  echo ""
  echo -e "${BOLD}─── Estado de Jarvis ───${NC}"
  
  # Frontend
  if check_http "http://localhost:$FRONTEND_PORT" >/dev/null; then
    echo -e "  ${OK} Web UI    :5173   activo"
  else
    echo -e "  ${FAIL} Web UI    :5173   inactivo"
  fi

  # Gateway
  if tmux has-session -t jarvis-server 2>/dev/null; then
    echo -e "  ${OK} Gateway   tmux    activo"
  else
    echo -e "  ${FAIL} Gateway   tmux    inactivo"
  fi

  # CLI
  if command -v jarvis &>/dev/null || [ -f "$JARVIS_DIR/.venv/bin/jarvis" ]; then
    JVER=$("$JARVIS_DIR/.venv/bin/jarvis" --version 2>/dev/null | head -1 || echo "instalado")
    echo -e "  ${OK} CLI       path    ${JVER}"
  else
    echo -e "  ${FAIL} CLI       no encontrado"
  fi

  # Ollama check
  if check_http "http://localhost:11434/api/tags" >/dev/null; then
    echo -e "  ${OK} Ollama    :11434  reachable (backend de IA)"
  else
    echo -e "  ${WARN} Ollama    :11434  no responde"
  fi
}

start_all() {
  banner

  # ── 1. Verificar que existe ──
  if [ ! -d "$JARVIS_DIR" ]; then
    echo -e "  ${FAIL} OpenJarvis no encontrado en $JARVIS_DIR"
    echo -e "  ${INFO} Instala: cd ~ && git clone https://github.com/open-jarvis/OpenJarvis.git"
    exit 1
  fi

  # ── 2. Verificar Ollama ──
  echo -e "${BOLD}[1/3] Verificando backend Ollama...${NC}"
  if check_http "http://localhost:11434/api/tags" >/dev/null; then
    echo -e "  ${OK} Ollama conectado"
  else
    echo -e "  ${WARN} Ollama no responde. El chat usara modelos offline si estan disponibles."
  fi

  # ── 3. Iniciar Gateway ──
  echo -e "${BOLD}[2/3] Iniciando Jarvis Gateway...${NC}"
  if tmux has-session -t jarvis-server 2>/dev/null; then
    echo -e "  ${OK} Gateway ya activo"
  else
    tmux new-session -d -s jarvis-server \
      "cd '$JARVIS_DIR' && .venv/bin/jarvis gateway start 2>&1 | tee '$LOG_DIR/jarvis_server.log'; bash"
    sleep 3
    if tmux has-session -t jarvis-server 2>/dev/null; then
      echo -e "  ${OK} Gateway iniciado (sesion: jarvis-server)"
    else
      echo -e "  ${FAIL} Error al iniciar Gateway"
    fi
  fi

  # ── 4. Iniciar Frontend ──
  echo -e "${BOLD}[3/3] Iniciando Frontend Web...${NC}"
  if check_http "http://localhost:$FRONTEND_PORT" >/dev/null; then
    echo -e "  ${OK} Frontend ya activo en http://localhost:$FRONTEND_PORT"
  else
    cd "$JARVIS_DIR/frontend"
    tmux new-session -d -s jarvis-frontend \
      "npm run dev 2>&1 | tee '$LOG_DIR/jarvis_frontend.log'; bash"
    echo -n "  Esperando frontend"
    for i in $(seq 1 15); do
      sleep 1
      if check_http "http://localhost:$FRONTEND_PORT" >/dev/null; then
        echo -e "\n  ${OK} Frontend iniciado en http://localhost:$FRONTEND_PORT"
        break
      fi
      echo -n "."
    done
    if ! check_http "http://localhost:$FRONTEND_PORT" >/dev/null; then
      echo -e "\n  ${WARN} Frontend no respondio en 15s. Revisa: tail -20 $LOG_DIR/jarvis_frontend.log"
    fi
    cd "$HOME"
  fi

  # ── Resumen ──
  echo ""
  echo -e "${BOLD}══════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  📊 RESUMEN${NC}"
  echo -e "${BOLD}══════════════════════════════════════════════${NC}"
  show_status
  echo ""
  echo -e "${CYAN}  🌐 Web UI:  http://localhost:$FRONTEND_PORT${NC}"
  echo -e "${CYAN}  💻 CLI:     jarvis ask 'tu pregunta'${NC}"
  echo -e "${CYAN}  💬 Chat:    jarvis chat${NC}"
  echo -e "${CYAN}  📋 Doctor:  jarvis doctor${NC}"
  echo -e "${CYAN}  📁 Logs:    $LOG_DIR/jarvis_*.log${NC}"
}

stop_all() {
  echo -e "${YELLOW}🛑 Deteniendo Jarvis...${NC}"
  tmux kill-session -t jarvis-server 2>/dev/null && echo "  ${OK} Gateway detenido" || true
  tmux kill-session -t jarvis-frontend 2>/dev/null && echo "  ${OK} Frontend detenido" || true
}

update_jarvis() {
  echo -e "${BOLD}🔄 Actualizando OpenJarvis...${NC}"
  cd "$JARVIS_DIR"
  git pull 2>&1 | tail -5
  uv sync 2>&1 | tail -5
  echo ""
  JVER=$("$JARVIS_DIR/.venv/bin/jarvis" --version 2>/dev/null | head -1 || echo "?")
  echo -e "${OK} Version: ${JVER}"
}

# ── Main ──────────────────────────────────────────────────────────────────
case "${1:-start}" in
  start|up)
    start_all
    ;;
  status|check)
    show_status
    ;;
  stop|down)
    stop_all
    ;;
  restart)
    stop_all
    sleep 2
    start_all
    ;;
  update)
    update_jarvis
    ;;
  *)
    echo "Uso: bash launch_jarvis.sh {start|stop|status|restart|update}"
    echo ""
    echo "  start    Iniciar Gateway + Frontend Web"
    echo "  stop     Detener todo"
    echo "  status   Ver estado"
    echo "  restart  Reiniciar"
    echo "  update   Actualizar OpenJarvis (git pull + uv sync)"
    exit 1
    ;;
esac
