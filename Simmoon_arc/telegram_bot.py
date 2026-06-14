#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMMOON Telegram Bot — Multi-Agent Bridge 🤖

Conecta Telegram a todos los agentes del ecosistema SIMMOON:
  - 🤖 Buffy   → Asistente Codebuff (programación, debugging, gestión)
  - 🧠 Ollama  → Chat con IA local (estilo Jarvis)
  - 🧠 Hermes  → Bridge al agente Hermes (Nous Research)
  - 🤖 OpenHuman → API REST (si está disponible)
  - 📊 Monitor  → Estado del sistema, servicios, GPU

Comandos:
  /start   — Saludo de bienvenida
  /help    — Lista de comandos disponibles
  /status  — Reporte completo del sistema
  /agents  — Agentes disponibles y su estado
  /services — Estado de servicios backend
  /gpu     — Info de GPU en tiempo real
  /gpu_free — Liberar VRAM (descarga Ollama para ComfyUI)
  /gpu_restore — Restaurar Ollama a GPU
  /gen    — Generar imagen con orquestación GPU
  /ai      — Chat con IA vía Ollama (responde al mensaje siguiente)
  /buffy   — Chat con Buffy (Codebuff AI, programación y asistencia)
  /model   — Cambiar modelo de IA (admin)

Uso:
    python Simmoon_arc/telegram_bot.py            # Inicia el bot
    python Simmoon_arc/telegram_bot.py --setup    # Setup inicial
"""

import asyncio
import json
import os
import re
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp1252", "cp850"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

# ── Telegram ───────────────────────────────────────────────────────────────
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

# ── Config ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "telegram_config.json"
DEFAULT_CONFIG = {
    "telegram_token": "",
    "bot_name": "SIMMOON Bot",
    "allowed_users": [],
    "ollama_model": "qwen25-64k",
    "ollama_url": "http://127.0.0.1:11434",
    "openhuman_url": "http://localhost:7788",
    "hermes_model": "qwen25-64k",
    "buffy_model": "qwen25-64k",
}

# ── Buffy System Prompt ────────────────────────────────────────────────────
BUFFY_SYSTEM_PROMPT = """Eres Buffy, la asistente estratégica de Codebuff — una CLI que permite a los usuarios
chatear con IA para programar. Estás respondiendo a través de Telegram como el puente
personal del usuario Jeremi.

TU PERSONALIDAD:
- Profesional, directa y concisa (estilo CLI, no verboso)
- Amigable pero eficiente — vas al grano
- Hablas en español con naturalidad
- Tienes conocimiento técnico profundo sobre programación, DevOps, y el ecosistema SIMMOON
- Eres proactiva: si detectas un problema, lo mencionas y sugieres soluciones

EL ECOSISTEMA SIMMOON:
- Eres parte del proyecto SIMMOON, una fábrica de assets con IA
- Conoces los agentes: Hermes, Jarvis, OpenHuman, Agatha
- Sabes de los servicios: Ollama, ComfyUI, InvokeAI, PostgreSQL
- El proyecto genera imágenes pixel art estilo SimCity 2000

TU TRABAJO AQUÍ:
- Responder mensajes de Telegram de Jeremi
- Ayudar con código, debugging, ideas del proyecto
- Monitorear el sistema si te lo piden
- Ser el puente entre Jeremi y el ecosistema de IAs

REGLAS:
- Responde en español SIEMPRE
- Sé concisa (1-3 párrafos máximo, a menos que se necesite más detalle)
- Si no sabes algo, dilo honestamente
- Usa emojis con moderación
- Para comandos técnicos, usa formato `código`
"""


def load_config() -> dict:
    """Load bot configuration.

    Priority:
      1. TELEGRAM_BOT_TOKEN environment variable (overrides config file)
      2. telegram_config.json file
      3. DEFAULT_CONFIG defaults
    """
    cfg = dict(DEFAULT_CONFIG)

    # Load from config file
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
                cfg.update(file_cfg)
        except (json.JSONDecodeError, OSError):
            pass

    # Environment variable overrides token (more secure)
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if env_token:
        cfg["telegram_token"] = env_token

    # Other env var overrides
    env_ollama_url = os.environ.get("OLLAMA_URL", "")
    if env_ollama_url:
        cfg["ollama_url"] = env_ollama_url

    env_ollama_model = os.environ.get("OLLAMA_MODEL", "")
    if env_ollama_model:
        cfg["ollama_model"] = env_ollama_model

    return cfg


def save_config(cfg: dict):
    """Save bot configuration to telegram_config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── Ollama Integration ────────────────────────────────────────────────────
async def ollama_chat(model: str, prompt: str, system: Optional[str] = None,
                      temperature: float = 0.7, max_tokens: int = 500,
                      ollama_url: str = "http://127.0.0.1:11434") -> str:
    """Send a chat message to Ollama and return the response."""
    import urllib.request
    import json as j

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    data = j.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=120)
        )
        result = j.loads(resp.read().decode("utf-8"))
        return result.get("message", {}).get("content", "...") or "..."
    except Exception as e:
        return f"[ERROR] Ollama no responde: {e}"


