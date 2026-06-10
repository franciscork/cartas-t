#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buffy_telegram.py — Buffy Telegram Bridge 🤖📱

Conecta a Buffy (Codebuff AI) con Telegram para responder mensajes
usando su personalidad y conocimientos. Usa Ollama como backend LLM.

Modos:
  --daemon       Sondeo continuo de mensajes (responde automáticamente)
  --check        Ver mensajes nuevos SIN responder
  --send CHATID  Enviar mensaje proactivo a un chat específico
  --reply MSGID  Responder a un mensaje específico
  --setup        Configuración interactiva

Ejemplos:
  python buffy_telegram.py --daemon               # Iniciar servicio Buffy
  python buffy_telegram.py --check                 # Ver mensajes nuevos
  python buffy_telegram.py --send 123456 "Hola!"   # Enviar mensaje
  python buffy_telegram.py --setup                 # Configurar

Requisitos:
  - Token de bot de Telegram (en telegram_config.json o env TELEGRAM_BOT_TOKEN)
  - Ollama corriendo con un modelo disponible
"""

import json
import os
import sys
import time
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

# ── Config ─────────────────────────────────────────────────────────────────
CONFIG_PATH = SCRIPT_DIR / "telegram_config.json"
BUFFY_STATE_PATH = SCRIPT_DIR / "buffy_telegram_state.json"

DEFAULT_CONFIG = {
    "telegram_token": "",
    "bot_name": "Jeremi_Hermes_bot",
    "ollama_model": "qwen2.5:3b",
    "ollama_url": "http://127.0.0.1:11434",
}


def load_config() -> dict:
    """Cargar configuración del bot."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if env_token:
        cfg["telegram_token"] = env_token

    return cfg


# ── Buffy System Prompt ────────────────────────────────────────────────────
# Importada desde un lugar común para evitar duplicación.
# Si telegram_bot.py define BUFFY_SYSTEM_PROMPT, usamos esa.
try:
    sys.path.insert(0, str(SCRIPT_DIR))
    from telegram_bot import BUFFY_SYSTEM_PROMPT  # type: ignore
except ImportError:
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
- Si Jeremi pregunta por el estado del sistema, sugiérele ejecutar /status o /services
- Recuerda que este chat es por Telegram — no puedes ejecutar comandos directamente,
  pero puedes guiar a Jeremi para que los ejecute"""


# ── Ollama Integration ─────────────────────────────────────────────────────
def _http_post(url: str, payload: dict, timeout: int = 60) -> dict:
    """HTTP POST helper."""
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def _http_get(url: str, timeout: int = 10) -> dict:
    """HTTP GET helper."""
    import urllib.request

    req = urllib.request.Request(url, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def ollama_chat(model: str, messages: list, ollama_url: str = "http://127.0.0.1:11434",
                temperature: float = 0.7, max_tokens: int = 800) -> str:
    """Enviar chat a Ollama y obtener respuesta."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    result = _http_post(f"{ollama_url}/api/chat", payload, timeout=180)
    if "error" in result:
        return f"[ERROR] Ollama: {result['error']}"
    return result.get("message", {}).get("content", "...") or "..."


def ollama_list_models(ollama_url: str = "http://127.0.0.1:11434") -> list:
    """Listar modelos disponibles en Ollama."""
    result = _http_get(f"{ollama_url}/api/tags", timeout=10)
    if "error" in result:
        return []
    return [m["name"] for m in result.get("models", [])]


