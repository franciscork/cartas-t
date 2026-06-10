#!/usr/bin/env bash
# =============================================================================
#  SIMMOON Telegram Bot — Launch Script (WSL2/Linux)
#  Lanza el bot multi-agente de Telegram en segundo plano con tmux.
#
#  Uso:
#    ./launch_telegram_bot.sh              # Iniciar en tmux
#    ./launch_telegram_bot.sh status       # Ver estado
#    ./launch_telegram_bot.sh stop         # Detener
#    ./launch_telegram_bot.sh logs         # Ver logs
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIMMOON_DIR="$SCRIPT_DIR/Simmoon_arc"
SESSION_NAME="telegram-bot"
LOG_DIR="$HOME/.simmoon-logs"
LOG_FILE="$LOG_DIR/telegram_bot.log"
BOT_SCRIPT="$SIMMOON_DIR/telegram_bot.py"

mkdir -p "$LOG_DIR"

# ── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

# ── Helpers ────────────────────────────────────────────────────────────────
_status() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "  ${GREEN}🟢 Telegram Bot activo (sesión: $SESSION_NAME)${NC}"
        return 0
    else
        echo -e "  ${RED}⚫ Telegram Bot detenido${NC}"
        return 1
    fi
}

_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "No hay logs aún."
    fi
}

_stop() {
    echo -n "  ⏹ Deteniendo Telegram Bot... "
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    pkill -f "telegram_bot.py" 2>/dev/null || true
    echo -e "${GREEN}OK${NC}"
}

_start() {
    if [ ! -f "$BOT_SCRIPT" ]; then
        echo -e "${RED}[ERROR] $BOT_SCRIPT no encontrado${NC}"
        exit 1
    fi

    if _status >/dev/null; then
        echo -e "  ${YELLOW}⚠️  El bot ya está corriendo. Detenlo primero:${NC}"
        echo -e "     $0 stop"
        exit 0
    fi

    echo -e "  ${CYAN}🤖 Iniciando Telegram Bot...${NC}"

    tmux new-session -d -s "$SESSION_NAME" \
        "cd '$SIMMOON_DIR' && python3 telegram_bot.py 2>&1 | tee '$LOG_FILE'; bash"

    sleep 3

    if _status >/dev/null; then
        echo -e "  ${GREEN}✅ Telegram Bot iniciado${NC}"
        echo -e "  ${CYAN}📋 Logs: tail -f $LOG_FILE${NC}"
        echo -e "  ${CYAN}🖥️  TUI:  tmux attach -t $SESSION_NAME${NC}"
    else
        echo -e "  ${RED}❌ Error al iniciar. Revisa: cat $LOG_FILE${NC}"
        exit 1
    fi
}

# ── Main ───────────────────────────────────────────────────────────────────
case "${1:-start}" in
    start|run)
        _start
        ;;
    stop)
        _stop
        ;;
    status)
        _status
        ;;
    logs)
        _logs
        ;;
    restart)
        _stop
        sleep 1
        _start
        ;;
    *)
        echo -e "${YELLOW}Uso: $0 {start|stop|status|logs|restart}${NC}"
        exit 1
        ;;
esac
