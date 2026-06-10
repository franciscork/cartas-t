#!/usr/bin/env bash
# =============================================================================
# SIMMOON — AutoGen Launcher (WSL2)
# Lanza el sistema multi-agente de diseño colaborativo
# 3 agentes: Generator + Critic + Curator
# =============================================================================
set -euo pipefail

MAGENTA='\033[0;35m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTOGEN="$SCRIPT_DIR/simmoon_autogen.py"
MODEL="${2:-qwen3-coder}"

if [ ! -f "$AUTOGEN" ]; then
    echo -e "${RED}❌ No se encuentra: $AUTOGEN${NC}"
    exit 1
fi

case "${1:-chat}" in
    design)
        shift
        echo -e "${BOLD}${MAGENTA}🤖 AutoGen — Sesión de diseño${NC}"
        echo -e "   Agentes: Generator + Critic + Curator"
        python3 "$AUTOGEN" --design "$@" --model "$MODEL"
        ;;
    quick)
        shift
        echo -e "${BOLD}${MAGENTA}⚡ AutoGen — Sugerencia rápida${NC}"
        python3 "$AUTOGEN" --quick "$@" --model "$MODEL"
        ;;
    list|categories)
        python3 "$AUTOGEN" --list-categories
        ;;
    chat|interactive)
        echo -e "${BOLD}${MAGENTA}🤖 AutoGen — Modo interactivo${NC}"
        echo -e "   Comandos: design <cat> | quick [cat] | list | quit"
        python3 "$AUTOGEN" --model "$MODEL"
        ;;
    *)
        echo "Uso: launch_autogen.sh {design <cat>|quick [cat]|list|chat}"
        exit 1
        ;;
esac
