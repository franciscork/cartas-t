# 📊 Guía Rápida - Dashboard & Monitor

## ¿Qué es?
Sistema de monitoreo en tiempo real del hardware y servicios del ecosistema de IA.

## Puertos y URLs
| Recurso | URL |
|----------|-----|
| Dashboard Web | `http://localhost:5000` |
| API JSON | `http://localhost:5000/api/health` |

## Dashboard Web
Interfaz Flask con auto-refresh cada 10 segundos. Muestra:
- 🎮 **GPU**: Modelo, temperatura, VRAM usada/libre
- 🧠 **RAM**: Uso total, porcentaje
- 💾 **Disco**: Espacio libre en todas las unidades
- 🔌 **Servicios**: Ollama, ComfyUI, PostgreSQL — ✅/❌ en vivo
- ⚠️ **Alertas**: Temperatura alta, VRAM saturada, servicios caídos

### Iniciar / Detener
```bash
# Desde ias (recomendado)
ias start dashboard

# Manual
cd ~/Simmoon_arc
python3 dashboard.py

# Detener
ias stop dashboard
# o: fuser -k 5000/tcp
```

## Monitor del Sistema (CLI)
```bash
cd ~/Simmoon_arc

# Estado completo (texto formateado)
python3 monitor_sistema.py

# JSON (para scripts/agentes)
python3 monitor_sistema.py --json

# Watch mode (actualiza cada 5s)
python3 monitor_sistema.py --watch

# Solo GPU
python3 monitor_sistema.py --gpu

# Solo alertas
python3 monitor_sistema.py --alerts
```

### Output JSON de ejemplo:
```json
{
  "healthy": true,
  "gpu": {"available": true, "name": "RTX 4070", "vram_used_mb": 0, "temperature_c": 42},
  "ram": {"total_gb": 15.5, "used_gb": 1.9, "used_percent": 12.3},
  "disk": [{"mount": "/", "free_gb": 743, "total_gb": 1000}],
  "services": {"ollama": true, "comfyui": true, "postgresql": true},
  "alerts": []
}
```

## Integración con Jarvis
```bash
# Jarvis consulta el monitor
bash ~/jarvis_monitor.sh status
bash ~/jarvis_monitor.sh json
bash ~/jarvis_monitor.sh gpu
bash ~/jarvis_monitor.sh alerts
bash ~/jarvis_monitor.sh services
```

## nvtop (Monitor GPU en tiempo real)
```bash
# Lanzar monitor GPU interactivo
nvtop
```

## Ubicaciones
- **Dashboard**: `~/Simmoon_arc/dashboard.py`
- **Monitor**: `~/Simmoon_arc/monitor_sistema.py`
- **Jarvis bridge**: `~/jarvis_monitor.sh`
- **Logs dashboard**: `/tmp/dashboard.log`

## Solución de Problemas
- **Dashboard no carga**: `fuser -k 5000/tcp && python3 ~/Simmoon_arc/dashboard.py`
- **GPU no detectada**: `nvidia-smi` para verificar
- **Monitor lanza error**: Sincronizar archivos `cp` desde Windows a WSL2
