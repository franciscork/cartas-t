#!/usr/bin/env bash
# =============================================================================
# SIMMOON — Launch ALL IAs (WSL2)
# Lanzadera unificada para todos los servicios de IA
#
# Servicios:
#   🧠 Ollama       — LLM server (puerto 11434)
#   🎨 ComfyUI      — Generación de imágenes (puerto 8188)
#   🖼️  InvokeAI     — Generación alternativa (puerto 9090)
#   🧠 Hermes       — Agente con 3 escritorios (puerto 9119)
#   🤖 Agent        — AI director de assets
#   🤖 AutoGen      — Diseño multi-agente
#   🔄 Pipeline     — Workflow LangGraph
#
# Uso:
#   bash launch_ias.sh              # Inicia todo
#   bash launch_ias.sh status       # Estado
#   bash launch_ias.sh stop         # Detiene todo
#   bash launch_ias.sh start ollama # Inicia solo Ollama
# =============================================================================
set -uo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
MAGENTA='\033[0;35m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$HOME/.simmoon-logs"
COMFYUI_DIR="$HOME/ComfyUI"
INVOKEAI_DIR="$HOME/invokeai"
INVOKEAI_ENV="$HOME/invokeai-env"

mkdir -p "$LOG_DIR"

# ── Helpers ──────────────────────────────────────────────────
test_ollama()   { curl -sf --max-time 2 http://localhost:11434/api/tags &>/dev/null && echo "YES" || echo "NO"; }
test_comfyui()  { curl -sf --max-time 2 http://localhost:8188/queue &>/dev/null && echo "YES" || echo "NO"; }
test_invokeai() { curl -sf --max-time 2 http://localhost:9090/api/v1/app/version &>/dev/null && echo "YES" || echo "NO"; }
test_hermes()   { curl -sf --max-time 2 http://localhost:9119 &>/dev/null && echo "YES" || echo "NO"; }

service_status() {
    local name="$1" port="$2" testfn="$3"
    if [ "$($testfn)" = "YES" ]; then
        echo -e "  ${GREEN}✅ $name → http://localhost:$port${NC}"
    else
        echo -e "  ${RED}❌ $name — INACTIVO${NC}"
    fi
}

# ── Banner ───────────────────────────────────────────────────
banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}          ${BOLD}☾  SIMMOON  —  Launch ALL IAs${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Ollama  ·  🎨 ComfyUI  ·  🖼️  InvokeAI               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Hermes (3 desktop)  ·  🤖 Agent  ·  🔄 Pipeline     ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════
#  STATUS
# ═══════════════════════════════════════════════════════════════
status_all() {
    banner
    echo -e "${BOLD}📊 Estado de todas las IAs:${NC}"
    echo ""
    service_status "🧠 Ollama   " "11434" test_ollama
    service_status "🎨 ComfyUI  " "8188"  test_comfyui
    service_status "🖼️  InvokeAI " "9090"  test_invokeai
    service_status "🧠 Hermes   " "9119"  test_hermes

    echo ""
    echo -e "${BOLD}📋 Agentes Python:${NC}"
    [ -f "$SCRIPT_DIR/simmoon_agent.py" ]    && echo -e "  ${GREEN}✅ Simmoon Agent${NC}"    || echo -e "  ${RED}❌ Simmoon Agent${NC}"
    [ -f "$SCRIPT_DIR/simmoon_autogen.py" ]  && echo -e "  ${GREEN}✅ AutoGen${NC}"          || echo -e "  ${RED}❌ AutoGen${NC}"
    [ -f "$SCRIPT_DIR/simmoon_pipeline.py" ] && echo -e "  ${GREEN}✅ Pipeline${NC}"         || echo -e "  ${RED}❌ Pipeline${NC}"

    echo ""
    echo -e "${BOLD}🚀 Lanzaderas disponibles:${NC}"
    for f in "$SCRIPT_DIR"/launch_*.sh; do
        [ -f "$f" ] && echo -e "     bash $(basename "$f")"
    done
    echo ""

    # GPU info
    if command -v nvidia-smi &>/dev/null; then
        echo -e "${BOLD}🖥️  GPU:${NC}"
        nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | while read line; do
            echo "     $line MiB"
        done
    fi
    echo ""
}

# ═══════════════════════════════════════════════════════════════
#  STOP ALL
# ═══════════════════════════════════════════════════════════════
stop_all() {
    echo -e "${YELLOW}🛑 SIMMOON — Deteniendo todas las IAs...${NC}"
    echo ""

    echo -n "  ⏹ Hermes... "
    for s in hermes-gateway hermes-tui hermes-dashboard; do
        tmux kill-session -t "$s" 2>/dev/null
    done
    pkill -f "hermes dashboard" 2>/dev/null || true
    pkill -f "hermes gateway" 2>/dev/null || true
    echo "OK"

    echo -n "  ⏹ InvokeAI... "
    pkill -f "invokeai-web" 2>/dev/null || true
    echo "OK"

    echo -n "  ⏹ ComfyUI... "
    pkill -f "main.py.*--port 8188" 2>/dev/null || true
    echo "OK"

    echo -n "  ⏹ Ollama... "
    pkill -f "ollama serve" 2>/dev/null || true
    echo "OK"

    echo ""
    echo -e "${GREEN}✅ Todos los servicios detenidos${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════
#  START SINGLE
# ═══════════════════════════════════════════════════════════════
start_single() {
    local svc="$1"
    case "$svc" in
        ollama)
            [ -f "$SCRIPT_DIR/launch_ollama.sh" ] && bash "$SCRIPT_DIR/launch_ollama.sh" start
            ;;
        comfyui)
            [ -f "$SCRIPT_DIR/launch_comfyui.sh" ] && bash "$SCRIPT_DIR/launch_comfyui.sh" start
            ;;
        invokeai)
            [ -f "$SCRIPT_DIR/launch_invokeai.sh" ] && bash "$SCRIPT_DIR/launch_invokeai.sh" start
            ;;
        hermes)
            HERMES_SCRIPT="$(dirname "$SCRIPT_DIR")/launch_hermes.sh"
            if [ -f "$HERMES_SCRIPT" ]; then
                bash "$HERMES_SCRIPT" start
            else
                echo "🧠 Hermes — launch_hermes.sh no encontrado. Usa desde el directorio raíz del proyecto."
            fi
            ;;
        *)
            echo "Servicio no reconocido: $svc"
            echo "  Opciones: ollama, comfyui, invokeai, hermes"
            return 1
            ;;
    esac
}

