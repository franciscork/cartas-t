#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
poblar_memoria.py — Poblar el vault de Obsidian con todos los hechos del ecosistema.

Ejecutar una vez para consolidar la memoria de todo el sistema SIMMOON.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from obsidian_memory import ObsidianMemory
import json

# Intentar usar REST API; fallback a filesystem
_rest_cfg_path = Path(__file__).parent / "obsidian_rest_config.json"
_rest_kw = {"vault_path": str(Path.home() / "simmoon-memoria"), "agent_name": "Buffy", "project": "SIMMOON"}
try:
    if _rest_cfg_path.exists():
        with open(_rest_cfg_path) as f:
            _rc = json.load(f)
        _rest_kw["rest_port"] = int(_rc.get("port", 27124))
        _rest_kw["rest_api_key"] = _rc.get("apiKey", _rc.get("api_key", ""))
        _rest_kw["rest_https"] = _rc.get("use_https", True)
        _rest_kw["rest_host"] = _rc.get("host", "127.0.0.1")
except Exception:
    pass

memory = ObsidianMemory(**_rest_kw)

# ══════════════════════════════════════════════════════════════════════════
# HECHOS FUNDACIONALES (fact, importancia=5)
# ══════════════════════════════════════════════════════════════════════════

facts = [
    ("quien_es_fran", "Fran es el CEO y dueño de la empresa. Es el creador del ecosistema SIMMOON.", ["fundacional", "ceo"]),
    ("quien_es_buffy", "Buffy es el orquestador principal y secretario personal de Fran. Coordina todos los agentes y servicios del ecosistema. Corre sobre DeepSeek v4.", ["fundacional", "orquestador"]),
    ("proposito_simmoon", "SIMMOON es una fábrica de juegos que genera assets pixel-art automáticamente usando IA. Estilo SimCity 2000 isométrico 2:1. El pipeline genera imágenes → pixel-art → GIFs → PostgreSQL.", ["fundacional", "proposito"]),
    ("hardware", "Core Ultra 7 155H / RTX 4070 8GB / 32GB RAM. Windows 11 + WSL2 Ubuntu 24.04.", ["hardware", "infraestructura"]),
    ("stack_principal", "ComfyUI :8188 (generación imágenes GPU), Ollama :11434 (LLM local, 7 modelos), PostgreSQL :5432 (base de datos simmoon), Docker (contenedores + GPU).", ["stack", "infraestructura"]),
    ("assets_generados", "1536+ PNGs en 22 categorías. 7 runs completos con todos los checkpoints. Categorías: businesses, vehicles, solar_energy, buildings_misc, lunar_sites, greenhouses, characters, roads, decorations, y más.", ["assets", "generacion"]),
    ("checkpoints_comfyui", "v1-5-pruned-emaonly, dreamshaper_8, pixelArtSpriteDiffusion, revAnimated_v122, counterfeit_v30. LoRAs: isometric_world, pixhell, pixel_art_style.", ["comfyui", "checkpoints"]),
    ("juego_simmoon_v2", "Juego estilo SimCity 2000 con Pygame 2.6.1. Grid 40×40, cámara con zoom, 86 edificios, 4 recursos (créditos, energía, oxígeno, agua), sistema de turnos, zonificación, minimapa, sonidos procedurales. Archivo: juego_simmoon.py (~2200 líneas).", ["juego", "pygame"]),
    ("modelos_ollama", "Qwen3-Coder 30.5B (principal), Qwen2.5-Coder 14B, Qwen3 14B, Gemma3-Tools 64K, Nomic-Embed-Text (embeddings). También: llama3.1:8b, tinyllama.", ["ollama", "modelos"]),
    ("backends_generacion", "Primario: ComfyUI (GPU local). Alternativos: InvokeAI :9090, Diffusers (WSL2 CUDA). Fallback cloud: Leonardo.ai (requiere tarjeta). HuggingFace Inference API bloqueado por DNS.", ["backends", "generacion"]),
]

for key, content, tags in facts:
    memory.save(key, content, memory_type="fact", tags=tags, importance=5)
    print(f"  ✅ fact: {key}")

# ══════════════════════════════════════════════════════════════════════════
# AGENTES (fact, importancia=4-5)
# ══════════════════════════════════════════════════════════════════════════

