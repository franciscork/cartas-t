#!/usr/bin/env bash
# =============================================================================
# SIMMOON — Launch ALL IAs (WSL2)
# Lanzadera unificada para todos los servicios de IA
#
# ⚠️  GPU: RTX 4070 Laptop (8GB VRAM) — NO pueden coexistir Ollama + ComfyUI
#     El orquestador GPU de Telegram (/gen, /gpu_free) gestiona la VRAM.
#     Esta lanzadera respeta ese límite: por defecto solo inicia agentes texto.
#
# Servicios:
#   🧠 Ollama       — LLM server (puerto 11434)
#   🎨 ComfyUI      — Generación de imágenes (puerto 8188) [bajo demanda]
#   🖼️  InvokeAI     — Generación alternativa (puerto 9090)
#   🧠 Hermes       — Agente con 3 escritorios (puerto 9119)
#   🤖 Agent        — AI director de assets
#   🤖 AutoGen      — Diseño multi-agente
#   🔄 Pipeline     — Workflow LangGraph
#
# Uso:
#   bash launch_ias.sh                # Inicia [smart]: Ollama + Hermes (texto)
#   bash launch_ias.sh start text     # Solo agentes de texto (seguro)
#   bash launch_ias.sh start art      # Libera Ollama VRAM → lanza ComfyUI
#   bash launch_ias.sh start all      # ⚠️ Legacy: todo a la vez (puede OOM)
#   bash launch_ias.sh status         # Estado
#   bash launch_ias.sh stop           # Detiene todo
#   bash launch_ias.sh start ollama   # Inicia solo Ollama
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

# ── VRAM helpers ──────────────────────────────────────────────
check_vram() {
    # Devuelve VRAM usada en MB, o -1 si nvidia-smi no disponible
    if command -v nvidia-smi &>/dev/null; then
        nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null || echo "-1"
    else
        echo "-1"
    fi
}

