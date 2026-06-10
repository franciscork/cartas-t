#!/usr/bin/env bash
# =============================================================================
# SIMMOON — InvokeAI Launcher (WSL2)
# Inicia / Detiene / Estado del backend alternativo de generación de imágenes
# Usa symlinks a los checkpoints de ComfyUI para ahorrar espacio
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
INVOKEAI_DIR="$HOME/invokeai"
INVOKEAI_ENV="$HOME/invokeai-env"
INVOKEAI_PORT=9090

test_invokeai() { curl -sf --max-time 2 "http://localhost:$INVOKEAI_PORT/api/v1/app/version" &>/dev/null && echo "YES" || echo "NO"; }

case "${1:-start}" in
    start)
        echo -e "${BOLD}🖼️  InvokeAI — Iniciando...${NC}"
        if [ "$(test_invokeai)" = "YES" ]; then
            echo -e "  ${GREEN}✅ Ya está corriendo en http://localhost:$INVOKEAI_PORT${NC}"
        else
            if [ ! -d "$INVOKEAI_ENV" ]; then
                echo -e "  ${RED}❌ Virtualenv '$INVOKEAI_ENV' no encontrado${NC}"
                exit 1
            fi
            if [ ! -d "$INVOKEAI_DIR" ]; then
                echo -e "  ${RED}❌ InvokeAI no encontrado en '$INVOKEAI_DIR'${NC}"
                exit 1
            fi
            source "$INVOKEAI_ENV/bin/activate"
            cd "$INVOKEAI_DIR"
            nohup invokeai-web --root "$INVOKEAI_DIR" &>/dev/null &
            disown
            echo -n "  ⏳ Esperando"
            for i in $(seq 1 30); do
                sleep 1; echo -n "."
                if [ "$(test_invokeai)" = "YES" ]; then
                    echo -e "\n  ${GREEN}✅ Iniciado en http://localhost:$INVOKEAI_PORT${NC}"
                    break
                fi
            done
            if [ "$(test_invokeai)" != "YES" ]; then
                echo -e "\n  ${YELLOW}⚠️ No respondió. Verifica: source ~/invokeai-env/bin/activate && invokeai-web --version${NC}"
            fi
        fi
        echo -e "  URL: ${CYAN}http://localhost:$INVOKEAI_PORT${NC}"
        echo -e "  Checkpoints (symlinks → ComfyUI):"
        ls -la "$INVOKEAI_DIR/models/checkpoints/"*.safetensors 2>/dev/null | awk '{print "    • " $NF}' || echo "    (no encontrados)"
        ;;
    stop)
        echo -e "${YELLOW}🛑 InvokeAI — Deteniendo...${NC}"
        pkill -f "invokeai-web" 2>/dev/null && echo -e "  ${GREEN}✅ Detenido${NC}" || echo -e "  ${GREEN}✅ Ya estaba detenido${NC}"
        ;;
    status|check)
        if [ "$(test_invokeai)" = "YES" ]; then
            echo -e "${GREEN}🖼️  InvokeAI — ACTIVO en http://localhost:$INVOKEAI_PORT${NC}"
        else
            echo -e "${RED}🖼️  InvokeAI — INACTIVO${NC}"
        fi
        ;;
    restart)
        pkill -f "invokeai-web" 2>/dev/null || true
        sleep 2
        exec "$0" start
        ;;
    *)
        echo "Uso: launch_invokeai.sh {start|stop|status|restart}"
        exit 1
        ;;
esac
