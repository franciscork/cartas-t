#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hera/core.py — Núcleo del Sistema de Agentes HERA 🏛️

Proporciona:
  - Message: protocolo de comunicación entre agentes
  - Task: unidad de trabajo en la cola
  - TaskQueue: cola persistente con SQLite
  - MessageBus: sistema pub/sub entre agentes
  - HeraCore: orquestador principal

Uso:
    from hera import HeraCore, Message

    hera = HeraCore()
    hera.start()

    # Enviar mensaje a un agente
    msg = Message(sender="buffy", target="claude-code",
                  action="refactor", payload={"file": "x.py"})
    hera.send(msg)

    # Encargar tarea
    task_id = hera.enqueue("claude-code", "refactor",
                           {"file": "x.py"}, priority=5)

    # Ver estado
    print(hera.status())
"""

import json
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any


# ── Encoding fix for Windows ───────────────────────────────────────────────
import sys
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Ruta de la base de datos ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
DEFAULT_DB_PATH = SCRIPT_DIR / "hera_tasks.db"


# ══════════════════════════════════════════════════════════════════════════
#  Modelos de Datos
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Message:
    """Protocolo de comunicación entre agentes del ecosistema HERA.

    Cada mensaje tiene un remitente, destinatario, acción y payload.
    Soporta respuestas (reply_to) y prioridades.
    """
    sender: str                          # Agente que envía (ej: "buffy")
    target: str                          # Agente destino o "broadcast"
    action: str                          # Acción a realizar (ej: "refactor", "chat")
    payload: dict = field(default_factory=dict)  # Datos de la tarea
    id: str = ""                         # UUID del mensaje
    priority: int = 5                    # 0-10, mayor = más importante
    timestamp: float = 0.0               # Tiempo de creación
    reply_to: str = ""                   # ID del mensaje al que responde
    status: str = "pending"              # pending | processing | done | failed

    def __post_init__(self):
        if not self.id:
            self.id = f"msg_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(**data)

    @classmethod
    def from_json(cls, text: str) -> "Message":
        return cls.from_dict(json.loads(text))

    def reply(self, action: str = "", payload: Optional[dict] = None) -> "Message":
        """Crear un mensaje de respuesta a este mensaje."""
        return Message(
            sender=self.target,
            target=self.sender,
            action=action or self.action,
            payload=payload or {},
            reply_to=self.id,
            priority=self.priority,
        )


@dataclass
class Task:
    """Una unidad de trabajo encolada para un agente.

    Similar a Message pero con tracking de estado, intentos y resultado.
    """
    agent: str                           # Agente responsable
    action: str                          # Acción a ejecutar
    payload: dict = field(default_factory=dict)  # Datos de la tarea
    id: str = ""                         # UUID de la tarea
    priority: int = 5                    # 0-10, mayor = más importante
    status: str = "pending"              # pending | processing | done | failed
    created_at: float = 0.0              # Timestamp de creación
    started_at: Optional[float] = None   # Timestamp de inicio
    finished_at: Optional[float] = None  # Timestamp de fin
    attempts: int = 0                    # Intentos de ejecución
    max_attempts: int = 3                # Máximo de reintentos
    result: Optional[str] = None         # Output de la ejecución
    error: Optional[str] = None          # Error si falló
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def duration(self) -> Optional[float]:
        """Duración de la ejecución en segundos."""
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None

    @property
    def age(self) -> float:
        """Tiempo desde que se creó la tarea."""
        return time.time() - self.created_at

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**data)

    @classmethod
    def from_message(cls, msg: Message) -> "Task":
        """Crear una Task a partir de un Message."""
        return cls(
            agent=msg.target,
            action=msg.action,
            payload=msg.payload,
            priority=msg.priority,
            tags=[f"msg:{msg.id}", msg.sender],
        )


# ══════════════════════════════════════════════════════════════════════════
#  TaskQueue — Cola Persistente con SQLite
# ══════════════════════════════════════════════════════════════════════════

class TaskQueue:
    """Cola de tareas persistente con SQLite.

    Las tareas se almacenan en SQLite para persistencia entre reinicios.
    Soporta prioridades, reintentos y filtering por estado/agente.

    Uso:
        queue = TaskQueue("hera_tasks.db")
        queue.enqueue(Task(agent="claude", action="refactor", payload={}))
        task = queue.dequeue()
        queue.ack(task.id)
    """

    def __init__(self, db_path: str = str(DEFAULT_DB_PATH)):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Crear la tabla de tareas si no existe."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        agent TEXT NOT NULL,
                        action TEXT NOT NULL,
                        payload TEXT NOT NULL DEFAULT '{}',
                        priority INTEGER NOT NULL DEFAULT 5,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at REAL NOT NULL,
                        started_at REAL,
                        finished_at REAL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 3,
                        result TEXT,
                        error TEXT,
                        tags TEXT NOT NULL DEFAULT '[]'
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_status
                    ON tasks(status)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_agent
                    ON tasks(agent)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_priority
                    ON tasks(priority DESC)
                """)
                conn.commit()
            finally:
                conn.close()

    def _to_row(self, task: Task) -> tuple:
        """Convertir Task a tupla para SQLite."""
        return (
            task.id, task.agent, task.action,
            json.dumps(task.payload, ensure_ascii=False),
            task.priority, task.status, task.created_at,
            task.started_at, task.finished_at, task.attempts,
            task.max_attempts, task.result, task.error,
            json.dumps(task.tags),
        )

    def _from_row(self, row: tuple) -> Task:
        """Convertir fila de SQLite a Task."""
        return Task(
            id=row[0], agent=row[1], action=row[2],
            payload=json.loads(row[3]),
            priority=row[4], status=row[5], created_at=row[6],
            started_at=row[7], finished_at=row[8],
            attempts=row[9], max_attempts=row[10],
            result=row[11], error=row[12],
            tags=json.loads(row[13]),
        )

    # ── Operaciones básicas ─────────────────────────────────────────────

    def enqueue(self, task: Task) -> str:
        """Añadir una tarea a la cola. Retorna el ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO tasks
                       (id, agent, action, payload, priority, status,
                        created_at, started_at, finished_at, attempts,
                        max_attempts, result, error, tags)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    self._to_row(task),
                )
                conn.commit()
            finally:
                conn.close()
        return task.id

    def dequeue(self, agent: Optional[str] = None,
                timeout: float = 0) -> Optional[Task]:
        """Obtener la siguiente tarea pendiente (FIFO con prioridad).

        Args:
            agent: Filtrar por agente específico
            timeout: Timeout en segundos para esperar (0 = no esperar)

        Returns:
            Task o None si no hay tareas pendientes
        """
        started = time.time()
        while True:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    if agent:
                        cursor = conn.execute(
                            """SELECT * FROM tasks
                               WHERE status = 'pending' AND agent = ?
                               ORDER BY priority DESC, created_at ASC
                               LIMIT 1""",
                            (agent,),
                        )
                    else:
                        cursor = conn.execute(
                            """SELECT * FROM tasks
                               WHERE status = 'pending'
                               ORDER BY priority DESC, created_at ASC
                               LIMIT 1"""
                        )
                    row = cursor.fetchone()
                    if row:
                        task = self._from_row(row)
                        task.status = "processing"
                        task.started_at = time.time()
                        task.attempts += 1
                        conn.execute(
                            """UPDATE tasks
                               SET status = 'processing', started_at = ?,
                                   attempts = ?
                               WHERE id = ?""",
                            (task.started_at, task.attempts, task.id),
                        )
                        conn.commit()
                        return task
                finally:
                    conn.close()

            if timeout <= 0 or (time.time() - started) >= timeout:
                return None
            time.sleep(0.1)

    def ack(self, task_id: str, result: str = "") -> bool:
        """Marcar tarea como completada exitosamente."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(
                    """UPDATE tasks
                       SET status = 'done', finished_at = ?, result = ?
                       WHERE id = ? AND status = 'processing'""",
                    (time.time(), result, task_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def nack(self, task_id: str, error: str = "") -> bool:
        """Marcar tarea como fallida. Reintenta si quedan intentos."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                # Obtener intentos actuales
                cursor = conn.execute(
                    "SELECT attempts, max_attempts FROM tasks WHERE id = ?",
                    (task_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return False
                attempts, max_attempts = row

                if attempts >= max_attempts:
                    # Sin reintentos: marcar como failed
                    conn.execute(
                        """UPDATE tasks
                           SET status = 'failed', finished_at = ?, error = ?
                           WHERE id = ?""",
                        (time.time(), error, task_id),
                    )
                else:
                    # Reintentar: volver a pending
                    conn.execute(
                        """UPDATE tasks
                           SET status = 'pending', error = ?
                           WHERE id = ?""",
                        (error, task_id),
                    )
                conn.commit()
                return True
            finally:
                conn.close()

    # ── Consultas ───────────────────────────────────────────────────────

    def get(self, task_id: str) -> Optional[Task]:
        """Obtener una tarea por ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task_id,)
                )
                row = cursor.fetchone()
                return self._from_row(row) if row else None
            finally:
                conn.close()

    def list(self, status: Optional[str] = None,
             agent: Optional[str] = None,
             limit: int = 50) -> List[Task]:
        """Listar tareas con filtros opcionales."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                query = "SELECT * FROM tasks WHERE 1=1"
                params = []
                if status:
                    query += " AND status = ?"
                    params.append(status)
                if agent:
                    query += " AND agent = ?"
                    params.append(agent)
                query += " ORDER BY priority DESC, created_at DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                return [self._from_row(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def stats(self) -> Dict[str, Any]:
        """Estadísticas de la cola."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(
                    """SELECT status, COUNT(*) as count
                       FROM tasks GROUP BY status"""
                )
                by_status = {row[0]: row[1] for row in cursor.fetchall()}

                cursor = conn.execute(
                    """SELECT agent, COUNT(*) as count
                       FROM tasks WHERE status = 'pending'
                       GROUP BY agent"""
                )
                pending_by_agent = {row[0]: row[1]
                                    for row in cursor.fetchall()}

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tasks"
                )
                total = cursor.fetchone()[0]

                return {
                    "total": total,
                    "by_status": by_status,
                    "pending_by_agent": pending_by_agent,
                    "db_path": self.db_path,
                }
            finally:
                conn.close()

    def clear(self, status: Optional[str] = None) -> int:
        """Limpiar tareas (opcionalmente por estado)."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                if status:
                    cursor = conn.execute(
                        "DELETE FROM tasks WHERE status = ?", (status,)
                    )
                else:
                    cursor = conn.execute("DELETE FROM tasks")
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()

    def cancel(self, task_id: str) -> bool:
        """Cancelar una tarea pendiente."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(
                    """UPDATE tasks SET status = 'failed',
                       finished_at = ?, error = 'cancelled'
                       WHERE id = ? AND status = 'pending'""",
                    (time.time(), task_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def cleanup(self, max_age_hours: float = 24):
        """Eliminar tareas completadas/fallidas más viejas que max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute(
                    """DELETE FROM tasks
                       WHERE status IN ('done', 'failed')
                       AND finished_at < ?""",
                    (cutoff,),
                )
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()


# ══════════════════════════════════════════════════════════════════════════
#  MessageBus — Sistema Pub/Sub entre Agentes
# ══════════════════════════════════════════════════════════════════════════

class MessageBus:
    """Sistema de mensajería publish/subscribe entre agentes.

    Los agentes se suscriben a mensajes y reciben callbacks cuando
    se publican mensajes dirigidos a ellos o broadcasts.

    Uso:
        bus = MessageBus()

        def on_message(msg):
            print(f"{msg.sender} -> {msg.target}: {msg.action}")

        bus.subscribe("buffy", on_message)
        bus.publish(Message(sender="cli", target="buffy",
                            action="status", payload={}))
    """

    def __init__(self):
        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Message] = []
        self._max_history: int = 1000
        self._lock = threading.Lock()

    # ── Suscripción ─────────────────────────────────────────────────────

    def subscribe(self, agent: str, callback: Callable[[Message], None]):
        """Suscribir un callback para mensajes dirigidos a un agente.

        Args:
            agent: Nombre del agente (ej: "buffy", "claude-code")
            callback: Función que recibe el mensaje
        """
        with self._lock:
            if callback not in self._subscriptions[agent]:
                self._subscriptions[agent].append(callback)

    def unsubscribe(self, agent: str, callback: Callable):
        """Desuscribir un callback."""
        with self._lock:
            if callback in self._subscriptions.get(agent, []):
                self._subscriptions[agent].remove(callback)

    def unsubscribe_all(self, agent: str):
        """Desuscribir todos los callbacks de un agente."""
        with self._lock:
            self._subscriptions[agent] = []

    # ── Publicación ─────────────────────────────────────────────────────

    def publish(self, message: Message) -> int:
        """Publicar un mensaje y notificar a los suscriptores.

        Args:
            message: Mensaje a publicar

        Returns:
            Número de suscriptores notificados
        """
        # Guardar en histórico
        with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        # Notificar suscriptores
        notified = 0
        targets = ["broadcast"]

        if message.target != "broadcast":
            targets.append(message.target)
            # También notificar a "broadcast" suscriptores
            if "broadcast" in self._subscriptions:
                targets.append("broadcast_before")
        else:
            # Broadcast a todos
            with self._lock:
                targets = list(self._subscriptions.keys())

        for target in targets:
            if target == "broadcast_before":
                continue
            with self._lock:
                callbacks = list(self._subscriptions.get(target, []))

            for callback in callbacks:
                try:
                    callback(message)
                    notified += 1
                except Exception as e:
                    print(f"[HERA] Error en callback de {target}: {e}",
                          file=sys.stderr)

        # Broadcast especial
        if message.target == "broadcast":
            with self._lock:
                broadcast_cbs = list(
                    self._subscriptions.get("broadcast", [])
                )
            for callback in broadcast_cbs:
                try:
                    callback(message)
                    notified += 1
                except Exception as e:
                    print(f"[HERA] Error en broadcast callback: {e}",
                          file=sys.stderr)

        return notified

    def request(self, message: Message, timeout: float = 30.0) -> Optional[Message]:
        """Publicar un mensaje y esperar una respuesta.

        Útil para petición-respuesta síncrona entre agentes.

        Args:
            message: Mensaje a publicar
            timeout: Tiempo máximo de espera en segundos

        Returns:
            Mensaje de respuesta o None si timeout
        """
        response = [None]  # Lista mutable para la closure
        event = threading.Event()

        def reply_handler(msg: Message):
            if msg.reply_to == message.id:
                response[0] = msg
                event.set()

        self.subscribe(message.sender, reply_handler)
        try:
            self.publish(message)
            event.wait(timeout=timeout)
            return response[0]
        finally:
            self.unsubscribe(message.sender, reply_handler)

    # ── Consultas ───────────────────────────────────────────────────────

    def history(self, limit: int = 50,
                agent: Optional[str] = None) -> List[Message]:
        """Obtener histórico de mensajes."""
        with self._lock:
            msgs = list(self._history)
        if agent:
            msgs = [m for m in msgs
                    if m.sender == agent or m.target == agent]
        return msgs[-limit:]

    def subscribers(self, agent: Optional[str] = None) -> Dict[str, int]:
        """Listar suscriptores y cantidad de callbacks."""
        with self._lock:
            if agent:
                return {agent: len(self._subscriptions.get(agent, []))}
            return {
                agent: len(cbs)
                for agent, cbs in self._subscriptions.items()
                if cbs
            }

    def clear_history(self):
        """Limpiar histórico de mensajes."""
        with self._lock:
            self._history = []


# ══════════════════════════════════════════════════════════════════════════
#  HeraCore — Orquestador Principal
# ══════════════════════════════════════════════════════════════════════════

class HeraCore:
    """Orquestador principal del sistema HERA.

    Coordina el MessageBus, TaskQueue y registro de agentes.
    Es el punto de entrada único para interactuar con el ecosistema.

    Uso:
        hera = HeraCore()
        hera.start()

        # Registrar un agente
        hera.register_agent("claude-code", ["coding", "refactor"])

        # Enviar mensaje
        hera.send(Message(sender="buffy", target="claude-code",
                          action="refactor", payload={"file": "x.py"}))

        # Encolar tarea
        tid = hera.enqueue("claude-code", "refactor",
                           {"file": "x.py"}, priority=8)

        # Ver estado
        print(hera.status())
    """

    def __init__(self, db_path: str = str(DEFAULT_DB_PATH),
                 verbose: bool = True):
        self.bus = MessageBus()
        self.queue = TaskQueue(db_path)
        self.verbose = verbose

        # Registro de agentes: {name: {capabilities, status, ...}}
        self._agents: Dict[str, Dict[str, Any]] = {}

        # Callbacks de workers (workers registran su callback aquí)
        self._workers: Dict[str, Callable] = {}

        # Estado interno
        self._running = False
        self._started_at: Optional[float] = None
        self._stats = {
            "messages_sent": 0,
            "tasks_enqueued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
        }

        # Auto-registrar HERA
        self.register_agent("hera", ["orchestrate", "monitor", "status"],
                            description="HERA Core — orquestador principal")

    # ── Ciclo de vida ───────────────────────────────────────────────────

    def start(self):
        """Iniciar el orquestador."""
        self._running = True
        self._started_at = time.time()
        if self.verbose:
            print(f"\n  {'='*55}")
            print(f"  🏛️  HERA Core — Iniciado")
            print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  🗄️  DB: {self.queue.db_path}")
            print(f"  {'='*55}\n")
        self._log("HERA", "Core iniciado")

    def stop(self):
        """Detener el orquestador."""
        self._running = False
        self._log("HERA", "Core detenido")
        if self.verbose:
            total = self._stats["tasks_completed"] + self._stats["tasks_failed"]
            print(f"\n  🏛️  HERA Core — Detenido")
            print(f"  📊 {total} tareas procesadas")
            if self._started_at:
                uptime = time.time() - self._started_at
                print(f"  ⏱️  Uptime: {uptime:.0f}s\n")

    @property
    def running(self) -> bool:
        return self._running

    # ── Gestión de Agentes ──────────────────────────────────────────────

    def register_agent(self, name: str,
                       capabilities: Optional[List[str]] = None,
                       description: str = "") -> bool:
        """Registrar un agente en HERA.

        Args:
            name: Nombre del agente (ej: "claude-code")
            capabilities: Lista de capacidades (ej: ["coding", "refactor"])
            description: Descripción del agente

        Returns:
            True si se registró, False si ya existía
        """
        if name in self._agents:
            return False

        self._agents[name] = {
            "name": name,
            "capabilities": capabilities or [],
            "description": description,
            "status": "registered",
            "registered_at": time.time(),
            "last_seen": time.time(),
            "tasks_processed": 0,
        }
        self._log("HERA", f"Agente registrado: {name}")
        return True

    def unregister_agent(self, name: str) -> bool:
        """Eliminar un agente del registro."""
        if name not in self._agents:
            return False
        del self._agents[name]
        self.bus.unsubscribe_all(name)
        self._workers.pop(name, None)
        self._log("HERA", f"Agente dado de baja: {name}")
        return True

    def agent_heartbeat(self, name: str):
        """Actualizar el timestamp de último contacto de un agente."""
        if name in self._agents:
            self._agents[name]["last_seen"] = time.time()
            self._agents[name]["status"] = "active"

    def register_worker(self, agent: str,
                        callback: Callable[[Task], Optional[str]]):
        """Registrar un worker (función que procesa tareas).

        El worker recibe una Task y debe retornar un string con el resultado
        o None/raise exception si falla.

        Args:
            agent: Nombre del agente
            callback: Función que procesa la tarea
        """
        self._workers[agent] = callback
        if agent not in self._agents:
            self.register_agent(agent)

        # Suscribir al bus para recibir mensajes
        def message_handler(msg: Message):
            self.send(msg)

        self.bus.subscribe(agent, message_handler)
        self._log("HERA", f"Worker registrado: {agent}")

    # ── Envío de Mensajes ───────────────────────────────────────────────

    def send(self, message: Message) -> int:
        """Enviar un mensaje a través del MessageBus.

        Args:
            message: Mensaje a enviar

        Returns:
            Número de suscriptores notificados
        """
        if not self._running and self.verbose:
            print(f"  [WARN] HERA no iniciado. Encolando mensaje '{message.id}'")

        notified = self.bus.publish(message)
        self._stats["messages_sent"] += 1
        return notified

    def request(self, message: Message,
                timeout: float = 30.0) -> Optional[Message]:
        """Enviar un mensaje y esperar respuesta."""
        return self.bus.request(message, timeout)

    # ── Cola de Tareas ──────────────────────────────────────────────────

    def enqueue(self, agent: str, action: str,
                payload: Optional[dict] = None,
                priority: int = 5,
                tags: Optional[List[str]] = None) -> str:
        """Encolar una tarea para un agente.

        Args:
            agent: Agente destino
            action: Acción a realizar
            payload: Datos de la tarea
            priority: Prioridad (0-10)
            tags: Tags para filtrado

        Returns:
            ID de la tarea creada
        """
        task = Task(
            agent=agent,
            action=action,
            payload=payload or {},
            priority=priority,
            tags=tags or [],
        )
        self.queue.enqueue(task)
        self._stats["tasks_enqueued"] += 1

        # Notificar al agente via MessageBus
        self.bus.publish(Message(
            sender="hera",
            target=agent,
            action="task.assigned",
            payload={"task_id": task.id, "action": action},
        ))

        if self.verbose:
            print(f"  📋 [{agent}] {action} (prioridad {priority}) → {task.id}")
        return task.id

    def process_next(self, agent: Optional[str] = None) -> bool:
        """Procesar la siguiente tarea de la cola.

        Args:
            agent: Procesar tarea de un agente específico

        Returns:
            True si se procesó una tarea, False si no había
        """
        task = self.queue.dequeue(agent)
        if not task:
            return False

        self._log("TASK", f"{task.agent}: {task.action} ({task.id})")

        # Buscar worker registrado
        worker = self._workers.get(task.agent)
        if worker:
            try:
                result = worker(task)
                if result is not None:
                    self.queue.ack(task.id, result)
                    self._stats["tasks_completed"] += 1
                    if self.verbose:
                        print(f"  ✅ [{task.agent}] {task.action} completado")
                else:
                    self.queue.nack(task.id, "Worker returned None")
                    self._stats["tasks_failed"] += 1
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                self.queue.nack(task.id, error)
                self._stats["tasks_failed"] += 1
                if self.verbose:
                    print(f"  ❌ [{task.agent}] {task.action}: {error}")
        else:
            # Sin worker: notificar via bus y dejar en processing
            self.bus.publish(Message(
                sender="hera",
                target=task.agent,
                action="task.assigned",
                payload={"task_id": task.id, "action": task.action,
                         "payload": task.payload},
            ))
            if self.verbose:
                print(f"  📤 [{task.agent}] Tarea delegada via bus: {task.action}")

        # Actualizar heartbeat
        self.agent_heartbeat(task.agent)
        return True

    def process_all(self, agent: Optional[str] = None,
                    max_tasks: int = 10) -> int:
        """Procesar múltiples tareas en lote.

        Args:
            agent: Filtrar por agente
            max_tasks: Máximo de tareas a procesar

        Returns:
            Número de tareas procesadas
        """
        count = 0
        for _ in range(max_tasks):
            if not self.process_next(agent):
                break
            count += 1
        return count

    def get_task(self, task_id: str) -> Optional[Task]:
        """Obtener una tarea por ID."""
        return self.queue.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancelar una tarea pendiente."""
        return self.queue.cancel(task_id)

    # ── Estado y Monitoreo ──────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Obtener estado completo del sistema HERA."""
        queue_stats = self.queue.stats()
        uptime = 0.0
        if self._started_at:
            uptime = time.time() - self._started_at

        # Salud de agentes (último heartbeat)
        now = time.time()
        agent_health = {}
        for name, info in self._agents.items():
            last_seen = info.get("last_seen", 0)
            if name == "hera":
                agent_health[name] = "active"
            elif now - last_seen < 60:
                agent_health[name] = "active"
            elif now - last_seen < 300:
                agent_health[name] = "idle"
            else:
                agent_health[name] = "unknown"

        return {
            "version": "0.1.0",
            "running": self._running,
            "uptime": round(uptime, 1),
            "agents": {
                "total": len(self._agents),
                "active": sum(1 for h in agent_health.values()
                              if h == "active"),
                "list": {
                    name: {
                        "capabilities": info["capabilities"],
                        "health": agent_health[name],
                        "tasks_processed": info["tasks_processed"],
                    }
                    for name, info in self._agents.items()
                },
            },
            "queue": queue_stats,
            "bus": {
                "messages_sent": self._stats["messages_sent"],
                "subscribers": self.bus.subscribers(),
            },
            "stats": dict(self._stats),
            "timestamp": datetime.now().isoformat(),
        }

    def status_text(self) -> str:
        """Estado formateado como texto legible."""
        s = self.status()
        lines = [
            f"\n  {'='*55}",
            f"  🏛️  HERA Core — Estado del Sistema",
            f"  {'='*55}",
            f"  Versión: {s['version']}  |  Uptime: {s['uptime']}s",
            f"",
            f"  🤖 Agentes: {s['agents']['active']}/{s['agents']['total']} activos",
        ]
        for name, info in s['agents']['list'].items():
            icon = {"active": "🟢", "idle": "🟡", "unknown": "⚫"}
            h = icon.get(info['health'], "⚫")
            caps = ", ".join(info['capabilities'][:3]) if info['capabilities'] else ""
            lines.append(f"     {h} {name:20s} {caps}")

        lines.extend([
            f"",
            f"  📋 Cola: {s['queue']['total']} tareas totales",
        ])
        by_status = s['queue'].get('by_status', {})
        for status, count in by_status.items():
            lines.append(f"     • {status}: {count}")

        lines.extend([
            f"",
            f"  📊 Stats: {s['stats']['tasks_completed']}✅ / "
            f"{s['stats']['tasks_failed']}❌ / "
            f"{s['stats']['messages_sent']}📨 mensajes",
            f"  {'='*55}\n",
        ])
        return "\n".join(lines)

    # ── Internos ────────────────────────────────────────────────────────

    def _log(self, component: str, message: str):
        """Log interno de HERA."""
        if self.verbose:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  [{ts}] [{component}] {message}")


# ══════════════════════════════════════════════════════════════════════════
#  CLI / Test Rápido
# ══════════════════════════════════════════════════════════════════════════

def test_hera():
    """Probar HERA Core con un flujo básico."""
    print("\n  🧪 HERA Core — Test\n")

    # 1. Crear instancia
    hera = HeraCore(verbose=True)
    hera.start()

    # 2. Registrar agente de prueba
    hera.register_agent("test-agent", ["testing"],
                        description="Agente de prueba")

    # 3. Encolar tarea
    tid = hera.enqueue("test-agent", "test_action",
                       {"mensaje": "hola"}, priority=5)
    print(f"  📋 Tarea encolada: {tid}")

    # 4. Ver estado
    task = hera.get_task(tid)
    print(f"  📋 Estado tarea: {task.status if task else 'no encontrada'}")

    # 5. Procesar (sin worker registrado - se delega via bus)
    processed = hera.process_next("test-agent")
    print(f"  {'✅' if processed else '❌'} Tarea procesada: {processed}")

    # 6. Registrar worker y probar de nuevo
    def mi_worker(task: Task) -> str:
        print(f"  [WORKER] Procesando: {task.action} — {task.payload}")
        return f"Resultado de {task.id}"

    hera.register_worker("test-worker", mi_worker)
    tid2 = hera.enqueue("test-worker", "otra_accion", {"data": 42})
    hera.process_next("test-worker")

    task2 = hera.get_task(tid2)
    if task2:
        print(f"  ✅ Tarea completada: {task2.status}")

    # 7. Probar MessageBus
    messages_received = []

    def test_callback(msg):
        messages_received.append(msg)

    hera.bus.subscribe("test-listener", test_callback)
    test_msg = Message(sender="hera", target="test-listener",
                       action="ping", payload={})
    hera.send(test_msg)
    print(f"  📨 Mensajes recibidos por listener: {len(messages_received)}")

    # 8. Status final
    print(hera.status_text())

    hera.stop()
    print(f"\n  🧪 Test completado — {len(messages_received)} mensajes, "
          f"2 tareas\n")
    return True


if __name__ == "__main__":
    test_hera()
