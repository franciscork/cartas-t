#!/usr/bin/env bash
# =============================================================================
#  buffy_poll.sh — Buffy Telegram Round-Trip Communication Tool
#  
#  Permite a Buffy (desde esta sesión CLI) leer mensajes nuevos de Telegram
#  y responder manualmente con respuestas personalizadas.
#
#  Uso:
#    bash buffy_poll.sh check          # Ver mensajes nuevos (sin responder)
#    bash buffy_poll.sh reply MSGID "respuesta"  # Responder a un msg específico
#    bash buffy_poll.sh send "mensaje" # Enviar mensaje proactivo a Jeremi
#    bash buffy_poll.sh watch          # Modo interactivo: ver y responder
#    bash buffy_poll.sh status         # Estado de los bridges
# =============================================================================

set -euo pipefail

DISTRO="Ubuntu"
CHAT_ID="1573505394"
SIMMOON_DIR="$HOME/Simmoon_arc"
TOKEN="8866399930:AAG6N-jd4A6R-OPYehqNzGZzVCu1n9GNuMM"
STATE_FILE="$SIMMOON_DIR/buffy_telegram_state.json"

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

# ── Check new messages ─────────────────────────────────────────────────────
cmd_check() {
    echo ""
    echo -e "${CYAN}📬 Verificando mensajes nuevos para Buffy...${NC}"
    echo ""

    # Get updates from Telegram API
    wsl -d "$DISTRO" -- bash -c "
python3 -c \"
import json, urllib.request, sys

token = '$TOKEN'
state_path = '$STATE_FILE'

# Load last update_id
last_id = 0
try:
    import os
    if os.path.exists(state_path):
        with open(state_path, 'r') as f:
            state = json.load(f)
            last_id = state.get('last_update_id', 0)
except: pass

# Get updates
url = f'https://api.telegram.org/bot{token}/getUpdates?offset={last_id+1}&timeout=5'
try:
    resp = urllib.request.urlopen(url, timeout=10)
    data = json.loads(resp.read())
    updates = data.get('result', [])
    
    if not updates:
        print('📭 No hay mensajes nuevos.')
    else:
        print(f'📬 {len(updates)} mensaje(s) nuevo(s):')
        print()
        for u in updates:
            msg = u.get('message', {})
            chat = msg.get('chat', {})
            user = msg.get('from', {})
            uid = u.get('update_id', 0)
            mid = msg.get('message_id', 0)
            cid = chat.get('id', '?')
            name = user.get('first_name', '?')
            text = msg.get('text', '[no texto]')
            date = msg.get('date', 0)
            from datetime import datetime
            ts = datetime.fromtimestamp(date).strftime('%H:%M:%S') if date else '?'
            
            print(f'  🆔 UpdateID: {uid} | MsgID: {mid} | ChatID: {cid}')
            print(f'  👤 {name} ({ts}):')
            print(f'  ┃  {text[:300]}')
            print()
        
        # Update last_id
        new_last = updates[-1]['update_id']
        print(f'  📌 Para marcar como leídos: actualizar last_update_id a {new_last}')
except Exception as e:
    print(f'❌ Error: {e}')
\"
"
    echo ""
}

# ── Reply to a specific message ────────────────────────────────────────────
cmd_reply() {
    local msg_id="$1"
    local reply_text="$2"

    echo ""
    echo -e "${CYAN}📤 Respondiendo a mensaje $msg_id...${NC}"

    wsl -d "$DISTRO" -- bash -c "
python3 -c \"
import json, urllib.request

token = '$TOKEN'
chat_id = $CHAT_ID
msg_id = $msg_id
text = '''🤖 *Buffy:*\\n$reply_text'''

if len(text) > 4000:
    text = text[:4000] + '\\n\\n_(truncado)_'

payload = {
    'chat_id': chat_id,
    'text': text,
    'reply_to_message_id': msg_id,
    'parse_mode': 'Markdown',
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    f'https://api.telegram.org/bot{token}/sendMessage',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST',
)

try:
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    if result.get('ok'):
        print('✅ Respuesta enviada')
    else:
        desc = result.get('description', 'unknown')
        if 'parse' in desc.lower():
            # Retry without Markdown
            payload.pop('parse_mode', None)
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{token}/sendMessage',
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read())
            if result.get('ok'):
                print('✅ Respuesta enviada (sin formato)')
            else:
                print(f'❌ Error: {result.get(\"description\", \"unknown\")}')
        else:
            print(f'❌ Error: {desc}')
