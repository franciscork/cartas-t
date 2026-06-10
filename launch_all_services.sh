#!/usr/bin/env bash
# =============================================================================
# SIMMOON — Launch All Services
# Inicia y verifica TODOS los servicios del ecosistema en orden:
#   PostgreSQL → Ollama → ComfyUI → OpenHuman → Jarvis → Telegram Bot → Buffy Bridge → Agatha
#
# Uso:
#   bash launch_all_services.sh              # Iniciar todo
#   bash launch_all_services.sh status       # Ver estado de todo
#   bash launch_all_services.sh stop         # Detener todo
#   bash launch_all_services.sh --quick      # Solo verificar, no iniciar
# =============================================================================

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIMMOON_DIR="$SCRIPT_DIR/Simmoon_arc""
LOG_DIR="$HOME/.simmoon-logs"
mkdir -p "$LOG_DIR"
SUMMARY_LOG="$LOG_DIR/launch_summary.log"

# ── Colors for icons ──
OK="${GREEN}✅${NC}"
FAIL="${RED}❌${NC}"
WARN="${YELLOW}⚠️${NC}"
INFO="${CYAN}ℹ️${NC}"

# ── Helpers ────────────────────────────────────────────────────────────────
log() { echo -e "$1" | tee -a "$SUMMARY_LOG"; }
banner() {
  echo -e "${CYAN}"
  echo '  ╔══════════════════════════════════════════════════════╗'
  echo '  ║      ☾  SIMMOON  —  LAUNCH ALL SERVICES             ║'
  echo '  ║                                                    ║'
  echo '  ║  PostgreSQL · Ollama · ComfyUI · OpenHuman          ║'
  echo '  ║  Jarvis · Telegram Bot · Buffy Bridge · Agatha Actas ║'
  echo '  ╚══════════════════════════════════════════════════════╝'
  echo -e "${NC}"
}

section() {
  echo ""
  echo -e "${BOLD}─── $1 ───${NC}"
}

check_http() {
  curl -sf --max-time 3 "$1" &>/dev/null && echo "OK" || echo "FAIL"
}

check_wsl_binary() {
  command -v "$1" &>/dev/null && echo "OK" || echo "FAIL"
}

