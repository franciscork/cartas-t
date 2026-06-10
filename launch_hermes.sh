#!/usr/bin/env bash
# ============================================================
#  Hermes Agent — Launch Script (WSL2 Ubuntu)
#  Lanza las 3 interfaces desktop + Gateway backend
#  Hardware: Core Ultra 7 155H / RTX 4070 8GB / 32GB RAM
# ============================================================

set -euo pipefail

# ── Colores ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# ── Configuración ────────────────────────────────────────────
HERMES_BIN="$HOME/.local/bin/hermes"
HERMES_VENV="$HOME/.hermes/hermes-agent/venv/bin/hermes"
LOG_DIR="$HOME/.hermes/logs"
SESSION_NAME="hermes"
DASHBOARD_PORT=9119
OLLAMA_URL="http://127.0.0.1:11434"

# ── Asegurar que hermes está en PATH ─────────────────────────
export PATH="$HOME/.local/bin:$PATH"

# Resolver binario de hermes
if command -v hermes &>/dev/null; then
    HERMES_CMD="hermes"
elif [[ -x "$HERMES_BIN" ]]; then
    HERMES_CMD="$HERMES_BIN"
elif [[ -x "$HERMES_VENV" ]]; then
    HERMES_CMD="$HERMES_VENV"
else
    echo -e "${RED}[ERROR] Hermes no encontrado. Ejecuta la instalación primero.${NC}"
    exit 1
fi

# ── Crear directorio de logs ─────────────────────────────────
mkdir -p "$LOG_DIR"

