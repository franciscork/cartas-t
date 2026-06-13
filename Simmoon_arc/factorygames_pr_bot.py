#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏭 FactoryGames PR Bot — Telegram Publisher

Publica automáticamente resúmenes ejecutivos, devlogs y anuncios de
FactoryGames en canales públicos de Telegram.

Es el 3er bot del estudio (PR Bot) según el documento fundacional.

Uso:
    python factorygames_pr_bot.py --setup          # Configurar bot token + canal
    python factorygames_pr_bot.py --publish        # Publicar resumen ejecutivo ahora
    python factorygames_pr_bot.py --test           # Enviar mensaje de prueba
    python factorygames_pr_bot.py --status         # Ver estado del bot
    python factorygames_pr_bot.py --publish-summary "texto"  # Publicar texto personalizado
"""

import json
import os
import sys
import time
import urllib.request
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
CONFIG_PATH = SCRIPT_DIR / "factorygames_pr_config.json"


# ── Config ────────────────────────────────────────────────────────────────
def load_config() -> dict:
    """Load PR Bot configuration."""
    default = {
        "bot_token": "",
        "bot_name": "FactoryGamesPRBot",
        "channel": "",       # @channel_username or channel ID (negative number)
        "channel_name": "",
        "last_publish": None,
        "auto_publish_weekly": True,
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except Exception:
            pass
    return dict(default)


def save_config(cfg: dict):
    """Save PR Bot configuration."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Config guardada en {CONFIG_PATH}")


