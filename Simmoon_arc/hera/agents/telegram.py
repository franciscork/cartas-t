#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hera/agents/telegram.py — Adaptador de Telegram para HERA 🤖📱

Conecta Telegram al ecosistema HERA como un agente más.

Capas:
  - TelegramAPI:    Cliente HTTP ligero para la API de Telegram Bot
  - TelegramAgent:  Lógica de negocio (comandos, chat IA, estado)
  - HeraTelegramAgent: Integración con HeraCore (MessageBus + Vault)

La integración con Hera resuelve el problema de 409 Conflict:
  - Un solo bot de Telegram (polling)
  - Múltiples agentes HERA pueden enviar/recibir mensajes via bus
  - Cada agente HERA se suscribe a su propio canal en el bus

Uso básico:
    from hera.agents import TelegramAgent

    agent = TelegramAgent(token="...")
    agent.run_daemon()

Uso con Hera:
    from hera import HeraCore
    from hera.agents import HeraTelegramAgent

    hera = HeraCore()
    tg = HeraTelegramAgent()
    tg.attach(hera)
    hera.start()
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any


# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()


# ══════════════════════════════════════════════════════════════════════════
#  HTTP Helpers
# ══════════════════════════════════════════════════════════════════════════

def _http_post(url: str, payload: dict, timeout: int = 30) -> dict:
    """HTTP POST helper."""
    import urllib.request
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def _http_get(url: str, timeout: int = 30) -> dict:
    """HTTP GET helper."""
    import urllib.request
    import urllib.parse

    # If url has params dict, encode it
    if isinstance(url, tuple):
        base, params = url
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{base}?{query}"

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════
#  TelegramAPI — Cliente HTTP ligero (sin python-telegram-bot)
# ══════════════════════════════════════════════════════════════════════════