unload_ollama_vram() {
    # Libera VRAM de Ollama vía API (keep_alive=0).
    # Consulta /api/ps para obtener el modelo cargado actualmente.
    local ollama_url="${OLLAMA_URL:-http://localhost:11434}"
    local model="${1:-}"
    # Si no se pasó modelo, detectar el que está cargado
    if [ -z "$model" ]; then
        model=$(curl -s --max-time 3 "$ollama_url/api/ps" 2>/dev/null | \
                grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
        [ -z "$model" ] && model="deepseek-r1:7b"  # fallback: modelo pequeño siempre disponible
    fi
    curl -s --max-time 5 "$ollama_url/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$model\",\"prompt\":\"\",\"keep_alive\":0}" &>/dev/null
    return $?
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
#  START SINGLE (con VRAM warnings)
# ═══════════════════════════════════════════════════════════════
start_single() {
    local svc="$1"
    case "$svc" in
        ollama)
            [ -f "$SCRIPT_DIR/launch_ollama.sh" ] && bash "$SCRIPT_DIR/launch_ollama.sh" start
            ;;
        comfyui)
            # ── VRAM check antes de lanzar ComfyUI ──
            local vram=$(check_vram)
            if [ "$vram" != "-1" ] && [ "$vram" -gt 4000 ] 2>/dev/null; then
                echo -e "  ${YELLOW}⚠️  VRAM en uso: ${vram}MB${NC}"
                echo -e "  ${YELLOW}   Ollama parece estar cargado en GPU.${NC}"
                echo -e "  ${YELLOW}   Lanzar ComfyUI ahora puede causar CUDA OOM.${NC}"
                echo ""
                echo -n "  ¿Liberar VRAM de Ollama primero? (s/N): "
                read -r answer
                if [ "$answer" = "s" ] || [ "$answer" = "S" ]; then
                    echo -e "  🧹 Liberando VRAM de Ollama..."
                    unload_ollama_vram
                    sleep 2
                    vram=$(check_vram)
                    echo -e "  ${GREEN}   VRAM tras liberar: ${vram}MB${NC}"
                else
                    echo -e "  ${YELLOW}   Continuando sin liberar — riesgo de OOM.${NC}"
                fi
            fi
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
#  START ART — libera Ollama VRAM y lanza ComfyUI
# ═══════════════════════════════════════════════════════════════
start_art() {
    echo ""
    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}       ${BOLD}🎨  SIMMOON  —  Art Mode (ComfyUI)${NC}                 ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}                                                          ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  Ollama → RAM (overflow 32GB) · ComfyUI → GPU (8GB)     ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local vram_before=$(check_vram)
    if [ "$vram_before" != "-1" ]; then
        echo -e "  🎮 VRAM antes: ${vram_before}MB / 8192MB"
    fi

    # 1. Asegurar Ollama corriendo (pero liberar su VRAM)
    echo -e "${BOLD}[1/3] 🧠 Ollama...${NC}"
    if [ "$(test_ollama)" != "YES" ]; then
        echo -e "  Iniciando Ollama..."
        nohup ollama serve &>/dev/null &
        sleep 3
        [ "$(test_ollama)" = "YES" ] && echo -e "  ${GREEN}[OK] Iniciado${NC}" || echo -e "  ${YELLOW}[WARN]${NC}"
    else
        echo -e "  ${GREEN}[OK] Ya activo${NC}"
    fi

    # 2. Liberar VRAM de Ollama
    echo -e "\n${BOLD}[2/3] 🧹 Liberando VRAM de Ollama...${NC}"
    if [ "$(test_ollama)" = "YES" ]; then
        echo -e "  Enviando keep_alive=0 a Ollama..."
        unload_ollama_vram
        sleep 2
        local vram_mid=$(check_vram)
        local freed=$((vram_before - vram_mid))
        if [ "$vram_mid" != "-1" ]; then
            echo -e "  ${GREEN}VRAM: ${vram_mid}MB (${freed}MB liberados)${NC}"
        else
            echo -e "  ${GREEN}[OK] Ollama descargado de GPU${NC}"
        fi
    else
        echo -e "  ${YELLOW}Ollama no está corriendo, no hay VRAM que liberar${NC}"
    fi

    # 3. Lanzar ComfyUI
    echo -e "\n${BOLD}[3/3] 🎨 ComfyUI...${NC}"
    if [ "$(test_comfyui)" = "YES" ]; then
        echo -e "  ${GREEN}[OK] Ya activo${NC}"
    else
        cd "$COMFYUI_DIR" 2>/dev/null || { echo -e "  ${RED}[ERROR] $COMFYUI_DIR no existe${NC}"; return 1; }
        nohup ./venv/bin/python main.py --listen --port 8188 --lowvram &> "$LOG_DIR/comfyui.log" &
        echo -n "  ⏳ Esperando"
        for i in $(seq 1 60); do
            sleep 1
            if [ "$(test_comfyui)" = "YES" ]; then
                echo -e "\n  ${GREEN}[OK] Iniciado${NC}"
                break
            fi
            [ $((i % 15)) -eq 0 ] && echo -n " ${i}s"
        done
        [ "$(test_comfyui)" != "YES" ] && echo -e "\n  ${YELLOW}[WARN] Tarda más de lo esperado${NC}"
    fi

    # ── Summary ──
    local vram_after=$(check_vram)
    echo ""
    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}           ${GREEN}✅  MODO ARTE ACTIVO${NC}                          ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${MAGENTA}║${NC}                                                          ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  🎨 ComfyUI      → http://localhost:8188                 ${MAGENTA}║${NC}"
    if [ "$vram_after" != "-1" ]; then
        echo -e "${MAGENTA}║${NC}  🎮 VRAM: ${vram_after}MB / 8192MB                              ${MAGENTA}║${NC}"
    fi
    echo -e "${MAGENTA}║${NC}  🧠 Ollama modelo descargado de GPU.                    ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}     No chatees con Ollama durante generación.           ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}                                                          ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ⚠️  Para restaurar Ollama a GPU:                        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}     Telegram → /gpu_restore                              ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}     O simplemente chatea — se recarga solo               ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════