# ── Telegram API ──────────────────────────────────────────────────────────
def _tg_request(token: str, method: str, params: dict = None) -> dict:
    """Make a request to the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/{method}"
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


def get_bot_info(token: str) -> dict:
    """Get bot information from Telegram."""
    return _tg_request(token, "getMe")


def send_to_channel(token: str, channel: str, text: str,
                    parse_mode: str = "Markdown") -> bool:
    """Send a message to a Telegram channel.

    Args:
        token: Bot token
        channel: Channel @username or ID (negative number for channels).
                 String IDs like "-100123456" are auto-converted to int.
        text: Message text
        parse_mode: 'Markdown', 'HTML', or None

    Returns:
        True on success, False on failure
    """
    # Convert channel to int if it's a numeric ID (channels use negative IDs)
    chat_id = channel
    stripped = str(channel).lstrip("-")
    if stripped.isdigit():
        chat_id = int(channel)

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

    result = _tg_request(token, "sendMessage", payload)

    if result.get("ok"):
        msg_id = result.get("result", {}).get("message_id", "?")
        print(f"  ✅ Publicado en {channel} (msg #{msg_id})")
        return True
    else:
        error_desc = result.get("error", "")
        # Retry without parse_mode if Markdown parsing fails
        if "parse" in error_desc.lower() and parse_mode is not None:
            payload.pop("parse_mode", None)
            result2 = _tg_request(token, "sendMessage", payload)
            if result2.get("ok"):
                print(f"  ✅ Publicado (sin formato) en {channel}")
                return True
        print(f"  ❌ Error al publicar: {error_desc}")
        return False


# ── FactoryGames Summary Builder ──────────────────────────────────────────
def build_factorygames_summary() -> str:
    """Build the FactoryGames executive summary for channel publication.
    
    Intenta leer el asset count del sistema; si no, usa un valor por defecto.
    """
    now = datetime.now()
    
    # Try to get live asset count from the system
    assets_total = "826+"
    try:
        from agatha_actas import get_recent_summaries
        summaries = get_recent_summaries(days=1)
        if summaries:
            assets_total = str(summaries[0].get("assets_total", "826+"))
    except Exception:
        pass
    
    return (
        "🏭 *FACTORYGAMES — Estudio Indie de Videojuegos*\n\n"
        f"📅 {now.strftime('%d/%m/%Y')}\n\n"
        "*FactoryGames* es un estudio indie impulsado por *15 agentes IA "
        "open-source* que colaboran sin coste de API externo —Ollama local, "
        "Freebuff (Buffy), Claude Code y Hermes Agent (8 agentes)— para "
        "cubrir todo el ciclo creativo: de la idea al juego publicado.\n\n"
        "📊 *Stack Tecnológico*\n"
        "🧠 IA: Ollama + Freebuff + Claude Code + Hermes Agent\n"
        "🎨 Arte: Blender 3D · InvokeAI · ComfyUI · GIMP\n"
        "📡 Comunicación: 5 Bots Telegram\n"
        "⚙️ Orquestación: CrewAI / LangGraph\n\n"
        "🎮 *Pipeline 8 fases*\n"
        "Concepto → Diseño → Arte → 3D → Código → QA → Marketing → Release\n\n"
        "🚀 *Proyecto Piloto:* SimMoon — Simulador de colonia lunar\n"
        f"🏗️ *Estado:* En desarrollo activo · {assets_total} assets · Pipeline Blender integrado\n\n"
        "💡 *Ventaja:* Primer estudio indie con producción 100% local, "
        "gratuita y completa.\n\n"
        f"_🤖 FactoryGames PR Bot · {now.strftime('%H:%M')}_"
    )


def build_devlog_summary(title: str, content: str) -> str:
    """Build a devlog post for channel publication."""
    now = datetime.now()
    return (
        f"🎮 *DEVLOG: {title}*\n\n"
        f"{content}\n\n"
        f"🏭 FactoryGames · {now.strftime('%d/%m/%Y')}\n"
        f"_#gamedev #indiedev #ai #opensource_"
    )


# ── Main Commands ─────────────────────────────────────────────────────────
def cmd_setup():
    """Interactive setup of the PR Bot."""
    print("\n  🏭 FactoryGames PR Bot — Setup")
    print("  " + "=" * 50)
    print()
    print("  Para crear un bot nuevo en Telegram:")
    print("  1. Abre @BotFather en Telegram")
    print("  2. Envía /newbot")
    print("  3. Elige nombre: FactoryGames PR Bot")
    print("  4. Elige username: @FactoryGamesPR_bot")
    print("  5. Copia el token y pégalo aquí")
    print()
    
    token = input("  Token del bot: ").strip()
    if not token:
        print("  ❌ Se requiere un token.\n")
        return False
    
    # Verify token
    info = get_bot_info(token)
    if not info.get("ok"):
        print(f"  ❌ Token inválido: {info.get('error', '?')}\n")
        return False
    
    bot_username = info.get("result", {}).get("username", "?")
    print(f"  ✅ Bot verificado: @{bot_username}")
    
    print()
    print("  Para publicar en un canal:")
    print("  1. Crea un canal en Telegram (ej: @FactoryGamesNews)")
    print("  2. Añade al bot como administrador del canal")
    print("  3. Pega el @username o ID del canal aquí")
    print()
    
    channel = input("  Canal (@username o ID): ").strip()
    if not channel:
        print("  ⚠️  Sin canal configurado. Solo se podrá publicar manualmente.")
    
    cfg = load_config()
    cfg["bot_token"] = token
    cfg["bot_name"] = f"@{bot_username}"
    cfg["channel"] = channel
    save_config(cfg)
    
    # Test publish
    if channel:
        print(f"\n  📤 Enviando mensaje de prueba al canal {channel}...")
        test_msg = (
            "🏭 *FactoryGames PR Bot — ONLINE* ✅\n\n"
            "Este canal recibirá actualizaciones automáticas del estudio:\n"
            "📊 Resúmenes ejecutivos semanales\n"
            "🎮 Devlogs de proyectos\n"
            "🚀 Anuncios de lanzamientos\n\n"
            "_Powered by FactoryGames · Agatha Actas_ 🤖"
        )
        if send_to_channel(token, channel, test_msg):
            print(f"  ✅ Bot configurado y funcionando!\n")
        else:
            print(f"  ⚠️  No se pudo publicar. Revisa que el bot sea admin del canal.\n")
    
    return True


def cmd_publish(text: str = None, devlog_title: str = None):
    """Publish to the configured channel."""
    cfg = load_config()
    token = cfg.get("bot_token")
    channel = cfg.get("channel")
    
    if not token:
        print("❌ No hay token configurado. Ejecuta: python factorygames_pr_bot.py --setup")
        return False
    
    if not channel:
        print("❌ No hay canal configurado. Ejecuta: python factorygames_pr_bot.py --setup")
        return False
    
    if text:
        msg = text
    elif devlog_title:
        msg = build_devlog_summary(devlog_title, text or "")
    else:
        msg = build_factorygames_summary()
    
    print(f"  📤 Publicando en {channel}...")
    ok = send_to_channel(token, channel, msg)
    
    if ok:
        cfg["last_publish"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_config(cfg)
    
    return ok


def cmd_status():
    """Show bot status."""
    cfg = load_config()
    token = cfg.get("bot_token")
    
    print("\n  🏭 FactoryGames PR Bot — Estado")
    print("  " + "=" * 50)
    
    if token:
        info = get_bot_info(token)
        if info.get("ok"):
            bot = info.get("result", {})
            print(f"  ✅ Bot: @{bot.get('username', '?')}")
            print(f"  🆔 ID: {bot.get('id', '?')}")
            print(f"  👤 Nombre: {bot.get('first_name', '?')}")
        else:
            print(f"  ❌ Token inválido: {info.get('error', '?')}")
    else:
        print("  ⚠️  Token no configurado")
    
    channel = cfg.get("channel", "")
    print(f"  📡 Canal: {channel or '(no configurado)'}")
    print(f"  🕐 Última publicación: {cfg.get('last_publish', 'nunca')}")
    print(f"  🔄 Auto-publish semanal: {'✅' if cfg.get('auto_publish_weekly') else '❌'}")
    print()


# ── CLI Interface ──────────────────────────────────────────────────────────
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🏭 FactoryGames PR Bot — Publica en canales de Telegram"
    )
    parser.add_argument("--setup", action="store_true",
                        help="Configurar bot token y canal")
    parser.add_argument("--publish", action="store_true",
                        help="Publicar resumen ejecutivo ahora")
    parser.add_argument("--test", action="store_true",
                        help="Enviar mensaje de prueba al canal")
    parser.add_argument("--status", action="store_true",
                        help="Ver estado del bot")
    parser.add_argument("--publish-summary", type=str, metavar="TEXT",
                        help="Publicar texto personalizado en el canal")
    parser.add_argument("--devlog", type=str, metavar="TITLE",
                        help="Publicar un devlog con el título dado")
    parser.add_argument("--devlog-content", type=str, metavar="TEXT",
                        help="Contenido del devlog (usar con --devlog)")
    
    args = parser.parse_args()
    
    if args.setup:
        cmd_setup()
        return
    
    if args.status:
        cmd_status()
        return
    
    if args.test:
        cfg = load_config()
        token = cfg.get("bot_token")
        channel = cfg.get("channel")
        if not token or not channel:
            print("❌ Ejecuta --setup primero para configurar token y canal.")
            return
        test_msg = (
            "🧪 *PR Bot — Test de publicación*\n\n"
            "Si ves este mensaje, el bot está funcionando correctamente.\n\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_to_channel(token, channel, test_msg)
        return
    
    if args.publish:
        cmd_publish()
        return
    
    if args.publish_summary:
        cmd_publish(text=args.publish_summary)
        return
    
    if args.devlog:
        cmd_publish(text=args.devlog_content or "", devlog_title=args.devlog)
        return
    
    # Default: show help
    parser.print_help()
    print("\n  Ejemplos:")
    print("    python factorygames_pr_bot.py --setup              # Configurar")
    print("    python factorygames_pr_bot.py --publish            # Publicar resumen")
    print("    python factorygames_pr_bot.py --test               # Mensaje de prueba")
    print("    python factorygames_pr_bot.py --status             # Ver estado")
    print("    python factorygames_pr_bot.py --devlog \"Nueva feature\" "
          "--devlog-content \"Añadimos...\"")
    print()


if __name__ == "__main__":
    main()