class TelegramAPI:
    """Cliente HTTP ligero para la API de Telegram Bot.

    No requiere python-telegram-bot. Usa urllib directamente.
    Soporta getUpdates (long polling), sendMessage, sendChatAction,
    getMe, y otros métodos comunes.

    Uso:
        api = TelegramAPI(token="123456:ABC-DEF1234")
        api.send_message(chat_id=123, text="Hola!")
        updates = api.get_updates()
    """

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str):
        self.token = token
        self._url = f"https://api.telegram.org/bot{token}"

    def _call(self, method: str, payload: Optional[dict] = None,
              timeout: int = 30) -> dict:
        """Llamar a un método de la API de Telegram."""
        url = f"{self._url}/{method}"
        result = _http_post(url, payload or {}, timeout=timeout)
        if not result.get("ok") and "error" not in result:
            return {"ok": False, "error": result.get("description", "unknown")}
        return result

    def get_updates(self, offset: Optional[int] = None,
                    timeout: int = 30,
                    allowed_updates: Optional[list] = None) -> list:
        """Obtener updates (mensajes nuevos) via long polling.

        Args:
            offset: ID del último update recibido + 1
            timeout: Timeout de long polling (max 60)
            allowed_updates: Tipos de updates a recibir

        Returns:
            Lista de updates, o [] si error/timeout
        """
        payload = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        if allowed_updates:
            payload["allowed_updates"] = allowed_updates

        import urllib.parse
        query = urllib.parse.urlencode(payload, doseq=True)
        url = f"{self._url}/getUpdates?{query}"

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    return data.get("result", [])
                else:
                    print(f"  [TgAPI] Error getUpdates: {data.get('description', '?')}",
                          file=sys.stderr)
                    return []
        except Exception as e:
            # Timeout en long polling es normal
            if "timeout" not in str(e).lower():
                print(f"  [TgAPI] Error en getUpdates: {e}", file=sys.stderr)
            return []

    def send_message(self, chat_id: int, text: str,
                     parse_mode: str = "Markdown",
                     reply_to_message_id: Optional[int] = None,
                     disable_web_page_preview: bool = True) -> bool:
        """Enviar mensaje a un chat.

        Si falla con error de parse_mode, reintenta sin parse_mode.
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        result = self._call("sendMessage", payload)
        if result.get("ok"):
            return True
        else:
            error = result.get("error", result.get("description", "unknown"))
            # Si falla por parse_mode, reintentar sin Markdown
            if "parse" in str(error).lower():
                payload.pop("parse_mode", None)
                result = self._call("sendMessage", payload)
                return result.get("ok", False)
            print(f"  [TgAPI] Error sendMessage: {error}", file=sys.stderr)
            return False

    def send_chat_action(self, chat_id: int, action: str = "typing") -> bool:
        """Mostrar acción de chat (typing...)."""
        result = self._call("sendChatAction", {
            "chat_id": chat_id,
            "action": action,
        })
        return result.get("ok", False)

    def get_me(self) -> dict:
        """Obtener información del bot."""
        result = self._call("getMe")
        if result.get("ok"):
            return result.get("result", {})
        return {"error": result.get("error", "unknown")}

    def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Eliminar un mensaje."""
        result = self._call("deleteMessage", {
            "chat_id": chat_id,
            "message_id": message_id,
        })
        return result.get("ok", False)

    def edit_message_text(self, chat_id: int, message_id: int,
                          text: str, parse_mode: str = "Markdown") -> bool:
        """Editar un mensaje."""
        result = self._call("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        })
        return result.get("ok", False)

    @property
    def bot_name(self) -> str:
        """Nombre del bot (cacheado)."""
        if not hasattr(self, "_bot_name_cache"):
            me = self.get_me()
            self._bot_name_cache = me.get("username", "UnknownBot") if "error" not in me else "UnknownBot"
        return self._bot_name_cache

    @property
    def is_valid(self) -> bool:
        """Verificar si el token es válido."""
        me = self.get_me()
        return "error" not in me


# ══════════════════════════════════════════════════════════════════════════
#  Ollama Chat Helper
# ══════════════════════════════════════════════════════════════════════════

def ollama_chat(model: str, messages: list,
                ollama_url: str = "http://127.0.0.1:11434",
                temperature: float = 0.7, max_tokens: int = 800,
                timeout: int = 180) -> str:
    """Enviar chat a Ollama y obtener respuesta.

    Args:
        model: Nombre del modelo (ej: "qwen2.5:3b")
        messages: Lista de mensajes [{"role": "user", "content": "..."}]
        ollama_url: URL del servidor Ollama
        temperature: Temperatura de generación
        max_tokens: Máximo de tokens a generar
        timeout: Timeout en segundos

    Returns:
        Texto de respuesta, o "[ERROR] ..." si falla
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    result = _http_post(f"{ollama_url}/api/chat", payload, timeout=timeout)
    if "error" in result:
        return f"[ERROR] Ollama: {result['error']}"
    return result.get("message", {}).get("content", "") or ""


def ollama_list_models(ollama_url: str = "http://127.0.0.1:11434") -> list:
    """Listar modelos disponibles en Ollama."""
    result = _http_get(f"{ollama_url}/api/tags", timeout=10)
    if "error" in result:
        return []
    return [m["name"] for m in result.get("models", [])]


# ══════════════════════════════════════════════════════════════════════════
#  ConversationState — Historial por chat
# ══════════════════════════════════════════════════════════════════════════

class ConversationState:
    """Mantiene el historial de conversaciones por chat.

    Persiste en un archivo JSON para sobrevivir reinicios.
    Cada chat tiene su propio historial de mensajes.

    Uso:
        state = ConversationState("tg_state.json")
        state.add_message("12345", "user", "Hola!")
        history = state.get_history("12345")
        state.save()
    """

    def __init__(self, state_path: str = ""):
        self.state_path = Path(state_path) if state_path else (
            SCRIPT_DIR / "hera_telegram_state.json"
        )
        self.max_history = 20  # pares de mensaje por chat
        self._data = self._load()

    def _load(self) -> dict:
        """Cargar estado desde archivo."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "version": 2,
            "last_update_id": 0,
            "chats": {},
            "created": datetime.now().isoformat(),
        }

    def save(self):
        """Guardar estado a archivo."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"  [WARN] No se pudo guardar estado: {e}", file=sys.stderr)

    @property
    def last_update_id(self) -> int:
        return self._data.get("last_update_id", 0)

    @last_update_id.setter
    def last_update_id(self, value: int):
        self._data["last_update_id"] = max(value, self.last_update_id)

    def get_history(self, chat_id: str) -> list:
        """Obtener historial de mensajes de un chat."""
        chat = self._data.get("chats", {}).get(str(chat_id), {})
        return chat.get("messages", [])

    def add_message(self, chat_id: str, role: str, content: str,
                    user_name: str = ""):
        """Añadir un mensaje al historial de un chat."""
        chat_id = str(chat_id)
        chats = self._data.setdefault("chats", {})

        if chat_id not in chats:
            chats[chat_id] = {
                "user_name": user_name,
                "messages": [],
                "created": datetime.now().isoformat(),
            }

        chat = chats[chat_id]
        chat["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        chat["last_activity"] = datetime.now().isoformat()
        if user_name:
            chat["user_name"] = user_name

        # Limitar historial
        max_msgs = self.max_history * 2
        if len(chat["messages"]) > max_msgs:
            chat["messages"] = chat["messages"][-max_msgs:]

    def get_user_name(self, chat_id: str) -> str:
        """Obtener nombre de usuario de un chat."""
        return self._data.get("chats", {}).get(str(chat_id), {}).get("user_name", "")

    def clear_chat(self, chat_id: str):
        """Limpiar historial de un chat."""
        chat_id = str(chat_id)
        name = self.get_user_name(chat_id)
        self._data.setdefault("chats", {})[chat_id] = {
            "user_name": name,
            "messages": [],
            "created": datetime.now().isoformat(),
            "cleared": datetime.now().isoformat(),
        }

    def list_chats(self) -> List[Dict[str, Any]]:
        """Listar todos los chats conocidos con metadata."""
        result = []
        for chat_id, info in self._data.get("chats", {}).items():
            result.append({
                "chat_id": chat_id,
                "user_name": info.get("user_name", "?"),
                "last_activity": info.get("last_activity", "?"),
                "messages": len(info.get("messages", [])),
            })
        return sorted(result, key=lambda c: c["last_activity"], reverse=True)


# ══════════════════════════════════════════════════════════════════════════
#  TelegramAgent — Lógica de negocio del bot
# ══════════════════════════════════════════════════════════════════════════

# System prompt por defecto para el chat con IA
HERA_TELEGRAM_SYSTEM_PROMPT = """Eres HERA, la asistente del ecosistema SIMMOON.

