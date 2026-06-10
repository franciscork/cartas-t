#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMMOON — Dashboard Web de Monitoreo y Control Agéntico
Dashboard compacto con estado de agentes, entorno, y controles.

Uso:
    python dashboard.py                  # http://localhost:5000
    python dashboard.py --port 8080      # Puerto personalizado
    python dashboard.py --host 0.0.0.0   # Accesible desde red local
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from flask import Flask, jsonify, render_template_string

# ── Monitor imports ──────────────────────────────────────────────────────
try:
    from monitor_sistema import (
        check_gpu, check_ram, check_disk, check_cpu_temp,
        check_services, detect_alerts, _wsl_cmd,
    )
    _MONITOR_OK = True
except ImportError:
    _MONITOR_OK = False

# ── System Logger ────────────────────────────────────────────────────────
try:
    from system_logger import log as syslog, get_recent as get_logs
    _LOG_OK = True
except ImportError:
    _LOG_OK = False

# ── Helper: check if a service exists ────────────────────────────────────
def _try_import(module_name):
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


# ── Agent Status Collector ──────────────────────────────────────────────
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

    # OpenHuman Desktop (native app — se instala aparte)
    openhuman_desktop = {
        "name": "OpenHuman Desktop",
        "icon": "🖥️",
        "running": False,  # Native app, no verificable desde aquí
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

    # Hermes Desktop (native app — se instala aparte)
    hermes_desktop = {
        "name": "Hermes Desktop",
        "icon": "🖥️",
        "running": False,  # Native app, no se puede verificar desde aquí
        "method": "Native App",
        "desc": "App nativa Windows/macOS/Linux — descargar de hermes-agent.nousresearch.com",
    }

    # 🆕 Obsidian Memory
    obsidian_status = collect_obsidian_status()
    obsidian_agent = {
        "name": "Obsidian Memory",
        "icon": "🪨",
        "running": obsidian_status.get("available", False),
        "method": obsidian_status.get("mode", "FS"),
        "desc": f"Vault: {obsidian_status.get('total_entries', 0)} entradas" if obsidian_status.get("available") else "Vault no disponible",
        "details": obsidian_status,
    }

    # 🆕 Claude Code
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

    # Count total running
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
        "active_models": [],  # populated by caller
    }


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


# ── Obsidian Memory Collector ───────────────────────────────────────────
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
    
    # Forzar recreacion con codigo fresco (evita cache stale de .pyc)
    _OBSIDIAN_MEMORY = None
    _OBSIDIAN_FAILED = False
    
    if _OBSIDIAN_MEMORY is None and not _OBSIDIAN_FAILED:
        try:
            from obsidian_memory import ObsidianMemory
            vault_path = str(Path.home() / "simmoon-memoria")
            
            # Detectar API key de entorno o archivo de config
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
            
            # Una sola instanciación — ObsidianMemory maneja el fallback
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
        # Usar ObsidianRestClient directamente (bypassea el singleton y
        # el cache de modulos que causa total_entries=0)
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
                MEMORY_TYPES = ["context","fact","preference","task","result","error","conversation"]
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
                # Fallback a filesystem
                result["available"] = True
                result["mode"] = "FS"
                result["vault_path"] = str(Path.home() / "simmoon-memoria")
                stats = {}
                total = 0
                vault = Path.home() / "simmoon-memoria"
                MEMORY_TYPES = ["context","fact","preference","task","result","error","conversation"]
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


# ── Claude Code Collector ────────────────────────────────────────────────
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
        # Check via WSL if possible
        if _MONITOR_OK:
            # 1. Check native ollama launch claude (mejor opción)
            r = _wsl_cmd(
                "ollama launch claude --help 2>/dev/null && echo 'NATIVE_OK' || echo 'NATIVE_NO'",
                timeout=10
            )
            out = r.stdout.strip() if r.stdout else ""
            if "NATIVE_OK" in out:
                result["available"] = True
                result["native_ollama"] = True
                result["backend"] = "native_ollama"
                # Detect installed cloud model
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
                # Try Windows
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


