#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shared_services_agents.py — Única fuente de verdad para servicios, agentes
y puestos de trabajo del sistema SIMMOON / FactoryGames.

Este módulo centraliza el registro de TODAS las "entidades" que el sistema
supervisa, eliminando la duplicación que existía entre:
  - `SERVICE_DEFINITIONS` y `FACTORY_WORKSTATIONS` (que contenía los
    mismos 4 servicios duplicados)
  - `AGENT_DEFINITIONS` y `FACTORY_WORKSTATIONS` (que contenía los
    mismos 3 agentes duplicados)

Diseño:
  - `ENTITIES`: lista única con todas las entidades. Cada una tiene
    `kinds` (subconjunto de {"service", "agent", "workstation"}) para
    permitir que una misma entidad sea, p.ej., un servicio HTTP Y un
    puesto de trabajo de la fábrica al mismo tiempo.
  - Vistas derivadas: `SERVICES`, `AGENTS`, `WORKSTATIONS` filtran `ENTITIES`.
  - Aliases de retrocompatibilidad: `SERVICE_DEFINITIONS` (tuplas de 4),
    `SERVICE_DISPLAY` (dict), `AGENT_DEFINITIONS` (tuplas de 5),
    `KNOWN_SERVICES_TOTAL`, `KNOWN_AGENTS_TOTAL`.

Importado por:
  - connect_agents_to_memory.py (re-exporta)
  - agatha_actas.py (usa WORKSTATIONS para supervisar la fábrica)
  - _cargar_ayer_obsidian.py (usa SERVICE_DEFINITIONS + AGENT_DEFINITIONS)
  - dashboard, monitor, etc.