agents = [
    ("agente_hermes", "Hermes Agent v0.16.0 (Nous Research). 3 interfaces: Gateway (backend), TUI (terminal), Dashboard web :9119. Usa Ollama como backend LLM. Lanzador: launch_hermes.ps1 / launch_hermes.sh.", ["agentes", "hermes"]),
    ("agente_openhuman", "OpenHuman — asistente AI con GUI de escritorio. API JSON-RPC :7788. Healthcheck :7788/health. Integraciones: Gmail, Notion, Google Calendar. Lanzador: launch_openhuman.sh.", ["agentes", "openhuman"]),
    ("agente_jarvis", "Jarvis — asistente AI por CLI. Instalado con uv + Rye. Puente JSON al generador SIMMOON via jarvis_bridge.py. Comando: jarvis ask --model qwen3:14b.", ["agentes", "jarvis"]),
    ("agente_agatha", "Agatha Actas — agente de reportes horarios. Corre como demonio en tmux. Envía reportes periódicos del sistema. Archivo: agatha_actas.py. Lanzador: launch_agatha.sh.", ["agentes", "agatha"]),
    ("agente_claude", "Claude Code CLI (Anthropic) — agente de codificación externo. Capacidades: refactor, implement, debug, test, review. Disponible si 'claude' está en PATH.", ["agentes", "claude"]),
    ("telegram_bot", "Bot de Telegram @Jeremi_Hermes_bot. Multi-agente, corre en tmux. Archivo: telegram_bot.py. Lanzador: launch_telegram_bot.sh.", ["agentes", "telegram"]),
    ("codebuff", "Codebuff es la herramienta CLI donde Buffy opera. Es el orquestador desde Windows que se conecta a WSL2. Corre sobre DeepSeek v4.", ["agentes", "codebuff"]),
]

for key, content, tags in agents:
    memory.save(key, content, memory_type="fact", tags=tags, importance=4)
    print(f"  ✅ agent: {key}")

# ══════════════════════════════════════════════════════════════════════════
# PREFERENCIAS (preference, importancia=4)
# ══════════════════════════════════════════════════════════════════════════

prefs = [
    ("idioma_espanol", "Fran prefiere comunicación en español. Todos los reportes, resúmenes y respuestas deben ser en español.", ["preferencia", "idioma"]),
    ("estilo_comunicacion", "Comunicación directa y concisa, estilo CLI. Sin rodeos. Reportes con emojis para legibilidad.", ["preferencia", "estilo"]),
    ("tono_profesional", "Tono profesional pero cercano. Fran es el CEO, Buffy es su secretario personal y orquestador.", ["preferencia", "tono"]),
    ("prioridad_calidad", "Prioridad: calidad sobre velocidad. Mejor pocos agentes bien informados que muchos apurados.", ["preferencia", "calidad"]),
    ("modo_trabajo", "Fran trabaja con Codebuff en modo DEFAULT o MAX. Le gusta ver a todos los agentes trabajando en paralelo.", ["preferencia", "modo"]),
]

for key, content, tags in prefs:
    memory.save(key, content, memory_type="preference", tags=tags, importance=4)
    print(f"  ✅ preference: {key}")

# ══════════════════════════════════════════════════════════════════════════
# CONTEXTO DE INFRAESTRUCTURA (context, importancia=4)
# ══════════════════════════════════════════════════════════════════════════

