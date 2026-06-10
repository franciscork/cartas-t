#!/usr/bin/env bash
# =============================================================================
# SIMMOON Launch All — WSL2 (FALLBACK)
# Inicia: Ollama + ComfyUI + VoteAPI + chequea Simmoon pipeline
#
# PREFERIDO: sudo systemctl start simmoon.target
#   Gestión individual:
#     sudo systemctl start|stop|restart simmoon-voteapi.service
#     sudo systemctl start|stop|restart simmoon-comfyui.service
#     sudo systemctl start|stop|restart ollama-simmoon.service
#   Logs: journalctl -u simmoon-voteapi.service -f
#
# Este script es un fallback para desarrollo/testing.
# Uso:    bash ~/launch_all.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

COMFYUI_DIR="$HOME/ComfyUI"
COMFYUI_PORT=8188
OLLAMA_PORT=11434
VOTE_API_PORT=9099
SIMMOON_DIR="$HOME/Simmoon_arc"
VENV_DIR="$HOME/simmoon-env"
LOG_DIR="$HOME/.simmoon-logs"

cleanup() {
  echo -e "\n${YELLOW}[!] Shutting down services...${NC}"
  [ -n "${OLLAMA_PID:-}" ] && kill "$OLLAMA_PID" 2>/dev/null && echo "  Ollama stopped"
  [ -n "${COMFYUI_PID:-}" ] && kill "$COMFYUI_PID" 2>/dev/null && echo "  ComfyUI stopped"
  [ -n "${VOTEAPI_PID:-}" ] && kill "$VOTEAPI_PID" 2>/dev/null && echo "  VoteAPI stopped"
  echo -e "${GREEN}[OK] Clean exit${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

mkdir -p "$LOG_DIR"

# ── BANNER ────────────────────────────────────────────────────────────────
echo -e "${CYAN}"
echo '  ╔══════════════════════════════════════════════╗'
echo '  ║       ☾  SIMMOON  —  LAUNCH ALL              ║'
echo '  ║                                              ║'
echo '  ║  Ollama · ComfyUI · Simmoon · VoteAPI        ║'
echo '  ╚══════════════════════════════════════════════╝'
echo -e "${NC}"

# ── STEP 1: OLLAMA ───────────────────────────────────────────────────────
echo -e "${BOLD}[1/4] Starting Ollama...${NC}"

# Check if systemd service is active (preferred)
if systemctl is-active ollama-simmoon.service &>/dev/null; then
  echo -e "  ${GREEN}[OK] Ollama running via systemd (ollama-simmoon.service)${NC}"
elif curl -s --max-time 2 http://localhost:$OLLAMA_PORT/api/tags &>/dev/null; then
  echo -e "  ${GREEN}[OK] Ollama already running on port $OLLAMA_PORT${NC}"
else
  ollama serve &> "$LOG_DIR/ollama.log" &
  OLLAMA_PID=$!
  echo -n "  Waiting for Ollama"
  for i in $(seq 1 15); do
    if curl -s --max-time 1 http://localhost:$OLLAMA_PORT/api/tags &>/dev/null; then
      echo -e "\n  ${GREEN}[OK] Ollama started (PID $OLLAMA_PID)${NC}"
      break
    fi
    echo -n "."
    sleep 1
  done
  if ! curl -s --max-time 1 http://localhost:$OLLAMA_PORT/api/tags &>/dev/null; then
    echo -e "\n  ${YELLOW}[WARN] Ollama did not respond in time${NC}"
    echo -e "  ${YELLOW}       Enable systemd: sudo systemctl enable --now ollama-simmoon.service${NC}"
  fi
fi

# Show available models
if curl -s --max-time 2 http://localhost:$OLLAMA_PORT/api/tags &>/dev/null; then
  MODELS=$(curl -s --max-time 5 http://localhost:$OLLAMA_PORT/api/tags 2>/dev/null | python3 -c '
import sys,json
d=json.load(sys.stdin)
for m in d.get("models",[]):
    print("    " + m["name"])
' 2>/dev/null || echo "    (could not parse)")
  echo -e "  Models:\n${MODELS:- (none)}"
fi

# ── STEP 2: COMFYUI ────────────────────────────────────────────────────
echo -e "\n${BOLD}[2/4] Starting ComfyUI...${NC}"

if curl -s --max-time 2 http://localhost:$COMFYUI_PORT/queue &>/dev/null; then
  echo -e "  ${GREEN}[OK] ComfyUI already running on port $COMFYUI_PORT${NC}"
else
  if [ ! -f "$COMFYUI_DIR/main.py" ]; then
    echo -e "  ${RED}[ERROR] ComfyUI not found at $COMFYUI_DIR${NC}"
    echo -e "  ${YELLOW}[HINT] Install: cd ~ && git clone https://github.com/comfyanonymous/ComfyUI${NC}"
  else
    cd "$COMFYUI_DIR"
    nohup ./venv/bin/python main.py --listen --port $COMFYUI_PORT \
      &> "$LOG_DIR/comfyui.log" &
    COMFYUI_PID=$!
    echo -n "  Waiting for ComfyUI"
    for i in $(seq 1 60); do
      if curl -s --max-time 2 http://localhost:$COMFYUI_PORT/queue &>/dev/null; then
        echo -e "\n  ${GREEN}[OK] ComfyUI started (PID $COMFYUI_PID) — http://localhost:$COMFYUI_PORT${NC}"
        break
      fi
      if [ $((i % 15)) -eq 0 ]; then echo -n "${i}s"; elif [ $((i % 3)) -eq 0 ]; then echo -n "."; fi
      sleep 1
    done
    if ! curl -s --max-time 2 http://localhost:$COMFYUI_PORT/queue &>/dev/null; then
      echo -e "\n  ${YELLOW}[WARN] ComfyUI did not respond within 60s${NC}"
      echo -e "  ${YELLOW}       Check: tail -50 $LOG_DIR/comfyui.log${NC}"
    fi
  fi
fi

# ── STEP 3: VOTE API ──────────────────────────────────────────────────
echo -e "\n${BOLD}[3/4] Starting Vote API...${NC}"

if curl -s --max-time 2 http://localhost:$VOTE_API_PORT/api/stats &>/dev/null; then
  echo -e "  ${GREEN}[OK] Vote API already running on port $VOTE_API_PORT${NC}"
else
  if [ -f "$SIMMOON_DIR/vote_api.py" ]; then
    # Read API key from config.json
    SIMMOON_API_KEY=$(python3 -c "import json; print(json.load(open('$SIMMOON_DIR/config.json')).get('vote_api',{}).get('api_key',''))" 2>/dev/null || echo "")
    export SIMMOON_API_KEY
    nohup python3 "$SIMMOON_DIR/vote_api.py" --port $VOTE_API_PORT --bind 0.0.0.0 \
      &> "$LOG_DIR/vote_api.log" &
    VOTEAPI_PID=$!
    echo -n "  Waiting for Vote API"
    for i in $(seq 1 10); do
      if curl -s --max-time 1 http://localhost:$VOTE_API_PORT/api/stats &>/dev/null; then
        echo -e "\n  ${GREEN}[OK] Vote API started (PID $VOTEAPI_PID) — http://localhost:$VOTE_API_PORT${NC}"
        break
      fi
      echo -n "."
      sleep 1
    done
    if ! curl -s --max-time 1 http://localhost:$VOTE_API_PORT/api/stats &>/dev/null; then
      echo -e "\n  ${YELLOW}[WARN] Vote API did not respond in time${NC}"
    fi
  else
    echo -e "  ${YELLOW}[WARN] vote_api.py not found at $SIMMOON_DIR${NC}"
  fi
fi

# ── STEP 4: SIMMOON PIPELINE CHECK ──────────────────────────────────────
echo -e "\n${BOLD}[4/4] Checking Simmoon pipeline...${NC}"

if [ -d "$SIMMOON_DIR" ]; then
  echo -e "  ${GREEN}[OK] Simmoon_arc: $SIMMOON_DIR${NC}"

  if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    echo -e "  ${GREEN}[OK] Simmoon venv: $(python --version 2>&1)${NC}"
  else
    echo -e "  ${YELLOW}[WARN] Simmoon venv not found at $VENV_DIR${NC}"
  fi

  if [ -f "$SIMMOON_DIR/generate.sh" ]; then
    echo -e "  ${GREEN}[OK] Generator: ./generate.sh [category]${NC}"
  fi
  echo -e "  ${YELLOW}[INFO] Assets: 112 images in Simmoon_arc/${NC}"
else
  echo -e "  ${YELLOW}[WARN] Simmoon_arc not found at $SIMMOON_DIR${NC}"
fi

# ── SUMMARY ───────────────────────────────────────────────────────────────
echo -e "\n${CYAN}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ ALL SERVICES RUNNING${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════${NC}"
echo -e "  ${BOLD}Ollama${NC}    → http://localhost:$OLLAMA_PORT    (chat: ollama run qwen3-coder)"
echo -e "  ${BOLD}ComfyUI${NC}  → http://localhost:$COMFYUI_PORT    (node-based UI)"
echo -e "  ${BOLD}VoteAPI${NC}  → http://localhost:$VOTE_API_PORT    (vote persistence)"
echo -e "  ${BOLD}Simmoon${NC}   → ~/Simmoon_arc/generate.sh    (asset generator)"
echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"
echo -e "  Logs: $LOG_DIR/"
echo -e "  ${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════${NC}"

# Keep running so user can Ctrl+C
wait