TU PERSONALIDAD:
- Profesional, directa y concisa (estilo CLI)
- Amigable pero eficiente — vas al grano
- Hablas en español con naturalidad
- Tienes conocimiento técnico profundo sobre el ecosistema SIMMOON
- Eres proactiva: si detectas un problema, lo mencionas

EL ECOSISTEMA SIMMOON:
- Eres parte del proyecto SIMMOON, una fábrica de assets con IA
- Conoces los agentes: Hermes, Jarvis, OpenHuman, Agatha, Buffy
- Sabes de los servicios: Ollama, ComfyUI, InvokeAI, PostgreSQL
- El proyecto genera imágenes pixel art estilo SimCity 2000

REGLAS:
- Responde en español SIEMPRE
- Sé concisa (1-3 párrafos máximo)
- Si no sabes algo, dilo honestamente
- Usa emojis con moderación
- Para comandos técnicos, usa formato `código`
"""


class TelegramAgent:
    """Agente de Telegram autónomo.

    Maneja el polling, comandos, chat con IA y estado del sistema.
    Puede funcionar standalone o integrarse con HeraCore.

    Uso:
        agent = TelegramAgent(token="...")
        agent.run_daemon()
    """

    def __init__(self, token: str = "",
                 ollama_url: str = "http://127.0.0.1:11434",
                 ollama_model: str = "qwen2.5:3b",
                 state_path: str = "",
                 system_prompt: str = "",
                 verbose: bool = True,
                 allowed_users: Optional[List[int]] = None):
        """
        Args:
            token: Token del bot de Telegram
            ollama_url: URL del servidor Ollama
            ollama_model: Modelo por defecto de Ollama
            state_path: Ruta al archivo de estado
            system_prompt: System prompt para chat IA
            verbose: Mostrar logs en consola
            allowed_users: Lista de user_ids permitidos (vacío = todos)
        """
        self.api = TelegramAPI(token) if token else None
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.state = ConversationState(state_path)
        self.system_prompt = system_prompt or HERA_TELEGRAM_SYSTEM_PROMPT
        self.verbose = verbose
        self.allowed_users = allowed_users or []

        # Callbacks para eventos
        self._on_message: Optional[Callable] = None  # callback(msg_dict) -> response_text
        self._on_command: Optional[Callable] = None   # callback(cmd, args, chat_id) -> response_text

        # Estadísticas
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "started_at": 0,
        }

    @property
    def is_ready(self) -> bool:
        """Verificar que el bot está listo para funcionar."""
        return self.api is not None and self.api.is_valid

    # ── Configuración dinámica ──────────────────────────────────────────

    def set_token(self, token: str):
        """Cambiar token en caliente."""
        self.api = TelegramAPI(token)

    def set_model(self, model: str):
        """Cambiar modelo en caliente."""
        self.ollama_model = model

    def register_message_handler(self, callback: Callable):
        """Registrar callback para mensajes.

        El callback recibe (msg_dict) y debe retornar str o None.
        Si retorna str, se envía como respuesta.
        """
        self._on_message = callback

    def register_command_handler(self, callback: Callable):
        """Registrar callback para comandos.

        El callback recibe (command, args, chat_id, msg_dict) y debe
        retornar str o None.
        """
        self._on_command = callback

    # ── Procesamiento de mensajes ───────────────────────────────────────

    def process_update(self, update: dict) -> Optional[str]:
        """Procesar un update de Telegram y generar respuesta.

        Args:
            update: Update de Telegram

        Returns:
            Texto de respuesta, o None si no requiere respuesta
        """
        msg = update.get("message")
        if not msg or "text" not in msg:
            return None

        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_name = user.get("first_name", "User")
        text = msg.get("text", "").strip()

        # Verificar permisos
        if self.allowed_users and chat_id not in self.allowed_users:
            return None

        # Ignorar mensajes vacíos
        if not text:
            return None

        self.stats["messages_received"] += 1
        self.state.add_message(chat_id, "user", text, user_name)

        if self.verbose:
            print(f"  📩 [{user_name}]: {text[:100]}{'...' if len(text) > 100 else ''}")

        # Comandos
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            # Comandos integrados
            response = self._handle_command(cmd, args, chat_id, msg)
            if response:
                self.state.add_message(chat_id, "assistant", response)
                return response

            # Callback externo
            if self._on_command:
                response = self._on_command(cmd, args, chat_id, msg)
                if response:
                    self.state.add_message(chat_id, "assistant", response)
                    return response

            return None

        # Mensaje normal: chat con IA
        response = self._handle_chat(chat_id, text, msg)
        if response:
            self.state.add_message(chat_id, "assistant", response)
        return response

    def _handle_command(self, cmd: str, args: str, chat_id: int,
                        msg: dict) -> Optional[str]:
        """Manejar comandos integrados."""
        user_name = msg.get("from", {}).get("first_name", "User")

        if cmd == "/start":
            return (
                f"👋 *¡Hola {user_name}!* Soy **HERA**, tu asistente del "
                f"ecosistema SIMMOON. 🤖\n\n"
                f"Estoy aquí para:\n"
                f"💻 Ayudarte con código y debugging\n"
                f"🏭 Gestionar la fábrica de assets\n"
                f"📊 Monitorear el sistema\n"
                f"💡 Responder tus preguntas\n\n"
                f"*Comandos:*\n"
                f"  /help — Ayuda completa\n"
                f"  /status — Estado del sistema\n"
                f"  /model — Ver/cambiar modelo IA\n"
                f"  /clear — Limpiar historial\n"
                f"  /stats — Estadísticas del bot\n\n"
                f"¡Pregúntame lo que necesites! 🚀"
            )

        elif cmd == "/help":
            return (
                "📖 *Comandos disponibles*\n\n"
                "💬 *Chat libre:*\n"
                "  Envía cualquier mensaje y conversamos\n\n"
                "🔧 *Comandos:*\n"
                "  /start — Saludo inicial\n"
                "  /help — Esta ayuda\n"
                "  /status — Estado del sistema\n"
                "  /clear — Borrar historial\n"
                "  /model — Ver modelo activo\n"
                "  /model <nombre> — Cambiar modelo\n"
                "  /stats — Estadísticas del bot\n"
                "  /chats — Listar chats conocidos\n"
            )

        elif cmd == "/clear":
            self.state.clear_chat(chat_id)
            return "🧹 *Historial limpiado.* Empecemos de nuevo."

        elif cmd == "/model":
            if args:
                models = ollama_list_models(self.ollama_url)
                if args in models:
                    self.ollama_model = args
                    return f"✅ Modelo cambiado a `{args}`"
                else:
                    avail = ", ".join(f"`{m}`" for m in models[:8])
                    return (f"❌ Modelo `{args}` no encontrado.\n\n"
                            f"Disponibles: {avail}")
            else:
                return (f"🧠 Modelo activo: `{self.ollama_model}`\n\n"
                        f"Para cambiar: `/model <nombre>`")

        elif cmd == "/status":
            return (
                "📊 *Estado del sistema:*\n\n"
                "Usa el dashboard web o pregúntame directamente "
                "qué servicio quieres verificar."
            )

        elif cmd == "/stats":
            uptime = time.time() - self.stats["started_at"]
            chats = len(self.state.list_chats())
            return (
                "📊 *Estadísticas de HERA Telegram*\n\n"
                f"⏱️  Uptime: {uptime:.0f}s\n"
                f"📨 Mensajes recibidos: {self.stats['messages_received']}\n"
                f"📤 Mensajes enviados: {self.stats['messages_sent']}\n"
                f"💬 Chats activos: {chats}\n"
                f"🧠 Modelo: `{self.ollama_model}`\n"
                f"❌ Errores: {self.stats['errors']}"
            )

        elif cmd == "/chats":
            chats = self.state.list_chats()
            if not chats:
                return "📭 No hay chats activos."
            lines = ["📋 *Chats activos:*\n"]
            for c in chats[:10]:
                lines.append(
                    f"  🆔 `{c['chat_id']}` | 👤 {c['user_name']} "
                    f"| {c['messages']} msgs"
                )
            return "\n".join(lines)

        return None

    def _handle_chat(self, chat_id: int, text: str,
                     msg: dict) -> Optional[str]:
        """Manejar chat libre con IA vía Ollama.

        Usa el historial de la conversación como contexto.
        """
        # Construir mensajes para Ollama
        messages = [{"role": "system", "content": self.system_prompt}]
        history = self.state.get_history(chat_id)
        for h in history[-16:]:  # últimos 8 intercambios
            if h["role"] == "system":
                continue
            messages.append({"role": h["role"], "content": h["content"]})

        # Generar respuesta
        response = ollama_chat(
            model=self.ollama_model,
            messages=messages,
            ollama_url=self.ollama_url,
            temperature=0.7,
            max_tokens=800,
        )

        if response.startswith("[ERROR]"):
            return f"⚠️ {response}"

        # Truncar para Telegram (límite 4096)
        if len(response) > 4000:
            response = response[:4000] + "\\n\\n_(mensaje truncado)_"

        return response

    # ── Envío de mensajes (proactivo) ───────────────────────────────────

    def send(self, chat_id: int, text: str,
             parse_mode: str = "Markdown",
             reply_to_msg_id: Optional[int] = None) -> bool:
        """Enviar mensaje a un chat.

        Args:
            chat_id: ID del chat destino
            text: Texto del mensaje
            parse_mode: Modo de parseo (Markdown, HTML, "")
            reply_to_msg_id: ID del mensaje al que responde

        Returns:
            True si se envió correctamente
        """
        if not self.api:
            return False

        if len(text) > 4000:
            text = text[:4000] + "\\n\\n_(mensaje truncado)_"

        ok = self.api.send_message(
            chat_id, text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_msg_id,
        )
        if ok:
            self.stats["messages_sent"] += 1
        else:
            self.stats["errors"] += 1
        return ok

    def send_to_all(self, text: str, parse_mode: str = "Markdown") -> int:
        """Enviar mensaje a todos los chats conocidos.

        Args:
            text: Texto del mensaje
            parse_mode: Modo de parseo

        Returns:
            Número de chats a los que se envió
        """
        count = 0
        for chat_info in self.state.list_chats():
            try:
                chat_id = int(chat_info["chat_id"])
                if self.send(chat_id, text, parse_mode):
                    count += 1
            except (ValueError, TypeError):
                continue
        return count

    # ── Daemon (polling loop) ───────────────────────────────────────────

    def run_daemon(self, poll_interval: float = 2.0,
                   max_consecutive_errors: int = 50):
        """Ejecutar el bot en modo daemon (sondeo continuo).

        Args:
            poll_interval: Intervalo entre polls en segundos
            max_consecutive_errors: Máximo de errores antes de pausar
        """
        if not self.is_ready:
            print("❌ Bot no configurado. Usa set_token() o pasa token al constructor.",
                  file=sys.stderr)
            return

        self.stats["started_at"] = time.time()
        bot_name = self.api.bot_name
        consecutive_errors = 0

        print(f"\\n  {'='*55}")
        print(f"  🤖 HERA Telegram Agent — ACTIVO")
        print(f"  📱 Bot: @{bot_name}")
        print(f"  🧠 Modelo: {self.ollama_model}")
        print(f"  🔄 Polling cada {poll_interval}s")
        print(f"  {'='*55}")
        print(f"\\n  Esperando mensajes... (Ctrl+C para detener)\\n")

        try:
            while True:
                try:
                    offset = self.state.last_update_id + 1
                    updates = self.api.get_updates(offset=offset, timeout=30)

                    if updates:
                        consecutive_errors = 0
                        for update in updates:
                            update_id = update.get("update_id", 0)
                            response = self.process_update(update)

                            if response:
                                msg = update.get("message", {})
                                chat_id = msg.get("chat", {}).get("id")
                                msg_id = msg.get("message_id")

                                if chat_id:
                                    # Mostrar typing mientras procesa
                                    self.api.send_chat_action(chat_id, "typing")
                                    time.sleep(0.3)

                                    # Enviar respuesta
                                    self.api.send_message(
                                        chat_id, response,
                                        reply_to_message_id=msg_id,
                                    )
                                    self.stats["messages_sent"] += 1

                                    if self.verbose:
                                        preview = response[:80].replace("\\n", " ")
                                        print(f"  📤 [HERA]: {preview}{'...' if len(response) > 80 else ''}")

                            # Actualizar offset
                            if update_id >= self.state.last_update_id:
                                self.state.last_update_id = update_id
                                self.state.save()

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    consecutive_errors += 1
                    self.stats["errors"] += 1
                    print(f"  ⚠️  Error en ciclo: {e}", file=sys.stderr)
                    if consecutive_errors > max_consecutive_errors:
                        print("  ⚠️  Demasiados errores consecutivos. Pausando 30s...",
                              file=sys.stderr)
                        consecutive_errors = 0
                        time.sleep(30)
                    else:
                        time.sleep(5)

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print(f"\\n\\n  👋 HERA Telegram Agent detenido.")
            print(f"  📊 Procesados: {self.stats['messages_received']} mensajes, "
                  f"{self.stats['messages_sent']} respuestas\\n")
            self.state.save()

    # ── Estado ──────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Estado actual del agente."""
        uptime = 0
        if self.stats["started_at"]:
            uptime = time.time() - self.stats["started_at"]

        return {
            "ready": self.is_ready,
            "bot_name": self.api.bot_name if self.api else "",
            "model": self.ollama_model,
            "ollama_url": self.ollama_url,
            "uptime": round(uptime, 1),
            "stats": dict(self.stats),
            "chats": len(self.state.list_chats()),
            "allowed_users": len(self.allowed_users),
        }

    def status_text(self) -> str:
        """Estado formateado como texto."""
        s = self.status()
        return (
            f"  🤖 HERA Telegram Agent\\n"
            f"  {'='*40}\\n"
            f"  Bot: @{s['bot_name']}\\n"
            f"  Estado: {'✅ Listo' if s['ready'] else '❌ No configurado'}\\n"
            f"  Modelo: {s['model']}\\n"
            f"  Uptime: {s['uptime']}s\\n"
            f"  Mensajes: {s['stats']['messages_received']} recibidos, "
            f"{s['stats']['messages_sent']} enviados\\n"
            f"  Chats: {s['chats']}\\n"
            f"  {'='*40}"
        )


