# Arquitectura SIMMOON — FÁBRICA DE JUEGOS

> Fecha: 2026-06-07
> Esquema completo del ecosistema tras la auditoría y mejoras.

---

## Diagrama

```
Windows 11 ── Codebuff (orquestador) + ias.bat
│
└── WSL2 Ubuntu 26.04 ────────────────────────────────────────────────
    │
    ├── 🧠 Ollama :11434 ─── LLM Server (7 modelos)
    │   ├── Qwen3-Coder 30.5B (principal)
    │   ├── Qwen2.5-Coder 14B
    │   ├── Qwen3 14B
    │   ├── Gemma3-Tools
    │   └── Nomic-Embed-Text (embeddings)
    │
    ├── 🎨 ComfyUI :8188 ─── Generación de imágenes (GPU RTX 4070 8GB)
    │   ├── Checkpoints: dreamshaper_8, pixelArtSpriteDiffusion, etc.
    │   └── LoRAs: pixhell_15, etc.
    │
    ├── 🖼️  InvokeAI :9090 ─── Generación alternativa (opcional)
    │
    ├── 🧠 Hermes Agent :9119 ─── 3 escritorios (Gateway + TUI + Dashboard)
    │
    ├── 🤖 OpenHuman :7788 ─── Asistente AI con GUI (opcional)
    │
    ├── 💬 Jarvis ─── Asistente AI CLI (uv + Rye)
    │
    ├── 📊 Monitor Sistema ─── GPU, RAM, disco, servicios, alertas
    │
    ├── 📊 Dashboard :5000 ─── Web monitoring (Flask)
    │
    ├── 🗄️  PostgreSQL :5432 ─── Base de datos simmoon (5 tablas)
    │
    ├── 🐳 Docker 29.1.3 + nvidia-container-toolkit
    │
    ├── 📦 nvtop 3.2.0 ─── Monitor GPU en terminal
    │
    └── Agentes Python:
        ├── simmoon_agent.py ─── AI Director (recomienda qué generar)
        ├── simmoon_autogen.py ─── Diseño multi-agente (Generator+Critic+Curator)
        ├── simmoon_pipeline.py ─── LangGraph: ComfyUI → PixelArt → PostgreSQL
        ├── generator_factory.py ─── Fábrica unificada con fallback Leonardo.ai
        ├── leonardo_client.py ─── Cliente REST para Leonardo.ai (cloud)
        ├── monitor_sistema.py ─── Healthcheck diario
        └── dashboard.py ─── Dashboard web Flask
```

---

## Stack Actual (Producción)

| Componente | Puerto | Estado | Propósito |
|-----------|--------|--------|-----------|
| **Codebuff** | CLI | ✅ Activo | Orquestador desde Windows |
| **WSL2 Ubuntu 26.04** | — | ✅ | Sistema base Linux |
| **ComfyUI** | 8188 | ✅ | Generación de assets por IA |
| **Ollama** | 11434 | ✅ | LLM local (7 modelos) |
| **PostgreSQL** | 5432 | ✅ | Base de datos simmoon |
| **Docker** | socket | ✅ | Contenedores + GPU |
| **nvtop** | CLI | ✅ | Monitor GPU en terminal |
| **Flask** | 5000 | ✅ | Dashboard web de monitoreo |

### Backends de Generación

| Backend | Tipo | Estado | Archivo |
|---------|------|--------|---------|
| **ComfyUI** | 🖥️ Local GPU | ✅ Primario | `generate_comfyui.py` |
| **Leonardo.ai** | ☁️ Cloud API | ✅ Fallback | `leonardo_client.py` |
| **InvokeAI** | 🖥️ Local | ⏳ Opcional | `generate_invokeai.py` |

### Agentes AI

| Framework | Estado | Uso | Archivo |
|-----------|--------|-----|---------|
| **LangGraph** | ✅ | Pipeline generación → pixel → DB | `simmoon_pipeline.py` |
| **AutoGen** | ✅ | Diseño multi-agente colaborativo | `simmoon_autogen.py` |
| **Simmoon Agent** | ✅ | AI Director (recomendaciones) | `simmoon_agent.py` |
| **Hermes** | ✅ | Agente 3 escritorios (Nous) | `launch_hermes.ps1` |
| **OpenHuman** | ✅ | Asistente AI GUI | `launch_openhuman.sh` |
| **Jarvis** | ✅ | Asistente AI CLI | `launch_jarvis.sh` |

---

## Flujo de Trabajo (Generación de Assets)