"""
from typing import Dict, List


# ── Catálogo unificado de entidades ───────────────────────────────────────
# Cada entidad es un dict con al menos:
#   - key:        identificador único (str)
#   - name:       nombre para mostrar
#   - kinds:      lista de roles ("service" | "agent" | "workstation")
#   - type:       categoría semántica ("engine" | "agent" | "design" | ...)
#   - check_type: estrategia de comprobación
#       "always_on"      → siempre True (servicio central)
#       "script_exists"  → SCRIPT_DIR/<target>.exists()
#       "db_conn"        → get_db_conn() es no-None
#       "http"           → check_http(target, timeout)
#       "wsl_http"       → check_wsl_http(target, timeout)
#       "windows_process"→ check_windows_process(target)
#       "path_exists"    → os.path.isdir(target) or os.path.exists(target)
#   - check_target / check_timeout (opcionales, según check_type)
#   - emoji, port, url, health_url, role, order, ... (opcionales)

ENTITIES: List[dict] = [
    # ── Servicios backend (HTTP endpoints) ───────────────────────────────
    {
        "key": "ollama",
        "name": "Ollama",
        "kinds": ["service", "workstation"],
        "type": "engine",
        "emoji": "🧠",
        "url": "http://localhost:11434",
        "port": 11434,
        "check_type": "http",
        "check_target": "http://localhost:11434",
        "check_timeout": 2,
        "role": "Motor de LLM local (modelos AI)",
        "order": 0,
    },
    {
        "key": "comfyui",
        "name": "ComfyUI",
        "kinds": ["service", "workstation"],
        "type": "engine",
        "emoji": "🎨",
        "url": "http://localhost:8188",
        "port": 8188,
        "check_type": "http",
        "check_target": "http://localhost:8188",
        "check_timeout": 2,
        "role": "Generación de imágenes con workflow visual",
        "order": 1,
    },
    {
        "key": "postgresql",
        "name": "PostgreSQL",
        "kinds": ["service", "workstation"],
        "type": "storage",
        "emoji": "🗄️",
        "url": "http://localhost:5432",
        "port": 5432,
        "check_type": "db_conn",
        "check_target": None,
        "role": "Base de datos compartida / memoria persistente",
        "order": 0,
    },
    {
        "key": "openhuman",
        "name": "OpenHuman",
        "kinds": ["service", "agent", "workstation"],
        "type": "agent",
        "emoji": "🤖",
        "url": "http://localhost:7788",
        "port": 7788,
        "check_type": "http",
        "check_target": "http://localhost:7788/health",
        "check_timeout": 3,
        "health_url": "http://localhost:7788/health",
        "role": "Agente open-source",
        "order": 1,
    },

    # ── Agentes IA / Bots ────────────────────────────────────────────────
    {
        "key": "telegram_bot",
        "name": "Telegram Bot",
        "kinds": ["agent", "workstation"],
        "type": "communication",
        "emoji": "📱",
        "check_type": "windows_process",
        "check_target": "telegram_bot",
        "health_url": None,
        "role": "Interfaz de chat con agentes",
        "order": 0,
    },
    {
        "key": "hermes",
        "name": "Hermes Agent",
        "kinds": ["agent", "workstation"],
        "type": "agent",
        "emoji": "🧠",
        "check_type": "http",
        "check_target": "http://localhost:9119",
        "check_timeout": 3,
        "health_url": "http://localhost:9119",
        "role": "Agente Nous Research con memoria",
        "order": 0,
    },

    # ── Puestos de trabajo de la fábrica (sólo workstations únicos) ───────
    {
        "key": "agatha_actas",
        "name": "Agatha Actas",
        "kinds": ["workstation"],
        "type": "management",
        "emoji": "📋",
        "check_type": "always_on",
        "check_target": None,
        "role": "Supervisora General",
        "order": 0,
    },
    {
        "key": "simmoon_agent",
        "name": "Director de Arte",
        "kinds": ["workstation"],
        "type": "design",
        "emoji": "🎨",
        "check_type": "script_exists",
        "check_target": "simmoon_agent.py",
        "role": "Recomienda qué assets generar vía IA",
        "order": 0,
    },
    {
        "key": "simmoon_autogen",
        "name": "Diseñador Colaborativo",
        "kinds": ["workstation"],
        "type": "design",
        "emoji": "🤝",
        "check_type": "script_exists",
        "check_target": "simmoon_autogen.py",
        "role": "AutoGen: Generator + Critic + Curator",
        "order": 1,
    },
    {
        "key": "simmoon_generator",
        "name": "Generador Multi-Backend",
        "kinds": ["workstation"],
        "type": "production",
        "emoji": "🖼️",
        "check_type": "script_exists",
        "check_target": "simmoon_generator.py",
        "role": "Genera assets con ComfyUI / HuggingFace",
        "order": 0,
    },
    {
        "key": "simmoon_diffusers",
        "name": "Generador Diffusers",
        "kinds": ["workstation"],
        "type": "production",
        "emoji": "🧪",
        "check_type": "script_exists",
        "check_target": "simmoon_diffusers.py",
        "role": "Genera assets vía Diffusers en WSL2",
        "order": 1,
    },
    {
        "key": "simmoon_pixelator",
        "name": "Pixelador",
        "kinds": ["workstation"],
        "type": "production",
        "emoji": "🎮",
        "check_type": "script_exists",
        "check_target": "simmoon_pixelator.py",
        "role": "Convierte assets a pixel-art retro",
        "order": 2,
    },
    {
        "key": "simmoon_pipeline",
        "name": "Pipeline Completo",
        "kinds": ["workstation"],
        "type": "production",
        "emoji": "🏭",
        "check_type": "script_exists",
        "check_target": "simmoon_pipeline.py",
        "role": "LangGraph: Prompt → Generar → Pixelar → DB",
        "order": 3,
    },
    {
        "key": "generator_factory",
        "name": "Generator Factory",
        "kinds": ["workstation"],
        "type": "production",
        "emoji": "🏗️",
        "check_type": "script_exists",
        "check_target": "generator_factory.py",
        "role": "Fábrica de backends con fallback chain",
        "order": 4,
    },
    {
        "key": "creativo_juegos",
        "name": "Creativo de Juegos",
        "kinds": ["workstation"],
        "type": "design",
        "emoji": "🎮",
        "check_type": "script_exists",
        "check_target": "factory/agent_creativo.py",
        "role": "Dirección Creativa y Diseño de Mecánicas",
        "order": 2,
    },
    {
        "key": "guionista",
        "name": "Guionista",
        "kinds": ["workstation"],
        "type": "design",
        "emoji": "✍️",
        "check_type": "script_exists",
        "check_target": "factory/agent_guionista.py",
        "role": "Narrativa, Diálogos y World-Building",
        "order": 3,
    },
    {
        "key": "reuniones",
        "name": "Sistema de Reuniones",
        "kinds": ["workstation"],
        "type": "management",
        "emoji": "🏢",
        "check_type": "script_exists",
        "check_target": "simmoon_reuniones.py",
        "role": "Brainstorming semanal y actas en Obsidian",
        "order": 1,
    },
    {
        "key": "quality_inspector",
        "name": "Quality Inspector",
        "kinds": ["workstation"],
        "type": "monitoring",
        "emoji": "🎯",
        "check_type": "script_exists",
        "check_target": "simmoon_quality_inspector.py",
        "role": "Control de calidad: verifica assets, detecta corruptos",
        "order": 0,
    },
    {
        "key": "monitor_sistema",
        "name": "Monitor Sistema",
        "kinds": ["workstation"],
        "type": "monitoring",
        "emoji": "📊",
        "check_type": "monitor_ok",  # Special: needs monitor_sistema.collect_report
        "check_target": None,
        "role": "Monitoreo de GPU/RAM/disco/servicios",
        "order": 1,
    },
    {
        "key": "gimp",
        "name": "GIMP",
        "kinds": ["workstation"],
        "type": "design",
        "emoji": "🖌️",
        "check_type": "path_exists",
        "check_target": r"C:\Users\docus\AppData\Local\Programs\GIMP 3",
        "role": "Edición y post-procesado de assets",
        "order": 4,
    },
    {
        "key": "blender",
        "name": "Blender",
        "kinds": ["workstation"],
        "type": "design",
        "emoji": "🏗️",
        "check_type": "path_exists",
        "check_target": r"C:\Program Files\Blender Foundation\Blender 5.1",
        "role": "Modelado 3D, renders y animaciones",
        "order": 5,
    },
]


# ── Vistas derivadas ──────────────────────────────────────────────────────
def _by_kinds(*wanted: str) -> List[dict]:
    return [e for e in ENTITIES if any(k in e.get("kinds", []) for k in wanted)]


SERVICES: List[dict] = _by_kinds("service")
AGENTS: List[dict] = _by_kinds("agent")
WORKSTATIONS: List[dict] = _by_kinds("workstation")


# ── Lookups por clave ─────────────────────────────────────────────────────
SERVICE_BY_KEY: Dict[str, dict] = {e["key"]: e for e in SERVICES}
AGENT_BY_KEY: Dict[str, dict] = {e["key"]: e for e in AGENTS}
WORKSTATION_BY_KEY: Dict[str, dict] = {e["key"]: e for e in WORKSTATIONS}


# ── Aliases de retrocompatibilidad ────────────────────────────────────────
# Estos son consumidos por _cargar_ayer_obsidian.py, connect_agents_to_memory,
# agatha_actas, etc. Mantener el shape (tupla 4 / tupla 5) intacto evita
# romper unpacking tipo `for key, name, _url, _tipo in SERVICE_DEFINITIONS`.

def _entity_service_tuple(e: dict) -> tuple:
    """Proyecta una entidad-servicio al shape 4-tuple legacy."""
    return (e["key"], e["name"], e.get("url", ""), e.get("type", ""))


def _entity_agent_tuple(e: dict) -> tuple:
    """Proyecta una entidad-agente al shape 5-tuple legacy."""
    return (
        e["key"],
        e["name"],
        e.get("type", ""),
        e.get("health_url"),
        e.get("check_type", ""),
    )


SERVICE_DEFINITIONS: List[tuple] = [_entity_service_tuple(e) for e in SERVICES]
"""Lista canónica de servicios backend (4-tupla). Backward compat."""

SERVICE_DISPLAY: Dict[str, dict] = {
    e["key"]: {
        "emoji": e.get("emoji", "📡"),
        "port": e.get("port", "?"),
        "check": e.get("check_type", "http"),
    }
    for e in SERVICES
}
"""Display info de servicios (emoji, port, check). Backward compat."""

AGENT_DEFINITIONS: List[tuple] = [_entity_agent_tuple(e) for e in AGENTS]
"""Lista canónica de agentes IA (5-tupla). Backward compat."""


# ── Totales (calculados dinámicamente) ────────────────────────────────────
KNOWN_SERVICES_TOTAL: int = len(SERVICES)
KNOWN_AGENTS_TOTAL: int = len(AGENTS)
KNOWN_WORKSTATIONS_TOTAL: int = len(WORKSTATIONS)
KNOWN_ENTITIES_TOTAL: int = len(ENTITIES)
