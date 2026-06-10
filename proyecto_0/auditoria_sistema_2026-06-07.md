# AUDITORÍA DEL SISTEMA — 2026-06-07

> **Hostname:** PULSE  
> **Sesión iniciada:** 2026-06-03 07:30 (4+ días encendido)  
> **Objetivo:** Esquema completo de Windows 11 + WSL2 Ubuntu, qué está instalado, qué se conecta, rendimiento, tabla de lanzamiento, y qué falta.

---

## 1. HARDWARE

| Componente | Detalle |
|-----------|---------|
| **Equipo** | MSI Pulse 17 AI C1VGKG |
| **CPU** | Intel Core Ultra (Family 6 Model 170 Stepping 4) — 22 hilos lógicos |
| **RAM** | 32 GB DDR5 (15.7 GB disponibles en este momento) |
| **GPU Integrada** | Intel Arc Graphics (1 GB VRAM) |
| **GPU Dedicada** | NVIDIA GeForce RTX 4070 Laptop GPU (8 GB GDDR6) |
| **Disco** | Micron 2400 NVMe SSD 1 TB (943 GB C:, 717 GB usado = 77%) |
| **Red** | Wi-Fi 6E Intel AX211 160 MHz @ 1.2 Gbps |
| **Batería** | 95% carga — Plan de energía: Alto Rendimiento |
| **BIOS** | American Megatrends E17T3IMS.106 (06/05/2024) |
| **Virtualización** | VBS activo + Hyper-V + Arranque Seguro + DMA Protection |

### Rendimiento GPU (en idle)
- **RTX 4070:** Temp 41°C, 0% utilización, 0 MB / 8188 MB VRAM en uso
- **Velocidad real LLM:** gemma3:12b ~13-20 tok/s | qwen3:14b ~8-10 tok/s

---

## 2. SISTEMA OPERATIVO

### Windows 11 Host

| Atributo | Valor |
|----------|-------|
| **Edición** | Windows 11 Pro |
| **Build** | 10.0.26200 |
| **Arquitectura** | x64 |
| **Instalado** | 15/12/2024 |
| **Idioma** | es-ES |
| **Seguridad** | VBS + HVCI + App Control for Business |

### WSL2

| Atributo | Valor |
|----------|-------|
| **Distro** | Ubuntu (única) |
| **Versión Ubuntu** | 26.04 (Resolute Raccoon) |
| **Kernel WSL** | 6.6.114.1-microsoft-standard-WSL2 |
| **systemd** | ✅ Activo |
| **RAM asignada** | ~15 GB (de 32 GB totales) |
| **CPUs visibles** | 22 cores |
| **Uptime** | ~3 horas (al momento del diagnóstico) |
| **WSLg (GUI)** | ✅ Configurado (DISPLAY=:0) |
| **CUDA** | ✅ 12.4 presente (nvcc) |
| **nvidia-smi** | ✅ Funcional dentro de WSL2 |

---

## 3. SERVICIOS ACTIVOS

### Windows Services (269 running services, 269 scheduled tasks)

| Servicio | Puerto/Info |
|----------|------------|
| **WSL2** | Hyper-V Virtual Ethernet @ 10 Gbps |
| **Wi-Fi** | Intel AX211 @ 1.2 Gbps |
| **PowerShell 7** | Instalado en `C:\Program Files\PowerShell\7` |

### WSL2 Systemd Services (19 activos)

| Servicio | Estado | Propósito |
|----------|--------|-----------|
| **docker-simmoon** | ✅ Running | Docker engine para contenedores |
| **containerd** | ✅ Running | Container runtime |
| **postgresql@18-main** | ✅ Running | PostgreSQL 18 en puerto 5432 |
| **ollama** | ✅ Running | LLM server en puerto 11434 |
| **chrony** | ✅ Running | Sincronización de reloj NTP |
| **rsyslog** | ✅ Running | Logging del sistema |
| **snapd** | ✅ Running | Snap package manager |
| **dbus** | ✅ Running | IPC del sistema |
| **systemd-journald** | ✅ Running | Journal logging |
| **systemd-resolved** | ✅ Running | Resolución DNS |

### Puertos en Escucha (WSL2)

| Puerto | Servicio | Acceso |
|--------|----------|--------|
| **11434** | Ollama API | `localhost:11434` |
| **5432** | PostgreSQL 18 | `localhost:5432` |
| **631** | CUPS (printing) | local |
| **53** | DNS (systemd-resolved) | local |