# ── Flask App ────────────────────────────────────────────────────────────
app = Flask(__name__)


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIMMOON — Dashboard de Control Agéntico</title>
    <style>
        :root {
            --bg: #08080c;
            --card: #101018;
            --card2: #14141e;
            --border: #1c1c2e;
            --text: #d0d0dc;
            --text-dim: #6a6a80;
            --text-bright: #f0f0ff;
            --accent: #6c5ce7;
            --accent2: #00cec9;
            --green: #00b894;
            --green-bg: rgba(0, 184, 148, 0.1);
            --yellow: #fdcb6e;
            --yellow-bg: rgba(253, 203, 110, 0.1);
            --red: #ff7675;
            --red-bg: rgba(255, 118, 117, 0.1);
            --blue: #74b9ff;
            --radius: 8px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 12px;
            font-size: 13px;
        }

        /* ── Header ── */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 4px 10px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 10px;
            flex-wrap: wrap;
            gap: 6px;
        }
        .header h1 {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.3px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .header h1 .dot {
            width: 8px; height: 8px; border-radius: 50%;
            display: inline-block;
        }
        .header h1 .dot.green { background: var(--green); box-shadow: 0 0 6px var(--green); }
        .header h1 .dot.red { background: var(--red); box-shadow: 0 0 6px var(--red); }
        .header .meta {
            display: flex;
            align-items: center;
            gap: 14px;
            font-size: 0.75rem;
            color: var(--text-dim);
        }
        .header .meta .live-dot {
            width: 6px; height: 6px; border-radius: 50%;
            background: var(--green);
            display: inline-block;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

        /* ── Grid ── */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 8px;
            margin-bottom: 8px;
        }
        .grid-4 { grid-template-columns: repeat(4, 1fr); }
        .grid-3 { grid-template-columns: repeat(3, 1fr); }
        .grid-full { grid-column: 1 / -1; }

        /* ── Cards ── */
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 10px 12px;
            transition: border-color 0.15s;
        }
        .card:hover { border-color: var(--accent); }

        .card h2 {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-dim);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .card h2 .icon { font-size: 0.9rem; }

        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 3px 0;
            font-size: 0.8rem;
        }
        .metric .label { color: var(--text-dim); }
        .metric .value { font-weight: 500; }
        .metric .value.green { color: var(--green); }
        .metric .value.yellow { color: var(--yellow); }
        .metric .value.red { color: var(--red); }
        .metric .value.blue { color: var(--blue); }

        .progress-bar {
            width: 100%; height: 4px;
            background: var(--border);
            border-radius: 2px;
            margin: 3px 0;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%; border-radius: 2px;
            transition: width 0.5s ease;
        }
        .progress-fill.green { background: var(--green); }
        .progress-fill.yellow { background: var(--yellow); }
        .progress-fill.red { background: var(--red); }

        /* ── Agent rows ── */
        .agent-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 1px;
        }
        .agent-group {
            margin-bottom: 6px;
        }
        .agent-group:last-child {
            margin-bottom: 0;
        }
        .agent-group-header {
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            padding: 4px 4px 3px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2px;
        }
        .agent-group-header .count {
            color: var(--text-dim);
            font-weight: 400;
        }
        .agent-row {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 4px;
            font-size: 0.78rem;
            border-radius: 4px;
            transition: background 0.12s;
        }
        .agent-row:hover {
            background: rgba(108, 92, 231, 0.06);
        }
        .agent-row .a-icon { font-size: 0.9rem; width: 18px; text-align: center; flex-shrink: 0; }
        .agent-row .a-dot {
            width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
        }
        .agent-row .a-dot.on { background: var(--green); box-shadow: 0 0 4px var(--green); }
        .agent-row .a-dot.off { background: var(--red); opacity: 0.4; }
        .agent-row .a-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .agent-row .a-status {
            font-size: 0.6rem;
            padding: 1px 7px;
            border-radius: 4px;
            font-weight: 700;
            letter-spacing: 0.3px;
            flex-shrink: 0;
        }
        .agent-row .a-status.on { background: var(--green-bg); color: var(--green); }
        .agent-row .a-status.off { background: var(--red-bg); color: var(--red); }

        /* ── Model pills ── */
        .model-pill {
            display: inline-block;
            padding: 2px 7px;
            margin: 1px 2px;
            border-radius: 4px;
            background: var(--card2);
            border: 1px solid var(--border);
            font-size: 0.65rem;
            color: var(--text);
            white-space: nowrap;
        }
        .model-pill.active {
            border-color: var(--accent);
            background: rgba(108, 92, 231, 0.15);
            color: var(--accent2);
        }
        .model-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 2px;
            margin-top: 4px;
        }

        /* ── Control buttons ── */
        .control-row {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 4px;
        }
        .ctrl-btn {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border: 1px solid var(--border);
            border-radius: 5px;
            background: var(--card2);
            color: var(--text);
            font-size: 0.72rem;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.15s;
            font-family: inherit;
        }
        .ctrl-btn:hover {
            border-color: var(--accent);
            background: rgba(108, 92, 231, 0.1);
            color: var(--text-bright);
        }
        .ctrl-btn.primary {
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }
        .ctrl-btn.primary:hover {
            background: #7c5cfc;
            box-shadow: 0 0 12px rgba(108, 92, 231, 0.3);
        }
        .ctrl-btn.green {
            background: var(--green);
            border-color: var(--green);
            color: #000;
        }
        .ctrl-btn.green:hover {
            box-shadow: 0 0 10px var(--green);
        }

        /* ── Alert ── */
        .alert-box {
            padding: 6px 10px;
            border-radius: 5px;
            font-size: 0.75rem;
            margin: 4px 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .alert-box.warn { background: var(--yellow-bg); border: 1px solid rgba(253,203,110,0.2); color: var(--yellow); }
        .alert-box.err { background: var(--red-bg); border: 1px solid rgba(255,118,117,0.2); color: var(--red); }
        .alert-box.ok { background: var(--green-bg); border: 1px solid rgba(0,184,148,0.2); color: var(--green); }

        /* ── Log entries ── */
        .log-entry {
            display: flex;
            align-items: baseline;
            gap: 6px;
            padding: 1px 4px;
            border-radius: 3px;
            transition: background 0.15s;
        }
        .log-entry:hover { background: rgba(108,92,231,0.08); }
        .log-entry .log-ts {
            color: var(--text-dim);
            font-size: 0.62rem;
            flex-shrink: 0;
            width: 7.5em;
        }
        .log-entry .log-icon { flex-shrink: 0; font-size: 0.78rem; }
        .log-entry .log-source {
            color: var(--accent2);
            font-weight: 600;
            flex-shrink: 0;
            font-size: 0.65rem;
        }
        .log-entry .log-msg {
            color: var(--text);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        #logContainer::-webkit-scrollbar {
            width: 4px;
        }
        #logContainer::-webkit-scrollbar-track {
            background: var(--card);
        }
        #logContainer::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 2px;
        }

        /* ── Footer ── */
        .footer {
            text-align: center;
            font-size: 0.65rem;
            color: var(--text-dim);
            padding: 12px;
            border-top: 1px solid var(--border);
            margin-top: 8px;
        }

        /* ── Responsive ── */
        @media (max-width: 900px) {
            .grid-4 { grid-template-columns: repeat(2, 1fr); }
            .grid-3 { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 500px) {
            body { padding: 6px; font-size: 12px; }
            .grid-4, .grid-3 { grid-template-columns: 1fr; }
            .header { flex-direction: column; align-items: start; }
        }
    </style>
</head>
<body>

<!-- ═══ HEADER ═══ -->
<div class="header">
    <h1>
        <span class="dot {{ 'green' if healthy else 'red' }}"></span>
        ☾ SIMMOON — Control Agéntico
    </h1>
    <div class="meta">
        <span><span class="live-dot"></span> Live</span>
        <span id="tsDisplay">{{ timestamp }}</span>
        <span>🤖 {{ agent_stats.running }}/{{ agent_stats.total }} agentes</span>
    </div>
</div>

<!-- ═══ SYSTEM GRID ═══ -->
<div class="grid grid-4">

    <!-- GPU -->
    <div class="card">
        <h2><span class="icon">🎮</span> GPU</h2>
        {% if gpu.available %}
        <div class="metric"><span class="label">Modelo</span><span class="value">{{ gpu.name[:45] }}</span></div>
        <div class="metric">
            <span class="label">Temp</span>
            <span class="value {{ 'green' if gpu.temperature_c < 70 else 'yellow' if gpu.temperature_c < 85 else 'red' }}">
                {{ gpu.temperature_c }}°C
            </span>
        </div>
        <div class="metric">
            <span class="label">VRAM</span>
            <span class="value blue">{{ gpu.memory_used_mb }}/{{ gpu.memory_total_mb }}MB</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill {{ 'green' if gpu.memory_used_percent < 70 else 'yellow' if gpu.memory_used_percent < 90 else 'red' }}"
                 style="width:{{ gpu.memory_used_percent }}%"></div>
        </div>
        <div class="metric"><span class="label">Util</span><span class="value">{{ gpu.utilization_gpu_percent }}%</span></div>
        {% if gpu.fan_speed_percent > 0 %}
        <div class="metric"><span class="label">Fan</span><span class="value">{{ gpu.fan_speed_percent }}%</span></div>
        {% endif %}
        {% else %}
        <div class="metric"><span class="label">Estado</span><span class="value red">No detectada</span></div>
        {% endif %}
    </div>

    <!-- RAM -->
    <div class="card">
        <h2><span class="icon">🧠</span> RAM</h2>
        <div class="metric">
            <span class="label">Usada</span>
            <span class="value {{ 'green' if ram.used_percent < 70 else 'yellow' if ram.used_percent < 90 else 'red' }}">
                {{ ram.used_gb }}/{{ ram.total_gb }}GB
            </span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill {{ 'green' if ram.used_percent < 70 else 'yellow' if ram.used_percent < 90 else 'red' }}"
                 style="width:{{ ram.used_percent }}%"></div>
        </div>
        <div class="metric"><span class="label">Disponible</span><span class="value green">{{ ram.available_gb }}GB</span></div>
    </div>

    <!-- Disco -->
    <div class="card">
        <h2><span class="icon">💾</span> Disco</h2>
        {% for mount, info in disk.items() %}
        <div class="metric">
            <span class="label">{{ mount.split('/')[-1] or mount }}</span>
            <span class="value {{ 'green' if info.available_gb > 100 else 'yellow' if info.available_gb > 50 else 'red' }}">
                {{ info.available_gb }}GB libre
            </span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill {{ 'green' if info.used_percent < 70 else 'yellow' if info.used_percent < 90 else 'red' }}"
                 style="width:{{ info.used_percent }}%"></div>
        </div>
        {% endfor %}
    </div>

    <!-- Servicios backend -->
    <div class="card">
        <h2><span class="icon">🔌</span> Backends</h2>
        {% for name, svc in services.items() %}
        <div class="metric">
            <span class="label">
                <span class="agent-row" style="padding:1px 0;gap:4px;">
                    <span class="a-dot {{ 'on' if svc.healthy else 'off' }}"></span>
                    {{ svc.name if svc.name else name }}
                </span>
            </span>
            <span class="value" style="font-size:0.7rem;color:var(--text-dim);">{{ svc.latency_ms }}ms</span>
        </div>
        {% endfor %}
    </div>
</div>

<!-- ═══ MEMORIA + CLAUDE ═══ -->
<div class="grid grid-3">
    <!-- Obsidian Memory -->
    <div class="card">
        <h2><span class="icon">🪨</span> Memoria Obsidian</h2>
        {% if obsidian.available %}
        <div class="metric"><span class="label">Estado</span><span class="value green">● Activo [{{ obsidian.mode }}]</span></div>
        <div class="metric"><span class="label">Vault</span><span class="value" style="font-size:0.65rem;">{{ obsidian.vault_name }}</span></div>
        <div class="metric"><span class="label">Entradas</span><span class="value blue">{{ obsidian.total_entries }}</span></div>
        {% if obsidian.by_type %}
        <div style="margin-top:4px;">
            {% for mtype, count in obsidian.by_type.items() %}
            <div class="metric" style="font-size:0.7rem;"><span class="label">  {{ mtype }}</span><span class="value" style="font-size:0.7rem;">{{ count }}</span></div>
            {% endfor %}
        </div>
        {% endif %}
        {% if obsidian.diarias > 0 %}
        <div class="metric" style="font-size:0.7rem;"><span class="label">📅 Diarias</span><span class="value">{{ obsidian.diarias }}</span></div>
        {% endif %}
        {% else %}
        <div class="metric"><span class="label">Estado</span><span class="value red">No disponible</span></div>
        <div class="metric"><span class="label">Vault</span><span class="value" style="font-size:0.65rem;">~/simmoon-memoria</span></div>
        {% endif %}
    </div>

    <!-- Claude Code -->
    <div class="card">
        <h2><span class="icon">🤖</span> Claude Code</h2>
        {% if claude.available %}
        <div class="metric"><span class="label">Estado</span><span class="value green">● Disponible</span></div>
        {% if claude.version %}
        <div class="metric"><span class="label">Versión</span><span class="value blue">v{{ claude.version }}</span></div>
        {% endif %}
        {% if claude.native_ollama %}
        <div class="metric"><span class="label">Backend</span><span class="value green">🦙 Ollama Nativo (v0.24+)</span></div>
        {% if claude.native_ollama_model %}
        <div class="metric"><span class="label">Modelo</span><span class="value" style="font-size:0.7rem;">{{ claude.native_ollama_model }}</span></div>
        {% endif %}
        <div class="metric"><span class="label">API Key</span><span class="value green">❌ No necesita</span></div>
        {% else %}
        <div class="metric"><span class="label">Backend</span><span class="value green">🦙 Ollama (local gratis)</span></div>
        {% endif %}
        {% if claude.binary_path %}
        <div class="metric"><span class="label">Binario</span><span class="value" style="font-size:0.6rem;">{{ claude.binary_path[:30] }}</span></div>
        {% endif %}
        <div class="metric"><span class="label">Rol</span><span class="value" style="font-size:0.7rem;">Sub-agente de Buffy</span></div>
        {% else %}
        <div class="metric"><span class="label">Estado</span><span class="value red">No disponible</span></div>
        <div class="metric"><span class="label">Backend</span><span class="value green">🦙 Ollama directo</span></div>
        <div class="metric"><span class="label">Modo</span><span class="value" style="font-size:0.7rem;">BuffySupervisor → Ollama</span></div>
        {% endif %}
    </div>

    <!-- Buffy (Orquestador) -->
    <div class="card">
        <h2><span class="icon">👑</span> Buffy — Orquestador</h2>
        <div class="metric"><span class="label">Estado</span><span class="value green">● Activo</span></div>
        <div class="metric"><span class="label">Modelo</span><span class="value blue">DeepSeek v4</span></div>
        <div class="metric"><span class="label">Rol</span><span class="value">CEO Assistant · Supervisor</span></div>
        <div class="metric"><span class="label">Memoria</span><span class="value {{ 'green' if obsidian.available else 'yellow' }}">{{ '🪨 Obsidian' if obsidian.available else '⚠️ Sin Obsidian' }}</span></div>
        <div class="metric"><span class="label">Workers</span><span class="value {{ 'green' if claude.available else 'yellow' }}">{{ '🤖 Claude' if claude.available else '⚠️ Sin Claude' }}</span></div>
    </div>
</div>

<!-- ═══ AGENT STATUS ═══ -->
<div class="grid grid-3">
    <div class="card grid-full">
        <h2><span class="icon">🤖</span> Estado de Agentes IA <span style="color:var(--text-dim);font-weight:400;font-size:0.65rem;">{{ agent_stats.running }}/{{ agent_stats.total }} activos</span></h2>
        {% set on_agents = agent_stats.list|selectattr('running')|list %}
        {% set off_agents = agent_stats.list|rejectattr('running')|list %}
        {% if on_agents %}
        <div class="agent-group">
            <div class="agent-group-header" style="color:var(--green);">🟢 Activos <span class="count">({{ on_agents|length }})</span></div>
            <div class="agent-grid">
            {% for agent in on_agents %}
                <div class="agent-row" title="{{ agent.method }}{% if agent.desc %} — {{ agent.desc }}{% endif %}">
                    <span class="a-icon">{{ agent.icon }}</span>
                    <span class="a-dot on"></span>
                    <span class="a-name">{{ agent.name }}</span>
                    <span class="a-status on">ON</span>
                </div>
            {% endfor %}
            </div>
        </div>
        {% endif %}
        {% if off_agents %}
        <div class="agent-group">
            <div class="agent-group-header" style="color:var(--text-dim);">⬜ Inactivos <span class="count">({{ off_agents|length }})</span></div>
            <div class="agent-grid">
            {% for agent in off_agents %}
                <div class="agent-row" title="{{ agent.method }}{% if agent.desc %} — {{ agent.desc }}{% endif %}">
                    <span class="a-icon">{{ agent.icon }}</span>
                    <span class="a-dot off"></span>
                    <span class="a-name">{{ agent.name }}</span>
                    <span class="a-status off">OFF</span>
                </div>
            {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
</div>

<!-- ═══ ENVIRONMENT + CONTROLS ═══ -->
<div class="grid grid-3">
    <!-- Situación del Entorno -->
    <div class="card">
        <h2><span class="icon">🌍</span> Entorno</h2>
        <div class="metric"><span class="label">⏱️ Uptime</span><span class="value" style="font-size:0.75rem;">{{ env.uptime }}</span></div>
        <div class="metric"><span class="label">🖼️ Assets</span><span class="value blue">{{ env.asset_count }}</span></div>
        <div class="metric"><span class="label">📂 Categorías</span><span class="value blue">{{ env.total_categories }}</span></div>
        {% if env.last_generation %}
        <div class="metric"><span class="label">🔄 Última gen</span><span class="value" style="font-size:0.7rem;">{{ env.last_generation }}</span></div>
        {% endif %}
        {% if env.cpu_temp_c %}
        <div class="metric"><span class="label">🌡️ CPU</span><span class="value">{{ "%.1f" % env.cpu_temp_c }}°C</span></div>
        {% endif %}
        <!-- OpenHuman health -->
        {% if openhuman.available and openhuman.ok %}
        <div style="margin-top:6px;padding-top:4px;border-top:1px solid var(--border);">
            <div style="font-size:0.65rem;color:var(--text-dim);margin-bottom:2px;">🤖 OpenHuman <span style="color:var(--green);">●</span></div>
            <div class="metric" style="font-size:0.7rem;"><span class="label">API</span><span class="value" style="font-size:0.65rem;">{{ openhuman.api_server[:35] }}{{ '…' if openhuman.api_server|length > 35 }}</span></div>
            <div class="metric" style="font-size:0.7rem;"><span class="label">Endpoints</span><span class="value" style="font-size:0.65rem;color:var(--accent2);">{{ openhuman.endpoints|join(', ') }}</span></div>
        </div>
        {% elif openhuman.available and not openhuman.ok %}
        <div style="margin-top:6px;padding-top:4px;border-top:1px solid var(--border);">
            <div style="font-size:0.65rem;color:var(--text-dim);">🤖 OpenHuman <span style="color:var(--red);">●</span> <span style="color:var(--red);">health: false</span></div>
        </div>
        {% endif %}
        <!-- Ollama models -->
        {% if ollama_models %}
        <div style="margin-top:6px;">
            <div style="font-size:0.65rem;color:var(--text-dim);margin-bottom:3px;">🧠 Modelos Ollama ({{ ollama_models|length }})</div>
            <div class="model-grid">
                {% for m in ollama_models[:8] %}
                <span class="model-pill {{ 'active' if m.get('active') else '' }}" title="{{ m.size_gb }}GB · {{ m.param_size }}">
                    {{ m.name[:24] }}{{ '…' if m.name|length > 24 }}
                </span>
                {% endfor %}
                {% if ollama_models|length > 8 %}
                <span class="model-pill">+{{ ollama_models|length - 8 }} más</span>
                {% endif %}
            </div>
        </div>
        {% endif %}
    </div>

    <!-- Controles Agénticos -->
    <div class="card">
        <h2><span class="icon">🎛️</span> Controles</h2>
        <div style="font-size:0.7rem;color:var(--text-dim);margin-bottom:4px;">Servicios según estado</div>
        <div class="control-row">
            {% for svc in servicios %}
            {% if svc.healthy %}
            <a href="{{ svc.url }}" target="_blank" class="ctrl-btn primary" title="{{ svc.name }} — {{ svc.desc }}">{{ svc.icon }}{{ svc.name }}<span style="font-size:0.6rem;opacity:0.7;margin-left:2px;">:{{ svc.port }}</span></a>
            {% else %}
            <span class="ctrl-btn" style="opacity:0.35;cursor:not-allowed;pointer-events:none;" title="{{ svc.name }} — {{ svc.desc }}">{{ svc.icon }}{{ svc.name }}<span style="font-size:0.6rem;opacity:0.7;margin-left:2px;">:{{ svc.port }}</span></span>
            {% endif %}
            {% endfor %}
        </div>
        <div style="font-size:0.7rem;color:var(--text-dim);margin:6px 0 4px;">Comandos CLI (tmux)</div>
        <div class="control-row">
            <span class="ctrl-btn" onclick="copyCmd('ias status')" title="Copiar comando">📋 ias status</span>
            <span class="ctrl-btn" onclick="copyCmd('ias start ollama')" title="Iniciar Ollama">▶️ Ollama</span>
            <span class="ctrl-btn" onclick="copyCmd('ias start telegram')" title="Iniciar Telegram Bot">▶️ Telegram</span>
            <span class="ctrl-btn" onclick="copyCmd('ias stop')" title="Detener todos los servicios">⏹️ Stop All</span>
            <span class="ctrl-btn" onclick="copyCmd('ias restart')" title="Reiniciar todos los servicios">🔄 Restart</span>
        </div>
        <div style="font-size:0.7rem;color:var(--text-dim);margin:6px 0 4px;">Visualizaciones</div>
        <div class="control-row">
            <a href="http://localhost:5000" class="ctrl-btn primary" title="Este dashboard">📊 Dashboard</a>
            {% if services.get('ollama',{}).get('healthy') %}
            <a href="http://localhost:11434" target="_blank" class="ctrl-btn" title="Ollama WebUI">🧠 Ollama</a>
            {% endif %}
            <a href="../viewer.html" class="ctrl-btn" title="Asset Gallery" target="_blank">🖼️ Gallery</a>
            <a href="../system_agent.html" class="ctrl-btn" title="System Agent" target="_blank">🤖 System Agent</a>
        </div>
    </div>

    <!-- Alertas -->
    <div class="card">
        <h2><span class="icon">🚨</span> Alertas</h2>
        {% if alerts %}
            {% for alert in alerts %}
            <div class="alert-box {{ 'err' if '❌' in alert else 'warn' }}">
                <span>{{ '❌' if '❌' in alert else '⚠️' }}</span>
                {{ alert.replace('❌ ','').replace('⚠️ ','') }}
            </div>
            {% endfor %}
        {% else %}
        <div class="alert-box ok">✅ Sin alertas — todos los sistemas nominales</div>
        {% endif %}
    </div>
</div>

<!-- ═══ LOGS ═══ -->
<div class="grid grid-3">
    <div class="card grid-full">
        <h2><span class="icon">📜</span> Últimos Eventos <span id="logCount" style="color:var(--text-dim);font-weight:400;font-size:0.65rem;"></span></h2>
        <div id="logContainer" style="max-height:240px;overflow-y:auto;font-size:0.72rem;font-family:'Consolas','Courier New',monospace;line-height:1.6;">
            <div style="color:var(--text-dim);">Cargando eventos...</div>
        </div>
    </div>
</div>

<div class="footer">
    ☾ SIMMOON — Actualización automática cada 10s · <a href="/api/health" target="_blank" style="color:var(--accent);text-decoration:none;">API JSON</a>
</div>

<script>
// ── Auto-refresh via fetch ──────────────────────────────────────────────
function copyCmd(cmd) {
    navigator.clipboard.writeText(cmd).then(() => {
        // brief visual feedback
    }).catch(() => {});
}

function refreshData() {
    fetch('/api/dashboard')
        .then(r => r.json())
        .then(data => {
            // Update timestamp
            document.getElementById('tsDisplay').textContent = data.timestamp;

            // Update agent stats in header
            const headerStats = document.querySelector('.header .meta span:last-child');
            if (headerStats) {
                headerStats.textContent = '🤖 ' + data.agent_stats.running + '/' + data.agent_stats.total + ' agentes';
            }

            // Update health dot
            const dot = document.querySelector('.header h1 .dot');
            if (dot) {
                dot.className = 'dot ' + (data.healthy ? 'green' : 'red');
            }

            // Reload full page if any critical data changed (GPU, RAM, etc.)
            // For simplicity, just do a full reload every 30s
        })
        .catch(() => {});
}

// ── Log auto-refresh ────────────────────────────────────────────────────
function refreshLogs() {
    fetch('/api/logs')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('logContainer');
            const countEl = document.getElementById('logCount');
            if (!container) return;

            const entries = data.entries || [];
            if (countEl) countEl.textContent = '· ' + entries.length + ' eventos';

            if (entries.length === 0) {
                container.innerHTML = '<div style="color:var(--text-dim);padding:4px 0;">Sin eventos registrados aún.</div>';
                return;
            }

            let html = '';
            for (const e of entries) {
                const ts = e.ts ? e.ts.slice(11, 19) : '';  // HH:MM:SS
                html += '<div class="log-entry">';
                html += '<span class="log-ts">' + escHtml(ts) + '</span>';
                html += '<span class="log-icon">' + escHtml(e.icon || '•') + '</span>';
                html += '<span class="log-source">' + escHtml(e.source || '') + '</span>';
                html += '<span class="log-msg">' + escHtml(e.message || '') + '</span>';
                html += '</div>';
            }
            container.innerHTML = html;
        })
        .catch(() => {});
}