# ══════════════════════════════════════════════════════════════════════════
#  HeraTelegramAgent — Integración con HeraCore
# ══════════════════════════════════════════════════════════════════════════

class HeraTelegramAgent:
    """Adaptador de Telegram para HeraCore.

    Se conecta al MessageBus de Hera y al Vault para:
      - Recibir tokens del Vault
      - Reportar mensajes de Telegram como tasks/messages en el bus
      - Enviar mensajes proactivos desde el bus a Telegram

    Uso:
        from hera import HeraCore
        from hera.agents import HeraTelegramAgent

        hera = HeraCore()
        tg = HeraTelegramAgent()
        tg.attach(hera)  # Lee token del Vault automáticamente
        hera.start()
        tg.run_daemon()
    """

    def __init__(self, token: str = "",
                 ollama_url: str = "http://127.0.0.1:11434",
                 ollama_model: str = "qwen2.5:3b",
                 verbose: bool = True):
        """
        Args:
            token: Token de Telegram (si se pasa, no usa Vault)
            ollama_url: URL de Ollama
            ollama_model: Modelo de Ollama
            verbose: Mostrar logs
        """
        self.token = token
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.verbose = verbose

        # Componentes
        self._agent: Optional[TelegramAgent] = None
        self._hera: Optional[Any] = None
        self._vault: Optional[Any] = None

    def attach(self, hera: Any):
        """Conectar a HeraCore.

        Args:
            hera: Instancia de HeraCore
        """
        # Import local para evitar circular imports
        from ..core import Message as HeraMessage
        from ..vault import Vault

        self._hera = hera
        self._vault = Vault()

        # Cargar token desde Vault si no se especificó
        if not self.token:
            self.token = self._vault.get("telegram_token") or ""

        if not self.token:
            print("  ⚠️  [HeraTelegram] No hay token configurado. "
                  "Usa Vault o pasa token explícitamente.",
                  file=sys.stderr)

        # Crear agente interno
        self._agent = TelegramAgent(
            token=self.token,
            ollama_url=self.ollama_url,
            ollama_model=self.ollama_model,
            verbose=self.verbose,
        )

        # Registrarse como agente en Hera
        hera.register_agent(
            "hera-telegram",
            ["telegram", "messaging", "notify"],
            description="Hera Telegram — adaptador de mensajería",
        )

        # Registrar worker para tareas relacionadas a Telegram
        def telegram_worker(task):
            action = task.action
            payload = task.payload

            if action == "send":
                chat_id = payload.get("chat_id", 0)
                text = payload.get("text", "")
                if chat_id and text:
                    ok = self._agent.send(chat_id, text)
                    return f"sent={ok}" if ok else "failed"
                return "missing_params"

            elif action == "broadcast":
                text = payload.get("text", "")
                if text:
                    count = self._agent.send_to_all(text)
                    return f"sent_to={count}"
                return "missing_text"

            elif action == "status":
                return json.dumps(self._agent.status(), indent=2)

            elif action == "set_model":
                model = payload.get("model", "")
                if model:
                    self._agent.set_model(model)
                    return f"model={model}"
                return "missing_model"

            return None

        hera.register_worker("hera-telegram", telegram_worker)

        # Conectar mensajes entrantes al bus de Hera
        def on_incoming_message(msg_dict):
            """Cuando llega un mensaje, publicarlo en el bus."""
            if not self._hera:
                return None

            chat_id = msg_dict.get("chat", {}).get("id")
            text = msg_dict.get("text", "")
            user = msg_dict.get("from", {}).get("first_name", "User")

            if not text:
                return None

            # Publicar en el bus
            self._hera.send(HeraMessage(
                sender="hera-telegram",
                target="broadcast",
                action="telegram.message",
                payload={
                    "chat_id": chat_id,
                    "user": user,
                    "text": text,
                    "raw": msg_dict,
                },
            ))

            # No interferir con la respuesta normal del agente
            return None

        self._agent.register_message_handler(on_incoming_message)

        # Conectar mensajes del bus a Telegram
        def on_bus_message(msg):
            """Cuando llega un mensaje del bus, reenviarlo a Telegram si aplica."""
            if not self._agent:
                return

            # Responder a comandos de notificación
            if msg.action == "telegram.send":
                chat_id = msg.payload.get("chat_id")
                text = msg.payload.get("text", "")
                if chat_id and text:
                    self._agent.send(chat_id, text)

            elif msg.action == "telegram.broadcast":
                text = msg.payload.get("text", "")
                if text:
                    self._agent.send_to_all(text)

        hera.bus.subscribe("hera-telegram", on_bus_message)

        if self.verbose:
            print(f"  ✅ [HeraTelegram] Conectado a HeraCore")

        # Verificar secretos requeridos
        if not self.token:
            print(f"  ⚠️  [HeraTelegram] Token de Telegram no configurado. "
                  f"Usa Vault.register_secret('telegram_token', ...)",
                  file=sys.stderr)

    @property
    def agent(self) -> Optional[TelegramAgent]:
        """Acceder al agente interno de Telegram."""
        return self._agent

    def run_daemon(self, **kwargs):
        """Ejecutar el daemon de polling.

        Args pasados directamente a TelegramAgent.run_daemon()
        """
        if not self._agent:
            print("❌ [HeraTelegram] No conectado. Usa attach(hera) primero.",
                  file=sys.stderr)
            return
        if not self._agent.is_ready:
            print("❌ [HeraTelegram] Bot no configurado (sin token válido).",
                  file=sys.stderr)
            return
        self._agent.run_daemon(**kwargs)

    def send(self, chat_id: int, text: str) -> bool:
        """Enviar mensaje a un chat de Telegram."""
        if not self._agent:
            return False
        return self._agent.send(chat_id, text)

    def broadcast(self, text: str) -> int:
        """Enviar mensaje a todos los chats conocidos."""
        if not self._agent:
            return 0
        return self._agent.send_to_all(text)

    def status(self) -> Dict[str, Any]:
        """Estado del adaptador."""
        agent_status = {}
        if self._agent:
            agent_status = self._agent.status()

        return {
            "connected": self._hera is not None,
            "ready": self._agent.is_ready if self._agent else False,
            "agent": agent_status,
        }