```
Codebuff / ias launcher (Windows)
    │
    │  "Genera assets con fallback a Leonardo.ai"
    ▼
generator_factory.py
    ├── 1. ¿ComfyUI :8188 responde? → build_workflow() → GPU local
    │   └── generate_comfyui.py (checkpoint + LoRAs)
    │
    └── 2. ¿No? ¿LEONARDO_API_KEY? → Leonardo.ai cloud
        └── leonardo_client.py (REST puro, sin SDK)
            │
            ▼
        Imagen generada → Simmoon_arc/<categoria>/
            │
            ├── simmoon_pixelator.py → Pixel Art
            │
            └── simmoon_pipeline.py → PostgreSQL
                │
                ▼
            viewer.html → Chrome (galería con votación)
```

---

## Lanzadores Unificados

| Archivo | Plataforma | Uso |
|---------|-----------|-----|
| **ias.sh** | Linux/WSL2 | `ias start \| stop \| status \| restart` |
| **ias.bat** | Windows | `ias start \| stop \| status \| restart` |
| **launch_simmoon.py** | Python | Menú interactivo + CLI flags |

### ias (Intelligent Agent System)

```bash
# WSL2/Linux
ias                  # Menú interactivo
ias start            # Inicia todos los backends
ias start comfyui    # Solo ComfyUI
ias stop             # Detiene todo
ias status           # Estado de todos los servicios
ias backup           # Backup PostgreSQL
ias models           # Lista modelos Ollama

# Windows
ias.bat start        # Inicia todos los backends
ias.bat status       # Estado
ias.bat stop         # Detiene todo
```

---

## Archivos Clave por Categoría

### Generación de Imágenes
| Archivo | Rol |
|---------|-----|
| `Simmoon_arc/generate_comfyui.py` | Cliente ComfyUI canónico (workflows, queue, polling) |
| `Simmoon_arc/leonardo_client.py` | Cliente REST Leonardo.ai (fallback cloud) |
| `Simmoon_arc/generator_factory.py` | Fábrica unificada con fallback automático |
| `Simmoon_arc/simmoon_generator.py` | Orquestador multi-backend (ComfyUI + HuggingFace) |
| `Simmoon_arc/simmoon_pipeline.py` | Pipeline LangGraph (generate → pixel → DB) |
| `Simmoon_arc/test_leonardo.py` | Test Leonardo.ai (usa leonardo_client.py) |

### Agentes AI
| Archivo | Rol |
|---------|-----|
| `Simmoon_arc/simmoon_agent.py` | AI Director — recomienda assets a generar |
| `Simmoon_arc/simmoon_autogen.py` | Diseño multi-agente (Generator + Critic + Curator) |

### Monitoreo y Sistema
| Archivo | Rol |
|---------|-----|
| `Simmoon_arc/monitor_sistema.py` | Healthcheck: GPU, RAM, disco, servicios, alertas |
| `Simmoon_arc/dashboard.py` | Dashboard web Flask (:5000) |

### Lanzadores
| Archivo | Plataforma |
|---------|-----------|
| `ias.sh` | Linux/WSL2 — lanzador unificado |
| `ias.bat` | Windows — lanzador unificado |
| `Simmoon_arc/launch_simmoon.py` | Python — menú interactivo |

---

## Comandos Rápidos

```bash
# Lanzar todo (desde WSL2)
ias start

# Estado de servicios
ias status

# Generar assets con fallback automático
cd ~/Simmoon_arc
python generator_factory.py    # Muestra estado de backends
python simmoon_pipeline.py --category businesses

# Monitoreo
python monitor_sistema.py      # Reporte en consola
python monitor_sistema.py --watch 30  # Cada 30s
python dashboard.py            # Dashboard web :5000

# Backup PostgreSQL
ias backup
# o manual: bash ~/backup_postgres.sh

# Restaurar backup
bash ~/restore_postgres.sh ~/backups/postgres/daily/simmoon_*.sql.gz

# Ver logs
tail -f ~/.simmoon-logs/comfyui.log
tail -f ~/.simmoon-logs/ollama.log

# GPU info
nvtop
```

---

## Problemas Conocidos

| Problema | Estado | Workaround |
|----------|--------|------------|
| **sudo pide password sin TTY** | ✅ Arreglado | Passwordless sudo configurado |
| **apt-get se congela** | ✅ Arreglado | Usar `wsl -u root` o sudo passwordless |
| **systemd degradado** | ⚠️ | Servicios funcionan manualmente |
