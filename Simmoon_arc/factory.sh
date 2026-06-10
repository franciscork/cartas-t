#!/usr/bin/env bash
# =============================================================================
# @factory FACTORY GAMES — Orchestrator Launcher
# Sistema de orquestación para el ecosistema Simmoon.
# Supervisado por: Buffy (DeepSeek)
#
# Instalación:
#   python Simmoon_arc/_install_factory_sh.py   # Copia a ~/ y agrega alias
#
# Uso (una vez instalado):
#   factory                    Menú interactivo
#   factory status             Estado del sistema
#   factory agents             Listar agentes
#   factory coding "tarea"     Delegar tarea de código
#   factory image "prompt"     Generar imagen
#   factory llm "consulta"     Consultar LLM local
#   factory recover <servicio> Recuperar servicio caído
#   factory session            Resumen de sesión
#   factory dashboard          Abrir dashboard v2
#   factory help               Ayuda detallada
# =============================================================================
set -uo pipefail

# ── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'
DIM='\033[2m'; NC='\033[0m'

# ── Path Resolution ────────────────────────────────────────────────────────
# Estrategia de búsqueda (en orden):
#   1. Variable de entorno SIMMOON_DIR (si el usuario la definió)
#   2. Relativo a este script (funciona si factory.sh está en ~/ o en Simmoon_arc/)
#   3. Relativo a la carpeta actual
#   4. Path absoluto por defecto en home
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "${SIMMOON_DIR:-}" ] && [ -f "$SIMMOON_DIR/factory.py" ]; then
    FACTORY_DIR="$SIMMOON_DIR"
elif [ -f "$_SCRIPT_DIR/Simmoon_arc/factory.py" ]; then
    FACTORY_DIR="$_SCRIPT_DIR/Simmoon_arc"
elif [ -f "$_SCRIPT_DIR/factory.py" ]; then
    FACTORY_DIR="$_SCRIPT_DIR"
elif [ -f "$HOME/Simmoon_arc/factory.py" ]; then
    FACTORY_DIR="$HOME/Simmoon_arc"
elif [ -f "$(pwd)/Simmoon_arc/factory.py" ]; then
    FACTORY_DIR="$(pwd)/Simmoon_arc"
else
    echo -e "${RED}[ERROR] No se encuentra Simmoon_arc/factory.py${NC}"
    echo -e "  Busqué en:"
    echo -e "    - \$SIMMOON_DIR/factory.py"
    echo -e "    - $_SCRIPT_DIR/Simmoon_arc/factory.py"
    echo -e "    - $_SCRIPT_DIR/factory.py"
    echo -e "    - $HOME/Simmoon_arc/factory.py"
    echo -e "  Sugerencia: export SIMMOON_DIR=/ruta/a/Simmoon_arc"
    exit 1
fi

FACTORY_PY="$FACTORY_DIR/factory.py"
DASHBOARD_V2="$FACTORY_DIR/dashboard_v2.py"

# ── Helpers ─────────────────────────────────────────────────────────────────
_factory_cmd() {
    local cmd="$1"; shift
    cd "$FACTORY_DIR" 2>/dev/null || {
        echo -e "  ${RED}[ERROR] No se encuentra $FACTORY_DIR${NC}"; return 1
    }
    python "$FACTORY_PY" "$cmd" "$@"
}

_test_port() {
    local port="$1" path="${2:-/}" timeout="${3:-2}"
    curl -sf --max-time "$timeout" "http://localhost:$port$path" &>/dev/null && echo "YES" || echo "NO"
}

