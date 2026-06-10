# 🧠 Guía Rápida - Hermes Agent (Agente Autónomo)

## ¿Qué es?
Hermes es un sistema multi-agente con 3 escritorios: **Gateway** (orquestador), **TUI** (terminal interactiva), y **Dashboard** (monitor visual). Corre tareas autónomas usando modelos locales (Ollama).

## Puertos y URLs
| Recurso | URL / Acceso |
|----------|--------------|
| Gateway API | `http://localhost:9119` |
| Dashboard Web | `http://localhost:9120` |
| TUI (Terminal) | `tmux attach -t hermes-tui` |

## Iniciar / Detener
```bash
# Desde el lanzador unificado (recomendado)
ias start hermes

# Manualmente (los 3 componentes)
hermes gateway     # Puerto 9119
hermes tui         # Terminal interactiva
hermes dashboard   # Puerto 9120

# Detener
ias stop hermes
```

## Arquitectura
```
┌──────────────────────────────────────────┐
│              Hermes Gateway              │
│           (orquestador :9119)            │
├────────────────┬─────────────────────────┤
│   Hermes TUI   │   Hermes Dashboard      │
│  (terminal)    │   (web :9120)           │
└────────────────┴─────────────────────────┘
```

## Comandos
```bash
# Verificar instalación
hermes --version
hermes doctor

# Sesiones tmux
tmux ls                          # Listar sesiones
tmux attach -t hermes-tui        # Conectar a TUI

# Logs
tail -f /tmp/simmoon_hermes.log
```

## Skills / Capacidades
- 🔍 Búsqueda y análisis de información
- 📝 Generación de texto estructurado
- 🧩 Resolución de problemas multi-paso
- 📊 Análisis de datos y reportes
- 🔗 Integración con APIs externas

## Ubicaciones
- **Binario**: `~/.local/bin/hermes`
- **Proyecto**: `~/hermes-agent/`
- **Logs**: `/tmp/simmoon_hermes.log`
- **Config**: `~/hermes-agent/config/`

## Integración con Ollama
```bash
# Configurar modelo por defecto
export HERMES_MODEL=qwen3:14b
export OLLAMA_BASE_URL=http://localhost:11434
```

## Solución de Problemas
- **Gateway no arranca**: `fuser -k 9119/tcp` y reintentar
- **TUI no responde**: `tmux kill-session -t hermes-tui`
- **Dashboard no carga**: `fuser -k 9120/tcp` y reintentar
- **Hermes no encontrado**: `export PATH="$HOME/.local/bin:$PATH"`
