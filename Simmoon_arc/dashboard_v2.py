#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMMOON — Dashboard Web de Control Agéntico + Orquestación FactoryGames 🏭

Este dashboard extiende el original (dashboard.py) con integración
del FactoryOrchestrator para mostrar el estado de los agentes en tiempo real.

Uso:
    python dashboard_v2.py                # http://localhost:5001
    python dashboard_v2.py --port 8080    # Puerto personalizado
"""

import argparse, json, sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from flask import Flask, jsonify, render_template_string, request

# --- Monitor imports ---
try:
    from monitor_sistema import check_gpu, check_ram, check_disk, check_cpu_temp, check_services, detect_alerts, _wsl_cmd
    _MONITOR_OK = True
except ImportError:
    _MONITOR_OK = False

# --- System Logger ---
try:
    from system_logger import log as syslog, get_recent as get_logs
    _LOG_OK = True
except ImportError:
    _LOG_OK = False

# --- Pipeline async execution state ---
_PIPELINE_RUNNING = False
_PIPELINE_THREAD = None

AVAILABLE_CATEGORIES = [
    "businesses", "vehicles", "greenhouses", "solar_energy",
    "lunar_map", "buildings_misc", "lunar_sites", "ui_elements",
    "roads", "decorations", "characters", "lunar_flora", "infrastructure",
]

# --- Factory Orchestrator (soft import) ---
_FACTORY = None
def _get_factory():
    global _FACTORY
    if _FACTORY is None:
        try:
            from factory.orchestrator import FactoryOrchestrator
            _FACTORY = FactoryOrchestrator(verbose=False)
            _FACTORY.monitor.check_all()
        except Exception:
            _FACTORY = None
    return _FACTORY

def collect_factory_status() -> dict:
    factory = _get_factory()
    if not factory:
        return {"available": False, "agents": [], "healthy": 0, "total": 0}
    try:
        agent_health = factory.registry.health()
        agents = [{"name": a.name, "type": a.agent_type, "healthy": agent_health.get(a.name, False),
                    "endpoint": a.endpoint, "capabilities": a.capabilities} for a in factory.registry.all()]
        return {"available": True, "agents": agents, "healthy": sum(1 for a in agents if a["healthy"]),
                "total": len(agents), "uptime": factory.started_at.isoformat()}
    except Exception as e:
        return {"available": False, "error": str(e)}

def collect_pipeline_status() -> dict:
    """Obtener estado de la ultima ejecucion del pipeline desde el orquestador."""
    factory = _get_factory()
    if not factory:
        return {"available": False, "executed": False}
    try:
        history = factory.dispatcher.get_history(20)
        pipeline_runs = [h for h in history if h.get("task_type") == "pipeline"]
        if not pipeline_runs:
            return {"available": True, "executed": False}
        last = pipeline_runs[-1]
        # Parsear el output del pipeline
        output_text = last.get("output", "")
        lines = output_text.split("\n")
        cats_line = ""
        gen_line = ""
        pix_line = ""
        db_line = ""
        for line in lines:
            line_stripped = line.strip()
            if "Categorias:" in line_stripped:
                cats_line = line_stripped
            elif "Generacion:" in line_stripped:
                gen_line = line_stripped
            elif "Pixel art:" in line_stripped:
                pix_line = line_stripped
            elif "DB insert:" in line_stripped:
                db_line = line_stripped
        return {
            "available": True,
            "executed": True,
            "success": last.get("success", False),
            "agent": last.get("agent", ""),
            "duration_min": round(last.get("duration", 0) / 60, 1),
            "error": last.get("error", ""),
            "output_summary": {
                "categories": cats_line,
                "generation": gen_line,
                "pixel_art": pix_line,
                "db_insert": db_line,
            },
        }
    except Exception as e:
        return {"available": True, "executed": False, "error": str(e)}

_OBSIDIAN_HISTORY = None
def _get_obsidian_history():
    """Singleton de ObsidianMemory para el historial de pipelines."""
    global _OBSIDIAN_HISTORY
    if _OBSIDIAN_HISTORY is None:
        try:
            from obsidian_memory import ObsidianMemory
            _OBSIDIAN_HISTORY = ObsidianMemory(
                vault_path=str(SCRIPT_DIR / "factory_memoria"),
                agent_name="factory", project="FACTORY_GAMES")
        except Exception:
            _OBSIDIAN_HISTORY = None
    return _OBSIDIAN_HISTORY

# ── Dispatcher Config (soft import) ────────────────────────────────────
_DISPATCHER_CONFIG_CACHE = None
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


def collect_pipeline_history() -> list:
    """Obtener historial de ejecuciones de pipeline desde ObsidianMemory."""
    obs = _get_obsidian_history()
    if not obs:
        return []
    try:
        records = obs.search_by_tag("pipeline", limit=50)
        history = []
        for r in records:
            content = r.get("content", "")
            # Parsear [PIPELINE] Categorias: ... | Duracion: ... | ...
            cats = ""
            duration = ""
            gen = ""
            pix = ""
            db = ""
            result = ""
            for part in content.split("|"):
                p = part.strip()
                # La primera parte puede tener prefijo [PIPELINE]
                if "Categorias:" in p:
                    cats = p.split("Categorias:", 1)[-1].strip()
                if p.startswith("Duracion:"):
                    duration = p.split(":", 1)[-1].strip()
                elif p.startswith("Generacion:"):
                    gen = p.split(":", 1)[-1].strip()
                elif p.startswith("Pixel art:"):
                    pix = p.split(":", 1)[-1].strip()
                elif p.startswith("DB:"):
                    db = p.split(":", 1)[-1].strip()
                elif p.startswith("Resultado:"):
                    result = p.split(":", 1)[-1].strip()
            history.append({
                "key": r.get("key_name", ""),
                "timestamp": r.get("created_at", "") or r.get("updated_at", ""),
                "categories": cats,
                "duration": duration,
                "gen": gen,
                "pix": pix,
                "db": db,
                "result": result,
                "success": "EXITO" in result,
            })
        # Ordenar por timestamp descendente
        history.sort(key=lambda h: h["timestamp"], reverse=True)
        return history
    except Exception as e:
        return []

# --- Helper functions (from original dashboard) ---
def _try_import(mn):
    try: __import__(mn); return True
    except: return False

def _tmux_session_exists(name):
    try:
        r = _wsl_cmd(f"tmux has-session -t {name} 2>/dev/null && echo YES || echo NO", timeout=5)
        return "YES" in r.stdout
    except: return False

def _http_healthy(url, timeout=3):
    try:
        import urllib.request
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status < 500
    except: return False

def _wsl_has_binary(name):
    try:
        r = _wsl_cmd(f"command -v {name} 2>/dev/null && echo FOUND || echo NOT_FOUND", timeout=5)
        return "FOUND" in r.stdout
    except: return False

def _file_exists_in_wsl(path):
    try:
        r = _wsl_cmd(f"test -f {path} && echo YES || echo NO", timeout=5)
        return "YES" in r.stdout
    except: return False

def collect_agent_status():
    now = datetime.now().strftime("%H:%M:%S")
    ollama_healthy = _http_healthy("http://localhost:11434/api/tags", timeout=2)
    ollama_models = []
    if ollama_healthy:
        try:
            r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
            ollama_models = [m["name"] for m in json.loads(r.read().decode()).get("models", [])]
        except: pass

    agents = [
        {"name":"Telegram Bot","icon":"🤖","running":_tmux_session_exists("telegram-bot"),"method":"tmux","desc":"Bot @Jeremi_Hermes_bot"},
        {"name":"Hermes Agent","icon":"🧠","running":_http_healthy("http://localhost:9119",2),"method":":9119","desc":"Agente multi-escritorio","binary":_wsl_has_binary("hermes")},
        {"name":"Hermes Bridge","icon":"🔗","running":_try_import("hermes_bridge") and _file_exists_in_wsl("~/.local/bin/hermes"),"method":"Python","desc":"Puente Simmoon-Hermes"},
        {"name":"OpenHuman","icon":"🤖","running":_http_healthy("http://localhost:7788",2),"method":":7788","desc":"API core"},
        {"name":"Simmoon Agent","icon":"🎯","running":(SCRIPT_DIR/"simmoon_agent.py").exists(),"method":"Python","desc":"AI Director"},
        {"name":"AutoGen","icon":"👥","running":(SCRIPT_DIR/"simmoon_autogen.py").exists(),"method":"Python","desc":"Diseno multi-agente"},
        {"name":"Pipeline","icon":"🔄","running":(SCRIPT_DIR/"simmoon_pipeline.py").exists(),"method":"Python","desc":"LangGraph workflow"},
        {"name":"Simmoon Game","icon":"🎮","running":(SCRIPT_DIR/"juego_simmoon.py").exists(),"method":"Python","desc":"Juego colonia lunar"},
        {"name":"Agatha Actas","icon":"📋","running":_tmux_session_exists("agatha-actas"),"method":"tmux","desc":"Reportes horarios"},
        {"name":"DonHermes Bot","icon":"🤖","running":_tmux_session_exists("agatha-actas"),"method":"Telegram","desc":"Bot @...ai_bot"},
        {"name":"Hermes Dash","icon":"📊","running":_http_healthy("http://localhost:9120",2),"method":":9120","desc":"Web UI Hermes"},
    ]

    services_raw = {}
    if _MONITOR_OK:
        try: services_raw = check_services()
        except: pass

    return {"timestamp":now,"agents":agents,"services":services_raw,
            "total_running":sum(1 for a in agents if a["running"]),"total_agents":len(agents),
            "ollama_healthy":ollama_healthy,"ollama_models":ollama_models}

def collect_environment():
    now = datetime.now()
    uptime_str = "N/A"
    try:
        r = _wsl_cmd("uptime -p 2>/dev/null || uptime 2>/dev/null", timeout=5)
        uptime_str = r.stdout.strip() or "N/A"
    except: pass

    cpu_temp = None
    try: cpu_temp = check_cpu_temp()
    except: pass

    asset_cats = ["businesses","vehicles","greenhouses","solar_energy","lunar_map","buildings_misc",
                   "lunar_sites","ui_elements","roads","decorations","characters","lunar_flora","infrastructure"]
    asset_count = 0
    categories_found = {}
    for cat in asset_cats:
        d = SCRIPT_DIR / cat
        if d.is_dir():
            pngs = list(d.glob("*.png"))
            if pngs: categories_found[cat]=len(pngs); asset_count+=len(pngs)
    gen_logs = list(SCRIPT_DIR.glob("generation_log*.txt"))
    last_gen = None
    if gen_logs:
        newest = max(gen_logs, key=lambda p: p.stat().st_mtime)
        last_gen = datetime.fromtimestamp(newest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return {"timestamp":now.strftime("%Y-%m-%d %H:%M:%S"),"uptime":uptime_str,"cpu_temp_c":cpu_temp,
            "asset_count":asset_count,"categories_found":categories_found,
            "total_categories":len(categories_found),"last_generation":last_gen,"active_models":[]}

def check_openhuman_health():
    try:
        r = urllib.request.urlopen("http://localhost:7788/health", timeout=5)
        d = json.loads(r.read().decode())
        return {"available":True,"ok":d.get("ok",False),"api_server":d.get("api_server",""),
                "endpoints":list(d.get("endpoints",{}).keys())}
    except: return {"available":False}

def collect_ollama_models():
    try:
        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        models = []
        for m in json.loads(r.read().decode()).get("models",[]):
            size_gb = m.get("size",0)/(1024**3)
            models.append({"name":m["name"],"size_gb":round(size_gb,1),"family":m.get("details",{}).get("family",""),"param_size":m.get("details",{}).get("parameter_size","")})
        return models
    except: return []

app = Flask(__name__)

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIMMOON — Dashboard + Orquestacion FactoryGames</title>
    <style>
        :root {
            --bg: #08080c; --card: #101018; --card2: #14141e; --border: #1c1c2e;
            --text: #d0d0dc; --text-dim: #6a6a80; --text-bright: #f0f0ff;
            --accent: #6c5ce7; --accent2: #00cec9; --green: #00b894;
            --green-bg: rgba(0,184,148,0.1); --yellow: #fdcb6e; --yellow-bg: rgba(253,203,110,0.1);
            --red: #ff7675; --red-bg: rgba(255,118,117,0.1); --blue: #74b9ff; --radius: 8px;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Segoe UI',system-ui,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; padding:12px; font-size:13px; }
        .header { display:flex; justify-content:space-between; align-items:center; padding:8px 4px 10px; border-bottom:1px solid var(--border); margin-bottom:10px; flex-wrap:wrap; gap:6px; }
        .header h1 { font-size:1.15rem; font-weight:700; display:flex; align-items:center; gap:8px; }
        .header h1 .dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
        .header h1 .dot.green { background:var(--green); box-shadow:0 0 6px var(--green); }
        .header h1 .dot.red { background:var(--red); box-shadow:0 0 6px var(--red); }
        .header .meta { display:flex; align-items:center; gap:14px; font-size:0.75rem; color:var(--text-dim); }
        .header .meta .live-dot { width:6px; height:6px; border-radius:50%; background:var(--green); display:inline-block; animation:pulse 1.5s infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .grid { display:grid; gap:8px; margin-bottom:8px; }
        .grid-4 { grid-template-columns:repeat(4,1fr); }
        .grid-3 { grid-template-columns:repeat(3,1fr); }
        .grid-2 { grid-template-columns:repeat(2,1fr); }
        .grid-full { grid-column:1/-1; }
        .card { background:var(--card); border:1px solid var(--border); border-radius:var(--radius); padding:10px 12px; transition:border-color 0.15s; }
        .card:hover { border-color:var(--accent); }
        .card h2 { font-size:0.7rem; text-transform:uppercase; letter-spacing:0.8px; color:var(--text-dim); margin-bottom:8px; display:flex; align-items:center; gap:5px; }
        .card h2 .icon { font-size:0.9rem; }
        .metric { display:flex; justify-content:space-between; align-items:center; padding:3px 0; font-size:0.8rem; }
        .metric .label { color:var(--text-dim); }
        .metric .value { font-weight:500; }
        .metric .value.green { color:var(--green); }
        .metric .value.yellow { color:var(--yellow); }
        .metric .value.red { color:var(--red); }
        .metric .value.blue { color:var(--blue); }
        .progress-bar { width:100%; height:4px; background:var(--border); border-radius:2px; margin:3px 0; overflow:hidden; }
        .progress-fill { height:100%; border-radius:2px; transition:width 0.5s ease; }
        .progress-fill.green { background:var(--green); }
        .progress-fill.yellow { background:var(--yellow); }
        .progress-fill.red { background:var(--red); }
        .agent-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:1px; }
        .agent-row { display:flex; align-items:center; gap:6px; padding:4px 4px; font-size:0.78rem; border-radius:4px; }
        .agent-row:hover { background:rgba(108,92,231,0.06); }
        .agent-row .a-icon { font-size:0.9rem; width:18px; text-align:center; flex-shrink:0; }
        .agent-row .a-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
        .agent-row .a-dot.on { background:var(--green); box-shadow:0 0 4px var(--green); }
        .agent-row .a-dot.off { background:var(--red); opacity:0.4; }
        .agent-row .a-name { flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .agent-row .a-status { font-size:0.6rem; padding:1px 7px; border-radius:4px; font-weight:700; flex-shrink:0; }
        .agent-row .a-status.on { background:var(--green-bg); color:var(--green); }
        .agent-row .a-status.off { background:var(--red-bg); color:var(--red); }
        .ctrl-btn { display:inline-flex; align-items:center; gap:4px; padding:4px 8px; border:1px solid var(--border); border-radius:5px; background:var(--card2); color:var(--text); font-size:0.72rem; cursor:pointer; text-decoration:none; transition:all 0.15s; font-family:inherit; }
        .ctrl-btn:hover { border-color:var(--accent); background:rgba(108,92,231,0.1); color:var(--text-bright); }
        .ctrl-btn.primary { background:var(--accent); border-color:var(--accent); color:white; }
        .alert-box { padding:6px 10px; border-radius:5px; font-size:0.75rem; margin:4px 0; display:flex; align-items:center; gap:6px; }
        .alert-box.warn { background:var(--yellow-bg); border:1px solid rgba(253,203,110,0.2); color:var(--yellow); }
        .alert-box.err { background:var(--red-bg); border:1px solid rgba(255,118,117,0.2); color:var(--red); }
        .alert-box.ok { background:var(--green-bg); border:1px solid rgba(0,184,148,0.2); color:var(--green); }
        .log-entry { display:flex; align-items:baseline; gap:6px; padding:1px 4px; border-radius:3px; font-size:0.72rem; font-family:'Consolas',monospace; }
        .log-entry:hover { background:rgba(108,92,231,0.08); }
        .log-entry .log-ts { color:var(--text-dim); font-size:0.62rem; flex-shrink:0; width:7.5em; }
        .footer { text-align:center; font-size:0.65rem; color:var(--text-dim); padding:12px; border-top:1px solid var(--border); margin-top:8px; }
        @media (max-width:900px) { .grid-4,.grid-3,.grid-2 { grid-template-columns:repeat(2,1fr); } }
        @media (max-width:500px) { .grid-4,.grid-3,.grid-2 { grid-template-columns:1fr; } }
    </style>
</head>
<body>
<div class="header">
    <h1><span class="dot {{ 'green' if healthy else 'red' }}"></span> ☾ SIMMOON — Control + Orquestacion</h1>
    <div class="meta">
        <span><span class="live-dot"></span> Live</span>
        <span id="tsDisplay">{{ timestamp }}</span>
        <span>🏭 {{ factory_stats.healthy }}/{{ factory_stats.total }} orquestados</span>
    <span>🔧 {% if pipeline_stats.executed %}Pipeline: {{ pipeline_stats.duration_min }}m{% else %}Pipeline: --{% endif %}</span>
    </div>
</div>

<div class="grid grid-2">
    <div class="card grid-full">
        <h2><span class="icon">🏭</span> Orquestacion FactoryGames <span style="color:var(--text-dim);font-weight:400;font-size:0.65rem;">{{ factory_stats.healthy }}/{{ factory_stats.total }} agentes</span></h2>
        {% if factory_stats.available %}
        <div id="factoryAgents" class="agent-grid">
            {% for agent in factory_stats.agents %}
            <div class="agent-row" title="{{ agent.type }} - {{ agent.endpoint }}{% if agent.capabilities %} - {{ agent.capabilities|join(', ') }}{% endif %}">
                {% set icons = {'coding': '\U0001F916', 'image': '\U0001F5BC', 'llm': '\U0001F9E0', 'service': '\U0001F50C', 'supervisor': '\U0001F468\u200D\U0001F527'} %}
                <span class="a-icon">{{ icons.get(agent.type, '\u2022') }}</span>
                <span class="a-dot {{ 'on' if agent.healthy else 'off' }}"></span>
                <span class="a-name">{{ agent.name }}</span>
                <span class="a-status {{ 'on' if agent.healthy else 'off' }}">{{ 'ON' if agent.healthy else 'OFF' }}</span>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="alert-box warn">Orquestador no disponible - ejecuta: cd Simmoon_arc && python factory.py</div>
        {% endif %}
    </div>
</div>

<!-- ==== PIPELINE ==== -->
<div class="grid grid-2">
    <div class="card grid-full">
        <h2><span class="icon">\U0001F527</span> Pipeline de Assets <span id="pipelineMeta" style="color:var(--text-dim);font-weight:400;font-size:0.65rem;">{% if pipeline_stats.executed %}{{ pipeline_stats.duration_min }}m · {{ 'EXITO' if pipeline_stats.success else 'FALLO' }}{% else %}Sin ejecuciones{% endif %}</span></h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px;">
            <!-- Columna: Formulario para ejecutar -->
            <div style="border-right:1px solid var(--border);padding-right:12px;">
                <div style="font-size:0.72rem;font-weight:600;color:var(--text-dim);margin-bottom:8px;">🏭 EJECUTAR PIPELINE</div>
                <div style="display:flex;flex-direction:column;gap:6px;">
                    <input id="pipeCats" type="text" placeholder="Categorias: businesses vehicles ..."
                           style="background:var(--card2);border:1px solid var(--border);border-radius:5px;padding:5px 8px;color:var(--text);font-size:0.75rem;font-family:inherit;width:100%;">
                    <div style="display:flex;gap:6px;flex-wrap:wrap;">
                        <select id="pipeBackend" style="background:var(--card2);border:1px solid var(--border);border-radius:5px;padding:4px 6px;color:var(--text);font-size:0.7rem;flex:1;">
                            <option value="factory">factory (auto)</option>
                            <option value="diffusers">diffusers (WSL2)</option>
                            <option value="comfyui">comfyui (legacy)</option>
                        </select>
                        <input id="pipeSuffix" type="text" placeholder="suffix"
                               style="background:var(--card2);border:1px solid var(--border);border-radius:5px;padding:4px 6px;color:var(--text);font-size:0.7rem;width:80px;">
                    </div>
                    <div style="display:flex;gap:10px;font-size:0.7rem;flex-wrap:wrap;">
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input id="pipeSkipGen" type="checkbox" style="accent-color:var(--accent);"> Skip gen</label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input id="pipeSkipPix" type="checkbox" style="accent-color:var(--accent);"> Skip pixel</label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input id="pipeSkipDb" type="checkbox" style="accent-color:var(--accent);"> Skip DB</label>
                    </div>
                    <button id="pipeRunBtn" onclick="runPipeline()" class="ctrl-btn primary" style="align-self:flex-start;margin-top:2px;">\u25b6 Ejecutar Pipeline</button>
                    <div id="pipeRunStatus" style="font-size:0.7rem;color:var(--text-dim);min-height:1.2em;"></div>
                </div>
            </div>
            <!-- Columna: Resultados de la ultima ejecucion -->
            <div id="pipelineContainer">
                {% if pipeline_stats.executed %}
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
                    <div>
                        <div class="metric"><span class="label">Duracion</span><span class="value blue">{{ pipeline_stats.duration_min }} min</span></div>
                        <div class="metric"><span class="label">Resultado</span><span class="value {{ 'green' if pipeline_stats.success else 'red' }}">{{ 'EXITO' if pipeline_stats.success else 'FALLO' }}</span></div>
                        <div class="metric"><span class="label">Categorias</span><span class="value">{{ pipeline_stats.output_summary.categories }}</span></div>
                    </div>
                    <div>
                        <div class="metric"><span class="label">Generacion</span><span class="value">{{ pipeline_stats.output_summary.generation }}</span></div>
                        <div class="metric"><span class="label">Pixel Art</span><span class="value">{{ pipeline_stats.output_summary.pixel_art }}</span></div>
                        <div class="metric"><span class="label">DB Insert</span><span class="value">{{ pipeline_stats.output_summary.db_insert }}</span></div>
                    </div>
                    {% if pipeline_stats.error %}
                    <div class="alert-box err" style="grid-column:1/-1;">Error: {{ pipeline_stats.error[:200] }}</div>
                    {% endif %}
                </div>
                {% else %}
                <div class="alert-box warn" style="margin-top:0;">Aun no hay ejecuciones. Completa el formulario y presiona Ejecutar.</div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- ==== HISTORIAL DE PIPELINES ==== -->
<div class="grid grid-2">
    <div class="card grid-full">
        <h2><span class="icon">📋</span> Historial de Pipelines <span id="histCount" style="color:var(--text-dim);font-weight:400;font-size:0.65rem;"></span></h2>
        <div id="pipelineHistoryContainer" style="max-height:300px;overflow-y:auto;margin-top:4px;">
            <div style="color:var(--text-dim);font-size:0.72rem;">Cargando historial...</div>
        </div>
    </div>
</div>

<div class="grid grid-4">
    <div class="card">
        <h2><span class="icon">🎮</span> GPU</h2>
        {% if gpu.available %}
        <div class="metric"><span class="label">Modelo</span><span class="value">{{ gpu.name[:45] }}</span></div>
        <div class="metric"><span class="label">Temp</span><span class="value {{ 'green' if gpu.temperature_c < 70 else 'yellow' if gpu.temperature_c < 85 else 'red' }}">{{ gpu.temperature_c }}C</span></div>
        <div class="metric"><span class="label">VRAM</span><span class="value blue">{{ gpu.memory_used_mb }}/{{ gpu.memory_total_mb }}MB</span></div>
        <div class="progress-bar"><div class="progress-fill {{ 'green' if gpu.memory_used_percent < 70 else 'yellow' if gpu.memory_used_percent < 90 else 'red' }}" style="width:{{ gpu.memory_used_percent }}%"></div></div>
        {% else %}<div class="metric"><span class="label">Estado</span><span class="value red">No detectada</span></div>{% endif %}
    </div>
    <div class="card">
        <h2><span class="icon">🧠</span> RAM</h2>
        <div class="metric"><span class="label">Usada</span><span class="value {{ 'green' if ram.used_percent < 70 else 'yellow' if ram.used_percent < 90 else 'red' }}">{{ ram.used_gb }}/{{ ram.total_gb }}GB</span></div>
        <div class="progress-bar"><div class="progress-fill {{ 'green' if ram.used_percent < 70 else 'yellow' if ram.used_percent < 90 else 'red' }}" style="width:{{ ram.used_percent }}%"></div></div>
    </div>
    <div class="card">
        <h2><span class="icon">💾</span> Disco</h2>
        {% for mount, info in disk.items() %}
        <div class="metric"><span class="label">{{ mount.split('/')[-1] or mount }}</span><span class="value {{ 'green' if info.available_gb > 100 else 'yellow' if info.available_gb > 50 else 'red' }}">{{ info.available_gb }}GB libre</span></div>
        {% endfor %}
    </div>
    <div class="card">
        <h2><span class="icon">🔌</span> Backends</h2>
        {% for name, svc in services.items() %}
        <div class="metric"><span class="label">{{ svc.name if svc.name else name }}</span><span class="value" style="font-size:0.7rem;color:var(--text-dim);">{{ svc.latency_ms }}ms</span></div>
        {% endfor %}
    </div>
</div>

<div class="grid grid-2">
    <div class="card grid-full">
        <h2><span class="icon">🤖</span> Agentes IA <span style="color:var(--text-dim);font-weight:400;font-size:0.65rem;">{{ agent_stats.running }}/{{ agent_stats.total }} activos</span></h2>
        <div class="agent-grid">
            {% for agent in agent_stats.list %}
            <div class="agent-row" title="{{ agent.method }}{% if agent.desc %} - {{ agent.desc }}{% endif %}">
                <span class="a-icon">{{ agent.icon }}</span>
                <span class="a-dot {{ 'on' if agent.running else 'off' }}"></span>
                <span class="a-name">{{ agent.name }}</span>
                <span class="a-status {{ 'on' if agent.running else 'off' }}">{{ 'ON' if agent.running else 'OFF' }}</span>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<div class="grid grid-2">
    <div class="card grid-full">
        <h2><span class="icon">🚨</span> Alertas</h2>
        {% if alerts %}
            {% for alert in alerts %}
            <div class="alert-box {{ 'err' if '❌' in alert else 'warn' }}"><span>{{ '❌' if '❌' in alert else '⚠' }}</span>{{ alert.replace('❌ ','').replace('⚠ ','') }}</div>
            {% endfor %}
        {% else %}<div class="alert-box ok">Sin alertas</div>{% endif %}
    </div>
    <div class="card">
        <h2><span class="icon">⚙</span> Dispatcher Config</h2>
        <div id="configContainer" style="font-size:0.72rem;">
            <div style="color:var(--text-dim);">Cargando...</div>
        </div>
    </div>
    <div class="card">
        <h2><span class="icon">📜</span> Eventos <span id="logCount" style="color:var(--text-dim);font-weight:400;font-size:0.65rem;"></span></h2>
        <div id="logContainer" style="max-height:200px;overflow-y:auto;font-size:0.72rem;font-family:'Consolas',monospace;line-height:1.6;">
            <div style="color:var(--text-dim);">Cargando...</div>
        </div>
    </div>
</div>        <div class="footer">
    SIMMOON + FactoryGames | Actualizacion cada 10s |
    <a href="/api/health" target="_blank" style="color:var(--accent);text-decoration:none;">API Health</a> |
    <a href="/api/factory" target="_blank" style="color:var(--accent);text-decoration:none;">API Factory</a> |
    <a href="/api/pipeline" target="_blank" style="color:var(--accent);text-decoration:none;">API Pipeline</a> |
    <a href="/api/pipeline/history" target="_blank" style="color:var(--accent);text-decoration:none;">API History</a> |
    <a href="/api/config" target="_blank" style="color:var(--accent);text-decoration:none;">API Config</a>
</div>

<script>
function copyCmd(cmd) { navigator.clipboard.writeText(cmd).catch(function(){}); }
function refreshData() {
    fetch('/api/dashboard').then(function(r){return r.json()}).then(function(data){
        var d=document.getElementById('tsDisplay'); if(d) d.textContent=data.timestamp;
    }).catch(function(){});
}
function refreshLogs() {
    fetch('/api/logs').then(function(r){return r.json()}).then(function(data){
        var c=document.getElementById('logContainer'); if(!c) return;
        var entries=data.entries||[];
        if(entries.length===0){c.innerHTML='<div style=\"color:var(--text-dim);\">Sin eventos.</div>';return;}
        var html=''; var i,e; for(i=0;i<entries.length;i++){e=entries[i];
            html+='<div class=\"log-entry\"><span class=\"log-ts\">'+(e.ts?e.ts.slice(11,19):'')+'</span>'
                +'<span>'+escHtml(e.icon||'\u2022')+'</span>'
                +'<span style=\"color:var(--accent2);font-weight:600;font-size:0.65rem;\">'+escHtml(e.source||'')+'</span>'
                +'<span>'+escHtml(e.message||'')+'</span></div>';}
        c.innerHTML=html;
    }).catch(function(){});
}
function runPipeline() {
    var btn=document.getElementById('pipeRunBtn'); var status=document.getElementById('pipeRunStatus');
    if(!btn||btn.disabled) return;
    var cats=document.getElementById('pipeCats').value.trim();
    if(!cats){status.textContent='Indica al menos una categoria'; return;}
    btn.disabled=true; btn.textContent='... Ejecutando'; status.textContent='Iniciando pipeline...';
    var body=JSON.stringify({
        categories: cats,
        backend: document.getElementById('pipeBackend').value,
        run_suffix: document.getElementById('pipeSuffix').value.trim(),
        skip_generation: document.getElementById('pipeSkipGen').checked,
        skip_pixel: document.getElementById('pipeSkipPix').checked,
        skip_db: document.getElementById('pipeSkipDb').checked,
    });
    fetch('/api/pipeline/run',{method:'POST',headers:{'Content-Type':'application/json'},body:body})
    .then(function(r){return r.json()})
    .then(function(data){
        if(data.success){
            status.textContent='Pipeline iniciado. Monitoreando...';
            var poll=setInterval(function(){
                fetch('/api/pipeline').then(function(r){return r.json()}).then(function(d){
                    if(!d.running){
                        clearInterval(poll);
                        btn.disabled=false; btn.textContent='\u25b6 Ejecutar Pipeline';
                        status.textContent='Completado en '+d.duration_min+'m';
                        refreshPipeline();
                    }
                }).catch(function(){});
            },3000);
        } else {
            btn.disabled=false; btn.textContent='\u25b6 Ejecutar Pipeline';
            status.textContent='Error: '+(data.error||'desconocido');
        }
    }).catch(function(err){
        btn.disabled=false; btn.textContent='\u25b6 Ejecutar Pipeline';
        status.textContent='Error de conexion';
    });
}
function refreshConfig() {
    fetch('/api/config').then(function(r){return r.json()}).then(function(data){
        var c=document.getElementById('configContainer'); if(!c) return;
        if(!data.available){
            c.innerHTML='<div style="color:var(--text-dim);">Config no disponible</div>'; return;
        }
        var labels = {
            llm_timeout: 'LLM (Ollama)',
            coding_timeout: 'Coding (Buffy)',
            image_timeout: 'Image (GenFactory)',
            pipeline_timeout: 'Pipeline (Assets)',
            multi_timeout: 'Lote paralelo',
        };
        var html='';
        for (var key in labels) {
            var val = data[key];
            var display = val === null ? 'sin limite' : val + 's';
            html += '<div class=\"metric\"><span class=\"label\">' + labels[key] + '</span><span class=\"value blue\">' + display + '</span></div>';
        }
        c.innerHTML = html;
    }).catch(function(){});
}

function refreshPipelineHistory() {
    fetch('/api/pipeline/history').then(function(r){return r.json()}).then(function(data){
        var c=document.getElementById('pipelineHistoryContainer'); var cnt=document.getElementById('histCount');
        if(!c) return;
        var hist=data.history||[];
        if(cnt) cnt.textContent=hist.length+' registros';
        if(hist.length===0){c.innerHTML='<div style="color:var(--text-dim);font-size:0.72rem;">Sin ejecuciones historicas.</div>';return;}
        var html='<table style="width:100%;border-collapse:collapse;font-size:0.7rem;">'
            +'<thead><tr style="color:var(--text-dim);border-bottom:1px solid var(--border);">'
            +'<th style="padding:4px 6px;text-align:left;">Hora</th>'
            +'<th style="padding:4px 6px;text-align:left;">Categorias</th>'
            +'<th style="padding:4px 6px;text-align:right;">Duracion</th>'
            +'<th style="padding:4px 6px;text-align:center;">Gen</th>'
            +'<th style="padding:4px 6px;text-align:center;">Pix</th>'
            +'<th style="padding:4px 6px;text-align:center;">DB</th>'
            +'<th style="padding:4px 6px;text-align:center;">Resultado</th></tr></thead><tbody>';
        var i,h,ts,timeStr,cls,resultLabel;
        for(i=0;i<hist.length;i++){h=hist[i];
            ts=h.timestamp||''; timeStr=ts.length>16?ts.slice(11,19):ts.slice(0,10);
            cls=h.success?'green':'red';
            resultLabel=h.success?'EXITO':'FALLO';
            html+='<tr style="border-bottom:1px solid rgba(28,28,46,0.5);">'
                +'<td style="padding:3px 6px;color:var(--text-dim);">'+escHtml(timeStr)+'</td>'
                +'<td style="padding:3px 6px;">'+escHtml(h.categories||'')+'</td>'
                +'<td style="padding:3px 6px;text-align:right;color:var(--blue);">'+escHtml(h.duration||'')+'</td>'
                +'<td style="padding:3px 6px;text-align:center;">'+escHtml(h.gen||'')+'</td>'
                +'<td style="padding:3px 6px;text-align:center;">'+escHtml(h.pix||'')+'</td>'
                +'<td style="padding:3px 6px;text-align:center;">'+escHtml(h.db||'')+'</td>'
                +'<td style="padding:3px 6px;text-align:center;"><span style="color:var(--'+cls+');font-weight:600;">'+resultLabel+'</span></td>'
                +'</tr>';}
        html+='</tbody></table>';
        c.innerHTML=html;
    }).catch(function(){});
}
function refreshPipeline() {
    fetch('/api/pipeline').then(function(r){return r.json()}).then(function(data){
        var el=document.getElementById('pipelineContainer'); var meta=document.getElementById('pipelineMeta');
        if(!el||!data.available) return;
        if(!data.executed){
            el.innerHTML='<div class=\"alert-box warn\">Aun no se ha ejecutado ningun pipeline.</div>';
            if(meta) meta.textContent='Sin ejecuciones'; return;
        }
        var status=data.success?'EXITO':'FALLO'; var cls=data.success?'green':'red';
        if(meta) meta.textContent=data.duration_min+'m . '+status;
        var html='<div style=\"display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px;\">'
            +'<div><div class=\"metric\"><span class=\"label\">Duracion</span><span class=\"value blue\">'+data.duration_min+' min</span></div>'
            +'<div class=\"metric\"><span class=\"label\">Resultado</span><span class=\"value '+cls+'\">'+status+'</span></div>'
            +'<div class=\"metric\"><span class=\"label\">Categorias</span><span class=\"value\">'+(data.output_summary?escHtml(data.output_summary.categories):'')+'</span></div></div>'
            +'<div><div class=\"metric\"><span class=\"label\">Generacion</span><span class=\"value\">'+(data.output_summary?escHtml(data.output_summary.generation):'')+'</span></div>'
            +'<div class=\"metric\"><span class=\"label\">Pixel Art</span><span class=\"value\">'+(data.output_summary?escHtml(data.output_summary.pixel_art):'')+'</span></div>'
            +'<div class=\"metric\"><span class=\"label\">DB Insert</span><span class=\"value\">'+(data.output_summary?escHtml(data.output_summary.db_insert):'')+'</span></div></div>';
        if(data.error) html+='<div class=\"alert-box err\" style=\"grid-column:1/-1;\">Error: '+escHtml(data.error.slice(0,200))+'</div>';
        html+='</div>';
        el.innerHTML=html;
    }).catch(function(){});
}
function refreshFactory() {
    fetch('/api/factory').then(function(r){return r.json()}).then(function(data){
        var el=document.getElementById('factoryAgents'); if(!el||!data.available||!data.agents) return;
        var html=''; var icons={coding:'\uD83E\uDD16',image:'\uD83D\uDDBC',llm:'\uD83E\uDDE0',service:'\uD83D\uDD0C',supervisor:'\uD83D\uDC68\u200D\uD83D\uDD27'};
        var i,a,icon,cls; for(i=0;i<data.agents.length;i++){a=data.agents[i];
            icon=icons[a.type]||'\u2022'; cls=a.healthy?'on':'off';
            html+='<div class=\"agent-row\" title=\"'+a.type+' - '+a.endpoint+'\">'
                +'<span class=\"a-icon\">'+icon+'</span>'
                +'<span class=\"a-dot '+cls+'\"></span>'
                +'<span class=\"a-name\">'+escHtml(a.name)+'</span>'
                +'<span class=\"a-status '+cls+'\">'+(a.healthy?'ON':'OFF')+'</span></div>';}
        el.innerHTML=html;
    }).catch(function(){});
}
function escHtml(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}
refreshLogs(); setInterval(refreshLogs,10000); refreshFactory(); setInterval(refreshFactory,8000);
refreshPipeline(); setInterval(refreshPipeline,10000);
refreshPipelineHistory(); setInterval(refreshPipelineHistory,15000);
refreshConfig(); setInterval(refreshConfig,15000);
setInterval(refreshData,8000);
</script>
</body>
</html>
"""