# ── Última ejecución de pipeline ────────────────────────────────────────
_show_last_pipeline() {
    local json_file="$FACTORY_DIR/.last_pipeline.json"
    [ ! -f "$json_file" ] && echo -e "  ${DIM}⚫${NC} Pipeline           ${DIM}(sin ejecuciones previas)${NC}" && return

    local ts duration cats gen pix db
    ts=$(grep -o '"timestamp": *"[^"]*"' "$json_file" 2>/dev/null | head -1 | sed 's/.*"\(.*\)"/\1/')
    duration=$(grep -o '"duration_min": *[0-9.]*' "$json_file" 2>/dev/null | head -1 | sed 's/.*: *//')
    cats=$(grep -o '"cat_count": *[0-9]*' "$json_file" 2>/dev/null | head -1 | sed 's/.*: *//')
    gen=$(grep -o '"gen_count": *"[^"]*"' "$json_file" 2>/dev/null | head -1 | sed 's/.*"\(.*\)"/\1/')
    pix=$(grep -o '"pix_count": *"[^"]*"' "$json_file" 2>/dev/null | head -1 | sed 's/.*"\(.*\)"/\1/')
    db=$(grep -o '"db_status": *"[^"]*"' "$json_file" 2>/dev/null | head -1 | sed 's/.*"\(.*\)"/\1/')

    # Estado con grep -q para evitar capturar output extra
    local icon="${GREEN}✅${NC}"
    if ! grep -q '"success": *true' "$json_file" 2>/dev/null; then
        icon="${RED}❌${NC}"
    fi

    local time_str="${duration:-0}m"
    [ "${duration%.*}" = "0" ] && time_str="<1m"

    local cats_str="${cats:-?} cats"

    echo -e "  ${icon} Pipeline           ${DIM}${cats_str} · ${time_str} · gen:${gen:-?} pix:${pix:-?} db:${db:-?}${NC}"
}

_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}       ${BOLD}🏭  FACTORY GAMES — Orchestrator${NC}                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}       ${DIM}Supervisado por: Buffy (DeepSeek)${NC}                ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  COMANDOS
# ═══════════════════════════════════════════════════════════════════════════

cmd_status() {
    _banner
    echo -e "${BOLD}📊 Estado del Sistema de Orquestación:${NC}" ""
    [ ! -f "$FACTORY_PY" ] && echo -e "  ${RED}[ERROR] factory.py no encontrado${NC}" && return 1
    _factory_cmd status
}

cmd_agents() {
    [ ! -f "$FACTORY_PY" ] && echo -e "${RED}[ERROR] factory.py no encontrado${NC}" && return 1
    _factory_cmd agents
}

cmd_delegate() {
    local task_type="${1:-}"; shift 2>/dev/null || true
    local task="${*:-}"
    if [ -z "$task_type" ] || [ -z "$task" ]; then
        echo -e "${YELLOW}Uso: factory <coding|image|llm|pipeline> \"descripción de la tarea\"${NC}"
        return 1
    fi
    echo -e "  ${CYAN}🚀 Delegando tarea a ${BOLD}$task_type${NC}..." ""
    _factory_cmd delegate "$task_type" "$task"
}

