# 🎮 Guía Rápida - Simmoon (Juego + Generador de Assets)

## ¿Qué es?
Simmoon es un juego que combina generación de imágenes con IA (Stable Diffusion vía ComfyUI/InvokeAI/Leonardo.ai) y mecánicas de votación. Los jugadores crean y votan assets generados por IA.

## Puertos y URLs
| Recurso | URL |
|----------|-----|
| Dashboard | `http://localhost:5000` |
| Dashboard API | `http://localhost:5000/api/health` |
| Viewer HTML | `Simmoon_arc/viewer.html` |

## Componentes del Sistema
```
Simmoon_arc/
├── simmoon_generator.py     ← Motor de generación (ComfyUI/Leonardo)
├── simmoon_menu.py          ← Menú interactivo del juego
├── simmoon_pipeline.py      ← Pipeline automatizado
├── simmoon_autogen.py       ← Generación autónoma
├── simmoon_mecanicas.py     ← Mecánicas de juego
├── simmoon_pixelator.py     ← Pixelado de assets
├── generator_factory.py     ← Fábrica de backends (ComfyUI/Leonardo)
├── leonardo_client.py       ← Cliente REST para Leonardo.ai
├── generate_comfyui.py      ← Constructor de workflows ComfyUI
├── generate_invokeai.py     ← Generación con InvokeAI
├── populate_db.py           ← Poblar base de datos
├── vote_api.py              ← API de votaciones
├── dashboard.py             ← Dashboard web Flask
├── monitor_sistema.py       ← Monitor de salud del sistema
├── launch_simmoon.py        ← Lanzador unificado Python
└── viewer.html              ← Visor de assets
```

## Iniciar Simmoon
```bash
# Desde el lanzador unificado
cd ~/Simmoon_arc
python3 launch_simmoon.py

# Menú interactivo del juego
python3 simmoon_menu.py

# Pipeline automatizado
python3 simmoon_pipeline.py
```

## Backends de Generación
| Backend | Estado | Prioridad |
|---------|--------|-----------|
| ComfyUI (localhost:8188) | Primario | 1 |
| Leonardo.ai (API cloud) | Fallback | 2 |
| InvokeAI (localhost:9090) | Secundario | 3 |

### Configurar Leonardo API Key
```bash
export LEONARDO_API_KEY="tu-api-key"
# Obtener en: https://app.leonardo.ai → API Access
```

## Base de Datos (PostgreSQL)
```bash
# Crear esquema
psql -U docus -d simmoon -f ~/Simmoon_arc/schema.sql

# Poblar datos iniciales
python3 ~/Simmoon_arc/populate_db.py
```

## Monitor del Sistema
```bash
# Estado completo
python3 ~/Simmoon_arc/monitor_sistema.py

# Solo JSON (para scripts)
python3 ~/Simmoon_arc/monitor_sistema.py --json

# Vista en vivo (watch mode)
python3 ~/Simmoon_arc/monitor_sistema.py --watch
```

## Solución de Problemas
- **Generación falla**: Verificar ComfyUI (puerto 8188) o API key de Leonardo
- **Votos no guardan**: Verificar PostgreSQL corriendo (`pg_isready`)
- **Dashboard vacío**: Reiniciar dashboard: `python3 dashboard.py`