# ══════════════════════════════════════════════════════════════════════════
#  CLI / Test rápido
# ══════════════════════════════════════════════════════════════════════════

def test_agent():
    """Probar el agente sin conexión a Telegram."""
    print(f"\\n  🧪 HERA Telegram Agent — Test\\n")

    # Probar con token vacío (solo validar estructura)
    agent = TelegramAgent(token="test:token", verbose=True)
    print(f"  📱 Bot ready: {agent.is_ready}")
    print(f"  📊 Status: {json.dumps(agent.status(), indent=2, ensure_ascii=False)}")

    # Probar creación de HeraTelegramAgent
    htg = HeraTelegramAgent(verbose=True)
    print(f"  🔌 HeraTelegramAgent creado: {htg is not None}")

    # Probar ConversationState
    state = ConversationState()
    print(f"  💾 ConversationState version: {state._data['version']}")
    state.add_message("12345", "user", "Hola!", "TestUser")
    history = state.get_history("12345")
    print(f"  📝 Historial: {len(history)} mensajes")
    state.clear_chat("12345")
    history = state.get_history("12345")
    print(f"  🧹 Después de clear: {len(history)} mensajes")

    print(f"\\n  🧪 Test completado\\n")
    return True


def main():
    """CLI para el adaptador de Telegram."""
    import argparse

    parser = argparse.ArgumentParser(
        description="🤖 HERA Telegram Agent — Adaptador de Telegram para HERA",
    )
    parser.add_argument("--daemon", action="store_true",
                        help="Iniciar daemon de polling")
    parser.add_argument("--token", type=str, default="",
                        help="Token del bot de Telegram")
    parser.add_argument("--model", type=str, default="qwen2.5:3b",
                        help="Modelo de Ollama")
    parser.add_argument("--ollama-url", type=str, default="http://127.0.0.1:11434",
                        help="URL de Ollama")
    parser.add_argument("--test", action="store_true",
                        help="Ejecutar test de validación")
    parser.add_argument("--send", nargs=2, metavar=("CHAT_ID", "TEXTO"),
                        help="Enviar mensaje y salir")
    parser.add_argument("--status", action="store_true",
                        help="Mostrar estado y salir")

    args = parser.parse_args()

    if args.test:
        test_agent()
        return

    # Cargar token desde Vault si no se pasa por CLI
    token = args.token
    if not token:
        try:
            from hera.vault import Vault
            vault = Vault()
            token = vault.get("telegram_token") or ""
        except ImportError:
            pass

    agent = TelegramAgent(
        token=token,
        ollama_url=args.ollama_url,
        ollama_model=args.model,
    )

    if args.status:
        print(agent.status_text())
        return

    if args.send:
        chat_id = int(args.send[0])
        text = args.send[1]
        if agent.send(chat_id, text):
            print(f"✅ Mensaje enviado a chat {chat_id}")
        else:
            print(f"❌ Error enviando mensaje a chat {chat_id}")
        return

    if args.daemon:
        if not token:
            print("❌ No hay token. Pasa --token o configura telegram_token en Vault.")
            sys.exit(1)
        agent.run_daemon()
        return

    # Sin args: mostrar ayuda
    parser.print_help()
    print(f"\\n  🚀 Modo común: python -m hera.agents.telegram --daemon")
    print(f"  🧪 Test:       python -m hera.agents.telegram --test")


if __name__ == "__main__":
    main()
