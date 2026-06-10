#!/bin/bash
# =============================================================================
#  SIMMOON — Buffy Telegram Bridge — Launch Script (WSL2/Linux)
#  Lanza el bridge Buffy↔Telegram en segundo plano con tmux.
#
#  Uso:
#    ./launch_buffy_telegram.sh              # Iniciar en tmux
#    ./launch_buffy_telegram.sh status       # Ver estado
#    ./launch_buffy_telegram.sh stop         # Detener
#    ./launch_buffy_telegram.sh logs         # Ver logs
#    ./launch_buffy_telegram.sh restart      # Reiniciar
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SIMMOON_DIR="$SCRIPT_DIR/Simmoon_arc"
LOG_DIR="$HOME/.simmoon-logs"
SESSION_NAME="buffy-telegram"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/buffy_telegram.log"

# ── Funciones ──────────────────────────────────────────────────────────────

show_status() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "  ${GREEN}🟢 Buffy Telegram activa (sesión: $SESSION_NAME)${NC}"
        echo -e "  ${CYAN}📱 Bot: @Jeremi_Hermes_bot${NC}"
    else
        echo -e "  ${RED}⚫ Buffy Telegram detenida${NC}"
    fi
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -50 "$LOG_FILE"
    else
        echo "  📭 No hay logs disponibles."
    fi
}

start_bridge() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠️  Buffy Telegram ya está activa${NC}"
        show_status
        return
    fi

    if [ ! -f "$SIMMOON_DIR/buffy_telegram.py" ]; then
        echo -e "  ${RED}❌ $SIMMOON_DIR/buffy_telegram.py no encontrado${NC}"
        exit 1
    fi

    echo -ne "  ${CYAN}🤖 Iniciando Buffy Telegram...${NC} "

    # Matar sesión anterior si existe
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

    # Iniciar nueva sesión
    tmux new-session -d -s "$SESSION_NAME" \
        "cd '$SIMMOON_DIR' && python3 buffy_telegram.py --daemon 2>&1 | tee '$LOG_FILE'; bash"

    sleep 2

    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${GREEN}✅${NC}"
        echo -e "  ${GREEN}✅ Buffy Telegram iniciada (sesión: $SESSION_NAME)${NC}"
        echo -e "  ${CYAN}📋 Logs: tail -f $LOG_FILE${NC}"
        echo -e "  ${CYAN}🖥️  Conectar: tmux attach -t $SESSION_NAME${NC}"
    else
        echo -e "${RED}❌${NC}"
        echo -e "  ${RED}❌ Error al iniciar Buffy Telegram${NC}"
        echo -e "  ${YELLOW}Revisa los logs: cat $LOG_FILE${NC}"
        exit 1
    fi
}

stop_bridge() {
    echo -ne "  ⏹ Deteniendo Buffy Telegram... "
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    pkill -f "buffy_telegram.py" 2>/dev/null || true
    echo -e "${GREEN}✅${NC}"
}

# ── Main ───────────────────────────────────────────────────────────────────

case "${1:-start}" in
    status)
        show_status
        ;;
    logs|log)
        show_logs
        ;;
    stop|kill)
        stop_bridge
        ;;
    restart)
        stop_bridge
        sleep 1
        start_bridge
        ;;
    attach|conn)
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            tmux attach -t "$SESSION_NAME"
        else
            echo -e "  ${RED}❌ Sesión no activa. Iníciala primero.${NC}"
        fi
        ;;
    start|*)
        start_bridge
        ;;
esac