contexts = [
    ("puertos_servicios", "ComfyUI :8188 | Ollama :11434 | PostgreSQL :5432 | InvokeAI :9090 | Hermes Dashboard :9119 | OpenHuman :7788 | Dashboard :5000 | Vote API :9099", ["infraestructura", "puertos"]),
    ("lanzadores_unificados", "ias.sh (WSL2/Linux) e ias.bat (Windows) — menú interactivo para todos los servicios. Comandos: ias start|stop|status|restart. IAS_Launcher.bat para Windows con menú visual.", ["infraestructura", "lanzadores"]),
    ("virtualenvs", "5 entornos Python conservados: ComfyUI/venv (6.1GB, CUDA), simmoon-cuda-env (6.0GB, Diffusers), simmoon-env (6.3GB, LangGraph+AutoGen), crewai-env (953MB), aiagents (114MB).", ["infraestructura", "python"]),
    ("postgresql_tablas", "Base simmoon con 10 tablas: categories, assets, generations, generation_assets, colony_state, colony_buildings, colony_population, votes, daily_summaries, agent_memory.", ["infraestructura", "postgresql"]),
    ("backups", "backup_postgres.sh — backups automáticos diarios, semanales y mensuales. restore_postgres.sh para restaurar. Ubicación: ~/backups/postgres/.", ["infraestructura", "backups"]),
    ("monitoreo", "monitor_sistema.py — healthcheck de GPU, RAM, disco, servicios, alertas. dashboard.py — dashboard web Flask :5000. nvtop — monitor GPU en terminal.", ["infraestructura", "monitoreo"]),
    ("pipeline_generacion", "generator_factory.py → ComfyUI/InvokeAI/Diffusers → simmoon_pixelator.py (pixel-art) → simmoon_gifs.py (GIFs) → PostgreSQL. Pipeline LangGraph: simmoon_pipeline.py.", ["infraestructura", "pipeline"]),
    ("sistema_memoria", "Dos sistemas de memoria: 1) agent_memory.py → PostgreSQL (tabla agent_memory), 2) obsidian_memory.py → archivos .md en vault local (~/simmoon-memoria). Sincronización bidireccional disponible.", ["infraestructura", "memoria"]),
    ("problemas_conocidos", "systemd degradado en WSL2 (servicios funcionan manualmente). HuggingFace Inference API bloqueado por DNS. Leonardo.ai requiere tarjeta de crédito.", ["infraestructura", "problemas"]),
    ("documentacion", "14 guías en formato .md: ComfyUI, Dashboard, Docker+NVIDIA, Hermes, IAS, InvokeAI, Ollama, OpenHuman, OpenJarvis, PostgreSQL, Simmoon, + integraciones. Índice: README_DOCS.md.", ["infraestructura", "docs"]),
    ("proyecto_0", "Directorio de memoria del sistema. Contiene: system_agent.html (documento maestro), estado_sistema.md, arquitectura.md, LEEME_PRIMERO.md (protocolo de inicio), acciones_hoy.md, siguiente.md.", ["infraestructura", "memoria"]),
]

for key, content, tags in contexts:
    memory.save(key, content, memory_type="context", tags=tags, importance=4)
    print(f"  ✅ context: {key}")

# ══════════════════════════════════════════════════════════════════════════
# TAREAS Y ESTADO ACTUAL
# ══════════════════════════════════════════════════════════════════════════

tasks = [
    ("sesion_2026_06_10", "Sesión iniciada. Fran pidió consolidar la memoria del ecosistema usando Obsidian. Se revisó toda la arquitectura, agentes, servicios y estado del proyecto.", ["sesion", "2026-06-10"]),
    ("memoria_consolidada", "Vault Obsidian inicializado y poblado con 30+ entradas de memoria: 10 hechos fundacionales, 7 agentes, 5 preferencias, 11 contextos de infraestructura. Sistema listo para recordar entre sesiones.", ["memoria", "consolidacion"]),
    ("proximo_obsidian_rest", "Queda pendiente instalar y configurar el plugin Local REST API en Obsidian para usar el vault real de Obsidian en vez del filesystem local. Puerto: 27123.", ["pendiente", "obsidian"]),
]

for key, content, tags in tasks:
    memory.save(key, content, memory_type="task", tags=tags, importance=4)
    print(f"  ✅ task: {key}")

# ══════════════════════════════════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
print(f"  🪨 MEMORIA OBSIDIAN — POBLADA")
print(f"  {'='*60}")
print(f"  📁 Vault: {memory.vault_path}")
print(f"  🤖 Agente: {memory.agent_name}")
print(f"  📊 Total entradas guardadas: {len(facts) + len(agents) + len(prefs) + len(contexts) + len(tasks)}")
print(f"     • Hechos fundacionales: {len(facts)}")
print(f"     • Agentes: {len(agents)}")
print(f"     • Preferencias: {len(prefs)}")
print(f"     • Contextos: {len(contexts)}")
print(f"     • Tareas: {len(tasks)}")
print(f"  {'='*60}")

# Mostrar resumen del vault
print(memory.summary())