---

## 4. STACK COMPLETO — QUÉ ESTÁ INSTALADO

### 🎨 Generación de Imágenes (AI)

| Componente | Ubicación | Estado | Puerto |
|-----------|----------|--------|--------|
| **ComfyUI** | `~/ComfyUI/` (WSL2) | ⚠️ Apagado (no responde) | 8188 |
| **InvokeAI v6.13.0** | `~/invokeai/` (WSL2) | ⚠️ Apagado (no responde) | 9090 |
| **Diffusers CUDA** | `~/simmoon-cuda-env/` | ✅ Instalado | — |
| **Checkpoints** | `~/ComfyUI/models/checkpoints/` | 5 archivos | — |
| **LoRAs** | `~/ComfyUI/models/loras/` | 3 archivos (isometric, pixel) | — |
| **Assets generados** | `~/Simmoon_arc/` | 1580 PNGs | — |

### 🧠 LLMs y Agentes AI

| Componente | Detalle |
|-----------|---------|
| **Ollama** | ✅ Corriendo en :11434 |
| **Modelos Ollama** | 13 modelos instalados |
| **LangGraph** | ✅ En `simmoon-env` (`simmoon_pipeline.py`) |
| **AutoGen** | ✅ En `simmoon-env` |
| **CrewAI** | ✅ En `crewai-env` |
| **Hermes Agent** | ❌ No se encuentra `~/hermes-agent/config.yaml` |
| **OpenHuman** | ❌ `openhuman-core` no está en PATH |
| **Jarvis** | ❌ `jarvis` no está en PATH |

#### Ollama Models (13)

| Modelo | Tamaño |
|--------|--------|
| qwen3.5:9b | 6 GB |
| qwen3.5:4b | 3 GB |
| qwen3.5:2b | 2 GB |
| qwen3.5:0.8b | 0.5 GB |
| qwen2.5:3b | 1 GB |
| qwen3-64k:latest | 8 GB |
| qwen25-64k:latest | 8 GB |
| gemma3:12b | 7 GB |
| gemma3-64k:latest | 6 GB |
| deepseek-r1:8b, deepseek-r1:7b | 4 GB c/u |
| hermes3:8b | 4 GB |
| command-r7b:latest | 4 GB |

### 🗄️ Bases de Datos

| Componente | Versión | Puerto | Estado |
|-----------|---------|--------|--------|
| **PostgreSQL** | 18 | 5432 | ✅ Running |
| **Base `simmoon`** | — | — | 108 assets, 13 categorías, 8 tablas |

### 🐳 Contenedores

| Componente | Versión | Estado |
|-----------|---------|--------|
| **Docker Engine** | 29.1.3 | ✅ Running (docker-simmoon) |
| **Contenedores activos** | — | Ninguno (0) |
| **nvidia-container-toolkit** | — | ❌ No instalado |

### 🐍 Python & Entornos Virtuales

| Entorno | Ubicación | Tamaño | Propósito |
|---------|----------|--------|-----------|
| **ComfyUI/venv** | `~/ComfyUI/venv` | 6.1 GB | PyTorch CUDA + ComfyUI |
| **simmoon-cuda-env** | `~/simmoon-cuda-env` | 6.0 GB | Diffusers CUDA |
| **simmoon-env** | `~/simmoon-env` | 6.3 GB | LangGraph + AutoGen |
| **invokeai-env** | `~/invokeai-env` | — | InvokeAI v6.13.0 |
| **crewai-env** | `~/crewai-env` | 953 MB | CrewAI |
| **aiagents** | `~/aiagents` | 114 MB | Agentes ligeros |

### 📦 Gestores de Paquetes

| Herramienta | Versión | Estado |
|-------------|---------|--------|
| **uv** | 0.11.18 | ✅ En PATH |
| **pnpm** | 11.5.0 | ✅ Instalado |
| **npm** | — | ⚠️ No confirmado en WSL2 |
| **pip** | 3.12 | ✅ |
| **Snap** | chromium, cups, gnome, gtk-themes | ✅ |

### 🔧 Herramientas WSL2

| Paquete | Estado |
|---------|--------|
| CUDA Toolkit 12.4 | ✅ `nvcc` presente |
| espeak-ng | ✅ (OpenJarvis TTS) |
| libxdo3 | ✅ (OpenHuman GUI support) |
| xdotool | ✅ |

---