function escHtml(s) {
    const div = document.createElement('div');
    div.textContent = s || '';
    return div.innerHTML;
}

// Auto-refresh logs every 10s
refreshLogs();
setInterval(refreshLogs, 10000);

// ── Dashboard data refresh ──────────────────────────────────────────────
setInterval(refreshData, 8000);
setTimeout(() => location.reload(), 180000);
</script>
</body>
</html>
"""


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render dashboard."""
    def _safe(fn, default):
        try:
            return fn() if callable(fn) else fn
        except Exception:
            return default

    gpu_def = {"available": False}
    ram_def = {"total_gb": 0, "used_gb": 0, "available_gb": 0, "used_percent": 0}
    disk_def = {}

    gpu = _safe(check_gpu, gpu_def) if _MONITOR_OK else gpu_def
    ram = _safe(check_ram, ram_def) if _MONITOR_OK else ram_def
    disk = _safe(check_disk, disk_def) if _MONITOR_OK else disk_def
    services = _safe(check_services, {}) if _MONITOR_OK else {}

    # Agent status
    agent_data = collect_agent_status()
    agents_list = agent_data.get("agents", [])
    running = sum(1 for a in agents_list if a["running"])
    total = len(agents_list)

    # Environment
    env_data = collect_environment()

    # Ollama models
    ollama_models = collect_ollama_models()
    env_data["active_models"] = [m["name"] for m in ollama_models]

    # Mark the active model
    try:
        conf_path = SCRIPT_DIR / "telegram_config.json"
        if conf_path.exists():
            with open(conf_path) as f:
                cfg = json.load(f)
                active_model = cfg.get("ollama_model", "")
                for m in ollama_models:
                    m["active"] = m["name"] == active_model
    except Exception:
        pass

    # OpenHuman health details
    openhuman_health = check_openhuman_health()

    # 🆕 Obsidian memory status (extracted from agent data)
    obsidian_data = collect_obsidian_status()

    # 🆕 Claude Code status
    claude_data = collect_claude_status()

    # Alerts
    alerts = []
    healthy = True
    if _MONITOR_OK:
        try:
            alerts = detect_alerts({
                "gpu": gpu, "ram": ram, "disk": disk, "services": services,
            })
            healthy = len(alerts) == 0
        except Exception:
            alerts = ["Error verificando alertas"]
            healthy = False
    else:
        alerts = ["monitor_sistema.py no disponible"]

    # Add agent alerts
    if running < total:
        alerts.append(f"⚠️  {total - running} agente(s) offline")

    # ── Services with ports for enable/disable buttons ──
    SERVICE_CATALOG = [
        {"name": "Ollama",    "port": 11434, "icon": "🧠", "desc": "LLM Server local",           "health_key": "ollama"},
        {"name": "ComfyUI",   "port": 8188,  "icon": "🎨", "desc": "Generación de imágenes",    "health_key": "comfyui"},
        {"name": "Hermes",    "port": 9119,  "icon": "🧠", "desc": "Agente 3 escritorios",       "health_key": "hermes"},
        {"name": "OpenHuman", "port": 7788,  "icon": "🤖", "desc": "API core (sin web UI)",    "health_key": "openhuman"},
        {"name": "OpenHuman Desk","port": 0, "icon": "🖥️", "desc": "App nativa local-first",      "health_key": "openhuman_desktop"},
        {"name": "PostgreSQL","port": 5432,  "icon": "🗄️", "desc": "Base de datos",             "health_key": "postgresql"},
        {"name": "Vote API",  "port": 9099,  "icon": "🗳️", "desc": "API de votación de assets", "health_key": "vote"},
        {"name": "Telegram",  "port": 0,     "icon": "🤖", "desc": "Bot multi-agente (tmux)",   "health_key": "telegram_bot"},
        {"name": "Agatha",    "port": 0,     "icon": "📋", "desc": "Reportes horarios (tmux)",    "health_key": "agatha"},
        {"name": "DonHermes", "port": 0,     "icon": "🤖", "desc": "Bot de Agatha (@...ai_bot)", "health_key": "donhermes"},
        {"name": "Hermes Dash","port": 9120, "icon": "📊", "desc": "Web UI de Hermes Agent",    "health_key": "hermes_dashboard"},
        {"name": "Hermes Desk","port": 0,    "icon": "🖥️", "desc": "App nativa Hermes Desktop",  "health_key": "hermes_desktop"},
        {"name": "Claude Code", "port": 0,   "icon": "🤖", "desc": "Sub-agente de Buffy",         "health_key": "claude"},
        {"name": "Obsidian",   "port": 0,     "icon": "🪨", "desc": "Memoria persistente",           "health_key": "obsidian"},
    ]

    # Enrich with health status
    servicios = []
    for svc in SERVICE_CATALOG:
        if svc["health_key"] == "telegram_bot":
            # Check from agent data
            for a in agents_list:
                if a["name"] == "Telegram Bot":
                    svc["healthy"] = a["running"]
                    break
            else:
                svc["healthy"] = False
            svc["url"] = "#"
        elif svc["health_key"] == "agatha":
            # Check from agent data
            for a in agents_list:
                if a["name"] == "Agatha Actas":
                    svc["healthy"] = a["running"]
                    break
            else:
                svc["healthy"] = False
            svc["url"] = "#"
        elif svc["health_key"] == "donhermes":
            # Check from agent data
            for a in agents_list:
                if a["name"] == "DonHermes Bot":
                    svc["healthy"] = a["running"]
                    break
            else:
                svc["healthy"] = False
            svc["url"] = "#"
        elif svc["health_key"] == "hermes":
            # Direct HTTP check (not in check_services())
            svc["healthy"] = _http_healthy(f"http://localhost:{svc['port']}", timeout=2)
            svc["url"] = f"http://localhost:{svc['port']}"
        elif svc["health_key"] == "hermes_dashboard":
            # Web UI de Hermes en :9120
            svc["healthy"] = _http_healthy(f"http://localhost:{svc['port']}", timeout=2)
            svc["url"] = f"http://localhost:{svc['port']}"
        elif svc["health_key"] == "hermes_desktop":
            # Native app - no se puede verificar desde aquí
            svc["healthy"] = False
            svc["url"] = "#"
        elif svc["health_key"] == "openhuman":
            # Solo API core — no tiene web UI, el botón no debe abrir :7788
            svc["healthy"] = _http_healthy("http://localhost:7788", timeout=2)
            svc["url"] = "#"
        elif svc["health_key"] == "openhuman_desktop":
            # Native app - no verificable
            svc["healthy"] = False
            svc["url"] = "#"
        elif svc["health_key"] == "claude":
            # Claude Code - check from agent data
            svc["healthy"] = claude_data.get("available", False)
            svc["url"] = "#"
        elif svc["health_key"] == "obsidian":
            # Obsidian Memory - check from collected data
            svc["healthy"] = obsidian_data.get("available", False)
            svc["url"] = "#"
        elif svc["health_key"] == "vote":
            svc["healthy"] = _http_healthy(f"http://localhost:{svc['port']}/api/stats", timeout=2)
            svc["url"] = f"http://localhost:{svc['port']}"
        else:
            svc_data = services.get(svc["health_key"], {})
            svc["healthy"] = svc_data.get("healthy", False)
            svc["url"] = f"http://localhost:{svc['port']}"
        servicios.append(svc)

    return render_template_string(
        DASHBOARD_HTML,
        gpu=gpu, ram=ram, disk=disk, services=services,
        alerts=alerts, healthy=healthy,
        timestamp=datetime.now().strftime("%H:%M:%S"),
        agent_stats={"running": running, "total": total, "list": agents_list},
        env=env_data,
        ollama_models=ollama_models,
        servicios=servicios,
        openhuman=openhuman_health,
        obsidian=obsidian_data,
        claude=claude_data,
    )