# --- Routes ---
@app.route("/")
def index():
    def _safe(fn, default):
        try: return fn() if callable(fn) else fn
        except: return default

    gpu_def = {"available":False}; ram_def = {"total_gb":0,"used_gb":0,"available_gb":0,"used_percent":0}; disk_def = {}
    gpu = _safe(check_gpu,gpu_def) if _MONITOR_OK else gpu_def
    ram = _safe(check_ram,ram_def) if _MONITOR_OK else ram_def
    disk = _safe(check_disk,disk_def) if _MONITOR_OK else disk_def
    services = _safe(check_services,{}) if _MONITOR_OK else {}
    agent_data = collect_agent_status()
    agents_list = agent_data.get("agents",[])
    env_data = collect_environment()
    ollama_models = collect_ollama_models()
    openhuman_health = check_openhuman_health()

    alerts = []
    healthy = True
    if _MONITOR_OK:
        try:
            alerts = detect_alerts({"gpu":gpu,"ram":ram,"disk":disk,"services":services})
            healthy = len(alerts) == 0
        except: alerts = ["Error alertas"]; healthy = False
    else: alerts = ["monitor_sistema.py no disponible"]

    factory_data = collect_factory_status()

    return render_template_string(DASHBOARD_HTML,
        gpu=gpu, ram=ram, disk=disk, services=services, alerts=alerts, healthy=healthy,
        timestamp=datetime.now().strftime("%H:%M:%S"),
        agent_stats={"running":sum(1 for a in agents_list if a["running"]),"total":len(agents_list),"list":agents_list},
        env=env_data, ollama_models=ollama_models, openhuman=openhuman_health,
        factory_stats=factory_data,
        pipeline_stats=collect_pipeline_status())

