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

from flask import Flask, jsonify, render_template, send_file

# ── Dashboard Collectors ─────────────────────────────────────────────────
from dashboard_collectors import (
    collect_agent_status, collect_environment,
    check_openhuman_health, collect_ollama_models,
    collect_obsidian_status, collect_claude_status,
    _http_healthy,
    _MONITOR_OK, check_gpu, check_ram, check_disk,
    check_services, check_cpu_temp, detect_alerts,
)        # ── Shared services (dynamic service catalog) ────────────────────────────
try:
    from shared_services_agents import ENTITIES as _ENTITIES, resolve_app_path as _resolve_app_path
    _HAS_ENTITIES = True
except ImportError:
    _HAS_ENTITIES = False
    _ENTITIES = []
    _resolve_app_path = None

# ── System Logger ────────────────────────────────────────────────────────
try:
    from system_logger import log as syslog, get_recent as get_logs, log_exception
    _LOG_OK = True
except ImportError:
    _LOG_OK = False


# ── Helper: Dynamic Service Catalog from shared_services_agents ──────────
def _build_service_catalog(agents_list, claude_data, obsidian_data, services):
    """Build service catalog dynamically from shared_services_agents.ENTITIES.

    Falls back to a minimal hardcoded catalog if ENTITIES is unavailable.
    """
    result = []

    if _HAS_ENTITIES:
        # Build from ENTITIES — entities with kind "service" or "dashboard"
        seen = set()
        for e in _ENTITIES:
            kinds = e.get("kinds", [])
            key = e["key"]
            if key in seen:
                continue
            # Skip deprecated
            if e.get("deprecated"):
                continue
            # Only include if it has service or dashboard kind
            if "service" not in kinds and "dashboard" not in kinds:
                continue
            seen.add(key)

            port = e.get("port", 0)
            icon = e.get("emoji", "📌")
            name = e["name"]
            role = e.get("role", "")
            check_type = e.get("check_type", "")

            # ── Determine health ──
            healthy = False
            url = "#"
            if check_type == "http":
                target = e.get("check_target", f"http://localhost:{port}")
                timeout = e.get("check_timeout", 2)
                healthy = _http_healthy(target, timeout=timeout)
                if healthy and port:
                    url = f"http://localhost:{port}"
            elif check_type == "db_conn":
                svc_data = services.get(key, {})
                healthy = svc_data.get("healthy", False)
            elif check_type == "windows_process":
                # Check from agent data (name match)
                for a in agents_list:
                    if a["name"] == name:
                        healthy = a["running"]
                        break
            elif check_type == "always_on":
                healthy = True
            elif check_type == "claude_collector":
                healthy = claude_data.get("available", False)
            elif check_type == "obsidian_collector":
                healthy = obsidian_data.get("available", False)
            elif check_type == "script_exists":
                target = e.get("check_target", "")
                healthy = bool(target) and (SCRIPT_DIR / target).exists()
            elif check_type == "app_discover":
                healthy = bool(_resolve_app_path(key) if _resolve_app_path else False)
            else:
                # For unknown types, check services dict
                svc_data = services.get(key, {})
                healthy = svc_data.get("healthy", False)

            result.append({
                "name": name,
                "port": port,
                "icon": icon,
                "desc": role[:80] if role else name,
                "health_key": key,
                "healthy": healthy,
                "url": url,
            })
    else:
        # Minimal fallback catalog
        fallback = [
            {"name": "Ollama",    "port": 11434, "icon": "🧠", "desc": "LLM Server local",           "health_key": "ollama"},
            {"name": "PostgreSQL","port": 5432,  "icon": "🗄️", "desc": "Base de datos",             "health_key": "postgresql"},
            {"name": "Dashboard", "port": 5000,  "icon": "📊", "desc": "Monitor web del sistema",    "health_key": "dashboard_web"},
            {"name": "Telegram",  "port": 0,     "icon": "🤖", "desc": "Bot multi-agente (tmux)",   "health_key": "telegram_bot"},
            {"name": "Agatha",    "port": 0,     "icon": "📋", "desc": "Reportes horarios (tmux)",    "health_key": "agatha_actas"},
            {"name": "Obsidian",  "port": 0,     "icon": "🪨", "desc": "Memoria persistente",           "health_key": "obsidian_memory"},
        ]
        for svc in fallback:
            svc_data = services.get(svc["health_key"], {})
            if svc["health_key"] == "telegram_bot":
                svc["healthy"] = any(a["name"] == "Telegram Bot" and a["running"] for a in agents_list)
            elif svc["health_key"] == "agatha_actas":
                svc["healthy"] = any(a["name"] == "Agatha Actas" and a["running"] for a in agents_list)
            elif svc["health_key"] == "obsidian_memory":
                svc["healthy"] = obsidian_data.get("available", False)
            else:
                svc["healthy"] = svc_data.get("healthy", False)
            svc["url"] = f"http://localhost:{svc['port']}" if svc.get("port") else "#"
            result.append(svc)

    return result


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

    # ── Services with ports for enable/disable buttons (DYNAMIC from ENTITIES) ──
    servicios = _build_service_catalog(agents_list, claude_data, obsidian_data, services)

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


