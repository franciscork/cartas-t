# 🚀 SIMMOON — Fábrica de Assets Pixel-Art

Generación automatizada de sprites pixel-art para juegos estilo SimCity 2000.
Pipeline multi-backend con IA local + cloud, procesamiento de imágenes y persistencia en PostgreSQL.

---

## 📋 Estado del Proyecto

| Componente | Estado | Puerto |
|-----------|--------|--------|
| 🔧 **ComfyUI** (generación local, GPU) | ✅ Operativo | `:8188` |
| 🎨 **InvokeAI v6.13.0** (generación local) | ✅ Instalado | `:9090` |
| 🐍 **Diffusers (WSL2)** (descarga HuggingFace Hub) | ✅ Probado — 4.3s/img en RTX 4070 | CUDA |
| ⚙️ **GeneratorFactory** (cadena de fallback) | ✅ ComfyUI → InvokeAI → Diffusers/HF → Leonardo | — |
| 🔗 **Pipeline LangGraph** (`simmoon_pipeline.py`) | ✅ Arreglado — contador de fallos + parada en errores | — |
| 🌉 **Jarvis Bridge** (`jarvis_bridge.py`) | ✅ Puerto JSON para agentes externos | — |
| 🖼️ **ImageMagick GIFs** (`simmoon_gifs.py`) | ✅ GIFs animados por categoría | — |
| 🎨 **Pixel-Art** (`simmoon_pixelator.py`) | ✅ Conversión a pixel-art con paleta limitada | — |
| 🗳️ **Vote API** (`vote_api.py`) | ✅ Persistencia de votos en PostgreSQL | `:9099` |
| 🗄️ **PostgreSQL** (`simmoon`) | ✅ 22 categorías, +500 assets, tabla de votos | `:5432` |
| 📊 **Dashboard** (`dashboard.py`) | ✅ Monitoreo de servicios | `:5000` |

### ❌ No Disponibles

| API | Motivo |
|-----|--------|
| HuggingFace Inference API | `api-inference.huggingface.co` bloqueado por red/DNS |
| Leonardo.ai | Requiere tarjeta de crédito |

---

## 🧠 Memoria de Buffy — Persistencia entre Sesiones 🆕

Buffy **no tiene memoria entre sesiones** por defecto. Este sistema soluciona eso
persistiendo contexto, hechos y preferencias en PostgreSQL.

### ¿Cómo funciona?

```
Sesión 1 (hoy)                                Sesión 2 (mañana)
┌─────────────────┐                          ┌─────────────────┐
│  Buffy           │  guarda en PostgreSQL   │  Buffy (nueva)  │
│  ¡Hace trabajo!  │ ──────────────────────► │  ¿Qué pasó ayer?│
│                  │  10+ memorias clave     │  python buffy_  │
│  python agent_   │                         │  boot.py ──────►│
│  memory.py       │ ◄────────────────────── │  ¡Ya sé todo!   │
└─────────────────┘  lee al iniciar sesión   └─────────────────┘
```

### 💾 Lo que se guardó en esta sesión (2026-06-08)

| Memoria | Tipo | Importancia | Descripción |
|---------|------|-------------|-------------|
| `project_overview` | fact ⭐⭐⭐⭐⭐ | 5 | Visión general del proyecto |
| `architecture` | fact ⭐⭐⭐⭐⭐ | 5 | Arquitectura: Jarvis → bridge → Buffy |
| `session_20260608` | context ⭐⭐⭐⭐⭐ | 5 | Todo lo hecho hoy: pipeline, bridge, diffusers, README |
| `jarvis_bridge` | fact ⭐⭐⭐⭐⭐ | 5 | Bridge creado y probado con Jarvis |
| `pipeline_state` | fact ⭐⭐⭐⭐ | 4 | Pipeline arreglado, backend router |
| `backends_status` | fact ⭐⭐⭐⭐ | 4 | Estado de todos los backends |
| `assets_state` | fact ⭐⭐⭐⭐ | 4 | 22 categorías, 1500+ archivos, 10 tablas DB |
| `next_steps` | context ⭐⭐⭐⭐ | 4 | Próximos pasos planificados |
| `language_spanish` | preference ⭐⭐⭐⭐ | 4 | 🇪🇸 Usuario prefiere español |
| `readme_created` | fact ⭐⭐⭐ | 3 | README.md documentado |

### 🚀 Para la próxima Buffy (al iniciar sesión)