## 5. MAPA DE CONEXIONES

```
┌──────────────────────────────────────────────────────────────────┐
│                    WINDOWS 11 (Host)                              │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Codebuff     │  │ Chrome       │  │ PowerShell 7             │ │
│  │ (orquestador)│  │ viewer.html  │  │ launch_all.ps1           │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘ │
│         │                 │                       │               │
│         ▼                 ▼                       ▼               │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              WSL2 Ubuntu 26.04 (Hyper-V)                     │ │
│  │                                                              │ │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐                │ │
│  │  │ Ollama   │  │ ComfyUI   │  │ PostgreSQL │                │ │
│  │  │ :11434   │  │ :8188 ⚠️  │  │ :5432      │                │ │
│  │  └────┬─────┘  └─────┬─────┘  └─────┬──────┘                │ │
│  │       │              │              │                        │ │
│  │       ▼              ▼              ▼                        │ │
│  │  ┌────────────────────────────────────────┐                  │ │
│  │  │        NVIDIA RTX 4070 (8GB)           │                  │ │
│  │  │   CUDA 12.4  ·  PyTorch 2.6.0+cu124   │                  │ │
│  │  └────────────────────────────────────────┘                  │ │
│  │                                                              │ │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐                │ │
│  │  │ Docker   │  │ InvokeAI  │  │ Simmoon    │                │ │
│  │  │ :socket  │  │ :9090 ⚠️  │  │ pipeline   │                │ │
│  │  └──────────┘  └───────────┘  └────────────┘                │ │
│  │                                                              │ │
│  │  Python envs: ComfyUI · simmoon-cuda · simmoon · invokeai   │ │
│  │              crewai · aiagents                               │ │
│  │                                                              │ │
│  │  Agentes AI: LangGraph ✅ · AutoGen ✅ · CrewAI ✅           │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. TABLA DE LANZAMIENTO — CÓMO SE ARRANCA CADA COSA

| # | Componente | Ubicación | Comando / Script | Se lanza desde |
|---|-----------|----------|------------------|----------------|
| 1 | **WSL2** | Windows | `wsl -d Ubuntu` (automático al boot) | Windows Boot |
| 2 | **Ollama** | WSL2 | `systemctl start ollama` (systemd) o `ollama serve &` | WSL2 systemd |
| 3 | **PostgreSQL 18** | WSL2 | `systemctl start postgresql@18-main` (systemd) | WSL2 systemd |
| 4 | **Docker** | WSL2 | `systemctl start docker-simmoon` (systemd) | WSL2 systemd |
| 5 | **ComfyUI** | WSL2 `~/ComfyUI/` | `launch_all.ps1` → `./venv/bin/python main.py --listen --port 8188` | Windows PowerShell |
| 6 | **InvokeAI** | WSL2 `~/invokeai/` | `source ~/invokeai-env/bin/activate && invokeai-web --root ~/invokeai` | WSL2 Bash |
| 7 | **viewer.html** | Windows `Simmoon_arc/` | `launch_all.ps1` → `Start-Process chrome` | Windows PowerShell |
| 8 | **Simmoon Pipeline** | WSL2 `~/Simmoon_arc/` | `python simmoon_pipeline.py --category <cat>` | WSL2 Bash |
| 9 | **Simmoon Agent** | WSL2 `~/Simmoon_arc/` | `python simmoon_agent.py --advise` | WSL2 Bash |
| 10 | **Vote API** | WSL2 `~/Simmoon_arc/` | `python vote_api.py` → `:9099` | WSL2 Bash |
| 11 | **Juego Simmoon** | Windows | `python Simmoon_arc/juego_simmoon.py` | Windows/Codebuff |
| 12 | **Juego .exe** | Windows | `Simmoon_arc/dist/SIMMOON_1_3_0.exe` | Windows |
| 13 | **launch_all.ps1** | Windows | `.\launch_all.ps1` | Windows PowerShell |
| 14 | **launch_all.sh** | WSL2 `~/launch_all.sh` | `bash ~/launch_all.sh` | WSL2 Bash |
| 15 | **OpenHuman** | WSL2 | `openhuman-core` (NO instalado en PATH) | — |
| 16 | **Jarvis** | WSL2 | `jarvis` (NO instalado en PATH) | — |

### Scripts de Launch Disponibles

| Script | Plataforma | Qué lanza |
|--------|-----------|-----------|
| `launch_all.ps1` | Windows | WSL2 → Ollama → ComfyUI → viewer.html |
| `launch_all.sh` | WSL2 Bash | Ollama (systemd) → ComfyUI → chequea Simmoon |
| `launch_ollama.ps1` | Windows | Ollama via WSL2 |
| `launch_comfyui.ps1` | Windows | ComfyUI via WSL2 |
| `launch_invokeai.ps1` | Windows | InvokeAI via WSL2 |
| `launch_agent.ps1` | Windows | Agentes AI |
| `launch_autogen.ps1` | Windows | AutoGen agents |
| `launch_pipeline.ps1` | Windows | Simmoon pipeline |
| `launch_ias.ps1` | Windows | IAS agent |
| `launch_hermes.ps1` | Windows | Hermes agent (⚠️ no encontrado) |

---

## 7. RENDIMIENTO

### GPU (NVIDIA RTX 4070)
- **VRAM:** 8 GB GDDR6 — suficiente para modelos de ~8B params
- **Temperatura idle:** 41°C ✅
- **Inferencia LLM:** 8-20 tok/s según modelo
- **Generación de imágenes:** ComfyUI usa CUDA (no confirmado corriendo ahora)

### CPU
- **22 hilos** Intel Core Ultra — amplio margen
- Carga baja en idle

### RAM
- **32 GB total**, ~16 GB libres en Windows
- **WSL2:** ~15 GB asignados, 14 GB disponibles
- Con ComfyUI + Ollama corriendo simultáneamente, ~10-12 GB en uso de WSL2

### Disco
- **Micron 2400 NVMe 1 TB** — SSD rápido
- **Windows C::** 943 GB, 717 GB usados (77%) — ⚠️ Queda ~226 GB libres
- **WSL2 /:** 1007 GB virtual, 211 GB usados (23%)

### Red
- **Wi-Fi 6E:** 1.2 Gbps teórico — suficiente
- **WSL2 ↔ Windows:** Virtual Ethernet 10 Gbps — sin cuello de botella

### ⚠️ Puntos de atención
1. **Disco C: al 77%** — 226 GB libres. Con checkpoints, modelos y assets, vigilar.
2. **8 GB VRAM** — justo para modelos medianos. Modelos de 14B+ en 4-bit caben, pero justos.
3. **ComfyUI e InvokeAI apagados** — no se están ejecutando en este momento.
4. **0 contenedores Docker** — Docker está corriendo pero sin uso.

---

## 8. QUÉ FALTARÍA PARA UN SISTEMA MÁS COMPLETO

### 🔴 Crítico (afecta funcionalidad actual)

| Item | Descripción | Prioridad |
|------|-------------|-----------|
| **ComfyUI no responde** | Verificar por qué ComfyUI no está corriendo. Sin él, la fábrica de assets no funciona. | 🔴 ALTA |
| **PATH de WSL2 roto** | `.bashrc` línea 210 sobreescribe PATH con rutas Git Bash (`/c/...`). Ya documentado en `lee_equipo_hard_IA.md`. Limpiar. | 🔴 ALTA |
| **Node.js ausente en WSL2** | `node` y `npm` no detectados. Necesario para herramientas JS y `pnpm` ya instalado pero inútil sin Node. | 🔴 ALTA |

### 🟡 Importante (mejora significativa)

| Item | Descripción | Prioridad |
|------|-------------|-----------|
| **nvidia-container-toolkit** | Sin esto, Docker no puede usar la GPU. Fundamental para contenedores AI. | 🟡 MEDIA |
| **Hermes Agent no configurado** | `~/hermes-agent/config.yaml` no existe. El agente Hermes completo no está desplegado. | 🟡 MEDIA |
| **OpenHuman no en PATH** | `openhuman-core` no encontrado. La GUI de escritorio AI no es accesible. Instalar binario y añadir al PATH. | 🟡 MEDIA |
| **Jarvis no en PATH** | `jarvis` (asistente de voz) no encontrado. Si se desea usar, necesita reinstalación. | 🟡 MEDIA |
| **Monitoreo GPU** | `nvtop` no instalado. Sería útil para monitorear uso de GPU en tiempo real. | 🟡 MEDIA |

### 🟢 Deseable (expansión del sistema)

| Item | Descripción | Prioridad |
|------|-------------|-----------|
| **Leonardo.ai API** | Ya documentado en `LEONARDO_INVOKEAI_SCENARIO.md`. Daría capacidad de generación cloud sin usar GPU local. | 🟢 BAJA |
| **Scenario.gg** | API especializada en consistencia de estilo para juegos. Evaluado. | 🟢 BAJA |
| **Redis / cache** | Para caching de inferencias y assets. Reduciría latencia en viewer. | 🟢 BAJA |
| **Backups de PostgreSQL** | No hay script de backup de la BD `simmoon`. `pg_dump` automatizado. | 🟢 BAJA |
| **CI/CD pipeline** | Automatizar tests + generación de assets. GitHub Actions o similar. | 🟢 BAJA |
| **Grafana + Prometheus** | Dashboard de monitoreo para GPU, RAM, generaciones. | 🟢 BAJA |
| **Speach-to-Text local** | Whisper via Ollama para OpenJarvis. Ya documentado. | 🟢 BAJA |
| **HTTPS / dominio local** | mDNS o `.local` para acceder a servicios sin recordar puertos. | 🟢 BAJA |

---

## 9. ESTADO DEL PROYECTO SIMMOON

### Juego — SIMMOON v2

| Atributo | Valor |
|----------|-------|
| **Estado** | ✅ Funcional |
| **Motor** | Pygame 2.6.1 |
| **Grid** | 40×40 isométrico 2:1 |
| **Categorías** | 13 con 86+ edificios |
| **Assets** | 1580 PNGs (768 originales + 768 pixel-art + 44 extra) |
| **Modos** | Construir (B), Vender (V), Zonificar (Z), Turnos (ESPACIO) |
| **Recursos** | 💰 Créditos, ⚡ Energía, 🫁 Oxígeno, 💧 Agua |
| **.exe** | `SIMMOON_1_3_0.exe` (30 MB) |

### Pipeline de Generación

| Etapa | Estado |
|-------|--------|
| **Prompt → ComfyUI** | ✅ `generate_comfyui.py` |
| **Pixel Art** | ✅ `simmoon_pixelator.py` → 768 pixelados |
| **PostgreSQL** | ✅ `populate_db.py` → 108 assets en BD |
| **Vote API** | ✅ `vote_api.py` → :9099 |
| **Viewer** | ✅ `viewer.html` con búsqueda, stats, filtros |
| **LangGraph pipeline** | ✅ `simmoon_pipeline.py` (orquestador completo) |

### Fábrica de Juegos — Próximos Pasos Sugeridos

1. **Reactivar ComfyUI** — es el corazón de la generación
2. **Implementar Leonardo.ai como fallback** — generación cloud cuando GPU esté ocupada
3. **Automatizar el ciclo completo** — 1 comando: "genera 108 assets del checkpoint X, pixela, guarda en BD, actualiza viewer"
4. **Multi-juego** — expandir de 1 juego (Simmoon lunar) a N juegos con distintos temas

---

## 10. RESUMEN EJECUTIVO

**Fortalezas:**
- Hardware sólido: RTX 4070 (8GB), 32GB RAM, NVMe 1TB, Wi-Fi 6E
- Stack AI maduro: 3 frameworks de agentes, 13 modelos Ollama, 6 venvs Python
- Pipeline de generación completo (LangGraph → ComfyUI → Pixel → DB → Viewer)
- 1580 assets generados, juego funcional, API de votos operativa
- Docker y PostgreSQL corriendo como servicios systemd

**Debilidades:**
- ComfyUI e InvokeAI **apagados** en este momento → fábrica de assets parada
- `.bashrc` con PATH corrupto (rutas Git Bash mezcladas)
- Node.js no instalado en WSL2 (rompe tooling JS)
- Sin monitoreo GPU (`nvtop`), sin backups de BD, sin nvidia-container-toolkit
- Disco C: al 77% — monitorear crecimiento

**Acciones inmediatas recomendadas:**
1. `wsl -d Ubuntu -- bash -c "cd ~/ComfyUI && nohup ./venv/bin/python main.py --listen --port 8188 &"` — levantar ComfyUI
2. `wsl -d Ubuntu -- bash -c "curl -sSf https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs"` — instalar Node.js
3. Limpiar `.bashrc` líneas 208-210 (consolidar PATHs WSL, eliminar rutas Git Bash)
4. `wsl -d Ubuntu -- bash -c "sudo apt-get install -y nvtop nvidia-container-toolkit"` — instalar herramientas faltantes

---

*Informe generado: 2026-06-07 — Auditoría completa del sistema PULSE.*
