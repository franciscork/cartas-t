#!/usr/bin/env bash
# =============================================================================
# SIMMOON — IAS (Intelligent Agent System) Launcher
# Lanzador unificado para TODAS las IAs del ecosistema SIMMOON.
# Reemplaza: launch_ias.sh, launch_all.sh, launch_ollama.sh, launch_hermes.sh,
#            launch_openhuman.sh, launch_jarvis.sh, launch_simmoon.py
#
# Servicios:
#   🧠 Ollama       :11434 — LLM server local
#   🖌️  InvokeAI     :9090  — Generación de imágenes
#   🧠 Hermes        :9119  — Agente 3 escritorios (gateway + TUI + dash)
#   🤖 OpenHuman     :7788  — Asistente AI con GUI
#   💬 Jarvis         :6900  — Asistente AI CLI
#   📊 Dashboard     :5000  — Monitor web
#   🗄️  PostgreSQL    :5432  — Base de datos
#
# Uso:
#   ias                    # Modo interactivo (menú)
#   ias start              # Inicia todos los backends
#   ias start ollama       # Inicia solo Ollama
#   ias stop               # Detiene todo
#   ias status             # Estado de todos los servicios
#   ias restart            # Reinicia todo
#   ias backup             # Backup de PostgreSQL
#   ias models             # Lista modelos Ollama
# =============================================================================
set -euo pipefail

# ── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'
DIM='\033[2m'; NC='\033[0m'

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIMMOON_DIR="$SCRIPT_DIR/Simmoon_arc"
LOG_DIR="$HOME/.simmoon-logs"
INVOKEAI_DIR="$HOME/invokeai"
COMFYUI_DIR="$HOME/ComfyUI"
OPENHUMAN_DIR="$HOME/openhuman"
JARVIS_DIR="$HOME/OpenJarvis"
HERMES_LOG_DIR="$HOME/.hermes/logs"

mkdir -p "$LOG_DIR" "$HERMES_LOG_DIR" 2>/dev/null

# ── Health Check Helpers ──────────────────────────────────────────────────
_test_port() {
    local port="$1" path="${2:-/}" timeout="${3:-2}"
    curl -sf --max-time "$timeout" "http://localhost:$port$path" &>/dev/null && echo "YES" || echo "NO"
}
_test_ollama()   { _test_port 11434 "/api/tags"; }
_test_invokeai() { _test_port 9090 "/api/v1/app/version"; }
_test_comfyui()  { _test_port 8188 "/queue"; }
_test_hermes()   { _test_port 9119; }
_test_openhuman(){ _test_port 7788 "/health"; }
_test_openhuman_desktop() {
    command -v openhuman-core &>/dev/null && echo "YES" || echo "NO"
}
_test_jarvis()   {
    # Jarvis is CLI-only (no HTTP server) — check if binary exists
    [ -d "$JARVIS_DIR" ] && echo "YES" || echo "NO"
}
_test_telegram_bot() {
    tmux has-session -t telegram-bot 2>/dev/null && echo "YES" || echo "NO"
}
_test_buffy_telegram() {
    tmux has-session -t buffy-telegram 2>/dev/null && echo "YES" || echo "NO"
}
_test_agatha() {
    tmux has-session -t agatha-actas 2>/dev/null && echo "YES" || echo "NO"
}
_test_dashboard(){ _test_port 5000; }
_test_postgres() {
    pg_isready -q -h localhost -p 5432 &>/dev/null && echo "YES" || echo "NO"
}

_service_status() {
    local name="$1" port="$2" testfn="$3"
    if [ "$($testfn)" = "YES" ]; then
        echo -e "  ${GREEN}🟢${NC} ${name} ${DIM}→ :${port}${NC}"
    else
        echo -e "  ${RED}⚫${NC} ${name}"
    fi
}