```bash
# 1. Cargar toda la memoria
python Simmoon_arc/buffy_boot.py

# 2. O solo un resumen rápido
python Simmoon_arc/buffy_boot.py --quick

# 3. O cargar contexto completo para la ventana de contexto
python Simmoon_arc/buffy_boot.py --days 7
```

### 🔧 Comandos útiles

```bash
# Guardar una memoria
python Simmoon_arc/agent_memory.py --agent buffy --save 'mi_memoria' 'fact' 'Esto es importante'

# Leer una memoria específica
python Simmoon_arc/agent_memory.py --agent buffy --get mi_memoria

# Ver memorias recientes
python Simmoon_arc/agent_memory.py --agent buffy --recent 7

# Resumen de todos los agentes (Hermes, OpenHuman, Buffy)
python Simmoon_arc/agent_memory.py --summary
```

### 📝 Al finalizar tu sesión

Antes de cerrar la sesión, guarda tu trabajo para que la próxima Buffy lo recuerde:

```bash
# Guardar resumen de la sesión (¡IMPORTANTE!)
python Simmoon_arc/agent_memory.py --agent buffy --save 'session_YYYYMMDD' 'context' 'Lo que hiciste hoy en 1-2 líneas.'

# Guardar hechos importantes
python Simmoon_arc/agent_memory.py --agent buffy --save 'logro_clave' 'fact' 'Descubrimiento importante de la sesión.'

# Guardar próximos pasos (para continuar mañana)
python Simmoon_arc/agent_memory.py --agent buffy --save 'next_steps' 'context' '1) Tarea pendiente 1. 2) Tarea pendiente 2.'
```

> 💡 **Tip**: Usa `importancia=5` para hechos críticos, `importancia=3` para información normal.

---

## 🏗️ Arquitectura

```
                    ┌─────────────┐
                    │   Jarvis    │ (coordina: qué, cuándo, estilo)
                    └──────┬──────┘
                           │ llama
                    ┌──────▼──────┐
                    │jarvis_bridge│ → JSON output
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌────────────┐ ┌──────────┐ ┌──────────┐
     │simmoon_    │ │generator_│ │simmoon_  │
     │pipeline.py │ │factory.py│ │diffusers │ ← WSL2
     └────────────┘ └──────────┘ └──────────┘
              │            │            │
              ▼            ▼            ▼
     ┌────────────┐ ┌──────────┐ ┌──────────┐
     │   ComfyUI  │ │ InvokeAI│ │  Diff.   │
     │   :8188    │ │ :9090   │ │  CUDA    │
     └────────────┘ └──────────┘ └──────────┘
              │
              ▼
     ┌────────────┐
     │simmoon_    │
     │pixelator.py│ → *_pixel/
     └────────────┘
              │
              ▼
     ┌────────────┐
     │simmoon_    │
     │gifs.py     │ → *.gif (ImageMagick)
     └────────────┘
              │
              ▼
     ┌────────────┐
     │ PostgreSQL │
     │populate_db │
     └────────────┘
```

---

## 🚀 Scripts Principales

### Generación

| Script | Descripción | Uso |
|--------|-------------|-----|
| `simmoon_pipeline.py` | Pipeline completo: generar → pixelar → DB | `--backend diffusers --category businesses` |
| `generator_factory.py` | Fábrica unificada con fallback automático | `generate_category("businesses")` |
| `simmoon_diffusers.py` | Generación con Diffusers (WSL2) | `--category businesses` |
| `generate_comfyui.py` | Generación batch con ComfyUI | `--category businesses --suffix run1` |
| `generate_invokeai.py` | Generación con InvokeAI | `--category businesses` |

### Procesamiento

| Script | Descripción | Uso |
|--------|-------------|-----|
| `simmoon_pixelator.py` | Convierte imágenes a pixel-art | `--directory ./businesses --game-res 64 --colors 16` |
| `simmoon_gifs.py` | Crea GIFs animados por categoría | `--categories businesses --delay 100 --resize 256` |
| `run_pixelator_all.py` | Pixeliza todas las categorías | (sin args, todo automático) |

### Infraestructura

| Script | Descripción | Puerto |
|--------|-------------|--------|
| `vote_api.py` | API REST de votos (PostgreSQL) | `:9099` |
| `dashboard.py` | Dashboard de monitoreo (Flask) | `:5000` |
| `jarvis_bridge.py` | Puerto JSON para Jarvis | CLI |

### Agentes / Integraciones

| Script | Descripción |
|--------|-------------|
| `connect_agents_to_memory.py` | Sincroniza Hermes + OpenHuman a memoria compartida |
| `telegram_bot.py` | Bot de Telegram para interactuar con el sistema |
| `agent_memory.py` | Sistema de memoria compartida entre agentes |