# ═══════════════════════════════════════════════════════════════
#  START ALL
# ═══════════════════════════════════════════════════════════════
start_all() {
    banner

    # 1. Ollama
    echo -e "${BOLD}[1/4] 🧠 Ollama...${NC}"
    if [ "$(test_ollama)" = "YES" ]; then
        echo -e "  ${GREEN}[OK] Ya activo${NC}"
    else
        nohup ollama serve &>/dev/null &
        sleep 3
        [ "$(test_ollama)" = "YES" ] && echo -e "  ${GREEN}[OK] Iniciado${NC}" || echo -e "  ${YELLOW}[WARN] No respondió${NC}"
    fi

    # 2. ComfyUI
    echo -e "\n${BOLD}[2/4] 🎨 ComfyUI...${NC}"
    if [ "$(test_comfyui)" = "YES" ]; then
        echo -e "  ${GREEN}[OK] Ya activo${NC}"
    else
        cd "$COMFYUI_DIR"
        nohup ./venv/bin/python main.py --listen --port 8188 &> "$LOG_DIR/comfyui.log" &
        echo -n "  ⏳ Esperando"
        for i in $(seq 1 45); do
            sleep 1
            if [ "$(test_comfyui)" = "YES" ]; then
                echo -e "\n  ${GREEN}[OK] Iniciado${NC}"
                break
            fi
            [ $((i % 10)) -eq 0 ] && echo -n " ${i}s"
        done
        [ "$(test_comfyui)" != "YES" ] && echo -e "\n  ${YELLOW}[WARN] Puede tardar más${NC}"
    fi

    # 3. InvokeAI
    echo -e "\n${BOLD}[3/4] 🖼️  InvokeAI...${NC}"
    if [ "$(test_invokeai)" = "YES" ]; then
        echo -e "  ${GREEN}[OK] Ya activo${NC}"
    else
        source "$INVOKEAI_ENV/bin/activate" 2>/dev/null
        cd "$INVOKEAI_DIR" 2>/dev/null || cd ~
        nohup invokeai-web --root "$INVOKEAI_DIR" &>/dev/null &
        disown
        sleep 5
        [ "$(test_invokeai)" = "YES" ] && echo -e "  ${GREEN}[OK] Iniciado${NC}" || echo -e "  ${YELLOW}[WARN] No respondió aún${NC}"
    fi

    # 4. Hermes
    echo -e "\n${BOLD}[4/4] 🧠 Hermes Agent (3 desktop)...${NC}"
    if [ "$(test_hermes)" = "YES" ]; then
        echo -e "  ${GREEN}[OK] Ya activo${NC}"
    else
        export PATH="$HOME/.local/bin:$PATH"
        mkdir -p "$HOME/.hermes/logs"

        for s in hermes-gateway hermes-tui hermes-dashboard; do
            tmux kill-session -t "$s" 2>/dev/null
        done
        pkill -f "hermes dashboard" 2>/dev/null || true

        tmux new-session -d -s hermes-gateway \
            "source ~/.bashrc 2>/dev/null; hermes gateway run 2>&1 | tee $HOME/.hermes/logs/gateway.log; bash"
        tmux new-session -d -s hermes-tui \
            "source ~/.bashrc 2>/dev/null; hermes --tui 2>&1 | tee $HOME/.hermes/logs/tui.log; bash"
        tmux new-session -d -s hermes-dashboard \
            "hermes dashboard --port 9119 --no-open 2>&1 | tee $HOME/.hermes/logs/dashboard.log; bash"

        sleep 3
        echo -e "  ${GREEN}[OK] 3 interfaces iniciadas${NC}"
    fi

    # ── Summary ──
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}              ${GREEN}✅  TODAS LAS IAs ACTIVAS${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Ollama       → http://localhost:11434                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🎨 ComfyUI      → http://localhost:8188                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🖼️  InvokeAI     → http://localhost:9090                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Hermes Dash  → http://localhost:9119                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Hermes TUI   → tmux attach -t hermes-tui            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🤖 Agentes Python (bajo demanda):                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}     bash launch_agent.sh advise                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}     bash launch_autogen.sh design <cat>                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}     bash launch_pipeline.sh --category <cats>            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🛑 detener: bash launch_ias.sh stop                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  📊 estado:  bash launch_ias.sh status                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
case "${1:-start}" in
    status|check)
        status_all
        ;;
    stop)
        stop_all
        ;;
    start)
        if [ -n "${2:-}" ]; then
            start_single "$2"
        else
            start_all
        fi
        ;;
    *)
        echo "Uso: launch_ias.sh {start [servicio]|stop|status}"
        echo "  start          — Inicia todos los servicios"
        echo "  start ollama   — Inicia solo Ollama"
        echo "  stop           — Detiene todos los servicios"
        echo "  status         — Muestra estado de todos"
        exit 1
        ;;
esac