# ── Banner ─────────────────────────────────────────────────────────────────
_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}       ${BOLD}☾  SIMMOON  —  IAS Launcher${NC}                        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}       ${DIM}Intelligent Agent System${NC}                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ── GPU Info ───────────────────────────────────────────────────────────────
_gpu_info() {
    if command -v nvidia-smi &>/dev/null; then
        nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total,utilization.gpu \
            --format=csv,noheader,nounits 2>/dev/null | while IFS=',' read -r name temp mem_used mem_total util; do
            name=$(echo "$name" | xargs)
            temp=$(echo "$temp" | xargs)
            mem_used=$(echo "$mem_used" | xargs)
            mem_total=$(echo "$mem_total" | xargs)
            util=$(echo "$util" | xargs)
            echo -e "  🎮 ${name} | ${temp}°C | VRAM: ${mem_used}/${mem_total} MB | GPU: ${util}%"
        done
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
#  STATUS
# ═══════════════════════════════════════════════════════════════════════════
cmd_status() {
    _banner
    echo -e "${BOLD}📊 Estado de Servicios:${NC}"
    echo ""
    _service_status "🧠 Ollama      " "11434" _test_ollama
    _service_status "🖌️  InvokeAI    " "9090"  _test_invokeai
    _service_status "🤖 OpenHuman   " "7788"  _test_openhuman
    _service_status "📊 Dashboard   " "5000"  _test_dashboard
    _service_status "🗄️  PostgreSQL  " "5432"  _test_postgres
    _service_status "🤖 Telegram Bot " "tmux" _test_telegram_bot
    _service_status "📋 Agatha Actas " "tmux" _test_agatha
    _service_status "🖥️  OpenHuman Desk" "WSL" _test_openhuman_desktop

    echo ""
    _gpu_info

    echo ""
    echo -e "${BOLD}📋 Agentes Python:${NC}"
    [ -f "$SIMMOON_DIR/simmoon_agent.py" ]    && echo -e "  ${GREEN}✅${NC} Simmoon Agent   ${DIM}(ias agent)${NC}"    || echo -e "  ${RED}❌${NC} Simmoon Agent"
    [ -f "$SIMMOON_DIR/simmoon_autogen.py" ]  && echo -e "  ${GREEN}✅${NC} AutoGen          ${DIM}(ias autogen)${NC}"  || echo -e "  ${RED}❌${NC} AutoGen"
    [ -f "$SIMMOON_DIR/simmoon_pipeline.py" ] && echo -e "  ${GREEN}✅${NC} Pipeline         ${DIM}(ias pipeline)${NC}" || echo -e "  ${RED}❌${NC} Pipeline"
    [ -f "$SIMMOON_DIR/monitor_sistema.py" ]  && echo -e "  ${GREEN}✅${NC} Monitor Sistema  ${DIM}(ias monitor)${NC}"  || echo -e "  ${RED}❌${NC} Monitor"
    [ -f "$SIMMOON_DIR/telegram_bot.py" ]    && echo -e "  ${GREEN}✅${NC} Telegram Bot     ${DIM}(ias telegram)${NC}" || echo -e "  ${RED}❌${NC} Telegram Bot"
    [ -f "$SIMMOON_DIR/buffy_telegram.py" ]  && echo -e "  ${GREEN}✅${NC} Buffy Bridge      ${DIM}(ias buffy)${NC}" || echo -e "  ${RED}❌${NC} Buffy Bridge"
    [ -f "$SIMMOON_DIR/agatha_actas.py" ]    && echo -e "  ${GREEN}✅${NC} Agatha Actas     ${DIM}(ias agatha)${NC}" || echo -e "  ${RED}❌${NC} Agatha Actas"
    [ -f "$SIMMOON_DIR/dashboard.py" ]        && echo -e "  ${GREEN}✅${NC} Dashboard        ${DIM}(ias dashboard)${NC}" || echo -e "  ${RED}❌${NC} Dashboard"

    # Ollama models
    if [ "$(_test_ollama)" = "YES" ]; then
        echo ""
        echo -e "${BOLD}📦 Modelos Ollama:${NC}"
        curl -s "http://localhost:11434/api/tags" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
for m in d.get('models',[]):
    size_gb = m.get('size',0)/(1024**3)
    print(f\"  • {m['name']:40s} {size_gb:.1f} GB\")
" 2>/dev/null || echo "  (no se pudieron listar)"
    fi

    echo ""
    echo -e "${DIM}Comandos: ias start | ias stop | ias start <servicio> | ias${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  STOP
# ═══════════════════════════════════════════════════════════════════════════
cmd_stop() {
    local target="${1:-all}"

    if [ "$target" = "all" ]; then
        echo -e "${YELLOW}🛑 Deteniendo TODOS los servicios...${NC}"
        echo ""
        for svc in ollama invokeai openhuman telegram agatha dashboard; do
            _stop_one "$svc"
        done
        echo ""
        echo -e "${GREEN}✅ Todos los servicios detenidos${NC}"
        echo ""
    else
        _stop_one "$target"
    fi
}

_stop_one() {
    local svc="$1"
    case "$svc" in
        ollama)
            echo -n "  ⏹ Ollama... "
            pkill -f "ollama serve" 2>/dev/null && echo "OK" || echo "ya detenido"
            ;;
        invokeai)
            echo -n "  ⏹ InvokeAI... "
            pkill -f "invokeai-web" 2>/dev/null && echo "OK" || echo "ya detenido"
            ;;
        comfyui)
            echo -n "  ⏹ ComfyUI... "
            pkill -f "main.py.*--port 8188" 2>/dev/null && echo "OK" || echo "ya detenido"
            ;;
        hermes)
            echo -n "  ⏹ Hermes... "
            for s in hermes-gateway hermes-tui hermes-dashboard; do
                tmux kill-session -t "$s" 2>/dev/null
            done
            pkill -f "hermes dashboard" 2>/dev/null || true
            pkill -f "hermes gateway" 2>/dev/null || true
            echo "OK"
            ;;
        openhuman)
            echo -n "  ⏹ OpenHuman... "
            pkill -f "openhuman-core" 2>/dev/null && echo "OK" || echo "ya detenido"
            ;;
        jarvis)
            echo -n "  ⏹ Jarvis... "
            pkill -f "uv run jarvis" 2>/dev/null && echo "OK" || echo "ya detenido"
            ;;
        telegram)
            echo -n "  ⏹ Telegram Bot... "
            tmux kill-session -t telegram-bot 2>/dev/null
            pkill -f "telegram_bot.py" 2>/dev/null || true
            echo "OK"
            ;;
        buffy)
            echo -n "  ⏹ Buffy Bridge... "
            tmux kill-session -t buffy-telegram 2>/dev/null
            pkill -f "buffy_telegram.py" 2>/dev/null || true
            echo "OK"
            ;;
        agatha)
            echo -n "  ⏹ Agatha Actas... "
            tmux kill-session -t agatha-actas 2>/dev/null
            pkill -f "agatha_actas.py" 2>/dev/null || true
            echo "OK"
            ;;
        dashboard)
            echo -n "  ⏹ Dashboard... "
            pkill -f "dashboard.py" 2>/dev/null && echo "OK" || echo "ya detenido"
            ;;
        *)
            echo "  ❓ Servicio desconocido: $svc"
            echo "     Opciones: ollama, invokeai, comfyui, openhuman, telegram, agatha, dashboard"
            ;;
    esac
}