# ── Status Check ──────────────────────────────────────────────────────────
check_status() {
  echo ""
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  📊 SIMMOON — Estado de Servicios${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  
  local ALL_OK=true

  # PostgreSQL
  if pg_isready -h localhost -p 5432 &>/dev/null 2>/dev/null || \
     check_http "http://localhost:5432" >/dev/null; then
    log "  ${OK} PostgreSQL     :5432    activo"
  else
    log "  ${FAIL} PostgreSQL     :5432    inactivo"; ALL_OK=false
  fi

  # Ollama
  if check_http "http://localhost:11434/api/tags" >/dev/null; then
    local MODELS
    MODELS=$(curl -sf http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
    log "  ${OK} Ollama         :11434   activo (${MODELS} modelos)"
  else
    log "  ${FAIL} Ollama         :11434   inactivo"; ALL_OK=false
  fi

  # ComfyUI
  if check_http "http://localhost:8188/queue" >/dev/null; then
    log "  ${OK} ComfyUI        :8188    activo"
  else
    log "  ${FAIL} ComfyUI        :8188    inactivo"; ALL_OK=false
  fi

  # OpenHuman
  if check_http "http://localhost:7788/health" >/dev/null; then
    log "  ${OK} OpenHuman      :7788    activo"
  else
    log "  ${FAIL} OpenHuman      :7788    inactivo"; ALL_OK=false
  fi

  # Jarvis
  if command -v jarvis &>/dev/null; then
    local JVER
    JVER=$(jarvis --version 2>/dev/null | head -1 || echo "instalado")
    log "  ${OK} Jarvis         CLI      ${JVER}"
  else
    log "  ${FAIL} Jarvis         CLI      no encontrado"; ALL_OK=false
  fi

  # Telegram Bot
  if tmux has-session -t telegram-bot 2>/dev/null; then
    log "  ${OK} Telegram Bot   tmux     activo"
  else
    log "  ${FAIL} Telegram Bot   tmux     inactivo"; ALL_OK=false
  fi

  # Buffy Bridge
  if tmux has-session -t buffy-telegram 2>/dev/null; then
    log "  ${OK} Buffy Bridge    tmux     activo"
  else
    log "  ${FAIL} Buffy Bridge    tmux     inactivo"; ALL_OK=false
  fi

  # Agatha Actas
  if tmux has-session -t agatha-daemon 2>/dev/null || tmux has-session -t agatha-actas 2>/dev/null; then
    log "  ${OK} Agatha Actas   tmux     activo"
  else
    log "  ${FAIL} Agatha Actas   tmux     inactivo"; ALL_OK=false
  fi

  echo ""
  if $ALL_OK; then
    log "  ${OK} ${GREEN}Todos los servicios operativos${NC}"
  else
    log "  ${WARN} ${YELLOW}Algunos servicios no estan activos${NC}"
    log "  ${INFO} Ejecuta: bash launch_all_services.sh"
  fi
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
}

# ── Stop All ──────────────────────────────────────────────────────────────
stop_all() {
  echo ""
  echo -e "${YELLOW}🛑 Deteniendo todos los servicios...${NC}"
  
  # Tmux sessions
  for session in telegram-bot buffy-telegram agatha-daemon agatha-actas; do
    tmux kill-session -t "$session" 2>/dev/null && echo "  ${OK} Sesion tmux: $session" || true
  done

  # Python processes
  for proc in "telegram_bot.py" "buffy_telegram.py" "agatha_actas.py" "monitor_sistema.py"; do
    pkill -f "$proc" 2>/dev/null && echo "  ${OK} Proceso: $proc" || true
  done

  # OpenHuman
  pkill -f "openhuman" 2>/dev/null && echo "  ${OK} OpenHuman detenido" || true

  # ComfyUI
  pkill -f "main.py.*--port 8188" 2>/dev/null && echo "  ${OK} ComfyUI detenido" || true

  # Ollama (avisa, no mata — suele estar como servicio)
  if systemctl is-active ollama-simmoon.service &>/dev/null 2>/dev/null; then
    echo "  ${INFO} Ollama corre como servicio systemd (no se detiene)"
  else
    pkill -f "ollama serve" 2>/dev/null && echo "  ${OK} Ollama detenido" || true
  fi

  echo ""
  echo -e "${GREEN}✅ Todos los servicios detenidos${NC}"
}

# ── Wait for service ──────────────────────────────────────────────────────
wait_for_http() {
  local NAME="$1" URL="$2" TIMEOUT="${3:-30}"
  echo -n "  ⏳ Esperando $NAME"
  for i in $(seq 1 "$TIMEOUT"); do
    if curl -sf --max-time 1 "$URL" &>/dev/null; then
      echo -e "\r  ${OK} ${GREEN}$NAME listo${NC}        "
      return 0
    fi
    if [ $((i % 5)) -eq 0 ]; then echo -n " ${i}s"; else echo -n "."; fi
    sleep 1
  done
  echo -e "\r  ${FAIL} ${RED}$NAME no respondio tras ${TIMEOUT}s${NC}"
  return 1
}

wait_for_pid() {
  local NAME="$1" PID="$2" TIMEOUT="${3:-10}"
  echo -n "  ⏳ Esperando $NAME (PID $PID)"
  for i in $(seq 1 "$TIMEOUT"); do
    if kill -0 "$PID" 2>/dev/null; then
      echo -e "\r  ${OK} ${GREEN}$NAME corriendo (PID $PID)${NC}        "
      return 0
    fi
    sleep 1
    echo -n "."
  done
  echo -e "\r  ${FAIL} ${RED}$NAME no arranco${NC}"
  return 1
}

# ── Start All ─────────────────────────────────────────────────────────────
start_all() {
  banner
  log "${BOLD}Iniciando servicios SIMMOON — $(date)${NC}"
  log ""

  local HAS_ERRORS=false

  # ── 1. PostgreSQL ──
  section "1/7  PostgreSQL"
  if pg_isready -h localhost -p 5432 &>/dev/null 2>/dev/null; then
    log "  ${OK} PostgreSQL ya estaba activo"
  else
    sudo service postgresql start 2>/dev/null || \
      sudo pg_ctlcluster $(pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1, $2}') start 2>/dev/null || {
      log "  ${WARN} No se pudo iniciar PostgreSQL automaticamente"
      log "  ${INFO} Prueba: sudo service postgresql start"
    }
    sleep 2
    if pg_isready -h localhost -p 5432 &>/dev/null 2>/dev/null; then
      log "  ${OK} PostgreSQL activo"
    else
      log "  ${FAIL} PostgreSQL no responde"
    fi
  fi

  # ── 2. Ollama ──
  section "2/7  Ollama"
  if check_http "http://localhost:11434/api/tags" >/dev/null; then
    log "  ${OK} Ollama ya estaba activo"
  else
    nohup ollama serve &>"$LOG_DIR/ollama.log" &
    local OLLAMA_PID=$!
    wait_for_http "Ollama" "http://localhost:11434/api/tags" 15
    local MODELS
    MODELS=$(curl -sf http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
    log "  ${INFO} Modelos disponibles: ${MODELS}"
    log "  ${OK} Ollama activo en :11434"
  fi

  # ── 3. ComfyUI ──
  section "3/7  ComfyUI"
  if check_http "http://localhost:8188/queue" >/dev/null; then
    log "  ${OK} ComfyUI ya estaba activo"
  else
    if [ ! -f "$HOME/ComfyUI/main.py" ]; then
      log "  ${FAIL} ComfyUI no encontrado en $HOME/ComfyUI"
      log "  ${INFO} Instala: cd ~ && git clone https://github.com/comfyanonymous/ComfyUI"
    else
      cd "$HOME/ComfyUI"
      nohup ./venv/bin/python main.py --listen --port 8188 &>"$LOG_DIR/comfyui.log" &
      local COMFY_PID=$!
      wait_for_http "ComfyUI" "http://localhost:8188/queue" 60
      log "  ${OK} ComfyUI activo en :8188"
    fi
    cd "$HOME"
  fi

  # ── 4. OpenHuman ──
  section "4/7  OpenHuman"
  if check_http "http://localhost:7788/health" >/dev/null; then
    log "  ${OK} OpenHuman ya estaba activo"
  elif [ -f "$HOME/OpenHuman/main.py" ] || [ -d "$HOME/OpenHuman" ]; then
    cd "$HOME/OpenHuman"
    nohup .venv/bin/python main.py &>"$LOG_DIR/openhuman.log" &
    local OH_PID=$!
    wait_for_http "OpenHuman" "http://localhost:7788/health" 30
    log "  ${OK} OpenHuman activo en :7788"
    cd "$HOME"
  else
    log "  ${WARN} OpenHuman no encontrado en ~/OpenHuman"
    log "  ${INFO} Si no lo necesitas, ignora este aviso"
  fi

  # ── 5. Jarvis ──
  section "5/7  Jarvis"
  if command -v jarvis &>/dev/null; then
    local JVER
    JVER=$(jarvis --version 2>/dev/null | head -1 || echo "instalado")
    log "  ${OK} Jarvis disponible: ${JVER}"
  elif [ -f "$HOME/OpenJarvis/.venv/bin/jarvis" ]; then
    log "  ${WARN} jarvis no esta en PATH"
    log "  ${INFO} Agrega ~/.local/bin a tu PATH o crea un alias"
  else
    log "  ${WARN} Jarvis no instalado"
    log "  ${INFO} Instala: cd ~ && git clone https://github.com/open-jarvis/OpenJarvis.git"
  fi

  # ── 6. Telegram Bot ──
  section "6/7  Telegram Bot"
  if tmux has-session -t telegram-bot 2>/dev/null; then
    log "  ${OK} Telegram Bot ya estaba activo (sesion: telegram-bot)"
  elif [ -f "$SIMMOON_DIR/telegram_bot.py" ]; then
    tmux kill-session -t telegram-bot 2>/dev/null || true
    tmux new-session -d -s telegram-bot \
      "cd '$SIMMOON_DIR' && python3 telegram_bot.py 2>&1 | tee '$LOG_DIR/telegram_bot.log'; bash"
    sleep 3
    if tmux has-session -t telegram-bot 2>/dev/null; then
      log "  ${OK} Telegram Bot iniciado (sesion: telegram-bot)"
    else
      log "  ${FAIL} Error al iniciar Telegram Bot"
      HAS_ERRORS=true
    fi
  else
    log "  ${FAIL} telegram_bot.py no encontrado en $SIMMOON_DIR"
    HAS_ERRORS=true
  fi

  # ── 7. Agatha Actas ──
  section "7/7  Agatha Actas"
  if tmux has-session -t agatha-daemon 2>/dev/null; then
    log "  ${OK} Agatha Actas ya estaba activo (sesion: agatha-daemon)"
  elif [ -f "$SIMMOON_DIR/agatha_actas.py" ]; then
    tmux kill-session -t agatha-daemon 2>/dev/null || true
    tmux new-session -d -s agatha-daemon \
      "cd '$SIMMOON_DIR' && python3 agatha_actas.py --daemon 2>&1 | tee '$LOG_DIR/agatha_daemon.log'; bash"
    sleep 3
    if tmux has-session -t agatha-daemon 2>/dev/null; then
      log "  ${OK} Agatha Actas iniciado (sesion: agatha-daemon)"
      log "  ${INFO} Reportes cada 60 min a Telegram"
    else
      log "  ${FAIL} Error al iniciar Agatha Actas"
      HAS_ERRORS=true
    fi
  else
    log "  ${FAIL} agatha_actas.py no encontrado en $SIMMOON_DIR"
    HAS_ERRORS=true
  fi

  # ── 8. Buffy Telegram Bridge ──
  section "8/8  Buffy Telegram Bridge"
  if tmux has-session -t buffy-telegram 2>/dev/null; then
    log "  ${OK} Buffy Bridge ya estaba activo (sesion: buffy-telegram)"
  elif [ -f "$SIMMOON_DIR/buffy_telegram.py" ]; then
    tmux kill-session -t buffy-telegram 2>/dev/null || true
    tmux new-session -d -s buffy-telegram \
      "cd '$SIMMOON_DIR' && python3 buffy_telegram.py --daemon 2>&1 | tee '$LOG_DIR/buffy_telegram.log'; bash"
    sleep 3
    if tmux has-session -t buffy-telegram 2>/dev/null; then
      log "  ${OK} Buffy Bridge iniciado (sesion: buffy-telegram)"
      log "  ${INFO} Buffy responde en Telegram como @Jeremi_Hermes_bot"
    else
      log "  ${FAIL} Error al iniciar Buffy Bridge"
      HAS_ERRORS=true
    fi
  else
    log "  ${FAIL} buffy_telegram.py no encontrado en $SIMMOON_DIR"
    HAS_ERRORS=true
  fi

  # ── Summary ──
  echo ""
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  📊 RESUMEN${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
  check_status
  echo ""
  echo -e "${CYAN}  📁 Logs: $LOG_DIR/${NC}"
  echo -e "${CYAN}  🖥️  Dashboard: http://localhost:5000${NC}"
  echo -e "${CYAN}  📊 Monitor HTML: Simmoon_arc/monitor_dashboard.html${NC}"

  if $HAS_ERRORS; then
    echo ""
    echo -e "${YELLOW}  ⚠️  Algunos servicios tienen errores. Revisa los logs.${NC}"
  fi

  echo ""
  log "${BOLD}Inicio completado — $(date)${NC}"
}

# ── Main ──────────────────────────────────────────────────────────────────
case "${1:-start}" in
  start|up)
    start_all
    ;;
  status|check)
    check_status
    ;;
  stop|down)
    stop_all
    ;;
  restart)
    stop_all
    sleep 2
    start_all
    ;;
  --quick)
    check_status
    ;;
  *)
    echo "Uso: bash launch_all_services.sh {start|stop|status|restart|--quick}"
    echo ""
    echo "  start      Iniciar todos los servicios en orden"
    echo "  stop       Detener todos los servicios"
    echo "  status     Ver estado de todos los servicios"
    echo "  restart    Reiniciar todos los servicios"
    echo "  --quick    Solo verificar estado (no iniciar)"
    exit 1
    ;;
esac
