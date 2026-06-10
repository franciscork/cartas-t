# Estado del Sistema — Fábrica de Juegos SIMMOON

> Fecha: 2026-06-04 (noche)  
> Solo lo que importa para la fábrica de juegos.

---

## Windows 11 (Host)

| Componente | Estado | Detalle |
|-----------|--------|---------|
| **Freebuff/Codebuff** | ✅ | Orquestador principal |
| **WSL2** | ✅ | Ubuntu 24.04, systemd activo |
| **Chrome** | ✅ | viewer.html + ComfyUI |

---

## WSL2 Ubuntu — Stack Activo

### 🎨 ComfyUI (Backend de Generación Oficial)
| Atributo | Valor |
|----------|-------|
| **Puerto** | `8188` |
| **Estado** | ✅ Corriendo |
| **Python** | 3.12.13 (venv) |
| **PyTorch** | 2.6.0+cu124 (CUDA ✅) |
| **Checkpoints** | 5 (v1-5, dreamshaper, pixelart, revAnimated, counterfeit_v30) |
| **LoRAs** | 3 (isometric_world, pixhell, pixel_art_style) |
| **Runs generados** | **7/7** ✅ (todos los checkpoints regenerados) |
| **Comando** | `python generate_comfyui.py --suffix <run> --checkpoint <file>` |

### 🧠 Ollama (LLM Local)
| Atributo | Valor |
|----------|-------|
| **Puerto** | `11434` |
| **Estado** | ✅ Corriendo |
| **Modelos** | qwen3-coder (30.5B), llama3.1:8b, tinyllama |
| **Uso principal** | Backend LLM para agentes AI |

### 🐳 Docker
| Atributo | Valor |
|----------|-------|
| **Versión** | 29.1.3 |
| **Estado** | ✅ Servicio activo |

### 📦 Gestores de Paquetes
| Herramienta | Versión | Estado |
|-------------|---------|--------|
| **uv** | 0.11.18 | ✅ En PATH |
| **pnpm** | 11.5.0 | ✅ Instalado |

### 🐍 Python
| Versión | Dónde | Uso |
|---------|-------|-----|
| **3.12.13** | `~/ComfyUI/venv` + `~/simmoon-cuda-env` | Generación CUDA + ComfyUI |

---

## Assets Generados

| Run | Checkpoint | Assets | Estado |
|-----|-----------|--------|--------|
| Default (v1-5) | `v1-5-pruned-emaonly` | 108 | ✅ + pixel |
| DreamShaper v8 + LoRA | `dreamshaper_8` | 108 | ✅ + pixel |
| DreamShaper v8 (no LoRA) | `dreamshaper_8` | 108 | ✅ + pixel |
| Pixel Art + LoRA | `pixelArtSpriteDiffusion` | 108 | ✅ + pixel |
| Pixel Art (no LoRA) | `pixelArtSpriteDiffusion` | 108 | ✅ + pixel |
| ReV Animated | `revAnimated_v122` | 108 | ✅ + pixel |
| **Counterfeit-V3.0** | `counterfeit_v30` | 108 | ✅ + pixel |
| **TOTAL** | | **1536 PNGs** | ✅ |

---

## Eliminado del Proyecto

| Componente | Motivo |
|-----------|--------|
| ~~A1111 SD WebUI~~ | Reemplazado por ComfyUI (mejor rendimiento) |
| ~~openclaw~~ | No necesario para la fábrica de juegos |

---

## En Estudio

| Herramienta | Tipo | Evaluación |
|-------------|------|------------|
| **Leonardo.ai** | ☁️ API cloud | Pay-as-you-go, buen plan gratuito |
| **InvokeAI** | 🖥️ Local | Unified Canvas, instalación guiada |
| **Scenario.gg** | ☁️ API juegos | Consistencia de estilo, plan profesional |

---

## PostgreSQL

| Atributo | Valor |
|----------|-------|
| **Estado** | ✅ Servicio activo en puerto 5432 |
| **Base de datos** | `simmoon` — 108 assets, 13 categorías |
| **Uso** | Persistencia de assets, votos, y estado del juego |

### Tablas
| Tabla | Propósito |
|-------|-----------|
| `categories` | 13 categorías de assets |
| `assets` | 108 assets con metadata completa |
| `generations` | 7 runs de generación registrados |
| `generation_assets` | Junction table generations ↔ assets |
| `colony_state` | 🆕 Estado del juego por turno (recursos, población) |
| `colony_buildings` | 🆕 Edificios colocados en la cuadrícula de la colonia |
| `colony_population` | 🆕 Desglose de población por turno |
| `votes` | 🆕 Votos persistidos (1-5 estrellas) desde viewer.html — **tabla creada, API validada** |

---

## 🆕 Novedades de la Sesión

### Pipeline LangGraph
- `Simmoon_arc/simmoon_pipeline.py` — Orquestador: Prompts → ComfyUI → Pixel Art → PostgreSQL
- Uso: `python simmoon_pipeline.py --category businesses`

### Vote API
- `Simmoon_arc/vote_api.py` — Servidor HTTP para persistir votos en PostgreSQL
- Endpoint: `http://localhost:9099/api/votes`
- **✅ Validado:** stats, POST, GET all, GET single — todos funcionando
- **Fix aplicado:** `dbname` vs `database` para compatibilidad psycopg2/psycopg3
- viewer.html sincroniza votos con la API (fallback a localStorage si no disponible)