---

## 🔧 Backends de Generación

### 1. Local — ComfyUI (`:8188`) ✅
- **Estado**: 7 runs generados (1536+ PNGs)
- **Checkpoints**: v1-5, dreamshaper, pixelArt, revAnimated, counterfeit
- **LoRAs**: isometric_world, pixhell, pixel_art_style
- **GPU**: RTX 4070 (CUDA 12.4)

### 2. Local — InvokeAI (`:9090`) ✅
- **Estado**: Instalado y funcional
- **Modelos**: 5 checkpoints importados

### 3. Local — Diffusers (WSL2) ✅
- **Modelo**: `runwayml/stable-diffusion-v1-5` (descarga del Hub)
- **Rendimiento**: ~4.3s por imagen en CUDA
- **Entorno**: `simmoon-cuda-env` (diffusers 0.38.0, torch 2.6.0+cu124)

### 4. Cloud — HuggingFace Inference API ❌
- **Problema**: `api-inference.huggingface.co` no resuelve DNS en esta red
- **Alternativa**: Usar Diffusers (descarga del Hub)

### 5. Cloud — Leonardo.ai ❌
- **Problema**: Requiere tarjeta de crédito
- **Cliente**: `leonardo_client.py` listo pero desactivado

---

## 🌉 Jarvis Bridge (`jarvis_bridge.py`)

Puente para que agentes externos (Jarvis) llamen al generador.

```bash
# Estado
python jarvis_bridge.py status

# Generar assets
python jarvis_bridge.py generate --category businesses --mode diffusers

# Pixelar
python jarvis_bridge.py pixelate --category businesses

# GIFs animados
python jarvis_bridge.py gif --category businesses --delay 100

# Pipeline completo
python jarvis_bridge.py run --category all --mode diffusers
```

**Salida**: Siempre JSON
```json
{"ok": true, "data": {"active_backend": "comfyui", "wsl_cuda": true}}
{"ok": false, "error": "No categories specified"}
```

---

## 🔗 Pipeline (`simmoon_pipeline.py`)

```bash
# Con Diffusers (WSL2) — recomendado
python simmoon_pipeline.py --category businesses --backend diffusers

# Con GeneratorFactory (ComfyUI local)
python simmoon_pipeline.py --category businesses --backend factory

# Pasos individuales
python simmoon_pipeline.py --category all --skip-generation  # Solo pixelar + DB
python simmoon_pipeline.py --category all --skip-pixel       # Solo generar + DB
python simmoon_pipeline.py --category all --skip-db          # Solo generar + pixelar
```

---

## 🗄️ PostgreSQL — Base de Datos `simmoon`

| Tabla | Propósito |
|-------|-----------|
| `categories` | 22 categorías de assets |
| `assets` | +500 assets con metadata |
| `generations` | Runs de generación |
| `generation_assets` | Junction table |
| `votes` | Votos 1-5⭐ persistidos |
| `colony_state` | Estado del juego por turno |
| `colony_buildings` | Edificios colocados |
| `colony_population` | Desglose de población |
| `daily_summaries` | Resúmenes diarios del proyecto (para memoria de agentes) |
| `agent_memory` | 🆕 Memoria compartida entre agentes (Buffy, Hermes, OpenHuman) |

---

## 📁 Assets Generados

### Categorías (22)

| Categoría | Icono | Items | Resolución Pixel |
|-----------|-------|-------|------------------|
| businesses | 🏢 | 12 | 64px, 16 col |
| vehicles | 🚗 | 10 | 48px, 16 col |
| buildings_misc | 🏗️ | 12 | 64px, 16 col |
| solar_energy | ⚡ | 65 | 64px, 16 col |
| lunar_sites | 🏛️ | 12 | 128px, 32 col |
| greenhouses | 🌱 | 7 | 64px, 16 col |
| characters | 👨‍🚀 | 6 | 64px, 16 col |
| roads | 🛣️ | 8 | 64px, 16 col |
| decorations | 🎨 | 8 | 64px, 16 col |
| lunar_map | 🗺️ | 8 | 64px, 16 col |
| ui_elements | 🖥️ | 9 | 32px, 8 col |
| infrastructure | 🔧 | 4 | 64px, 16 col |
| lunar_flora | 🌿 | 4 | 64px, 16 col |
| civic | 🏛️ | 2 | 64px, 16 col |
| government | 🏛️ | 2 | 64px, 16 col |
| housing | 🏠 | 4 | 64px, 16 col |
| industry | 🏭 | 4 | 64px, 16 col |
| life_support | 💨 | 3 | 64px, 16 col |
| risk_management | ⚠️ | 3 | 64px, 16 col |
| transport | 🚇 | 2 | 64px, 16 col |