async def ollama_list_models(ollama_url: str = "http://127.0.0.1:11434") -> list:
    """List available models from Ollama."""
    import urllib.request
    import json as j

    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(
                f"{ollama_url}/api/tags", timeout=10
            )
        )
        data = j.loads(resp.read().decode("utf-8"))
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ── GPU Orchestrator ─────────────────────────────────────────────────────
# Gestiona la VRAM de la RTX 4070 (8GB) entre Ollama y ComfyUI.
# Principio: solo uno puede usar GPU a la vez. El orquestador de Telegram
# actúa como gestor: cuando el carril de arte está activo, Ollama hace
# overflow a RAM (32GB). Cuando termina arte, libera GPU.

async def unload_ollama_model(model: str, ollama_url: str) -> bool:
    """Descarga el modelo de Ollama de la VRAM enviando keep_alive=0.

    Más elegante que matar `ollama serve`: mantiene el servicio vivo
    pero libera la VRAM instantáneamente para ComfyUI.
    """
    import urllib.request
    import json as j

    payload = {"model": model, "prompt": ".", "keep_alive": 0,
              "options": {"num_predict": 1}}
    data = j.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: urllib.request.urlopen(req, timeout=15)
        )
        return True
    except (socket.timeout, TimeoutError):
        # Timeout esperado: keep_alive=0 se procesa async.
        # La request se envió → Ollama descargará el modelo.
        return True
    except Exception as e:
        print(f"[ORCH] Error descargando Ollama: {e}", file=sys.stderr)
        return False


async def is_comfyui_busy(comfyui_url: str = "http://localhost:8188") -> bool:
    """Verifica si ComfyUI está generando imágenes (cola activa)."""
    import urllib.request
    import json as j

    try:
        req = urllib.request.Request(f"{comfyui_url}/queue", method="GET")
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=5)
        )
        result = j.loads(resp.read().decode("utf-8"))
        return len(result.get("queue_running", [])) > 0 or len(result.get("queue_pending", [])) > 0
    except Exception:
        return False  # Si no responde, asumimos libre


async def wait_for_comfyui(comfyui_url: str = "http://localhost:8188",
                           timeout: int = 120) -> bool:
    """Espera asíncronamente hasta que ComfyUI esté libre."""
    start = time.time()
    while await is_comfyui_busy(comfyui_url):
        if time.time() - start > timeout:
            return False
        await asyncio.sleep(2)
    return True


async def get_gpu_vram_used() -> int:
    """Devuelve VRAM usada en MB vía nvidia-smi, o -1 si falla."""
    import subprocess

    try:
        loop = asyncio.get_event_loop()
        out = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
        )
        if out.returncode == 0:
            return int(out.stdout.strip())
    except Exception:
        pass
    return -1


# ── Hermes Bridge Integration ────────────────────────────────────────────
async def hermes_bridge_chat(prompt: str, model: str = "qwen2.5:3b",
                              timeout: int = 60) -> str:
    """Connect to Hermes Agent via hermes_bridge.py."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from hermes_bridge import HermesBridge

        bridge = HermesBridge(model=model, verbose=False)
        if not bridge.hermes_path:
            return "[SKIP] Hermes binary no encontrado"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: bridge.chat(prompt, max_turns=5, timeout=timeout),
        )
        return response
    except ImportError:
        return "[SKIP] hermes_bridge.py no disponible"
    except Exception as e:
        return f"[ERROR] Hermes bridge: {e}"


# ── OpenHuman Integration ─────────────────────────────────────────────────
async def openhuman_chat(prompt: str, base_url: str = "http://localhost:7788",
                          timeout: int = 30) -> str:
    """Send a message to OpenHuman via its REST API."""
    import urllib.request
    import json as j

    payload = {
        "message": prompt,
        "stream": False,
    }
    data = j.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=timeout)
        )
        result = j.loads(resp.read().decode("utf-8"))
        return result.get("response", result.get("message", "(sin respuesta)"))
    except Exception as e:
        return f"[SKIP] OpenHuman no disponible en {base_url}: {e}"


# ── System Monitor Integration ──────────────────────────────────────────
async def get_system_status() -> dict:
    """Get system health report via monitor_sistema.py."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from monitor_sistema import collect_report
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, collect_report)
        return report
    except ImportError:
        return {"error": "monitor_sistema.py no disponible"}
    except Exception as e:
        return {"error": str(e)}