# ═══════════════════════════════════════════════════════════════════════════
#  START
# ═══════════════════════════════════════════════════════════════════════════
cmd_start() {
    local target="${1:-all}"

    if [ "$target" = "all" ]; then
        _banner
        _start_backends
        _show_summary
    else
        _start_one "$target"
    fi
}

_start_backends() {
    # 1. Ollama
    echo -e "${BOLD}[1/8] 🧠 Ollama${NC}"
    if [ "$(_test_ollama)" = "YES" ]; then
        echo -e "  ${GREEN}✅ Ya activo en :11434${NC}"
    else
        nohup ollama serve &>"$LOG_DIR/ollama.log" &
        echo -n "  ⏳ Esperando"
        for i in $(seq 1 15); do
            sleep 1; echo -n "."
            [ "$(_test_ollama)" = "YES" ] && break
        done
        if [ "$(_test_ollama)" = "YES" ]; then
            echo -e "\n  ${GREEN}✅ Iniciado${NC}"
        else
            echo -e "\n  ${YELLOW}⚠️  No respondió — verifica $LOG_DIR/ollama.log${NC}"
        fi
    fi

    # 2. PostgreSQL
    echo -e "\n${BOLD}[2/8] 🗄️  PostgreSQL${NC}"
    if [ "$(_test_postgres)" = "YES" ]; then
        echo -e "  ${GREEN}✅ Ya activo en :5432${NC}"
    else
        sudo systemctl start postgresql 2>/dev/null || sudo service postgresql start 2>/dev/null
        if [ "$(_test_postgres)" = "YES" ]; then
            echo -e "  ${GREEN}✅ Iniciado${NC}"
        else
            echo -e "  ${YELLOW}⚠️  No se pudo iniciar${NC}"
        fi
    fi

    # 3. InvokeAI
    echo -e "\n${BOLD}[3/8] 🖌️  InvokeAI${NC}"
    if [ "$(_test_invokeai)" = "YES" ]; then
        echo -e "  ${GREEN}✅ Ya activo en :9090${NC}"
    elif [ -d "$INVOKEAI_DIR" ]; then
        cd "$INVOKEAI_DIR"
        nohup invokeai-web --host 0.0.0.0 --port 9090 &>"$LOG_DIR/invokeai.log" &
        echo -n "  ⏳ Esperando"
        for i in $(seq 1 20); do
            sleep 1; echo -n "."
            [ "$(_test_invokeai)" = "YES" ] && break
        done
        if [ "$(_test_invokeai)" = "YES" ]; then
            echo -e "\n  ${GREEN}✅ Iniciado${NC}"
        else
            echo -e "\n  ${YELLOW}⚠️  Sigue cargando — verifica con: ias status${NC}"
        fi
    else
        echo -e "  ${DIM}⏭️  InvokeAI no encontrado en $INVOKEAI_DIR${NC}"
    fi

    # 4. OpenHuman (opcional — solo si está instalado)
    echo -e "\n${BOLD}[4/8] 🤖 OpenHuman${NC}"
    if [ "$(_test_openhuman)" = "YES" ]; then
        echo -e "  ${GREEN}✅ Ya activo en :7788${NC}"
    elif [ -f "$OPENHUMAN_DIR/openhuman-core" ]; then
        export LD_LIBRARY_PATH="$OPENHUMAN_DIR:${LD_LIBRARY_PATH:-}"
        export OLLAMA_BASE_URL="http://localhost:11434"
        export DISPLAY="${DISPLAY:-:0}"
        nohup "$OPENHUMAN_DIR/openhuman-core" run --jsonrpc-only --host 0.0.0.0 --port 7788 &>"$LOG_DIR/openhuman.log" &
        sleep 5
        echo -e "  ${GREEN}✅ Iniciado en :7788${NC}"
    else
        echo -e "  ${DIM}⏭️  No instalado${NC}"
    fi

    # 5. Dashboard (siempre)
    echo -e "\n${BOLD}[5/8] 📊 Dashboard${NC}"
    if [ "$(_test_dashboard)" = "YES" ]; then
        echo -e "  ${GREEN}✅ Ya activo en :5000${NC}"
    elif [ -f "$SIMMOON_DIR/dashboard.py" ]; then
        cd "$SIMMOON_DIR"
        nohup python3 dashboard.py &>"$LOG_DIR/dashboard.log" &
        sleep 2
        echo -e "  ${GREEN}✅ http://localhost:5000${NC}"
    else
        echo -e "  ${DIM}⏭️  dashboard.py no encontrado${NC}"
    fi

    # 6. Telegram Bot
    echo -e "\n${BOLD}[6/8] 🤖 Telegram Bot${NC}"
    if [ "$(_test_telegram_bot)" = "YES" ]; then
        echo -e "  ${GREEN}✅ Ya activo (sesión tmux: telegram-bot)${NC}"
    elif [ -f "$SIMMOON_DIR/telegram_bot.py" ]; then
        tmux kill-session -t telegram-bot 2>/dev/null || true
        cd "$SIMMOON_DIR"
        tmux new-session -d -s telegram-bot \
            "cd '$SIMMOON_DIR' && python3 telegram_bot.py 2>&1 | tee $LOG_DIR/telegram_bot.log; bash"
        sleep 3
        if [ "$(_test_telegram_bot)" = "YES" ]; then
            echo -e "  ${GREEN}✅ Iniciado (sesión: telegram-bot)${NC}"
        else
            echo -e "  ${YELLOW}⚠️  No arrancó — verifica: cat $LOG_DIR/telegram_bot.log${NC}"
        fi
    else
        echo -e "  ${DIM}⏭️  telegram_bot.py no encontrado${NC}"
    fi

    # 7. Agatha Actas
    echo -e "\n${BOLD}[7/8] 📋 Agatha Actas${NC}"
    if [ "$(_test_agatha)" = "YES" ]; then
        echo -e "  ${GREEN}✅ Ya activo (sesión tmux: agatha-actas)${NC}"
    elif [ -f "$SIMMOON_DIR/agatha_actas.py" ]; then
        tmux kill-session -t agatha-actas 2>/dev/null || true
        cd "$SIMMOON_DIR"
        tmux new-session -d -s agatha-actas \
            "cd '$SIMMOON_DIR' && python3 agatha_actas.py --daemon 2>&1 | tee $LOG_DIR/agatha_actas.log; bash"
        sleep 3
        if [ "$(_test_agatha)" = "YES" ]; then
            echo -e "  ${GREEN}✅ Iniciado (sesión: agatha-actas)${NC}"
        else
            echo -e "  ${YELLOW}⚠️  No arrancó — verifica: cat $LOG_DIR/agatha_actas.log${NC}"
        fi
    else
        echo -e "  ${DIM}⏭️  agatha_actas.py no encontrado${NC}"
    fi

    # 8. Coding Agents (verificación)
    echo -e "\n${BOLD}[8/8] 🤖 Coding Agents${NC}"
    command -v aider &>/dev/null && echo -e "  🧑‍✈️ Aider      ${GREEN}✅ disponible${NC}" || echo -e "  🧑‍✈️ Aider      ${YELLOW}⚠️  no en PATH${NC}"
    command -v goose &>/dev/null && echo -e "  🪿 goose      ${GREEN}✅ disponible${NC}" || echo -e "  🪿 goose      ${YELLOW}⚠️  no en PATH${NC}"
}