@app.route("/api/health")
def api_health():
    """JSON health endpoint (backward-compatible)."""
    if not _MONITOR_OK:
        return jsonify({"error": "monitor_sistema.py not available"}), 500

    def _safe(fn, default):
        try:
            return fn()
        except Exception:
            return default

    gpu = _safe(check_gpu, {"available": False})
    ram = _safe(check_ram, {"total_gb": 0})
    disk = _safe(check_disk, {})
    services = _safe(check_services, {})

    try:
        alerts = detect_alerts({"gpu": gpu, "ram": ram, "disk": disk, "services": services})
    except Exception:
        alerts = ["Error checking alerts"]

    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "healthy": len(alerts) == 0,
        "gpu": gpu, "ram": ram, "disk": disk,
        "services": services, "alerts": alerts,
    })


@app.route("/api/agents")
def api_agents():
    """JSON endpoint with agent status."""
    agent_data = collect_agent_status()
    return jsonify(agent_data)


@app.route("/api/environment")
def api_environment():
    """JSON endpoint with environment situation."""
    env_data = collect_environment()
    env_data["ollama_models"] = collect_ollama_models()
    return jsonify(env_data)


@app.route("/api/logs")
def api_logs():
    """JSON endpoint returning recent log entries."""
    entries = get_logs(40) if _LOG_OK else []
    return jsonify({
        "entries": entries,
        "total": len(entries),
    })