### Pixel-Art
- 768 imágenes originales → 768 pixel-art = 1536 PNGs totales
- 7 runs completos con pixel-art en 13 categorías cada uno
- Runs: default, counterfeit_v30, dreamshaper_v8, dreamshaper_v8_nolora, pixelart, pixelart_nolora, rev_animated

### InvokeAI
- v6.13.0 instalado en `~/invokeai-env` (Python 3.12)
- ✅ Modelo v1-5-pruned-emaonly importado y funcional
- ✅ Generación de prueba exitosa: "lunar mining office isometric pixel art"
- UI en `http://127.0.0.1:9090`
- Comando: `source ~/invokeai-env/bin/activate && invokeai-web --root ~/invokeai`

### Viewer.html v2
- 🔍 Búsqueda por nombre de asset
- 📊 Stats: muestra número de runs activos
- ❌ Runs vacíos removidos (`rev_aniso`, `rev_pixel`)
- 🔄 Sincronización de votos con PostgreSQL

### Virtualenvs Consolidados
| Eliminado | Motivo |
|-----------|--------|
| `~/sd_env` | ❌ Huérfano de A1111 |
| `~/sd_env2` | ❌ Huérfano de A1111 |
| `~/crewai_env` | ❌ Duplicado de `crewai-env` |
| `~/openclaw-env` | ❌ Ya eliminado en sesión anterior |

**Conservados (5):**
| Entorno | Tamaño | Propósito |
|---------|--------|-----------|
| `ComfyUI/venv` | 6.1 GB | ComfyUI + PyTorch CUDA |
| `simmoon-cuda-env` | 6.0 GB | Diffusers CUDA |
| `simmoon-env` | 6.3 GB | LangGraph + AutoGen |
| `crewai-env` | 953 MB | CrewAI (Py3.12) |
| `aiagents` | 114 MB | Agentes ligeros |

### En Estudio
| Herramienta | Estado |
|-------------|--------|
| **InvokeAI v6.13.0** | 📥 Descarga pendiente — `curl -L https://github.com/invoke-ai/InvokeAI/releases/latest` |
| **Leonardo.ai** | 📄 Documentado en `LEONARDO_INVOKEAI_SCENARIO.md` |
| **Scenario.gg** | 📄 Documentado en `LEONARDO_INVOKEAI_SCENARIO.md` |

### Pendiente
- `openclaw` — ✅ desinstalado (sudo npm uninstall -g)

---

## 🎮 Juego SIMMOON v2

| Atributo | Valor |
|----------|-------|
| **Motor** | Pygame 2.6.1 |
| **Estilo** | SimCity 2000 isométrico 2:1 |
| **Grid** | 40×40 tiles (expandido) |
| **Cámara** | Zoom 0.5x-2.0x + WASD |
| **Edificios** | 86 en catálogo (74 originales + 12 oficios extraños), 33 públicos + 53 privados |
| **Footprints** | 1×1, 2×1, 2×2, 3×2, 4×4 tiles |
| **Recursos** | 💰 Créditos, ⚡ Energía, 🫁 Oxígeno, 💧 Agua |
| **Modos** | 🔨 Construir (B) + 💸 Vender (V) + 🗺️ Zonificar (Z) |
| **Turnos** | ⏩ Botón + ESPACIO, overlay resumen post-turno + auto-settlement |
| **Población** | Crece con empleos, cae con déficits |
| **Filtro de votos** | Solo edificios con ≥1⭐ aparecen |
| **Archivo** | `Simmoon_arc/juego_simmoon.py` (~2200 líneas) |
| **.exe** | `Simmoon_arc/dist/SIMMOON_1_3_0.exe` — 30 MB ✅ |

### 🆕 Oficios Extraños (12 nuevos)
| Atributo | Valor |
|----------|-------|
| **Rubros** | 8: ecológico, vivienda, industrial, cívico-comercial, aeroespacial, investigación, entretenimiento, militar |
| **Mecánica** | Pinta zonas con Z → emprendedores auto-settlean → pagas prima + alquiler variable |
| **Auto-settlement** | Hasta 5 edificios/turno en tiles zonificados libres |
| **Primas** | Pago único al asentarse (varía por rubro: 40-800💰) |
| **Alquiler** | Ingreso por turno (varía por rubro: 8-200💰/turno) |
| **Energía** | ⚡ Pública — colocación directa por la comisión |
| **Edificios públicos** | Carreteras, energía, agua, O2, bomberos, policía, decoración, parques → colocación directa |
| **Edificios privados** | Negocios, vehículos, invernaderos, viviendas, sitios → auto-settlement en zonas |

### Minimapa + Sonidos
| Atributo | Valor |
|----------|-------|
| **Minimapa** | 156×156px, esquina inferior izquierda, colores por categoría, viewport dinámico |
| **Sonidos** | 🔊 Construir, 💰 Vender, 🔄 Turno, ⚠️ Alerta — procedurales (PCM sintetizado) |

### Categorías
| # | Categoría | Items |
|---|-----------|-------|
| 1 | 🏢 Negocios | 11 |
| 2 | ⚡ Energía | 6 |
| 3 | 🚗 Vehículos | 10 |
| 4 | 🛣️ Carreteras | 8 |
| 5 | 🎨 Decoración | 8 |
| 6 | 🌱 Invernaderos | 7 |
| 7 | 🏗️ Edificios | 12 |
| 8 | 🏛️ Sitios Lunares | 12 |

---

*Documento actualizado: 2026-06-04 (noche) — SIMMOON v2 con 8 categorías y sistema de turnos.*