cmd_pipeline() {
    if [ $# -eq 0 ]; then
        echo -e "${YELLOW}Uso: factory pipeline <categoria1> [categoria2] ...${NC}"
        echo -e "     factory pipeline businesses vehicles"
        echo -e "     factory pipeline greenhouses --run-suffix dreamshaper_v8"
        return 1
    fi
    echo -e "  ${CYAN}🔧 Ejecutando pipeline de generación...${NC}" ""
    _factory_cmd pipeline "$@"
}

cmd_recover() {
    local service="${1:-}"
    [ -z "$service" ] && echo -e "${YELLOW}Uso: factory recover <servicio>${NC}" && return 1
    echo -e "  ${YELLOW}🔄 Recuperando servicio: ${BOLD}$service${NC}..."
    _factory_cmd recover "$service"
}

cmd_session() {
    [ ! -f "$FACTORY_PY" ] && echo -e "${RED}[ERROR] factory.py no encontrado${NC}" && return 1
    _factory_cmd session
}

cmd_dashboard() {
    if [ ! -f "$DASHBOARD_V2" ]; then
        echo -e "${RED}[ERROR] dashboard_v2.py no encontrado en:${NC}"
        echo -e "     $DASHBOARD_V2"
        echo -e "${YELLOW}¿Quieres abrir el dashboard original en :5000?${NC}"
        (start http://localhost:5000 2>/dev/null || true)
        return 1
    fi
    if [ "$(_test_port 5001)" = "YES" ]; then
        echo -e "${GREEN}✅ Dashboard v2 activo en http://localhost:5001${NC}"
    else
        echo -e "  ${CYAN}🚀 Iniciando Dashboard v2 en :5001...${NC}"
        cd "$FACTORY_DIR" && nohup python "$DASHBOARD_V2" &>/dev/null &
        sleep 2
        echo -e "  ${GREEN}✅ http://localhost:5001 ${DIM}(abriendo navegador)${NC}"
    fi
    (start http://localhost:5001 2>/dev/null || xdg-open http://localhost:5001 &>/dev/null || true)
}

cmd_help() {
    echo ""
    echo -e "${BOLD}🏭  FACTORY GAMES — Orquestador${NC}"
    echo -e "${DIM}Supervisado por: Buffy (DeepSeek)${NC}" ""
    echo -e "${BOLD}Uso:${NC}"
    echo -e "  ${GREEN}factory${NC}                     Menú interactivo"
    echo -e "  ${GREEN}factory status${NC}              Estado del sistema de orquestación"
    echo -e "  ${GREEN}factory agents${NC}              Listar agentes registrados"
    echo -e "  ${GREEN}factory coding \"...\"${NC}       Delegar tarea de código"
    echo -e "  ${GREEN}factory image \"...\"${NC}         Generar imagen"
    echo -e "  ${GREEN}factory llm \"...\"${NC}           Consultar LLM local"
    echo -e "  ${GREEN}factory recover <svc>${NC}       Recuperar servicio caído"
    echo -e "  ${GREEN}factory pipeline <cats>${NC}     Ejecutar pipeline de assets"
    echo -e "  ${GREEN}factory session${NC}             Resumen de sesión"
    echo -e "  ${GREEN}factory dashboard${NC}            Abrir dashboard v2"
    echo -e "  ${GREEN}factory help${NC}                Esta ayuda" ""
    echo -e "${BOLD}Agentes disponibles:${NC}"
    echo -e "  🤖 ${BOLD}coding${NC}     claude-code     — refactor, implement, debug, test, review"
    echo -e "  🖼️  ${BOLD}image${NC}      comfyui         — generación (fallback: invokeai)"
    echo -e "  🧠 ${BOLD}llm${NC}         ollama          — inferencia local"
    echo -e "  🔧 ${BOLD}pipeline${NC}   simmoon-pipeline — assets: ComfyUI → Pixel → DB"
    echo -e "  🔌 ${BOLD}service${NC}    postgresql, telegram, agatha"
    echo -e "  👨‍🔧 ${BOLD}supervisor${NC}  buffy           — el orquestador mismo" ""
    echo -e "${BOLD}Ejemplos:${NC}"
    echo -e "  ${DIM}\$ factory pipeline businesses vehicles${NC}"
    echo -e "  ${DIM}\$ factory pipeline greenhouses --run-suffix dreamshaper_v8${NC}"
    echo -e "  ${DIM}\$ factory coding \"refactoriza el módulo de economía\"${NC}"
    echo -e "  ${DIM}\$ factory image \"un castillo medieval al atardecer\"${NC}"
    echo -e "  ${DIM}\$ factory llm \"resume el estado del sistema\"${NC}"
    echo -e "  ${DIM}\$ factory recover ollama${NC}" ""
    echo -e "${BOLD}📡 Estado:${NC}"
    echo -n "  🐍 factory.py: "
    [ -f "$FACTORY_PY" ] && echo -e "${GREEN}✅ Encontrado${NC}" || echo -e "${RED}❌ No encontrado${NC}"
    echo -n "  📊 dashboard_v2.py: "
    [ -f "$DASHBOARD_V2" ] && echo -e "${GREEN}✅ Encontrado${NC}" || echo -e "${RED}❌ No encontrado${NC}"
    echo -n "  🖥️  Dashboard v2 (:5001): "
    [ "$(_test_port 5001)" = "YES" ] && echo -e "${GREEN}✅ Activo${NC}" || true
    echo ""
    echo -e "${DIM}Para cambiar la ruta del proyecto: export SIMMOON_DIR=/ruta/a/Simmoon_arc${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
#  MENÚ INTERACTIVO
# ═══════════════════════════════════════════════════════════════════════════
cmd_menu() {
    while true; do
        clear 2>/dev/null || true
        _banner
        echo -e "${BOLD}📡 Salud del Sistema:${NC}" ""
        [ -f "$FACTORY_PY" ] && echo -e "  ${GREEN}✅${NC} factory.py        ${DIM}(orquestador listo)${NC}" \
                              || echo -e "  ${RED}❌${NC} factory.py        ${DIM}(no encontrado)${NC}"
        if [ "$(_test_port 5001)" = "YES" ]; then
            echo -e "  ${GREEN}✅${NC} Dashboard v2      ${DIM}(:5001)${NC}"
        else
            echo -e "  ${DIM}⚫${NC} Dashboard v2      ${DIM}(inactivo)${NC}"
        fi
        if [ "$(_test_port 11434 "/api/tags")" = "YES" ]; then
            echo -e "  ${GREEN}✅${NC} Ollama LLM        ${DIM}(:11434)${NC}"
        else
            echo -e "  ${DIM}⚫${NC} Ollama LLM        ${DIM}(inactivo)${NC}"
        fi
        if [ "$(_test_port 8188 "/queue")" = "YES" ]; then
            echo -e "  ${GREEN}✅${NC} ComfyUI           ${DIM}(:8188)${NC}"
        else
            echo -e "  ${DIM}⚫${NC} ComfyUI           ${DIM}(inactivo)${NC}"
        fi
        _show_last_pipeline
        echo ""
        echo -e "${CYAN}──────────────────────────────────────────────────────────${NC}"
        echo -e "  ${BOLD}[1]${NC} Status      ${BOLD}[2]${NC} Agents      ${BOLD}[3]${NC} Dashboard"
        echo -e "  ${BOLD}[4]${NC} Coding      ${BOLD}[5]${NC} Image       ${BOLD}[6]${NC} LLM"
        echo -e "  ${BOLD}[7]${NC} Recover     ${BOLD}[8]${NC} Session     ${BOLD}[p]${NC} Pipeline"
        echo -e "  ${BOLD}[h]${NC} Help                          ${BOLD}[q]${NC} Salir"
        echo -e "${CYAN}──────────────────────────────────────────────────────────${NC}" ""
        read -r -p "  > " choice
        choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')

        case "$choice" in
            q|quit|exit) break ;;
            1|status)    _factory_cmd status ;;
            2|agents)    _factory_cmd agents ;;
            3|dashboard) cmd_dashboard ;;
            4|coding)    read -r -p "  Describe la tarea: " t; [ -n "$t" ] && cmd_delegate coding "$t" || echo -e "${YELLOW}Tarea vacía${NC}" ;;
            5|image)     read -r -p "  Describe la imagen: " p; [ -n "$p" ] && cmd_delegate image "$p" || echo -e "${YELLOW}Prompt vacío${NC}" ;;
            6|llm)       read -r -p "  Tu consulta: " q; [ -n "$q" ] && cmd_delegate llm "$q" || echo -e "${YELLOW}Consulta vacía${NC}" ;;
            7|recover)   read -r -p "  Servicio: " s; [ -n "$s" ] && cmd_recover "$s" || echo -e "${YELLOW}Servicio vacío${NC}" ;;
            8|session)   _factory_cmd session ;;
            p|pipeline)  read -r -p "  Categorias (ej: businesses vehicles): " cats; [ -n "$cats" ] && cmd_pipeline $cats || echo -e "${YELLOW}Categorias vacias${NC}" ;;
            h|help)      cmd_help ;;
            *) echo -e "${YELLOW}Opción no reconocida${NC}" ;;
        esac
        echo ""; read -r -p "  Presiona Enter para continuar..." _
    done
}

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
case "${1:-menu}" in
    menu|"")     cmd_menu ;;
    status|check) cmd_status ;;
    agents|list) cmd_agents ;;
    pipeline) shift; cmd_pipeline "$@" ;;
    coding|code) shift; cmd_delegate coding "$*" ;;
    image|img|generate) shift; cmd_delegate image "$*" ;;
    llm|ask|query) shift; cmd_delegate llm "$*" ;;
    delegate)    shift; cmd_delegate "$@" ;;
    recover|repair) cmd_recover "${2:-}" ;;
    session)     _factory_cmd session ;;
    dashboard|dash|ui) cmd_dashboard ;;
    help|-h|--help) cmd_help ;;
    *)
        echo -e "${YELLOW}Comando no reconocido: $1${NC}"
        echo -e "  Usa: ${GREEN}factory help${NC}"
        exit 1
        ;;
esac