_start_one() {
    local svc="$1"
    case "$svc" in
        ollama)
            if [ "$(_test_ollama)" = "YES" ]; then
                echo -e "${GREEN}🧠 Ollama ya activo en :11434${NC}"
            else
                nohup ollama serve &>"$LOG_DIR/ollama.log" &
                sleep 3
                echo -e "${GREEN}🧠 Ollama iniciado${NC}"
            fi
            ;;
        invokeai)
            if [ "$(_test_invokeai)" = "YES" ]; then
                echo -e "${GREEN}🖌️  InvokeAI ya activo en :9090${NC}"
            elif [ -d "$INVOKEAI_DIR" ]; then
                cd "$INVOKEAI_DIR"
                nohup invokeai-web --host 0.0.0.0 --port 9090 &>"$LOG_DIR/invokeai.log" &
                echo -e "${GREEN}🖌️  InvokeAI iniciando... (ias status para verificar)${NC}"
            else
                echo -e "${RED}InvokeAI no encontrado en $INVOKEAI_DIR${NC}"
            fi
            ;;
        comfyui)
            if [ "$(_test_comfyui)" = "YES" ]; then
                echo -e "${GREEN}🎨 ComfyUI ya activo en :8188${NC}"
            else
                cd "$COMFYUI_DIR" 2>/dev/null || { echo -e "${RED}ComfyUI no encontrado${NC}"; return 1; }
                nohup ./venv/bin/python main.py --listen --port 8188 &>"$LOG_DIR/comfyui.log" &
                echo -e "${GREEN}🎨 ComfyUI iniciando... (ias status para verificar)${NC}"
            fi
            ;;
        hermes)
            cmd_start_hermes
            ;;
        openhuman)
            if [ "$(_test_openhuman)" = "YES" ]; then
                echo -e "${GREEN}🤖 OpenHuman ya activo en :7788${NC}"
            elif [ -f "$OPENHUMAN_DIR/openhuman-core" ]; then
                export LD_LIBRARY_PATH="$OPENHUMAN_DIR:${LD_LIBRARY_PATH:-}"
                nohup "$OPENHUMAN_DIR/openhuman-core" run --jsonrpc-only --host 0.0.0.0 --port 7788 &>"$LOG_DIR/openhuman.log" &
                echo -e "${GREEN}🤖 OpenHuman iniciado en :7788${NC}"
            else
                echo -e "${RED}OpenHuman no instalado${NC}"
            fi
            ;;
        jarvis)
            if [ -d "$JARVIS_DIR" ]; then
                cd "$JARVIS_DIR"
                export PATH="$HOME/.local/bin:$PATH"
                echo -e "${GREEN}💬 Jarvis — ejecutando...${NC}"
                uv run jarvis chat
            else
                echo -e "${RED}Jarvis no instalado en $JARVIS_DIR${NC}"
            fi
            ;;
        telegram)
            if [ "$(_test_telegram_bot)" = "YES" ]; then
                echo -e "${GREEN}🤖 Telegram Bot ya activo (sesión: telegram-bot)${NC}"
            elif [ -f "$SIMMOON_DIR/telegram_bot.py" ]; then
                if ! command -v python3 &>/dev/null; then
                    echo -e "${RED}❌ python3 no encontrado en PATH${NC}"
                    return 1
                fi
                tmux kill-session -t telegram-bot 2>/dev/null || true
                tmux new-session -d -s telegram-bot \
                    "cd '$SIMMOON_DIR' && python3 telegram_bot.py 2>&1 | tee $LOG_DIR/telegram_bot.log; bash"
                sleep 3
                if [ "$(_test_telegram_bot)" = "YES" ]; then
                    echo -e "${GREEN}🤖 Telegram Bot iniciado (sesión: telegram-bot)${NC}"
                else
                    echo -e "${YELLOW}⚠️  No arrancó — verifica: cat $LOG_DIR/telegram_bot.log${NC}"
                fi
            else
                echo -e "${RED}telegram_bot.py no encontrado${NC}"
            fi
            ;;
        buffy)
            if [ "$(_test_buffy_telegram)" = "YES" ]; then
                echo -e "${GREEN}🤖 Buffy Bridge ya activo (sesión: buffy-telegram)${NC}"
            elif [ -f "$SIMMOON_DIR/buffy_telegram.py" ]; then
                if ! command -v python3 &>/dev/null; then
                    echo -e "${RED}❌ python3 no encontrado en PATH${NC}"
                    return 1
                fi
                tmux kill-session -t buffy-telegram 2>/dev/null || true
                tmux new-session -d -s buffy-telegram \
                    "cd '$SIMMOON_DIR' && python3 buffy_telegram.py --daemon 2>&1 | tee $LOG_DIR/buffy_telegram.log; bash"
                sleep 3
                if [ "$(_test_buffy_telegram)" = "YES" ]; then
                    echo -e "${GREEN}🤖 Buffy Bridge iniciado (sesión: buffy-telegram)${NC}"
                else
                    echo -e "${YELLOW}⚠️  No arrancó — verifica: cat $LOG_DIR/buffy_telegram.log${NC}"
                fi
            else
                echo -e "${RED}buffy_telegram.py no encontrado${NC}"
            fi
            ;;
        agatha)
            if [ "$(_test_agatha)" = "YES" ]; then
                echo -e "${GREEN}📋 Agatha Actas ya activo (sesión: agatha-actas)${NC}"
            elif [ -f "$SIMMOON_DIR/agatha_actas.py" ]; then
                if ! command -v python3 &>/dev/null; then
                    echo -e "${RED}❌ python3 no encontrado en PATH${NC}"
                    return 1
                fi
                tmux kill-session -t agatha-actas 2>/dev/null || true
                tmux new-session -d -s agatha-actas \
                    "cd '$SIMMOON_DIR' && python3 agatha_actas.py --daemon 2>&1 | tee $LOG_DIR/agatha_actas.log; bash"
                sleep 3
                if [ "$(_test_agatha)" = "YES" ]; then
                    echo -e "${GREEN}📋 Agatha Actas iniciado (sesión: agatha-actas)${NC}"
                else
                    echo -e "${YELLOW}⚠️  No arrancó — verifica: cat $LOG_DIR/agatha_actas.log${NC}"
                fi
            else
                echo -e "${RED}agatha_actas.py no encontrado${NC}"
            fi
            ;;
        bot)
            _start_one telegram
            _start_one agatha
            return 0
            ;;
        dashboard)
            if [ "$(_test_dashboard)" = "YES" ]; then
                echo -e "${GREEN}📊 Dashboard ya activo en :5000${NC}"
            elif [ -f "$SIMMOON_DIR/dashboard.py" ]; then
                cd "$SIMMOON_DIR"
                nohup python3 dashboard.py &>"$LOG_DIR/dashboard.log" &
                sleep 2
                echo -e "${GREEN}📊 Dashboard → http://localhost:5000${NC}"
            else
                echo -e "${RED}dashboard.py no encontrado${NC}"
            fi
            ;;
        *)
            echo -e "${YELLOW}Servicio desconocido: $svc${NC}"
            echo "  Opciones: ollama, invokeai, openhuman, dashboard, telegram, agatha, bot"
            return 1
            ;;
    esac
}

