#!/usr/bin/env bash
# =============================================================================
# SIMMOON — AI Agent Launcher (WSL2)
# Lanza el agente de IA que analiza assets y recomienda qué generar
# =============================================================================
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT="$SCRIPT_DIR/simmoon_agent.py"
MODEL="${2:-qwen3.5:9b}"

if [ ! -f "$AGENT" ]; then
    echo -e "${RED}❌ No se encuentra: $AGENT${NC}"
    exit 1
fi

case "${1:-advise}" in
    advise)
        echo -e "${BOLD}🧠 Simmoon Agent — Consultando AI Director...${NC}"
        python3 "$AGENT" --advise --model "$MODEL"
        ;;
    scan)
        echo -e "${BOLD}📊 Simmoon Agent — Escaneando assets...${NC}"
        python3 "$AGENT" --scan
        ;;
    list|models)
        python3 "$AGENT" --list-models
        ;;
    generate)
        shift
        echo -e "${BOLD}🎨 Simmoon Agent — Generando...${NC}"
        python3 "$AGENT" --generate "$@" --model "$MODEL"
        ;;
    *)
        echo "Uso: launch_agent.sh {advise|scan|list|generate [--category X --checkpoint Y]}"
        exit 1
        ;;
esac