#  START ALL (legacy) — ⚠️ puede causar CUDA OOM
# ═══════════════════════════════════════════════════════════════
start_all_legacy() {
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC}  ${BOLD}⚠️  MODO LEGACY: TODO A LA VEZ${NC}                         ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}                                                          ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  Con 8GB VRAM, Ollama + ComfyUI juntos = CUDA OOM       ${YELLOW}║${NC}"
    echo -e "${YELLOW}║${NC}  Usa 'start smart' o 'start art' en su lugar.            ${YELLOW}║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -n "  ¿Continuar de todos modos? (s/N): "
    read -r answer
    if [ "$answer" != "s" ] && [ "$answer" != "S" ]; then
        echo -e "  ${GREEN}Cancelado. Usa: bash launch_ias.sh (smart)${NC}"
        return 0
    fi
    echo ""

    # Ollama
    if [ "$(test_ollama)" != "YES" ]; then
        nohup ollama serve &>/dev/null &
        sleep 3
    fi

    # ComfyUI
    if [ "$(test_comfyui)" != "YES" ]; then
        cd "$COMFYUI_DIR" 2>/dev/null
        nohup ./venv/bin/python main.py --listen --port 8188 &> "$LOG_DIR/comfyui.log" &
        sleep 5
    fi

    # Hermes
    if [ "$(test_hermes)" != "YES" ]; then
        export PATH="$HOME/.local/bin:$PATH"
        mkdir -p "$HOME/.hermes/logs"
        tmux new-session -d -s hermes-gateway \
            "source ~/.bashrc 2>/dev/null; hermes gateway run 2>&1 | tee $HOME/.hermes/logs/gateway.log; bash"
        tmux new-session -d -s hermes-dashboard \
            "hermes dashboard --port 9119 --no-open 2>&1 | tee $HOME/.hermes/logs/dashboard.log; bash"
    fi

    echo -e "${GREEN}✅ Servicios lanzados (legacy). Monitorea VRAM con /gpu.${NC}"
}

# ═══════════════════════════════════════════════════════════════
#  START SMART (default) — solo agentes de texto
# ═══════════════════════════════════════════════════════════════
start_smart() {
    # ── Banner ──
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}       ${BOLD}☾  SIMMOON  —  Smart Launch (Texto)${NC}                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Ollama + 🧠 Hermes  ·  GPU compartida (texto)       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🎨 ComfyUI → /gen en Telegram (orquestador GPU)        ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local vram=$(check_vram)
    if [ "$vram" != "-1" ]; then
        echo -e "  🎮 VRAM disponible: ~$((8192 - vram))MB libre de 8192MB"
        echo ""
    fi

    # 1. Ollama
    echo -e "${BOLD}[1/2] 🧠 Ollama...${NC}"
    if [ "$(test_ollama)" = "YES" ]; then
        echo -e "  ${GREEN}[OK] Ya activo${NC}"
    else
        nohup ollama serve &>/dev/null &
        sleep 3
        [ "$(test_ollama)" = "YES" ] && echo -e "  ${GREEN}[OK] Iniciado${NC}" || echo -e "  ${YELLOW}[WARN] No respondió${NC}"
    fi

    # 2. Hermes
    echo -e "\n${BOLD}[2/2] 🧠 Hermes Agent (3 desktop)...${NC}"
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
    echo -e "${CYAN}║${NC}           ${GREEN}✅  AGENTES DE TEXTO ACTIVOS${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Ollama       → http://localhost:11434                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Hermes Dash  → http://localhost:9119                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Hermes TUI   → tmux attach -t hermes-tui            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🎨 Para generar imágenes:                               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}     Telegram → /gen <prompt>  (orquestador GPU)         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}     Terminal → bash launch_ias.sh start art              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🛑 detener: bash launch_ias.sh stop                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  📊 estado:  bash launch_ias.sh status                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
case "${1:-smart}" in
    status|check)
        status_all
        ;;
    stop)
        stop_all
        ;;
    start)
        case "${2:-smart}" in
            smart|"")
                start_smart
                ;;
            text)
                start_smart
                ;;
            art)
                start_art
                ;;
            all)
                start_all_legacy
                ;;
            *)
                start_single "$2"
                ;;
        esac
        ;;
    smart|text)
        start_smart
        ;;
    art)
        start_art
        ;;
    all)
        start_all_legacy
        ;;
    *)
        echo "Uso: launch_ias.sh {start [modo]|stop|status}"
        echo ""
        echo "  🧠 Modos (respetan VRAM 8GB):"
        echo "    smart (default)  — Ollama + Hermes (agentes texto, seguro)"
        echo "    text             — Igual que smart"
        echo "    art              — Libera Ollama VRAM → lanza ComfyUI"
        echo "    all              — ⚠️  Legacy: todo a la vez (puede OOM)"
        echo ""
        echo "  🎯 Servicios individuales:"
        echo "    start ollama     — Solo Ollama"
        echo "    start comfyui    — ComfyUI (con VRAM check)"
        echo "    start hermes     — Solo Hermes Agent"
        echo ""
        echo "  🛑 stop            — Detiene todo"
        echo "  📊 status          — Estado de todos"
        exit 1
        ;;
esac