@app.route("/api/health")
def api_health():
    if not _MONITOR_OK: return jsonify({"error":"not available"}), 500
    def _safe(fn, default):
        try: return fn()
        except: return default
    gpu=_safe(check_gpu,{"available":False}); ram=_safe(check_ram,{}); disk=_safe(check_disk,{}); services=_safe(check_services,{})
    alerts = []
    try: alerts = detect_alerts({"gpu":gpu,"ram":ram,"disk":disk,"services":services})
    except: alerts = ["Error"]
    return jsonify({"timestamp":datetime.now().isoformat(),"healthy":len(alerts)==0,"gpu":gpu,"ram":ram,"disk":disk,"services":services,"alerts":alerts})

@app.route("/api/agents")
def api_agents():
    return jsonify(collect_agent_status())

@app.route("/api/config")
def api_config():
    return jsonify(collect_dispatcher_config())


@app.route("/api/environment")
def api_environment():
    env_data = collect_environment()
    env_data["ollama_models"] = collect_ollama_models()
    return jsonify(env_data)

@app.route("/api/logs")
def api_logs():
    entries = get_logs(40) if _LOG_OK else []
    return jsonify({"entries":entries,"total":len(entries)})

@app.route("/api/factory")
def api_factory():
    return jsonify(collect_factory_status())