async def get_system_status_formatted() -> str:
    """Get a formatted system status string for Telegram."""
    report = await get_system_status()

    if "error" in report:
        return f"❌ Error al obtener estado: {report['error']}"

    lines = []
    lines.append("📊 *SIMMOON — Estado del Sistema*\n")

    # GPU
    gpu = report.get("gpu", {})
    if gpu.get("available"):
        lines.append(f"🎮 *GPU:* {gpu.get('name', 'N/A')}")
        lines.append(f"   Temp: {gpu.get('temperature_c', '?')}°C  |  "
                      f"VRAM: {gpu.get('memory_used_mb', 0)}/{gpu.get('memory_total_mb', 0)}MB "
                      f"({gpu.get('memory_used_percent', 0)}%)")
    else:
        lines.append("🎮 *GPU:* ❌ No detectada")

    # RAM
    ram = report.get("ram", {})
    if ram.get("total_gb"):
        icon = "⚠️" if ram.get("used_percent", 0) > 85 else "🟢"
        lines.append(f"\n🧠 *RAM:* {icon} {ram.get('used_gb', 0)}/{ram.get('total_gb', 0)}GB "
                      f"({ram.get('used_percent', 0)}%)")

    # Disk
    disk = report.get("disk", {})
    for mount, info in disk.items():
        icon = "⚠️" if info.get("available_gb", 100) < 50 else "💾"
        lines.append(f"\n{icon} *Disco {mount}:* {info.get('available_gb', 0)}GB libre "
                      f"de {info.get('total_gb', 0)}GB")

    # Services
    lines.append(f"\n🔌 *Servicios:*")
    services = report.get("services", {})
    for name, svc in services.items():
        icon = "✅" if svc.get("healthy") else "❌"
        latency = svc.get("latency_ms", 0)
        lines.append(f"   {icon} {name}: {latency}ms")

    # Alerts
    alerts = report.get("alerts", [])
    if alerts:
        lines.append(f"\n🚨 *Alertas ({len(alerts)}):*")
        for a in alerts[:5]:
            lines.append(f"   {a}")

    # Timestamp
    ts = report.get("timestamp", datetime.now().isoformat())
    lines.append(f"\n📅 _{ts}_")

    return "\n".join(lines)


async def get_gpu_info() -> str:
    """Get GPU information only."""
    report = await get_system_status()
    gpu = report.get("gpu", {})

    if not gpu.get("available"):
        return "🎮 *GPU:* ❌ No detectada o nvidia-smi no disponible"

    lines = []
    lines.append(f"🎮 *GPU:* {gpu.get('name', 'N/A')}")
    lines.append(f"   • Driver: {gpu.get('driver_version', 'N/A')}")
    lines.append(f"   • Temp: {gpu.get('temperature_c', '?')}°C")
    lines.append(f"   • VRAM: {gpu.get('memory_used_mb', 0)}/{gpu.get('memory_total_mb', 0)}MB "
                  f"({gpu.get('memory_used_percent', 0)}%)")
    lines.append(f"   • Util: {gpu.get('utilization_gpu_percent', 0)}%")
    if gpu.get("fan_speed_percent", 0) > 0:
        lines.append(f"   • Fan: {gpu.get('fan_speed_percent', 0)}%")
    if gpu.get("power_draw_watts", 0) > 0:
        lines.append(f"   • Power: {gpu.get('power_draw_watts', 0)}W / "
                      f"{gpu.get('power_limit_watts', 0)}W")

    processes = gpu.get("processes", [])
    if processes:
        lines.append(f"\n   *Procesos:*")
        for p in processes[:5]:
            lines.append(f"   • {p.get('name', '?')} (PID {p.get('pid', '?')}, "
                          f"{p.get('memory_mb', 0)}MB)")

    return "\n".join(lines)


# ── Service Status ────────────────────────────────────────────────────────
async def get_service_status() -> str:
    """Get a quick service status overview."""
    report = await get_system_status()
    services = report.get("services", {})

    lines = []
    lines.append("🔌 *Estado de Servicios*\n")

    service_info = {
        "ollama": ("🧠 Ollama", ":11434"),
        "comfyui": ("🎨 ComfyUI", ":8188"),
        "openhuman": ("🤖 OpenHuman", ":7788"),
        "jarvis": ("💬 Jarvis", "CLI"),
        "hermes": ("🧠 Hermes", ":9119"),
        "postgresql": ("🗄️ PostgreSQL", ":5432"),
        "comfyui": ("🎨 ComfyUI", ":8188"),
    }

    for name, svc in services.items():
        label, port = service_info.get(name, (name, ""))
        icon = "✅" if svc.get("healthy") else "❌"
        latency = svc.get("latency_ms", 0)
        extra = ""
        if name == "ollama" and "model_count" in svc:
            extra = f"  |  {svc['model_count']} modelos"
        lines.append(f"   {icon} {label} {port}  [{latency}ms]{extra}")

    # Add agents
    lines.append(f"\n🤖 *Agentes Python:*")
    agents = [
        ("simmoon_agent.py", "AI Director"),
        ("simmoon_autogen.py", "Multi-Agent Design"),
        ("simmoon_pipeline.py", "LangGraph Pipeline"),
        ("telegram_bot.py", "🤖 Telegram Bot ✅" ),
    ]
    for agent_file, desc in agents:
        path = SCRIPT_DIR / agent_file
        icon = "✅" if path.exists() else "❌"
        lines.append(f"   {icon} {desc}")

    return "\n".join(lines)


