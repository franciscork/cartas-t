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

from flask import Flask, jsonify, render_template

# ── Dashboard Collectors ─────────────────────────────────────────────────
from dashboard_collectors import (
    collect_agent_status, collect_environment,
    check_openhuman_health, collect_ollama_models,
    collect_obsidian_status, collect_claude_status,
    _http_healthy,
    _MONITOR_OK, check_gpu, check_ram, check_disk,
    check_services, check_cpu_temp, detect_alerts,
)

# ── System Logger ────────────────────────────────────────────────────────
try:
    from system_logger import log as syslog, get_recent as get_logs, log_exception
    _LOG_OK = True
except ImportError:
    _LOG_OK = False


# ── Flask App ────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder=str(SCRIPT_DIR / "templates"))




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

    try:
        return render_template('dashboard.html',
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


    except Exception as e:
        log_exception("Dashboard", "📊", e, context="index() render")
        raise


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


@app.route("/viewer.html")
def serve_viewer():
    """Serve the asset gallery viewer."""
    viewer_path = SCRIPT_DIR / "viewer.html"
    if viewer_path.exists():
        return viewer_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html; charset=utf-8"}
    return jsonify({"error": "viewer.html not found"}), 404


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
    parser.add_argument("--debug", action="store_true", default=False, help="Activar debug mode (hot-reload)")
    args = parser.parse_args()

    if not _MONITOR_OK:
        print("[WARN] monitor_sistema.py no encontrado — datos limitados")

    # Log startup event
    debug_status = "ACTIVADO" if args.debug else "desactivado"
    if _LOG_OK:
        syslog("Dashboard", "📊", f"Dashboard iniciado en http://{args.host}:{args.port} | debug={debug_status}")

    print(f"\n  🚀 SIMMOON Dashboard de Control Agéntico")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Debug mode: {debug_status}")
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

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