@app.route("/api/pipeline")
def api_pipeline():
    return jsonify({
        **collect_pipeline_status(),
        "running": _PIPELINE_RUNNING,
        "available_categories": AVAILABLE_CATEGORIES,
    })

@app.route("/api/pipeline/history")
def api_pipeline_history():
    """Historial de ejecuciones de pipeline desde ObsidianMemory."""
    hist = collect_pipeline_history()
    return jsonify({
        "history": hist,
        "total": len(hist),
    })

@app.route("/api/pipeline/run", methods=["POST"])
def api_pipeline_run():
    """Ejecutar pipeline de assets desde el navegador."""
    import threading
    global _PIPELINE_RUNNING, _PIPELINE_THREAD

    data = request.get_json(silent=True) or {}
    categories = data.get("categories", "").strip()
    if not categories:
        return jsonify({"success": False, "error": "Debes especificar al menos una categoria"}), 400

    if _PIPELINE_RUNNING:
        return jsonify({"success": False, "error": "Ya hay un pipeline en ejecucion"}), 409

    backend = data.get("backend", "factory")
    skip_gen = data.get("skip_generation", False)
    skip_pix = data.get("skip_pixel", False)
    skip_db = data.get("skip_db", False)
    run_suffix = data.get("run_suffix", "")

    def _run_pipeline():
        global _PIPELINE_RUNNING
        _PIPELINE_RUNNING = True
        try:
            factory = _get_factory()
            if factory:
                factory.delegate(
                    task_type="pipeline",
                    task=categories,
                    backend=backend,
                    skip_generation=skip_gen,
                    skip_pixel=skip_pix,
                    skip_db=skip_db,
                    run_suffix=run_suffix,
                )
        except Exception as e:
            if _LOG_OK:
                syslog("Pipeline", "\u274c", f"Error en ejecucion: {e}")
        finally:
            _PIPELINE_RUNNING = False

    _PIPELINE_THREAD = threading.Thread(target=_run_pipeline, daemon=True)
    _PIPELINE_THREAD.start()

    if _LOG_OK:
        syslog("Pipeline", "\U0001f4a1", f"Pipeline iniciado desde dashboard: {categories}")

    return jsonify({"success": True, "status": "started", "categories": categories})

