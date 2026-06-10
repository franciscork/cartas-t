#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/agent_registry.py — Registro Central de Agentes FactoryGames

Mantiene el catálogo de todos los agentes disponibles, sus capacidades,
endpoints, y funciones de health-check/launch.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.parent.resolve()


# ══════════════════════════════════════════════════════════════════════════
#  Modelos
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class AgentCapability:
    """Capacidad de un agente en el ecosistema FactoryGames."""
    agent_type: str          # 'coding', 'image', 'llm', 'service', 'supervisor'
    name: str                # 'claude-code', 'comfyui', 'ollama', etc.
    endpoint: str            # Binary path, URL, o 'tmux'
    capabilities: List[str] = field(default_factory=list)
    priority: int = 5        # 1 = mayor prioridad
    description: str = ""
    health_check_fn: Optional[Callable[[], bool]] = None
    launch_fn: Optional[Callable[[], bool]] = None

    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "name": self.name,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "priority": self.priority,
            "description": self.description,
        }


# ══════════════════════════════════════════════════════════════════════════
#  Health Check Helpers
# ══════════════════════════════════════════════════════════════════════════

def _http_healthy(url: str, timeout: int = 3) -> bool:
    """Check if an HTTP endpoint is healthy."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def _binary_available(name: str) -> bool:
    """Check if a binary is available in PATH."""
    return shutil.which(name) is not None


def _tmux_session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        r = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True, text=True, timeout=3
        )
        return r.returncode == 0
    except Exception:
        return False


def _pg_isready() -> bool:
    """Check if PostgreSQL is accepting connections."""
    try:
        r = subprocess.run(
            ["pg_isready", "-h", "localhost", "-p", "5432"],
            capture_output=True, text=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def _check_claude() -> bool:
    """Check if Claude Code CLI is available (instant)."""
    return shutil.which("claude") is not None or shutil.which("claude.exe") is not None


def _check_ollama() -> bool:
    """Check if Ollama is running."""
    return _http_healthy("http://localhost:11434/api/tags", timeout=2)


def _check_comfyui() -> bool:
    """Check if ComfyUI is running."""
    return _http_healthy("http://localhost:8188", timeout=2)


def _check_invokeai() -> bool:
    """Check if InvokeAI is running."""
    return _http_healthy("http://localhost:9090/api/v1/app/version", timeout=2)


def _check_hermes() -> bool:
    """Check if Hermes Agent is running."""
    return _http_healthy("http://localhost:9119", timeout=2)


def _check_openhuman() -> bool:
    """Check if OpenHuman is running."""
    return _http_healthy("http://localhost:7788", timeout=2)


# ══════════════════════════════════════════════════════════════════════════
#  Launch Helpers
# ══════════════════════════════════════════════════════════════════════════

def _launch_ollama() -> bool:
    """Start Ollama server."""
    try:
        subprocess.Popen(
            ["nohup", "ollama", "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _launch_comfyui() -> bool:
    """Start ComfyUI."""
    try:
        comfy_dir = Path.home() / "ComfyUI"
        if not (comfy_dir / "main.py").exists():
            return False
        subprocess.Popen(
            ["nohup", str(comfy_dir / "venv/bin/python"), "main.py", "--listen"],
            cwd=str(comfy_dir),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _launch_postgres() -> bool:
    """Start PostgreSQL service."""
    try:
        subprocess.run(
            ["sudo", "service", "postgresql", "start"],
            capture_output=True, timeout=10
        )
        return _pg_isready()
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
#  AgentRegistry
# ══════════════════════════════════════════════════════════════════════════

class AgentRegistry:
    """Registro central de agentes disponibles en FactoryGames.

    Auto-descubre los agentes disponibles y sus capacidades.
    Mantiene health checks y funciones de lanzamiento.
    """

    def __init__(self):
        self._agents: Dict[str, AgentCapability] = {}
        self._categories: Dict[str, List[str]] = {}  # agent_type -> [name, ...]
        self.discover()

    # ── Registro ──────────────────────────────────────────────────────

    def register(self, agent: AgentCapability):
        """Registrar un agente en el catálogo."""
        self._agents[agent.name] = agent
        if agent.agent_type not in self._categories:
            self._categories[agent.agent_type] = []
        if agent.name not in self._categories[agent.agent_type]:
            self._categories[agent.agent_type].append(agent.name)

    def unregister(self, name: str):
        """Eliminar un agente del registro."""
        if name in self._agents:
            agent = self._agents.pop(name)
            cat = self._categories.get(agent.agent_type, [])
            if name in cat:
                cat.remove(name)

    # ── Búsqueda ──────────────────────────────────────────────────────

    def find(self, task_type: str, capability: str = "") -> List[AgentCapability]:
        """Encontrar agentes por tipo y capacidad opcional.

        Args:
            task_type: Tipo de agente ('coding', 'image', 'llm', 'service')
            capability: Capacidad específica (opcional)

        Returns:
            Lista de agentes ordenados por prioridad
        """
        results = []
        for agent in self._agents.values():
            if agent.agent_type == task_type:
                if not capability or capability in agent.capabilities:
                    results.append(agent)
        return sorted(results, key=lambda a: a.priority)

    def get(self, name: str) -> Optional[AgentCapability]:
        """Obtener un agente por nombre."""
        return self._agents.get(name)

    def all(self) -> List[AgentCapability]:
        """Listar todos los agentes registrados."""
        return list(self._agents.values())

    def by_type(self, agent_type: str) -> List[AgentCapability]:
        """Listar agentes de un tipo específico."""
        return [a for a in self._agents.values() if a.agent_type == agent_type]

    def types(self) -> Dict[str, List[str]]:
        """Obtener categorías de agentes."""
        return dict(self._categories)

    # ── Salud ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, bool]:
        """Verificar salud de todos los agentes.

        Returns:
            Dict {agent_name: is_healthy}
        """
        result = {}
        for name, agent in self._agents.items():
            if agent.health_check_fn:
                try:
                    result[name] = agent.health_check_fn()
                except Exception:
                    result[name] = False
            else:
                result[name] = False
        return result

    def health_summary(self) -> Dict[str, dict]:
        """Obtener resumen de salud con metadatos.

        Returns:
            Dict {agent_name: {healthy, type, endpoint, capabilities}}
        """
        health = self.health()
        return {
            name: {
                "healthy": health.get(name, False),
                "type": agent.agent_type,
                "endpoint": agent.endpoint,
                "capabilities": agent.capabilities,
                "priority": agent.priority,
            }
            for name, agent in self._agents.items()
        }

    # ── Descubrimiento automático ─────────────────────────────────────

    def discover(self):
        """Auto-descubrir agentes disponibles en el sistema."""
        # ── Coding Agents ──
        self.register(AgentCapability(
            agent_type="coding",
            name="claude-code",
            endpoint="claude",
            capabilities=["refactor", "implement", "debug", "test", "review"],
            priority=1,
            description="Claude Code CLI (Anthropic) — agente de codificación",
            health_check_fn=_check_claude,
        ))

        # ── Image Generation Agents ──
        self.register(AgentCapability(
            agent_type="image",
            name="comfyui",
            endpoint="http://localhost:8188",
            capabilities=["generate", "upscale"],
            priority=1,
            description="ComfyUI — generación de imágenes local (GPU)",
            health_check_fn=_check_comfyui,
            launch_fn=_launch_comfyui,
        ))

        self.register(AgentCapability(
            agent_type="image",
            name="invokeai",
            endpoint="http://localhost:9090",
            capabilities=["generate"],
            priority=2,
            description="InvokeAI — generación de imágenes alternativa",
            health_check_fn=_check_invokeai,
        ))

        # ── LLM / Inference Agents ──
        self.register(AgentCapability(
            agent_type="llm",
            name="ollama",
            endpoint="http://localhost:11434",
            capabilities=["inference", "chat", "generate"],
            priority=1,
            description="Ollama — LLM server local",
            health_check_fn=_check_ollama,
            launch_fn=_launch_ollama,
        ))

        self.register(AgentCapability(
            agent_type="llm",
            name="hermes",
            endpoint="http://localhost:9119",
            capabilities=["chat", "assist"],
            priority=3,
            description="Hermes Agent (Nous Research) — multi-escritorio",
            health_check_fn=_check_hermes,
        ))

        self.register(AgentCapability(
            agent_type="llm",
            name="openhuman",
            endpoint="http://localhost:7788",
            capabilities=["chat", "assist"],
            priority=4,
            description="OpenHuman — asistente AI con GUI",
            health_check_fn=_check_openhuman,
        ))

        # ── Services ──
        self.register(AgentCapability(
            agent_type="service",
            name="postgresql",
            endpoint="localhost:5432",
            capabilities=["database"],
            priority=1,
            description="PostgreSQL — base de datos compartida",
            health_check_fn=_pg_isready,
            launch_fn=_launch_postgres,
        ))

        self.register(AgentCapability(
            agent_type="service",
            name="telegram-bot",
            endpoint="tmux:telegram-bot",
            capabilities=["messaging"],
            priority=2,
            description="Telegram Bot — @Jeremi_Hermes_bot",
            health_check_fn=lambda: _tmux_session_exists("telegram-bot"),
        ))

        self.register(AgentCapability(
            agent_type="service",
            name="agatha",
            endpoint="tmux:agatha-actas",
            capabilities=["reporting"],
            priority=3,
            description="Agatha Actas — reportes horarios",
            health_check_fn=lambda: _tmux_session_exists("agatha-actas"),
        ))

        # ── Supervisor (Buffy herself) ──
        self.register(AgentCapability(
            agent_type="supervisor",
            name="buffy",
            endpoint="builtin",
            capabilities=["orchestrate", "design", "plan", "review"],
            priority=1,
            description="Buffy (DeepSeek) — orquestador principal",
            health_check_fn=lambda: True,  # Buffy siempre está aquí
        ))

# ── Quick test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    registry = AgentRegistry()
    print(f"\n  🏭 FactoryGames — Agent Registry\n")
    print(f"  {'='*55}\n")

    for agent_type, agents in registry.types().items():
        print(f"  📂 {agent_type.upper()}:")
        for name in agents:
            agent = registry.get(name)
            if agent:
                print(f"     • {name:20s} {agent.endpoint:30s} {agent.description}")
        print()

    print(f"  📊 Health check:")
    for name, healthy in registry.health().items():
        icon = "✅" if healthy else "⚫"
        print(f"     {icon} {name}")