# ── Funciones auxiliares ─────────────────────────────────────
print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}${MAGENTA}🧠 Hermes Agent — Launch Center${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${NC}v0.16.0 · Nous Research · Ollama Local          ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_ollama() {
    echo -e "${YELLOW}[1/5] Verificando Ollama...${NC}"
    if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
        local count
        count=$(curl -sf "$OLLAMA_URL/api/tags" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
        echo -e "  ${GREEN}✅ Ollama activo — $count modelos disponibles${NC}"
        return 0
    else
        echo -e "  ${RED}❌ Ollama no responde en $OLLAMA_URL${NC}"
        echo -e "  ${YELLOW}   Intentando iniciar Ollama...${NC}"
        if command -v ollama &>/dev/null; then
            nohup ollama serve &>/dev/null &
            sleep 3
            if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
                echo -e "  ${GREEN}✅ Ollama iniciado correctamente${NC}"
                return 0
            fi
        fi
        echo -e "  ${RED}   No se pudo iniciar Ollama. Continuando sin verificación...${NC}"
        return 1
    fi
}

check_model() {
    local model="$1"
    if ollama list 2>/dev/null | grep -q "$model"; then
        echo -e "  ${GREEN}✅ $model${NC}"
        return 0
    else
        echo -e "  ${RED}❌ $model no encontrado${NC}"
        return 1
    fi
}

stop_existing() {
    echo -e "${YELLOW}[2/5] Deteniendo instancias previas...${NC}"

    for sess in hermes-gateway hermes-tui hermes-dashboard; do
        if tmux has-session -t "$sess" 2>/dev/null; then
            tmux kill-session -t "$sess" 2>/dev/null
            echo -e "  ${GREEN}⏹ Sesión '$sess' detenida${NC}"
        fi
    done

    pkill -f "hermes dashboard" 2>/dev/null || true
    echo -e "  ${GREEN}✅ Limpieza completada${NC}"
}

launch_gateway() {
    echo -e "${YELLOW}[3/5] Iniciando Gateway (backend compartido)...${NC}"

    # hermes gateway run no acepta --port; usa config de config.yaml
    tmux new-session -d -s hermes-gateway \
        "source ~/.bashrc 2>/dev/null; $HERMES_CMD gateway run 2>&1 | tee $LOG_DIR/gateway.log; bash"

    sleep 3
    if tmux has-session -t hermes-gateway 2>/dev/null; then
        # Verificar que el gateway está escuchando
        if grep -qi "listening\|started\|ready\|running\|serving" "$LOG_DIR/gateway.log" 2>/dev/null; then
            echo -e "  ${GREEN}✅ Gateway activo${NC}"
        else
            echo -e "  ${GREEN}✅ Gateway sesión creada${NC}"
        fi
    else
        echo -e "  ${RED}❌ Gateway falló. Revisa: $LOG_DIR/gateway.log${NC}"
    fi
}

launch_tui() {
    echo -e "${YELLOW}[4/5] Iniciando TUI (interfaz de terminal)...${NC}"

    tmux new-session -d -s hermes-tui \
        "source ~/.bashrc 2>/dev/null; $HERMES_CMD --tui 2>&1 | tee $LOG_DIR/tui.log; bash"

    echo -e "  ${GREEN}✅ TUI iniciado en sesión 'hermes-tui'${NC}"
    echo -e "  ${CYAN}   Para acceder: tmux attach -t hermes-tui${NC}"
}

launch_dashboard() {
    echo -e "${YELLOW}[5/5] Iniciando Dashboard (web UI)...${NC}"

    tmux new-session -d -s hermes-dashboard \
        "$HERMES_CMD dashboard --port $DASHBOARD_PORT --no-open 2>&1 | tee $LOG_DIR/dashboard.log; bash"

    sleep 3
    if curl -sf "http://127.0.0.1:$DASHBOARD_PORT" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Dashboard activo en http://localhost:$DASHBOARD_PORT${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Dashboard iniciando (puede tardar un momento)...${NC}"
        echo -e "  ${CYAN}   URL: http://localhost:$DASHBOARD_PORT${NC}"
    fi
}

print_status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  🚀 Hermes Agent — Todas las interfaces activas${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}🖥️  TUI (Terminal):${NC}"
    echo -e "     tmux attach -t hermes-tui"
    echo ""
    echo -e "  ${BOLD}🌐 Dashboard (Web):${NC}"
    echo -e "     http://localhost:$DASHBOARD_PORT"
    echo ""
    echo -e "  ${BOLD}⚙️  Gateway (Backend):${NC}"
    echo -e "     Sesión tmux: hermes-gateway"
    echo ""
    echo -e "  ${BOLD}📋 Logs:${NC}"
    echo -e "     $LOG_DIR/{gateway,tui,dashboard}.log"
    echo ""
    echo -e "  ${BOLD}🛑 Detener todo:${NC}"
    echo -e "     bash $0 --stop"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
}

stop_all() {
    echo -e "${YELLOW}🛑 Deteniendo todas las interfaces de Hermes...${NC}"
    for sess in hermes-gateway hermes-tui hermes-dashboard; do
        if tmux has-session -t "$sess" 2>/dev/null; then
            tmux kill-session -t "$sess" 2>/dev/null
            echo -e "  ${GREEN}⏹ $sess detenido${NC}"
        fi
    done
    pkill -f "hermes dashboard" 2>/dev/null || true
    pkill -f "hermes gateway" 2>/dev/null || true
    echo -e "${GREEN}✅ Todas las interfaces detenidas${NC}"
}

show_status() {
    echo ""
    echo -e "${BOLD}📊 Estado de Hermes Agent:${NC}"
    echo ""

    if tmux has-session -t hermes-gateway 2>/dev/null; then
        echo -e "  ${GREEN}✅ Gateway${NC}  → Sesión activa"
    else
        echo -e "  ${RED}❌ Gateway${NC}  → No activo"
    fi

    if tmux has-session -t hermes-tui 2>/dev/null; then
        echo -e "  ${GREEN}✅ TUI${NC}     → tmux attach -t hermes-tui"
    else
        echo -e "  ${RED}❌ TUI${NC}     → No activo"
    fi

    if tmux has-session -t hermes-dashboard 2>/dev/null; then
        echo -e "  ${GREEN}✅ Dashboard${NC} → http://localhost:$DASHBOARD_PORT"
    else
        echo -e "  ${RED}❌ Dashboard${NC} → No activo"
    fi

    if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Ollama${NC}   → $OLLAMA_URL"
    else
        echo -e "  ${RED}❌ Ollama${NC}   → No responde"
    fi

    if command -v nvidia-smi &>/dev/null; then
        local gpu_info
        gpu_info=$(nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || echo "N/A")
        echo -e "  ${GREEN}✅ GPU${NC}      → $gpu_info MiB"
    fi
    echo ""
}

# ── Main ─────────────────────────────────────────────────────
case "${1:-}" in
    --stop|-s)
        stop_all
        exit 0
        ;;
    --status|-t)
        show_status
        exit 0
        ;;
    --help|-h)
        print_banner
        echo "Uso: bash launch_hermes.sh [opciones]"
        echo ""
        echo "  (sin args)    Inicia Gateway + TUI + Dashboard"
        echo "  --stop, -s    Detiene todas las interfaces"
        echo "  --status, -t  Muestra estado de las interfaces"
        echo "  --help, -h    Muestra esta ayuda"
        echo ""
        exit 0
        ;;
esac

print_banner

# Verificaciones
check_ollama || true

echo ""
echo -e "${YELLOW}📦 Modelos Hermes:${NC}"
check_model "gemma3-tools-64k" || true
check_model "qwen3-14b-64k" || true
check_model "qwen25-coder-14b-64k" || true
echo ""

# Detener instancias previas
stop_existing

# Lanzar las 3 interfaces
launch_gateway
launch_tui
launch_dashboard

# Mostrar estado final
print_status