# ── Telegram API ───────────────────────────────────────────────────────────
class TelegramAPI:
    """Cliente ligero para la API de Telegram Bot."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    def get_updates(self, offset: Optional[int] = None,
                    timeout: int = 30) -> list:
        """Obtener updates (mensajes nuevos)."""
        url = f"{self.base_url}/getUpdates"
        params = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset

        import urllib.request
        import urllib.parse

        query = urllib.parse.urlencode(params, doseq=True)
        full_url = f"{url}?{query}"

        try:
            req = urllib.request.Request(full_url, method="GET")
            resp = urllib.request.urlopen(req, timeout=timeout + 10)
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return data.get("result", [])
            else:
                print(f"[ERROR] Telegram API: {data.get('description', 'unknown')}")
                return []
        except Exception as e:
            print(f"[ERROR] Telegram getUpdates: {e}")
            return []

    def send_message(self, chat_id: int, text: str,
                     parse_mode: str = "Markdown",
                     reply_to_message_id: Optional[int] = None) -> bool:
        """Enviar mensaje a un chat."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        result = _http_post(f"{self.base_url}/sendMessage", payload, timeout=15)
        if result.get("ok"):
            return True
        else:
            desc = result.get("description", "unknown")
            # Si falla Markdown, intentar sin parse_mode
            if "parse" in desc.lower():
                payload.pop("parse_mode", None)
                result = _http_post(f"{self.base_url}/sendMessage", payload, timeout=15)
                return result.get("ok", False)
            print(f"[ERROR] sendMessage: {desc}")
            return False

    def send_chat_action(self, chat_id: int, action: str = "typing") -> bool:
        """Mostrar acción de chat (typing...)."""
        payload = {"chat_id": chat_id, "action": action}
        result = _http_post(f"{self.base_url}/sendChatAction", payload, timeout=5)
        return result.get("ok", False)

    def get_me(self) -> dict:
        """Obtener info del bot."""
        return _http_get(f"{self.base_url}/getMe")


