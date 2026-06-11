#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agatha Actas — Agente de Reportes Periódicos 📋

Recolecta la actividad del sistema cada 4 horas y envía un resumen
a Telegram usando el bot DonHermes @Jeremias_Hermesai_bot.

Plataforma: cualquier sistema con Python 3 + monitor_sistema.py
Ejecución: demonio en segundo plano (--daemon) o reporte único (--test)

Uso:
    python agatha_actas.py --setup       # Configurar chat ID (envía mensaje al bot primero)
    python agatha_actas.py --test        # Enviar reporte de prueba ahora
    python agatha_actas.py --daemon      # Bucle cada 4 horas (demonio)
    python agatha_actas.py --interval 4  # Cada 4 horas (o pasar segundos)
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Import system monitor ────────────────────────────────────────────────
try:
    from monitor_sistema import (
        collect_report, check_gpu, check_ram, check_disk,
        check_services, detect_alerts, _wsl_cmd,
    )
    _MONITOR_OK = True
except ImportError as e:
    _MONITOR_OK = False
    _MONITOR_ERR = str(e)

# ── System Logger ────────────────────────────────────────────────────────
try:
    from system_logger import log as syslog
    _LOG_OK = True
except ImportError:
    _LOG_OK = False

# ── Config ────────────────────────────────────────────────────────────────
CONFIG_PATH = SCRIPT_DIR / "agatha_config.json"

# Token loading: env var > config file > empty
_agatha_cfg_token = ""
try:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _agatha_cfg = json.load(f)
            _agatha_cfg_token = _agatha_cfg.get("bot_token", "")
except Exception:
    pass
AGATHA_TOKEN = os.environ.get("AGATHA_BOT_TOKEN", _agatha_cfg_token)
TELEGRAM_API = f"https://api.telegram.org/bot{AGATHA_TOKEN}"
DEFAULT_INTERVAL = 14400  # 4 hours in seconds

# ── FactoryGames — Puestos de Trabajo ─────────────────────────────────────
FACTORY_WORKSTATIONS = [
    # (key, name, emoji, role, type, check_fn_name, production_order)
    {
        "key": "agatha_actas",
        "name": "Agatha Actas",
        "emoji": "📋",
        "role": "Supervisora General",
        "type": "management",
        "order": 0,
        "check": lambda: True,  # Siempre activa (este script)
    },
    {
        "key": "simmoon_agent",
        "name": "Director de Arte",
        "emoji": "🎨",
        "role": "Recomienda qué assets generar vía IA",
        "type": "design",
        "order": 1,
        "check": lambda: (SCRIPT_DIR / "simmoon_agent.py").exists(),
    },
    {
        "key": "simmoon_autogen",
        "name": "Diseñador Colaborativo",
        "emoji": "🤝",
        "role": "AutoGen: Generator + Critic + Curator",
        "type": "design",
        "order": 2,
        "check": lambda: (SCRIPT_DIR / "simmoon_autogen.py").exists(),
    },
    {
        "key": "simmoon_generator",
        "name": "Generador Multi-Backend",
        "emoji": "🖼️",
        "role": "Genera assets con ComfyUI / HuggingFace",
        "type": "production",
        "order": 3,
        "check": lambda: (SCRIPT_DIR / "simmoon_generator.py").exists(),
    },
    {
        "key": "simmoon_diffusers",
        "name": "Generador Diffusers",
        "emoji": "🧪",
        "role": "Genera assets vía Diffusers en WSL2",
        "type": "production",
        "order": 4,
        "check": lambda: (SCRIPT_DIR / "simmoon_diffusers.py").exists(),
    },
    {
        "key": "simmoon_pixelator",
        "name": "Pixelador",
        "emoji": "🎮",
        "role": "Convierte assets a pixel-art retro",
        "type": "production",
        "order": 5,
        "check": lambda: (SCRIPT_DIR / "simmoon_pixelator.py").exists(),
    },
    {
        "key": "simmoon_pipeline",
        "name": "Pipeline Completo",
        "emoji": "🏭",
        "role": "LangGraph: Prompt → Generar → Pixelar → DB",
        "type": "production",
        "order": 6,
        "check": lambda: (SCRIPT_DIR / "simmoon_pipeline.py").exists(),
    },
    {
        "key": "generator_factory",
        "name": "Generator Factory",
        "emoji": "🏗️",
        "role": "Fábrica de backends con fallback chain",
        "type": "production",
        "order": 7,
        "check": lambda: (SCRIPT_DIR / "generator_factory.py").exists(),
    },
    {
        "key": "postgresql",
        "name": "PostgreSQL",
        "emoji": "🗄️",
        "role": "Base de datos compartida / memoria persistente",
        "type": "storage",
        "order": 8,
        "check": lambda: bool(get_db_conn()),
    },
    {
        "key": "ollama",
        "name": "Ollama",
        "emoji": "🧠",
        "role": "Motor de LLM local (modelos AI)",
        "type": "engine",
        "order": 9,
        "check": lambda: check_http("http://localhost:11434", timeout=2),
    },
    {
        "key": "comfyui",
        "name": "ComfyUI",
        "emoji": "🎨",
        "role": "Generación de imágenes con workflow visual",
        "type": "engine",
        "order": 10,
        "check": lambda: check_http("http://localhost:8188", timeout=2),
    },
    {
        "key": "hermes",
        "name": "Hermes Agent",
        "emoji": "🧠",
        "role": "Agente Nous Research con memoria",
        "type": "agent",
        "order": 11,
        "check": lambda: check_http("http://localhost:9119", timeout=2),
    },
    {
        "key": "openhuman",
        "name": "OpenHuman",
        "emoji": "🤖",
        "role": "Agente open-source",
        "type": "agent",
        "order": 12,
        "check": lambda: check_http("http://localhost:7788", timeout=2),
    },
    {
        "key": "creativo_juegos",
        "name": "Creativo de Juegos",
        "emoji": "🎮",
        "role": "Dirección Creativa y Diseño de Mecánicas",
        "type": "design",
        "order": 13,
        "check": lambda: (SCRIPT_DIR / "factory" / "agent_creativo.py").exists(),
    },
    {
        "key": "guionista",
        "name": "Guionista",
        "emoji": "✍️",
        "role": "Narrativa, Diálogos y World-Building",
        "type": "design",
        "order": 15,
        "check": lambda: (SCRIPT_DIR / "factory" / "agent_guionista.py").exists(),
    },
    {
        "key": "reuniones",
        "name": "Sistema de Reuniones",
        "emoji": "🏢",
        "role": "Brainstorming semanal y actas en Obsidian",
        "type": "management",
        "order": 0,
        "check": lambda: (SCRIPT_DIR / "simmoon_reuniones.py").exists(),
    },
    {
        "key": "quality_inspector",
        "name": "Quality Inspector",
        "emoji": "🎯",
        "role": "Control de calidad: verifica assets, detecta corruptos",
        "type": "monitoring",
        "order": 16,
        "check": lambda: (SCRIPT_DIR / "simmoon_quality_inspector.py").exists(),
    },
    {
        "key": "telegram_bot",
        "name": "Telegram Bot",
        "emoji": "📱",
        "role": "Interfaz de chat con agentes",
        "type": "communication",
        "order": 17,
        "check": lambda: check_windows_process("telegram_bot") or check_tmux_session("telegram-bot"),
    },
    {
        "key": "monitor_sistema",
        "name": "Monitor Sistema",
        "emoji": "📊",
        "role": "Monitoreo de GPU/RAM/disco/servicios",
        "type": "monitoring",
        "order": 18,
        "check": lambda: _MONITOR_OK and bool(collect_report()),
    },
]

