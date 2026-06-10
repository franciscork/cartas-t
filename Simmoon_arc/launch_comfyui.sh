#!/usr/bin/env bash
# =============================================================================
# SIMMOON — ComfyUI Launcher (WSL2)
# Inicia / Detiene / Estado del backend de generación de imágenes
# Checkpoints: dreamshaper_8, revAnimated_v122, counterfeit_v30, pixelArt, v1-5
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
COMFYUI_DIR="$HOME/ComfyUI"
COMFYUI_PORT="${2:-8188}"
LOG_DIR="$HOME/.simmoon-logs"

mkdir -p "$LOG_DIR"

test_comfyui() { curl -sf --max-time 2 "http://localhost:$COMFYUI_PORT/queue" &>/dev/null && echo "YES" || echo "NO"; }

list_checkpoints() {
    echo "  Checkpoints:"
    for ckpt in "$COMFYUI_DIR/models/checkpoints/"*.safetensors; do
        [ -f "$ckpt" ] || continue
        size=$(du -h "$ckpt" 2>/dev/null | cut -f1)
        echo "    • $(basename "$ckpt") ($size)"
    done
}

case "${1:-start}" in
    start)
        echo -e "${BOLD}🎨 ComfyUI — Iniciando...${NC}"
        if [ "$(test_comfyui)" = "YES" ]; then
            echo -e "  ${GREEN}✅ Ya está corriendo en http://localhost:$COMFYUI_PORT${NC}"
        else
            if [ ! -f "$COMFYUI_DIR/main.py" ]; then
                echo -e "  ${RED}❌ ComfyUI no encontrado en $COMFYUI_DIR${NC}"
                echo -e "  ${YELLOW}   Instalar: cd ~ && git clone https://github.com/comfyanonymous/ComfyUI && cd ComfyUI && python -m venv venv && ./venv/bin/pip install -r requirements.txt${NC}"
                exit 1
            fi
            cd "$COMFYUI_DIR"
            nohup ./venv/bin/python main.py --listen --port "$COMFYUI_PORT" &> "$LOG_DIR/comfyui.log" &
            echo -n "  ⏳ Esperando (puede tardar 20-40s)"
            for i in $(seq 1 60); do
                sleep 1
                if [ "$(test_comfyui)" = "YES" ]; then
                    echo -e "\n  ${GREEN}✅ Iniciado en http://localhost:$COMFYUI_PORT${NC}"
                    break
                fi
                [ $((i % 10)) -eq 0 ] && echo -n " ${i}s"
            done
            if [ "$(test_comfyui)" != "YES" ]; then
                echo -e "\n  ${YELLOW}⚠️ No respondió en 60s. Verifica: tail -20 $LOG_DIR/comfyui.log${NC}"
            fi
        fi
        list_checkpoints
        ;;
    stop)
        echo -e "${YELLOW}🛑 ComfyUI — Deteniendo...${NC}"
        pkill -f "main.py.*--port $COMFYUI_PORT" 2>/dev/null && echo -e "  ${GREEN}✅ Detenido${NC}" || echo -e "  ${GREEN}✅ Ya estaba detenido${NC}"
        ;;
    status|check)
        if [ "$(test_comfyui)" = "YES" ]; then
            echo -e "${GREEN}🎨 ComfyUI — ACTIVO en http://localhost:$COMFYUI_PORT${NC}"
            list_checkpoints
        else
            echo -e "${RED}🎨 ComfyUI — INACTIVO${NC}"
        fi
        ;;
    restart)
        pkill -f "main.py.*--port $COMFYUI_PORT" 2>/dev/null || true
        sleep 2
        exec "$0" start "$COMFYUI_PORT"
        ;;
    *)
        echo "Uso: launch_comfyui.sh {start|stop|status|restart} [port=$COMFYUI_PORT]"
        exit 1
        ;;
esac
