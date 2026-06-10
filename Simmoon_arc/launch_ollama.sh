#!/usr/bin/env bash
# =============================================================================
# SIMMOON — Ollama Launcher (WSL2)
# Inicia / Detiene / Estado del servidor LLM Ollama
# Modelos: gemma3-tools-64k, qwen3-14b-64k, qwen25-coder-14b-64k, nomic-embed-text
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
OLLAMA_PORT=11434

test_ollama() { curl -sf --max-time 2 "http://localhost:$OLLAMA_PORT/api/tags" &>/dev/null && echo "YES" || echo "NO"; }

case "${1:-start}" in
    start)
        echo -e "${BOLD}🧠 Ollama — Iniciando...${NC}"
        if [ "$(test_ollama)" = "YES" ]; then
            echo -e "  ${GREEN}✅ Ya está corriendo en http://localhost:$OLLAMA_PORT${NC}"
        else
            nohup ollama serve &>/dev/null &
            echo -n "  ⏳ Esperando"
            for i in $(seq 1 10); do
                sleep 1; echo -n "."
                if [ "$(test_ollama)" = "YES" ]; then
                    echo -e "\n  ${GREEN}✅ Iniciado en http://localhost:$OLLAMA_PORT${NC}"
                    break
                fi
            done
            if [ "$(test_ollama)" != "YES" ]; then
                echo -e "\n  ${RED}❌ No respondió. Ejecuta 'ollama serve' manualmente.${NC}"
                exit 1
            fi
        fi
        echo -e "  Modelos:"
        curl -sf "http://localhost:$OLLAMA_PORT/api/tags" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for m in d.get('models',[]): print(f'    • {m[\"name\"]}')
" 2>/dev/null || echo "    (no se pudieron listar)"
        ;;
    stop)
        echo -e "${YELLOW}🛑 Ollama — Deteniendo...${NC}"
        pkill -f "ollama serve" 2>/dev/null && echo -e "  ${GREEN}✅ Detenido${NC}" || echo -e "  ${GREEN}✅ Ya estaba detenido${NC}"
        ;;
    status|check)
        if [ "$(test_ollama)" = "YES" ]; then
            echo -e "${GREEN}🧠 Ollama — ACTIVO en http://localhost:$OLLAMA_PORT${NC}"
            echo -e "  Modelos:"
            curl -sf "http://localhost:$OLLAMA_PORT/api/tags" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for m in d.get('models',[]): print(f'    • {m[\"name\"]}')
" 2>/dev/null || echo "    (no se pudieron listar)"
        else
            echo -e "${RED}🧠 Ollama — INACTIVO${NC}"
        fi
        ;;
    restart)
        pkill -f "ollama serve" 2>/dev/null || true
        sleep 1
        exec "$0" start
        ;;
    *)
        echo "Uso: launch_ollama.sh {start|stop|status|restart}"
        exit 1
        ;;
esac