@app.route("/api/dashboard")
def api_dashboard():
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

    def _build_dashboard():
        def _safe(fn, default):
            try: return fn()
            except: return default
        gpu=_safe(check_gpu,{"available":False}) if _MONITOR_OK else {"available":False}
        ram=_safe(check_ram,{}) if _MONITOR_OK else {}
        disk=_safe(check_disk,{}) if _MONITOR_OK else {}
        services=_safe(check_services,{}) if _MONITOR_OK else {}
        agent_data=_safe(collect_agent_status,{"agents":[],"services":{},"total_running":0,"total_agents":0})
        env_data=_safe(collect_environment,{"timestamp":"","asset_count":0,"categories_found":{}})
        ollama_models=_safe(collect_ollama_models,[])
        openhuman_health=_safe(check_openhuman_health,{"available":False})
        alerts=[]
        try: alerts=detect_alerts({"gpu":gpu,"ram":ram,"disk":disk,"services":services}) if _MONITOR_OK else []
        except: alerts=["Error"]
        factory_data = _safe(collect_factory_status,{"available":False,"agents":[],"healthy":0,"total":0})
        return {"timestamp":datetime.now().strftime("%H:%M:%S"),"healthy":len(alerts)==0,
            "gpu":gpu,"ram":ram,"disk":disk,"services":services,"alerts":alerts,
            "agent_stats":{"running":sum(1 for a in agent_data.get("agents",[]) if a["running"]),
                           "total":len(agent_data.get("agents",[])),"list":agent_data.get("agents",[])},
            "environment":env_data,"ollama_models":ollama_models,"openhuman":openhuman_health,
            "factory":factory_data,
            "pipeline":_safe(collect_pipeline_status,{"available":False,"executed":False}),
            "dispatcher_config":_safe(collect_dispatcher_config,{"available":False})}

    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_build_dashboard)
        result = future.result(timeout=5)
        executor.shutdown(wait=False)
        return jsonify(result)
    except (FutureTimeout, Exception):
        if executor:
            executor.shutdown(wait=False)
        return jsonify({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "healthy": False,
            "gpu": {"available": False},
            "ram": {},
            "disk": {},
            "services": {},
            "alerts": ["Dashboard timeout — servicios no responden"],
            "agent_stats": {"running": 0, "total": 0, "list": []},
            "environment": {},
            "ollama_models": [],
            "openhuman": {"available": False},
            "factory": {"available": False, "agents": [], "healthy": 0, "total": 0},
            "pipeline": {"available": False, "executed": False},
            "dispatcher_config": {"available": False},
        })