# ── Conversation State ─────────────────────────────────────────────────────
class ConversationState:
    """Mantiene el historial de conversaciones por chat."""

    def __init__(self, state_path: Path = BUFFY_STATE_PATH):
        self.state_path = state_path
        self.state = self._load()
        self.max_history = 20  # mensajes por chat

    def _load(self) -> dict:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "version": 1,
            "last_update_id": 0,
            "chats": {},
            "created": datetime.now().isoformat(),
        }

    def save(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def get_last_update_id(self) -> int:
        return self.state.get("last_update_id", 0)

    def set_last_update_id(self, update_id: int):
        self.state["last_update_id"] = update_id

    def get_history(self, chat_id: str) -> list:
        chat = self.state["chats"].get(str(chat_id), {})
        return chat.get("messages", [])

    def add_message(self, chat_id: str, role: str, content: str,
                    user_name: str = ""):
        chat_id = str(chat_id)
        if chat_id not in self.state["chats"]:
            self.state["chats"][chat_id] = {
                "user_name": user_name,
                "messages": [],
                "last_activity": datetime.now().isoformat(),
            }

        chat = self.state["chats"][chat_id]
        chat["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        chat["last_activity"] = datetime.now().isoformat()
        if user_name:
            chat["user_name"] = user_name

        # Limitar historial
        if len(chat["messages"]) > self.max_history * 2:
            chat["messages"] = chat["messages"][-self.max_history * 2:]

    def get_user_name(self, chat_id: str) -> str:
        return self.state["chats"].get(str(chat_id), {}).get("user_name", "")


# ── Buffy Core ─────────────────────────────────────────────────────────────
class BuffyTelegram:
    """Buffy en Telegram — responde mensajes como Buffy."""

    def __init__(self):
        self.config = load_config()
        self.token = self.config.get("telegram_token", "")
        self.api = TelegramAPI(self.token) if self.token else None
        self.state = ConversationState()
        self.model = self.config.get("buffy_model", self.config.get("ollama_model", "qwen2.5:3b"))
        self.ollama_url = self.config.get("ollama_url", "http://127.0.0.1:11434")

    def validate(self) -> bool:
        """Validar que todo esté listo."""
        if not self.token:
            print("❌ No hay token de Telegram configurado.")
            print("   Ejecuta: python buffy_telegram.py --setup")
            return False
        if not self.api:
            return False

        # Verificar conexión con Telegram
        me = self.api.get_me()
        if "error" in me:
            print(f"❌ Error conectando a Telegram: {me['error']}")
            return False
        print(f"✅ Conectado a Telegram como @{me.get('result', {}).get('username', '?')}")

        # Verificar Ollama
        models = ollama_list_models(self.ollama_url)
        if not models:
            print("⚠️  No se detectaron modelos en Ollama. ¿Está corriendo?")
        else:
            print(f"✅ Ollama disponible: {len(models)} modelo(s)")

        return True

    def process_message(self, msg: dict) -> Optional[str]:
        """Procesar un mensaje y generar respuesta de Buffy."""
        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_name = user.get("first_name", "Humano")
        text = msg.get("text", "").strip()

        if not text:
            return None

        # Guardar mensaje del usuario
        self.state.add_message(chat_id, "user", text, user_name)

        # Construir historial para Ollama
        messages = [{"role": "system", "content": BUFFY_SYSTEM_PROMPT}]

        # Añadir historial reciente
        history = self.state.get_history(chat_id)
        for h in history[-16:]:  # últimos 8 intercambios
            role = h["role"]
            if role == "system":
                continue
            messages.append({"role": role, "content": h["content"]})

        # Generar respuesta
        response = ollama_chat(
            model=self.model,
            messages=messages,
            ollama_url=self.ollama_url,
            temperature=0.7,
            max_tokens=800,
        )

        # Limpiar respuesta si empieza con error
        if response.startswith("[ERROR]"):
            return f"⚠️ {response}"

        # Truncar para Telegram (límite 4096)
        if len(response) > 4000:
            response = response[:4000] + "\n\n_(mensaje truncado)_"

        # Guardar respuesta
        self.state.add_message(chat_id, "assistant", response)
        self.state.save()

        return response

    def _voice_pipe(self, text: str):
        """Enviar texto al pipe de voz (no bloqueante)."""
        pipe_path = Path.home() / ".simmoon-logs" / "voice_pipe"
        try:
            if pipe_path.exists() and pipe_path.is_fifo():
                # Escribir sin bloquear: abrir en modo no bloqueante
                fd = os.open(str(pipe_path), os.O_WRONLY | os.O_NONBLOCK)
                try:
                    os.write(fd, (text + "\n").encode("utf-8"))
                finally:
                    os.close(fd)
        except Exception:
            pass  # Silencioso: si no hay voice daemon, no pasa nada

    def send_proactive(self, chat_id: int, text: str) -> bool:
        """Enviar mensaje proactivo de Buffy a un chat."""
        if not self.api:
            print("❌ API de Telegram no inicializada")
            return False

        # Añadir prefijo de Buffy
        prefix = "🤖 *Buffy:*\n"
        full_text = prefix + text

        if len(full_text) > 4000:
            full_text = full_text[:4000] + "\n\n_(mensaje truncado)_"

        success = self.api.send_message(chat_id, full_text)
        if success:
            self._voice_pipe(text)
        return success

    def run_daemon(self, poll_interval: float = 2.0):
        """Ejecutar Buffy como daemon — sondeo continuo."""
        if not self.validate():
            print("\n❌ No se puede iniciar el daemon. Corrige los errores primero.")
            sys.exit(1)

        print(f"\n{'='*55}")
        print(f"  🤖 BUFFY Telegram Bridge — ACTIVA")
        print(f"  📱 Bot: @{self.config.get('bot_name', 'Jeremi_Hermes_bot')}")
        print(f"  🧠 Modelo: {self.model}")
        print(f"  🔄 Sondeando cada {poll_interval}s")
        print(f"{'='*55}")
        print(f"\n  Esperando mensajes... (Ctrl+C para detener)\n")

        consecutive_errors = 0

        try:
            while True:
                try:
                    offset = self.state.get_last_update_id() + 1
                    updates = self.api.get_updates(offset=offset, timeout=30)

                    if updates:
                        consecutive_errors = 0
                        for update in updates:
                            update_id = update.get("update_id", 0)
                            msg = update.get("message")

                            if msg and "text" in msg:
                                chat_id = msg["chat"]["id"]
                                user_name = msg.get("from", {}).get("first_name", "?")
                                text = msg["text"]

                                # Ignorar comandos (se procesan aparte)
                                if text.startswith("/"):
                                    # Procesar comandos especiales de Buffy
                                    response = self._handle_command(text, chat_id, msg)
                                    if response:
                                        self.api.send_chat_action(chat_id, "typing")
                                        time.sleep(0.5)
                                        self.api.send_message(chat_id, response)
                                        self._voice_pipe(response)
                                else:
                                    print(f"  📩 [{user_name}]: {text[:80]}{'...' if len(text) > 80 else ''}")
                                    self.api.send_chat_action(chat_id, "typing")

                                    response = self.process_message(msg)
                                    if response:
                                        prefix = "🤖 *Buffy:*\n"
                                        full_response = prefix + response
                                        self.api.send_message(
                                            chat_id, full_response,
                                            reply_to_message_id=msg.get("message_id"),
                                        )
                                        self._voice_pipe(response)
                                        print(f"  📤 [Buffy]: {response[:80]}{'...' if len(response) > 80 else ''}")

                            # Siempre actualizar offset
                            if update_id >= self.state.get_last_update_id():
                                self.state.set_last_update_id(update_id)
                                self.state.save()                # No updates is normal — don't count as error
                # Only count real errors in the except block

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    consecutive_errors += 1
                    print(f"  ⚠️  Error en ciclo: {e}")
                    if consecutive_errors > 50:
                        print("⚠️  Demasiados errores consecutivos. ¿Internet caído?")
                        consecutive_errors = 0
                    time.sleep(5)

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print(f"\n\n  👋 Buffy se despide. ¡Hasta la próxima, Jeremi!")
            print(f"  📊 Mensajes procesados en esta sesión guardados.\n")

    def _handle_command(self, text: str, chat_id: int, msg: dict) -> Optional[str]:
        """Manejar comandos especiales de Buffy."""
        cmd = text.lower().split()[0]

        if cmd == "/start":
            user_name = msg.get("from", {}).get("first_name", "Humano")
            return (
                f"👋 *¡Hola {user_name}! Soy Buffy* 🤖\n\n"
                f"Soy la asistente de Codebuff y el puente entre tú y el "
                f"ecosistema SIMMOON. Estoy aquí para:\n\n"
                f"💻 *Programar y debuggear* — Tu copiloto de código\n"
                f"🏭 *Gestionar SIMMOON* — La fábrica de assets pixel art\n"
                f"📊 *Monitorear el sistema* — Estado de servicios y agentes\n"
                f"💡 *Resolver problemas* — Pregúntame lo que sea\n\n"
                f"*Comandos disponibles:*\n"
                f"  /status — Estado del sistema\n"
                f"  /help — Ayuda completa\n"
                f"  /clear — Limpiar historial de conversación\n"
                f"  /modelo — Ver/cambiar modelo IA\n\n"
                f"¡Adelante, pregúntame lo que necesites! 🚀"
            )

        elif cmd == "/help":
            return (
                "📖 *Comandos de Buffy*\n\n"
                "💬 *Conversación libre:*\n"
                "  Envía cualquier mensaje y te responderé\n\n"
                "🔧 *Comandos:*\n"
                "  /start — Saludo inicial\n"
                "  /help — Esta ayuda\n"
                "  /status — Estado del sistema\n"
                "  /clear — Borrar historial de esta conversación\n"
                "  /modelo — Ver modelo activo\n"
                "  /modelo <nombre> — Cambiar modelo\n\n"
                "📊 *Sistema:*\n"
                "  Pregúntame sobre el estado de servicios,\n"
                "  agentes, GPU, o cualquier componente SIMMOON\n\n"
                "💻 *Programación:*\n"
                "  Comparte código, pide debugging,\n"
                "  sugerencias de arquitectura, etc.\n\n"
                "⚡ *Tip:* Puedes mencionar archivos del proyecto\n"
                "  y te daré contexto específico."
            )

        elif cmd == "/clear":
            # Limpiar historial
            self.state.state["chats"][str(chat_id)] = {
                "user_name": self.state.get_user_name(chat_id),
                "messages": [],
                "last_activity": datetime.now().isoformat(),
            }
            self.state.save()
            return "🧹 *Historial limpiado.* Empecemos de nuevo. ¿En qué puedo ayudarte?"

        elif cmd == "/modelo":
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                new_model = parts[1].strip()
                models = ollama_list_models(self.ollama_url)
                if new_model in models:
                    self.model = new_model
                    return f"✅ Modelo cambiado a `{new_model}`"
                else:
                    available = ", ".join(f"`{m}`" for m in models[:8])
                    return f"❌ Modelo `{new_model}` no encontrado.\n\nDisponibles: {available}"
            else:
                return f"🧠 Modelo activo: `{self.model}`\n\nPara cambiar: `/modelo <nombre>`"

        elif cmd == "/status":
            return (
                "📊 *Para ver el estado del sistema:*\n\n"
                "Usa el bot de sistema con:\n"
                "  `/status` — Estado completo\n"
                "  `/services` — Servicios backend\n"
                "  `/gpu` — Info de GPU\n\n"
                "O pregúntame directamente y te ayudo."
            )

        return None

    def check_messages(self):
        """Ver mensajes nuevos sin responder (modo check)."""
        if not self.validate():
            return

        offset = self.state.get_last_update_id() + 1
        updates = self.api.get_updates(offset=offset, timeout=5)

        if not updates:
            print("📭 No hay mensajes nuevos.")
            return

        print(f"📬 {len(updates)} mensaje(s) nuevo(s):\n")
        for update in updates:
            msg = update.get("message", {})
            user = msg.get("from", {})
            user_name = user.get("first_name", "?")
            text = msg.get("text", "[sin texto]")
            chat_id = msg.get("chat", {}).get("id", "?")
            msg_id = msg.get("message_id", "?")

            print(f"  🆔 ChatID: {chat_id} | MsgID: {msg_id}")
            print(f"  👤 {user_name}: {text[:200]}")
            print()

        # Actualizar offset para no volver a ver estos mensajes
        last = updates[-1].get("update_id", 0)
        self.state.set_last_update_id(last)
        self.state.save()


# ── Setup ──────────────────────────────────────────────────────────────────
def setup():
    """Configuración interactiva del bridge Buffy-Telegram."""
    print("\n" + "=" * 60)
    print("  🤖 BUFFY Telegram Bridge — Setup")
    print("=" * 60)

    config = load_config()

    if config.get("telegram_token"):
        token_preview = config["telegram_token"][:8] + "..." + config["telegram_token"][-4:]
        print(f"\n  Token actual: {token_preview}")
        change = input("  ¿Cambiar token? (s/N): ").strip().lower()
        if change == "s":
            config["telegram_token"] = input("  Nuevo token de Telegram Bot: ").strip()
    else:
        print("\n  ⚠️  No hay token configurado.")
        print("  Obtén uno de @BotFather en Telegram: https://t.me/BotFather")
        config["telegram_token"] = input("  Token de Telegram Bot: ").strip()

    print(f"\n  Modelo Ollama actual: {config.get('ollama_model', 'qwen2.5:3b')}")
    change = input("  ¿Cambiar modelo? (s/N): ").strip().lower()
    if change == "s":
        config["ollama_model"] = input("  Nuevo modelo (ej: qwen2.5:7b): ").strip()

    # Guardar
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ Configuración guardada en {CONFIG_PATH}")
    print("=" * 60 + "\n")

    print("  🚀 Para iniciar Buffy en Telegram:")
    print("     python Simmoon_arc/buffy_telegram.py --daemon")
    print()


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="🤖 Buffy Telegram Bridge — Buffy responde en Telegram"
    )
    parser.add_argument("--daemon", action="store_true",
                        help="Iniciar sondeo continuo (Buffy responde automáticamente)")
    parser.add_argument("--check", action="store_true",
                        help="Ver mensajes nuevos sin responder")
    parser.add_argument("--send", nargs=2, metavar=("CHAT_ID", "TEXTO"),
                        help="Enviar mensaje proactivo: --send <chat_id> \"texto\"")
    parser.add_argument("--setup", action="store_true",
                        help="Configuración interactiva")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Intervalo de sondeo en segundos (default: 2.0)")

    args = parser.parse_args()

    if args.setup:
        setup()
        return

    buffy = BuffyTelegram()

    if args.send:
        chat_id = int(args.send[0])
        text = args.send[1]
        if buffy.send_proactive(chat_id, text):
            print(f"✅ Mensaje enviado a chat {chat_id}")
        else:
            print(f"❌ Error enviando mensaje a chat {chat_id}")
        return

    if args.check:
        buffy.check_messages()
        return

    if args.daemon:
        buffy.run_daemon(poll_interval=args.interval)
        return

    # Default: mostrar ayuda
    parser.print_help()
    print("\n  🚀 Modo más común: python buffy_telegram.py --daemon")


if __name__ == "__main__":
    main()