except Exception as e:
    print(f'❌ Error: {e}')
\"
"
    echo ""
}

# ── Send proactive message ─────────────────────────────────────────────────
cmd_send() {
    local text="$1"
    echo ""
    echo -e "${CYAN}📤 Enviando mensaje a Jeremi...${NC}"
    
    wsl -d "$DISTRO" -- bash -c "cd $SIMMOON_DIR && python3 buffy_telegram_send.py $CHAT_ID \"$text\""
    echo ""
}

# ── Status check ───────────────────────────────────────────────────────────
cmd_status() {
    echo ""
    echo -e "${BOLD}📊 Estado de Bridges Telegram:${NC}"
    echo ""

    # Buffy daemon
    echo -n "  🤖 Buffy Bridge:   "
    wsl -d "$DISTRO" -- bash -c "tmux has-session -t buffy-telegram 2>/dev/null && echo -e '${GREEN}🟢 ACTIVO${NC}' || echo -e '${RED}⚫ DETENIDO${NC}'"

    # Agatha daemon  
    echo -n "  📋 Agatha Actas:   "
    wsl -d "$DISTRO" -- bash -c "tmux has-session -t agatha-daemon 2>/dev/null && echo -e '${GREEN}🟢 ACTIVO${NC}' || echo -e '${RED}⚫ DETENIDO${NC}'"

    # Telegram Bot (original)
    echo -n "  🤖 Telegram Bot:   "
    wsl -d "$DISTRO" -- bash -c "tmux has-session -t telegram-bot 2>/dev/null && echo -e '${GREEN}🟢 ACTIVO${NC}' || echo -e '${RED}⚫ DETENIDO${NC}'"

    # Ollama
    echo -n "  🧠 Ollama:         "
    wsl -d "$DISTRO" -- bash -c "curl -sf --max-time 2 http://localhost:11434/api/tags &>/dev/null && echo -e '${GREEN}🟢 ACTIVO${NC}' || echo -e '${RED}⚫ DETENIDO${NC}'"

    echo ""
    echo -e "${CYAN}📱 ChatID de Jeremi: $CHAT_ID${NC}"
    echo ""
}

# ── Interactive watch mode ─────────────────────────────────────────────────
cmd_watch() {
    echo ""
    echo -e "${BOLD}🔍 Modo Watch — Buffy Telegram Monitor${NC}"
    echo -e "${CYAN}  Verificando mensajes cada 5 segundos...${NC}"
    echo -e "${CYAN}  Presiona Ctrl+C para salir${NC}"
    echo ""

    while true; do
        cmd_check
        sleep 5
    done
}

# ── Main ───────────────────────────────────────────────────────────────────
case "${1:-help}" in
    check|poll)
        cmd_check
        ;;
    reply|respond)
        if [ $# -lt 3 ]; then
            echo "Uso: buffy_poll.sh reply <msg_id> \"texto de respuesta\""
            exit 1
        fi
        cmd_reply "$2" "$3"
        ;;
    send|msg)
        if [ $# -lt 2 ]; then
            echo "Uso: buffy_poll.sh send \"mensaje\""
            exit 1
        fi
        cmd_send "$2"
        ;;
    watch|monitor)
        cmd_watch
        ;;
    status|st)
        cmd_status
        ;;
    help|*)
        echo ""
        echo -e "${BOLD}📱 Buffy Poll — Comunicación ida y vuelta con Telegram${NC}"
        echo ""
        echo "  check     Ver mensajes nuevos"
        echo "  reply     Responder a un mensaje:  buffy_poll.sh reply <msg_id> \"texto\""
        echo "  send      Enviar mensaje:          buffy_poll.sh send \"texto\""
        echo "  status    Estado de los bridges"
        echo "  watch     Monitoreo continuo (Ctrl+C para salir)"
        echo ""
        echo "  Ejemplo:"
        echo "    bash buffy_poll.sh check"
        echo "    bash buffy_poll.sh send \"¡Hola desde la CLI!\""
        echo "    bash buffy_poll.sh reply 123 \"Recibido, gracias\""
        echo ""
        ;;
esac