cmd_start_hermes() {
    echo -e "${MAGENTA}🧠 Iniciando Hermes (3 escritorios)...${NC}"
    export PATH="$HOME/.local/bin:$PATH"
    mkdir -p "$HERMES_LOG_DIR"

    if ! command -v hermes &>/dev/null; then
        echo -e "  ${DIM}⏭️  Hermes CLI no encontrado en PATH${NC}"
        return 1
    fi

    for s in hermes-gateway hermes-tui hermes-dashboard; do
        tmux kill-session -t "$s" 2>/dev/null
    done
    pkill -f "hermes dashboard" 2>/dev/null || true

    tmux new-session -d -s hermes-gateway \
        "source ~/.bashrc 2>/dev/null; hermes gateway run 2>&1 | tee $HERMES_LOG_DIR/gateway.log; bash"
    tmux new-session -d -s hermes-tui \
        "source ~/.bashrc 2>/dev/null; hermes --tui 2>&1 | tee $HERMES_LOG_DIR/tui.log; bash"
    tmux new-session -d -s hermes-dashboard \
        "hermes dashboard --port 9119 --no-open 2>&1 | tee $HERMES_LOG_DIR/dashboard.log; bash"

    sleep 3
    echo -e "  ${GREEN}✅ Gateway + TUI + Dashboard activos${NC}"
    echo -e "  ${CYAN}🌐 Dashboard → http://localhost:9119${NC}"
    echo -e "  ${CYAN}🖥️  TUI → tmux attach -t hermes-tui${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════
#  AGENTS
# ═══════════════════════════════════════════════════════════════════════════
cmd_agent() {
    if [ ! -f "$SIMMOON_DIR/simmoon_agent.py" ]; then
        echo -e "${RED}❌ simmoon_agent.py no encontrado${NC}"
        return 1
    fi
    cd "$SIMMOON_DIR"
    python3 simmoon_agent.py "${@}"
}

cmd_autogen() {
    if [ ! -f "$SIMMOON_DIR/simmoon_autogen.py" ]; then
        echo -e "${RED}❌ simmoon_autogen.py no encontrado${NC}"
        return 1
    fi
    cd "$SIMMOON_DIR"
    python3 simmoon_autogen.py "${@}"
}

cmd_pipeline() {
    if [ ! -f "$SIMMOON_DIR/simmoon_pipeline.py" ]; then
        echo -e "${RED}❌ simmoon_pipeline.py no encontrado${NC}"
        return 1
    fi
    cd "$SIMMOON_DIR"
    python3 simmoon_pipeline.py "${@}"
}

cmd_monitor() {
    if [ ! -f "$SIMMOON_DIR/monitor_sistema.py" ]; then
        echo -e "${RED}❌ monitor_sistema.py no encontrado${NC}"
        return 1
    fi
    cd "$SIMMOON_DIR"
    python3 monitor_sistema.py "${@}"
}

cmd_models() {
    if [ "$(_test_ollama)" != "YES" ]; then
        echo -e "${RED}❌ Ollama no está corriendo. Inícialo: ias start ollama${NC}"
        return 1
    fi
    echo -e "${BOLD}📦 Modelos disponibles en Ollama:${NC}"
    echo ""
    curl -s "http://localhost:11434/api/tags" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
models = d.get('models',[])
if not models:
    print('  (ninguno — descarga con: ollama pull <modelo>)')
for m in models:
    name = m['name']
    size_gb = m.get('size',0)/(1024**3)
    family = m.get('details',{}).get('family','')
    param_size = m.get('details',{}).get('parameter_size','')
    extra = f' ({param_size})' if param_size else ''
    print(f'  • {name:40s} {size_gb:5.1f} GB{extra}')
" 2>/dev/null || echo "  (error al listar)"
    echo ""
}

cmd_backup() {
    if [ -f "$HOME/backup_postgres.sh" ]; then
        bash "$HOME/backup_postgres.sh"
    else
        echo -e "${RED}❌ backup_postgres.sh no encontrado en ~/${NC}"
        return 1
    fi
}

cmd_restart() {
    cmd_stop all
    sleep 2
    cmd_start all
}

# ═══════════════════════════════════════════════════════════════════════════
#  INTERACTIVE MENU
# ═══════════════════════════════════════════════════════════════════════════
cmd_menu() {
    while true; do
        clear 2>/dev/null || true
        _banner
        echo -e "${BOLD}📊 Estado:${NC}"
        echo ""
        _service_status "🧠 Ollama      " "11434" _test_ollama
        _service_status "🖌️  InvokeAI    " "9090"  _test_invokeai
        _service_status "🤖 OpenHuman   " "7788"  _test_openhuman
        _service_status "📊 Dashboard   " "5000"  _test_dashboard
        _service_status "🗄️  PostgreSQL  " "5432"  _test_postgres
        _service_status "🤖 Telegram Bot " "tmux" _test_telegram_bot
        _service_status "📋 Agatha Actas " "tmux" _test_agatha
        _service_status "🖥️  OpenHuman Desk" "WSL" _test_openhuman_desktop

        echo ""
        echo -e "${CYAN}──────────────────────────────────────────────────────────${NC}"
        echo -e "  ${BOLD}[a]${NC} Start ALL        ${BOLD}[s]${NC} Stop ALL         ${BOLD}[r]${NC} Restart ALL"
        echo -e "  ${BOLD}[1]${NC} Ollama           ${BOLD}[2]${NC} InvokeAI         ${BOLD}[3]${NC} PostgreSQL"
        echo -e "  ${BOLD}[4]${NC} OpenHuman        ${BOLD}[5]${NC} Dashboard        ${BOLD}[6]${NC} Telegram Bot"
        echo -e "  ${BOLD}[7]${NC} Agatha Actas     ${BOLD}[8]${NC} All Bots         ${BOLD}[m]${NC} Models"
        echo -e "  ${BOLD}[b]${NC} Backup DB        ${BOLD}[q]${NC} Quit"
        echo -e "${CYAN}──────────────────────────────────────────────────────────${NC}"
        echo ""

        read -r -p "  > " choice
        choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')

        case "$choice" in
            q|quit|exit) break ;;
            a|all)  cmd_start all ;;
            s|stop) cmd_stop all ;;
            r|restart) cmd_restart ;;
            1) _start_one ollama ;;
            2) _start_one invokeai ;;
            3) sudo systemctl start postgresql 2>/dev/null || sudo service postgresql start 2>/dev/null; [ "$(_test_postgres)" = "YES" ] && echo -e "${GREEN}✅ PostgreSQL iniciado${NC}" || echo -e "${RED}❌ Error${NC}" ;;
            4) _start_one openhuman ;;
            5) _start_one dashboard ;;
            6) _start_one telegram ;;
            7) _start_one agatha ;;
            8) _start_one bot ;;
            m|models) cmd_models ;;
            b|backup) cmd_backup ;;
            g|gpu) _gpu_info ;;
            *) echo -e "${YELLOW}Opción no reconocida${NC}" ;;
        esac

        echo ""
        read -r -p "  Presiona Enter para continuar..." _
    done
}

