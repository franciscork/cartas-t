#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMMOON — Dashboard Collectors
Módulo separado de dashboard.py con los collectors de estado y helpers.

Exporta:
    collect_agent_status, collect_environment, check_openhuman_health,
    collect_ollama_models, collect_obsidian_status, collect_claude_status,
    _http_healthy, _tmux_session_exists, _try_import
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

# ── SCRIPT_DIR: raíz del proyecto (Simmoon_arc/) ────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Monitor imports ──────────────────────────────────────────────────────
try:
    from monitor_sistema import (
        check_gpu, check_ram, check_disk, check_cpu_temp,
        check_services, detect_alerts, _wsl_cmd,
    )
    _MONITOR_OK = True
except ImportError:
    _MONITOR_OK = False


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _try_import(module_name: str) -> bool:
    """Check if a Python module can be imported."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def _tmux_session_exists(name: str) -> bool:
    """Check if a tmux session exists (in WSL)."""
    try:
        r = _wsl_cmd(f"tmux has-session -t {name} 2>/dev/null && echo YES || echo NO", timeout=5)
        return "YES" in r.stdout
    except Exception:
        return False


def _http_healthy(url: str, timeout: int = 3) -> bool:
    """Quick HTTP health check."""
    try:
        import urllib.request
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status < 500
    except Exception:
        return False


def _wsl_has_binary(name: str) -> bool:
    """Check if a binary exists in WSL."""
    try:
        r = _wsl_cmd(f"command -v {name} 2>/dev/null && echo FOUND || echo NOT_FOUND", timeout=5)
        return "FOUND" in r.stdout
    except Exception:
        return False


def _file_exists_in_wsl(path: str) -> bool:
    """Check if a file exists in WSL."""
    try:
        r = _wsl_cmd(f"test -f {path} && echo YES || echo NO", timeout=5)
        return "YES" in r.stdout
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Agent Status Collector
# ═══════════════════════════════════════════════════════════════════════════

def collect_agent_status() -> dict:
    """Check the status of all AI agents in the ecosystem."""
    now = datetime.now().strftime("%H:%M:%S")

    # Telegram Bot
    telegram_bot = {
        "name": "Telegram Bot",
        "icon": "🤖",
        "running": _tmux_session_exists("telegram-bot"),
        "method": "tmux",
        "desc": "Bot multi-agente @Jeremi_Hermes_bot",
    }

    # Ollama
    ollama_healthy = _http_healthy("http://localhost:11434/api/tags", timeout=2)
    ollama_models = []
    if ollama_healthy:
        try:
            import urllib.request
            r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
            data = json.loads(r.read().decode())
            ollama_models = [m["name"] for m in data.get("models", [])]
        except Exception:
            pass

    # Hermes Agent (Nous Research binary)
    hermes_agent = {
        "name": "Hermes Agent",
        "icon": "🧠",
        "running": _http_healthy("http://localhost:9119", timeout=2),
        "method": "HTTP :9119",
        "desc": "Agente multi-escritorio (Nous Research)",
        "binary": _wsl_has_binary("hermes"),
    }

    # Hermes Bridge (Python module)
    hermes_bridge = {
        "name": "Hermes Bridge",
        "icon": "🔗",
        "running": _try_import("hermes_bridge") and _file_exists_in_wsl("~/.local/bin/hermes"),
        "method": "Python",
        "desc": "Puente Simmoon ↔ Hermes",
    }

    # OpenHuman (API core en :7788)
    openhuman = {
        "name": "OpenHuman",
        "icon": "🤖",
        "running": _http_healthy("http://localhost:7788", timeout=2),
        "method": "HTTP :7788",
        "desc": "API core — no tiene web UI",
    }

    # OpenHuman Desktop (native app)
    openhuman_desktop = {
        "name": "OpenHuman Desktop",
        "icon": "🖥️",
        "running": False,
        "method": "Native App",
        "desc": "App escritorio local-first — instalar desde github.com/tinyhumansai/openhuman",
    }

    # Simmoon Agent (Python)
    simmoon_agent = {
        "name": "Simmoon Agent",
        "icon": "🎯",
        "running": (SCRIPT_DIR / "simmoon_agent.py").exists(),
        "method": "Python",
        "desc": "AI Director — recomienda assets",
    }

    # AutoGen
    autogen = {
        "name": "AutoGen",
        "icon": "👥",
        "running": (SCRIPT_DIR / "simmoon_autogen.py").exists(),
        "method": "Python",
        "desc": "Diseño multi-agente colaborativo",
    }

    # Pipeline
    pipeline = {
        "name": "Pipeline",
        "icon": "🔄",
        "running": (SCRIPT_DIR / "simmoon_pipeline.py").exists(),
        "method": "Python",
        "desc": "LangGraph: generación → pixel → DB",
    }

    # Simmoon Mecanicas (Game)
    mecanicas = {
        "name": "Simmoon Game",
        "icon": "🎮",
        "running": (SCRIPT_DIR / "juego_simmoon.py").exists(),
        "method": "Python",
        "desc": "Juego de simulación de colonia lunar",
    }

    # Agatha Actas — reportes horarios
    agatha = {
        "name": "Agatha Actas",
        "icon": "📋",
        "running": _tmux_session_exists("agatha-actas"),
        "method": "tmux",
        "desc": "Reportes horarios del sistema",
    }

    # DonHermes Bot (bot de Agatha, mismo proceso)
    agatha_cfg = (SCRIPT_DIR / "agatha_config.json").exists()
    donhermes = {
        "name": "DonHermes Bot",
        "icon": "🤖",
        "running": _tmux_session_exists("agatha-actas"),
        "method": "Telegram API",
        "desc": "Bot @Jeremias_Hermesai_bot" + (" ✅" if agatha_cfg else " ⚠️ sin config"),
    }

    # Hermes Dashboard (web UI en :9120)
    hermes_dashboard = {
        "name": "Hermes Dashboard",
        "icon": "📊",
        "running": _http_healthy("http://localhost:9120", timeout=2),
        "method": "HTTP :9120",
        "desc": "Web UI de Hermes Agent",
    }

    # Hermes Desktop (native app)
    hermes_desktop = {
        "name": "Hermes Desktop",
        "icon": "🖥️",
        "running": False,
        "method": "Native App",
        "desc": "App nativa Windows/macOS/Linux — descargar de hermes-agent.nousresearch.com",
    }

    # Obsidian Memory
    obsidian_status = collect_obsidian_status()
    obsidian_agent = {
        "name": "Obsidian Memory",
        "icon": "🪨",
        "running": obsidian_status.get("available", False),
        "method": obsidian_status.get("mode", "FS"),
        "desc": f"Vault: {obsidian_status.get('total_entries', 0)} entradas" if obsidian_status.get("available") else "Vault no disponible",
        "details": obsidian_status,
    }

    # Claude Code
    claude_status = collect_claude_status()
    claude_agent = {
        "name": "Claude Code",
        "icon": "🤖",
        "running": claude_status.get("available", False),
        "method": f"CLI v{claude_status.get('version', '?')}" if claude_status.get("version") else "CLI",
        "desc": "Agente de codificación (Anthropic)" if claude_status.get("available") else "No instalado o sin auth",
        "details": claude_status,
    }

    agents = [
        telegram_bot, hermes_agent, hermes_bridge,
        openhuman, openhuman_desktop,
        simmoon_agent, autogen, pipeline, mecanicas,
        agatha, donhermes, obsidian_agent, claude_agent,
        hermes_dashboard, hermes_desktop,
    ]

    # Services
    services_raw = {}
    if _MONITOR_OK:
        try:
            services_raw = check_services()
        except Exception:
            pass

    total_running = sum(1 for a in agents if a["running"])
    total_agents = len(agents)

    return {
        "timestamp": now,
        "agents": agents,
        "services": services_raw,
        "total_running": total_running,
        "total_agents": total_agents,
        "ollama_healthy": ollama_healthy,
        "ollama_models": ollama_models,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Environment Collector
# ═══════════════════════════════════════════════════════════════════════════

def collect_environment() -> dict:
    """Collect present environment situation."""
    now = datetime.now()

    # Uptime (WSL)
    uptime_str = "N/A"
    try:
        r = _wsl_cmd("uptime -p 2>/dev/null || uptime 2>/dev/null", timeout=5)
        uptime_str = r.stdout.strip() if r.stdout.strip() else "N/A"
    except Exception:
        pass

    # CPU temperature
    cpu_temp = None
    try:
        cpu_temp = check_cpu_temp()
    except Exception:
        pass

    # Asset counts from filesystem
    asset_count = 0
    categories_found = {}
    asset_categories = [
        "businesses", "vehicles", "greenhouses", "solar_energy",
        "lunar_map", "buildings_misc", "lunar_sites", "ui_elements",
        "roads", "decorations", "characters", "lunar_flora", "infrastructure",
    ]
    for cat in asset_categories:
        cat_dir = SCRIPT_DIR / cat
        if cat_dir.is_dir():
            pngs = list(cat_dir.glob("*.png"))
            if pngs:
                categories_found[cat] = len(pngs)
                asset_count += len(pngs)

    # Generation logs
    gen_logs = list(SCRIPT_DIR.glob("generation_log*.txt"))
    last_gen = None
    if gen_logs:
        try:
            newest = max(gen_logs, key=lambda p: p.stat().st_mtime)
            last_gen = datetime.fromtimestamp(newest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": uptime_str,
        "cpu_temp_c": cpu_temp,
        "asset_count": asset_count,
        "categories_found": categories_found,
        "total_categories": len(categories_found),
        "last_generation": last_gen,
        "active_models": [],
    }


# ═══════════════════════════════════════════════════════════════════════════
# OpenHuman Health
# ═══════════════════════════════════════════════════════════════════════════

def check_openhuman_health() -> dict:
    """Check OpenHuman health endpoint and return details."""
    try:
        import urllib.request
        r = urllib.request.urlopen("http://localhost:7788/health", timeout=5)
        data = json.loads(r.read().decode())
        return {
            "available": True,
            "ok": data.get("ok", False),
            "name": data.get("name", "openhuman"),
            "api_server": data.get("api_server", ""),
            "endpoints": list(data.get("endpoints", {}).keys()),
            "method": list(data.get("usage", {}).keys()),
        }
    except Exception:
        return {"available": False}


# ═══════════════════════════════════════════════════════════════════════════
# Ollama Models
# ═══════════════════════════════════════════════════════════════════════════

def collect_ollama_models() -> list:
    """Get list of Ollama models."""
    try:
        import urllib.request
        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        data = json.loads(r.read().decode())
        models = []
        for m in data.get("models", []):
            size_gb = m.get("size", 0) / (1024 ** 3)
            models.append({
                "name": m["name"],
                "size_gb": round(size_gb, 1),
                "family": m.get("details", {}).get("family", ""),
                "param_size": m.get("details", {}).get("parameter_size", ""),
            })
        return models
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════
# Obsidian Memory Collector
# ═══════════════════════════════════════════════════════════════════════════

_OBSIDIAN_MEMORY = None
_OBSIDIAN_FAILED = False


def _get_obsidian():
    """Lazy-load ObsidianMemory instance.

    Prioridad:
    1. REST API (si OBSIDIAN_REST_API_KEY está en entorno/config)
    2. Filesystem local (~/simmoon-memoria)

    ObsidianMemory.__init__ ya maneja el fallback internamente:
    si REST no responde, automáticamente usa filesystem.
    """
    global _OBSIDIAN_MEMORY, _OBSIDIAN_FAILED

    _OBSIDIAN_MEMORY = None
    _OBSIDIAN_FAILED = False

    if _OBSIDIAN_MEMORY is None and not _OBSIDIAN_FAILED:
        try:
            from obsidian_memory import ObsidianMemory
            vault_path = str(Path.home() / "simmoon-memoria")

            rest_api_key = os.environ.get("OBSIDIAN_REST_API_KEY", "")
            try:
                rest_port = int(os.environ.get("OBSIDIAN_REST_PORT", "27123"))
            except (ValueError, TypeError):
                rest_port = 27123
            rest_https = os.environ.get("OBSIDIAN_REST_HTTPS", "").lower() == "true"

            if not rest_api_key:
                config_path = SCRIPT_DIR / "obsidian_rest_config.json"
                if config_path.exists():
                    try:
                        with open(config_path) as f:
                            cfg = json.load(f)
                            rest_api_key = cfg.get("api_key", "")
                            rest_port = cfg.get("port", rest_port)
                            rest_https = cfg.get("https", rest_https)
                    except Exception:
                        pass

            _OBSIDIAN_MEMORY = ObsidianMemory(
                vault_path=vault_path,
                agent_name="Buffy",
                project="SIMMOON",
                rest_port=rest_port if rest_api_key else None,
                rest_api_key=rest_api_key or None,
                rest_https=rest_https,
            )
        except Exception:
            _OBSIDIAN_FAILED = True
    return _OBSIDIAN_MEMORY


def collect_obsidian_status() -> dict:
    """Collect Obsidian vault memory status."""
    result = {
        "available": False,
        "vault_path": "",
        "vault_name": "simmoon-memoria",
        "mode": "N/A",
        "total_entries": 0,
        "by_type": {},
        "diarias": 0,
        "agent_name": "Buffy",
    }
    try:
        config_path = SCRIPT_DIR / "obsidian_rest_config.json"
        if config_path.exists():
            with open(config_path) as f:
                cfg = json.load(f)
            from obsidian_memory import ObsidianRestClient
            rest = ObsidianRestClient(
                host="127.0.0.1",
                port=cfg.get("port", 27124),
                api_key=cfg.get("api_key", ""),
                use_https=cfg.get("https", True),
            )
            if rest.is_available():
                result["available"] = True
                result["vault_path"] = str(Path.home() / "simmoon-memoria")
                result["vault_name"] = "simmoon-memoria"
                result["mode"] = "REST"
                result["agent_name"] = "Buffy"
                stats = {}
                total = 0
                MEMORY_TYPES = ["context", "fact", "preference", "task", "result", "error", "conversation"]
                for mt in MEMORY_TYPES:
                    prefix = f"Buffy/{mt}/"
                    files = rest.list_notes(prefix=prefix)
                    count = len([f for f in files if f.endswith(".md")])
                    if count > 0:
                        stats[mt] = count
                        total += count
                diarias_files = rest.list_notes(prefix="Diarias/")
                result["diarias"] = len([f for f in diarias_files if f.endswith(".md")])
                result["total_entries"] = total
                result["by_type"] = stats
            else:
                result["available"] = True
                result["mode"] = "FS"
                result["vault_path"] = str(Path.home() / "simmoon-memoria")
                stats = {}
                total = 0
                vault = Path.home() / "simmoon-memoria"
                MEMORY_TYPES = ["context", "fact", "preference", "task", "result", "error", "conversation"]
                for mt in MEMORY_TYPES:
                    d = vault / "Buffy" / mt
                    if d.exists():
                        count = len(list(d.glob("*.md")))
                        if count > 0:
                            stats[mt] = count
                            total += count
                diarias_dir = vault / "Diarias"
                if diarias_dir.exists():
                    result["diarias"] = len(list(diarias_dir.glob("*.md")))
                result["total_entries"] = total
                result["by_type"] = stats
    except Exception:
        pass
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Claude Code Collector
# ═══════════════════════════════════════════════════════════════════════════

def collect_claude_status() -> dict:
    """Collect Claude Code availability and status.

    Soporta 3 modos:
    - native_ollama: ollama launch claude (Ollama v0.24+, sin API key)
    - claude_binary: Claude Code CLI instalado
    - none: no disponible
    """
    result = {
        "available": False,
        "version": "",
        "auth_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "binary_path": "",
        "native_ollama": False,
        "native_ollama_model": "",
        "backend": "none",
    }
    try:
        if _MONITOR_OK:
            # 1. Check native ollama launch claude
            r = _wsl_cmd(
                "ollama launch claude --help 2>/dev/null && echo 'NATIVE_OK' || echo 'NATIVE_NO'",
                timeout=10
            )
            out = r.stdout.strip() if r.stdout else ""
            if "NATIVE_OK" in out:
                result["available"] = True
                result["native_ollama"] = True
                result["backend"] = "native_ollama"
                r2 = _wsl_cmd("ollama list 2>/dev/null | grep ':cloud' | head -1 | awk '{print $1}'", timeout=5)
                cloud_model = r2.stdout.strip() if r2.stdout else ""
                if cloud_model:
                    result["native_ollama_model"] = cloud_model
                else:
                    result["native_ollama_model"] = "minimax-m3:cloud"

            # 2. Check Claude Code binary
            r = _wsl_cmd("command -v claude 2>/dev/null && claude --version 2>/dev/null || echo 'NOT_FOUND'", timeout=10)
            out = r.stdout.strip() if r.stdout else ""
            if "NOT_FOUND" not in out and out:
                if not result["available"]:
                    result["available"] = True
                    result["backend"] = "claude_cli"
                result["version"] = out.replace("Claude Code", "").strip()
                result["binary_path"] = "WSL: /usr/local/bin/claude"
            else:
                for name in ["claude.cmd", "claude", "claude.exe"]:
                    path = shutil.which(name)
                    if path:
                        result["available"] = True
                        result["binary_path"] = path
                        break
        else:
            for name in ["claude.cmd", "claude", "claude.exe"]:
                path = shutil.which(name)
                if path:
                    result["available"] = True
                    result["binary_path"] = path
                    break
    except Exception:
        pass
    return result