@app.route("/api/obsidian")
def api_obsidian():
    """JSON endpoint with Obsidian vault status."""
    return jsonify(collect_obsidian_status())


@app.route("/api/claude")
def api_claude():
    """JSON endpoint with Claude Code status."""
    return jsonify(collect_claude_status())


@app.route("/api/dashboard")
def api_dashboard():
    """JSON endpoint with all dashboard data (for JS refresh)."""
    def _safe(fn, default):
        try:
            return fn()
        except Exception:
            return default

    gpu = _safe(check_gpu, {"available": False}) if _MONITOR_OK else {"available": False}
    ram = _safe(check_ram, {}) if _MONITOR_OK else {}
    disk = _safe(check_disk, {}) if _MONITOR_OK else {}
    services = _safe(check_services, {}) if _MONITOR_OK else {}
    agent_data = collect_agent_status()
    env_data = collect_environment()
    ollama_models = collect_ollama_models()
    openhuman_health = check_openhuman_health()
    obsidian_data = collect_obsidian_status()
    claude_data = collect_claude_status()

    try:
        alerts = detect_alerts({"gpu": gpu, "ram": ram, "disk": disk, "services": services}) if _MONITOR_OK else []
    except Exception:
        alerts = ["Error checking alerts"]

    running = sum(1 for a in agent_data.get("agents", []) if a["running"])
    total = len(agent_data.get("agents", []))

    return jsonify({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "healthy": len(alerts) == 0,
        "gpu": gpu, "ram": ram, "disk": disk, "services": services,
        "alerts": alerts,
        "agent_stats": {"running": running, "total": total, "list": agent_data.get("agents", [])},
        "environment": env_data,
        "ollama_models": ollama_models,
        "openhuman": openhuman_health,
        "obsidian": obsidian_data,
        "claude": claude_data,
    })


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SIMMOON — Dashboard de Control Agéntico")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Puerto (default: 5000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host (default: 127.0.0.1)")
    args = parser.parse_args()

    if not _MONITOR_OK:
        print("[WARN] monitor_sistema.py no encontrado — datos limitados")

    # Log startup event
    if _LOG_OK:
        syslog("Dashboard", "📊", f"Dashboard iniciado en http://{args.host}:{args.port}")

    print(f"\n  🚀 SIMMOON Dashboard de Control Agéntico")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Endpoints:")
    print(f"    /              — Dashboard web interactivo")
    print(f"    /api/health    — Salud del sistema (JSON)")
    print(f"    /api/agents    — Estado de agentes IA (JSON)")
    print(f"    /api/environment — Situación del entorno (JSON)")
    print(f"    /api/dashboard — Datos completos (JSON)")
    print(f"    /api/logs      — Últimos eventos (JSON)")
    print(f"    /api/obsidian  — Estado vault Obsidian (JSON)")
    print(f"    /api/claude    — Estado Claude Code (JSON)")
    print(f"  Press Ctrl+C to stop\n")

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