def main():
    parser = argparse.ArgumentParser(description="SIMMOON Dashboard + FactoryGames Orquestacion")
    parser.add_argument("--port","-p",type=int,default=5001,help="Puerto (default: 5001)")
    parser.add_argument("--host",type=str,default="127.0.0.1",help="Host (default: 127.0.0.1)")
    args = parser.parse_args()
    if not _MONITOR_OK: print("[WARN] monitor_sistema.py no encontrado")
    if _LOG_OK: syslog("Dashboard","📊",f"Dashboard v2 iniciado en http://{args.host}:{args.port}")
    print(f"\n  🚀 SIMMOON Dashboard v2 + FactoryGames")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Endpoints:")
    print(f"    /               - Dashboard web interactivo")
    print(f"    /api/health     - Salud del sistema (JSON)")
    print(f"    /api/agents     - Estado de agentes (JSON)")
    print(f"    /api/environment- Entorno (JSON)")
    print(f"    /api/dashboard  - Datos completos (JSON)")
    print(f"    /api/logs       - Ultimos eventos (JSON)")
    print(f"    /api/factory    - Orquestacion FactoryGames (JSON)")
    print(f"    /api/pipeline   - Estado del pipeline (JSON)")
    print(f"    POST /api/pipeline/run - Ejecutar pipeline (JSON)")
    print(f"  Press Ctrl+C to stop\n")
    app.run(host=args.host, port=args.port, debug=False)

if __name__ == "__main__":
    main()