# ── File helpers ─────────────────────────────────────────────────────────
def load_config() -> dict:
    """Load Agatha configuration."""
    default = {
        "chat_id": None,
        "bot_name": "DonHermes",
        "interval": DEFAULT_INTERVAL,
        "last_report": None,
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except Exception:
            pass
    return dict(default)


def save_config(cfg: dict):
    """Save Agatha configuration."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Config guardada en {CONFIG_PATH}")


# ── Telegram HTTP API ────────────────────────────────────────────────────
def _tg_request(method: str, params: dict = None) -> dict:
    """Make a request to the Telegram Bot API."""
    url = f"{TELEGRAM_API}/{method}"
    if params is None:
        params = {}
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_telegram(text: str, parse_mode: Optional[str] = "Markdown") -> bool:
    """Send a message to Telegram. Returns True on success.
    
    Args:
        text: Message text to send
        parse_mode: 'Markdown', 'HTML', or None to disable formatting
    """
    cfg = load_config()
    chat_id = cfg.get("chat_id")
    if not chat_id:
        print("[ERROR] No hay chat_id configurado. Ejecuta: python agatha_actas.py --setup")
        return False

    # Telegram has a 4096 char limit
    if len(text) > 4000:
        text = text[:4000] + "\n\n…(truncado)"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode is not None:
        payload["parse_mode"] = parse_mode

    result = _tg_request("sendMessage", payload)

    if result.get("ok"):
        return True
    else:
        # If Markdown parsing fails, retry without parse_mode
        error_desc = result.get("error", "")
        if "parse" in error_desc.lower() and parse_mode is not None:
            payload.pop("parse_mode", None)
            result2 = _tg_request("sendMessage", payload)
            if result2.get("ok"):
                return True
            else:
                print(f"[ERROR] Telegram send failed (plain text): {result2.get('error', 'unknown')}")
                return False
        print(f"[ERROR] Telegram send failed: {error_desc}")
        return False


def discover_chat_id() -> int:
    """Fetch recent updates to find a chat_id."""
    result = _tg_request("getUpdates", {"timeout": 5, "limit": 10})

    if not result.get("ok"):
        print(f"[ERROR] No se pudo conectar con Telegram: {result.get('error', '?')}")
        return None

    updates = result.get("result", [])
    if not updates:
        print("[WARN] No hay mensajes recientes. Envía un mensaje a @Jeremias_Hermesai_bot primero.")
        return None

    # Find the most recent chat
    for update in reversed(updates):
        msg = update.get("message", {})
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        username = chat.get("username", chat.get("first_name", "?"))
        if chat_id:
            print(f"  → Chat encontrado: {username} (ID: {chat_id})")
            return chat_id

    return None


# ── Activity Collector ───────────────────────────────────────────────────
def check_tmux_session(name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        r = _wsl_cmd(f"tmux has-session -t {name} 2>/dev/null && echo YES || echo NO", timeout=5)
        return "YES" in r.stdout
    except Exception:
        return False


def check_windows_process(script_name: str) -> bool:
    """Check if a Python script is running as a Windows process.
    
    Uses PowerShell to query running python processes and checks
    if any of them have the given script name in their command line.
    
    Args:
        script_name: Name of the Python script to find (e.g. 'telegram_bot')
    
    Returns:
        True if a matching process is found, False otherwise.
    """
    if sys.platform != "win32":
        return False
    try:
        cmd = [
            'powershell', '-NoProfile', '-Command',
            f'Get-CimInstance Win32_Process -Filter "name like \'%python%\'" | '
            f'Where-Object {{ $_.CommandLine -match \'{script_name}\' }} | '
            f'Select-Object -ExpandProperty ProcessId -First 1'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and result.stdout.strip().isdigit()
    except Exception:
        return False


def check_http(url: str, timeout: int = 3) -> bool:
    """Quick HTTP health check."""
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status < 500
    except Exception:
        return False


def collect_activity() -> dict:
    """Collect system activity data for the report."""
    now = datetime.now()

    # ── System health ──
    system = {}
    if _MONITOR_OK:
        system = collect_report()
    else:
        system = {"error": "monitor_sistema.py no disponible"}

    # ── Agent status ──
    agents = []
    agent_checks = {
        "Telegram Bot": check_windows_process("telegram_bot") or check_tmux_session("telegram-bot"),
        "Hermes Agent": check_http("http://localhost:9119", timeout=2),
        "OpenHuman": check_http("http://localhost:7788", timeout=2),
        "PostgreSQL": check_http("http://localhost:5432", timeout=2),
    }
    for name, running in agent_checks.items():
        agents.append({"name": name, "running": running})

    # Add Python agents
    py_agents = ["simmoon_agent.py", "simmoon_autogen.py", "simmoon_pipeline.py"]
    for py_file in py_agents:
        agents.append({
            "name": py_file.replace(".py", "").replace("simmoon_", "Simmoon ").title(),
            "running": (SCRIPT_DIR / py_file).exists(),
        })

    # ── Asset activity (recent files) ──
    now_ts = time.time()
    lookback_window = 14400  # 4 hours window (matches report interval)
    four_hours_ago = now_ts - lookback_window
    recent_assets = []
    total_assets = 0
    assets_by_category = {}  # Track per-category counts

    asset_categories = [
        "businesses", "vehicles", "greenhouses", "solar_energy",
        "lunar_map", "buildings_misc", "lunar_sites", "ui_elements",
        "roads", "decorations", "characters", "lunar_flora", "infrastructure",
    ]
    for cat in asset_categories:
        cat_dir = SCRIPT_DIR / cat
        if cat_dir.is_dir():
            cat_assets = 0
            cat_recent = 0
            for png in cat_dir.glob("*.png"):
                total_assets += 1
                cat_assets += 1
                try:
                    mtime = png.stat().st_mtime
                    if mtime > four_hours_ago:
                        recent_assets.append(str(png.name))
                        cat_recent += 1
                except Exception:
                    pass
            if cat_assets > 0:
                assets_by_category[cat] = {"total": cat_assets, "recent": cat_recent}

    # ── Last generation log ──
    gen_logs = list(SCRIPT_DIR.glob("generation_log*.txt"))
    last_gen = None
    gen_activity = ""
    gen_summary_lines = []
    gen_logs_in_window = 0
    if gen_logs:
        try:
            newest = max(gen_logs, key=lambda p: p.stat().st_mtime)
            last_gen_ts = newest.stat().st_mtime
            last_gen = datetime.fromtimestamp(last_gen_ts).strftime("%H:%M")
            # Read last lines for activity
            with open(newest, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Count lines within the 4h window
                for line in lines:
                    if line.strip():
                        gen_logs_in_window += 1
                gen_activity = "".join(lines[-5:])
                # Extract meaningful summary lines (non-boilerplate)
                for line in lines[-10:]:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("---") and not stripped.startswith("#"):
                        gen_summary_lines.append(stripped[:120])
        except Exception:
            pass

    # ── Timestamps ──
    uptime = "N/A"
    try:
        r = _wsl_cmd("uptime -p 2>/dev/null || uptime 2>/dev/null", timeout=5)
        uptime = r.stdout.strip() if r.stdout.strip() else "N/A"
    except Exception:
        pass

    # ── Count today's summaries ──
    today_summaries = 0
    try:
        from system_logger import get_recent
        logs = get_recent(48)  # Last 48 entries (24h at 30min intervals)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_summaries = sum(1 for e in logs if e.get('source') == 'Agatha Actas' and e.get('ts', '') >= today_start.strftime('%Y-%m-%d'))
    except Exception:
        pass

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "system": system,
        "agents": agents,
        "total_assets": total_assets,
        "assets_by_category": assets_by_category,
        "recent_assets": recent_assets[:10],
        "recent_count": len(recent_assets),
        "last_generation": last_gen,
        "gen_activity": gen_activity[:300],
        "gen_summary_lines": gen_summary_lines[-5:],
        "gen_logs_in_window": gen_logs_in_window,
        "uptime": uptime,
        "agent_running": sum(1 for a in agents if a["running"]),
        "agent_total": len(agents),
        "today_reports": today_summaries,
    }


def format_report(data: dict) -> str:
    """Format the hourly activity report for Telegram."""
    system = data.get("system", {})
    agents = data.get("agents", [])
    alerts = system.get("alerts", [])
    today_reports = data.get("today_reports", 0)

    lines = []
    lines.append(f"📋 *ACTA — Reporte (cada 4h)*")
    lines.append(f"🕐 {data['timestamp']}")
    lines.append(f"📊 Reports hoy: {today_reports}")
    lines.append("")

    # ── SISTEMA ──
    lines.append("━" * 30)
    lines.append("*SISTEMA*")
    lines.append("━" * 30)

    ram = system.get("ram", {})
    if ram.get("total_gb"):
        icon = "⚠️" if ram.get("used_percent", 0) > 85 else "🟢"
        lines.append(f"{icon} RAM: {ram['used_gb']}/{ram['total_gb']}GB ({ram['used_percent']}%)")

    disk = system.get("disk", {})
    for mount, info in disk.items():
        label = mount.split("/")[-1] or mount
        icon = "⚠️" if info.get("available_gb", 100) < 50 else "💾"
        lines.append(f"{icon} Disco {label}: {info['available_gb']}GB libre")

    gpu = system.get("gpu", {})
    if gpu.get("available"):
        lines.append(f"🎮 GPU: {gpu.get('temperature_c', '?')}°C · "
                      f"VRAM: {gpu.get('memory_used_mb', 0)}/{gpu.get('memory_total_mb', 0)}MB")
    else:
        lines.append("🎮 GPU: ❌ No disponible")

    lines.append(f"⏱️ Uptime: {data.get('uptime', 'N/A')}")

    # ── SERVICIOS ──
    lines.append("")
    lines.append("━" * 30)
    lines.append("*SERVICIOS*")
    lines.append("━" * 30)

    services = system.get("services", {})
    service_labels = {
        "ollama": ("🧠 Ollama", ":11434"),
        "comfyui": ("🎨 ComfyUI", ":8188"),
        "postgresql": ("🗄️ PostgreSQL", ":5432"),
        "openhuman": ("🤖 OpenHuman", ":7788"),

    }
    for key, (label, port) in service_labels.items():
        svc = services.get(key, {})
        icon = "✅" if svc.get("healthy") else "❌"
        latency = svc.get("latency_ms", "?")
        lines.append(f"{icon} {label} {port}  [{latency}ms]")

    # ── AGENTES ──
    lines.append("")
    lines.append("━" * 30)
    lines.append("*AGENTES*")
    lines.append("━" * 30)
    lines.append(f"({data['agent_running']}/{data['agent_total']} activos)")

    for a in agents:
        icon = "✅" if a["running"] else "⬜"
        lines.append(f"{icon} {a['name']}")

    # ── ACTIVIDAD ──
    lines.append("")
    lines.append("━" * 30)
    lines.append("*ACTIVIDAD — Últimas 4 Horas*")
    lines.append("━" * 30)

    # Assets generados recientemente
    if data["recent_count"] > 0:
        lines.append(f"🖼️ *Assets nuevos: {data['recent_count']}*")
        for asset in data["recent_assets"][:5]:
            lines.append(f"  • `{asset}`")
        if data["recent_count"] > 5:
            lines.append(f"  … y {data['recent_count'] - 5} más")
    else:
        lines.append("🖼️ Assets nuevos: 0")

    # Desglose por categoría
    assets_by_cat = data.get("assets_by_category", {})
    if assets_by_cat:
        lines.append("")
        lines.append(f"📂 *Distribución de Assets*")
        # Sort categories by total count descending
        sorted_cats = sorted(assets_by_cat.items(), key=lambda x: x[1]["total"], reverse=True)
        for cat, info in sorted_cats:
            recent_badge = f" +{info['recent']}" if info['recent'] > 0 else ""
            emoji_map = {
                "businesses": "🏪", "vehicles": "🚗", "greenhouses": "🌿",
                "solar_energy": "☀️", "lunar_map": "🌕", "buildings_misc": "🏛️",
                "lunar_sites": "🚀", "ui_elements": "🖥️", "roads": "🛣️",
                "decorations": "🎀", "characters": "🧑", "lunar_flora": "🌱",
                "infrastructure": "🏗️",
            }
            emoji = emoji_map.get(cat, "📁")
            lines.append(f"  {emoji} {cat}: {info['total']}{recent_badge}")

    # Actividad de generación
    if data["gen_summary_lines"]:
        lines.append("")
        lines.append(f"⚙️ *Actividad de Generación*")
        for gen_line in data["gen_summary_lines"]:
            lines.append(f"  • {gen_line}")
    elif data["gen_activity"]:
        lines.append("")
        lines.append(f"⚙️ *Generación*")
        lines.append(f"  {data['gen_activity'][:200]}")

    if data["last_generation"]:
        lines.append(f"🔄 Última generación: {data['last_generation']}")


    # ── BUFFY & CLAUDE CODE ACTIVITY ──
    lines.append("")
    lines.append("━" * 30)
    lines.append("*BUFFY & CLAUDE CODE*")
    lines.append("━" * 30)
    
    try:
        from system_logger import get_agent_activity
        buffy_acts = get_agent_activity("Buffy", limit=3)
        claude_acts = get_agent_activity("Claude Code", limit=3)
        
        if buffy_acts:
            for act in buffy_acts:
                lines.append(f"🦙 {act.get('message', '?')}")
        else:
            lines.append("🦙 Buffy: sin actividad registrada")
        
        if claude_acts:
            for act in claude_acts:
                lines.append(f"🤖 {act.get('message', '?')}")
        else:
            lines.append("🤖 Claude Code: sin actividad registrada")
    except Exception:
        lines.append("🦙 Buffy: sin actividad registrada")
        lines.append("🤖 Claude Code: sin actividad registrada")
    

    # Estado consolidado de la fábrica
    lines.append("")
    lines.append(f"🏭 *Estado de Fábrica*")
    lines.append(f"  🟢 Activos: {data['agent_running']}/{data['agent_total']} agentes")
    lines.append(f"  📦 Total assets: {data['total_assets']}")

    # Agentes activos e inactivos
    active_agents = [a["name"] for a in data.get("agents", []) if a["running"]]
    inactive_agents = [a["name"] for a in data.get("agents", []) if not a["running"]]
    if active_agents:
        lines.append(f"  ✅ Activos: {', '.join(active_agents)}")
    if inactive_agents:
        lines.append(f"  ⬜ Inactivos: {', '.join(inactive_agents)}")

    # ── ALERTAS ──
    if alerts:
        lines.append("")
        lines.append("━" * 30)
        lines.append(f"🚨 *ALERTAS ({len(alerts)})*")
        lines.append("━" * 30)
        for a in alerts[:5]:
            lines.append(f"  {a}")

    # ── FOOTER ──
    lines.append("")
    lines.append(f"_{datetime.now().strftime('%Y-%m-%d %H:%M')}_ · 🤖 Agatha Actas")
    lines.append("")

    return "\n".join(lines)


# ── FactoryGames Supervisor ────────────────────────────────────────────
def _check_workstation(ws: dict) -> dict:
    """Check a single workstation and return its live status."""
    try:
        running = ws["check"]()
    except Exception:
        running = False
    
    return {
        **ws,
        "running": running,
        "status_emoji": "🟢" if running else "🔴",
    }


def supervise_agents() -> list:
    """Supervisar todos los puestos de trabajo de FactoryGames.
    
    Returns list of workstation dicts with live status.
    """
    results = []
    for ws in FACTORY_WORKSTATIONS:
        checked = _check_workstation(ws)
        results.append(checked)
    return results


def factory_floor_overview(results: list = None) -> str:
    """Generar vista de piso de fábrica con todos los puestos.
    
    Returns string formateado con el layout de la fábrica.
    """
    if results is None:
        results = supervise_agents()
    
    # Separar por tipo
    by_type = {}
    for r in results:
        t = r["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(r)
    
    # Orden de tipos en la línea de producción
    type_order = ["management", "design", "production", "storage", "engine", "agent", "communication", "monitoring"]
    type_labels = {
        "management": "🏢 GESTIÓN",
        "design": "✏️ DISEÑO",
        "production": "⚙️ PRODUCCIÓN",
        "storage": "💾 ALMACENAMIENTO",
        "engine": "🔧 MOTORES",
        "agent": "🤖 AGENTES",
        "communication": "📡 COMUNICACIÓN",
        "monitoring": "📊 MONITOREO",
    }
    
    total = len(results)
    active = sum(1 for r in results if r["running"])
    
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  🏭 FACTORYGAMES — PISO DE FÁBRICA")
    lines.append(f"  {active}/{total} puestos activos")
    lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"{'='*60}")
    
    for t in type_order:
        if t not in by_type:
            continue
        workstations = sorted(by_type[t], key=lambda w: w["order"])
        
        lines.append(f"\n  {type_labels.get(t, t.upper())}")
        lines.append(f"  {'─'*56}")
        
        for ws in workstations:
            icon = ws["status_emoji"]
            lines.append(f"  {icon} {ws['emoji']} {ws['name']}")
            lines.append(f"     {ws['role']}")
    
    lines.append(f"\n{'='*60}")
    lines.append(f"  Total: {active}/{total} activos | "
                 f"{total-active} inactivos")
    lines.append(f"{'='*60}")
    
    return "\n".join(lines)


def coordinate_tasks(results: list = None) -> list:
    """Analizar el estado de la fábrica y sugerir próximas acciones.
    
    Returns list of suggested tasks with priority.
    """
    if results is None:
        results = supervise_agents()
    
    suggestions = []
    now = datetime.now()
    
    # ── Build lookup ──
    by_key = {r["key"]: r for r in results}
    
    # ── Check synthesis for gaps ──
    try:
        summaries = get_recent_summaries(days=2)
        if summaries:
            latest = summaries[0]
            today_date = now.strftime("%Y-%m-%d")
            
            # Check if today has production activity
            if str(latest["date"]) != today_date:
                suggestions.append({
                    "priority": "alta",
                    "area": "producción",
                    "action": "No hay síntesis de hoy — ejecutar generación de assets",
                    "command": "python simmoon_generator.py --backend comfyui",
                })
            
            # Check asset counts
            if latest["assets_total"] < 100:
                suggestions.append({
                    "priority": "media",
                    "area": "producción",
                    "action": f"Solo {latest['assets_total']} assets — bajo para una fábrica, generar más",
                    "command": "python simmoon_generator.py --backend comfyui",
                })
            
            # Check agents
            if latest["agents_active"] < latest["agents_total"]:
                inactive = latest["agents_total"] - latest["agents_active"]
                suggestions.append({
                    "priority": "media",
                    "area": "agentes",
                    "action": f"{inactive} agente(s) inactivo(s) — revisar logs",
                    "command": None,
                })
    except Exception as e:
        suggestions.append({
            "priority": "baja",
            "area": "síntesis",
            "action": f"No se pudo leer síntesis: {e}",
            "command": None,
        })
    
    # ── Check each workstation ──
    # Production line suggestions
    production_keys = ["ollama", "comfyui", "simmoon_generator", "simmoon_pixelator"]
    for key in production_keys:
        ws = by_key.get(key)
        if ws and not ws["running"]:
            suggestions.append({
                "priority": "alta" if key in ("ollama",) else "media",
                "area": "production_line",
                "action": f"{ws['emoji']} {ws['name']} está inactivo — iniciarlo para reactivar la línea",
                "command": None,
            })
    
    # Memory system
    pg = by_key.get("postgresql")
    if pg and not pg["running"]:
        suggestions.append({
            "priority": "crítica",
            "area": "infraestructura",
            "action": "🗄️ PostgreSQL caído — la memoria compartida no está disponible",
            "command": "sudo systemctl start postgresql  # o el comando correspondiente",
        })
    
    # ── Check recent generation activity ──
    gen_logs = list(SCRIPT_DIR.glob("generation_log*.txt"))
    if gen_logs:
        try:
            newest = max(gen_logs, key=lambda p: p.stat().st_mtime)
            hours_since = (time.time() - newest.stat().st_mtime) / 3600
            if hours_since > 6:
                suggestions.append({
                    "priority": "media",
                    "area": "producción",
                    "action": f"⏰ Última generación fue hace {hours_since:.0f}h — ¿necesitamos más assets?",
                    "command": "python simmoon_generator.py --backend comfyui",
                })
        except Exception:
            pass
    else:
        suggestions.append({
            "priority": "baja",
            "area": "producción",
            "action": "📭 No hay registros de generación — la fábrica nunca ha producido",
            "command": "python simmoon_generator.py --backend comfyui --category businesses",
        })
    
    # ── Check for agent memory sync needs ──
    try:
        from agent_memory import AgentMemory
        agatha_mem = AgentMemory('agatha', project='SIMMOON')
        last_sync = agatha_mem.get('hourly_status')
        if last_sync:
            sync_age = (now - last_sync.get('updated_at', now)).total_seconds() / 3600
            if sync_age > 2:
                suggestions.append({
                    "priority": "baja",
                    "area": "memoria",
                    "action": f"🔄 Último sync de memoria fue hace {sync_age:.0f}h — ejecutar sync",
                    "command": "python connect_agents_to_memory.py --sync-all",
                })
    except Exception:
        pass
    
    return suggestions


def format_factory_report(results: list = None) -> str:
    """Generate a complete factory status report for Telegram."""
    if results is None:
        results = supervise_agents()
    
    suggestions = coordinate_tasks(results)
    overview = factory_floor_overview(results)
    
    lines = []
    lines.append(f"🏭 *FACTORYGAMES — Reporte de Supervisión*")
    lines.append(f"🕐 {datetime.now().strftime('%H:%M')}")
    lines.append("")
    
    # Production summary
    active = sum(1 for r in results if r["running"])
    total = len(results)
    prod_active = sum(1 for r in results if r["type"] == "production" and r["running"])
    prod_total = sum(1 for r in results if r["type"] == "production")
    
    lines.append(f"📊 *Resumen de Fábrica*")
    lines.append(f"  Puestos: {active}/{total} activos")
    lines.append(f"  Producción: {prod_active}/{prod_total} activos")
    
    # Check synthesis for asset numbers
    try:
        summaries = get_recent_summaries(days=1)
        if summaries:
            s = summaries[0]
            lines.append(f"  Assets totales: {s['assets_total']}")
    except Exception:
        pass
    
    lines.append("")
    lines.append(f"⚠️ *Sugerencias ({len(suggestions)})*")
    lines.append("")
    for s in sorted(suggestions, key=lambda x: {"crítica": 0, "alta": 1, "media": 2, "baja": 3}.get(x["priority"], 4)):
        p_icon = {"crítica": "🚨", "alta": "⏫", "media": "🔶", "baja": "ℹ️"}.get(s["priority"], "•")
        lines.append(f"{p_icon} *[{s['priority'].upper()}]* {s['area']}: {s['action']}")
        if s.get("command"):
            lines.append(f"  `{s['command']}`")
    
    lines.append("")
    lines.append(f"_Agatha Supervisora · {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    
    return "\n".join(lines)


# ── Agent Memory Sync ─────────────────────────────────────────────────
try:
    from agent_memory import sync_hermes_to_openhuman, sync_openhuman_to_hermes
    _SYNC_OK = True
except ImportError:
    _SYNC_OK = False


# ── Agente Memory ───────────────────────────────────────────────────────
def sync_memory_to_agents():
    """Sincronizar memorias importantes con el sistema de memoria compartida."""
    try:
        import sys
        sys.path.insert(0, str(SCRIPT_DIR))
        from agent_memory import AgentMemory, get_all_agents_memory_summary
        
        # Guardar estado actual del sistema como memoria
        memory = AgentMemory('agatha', project='SIMMOON')
        
        # Guardar resumen de servicios activos
        system = {}
        if _MONITOR_OK:
            system = collect_report()
        
        services = system.get('services', {})
        services_active = sum(1 for s in services.values() if s.get('healthy'))
        
        memory.save_context(
            'hourly_status',
            f"Reporte 4h: {services_active}/{len(services)} servicios activos",
            tags=['status', '4hourly', 'services'],
            importance=2,
            content_json={'services': list(services.keys()), 'active': services_active}
        )
        
        # Guardar última síntesis diaria
        summary = generate_daily_summary()
        memory.save_fact(
            'last_daily_summary',
            summary['title'],
            tags=['daily', 'summary', 'telegram'],
            importance=4,
            content_json=summary['metadata']
        )
        
        # También guardar en daily_summaries para que otros agentes
        # puedan consultarla via jarvis_bridge.py synthesis
        try:
            save_daily_summary(
                summary['date'],
                summary['title'],
                summary['content'],
                summary['metadata'],
            )
        except Exception as e:
            print(f"  ⚠️  No se pudo guardar daily_summary: {e}")
        
        return True
    except Exception as e:
        print(f"[WARN] No se pudo sincronizar memoria: {e}")
        return False


def send_memory_summary():
    """Enviar resumen de memoria compartida a Telegram."""
    try:
        import sys
        sys.path.insert(0, str(SCRIPT_DIR))
        from agent_memory import get_all_agents_memory_summary
        
        print(f"  📝 Generando resumen de memoria compartida...")
        summary = get_all_agents_memory_summary('SIMMOON', days=7)
        
        # Formatear para Telegram (max 4000 chars)
        if len(summary) > 4000:
            summary = summary[:4000] + "\n\n…(truncado)"
        
        header = "🧠 *RESUMEN DE MEMORIA COMPARTIDA*\n"
        header += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if send_telegram(header + summary):
            print(f"  ✅ Resumen de memoria enviado a Telegram")
            if _LOG_OK:
                syslog("Agatha Actas", "🧠", "Resumen de memoria compartida enviado")
            return True
        else:
            print(f"  ❌ Error al enviar resumen de memoria")
            return False
    except ImportError:
        print(f"  ⚠️  agent_memory.py no disponible")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


# ── PostgreSQL: Daily Summaries ───────────────────────────────────────────
def get_db_conn():
    """Get PostgreSQL connection."""
    try:
        try:
            import psycopg
            return psycopg.connect(host="localhost", port=5432, dbname="simmoon", user="postgres")
        except ImportError:
            import psycopg2
            return psycopg2.connect(host="localhost", port=5432, database="simmoon", user="postgres")
    except Exception as e:
        print(f"[WARN] PostgreSQL no disponible: {e}")
        return None


def save_daily_summary(summary_date: str, title: str, content: str, metadata: dict) -> bool:
    """Save or update a daily summary in PostgreSQL."""
    conn = get_db_conn()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO daily_summaries 
                (summary_date, title, content, assets_created, assets_total,
                 services_active, services_total, agents_active, agents_total,
                 alerts_count, tags, project, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (summary_date) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                assets_created = EXCLUDED.assets_created,
                assets_total = EXCLUDED.assets_total,
                services_active = EXCLUDED.services_active,
                services_total = EXCLUDED.services_total,
                agents_active = EXCLUDED.agents_active,
                agents_total = EXCLUDED.agents_total,
                alerts_count = EXCLUDED.alerts_count,
                updated_at = NOW()
        """, (
            summary_date, title, content,
            metadata.get('assets_created', 0),
            metadata.get('assets_total', 0),
            metadata.get('services_active', 0),
            metadata.get('services_total', 0),
            metadata.get('agents_active', 0),
            metadata.get('agents_total', 0),
            metadata.get('alerts_count', 0),
            metadata.get('tags', []),
            'SIMMOON',
            'Agatha Actas',
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo guardar daily_summary: {e}")
        if conn:
            conn.close()
        return False


def get_recent_summaries(days: int = 7) -> list:
    """Get recent daily summaries from PostgreSQL. Returns list of dicts.
    
    Returns:
        List of {'date', 'title', 'content', 'assets_created', 'agents_active', ...}
    """
    conn = get_db_conn()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT summary_date, title, content, assets_created, assets_total,
                   services_active, services_total, agents_active, agents_total,
                   alerts_count, tags
            FROM daily_summaries
            WHERE summary_date >= CURRENT_DATE - (%s || ' days')::INTERVAL
            ORDER BY summary_date DESC
        """, (str(days),))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [
            {
                "date": row[0],
                "title": row[1],
                "content": row[2],
                "assets_created": row[3],
                "assets_total": row[4],
                "services_active": row[5],
                "services_total": row[6],
                "agents_active": row[7],
                "agents_total": row[8],
                "alerts_count": row[9],
                "tags": row[10] or [],
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[WARN] No se pudieron leer summaries: {e}")
        if conn:
            conn.close()
        return []


def generate_daily_summary() -> dict:
    """Generate a daily summary from recent activity logs.
    
    Returns dict with: date, title, content, metadata
    """
    from system_logger import get_recent
    
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    
    # Get last 24h of logs
    logs = get_recent(48)
    
    # Analyze activity
    report_count = sum(1 for e in logs if e.get('source') == 'Agatha Actas')
    
    # Get system state
    system = {}
    if _MONITOR_OK:
        system = collect_report()
    
    # Count assets by scanning directories
    asset_categories = [
        "businesses", "vehicles", "greenhouses", "solar_energy",
        "lunar_map", "buildings_misc", "lunar_sites", "ui_elements",
        "roads", "decorations", "characters", "lunar_flora", "infrastructure",
    ]
    total_assets = 0
    for cat in asset_categories:
        cat_dir = SCRIPT_DIR / cat
        if cat_dir.is_dir():
            total_assets += len(list(cat_dir.glob("*.png")))
    
    # Services status
    services = system.get("services", {})
    services_active = sum(1 for s in services.values() if s.get('healthy'))
    
    # Agents status
    agents_status = [
        ("Telegram Bot", check_windows_process("telegram_bot") or check_tmux_session("telegram-bot")),
        ("Hermes Agent", check_http("http://localhost:9119", timeout=2)),
        ("OpenHuman", check_http("http://localhost:7788", timeout=2)),
    ]
    agents_active = sum(1 for _, running in agents_status if running)
    
    # Alerts
    alerts = system.get("alerts", [])
    
    # Generate content summary
    lines = []
    lines.append(f"📊 *Resumen del {now.strftime('%Y-%m-%d')}*")
    lines.append("")
    lines.append(f"🔔 *Actividad:*")
    lines.append(f"  • Reportes enviados por Agatha: {report_count}")
    lines.append(f"  • Assets en sistema: {total_assets}")
    lines.append(f"  • Servicios activos: {services_active}/{len(services)}")
    lines.append(f"  • Agentes IA activos: {agents_active}/{len(agents_status)}")
    if alerts:
        lines.append(f"  • Alertas: {len(alerts)}")
    
    lines.append("")
    lines.append(f"🟢 *Servicios:*")
    for name, svc in services.items():
        icon = "✅" if svc.get('healthy') else "❌"
        lines.append(f"  {icon} {name}")
    
    lines.append("")
    lines.append(f"🤖 *Agentes:*")
    for name, running in agents_status:
        icon = "✅" if running else "❌"
        lines.append(f"  {icon} {name}")
    
    if alerts:
        lines.append("")
        lines.append(f"🚨 *Alertas ({len(alerts)}):*")
        for a in alerts[:3]:
            lines.append(f"  • {a}")
    
    lines.append("")
    lines.append(f"_Generado por Agatha Actas · {now.strftime('%H:%M')}_")
    
    content = "\n".join(lines)
    title = f"Resumen SIMMOON {today}"
    
    metadata = {
        "assets_created": report_count,  # reports = activity indicator
        "assets_total": total_assets,
        "services_active": services_active,
        "services_total": len(services),
        "agents_active": agents_active,
        "agents_total": len(agents_status),
        "alerts_count": len(alerts),
        "tags": ["daily", "agatha", "sistema"],
    }
    
    return {
        "date": today,
        "title": title,
        "content": content,
        "metadata": metadata,
    }


def send_daily_summary() -> bool:
    """Generate and send daily summary to Telegram + save to PostgreSQL."""
    print(f"  📝 Generando síntesis diaria...")
    
    summary = generate_daily_summary()
    
    # Save to PostgreSQL
    saved = save_daily_summary(
        summary['date'],
        summary['title'],
        summary['content'],
        summary['metadata'],
    )
    if saved:
        print(f"  ✅ Resumen guardado en PostgreSQL")
    else:
        print(f"  ⚠️  No se pudo guardar en PostgreSQL (¿está corriendo?)")
    
    # Send to Telegram
    print(f"  📤 Enviando síntesis a Telegram...")
    if send_telegram(summary['content']):
        print(f"  ✅ Síntesis diaria enviada")
        
        # Log the event
        if _LOG_OK:
            syslog("Agatha Actas", "📝", f"Síntesis diaria enviada: {summary['title']}")
        
        return True
    else:
        print(f"  ❌ Error al enviar síntesis a Telegram")
        return False


# ── Main ──────────────────────────────────────────────────────────────────
def setup():
    """Setup Agatha: discover chat ID and save config."""
    print("\n  📋 Agatha Actas — Setup")
    print("  " + "=" * 40)
    print("  Envía un mensaje a @Jeremias_Hermesai_bot en Telegram")
    print("  y presiona Enter cuando esté listo...")
    input("  > ")

    chat_id = discover_chat_id()
    if not chat_id:
        print("\n  ❌ No se encontró chat. Asegúrate de haber enviado")
        print("     un mensaje a @Jeremias_Hermesai_bot primero.\n")
        return False

    cfg = load_config()
    cfg["chat_id"] = chat_id
    save_config(cfg)

    # Send a test message
    print("\n  📤 Enviando mensaje de prueba...")
    test_msg = (
        "📋 *Agatha Actas — Configurada* ✅\n\n"
        "A partir de ahora recibirás reportes periódicos "
        "del sistema SIMMOON (cada 4h) con:\n"
        "📊 Estado del sistema\n"
        "🔌 Servicios backend\n"
        "🤖 Agentes IA\n"
        "🖼️ Actividad de generación\n"
        "🚨 Alertas\n\n"
        "_Powered by Agatha Actas_ 🤖"
    )
    if send_telegram(test_msg):
        print("  ✅ Mensaje de prueba enviado correctamente!\n")
    else:
        print(f"  ⚠️  No se pudo enviar prueba. Revisa que el bot pueda enviarte mensajes.\n")

    return True


def send_report():
    """Collect data and send one report."""
    if not _MONITOR_OK:
        print(f"[ERROR] monitor_sistema.py no disponible: {_MONITOR_ERR}")
        return False

    print(f"  📋 Recopilando datos del sistema...")
    data = collect_activity()
    print(f"  📤 Enviando reporte...")
    report = format_report(data)

    if send_telegram(report):
        print(f"  ✅ Reporte enviado a las {data['timestamp']}")

        # Log the event
        if _LOG_OK:
            agent_count = data.get('agent_running', 0)
            syslog("Agatha Actas", "📋", f"Reporte periódico enviado · {agent_count} agente(s) activo(s)")

        # Save last report time
        cfg = load_config()
        cfg["last_report"] = data["timestamp"]
        save_config(cfg)
        return True
    else:
        print(f"  ❌ Error al enviar reporte")
        return False


def daemon_loop(interval: int = DEFAULT_INTERVAL):
    """Run in daemon mode: report every interval seconds."""
    print(f"\n  📋 Agatha Actas — Modo Demonio")
    print(f"  ⏱️  Intervalo: cada {interval // 3600} horas ({interval // 60} minutos)")
    print(f"  📤 Reportes a: @Jeremias_Hermesai_bot")
    print(f"  🧠 Sync de memorias: automático")
    print(f"  {'='*50}")
    print(f"  Presiona Ctrl+C para detener.\n")

    # Sync counter for periodic Hermes <-> OpenHuman sync
    sync_counter = 0
    SYNC_INTERVAL = 4  # Sync Hermes<->OpenHuman every 4 reports (4 hours)

    # Send first report immediately
    send_report()
    
    # Initial memory sync
    print(f"  🔄 Sincronizando memorias iniciales...")
    sync_memory_to_agents()

    while True:
        next_time = time.time() + interval
        next_str = datetime.fromtimestamp(next_time).strftime("%H:%M:%S")
        print(f"\n  ⏳ Próximo reporte a las {next_str}...\n")

        # Sleep in chunks to allow Ctrl+C
        try:
            while time.time() < next_time:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n  🛑 Demonio detenido por el usuario.\n")
            break

        # Send report
        send_report()
        
        # Sync memory to PostgreSQL
        sync_counter += 1
        print(f"\n  🔄 Sincronizando memorias (reporte #{sync_counter})...")
        sync_memory_to_agents()
        
        # Supervise factory every 2 reports
        if sync_counter % 2 == 0:
            print(f"\n  🏭 Supervisando puestos de trabajo FactoryGames...")
            try:
                results = supervise_agents()
                active = sum(1 for r in results if r["running"])
                total = len(results)
                print(f"     {active}/{total} puestos activos")
                
                # Check for critical issues
                suggestions = coordinate_tasks(results)
                critical = [s for s in suggestions if s["priority"] == "crítica"]
                if critical:
                    print(f"     🚨 {len(critical)} problemas críticos detectados:")
                    for c in critical:
                        print(f"        • {c['action']}")
                    # Send critical alert to Telegram
                    alert_text = f"🚨 *FACTORYGAMES — Alerta Crítica*\n\n"
                    for c in critical:
                        alert_text += f"• {c['action']}\n"
                    send_telegram(alert_text)
                
                if _LOG_OK:
                    syslog("Agatha Actas", "🏭", f"Supervisión: {active}/{total} activos")
            except Exception as e:
                print(f"     ⚠️  Error en supervisión: {e}")
        
        # Send factory report to Telegram every 4 reports
        if sync_counter % 4 == 0:
            print(f"\n  📤 Enviando reporte de supervisión a Telegram...")
            try:
                report = format_factory_report()
                if send_telegram(report):
                    print(f"     ✅ Reporte de supervisión enviado")
            except Exception as e:
                print(f"     ⚠️  Error al enviar reporte: {e}")
        
        # Periodic Hermes <-> OpenHuman sync (every SYNC_INTERVAL reports)
        if _SYNC_OK and sync_counter % SYNC_INTERVAL == 0:
            print(f"  🔄 Sync Hermes <-> OpenHuman...")
            try:
                h2o = sync_hermes_to_openhuman()
                o2h = sync_openhuman_to_hermes()
                print(f"     Hermes->OpenHuman: {'✅' if h2o else '⚠️  (sin cambios)'}")
                print(f"     OpenHuman->Hermes: {'✅' if o2h else '⚠️  (sin cambios)'}")
            except Exception as e:
                print(f"     ❌ Error en sync: {e}")
            sync_counter = 0  # Reset after sync
            
            # Log only on sync events
            if _LOG_OK:
                syslog("Agatha Actas", "🧠", f"Sync Hermes<->OpenHuman completado")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Agatha Actas — Agente de Reportes Periódicos y Síntesis Diarias"
    )
    parser.add_argument("--setup", action="store_true", help="Configurar chat ID")
    parser.add_argument("--test", action="store_true", help="Enviar reporte de prueba ahora")
    parser.add_argument("--daemon", action="store_true", help="Modo demonio (cada 4h por defecto)")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="Intervalo en segundos (default: 14400 = 4 horas)")
    parser.add_argument("--daily-summary", action="store_true",
                        help="Generar y enviar síntesis del día actual")
    parser.add_argument("--synthesis", action="store_true",
                        help="Mostrar síntesis de los últimos días (para agentes)")
    parser.add_argument("--days", type=int, default=7,
                        help="Días a mostrar en synthesis (default: 7)")
    parser.add_argument("--json", action="store_true",
                        help="Salida en JSON para consumo por otros agentes")
    
    # ── Supervisor flags ──
    parser.add_argument("--supervise", action="store_true",
                        help="Supervisar todos los puestos de trabajo de FactoryGames")
    parser.add_argument("--workstations", action="store_true",
                        help="Mostrar vista de piso de fábrica")
    parser.add_argument("--factory", action="store_true",
                        help="Reporte completo de supervisión (estado + sugerencias)")
    parser.add_argument("--coordinate", action="store_true",
                        help="Sugerir próximas tareas según estado de la fábrica")
    parser.add_argument("--supervise-report", action="store_true",
                        help="Enviar reporte de supervisión a Telegram")
    args = parser.parse_args()

    if args.setup:
        setup()
        return

    if args.test:
        send_report()
        return

    if args.daemon:
        cfg = load_config()
        if not cfg.get("chat_id"):
            print("[ERROR] No hay chat_id configurado. Ejecuta primero:")
            print("  python agatha_actas.py --setup")
            sys.exit(1)        # Usar intervalo del config si no se paso --interval explicitamente
        if '--interval' not in sys.argv and not any(a.startswith('--interval=') for a in sys.argv):
            args.interval = cfg.get("interval", DEFAULT_INTERVAL)
        daemon_loop(args.interval)
        return

    if args.daily_summary:
        send_daily_summary()
        return

    # ── Supervisor handlers ──
    if args.workstations:
        print(factory_floor_overview())
        return
    
    if args.coordinate:
        suggestions = coordinate_tasks()
        print(f"\n  🔍 Sugerencias de coordinación ({len(suggestions)}):")
        print(f"  {'='*60}")
        for s in sorted(suggestions, key=lambda x: {"crítica": 0, "alta": 1, "media": 2, "baja": 3}.get(x["priority"], 4)):
            p_icon = {"crítica": "🚨", "alta": "⏫", "media": "🔶", "baja": "ℹ️"}.get(s["priority"], "•")
            print(f"\n  {p_icon} [{s['priority'].upper()}] {s['area']}")
            print(f"     {s['action']}")
            if s.get("command"):
                print(f"     → {s['command']}")
        print()
        return
    
    if args.factory or args.supervise:
        results = supervise_agents()
        print(factory_floor_overview(results))
        print()
        suggestions = coordinate_tasks(results)
        print(f"  🔍 Sugerencias ({len(suggestions)}):")
        for s in sorted(suggestions, key=lambda x: {"crítica": 0, "alta": 1, "media": 2, "baja": 3}.get(x["priority"], 4)):
            p_icon = {"crítica": "🚨", "alta": "⏫", "media": "🔶", "baja": "ℹ️"}.get(s["priority"], "•")
            print(f"  {p_icon} [{s['priority'].upper()}] {s['action']}")
        print()
        return
    
    if args.supervise_report:
        report = format_factory_report()
        print(f"  📤 Enviando reporte de supervisión a Telegram...")
        if send_telegram(report):
            print(f"  ✅ Reporte de supervisión enviado")
            if _LOG_OK:
                syslog("Agatha Actas", "🏭", "Reporte de supervisión enviado")
        else:
            print(f"  ❌ Error al enviar reporte de supervisión")
        return
    
    if args.synthesis:
        summaries = get_recent_summaries(args.days)
        
        if args.json:
            # Salida JSON para consumo por otros agentes
            output = {
                "ok": True,
                "days": args.days,
                "summaries": summaries,
                "count": len(summaries),
            }
            print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
        else:
            print("\n  📝 Síntesis de los últimos días:")
            print("  " + "=" * 50)
            if summaries:
                for s in summaries:
                    print(f"\n  📅 {s['date']}: {s['title']}")
                    print(f"     Assets: {s['assets_total']} | Agentes: {s['agents_active']}/{s['agents_total']}")
            else:
                print("  (No hay síntesis disponibles)")
            print()
        return

    # Default: show help
    parser.print_help()
    print("\n  Ejemplos:")
    print("    python agatha_actas.py --setup              # Configurar")
    print("    python agatha_actas.py --test               # Reporte de prueba")
    print("    python agatha_actas.py --daemon --interval 4   # Iniciar demonio (cada 4h)")
    print("    python agatha_actas.py --daemon               # Iniciar demonio "
          "(default: 4h)")
    print("    python agatha_actas.py --daily-summary        # Generar síntesis del día")
    print("    python agatha_actas.py --synthesis          # Ver síntesis de días anteriores")
    print("    python agatha_actas.py --factory            # Supervisor: piso de fábrica + sugerencias")
    print("    python agatha_actas.py --workstations       # Solo vista de puestos")
    print("    python agatha_actas.py --coordinate         # Solo sugerencias")
    print("    python agatha_actas.py --supervise-report   # Enviar reporte a Telegram\n")


if __name__ == "__main__":
    main()