async def get_agent_status() -> str:
    """Get status of all available AI agents."""
    config = load_config()
    lines = []
    lines.append("🤖 *Agentes Disponibles*\n")

    # 1. Ollama
    models = await ollama_list_models(config["ollama_url"])
    if models:
        lines.append("✅ *🧠 Ollama* — Chat IA local")
        lines.append(f"   Modelos: {', '.join(models[:5])}")
        if len(models) > 5:
            lines.append(f"   ... y {len(models) - 5} más")
        lines.append(f"   Modelo activo: `{config['ollama_model']}`")
    else:
        lines.append("❌ *🧠 Ollama* — No disponible")

    # 2. Hermes Bridge
    lines.append("")
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from hermes_bridge import _find_hermes
        hermes_path = _find_hermes()
        if hermes_path:
            lines.append(f"✅ *🧠 Hermes Bridge* — {hermes_path}")
        else:
            lines.append("❌ *🧠 Hermes Bridge* — Binario no encontrado")
    except ImportError:
        lines.append("⚠️ *🧠 Hermes Bridge* — Módulo no disponible")

    # 3. OpenHuman
    lines.append("")
    try:
        import urllib.request
        import json as j
        loop = asyncio.get_event_loop()
        req = urllib.request.Request(f"{config['openhuman_url']}/health", method="GET")
        resp = await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=5)
        )
        if resp.status < 500:
            lines.append(f"✅ *🤖 OpenHuman* — {config['openhuman_url']}")
        else:
            lines.append(f"❌ *🤖 OpenHuman* — No responde")
    except Exception:
        lines.append("⚠️ *🤖 OpenHuman* — No disponible")

    # 4. System Monitor
    lines.append("")
    if (SCRIPT_DIR / "monitor_sistema.py").exists():
        lines.append("✅ *📊 Monitor Sistema* — Reportes de salud")
    else:
        lines.append("❌ *📊 Monitor Sistema* — No disponible")

    return "\n".join(lines)