# ═══════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
_show_summary() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}              ${GREEN}✅  TODAS LAS IAs ACTIVAS${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🧠 Ollama       → http://localhost:11434                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🖌️  InvokeAI     → http://localhost:9090                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🤖 OpenHuman    → http://localhost:7788                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  📊 Dashboard    → http://localhost:5000                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🤖 Telegram Bot → tmux attach -t telegram-bot           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  📋 Agatha Actas → tmux attach -t agatha-actas           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  🛑 Detener: ias stop                                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  📊 Estado:  ias status                                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  📋 Logs:    $LOG_DIR/                     ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  HELP
# ═══════════════════════════════════════════════════════════════════════════
cmd_help() {
    echo ""
    echo -e "${BOLD}☾  SIMMOON — IAS Launcher${NC}"
    echo ""
    echo -e "${BOLD}Uso:${NC}"
    echo "  ias                        Modo interactivo (menú)"
    echo "  ias start                  Inicia todos los servicios backend"
    echo "  ias start <servicio>       Inicia un servicio específico"
    echo "  ias stop                   Detiene todos los servicios"
    echo "  ias stop <servicio>        Detiene un servicio específico"
    echo "  ias status                 Estado de todos los servicios"
    echo "  ias restart                Reinicia todos los servicios"
    echo "  ias backup                 Backup de PostgreSQL"
    echo "  ias models                 Lista modelos Ollama"
    echo ""
    echo -e "${BOLD}Servicios:${NC}"
    echo "  ollama      LLM server local           :11434"
    echo "  invokeai    Generación de imágenes      :9090"
    echo "  openhuman   Asistente AI GUI            :7788"
    echo "  dashboard   Monitor web                 :5000"
    echo "  telegram    Bot multi-agente Telegram    tmux"
    echo "  agatha      Agente reportes horarios     tmux"
    echo "  bot         Inicia Telegram + Agatha juntos"
    echo ""
    echo -e "${BOLD}Agentes Python:${NC}"
    echo "  ias agent [args]       Simmoon Agent (AI Director)"
    echo "  ias autogen [args]     AutoGen (diseño multi-agente)"
    echo "  ias pipeline [args]    Pipeline (LangGraph workflow)"
    echo "  ias monitor [args]     Monitor de sistema"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
case "${1:-menu}" in
    # Menu
    menu|"")
        cmd_menu
        ;;
    # Start
    start)
        cmd_start "${2:-all}"
        ;;
    # Stop
    stop)
        cmd_stop "${2:-all}"
        ;;
    # Status
    status|check|ps)
        cmd_status
        ;;
    # Restart
    restart)
        cmd_restart
        ;;
    # Hermes
    hermes)
        cmd_start_hermes
        ;;
    # Agents
    agent)
        shift
        cmd_agent "$@"
        ;;
    autogen)
        shift
        cmd_autogen "$@"
        ;;
    pipeline)
        shift
        cmd_pipeline "$@"
        ;;
    # Tools
    monitor)
        shift
        cmd_monitor "$@"
        ;;
    models|list)
        cmd_models
        ;;
    backup|dump)
        cmd_backup
        ;;
    # Help
    help|-h|--help)
        cmd_help
        ;;
    *)
        echo -e "${YELLOW}Comando no reconocido: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