# ── Dispatcher Config (soft import) ────────────────────────────────────
def collect_dispatcher_config() -> dict:
    """Obtener valores activos del dispatcher_config.json."""
    try:
        import factory.task_dispatcher as td
        return {
            "available": True,
            "llm_timeout": td.DEFAULT_LLM_TIMEOUT,
            "coding_timeout": td.DEFAULT_CODING_TIMEOUT,
            "image_timeout": td.DEFAULT_IMAGE_TIMEOUT,
            "pipeline_timeout": td.DEFAULT_PIPELINE_TIMEOUT,
            "multi_timeout": td.DEFAULT_MULTI_TIMEOUT,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.route("/api/config")
def api_config():
    return jsonify(collect_dispatcher_config())


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


@app.route("/api/factory")
def api_factory():
    """JSON endpoint with Factory production line status from agatha_actas.

    Returns workstations grouped by department (management, design,
    production, engine, agent, communication, storage, monitoring),
    services health, system metrics, and alerts.
    """
    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workstations": [],
        "by_department": {},
        "services": [],
        "system": {},
        "alerts": [],
        "available": False,
    }

    try:
        from agatha_actas import collect_activity, _check_workstation
        from shared_services_agents import WORKSTATIONS, ENTITIES

        # ── Workstations grouped by department ──
        dept_order = [
            ("management", "🏢 GESTIÓN"),
            ("design", "✏️ DISEÑO"),
            ("production", "⚙️ PRODUCCIÓN"),
            ("engine", "🔧 MOTORES"),
            ("agent", "🤖 AGENTES IA"),
            ("communication", "📡 COMUNICACIÓN"),
            ("storage", "💾 DATOS"),
            ("monitoring", "📊 MONITOREO"),
        ]

        workstations = []
        by_department = {}
        for ws in WORKSTATIONS:
            if ws.get("deprecated"):
                continue
            checked = _check_workstation(ws)
            entry = {
                "key": checked["key"],
                "name": checked["name"],
                "emoji": checked["emoji"],
                "type": checked["type"],
                "running": checked["running"],
                "status_emoji": checked.get("status_emoji", "🟢" if checked["running"] else "🔴"),
                "role": checked.get("role", ""),
            }
            workstations.append(entry)
            dtype = checked["type"]
            if dtype not in by_department:
                by_department[dtype] = []
            by_department[dtype].append(entry)

        result["workstations"] = workstations
        result["by_department"] = {
            dtype: {"label": dlabel, "members": by_department.get(dtype, [])}
            for dtype, dlabel in dept_order
            if dtype in by_department
        }

        # ── Services from ENTITIES ──
        svc_entities = [e for e in ENTITIES if "service" in e.get("kinds", [])
                        and not e.get("deprecated")]
        for svc in svc_entities:
            check_type = svc.get("check_type", "")
            target = svc.get("check_target")
            port = svc.get("port", 0)
            healthy = False
            if check_type == "http" and target:
                healthy = _http_healthy(target, timeout=svc.get("check_timeout", 3))
            elif check_type == "db_conn":
                if _MONITOR_OK:
                    svc_services = check_services()
                    svc_data = svc_services.get(svc["key"], {})
                    healthy = svc_data.get("healthy", False)
            elif check_type == "always_on":
                healthy = True

            result["services"].append({
                "key": svc["key"],
                "name": svc["name"],
                "emoji": svc.get("emoji", "📡"),
                "port": port,
                "healthy": healthy,
                "role": svc.get("role", ""),
            })

        # ── System metrics ──
        if _MONITOR_OK:
            result["system"] = {
                "gpu": check_gpu() if check_gpu else {"available": False},
                "ram": check_ram() if check_ram else {},
                "disk": check_disk() if check_disk else {},
            }

        # ── Alerts ──
        active_ws = sum(1 for w in workstations if w["running"])
        ws_total = len(workstations)
        active_svc = sum(1 for s in result["services"] if s["healthy"])
        svc_total = len(result["services"])

        if active_ws < ws_total:
            result["alerts"].append(f"🔴 {ws_total - active_ws} workstation(s) inactivas")
        if active_svc < svc_total:
            result["alerts"].append(f"❌ {svc_total - active_svc} servicio(s) caídos")

        result["available"] = True
        result["stats"] = {
            "workstations_active": active_ws,
            "workstations_total": ws_total,
            "services_healthy": active_svc,
            "services_total": svc_total,
        }

    except ImportError as e:
        result["error"] = f"agatha_actas or shared_services_agents not available: {e}"
    except Exception as e:
        result["error"] = str(e)

    return jsonify(result)


@app.route("/blender")
def serve_blender_viewer():
    """Serve the 3D Blender assets viewer."""
    viewer_path = SCRIPT_DIR / "blender_viewer.html"
    if viewer_path.exists():
        return viewer_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html; charset=utf-8"}
    return "<h2>blender_viewer.html not found</h2>", 404


@app.route("/render/<filename>")
def serve_render(filename: str):
    """Serve a raw Blender render PNG from blender_renders/."""
    safe_name = Path(filename).name  # Prevent path traversal
    filepath = SCRIPT_DIR / "blender_renders" / safe_name
    if filepath.exists():
        return send_file(str(filepath), mimetype="image/png")
    return "<h2>Render not found</h2>", 404


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
        "dispatcher_config": collect_dispatcher_config(),
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
