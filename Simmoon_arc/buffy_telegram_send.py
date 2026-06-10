#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buffy_telegram_send.py — Envío rápido de mensajes Buffy a Telegram 📤

Pequeño script para que Buffy envíe mensajes proactivos a un chat de Telegram.
Útil para notificaciones, alertas, o mensajes desde scripts.

Uso:
  python buffy_telegram_send.py <chat_id> "Mensaje a enviar"
  python buffy_telegram_send.py --alert "🚨 Alerta del sistema"
  python buffy_telegram_send.py --list-chats    # Ver chats conocidos

Ejemplos:
  python buffy_telegram_send.py 123456789 "¡Hola Jeremi! El sistema está listo."
  python buffy_telegram_send.py --alert "GPU al 95% de uso 🔥"
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "telegram_config.json"
STATE_PATH = SCRIPT_DIR / "buffy_telegram_state.json"


def load_token() -> str:
    """Cargar token de Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        return token

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg.get("telegram_token", "")
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def send_telegram_message(token: str, chat_id: int, text: str,
                          parse_mode: str = "Markdown") -> bool:
    """Enviar mensaje via Telegram Bot API."""
    import urllib.request

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("ok"):
            return True
        else:
            # Si falla parse_mode, reintentar sin él
            desc = result.get("description", "")
            if "parse" in desc.lower() and parse_mode:
                payload.pop("parse_mode", None)
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                resp = urllib.request.urlopen(req, timeout=15)
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("ok", False)
            print(f"[ERROR] Telegram: {desc}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[ERROR] Enviando a Telegram: {e}", file=sys.stderr)
        return False


def list_known_chats() -> list:
    """Listar chats conocidos desde el archivo de estado."""
    if not STATE_PATH.exists():
        return []

    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    chats = []
    for chat_id, info in state.get("chats", {}).items():
        chats.append({
            "chat_id": chat_id,
            "user_name": info.get("user_name", "Desconocido"),
            "last_activity": info.get("last_activity", "?"),
            "messages": len(info.get("messages", [])),
        })
    return sorted(chats, key=lambda c: c["last_activity"], reverse=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="📤 Buffy Telegram Send — Enviar mensajes a Telegram"
    )
    parser.add_argument("chat_id", nargs="?", type=int,
                        help="ID del chat al que enviar")
    parser.add_argument("text", nargs="?", type=str,
                        help="Texto del mensaje")
    parser.add_argument("--alert", type=str,
                        help="Enviar como alerta del sistema (con prefijo 🚨)")
    parser.add_argument("--notify", type=str,
                        help="Enviar como notificación (con prefijo 📢)")
    parser.add_argument("--list-chats", action="store_true",
                        help="Listar chats conocidos")

    args = parser.parse_args()

    # Listar chats
    if args.list_chats:
        chats = list_known_chats()
        if not chats:
            print("📭 No hay chats conocidos.")
            print("   Envía un mensaje al bot primero para registrarlo.")
        else:
            print(f"\n📋 Chats conocidos ({len(chats)}):\n")
            for c in chats:
                print(f"  🆔 {c['chat_id']} | 👤 {c['user_name']}")
                print(f"     Última actividad: {c['last_activity'][:19]}")
                print(f"     Mensajes: {c['messages']}")
                print()
        return

    # Cargar token
    token = load_token()
    if not token:
        print("❌ No hay token de Telegram configurado.")
        print("   Configúralo en telegram_config.json o variable TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    # Determinar chat_id y texto
    chat_id = args.chat_id
    text = args.text

    if args.alert:
        if not chat_id:
            # Usar el último chat conocido como fallback
            chats = list_known_chats()
            if chats:
                chat_id = int(chats[0]["chat_id"])
                print(f"📱 Usando chat {chat_id} ({chats[0]['user_name']})")
            else:
                print("❌ Especifica el chat_id (no hay chats conocidos)")
                print("   Uso: python buffy_telegram_send.py <chat_id> --alert \"mensaje\"")
                sys.exit(1)
        text = f"🚨 *Alerta de Buffy*\n{args.alert}"
    elif args.notify:
        if not chat_id:
            chats = list_known_chats()
            if chats:
                chat_id = int(chats[0]["chat_id"])
                print(f"📱 Usando chat {chat_id} ({chats[0]['user_name']})")
            else:
                print("❌ Especifica el chat_id (no hay chats conocidos)")
                print("   Uso: python buffy_telegram_send.py <chat_id> --notify \"mensaje\"")
                sys.exit(1)
        text = f"📢 *Notificación de Buffy*\n{args.notify}"

    if not chat_id or not text:
        parser.print_help()
        print("\n  💡 Tip: Usa --list-chats para ver tus chats disponibles")
        sys.exit(1)

    # Enviar
    prefix = "🤖 *Buffy:*\n"
    full_text = prefix + text

    if len(full_text) > 4000:
        full_text = full_text[:4000] + "\n\n_(mensaje truncado)_"

    print(f"📤 Enviando a chat {chat_id}...")
    if send_telegram_message(token, chat_id, full_text):
        print(f"✅ Mensaje enviado correctamente")
    else:
        print(f"❌ Error al enviar mensaje")
        sys.exit(1)


if __name__ == "__main__":
    main()
