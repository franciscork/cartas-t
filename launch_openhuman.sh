#!/usr/bin/env bash
# =============================================================================
# launch_openhuman.sh — Inicia OpenHuman con Ollama backend
# Uso: bash launch_openhuman.sh [--no-gui]
# =============================================================================

set -euo pipefail

OPENHUMAN_DIR="$HOME/openhuman"
OPENHUMAN_BIN="$OPENHUMAN_DIR/openhuman-core"
OPENHUMAN_PORT="${OPENHUMAN_CORE_PORT:-7788}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

export LD_LIBRARY_PATH="$OPENHUMAN_DIR:${LD_LIBRARY_PATH:-}"
export DISPLAY="${DISPLAY:-:0}"
export OLLAMA_BASE_URL="$OLLAMA_URL"
export OPENHUMAN_CORE_PORT="$OPENHUMAN_PORT"

if [ ! -f "$OPENHUMAN_BIN" ]; then
    echo "[ERROR] OpenHuman binary not found at $OPENHUMAN_BIN"
    echo "  Install: see Guia_OpenHuman_Primeros_Pasos.md"
    exit 1
fi

# Check if Ollama is running
if ! curl -s --max-time 2 "$OLLAMA_URL/api/tags" &>/dev/null; then
    echo "[WARN] Ollama not responding at $OLLAMA_URL"
    echo "  Start it: ollama serve &"
fi

echo "══════════════════════════════════════════════"
echo "  OpenHuman — Launching..."
echo "  Binary     : $OPENHUMAN_BIN"
echo "  Port       : $OPENHUMAN_PORT"
echo "  Ollama     : $OLLAMA_URL"
echo "  DISPLAY    : $DISPLAY"
echo "══════════════════════════════════════════════"

if [ "${1:-}" = "--no-gui" ]; then
    echo "  Mode: headless (API-only via JSON-RPC)"
    exec "$OPENHUMAN_BIN" run --jsonrpc-only --host 0.0.0.0 --port "$OPENHUMAN_PORT"
else
    echo "  Mode: GUI + API (fallback: headless si no hay display)"
    if [ -z "${DISPLAY:-}" ] || [ "$DISPLAY" = ":0" ] && ! xdpyinfo &>/dev/null 2>&1; then
        echo "  ⚠️  No display available, starting in headless mode"
        exec "$OPENHUMAN_BIN" run --jsonrpc-only --host 0.0.0.0 --port "$OPENHUMAN_PORT"
    else
        exec "$OPENHUMAN_BIN"
    fi
fi