# ── Telegram Command Handlers ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message — greet the user warmly."""
    user = update.effective_user
    first_name = user.first_name or "Humano"

    welcome_text = (
        f"👋 *¡Hola {first_name}! Bienvenido al bot {context.bot.first_name}* 🤖\n\n"
        f"Soy el puente multi-agente del ecosistema *SIMMOON*. "
        f"Estoy aquí para conectarte con todas las IAs del sistema:\n\n"
        f"🤖 *Buffy* — Codebuff AI (respondo por defecto en chat libre)\n"
        f"🧠 *Ollama* — Chat con modelos locales\n"
        f"🧠 *Hermes* — Agente Nous Research\n"
        f"🤖 *OpenHuman* — Asistente con GUI\n"
        f"📊 *Monitor* — Salud del sistema\n\n"
        f"*Comandos principales:*\n"
        f"  /buffy <mensaje> — Hablar conmigo (Buffy) 🤖\n"
        f"  /help  — Todos los comandos disponibles\n"
        f"  /status — Estado del sistema\n"
        f"  /agents — Agentes disponibles\n"
        f"  /services — Servicios backend\n"
        f"  /ai <mensaje> — Chat con Hermes (estilo clásico)\n"
        f"  /gpu — Info de GPU\n"
        f"  /gpu\\_free — Liberar VRAM\n"
        f"  /gpu\\_restore — Restaurar Ollama a GPU\n"
        f"  /gen <prompt> — Generar imagen 🎨\n\n"
        f"¡Estoy listo para ayudarte! 🚀"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available commands."""
    help_text = (
        "📖 *Comandos Disponibles*\n\n"
        "🔹 *Información:*\n"
        "  /start — Saludo de bienvenida\n"
        "  /help — Esta ayuda\n\n"
        "🔹 *Sistema:*\n"
        "  /status — Reporte completo del sistema\n"
        "  /services — Estado de servicios backend\n"
        "  /gpu — Información de GPU\n"
        "  /agents — Agentes IA disponibles\n\n"
        "🔹 *GPU Orchestrator (VRAM 8GB):*\n"
        "  /gpu\\_free — Liberar VRAM (descarga Ollama)\n"
        "  /gpu\\_restore — Restaurar Ollama a GPU\n"
        "  /gen <prompt> — Generar imagen (orquestación auto)\n\n"
        "🔹 *Chat con IA:*\n"
        "  /buffy <mensaje> — Chat con Buffy (programación)\n"
        "  /ai <mensaje> — Chat con Ollama\n"
        "  /ai\\_jarvis <mensaje> — Chat estilo Jarvis\n"
        "  /ai\\_hermes <mensaje> — Chat vía Hermes bridge\n"
        "  /ai\\_human <mensaje> — Chat vía OpenHuman\n\n"
        "🔹 *Configuración:*\n"
        "  /model <nombre> — Cambiar modelo Ollama\n"
        "  /models — Listar modelos disponibles\n\n"
        "🔹 *Chat libre (Buffy por defecto):*\n"
        "  Envía cualquier mensaje y *Buffy* responderá\n"
        "  con su personalidad de Codebuff AI.\n\n"
        "¡Explora y disfruta! 🚀"
    )

    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full system health report."""
    msg = await update.message.reply_text(
        "📊 Recopilando estado del sistema... ⏳",
    )

    status_text = await get_system_status_formatted()
    await msg.edit_text(status_text, parse_mode="Markdown")


async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show service status."""
    msg = await update.message.reply_text(
        "🔌 Verificando servicios... ⏳",
    )

    services_text = await get_service_status()
    await msg.edit_text(services_text, parse_mode="Markdown")


async def cmd_gpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show GPU information."""
    msg = await update.message.reply_text(
        "🎮 Consultando GPU... ⏳",
    )

    gpu_text = await get_gpu_info()
    await msg.edit_text(gpu_text, parse_mode="Markdown")


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available AI agents."""
    msg = await update.message.reply_text(
        "🤖 Consultando agentes disponibles... ⏳",
    )

    agents_text = await get_agent_status()
    await msg.edit_text(agents_text, parse_mode="Markdown")


async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chat with AI via Ollama."""
    if not context.args:
        await update.message.reply_text(
            "✏️ *Uso:* `/ai <tu mensaje>`\n"
            "Ejemplo: `/ai Hola, ¿cómo estás?`",
            parse_mode="Markdown",
        )
        return

    prompt = " ".join(context.args)
    config = load_config()

    msg = await update.message.reply_text(
        f"🧠 Pensando... 🤔",
    )

    system = ("Eres Hermes, un asistente AI amigable y servicial del ecosistema "
              "SIMMOON. Responde en español de forma natural y conversacional. "
              "Eres el bot de Telegram que conecta todos los agentes de IA.")

    response = await ollama_chat(
        model=config["ollama_model"],
        prompt=prompt,
        system=system,
        ollama_url=config["ollama_url"],
    )

    # Cap response length for Telegram
    if len(response) > 4000:
        response = response[:4000] + "\n\n*(mensaje truncado)*"

    await msg.edit_text(
        f"🧠 *Hermes:*\n{response}",
        parse_mode="Markdown",
    )


async def cmd_ai_jarvis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chat in Jarvis style."""
    if not context.args:
        await update.message.reply_text(
            "✏️ *Uso:* `/ai_jarvis <tu mensaje>`",
            parse_mode="Markdown",
        )
        return

    prompt = " ".join(context.args)
    config = load_config()

    msg = await update.message.reply_text("💬 Consultando a Jarvis... 🤔")

    system = ("Eres Jarvis, un asistente AI CLI eficiente y directo. "
              "Responde en español de forma clara y concisa, "
              "como un asistente técnico profesional.")

    response = await ollama_chat(
        model=config["ollama_model"],
        prompt=prompt,
        system=system,
        temperature=0.5,
        ollama_url=config["ollama_url"],
    )

    if len(response) > 4000:
        response = response[:4000] + "\n\n*(mensaje truncado)*"

    await msg.edit_text(
        f"💬 *Jarvis:*\n{response}",
        parse_mode="Markdown",
    )


async def cmd_buffy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chat with Buffy — Codebuff AI assistant."""
    if not context.args:
        await update.message.reply_text(
            "🤖 *Buffy a tu servicio.*\n\n"
            "✏️ *Uso:* `/buffy <tu mensaje>`\n"
            "Ejemplo: `/buffy ¿cómo optimizo el pipeline de generación?`\n\n"
            "Puedes preguntarme sobre:\n"
            "  💻 Programación y debugging\n"
            "  🏭 Gestión de SIMMOON\n"
            "  📊 Estado del sistema\n"
            "  💡 Ideas y arquitectura",
            parse_mode="Markdown",
        )
        return

    prompt = " ".join(context.args)
    config = load_config()

    msg = await update.message.reply_text(
        f"🤖 Buffy está pensando... 💭",
    )

    response = await ollama_chat(
        model=config.get("buffy_model", config["ollama_model"]),
        prompt=prompt,
        system=BUFFY_SYSTEM_PROMPT,
        temperature=0.7,
        max_tokens=800,
        ollama_url=config["ollama_url"],
    )

    # Cap response length for Telegram
    if len(response) > 4000:
        response = response[:4000] + "\n\n*(mensaje truncado)*"

    await msg.edit_text(
        f"🤖 *Buffy:*\n{response}",
        parse_mode="Markdown",
    )


async def cmd_ai_hermes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chat via Hermes bridge."""
    if not context.args:
        await update.message.reply_text(
            "✏️ *Uso:* `/ai_hermes <tu mensaje>`",
            parse_mode="Markdown",
        )
        return

    prompt = " ".join(context.args)
    config = load_config()

    msg = await update.message.reply_text("🧠 Consultando a Hermes Agent... 🤔")

    response = await hermes_bridge_chat(
        prompt=prompt,
        model=config["hermes_model"],
    )

    if response.startswith("[SKIP]") or response.startswith("[ERROR]"):
        await msg.edit_text(
            f"⚠️ *Hermes Bridge:*\n{response}\n\n"
            f"Usando Ollama como fallback...",
            parse_mode="Markdown",
        )
        # Fallback to Ollama
        response = await ollama_chat(
            model=config["ollama_model"],
            prompt=prompt,
            system="Eres un asistente útil. Responde en español.",
            ollama_url=config["ollama_url"],
        )

    if len(response) > 4000:
        response = response[:4000] + "\n\n*(mensaje truncado)*"

    await msg.edit_text(
        f"🧠 *Hermes Agent:*\n{response}",
        parse_mode="Markdown",
    )


async def cmd_ai_human(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chat via OpenHuman."""
    if not context.args:
        await update.message.reply_text(
            "✏️ *Uso:* `/ai_human <tu mensaje>`",
            parse_mode="Markdown",
        )
        return

    prompt = " ".join(context.args)
    config = load_config()

    msg = await update.message.reply_text("🤖 Consultando a OpenHuman... 🤔")

    response = await openhuman_chat(
        prompt=prompt,
        base_url=config["openhuman_url"],
    )

    if response.startswith("[SKIP]") or "no disponible" in response:
        await msg.edit_text(
            f"⚠️ *OpenHuman:*\n{response}\n\n"
            f"Usando Ollama como fallback...",
            parse_mode="Markdown",
        )
        response = await ollama_chat(
            model=config["ollama_model"],
            prompt=prompt,
            system="Eres OpenHuman, un asistente AI con capacidades de GUI. Responde en español.",
            ollama_url=config["ollama_url"],
        )

    if len(response) > 4000:
        response = response[:4000] + "\n\n*(mensaje truncado)*"

    await msg.edit_text(
        f"🤖 *OpenHuman:*\n{response}",
        parse_mode="Markdown",
    )


async def cmd_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available Ollama models."""
    config = load_config()
    msg = await update.message.reply_text("📦 Consultando modelos... ⏳")

    models = await ollama_list_models(config["ollama_url"])

    if models:
        text = "📦 *Modelos Ollama Disponibles:*\n\n"
        for m in models:
            active = " ✅ *(activo)*" if m == config["ollama_model"] else ""
            text += f"   • `{m}`{active}\n"
        text += f"\nModelo activo: `{config['ollama_model']}`"
        text += f"\nCambiar con: `/model <nombre>`"
    else:
        text = "❌ No se pudo conectar a Ollama o no hay modelos instalados."

    await msg.edit_text(text, parse_mode="Markdown")


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change the active Ollama model."""
    if not context.args:
        config = load_config()
        await update.message.reply_text(
            f"📦 Modelo actual: `{config['ollama_model']}`\n"
            f"✏️ *Uso:* `/model <nombre>`\n"
            f"Ver modelos: `/models`",
            parse_mode="Markdown",
        )
        return

    model_name = " ".join(context.args)
    config = load_config()

    # Verify model exists
    models = await ollama_list_models(config["ollama_url"])
    if models and model_name not in models:
        similar = [m for m in models if model_name.lower() in m.lower() or m.lower() in model_name.lower()] or models[:5]
        text = (f"❌ Modelo `{model_name}` no encontrado.\n\n"
                f"Modelos disponibles:\n" +
                "\n".join(f"   • `{m}`" for m in similar[:10]))
        if len( similar) > 10:
            text += f"\n   ... y {len(similar) - 10} más"
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    config["ollama_model"] = model_name
    save_config(config)

    await update.message.reply_text(
        f"✅ Modelo cambiado a `{model_name}`\n\n"
        f"Ahora todas las conversaciones usarán este modelo.",
        parse_mode="Markdown",
    )


# ── GPU Orchestrator Command Handlers ─────────────────────────────────────

async def cmd_gpu_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Libera VRAM descargando el modelo de Ollama manualmente.

    Útil antes de lanzar ComfyUI manualmente o cuando necesitas
    toda la VRAM para generación de imágenes.
    """
    config = load_config()
    msg = await update.message.reply_text("🧹 Liberando VRAM de Ollama... ⏳")

    vram_before = await get_gpu_vram_used()
    success = await unload_ollama_model(config["ollama_model"], config["ollama_url"])
    await asyncio.sleep(0.5)
    vram_after = await get_gpu_vram_used()

    if success and vram_after > 0 and vram_before > 0:
        freed = max(0, vram_before - vram_after)
        text = (
            f"✅ *VRAM Liberada*\n"
            f"   Antes: {vram_before}MB → Ahora: {vram_after}MB "
            f"({freed}MB liberados)\n\n"
            f"_Ollama ha descargado el modelo. ComfyUI puede usar la GPU._"
        )
    elif success:
        text = "✅ *VRAM Liberada*: Ollama ha descargado el modelo."
    else:
        text = "❌ *Error*: No se pudo contactar con Ollama."

    await msg.edit_text(text, parse_mode="Markdown")


async def cmd_gpu_restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restaura VRAM precargando el modelo de Ollama."""
    config = load_config()
    msg = await update.message.reply_text("🔄 Restaurando Ollama a GPU... ⏳")

    vram_before = await get_gpu_vram_used()
    # Un request simple fuerza la recarga del modelo a GPU
    await ollama_chat(
        model=config["ollama_model"],
        prompt=".",
        max_tokens=1,
        ollama_url=config["ollama_url"],
    )
    await asyncio.sleep(1)
    vram_after = await get_gpu_vram_used()

    if vram_after > 0 and vram_before > 0:
        loaded = max(0, vram_after - vram_before)
        text = (
            f"✅ *VRAM Restaurada*\n"
            f"   VRAM: {vram_after}MB ({loaded}MB cargados)\n\n"
            f"_Ollama `{config['ollama_model']}` listo en GPU._"
        )
    else:
        text = "✅ *VRAM Restaurada*: Ollama está listo en GPU."

    await msg.edit_text(text, parse_mode="Markdown")


async def cmd_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /gen con orquestación automática de GPU.

    Flujo:
      1. Esperar que ComfyUI termine trabajos previos (anti-overlap)
      2. Liberar VRAM de Ollama (keep_alive=0)
      3. Lanzar generación en ComfyUI
      4. Reportar resultado (Ollama se restaurará en el próximo chat)
    """
    if not context.args:
        await update.message.reply_text(
            "✏️ *Uso:* `/gen <prompt de imagen>`\n"
            "Ejemplo: `/gen isometric pixel art building, simcity 2000 style`\n\n"
            "También puedes usar:\n"
            "  /gpu\\_free — Liberar VRAM manualmente\n"
            "  /gpu\\_restore — Restaurar Ollama a GPU",
            parse_mode="Markdown",
        )
        return

    config = load_config()
    prompt = " ".join(context.args)
    msg = await update.message.reply_text("🎨 Orquestando GPU para generación... ⏳")

    # 1. Ensure ComfyUI is running (lazy startup via persistent tmux)
    await msg.edit_text("🔌 Asegurando que ComfyUI este corriendo...")
    try:
        from wsl_service_manager import ensure_comfyui
        if not await asyncio.get_event_loop().run_in_executor(None, ensure_comfyui):
            await msg.edit_text("⚠️ No se pudo iniciar ComfyUI. Intenta manualmente con: bash launch_ias.sh start art")
            return
    except ImportError:
        pass  # wsl_service_manager not available, assume ComfyUI is already running
    
    # 2. Esperar que ComfyUI termine trabajos previos (Anti-Overlap)
    await msg.edit_text("⏳ Verificando cola de ComfyUI...")
    if await is_comfyui_busy():
        await msg.edit_text("⏳ ComfyUI está ocupado. Esperando que termine...")
        if not await wait_for_comfyui():
            await msg.edit_text("⚠️ Timeout esperando a ComfyUI. Intenta de nuevo.")
            return

    # 2. Liberar VRAM de Ollama
    vram_before = await get_gpu_vram_used()
    await msg.edit_text(f"🧹 Liberando VRAM ({vram_before}MB en uso)...")
    freed = await unload_ollama_model(config["ollama_model"], config["ollama_url"])
    await asyncio.sleep(1)  # Delay para que NVIDIA libere memoria

    vram_after_free = await get_gpu_vram_used()
    freed_mb = max(0, vram_before - vram_after_free) if vram_before > 0 else 0

    # 3. Lanzar generación en ComfyUI
    await msg.edit_text(
        f"🎨 Generando en ComfyUI...\n"
        f"   VRAM libre: ~{8192 - vram_after_free}MB\n"
        f"   Prompt: _{prompt[:100]}_",
        parse_mode="Markdown",
    )

    # Invocar generación real vía simmoon_generator.py
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from simmoon_generator import generate_single

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: generate_single(
                prompt=prompt,
                backend="comfyui",
                width=512,
                height=512,
                steps=20,
                cfg=7,
            )
        )

        if result and result.get("image_path"):
            img_path = result["image_path"]
            # Enviar imagen al chat
            with open(img_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=f"🎨 *{prompt[:80]}*\n_Generado con ComfyUI · Orquestador GPU_",
                    parse_mode="Markdown",
                )
            await msg.edit_text(
                f"✅ *Generación completada* 🎨\n"
                f"   VRAM liberada: {freed_mb}MB\n"
                f"   Archivo: `{Path(img_path).name}`\n\n"
                f"_Ollama se restaurará a GPU en tu próximo chat._",
                parse_mode="Markdown",
            )
        else:
            await msg.edit_text(
                f"⚠️ *Generación finalizada sin imagen*\n"
                f"   El backend respondió pero no devolvió imagen.\n"
                f"   VRAM liberada: {freed_mb}MB\n\n"
                f"_Ollama se restaurará a GPU en tu próximo chat._",
                parse_mode="Markdown",
            )
    except ImportError:
        await msg.edit_text(
            f"⚠️ *simmoon_generator.py no disponible*\n"
            f"   VRAM liberada: {freed_mb}MB\n"
            f"   La GPU está libre para usar ComfyUI manualmente.\n\n"
            f"_Usa /gpu\\_restore cuando termines para restaurar Ollama._",
            parse_mode="Markdown",
        )
    except Exception as e:
        await msg.edit_text(
            f"❌ *Error en generación:* {str(e)[:200]}\n"
            f"   VRAM liberada: {freed_mb}MB\n\n"
            f"_Ollama se restaurará a GPU en tu próximo chat._",
            parse_mode="Markdown",
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message — chat with Buffy by default."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Ignore commands (already handled)
    if text.startswith("/"):
        return

    config = load_config()

    msg = await update.message.reply_text(
        f"🤖 Buffy está pensando... 💭",
    )

    response = await ollama_chat(
        model=config.get("buffy_model", config["ollama_model"]),
        prompt=text,
        system=BUFFY_SYSTEM_PROMPT,
        temperature=0.7,
        max_tokens=800,
        ollama_url=config["ollama_url"],
    )

    if len(response) > 4000:
        response = response[:4000] + "\n\n*(mensaje truncado)*"

    await msg.edit_text(
        f"🤖 *Buffy:*\n{response}",
        parse_mode="Markdown",
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    print(f"[ERROR] Update {update} caused error {context.error}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────
def setup_config():
    """Interactive setup wizard."""
    print("\n" + "=" * 60)
    print("  🤖 SIMMOON Telegram Bot — Setup")
    print("=" * 60)

    config = load_config()

    if config["telegram_token"]:
        print(f"\n  Token actual: {config['telegram_token'][:8]}...{config['telegram_token'][-4:]}")
        change = input("  ¿Cambiar token? (s/N): ").strip().lower()
        if change == "s":
            config["telegram_token"] = input("  Nuevo token: ").strip()
    else:
        print("\n  ⚠️  No hay token configurado.")
        config["telegram_token"] = input("  Token de Telegram Bot: ").strip()

    print(f"\n  Modelo Ollama actual: {config['ollama_model']}")
    change = input("  ¿Cambiar modelo? (s/N): ").strip().lower()
    if change == "s":
        config["ollama_model"] = input("  Nuevo modelo: ").strip()

    save_config(config)
    print(f"\n  ✅ Configuración guardada en {CONFIG_PATH}")
    print("=" * 60 + "\n")


def main():
    config = load_config()

    if "--setup" in sys.argv:
        setup_config()
        return

    if not HAS_TELEGRAM:
        print("[ERROR] python-telegram-bot no instalado.")
        print("  Instala con: pip install python-telegram-bot")
        sys.exit(1)

    token = config.get("telegram_token", "")
    if not token:
        print("[ERROR] No hay token configurado.")
        print("  Ejecuta: python Simmoon_arc/telegram_bot.py --setup")
        sys.exit(1)

    # Build application
    app = Application.builder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("gpu", cmd_gpu))
    app.add_handler(CommandHandler("agents", cmd_agents))
    app.add_handler(CommandHandler("buffy", cmd_buffy))               # /buffy
    app.add_handler(CommandHandler("ai", cmd_ai))
    app.add_handler(CommandHandler("ai_jarvis", cmd_ai_jarvis))       # /ai_jarvis
    app.add_handler(CommandHandler("ai_hermes", cmd_ai_hermes))       # /ai_hermes
    app.add_handler(CommandHandler("ai_human", cmd_ai_human))         # /ai_human
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("models", cmd_models))
    app.add_handler(CommandHandler("gpu_free", cmd_gpu_free))       # /gpu_free
    app.add_handler(CommandHandler("gpu_restore", cmd_gpu_restore)) # /gpu_restore
    app.add_handler(CommandHandler("gen", cmd_gen))                 # /gen

    # Message handler (free text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    app.add_error_handler(error_handler)

    print(f"\n  {'='*50}")
    print(f"  🤖 SIMMOON Telegram Bot — Iniciado")
    print(f"  🧠 Bot: @{config.get('bot_name', 'SIMMOON Bot')}")
    print(f"  🧠 Modelo: {config['ollama_model']}")
    print(f"  {'='*50}")
    
    # Auto-ensure Ollama is running (persistent WSL tmux)
    print(f"\n  🔌 Verificando Ollama en WSL...")
    try:
        from wsl_service_manager import ensure_ollama, check_comfyui
        ollama_ok = ensure_ollama()
        if ollama_ok:
            print(f"  ✅ Ollama listo")
        else:
            print(f"  ⚠️  Ollama no disponible — /ai y /buffy no funcionaran")
        comfyui_up = check_comfyui()
        if comfyui_up:
            print(f"  ✅ ComfyUI detectado")
        else:
            print(f"  💤 ComfyUI no detectado — se iniciara bajo demanda en /gen")
    except ImportError:
        print(f"  ⚠️  wsl_service_manager.py no encontrado")
    except Exception as e:
        print(f"  ⚠️  Error verificando servicios: {e}")
    
    print(f"\n  Presiona Ctrl+C para detener.\n")

    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
