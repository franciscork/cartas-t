#!/usr/bin/env bash
# =============================================================================
# SIMMOON — Pipeline Launcher (WSL2)
# Lanza el pipeline LangGraph: ComfyUI → Pixel Art → PostgreSQL
# =============================================================================
set -euo pipefail

CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIPELINE="$SCRIPT_DIR/simmoon_pipeline.py"

if [ ! -f "$PIPELINE" ]; then
    echo -e "${RED}❌ No se encuentra: $PIPELINE${NC}"
    exit 1
fi

echo -e "${BOLD}${CYAN}🔄 SIMMOON Pipeline — LangGraph Workflow${NC}"
echo -e "   ComfyUI → Pixel Art → PostgreSQL"

python3 "$PIPELINE" "$@"