**Total**: ~1500+ archivos (7 runs x 108 assets c/u, original + pixel-art + variantes por checkpoint)

### Runs de Generación (ComfyUI)
| Run | Checkpoint | LoRA | Estado |
|-----|-----------|------|--------|
| Default | v1-5-pruned-emaonly | — | ✅ |
| DreamShaper v8 | dreamshaper_8 | isometric_world | ✅ |
| DreamShaper v8 noLoRA | dreamshaper_8 | — | ✅ |
| PixelArt + LoRA | pixelArtSpriteDiffusion | pixhell | ✅ |
| PixelArt noLoRA | pixelArtSpriteDiffusion | — | ✅ |
| ReV Animated | revAnimated_v122 | — | ✅ |
| Counterfeit-V3.0 | counterfeit_v30 | — | ✅ |

---

## ⚙️ Requisitos

### Windows
- Python 3.12+
- ImageMagick 7 (`choco install imagemagick`)
- WSL2 con Ubuntu
- Chrome (para viewer.html y dashboards)

### WSL2 (Ubuntu)
- Python 3.12 (`simmoon-cuda-env`)
- CUDA 12.4 + drivers NVIDIA
- diffusers 0.38+, torch 2.6.0+cu124

### PostgreSQL 18
- Base de datos: `simmoon`
- Schema: `schema.sql`

---

## 🧪 Tests 🆕

Suite de tests unitarios en `test_*.py` ejecutable con `unittest discover`.

### Tests rápidos (modo por defecto)

```bash
cd Simmoon_arc
python -m unittest test_build_markdown_factorygames test_cargar_ayer_counts \
                    test_shared_services_agents test_workstation_dispatcher
```

| Test file | Tests | Tiempo | Skip |
|-----------|-------|--------|------|
| `test_build_markdown_factorygames.py` | 29 | 0.066 s | 1 (1 MB opt-in) |
| `test_cargar_ayer_counts.py` | 6 | 0.015 s | 0 |
| `test_shared_services_agents.py` | 19 | 0.017 s | 0 |
| `test_workstation_dispatcher.py` | 29 | 0.166 s | 0 |
| **Total** | **83** | **≈ 0.26 s** | **1** |

### Tests con stress de 1 MB (`RUN_SLOW_TESTS=1`)

Activa el test de stress que valida que `build_markdown()` no trunque
archivos grandes (> 100 KB) usando un buffer de **1 MB** sintético.

```bash
cd Simmoon_arc
RUN_SLOW_TESTS=1 python -m unittest test_build_markdown_factorygames
```

| Modo | Tests | Tiempo | Skip |
|------|-------|--------|------|
| Fast (sin env var) | 29 | 0.066 s | 1 (1 MB) |
| Slow (`RUN_SLOW_TESTS=1`) | 29 | 0.056 s | 0 |

> 📝 El test de 1 MB añade ~10 ms en este hardware (RTX 4070 + SSD
> NVMe). En máquinas más lentas el coste puede ser mayor, por eso se
> mantiene **opt-in por defecto** para no ralentizar el suite rápido.

### Cobertura de `build_markdown()`

- ✅ Frontmatter YAML válido (13 campos requeridos: `title`, `date`, `tags`,
  `importance`, `empresa`, `version`, `tipo`, `archivo_adjunto`, `caracteres`,
  `lineas`, `palabras`, `idioma`, `cargado_por`)
- ✅ Conteo de chars / lines / words correcto
- ✅ Fence de **4 backticks** (no 3) y robusto a ``` dentro del contenido
- ✅ Sin truncamiento en archivos grandes (> 100 KB, 150 KB, 1 MB)
- ✅ Edge cases: string vacío, BOM `\ufeff`, multibyte UTF-8, con y sin `\n` final

---

## 🔜 Próximos Pasos

1. Generar nuevas categorías con Diffusers (WSL2)
2. Integrar más modelos (SDXL, DreamShaper) en Diffusers
3. Mejorar el pipeline con soporte de run_suffix para Diffusers
4. Evaluar OpenCV para mejora de bordes en pixel-art
5. Probar Scenario.gg como alternativa cloud profesional

---

*Documento generado: 2026-06-12 — Estado actual del proyecto SIMMOON (incluye 🧪 sección de tests).*
