#!/usr/bin/env bash
# =============================================================================
# SIMMOON — Jarvis Monitor Bridge
# Permite a Jarvis (y otros agentes CLI) consultar el estado del sistema.
#
# Uso:
#   bash jarvis_monitor.sh status     # Estado completo (texto)
#   bash jarvis_monitor.sh json       # Estado en JSON (para agentes)
#   bash jarvis_monitor.sh gpu        # Solo GPU
#   bash jarvis_monitor.sh alerts     # Solo alertas
#   bash jarvis_monitor.sh services   # Solo servicios
# =============================================================================
set -euo pipefail

SIMMOON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/Simmoon_arc"
# Fallback to home directory if not found relative to script
[ -d "$SIMMOON_DIR" ] || SIMMOON_DIR="$HOME/Simmoon_arc"

if [ ! -f "$SIMMOON_DIR/monitor_sistema.py" ]; then
    echo '{"error": "monitor_sistema.py not found"}' 
    exit 1
fi

cd "$SIMMOON_DIR"

case "${1:-status}" in
    status)
        python3 -c "
from monitor_sistema import check_gpu, check_ram, check_disk, check_services, detect_alerts
gpu = check_gpu()
ram = check_ram()
disk = check_disk()
svc = check_services()
alerts = detect_alerts({'gpu': gpu, 'ram': ram, 'disk': disk, 'services': svc})

print('=== GPU ===')
if gpu.get('available'):
    print(f\"  {gpu['name']} | {gpu['temperature_c']}°C | VRAM: {gpu['memory_used_mb']}/{gpu['memory_total_mb']} MB | {gpu['utilization_gpu_percent']}%\")
else:
    print('  No detectada')

print()
print('=== RAM ===')
print(f\"  {ram['used_gb']:.1f} / {ram['total_gb']:.1f} GB ({ram['used_percent']:.1f}%)\")

print()
print('=== Disco ===')
for mount, info in disk.items():
    print(f\"  {mount}: {info['available_gb']:.1f} GB libre ({info['used_percent']}% usado)\")

print()
print('=== Servicios ===')
for name, s in svc.items():
    icon = '✅' if s.get('healthy') else '❌'
    extra = ''
    if name == 'postgresql' and s.get('databases'):
        extra = f\" (DBs: {', '.join(s['databases'][:3])})\"
    print(f\"  {icon} {name}{extra}\")

print()
if alerts:
    print('=== ALERTAS ===')
    for a in alerts:
        print(f\"  {a}\")
else:
    print('✅ Sin alertas')
"
        ;;
    json)
        python3 monitor_sistema.py --json 2>/dev/null || echo '{"error": "monitor failed"}'
        ;;
    gpu)
        python3 -c "
from monitor_sistema import check_gpu
gpu = check_gpu()
if gpu.get('available'):
    print(f\"{gpu['name']} | {gpu['temperature_c']}°C | VRAM: {gpu['memory_used_mb']}/{gpu['memory_total_mb']} MB | GPU: {gpu['utilization_gpu_percent']}%\")
else:
    print('GPU no detectada')
"
        ;;
    alerts)
        python3 -c "
from monitor_sistema import check_gpu, check_ram, check_disk, check_services, detect_alerts
alerts = detect_alerts({
    'gpu': check_gpu(), 'ram': check_ram(),
    'disk': check_disk(), 'services': check_services()
})
if alerts:
    for a in alerts:
        print(a)
else:
    print('✅ Sin alertas')
"
        ;;
    services|svc)
        python3 -c "
from monitor_sistema import check_services
svc = check_services()
for name, s in svc.items():
    icon = '✅' if s.get('healthy') else '❌'
    print(f'{icon} {name}')
"
        ;;
    ask)
        # Modo interactivo: preguntar a Jarvis sobre el estado del sistema
        # Uso: bash jarvis_monitor.sh ask "¿cómo está la GPU?"
        QUESTION="${2:-¿Cuál es el estado general del sistema?}"
        JSON_DATA=$(python3 monitor_sistema.py --json 2>/dev/null)
        if [ -z "$JSON_DATA" ]; then
            echo "❌ No se pudo obtener datos del monitor"
            exit 1
        fi
        
        export PATH="$HOME/.local/bin:$PATH"
        
        # Construir prompt con los datos del sistema
        PROMPT="Eres Jarvis, el asistente de IA del sistema Simmoon. Aquí están los datos ACTUALES del sistema en JSON:

\`\`\`json
$JSON_DATA
\`\`\`

Basándote EXCLUSIVAMENTE en estos datos reales (no inventes nada), responde en español de forma clara y concisa:

$QUESTION"

        timeout 120 jarvis ask --model qwen3:14b "$PROMPT" 2>&1
        ;;
    *)
        echo "Uso: jarvis_monitor.sh {status|json|gpu|alerts|services|ask}"
        echo ""
        echo "  ask 'pregunta'  - Preguntar a Jarvis sobre el estado del sistema"
        echo "  status          - Estado completo en texto"
        echo "  json            - Estado en JSON (para scripts)"
        echo "  gpu             - Solo GPU"
        echo "  alerts          - Solo alertas"
        echo "  services        - Solo servicios"
        echo ""
        echo "Ejemplo: bash jarvis_monitor.sh ask '¿hay suficiente VRAM para generar una imagen?'"
        exit 1
        ;;
esac
