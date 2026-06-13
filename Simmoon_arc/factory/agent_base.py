#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/agent_base.py — 🧠 Base Autónoma para Agentes FactoryGames

Proporciona la infraestructura común para que los agentes (Creativo,
Guionista, etc.) operen de forma autónoma: loop daemon, delegación
a Claude Code, persistencia de memoria y gestión de tareas.

Cada agente extiende AgentDaemon y define su propio SYSTEM_PROMPT
y lógica de decisión.
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:latest"

# ── Soft import: Claude Code Bridge (para delegar tareas a Claude) ─────
_CLAUDE_BRIDGE = None
def _get_claude_bridge():
    global _CLAUDE_BRIDGE
    if _CLAUDE_BRIDGE is None:
        try:
            from claude_code_bridge import BuffySupervisor
            _CLAUDE_BRIDGE = BuffySupervisor(verbose=False, prefer_ollama=True)
        except Exception as e:
            _CLAUDE_BRIDGE = False
    return _CLAUDE_BRIDGE if _CLAUDE_BRIDGE else None


def _extraer_json(texto: str) -> Optional[dict]:
    """Extraer el primer objeto JSON válido de un texto.

    Busca el primer '{' y el último '}' y prueba parsear.
    Útil cuando el LLM devuelve texto adicional alrededor del JSON.
    """
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio != -1 and fin != -1 and fin > inicio:
        candidato = texto[inicio:fin + 1]
        try:
            return json.loads(candidato)
        except json.JSONDecodeError:
            pass
    return None


def _consulta_llm(system_prompt: str, prompt: str, model: str = DEFAULT_MODEL,
                  temperature: float = 0.7, max_tokens: int = 2048,
                  timeout: int = 120) -> Optional[str]:
    """Consultar el LLM local (Ollama) con un system prompt personalizado."""
    full_prompt = f"{system_prompt}\n\n{prompt}"
    payload = json.dumps({
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════
#  Memoria del agente (persistencia JSON local)
# ══════════════════════════════════════════════════════════════════════════

class AgentMemory:
    """Memoria persistente del agente en un archivo JSON dentro de factory_memoria/."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.mem_dir = SCRIPT_DIR / "factory_memoria" / agent_name
        self.mem_dir.mkdir(parents=True, exist_ok=True)
        self._tasks_file = self.mem_dir / "tasks.json"
        self._decisions_file = self.mem_dir / "decisions.json"
        self._tasks = self._load(self._tasks_file)
        self._decisions = self._load(self._decisions_file)

    def _load(self, path: Path) -> list:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self, path: Path, data: list):
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"  [WARN] No se pudo guardar memoria: {e}")

    def add_task(self, task_type: str, description: str,
                 delegated_to: str = "claude", status: str = "pending"):
        """Registrar una tarea delegada."""
        entry = {
            "id": f"{self.agent_name}_{int(time.time())}_{len(self._tasks)}",
            "timestamp": datetime.now().isoformat(),
            "type": task_type,
            "description": description,
            "delegated_to": delegated_to,
            "status": status,
        }
        self._tasks.append(entry)
        self._save(self._tasks_file, self._tasks)
        return entry["id"]

    def complete_task(self, task_id: str, result: str = ""):
        """Marcar tarea como completada."""
        for t in self._tasks:
            if t["id"] == task_id:
                t["status"] = "completed"
                t["completed_at"] = datetime.now().isoformat()
                if result:
                    t["result"] = result
                break
        self._save(self._tasks_file, self._tasks)

    def pending_tasks(self) -> list:
        """Tareas pendientes (no completadas)."""
        return [t for t in self._tasks if t["status"] == "pending"]

    def recent_tasks(self, n: int = 5) -> list:
        """Últimas n tareas."""
        return self._tasks[-n:]

    def add_decision(self, decision: str, context: str = ""):
        """Registrar una decisión del agente."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "context": context,
        }
        self._decisions.append(entry)
        self._save(self._decisions_file, self._decisions)

    def recent_decisions(self, n: int = 5) -> list:
        return self._decisions[-n:]

    def summary(self) -> str:
        """Resumen de actividad del agente."""
        total = len(self._tasks)
        pending = len(self.pending_tasks())
        completed = total - pending
        return (
            f"📊 {self.agent_name}: {total} tareas totales, "
            f"{completed} completadas, {pending} pendientes"
        )


# ══════════════════════════════════════════════════════════════════════════
#  Daemon Autónomo (Base)
# ══════════════════════════════════════════════════════════════════════════

class AgentDaemon:
    """Loop autónomo para agentes FactoryGames.

    Cada agente (Creativo, Guionista) extiende esta clase y define:
      - system_prompt: su personalidad y expertise
      - decidir_siguiente_tarea(): lógica de decisión específica
    """

    def __init__(self, name: str, emoji: str, role: str,
                 model: str = DEFAULT_MODEL,
                 system_prompt: str = "",
                 verbose: bool = True,
                 interval_minutos: int = 30):
        self.name = name
        self.emoji = emoji
        self.role = role
        self.model = model
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.interval = interval_minutos * 60  # convertir a segundos

        self.memoria = AgentMemory(name.lower().replace(" ", "_"))
        self.bridge = _get_claude_bridge()

    # ── LLM ──────────────────────────────────────────────────────────

    def _preguntar(self, prompt: str, temperature: float = 0.7,
                   max_tokens: int = 2048) -> Optional[str]:
        raw = _consulta_llm(
            self.system_prompt, prompt, self.model,
            temperature, max_tokens
        )
        if not raw:
            return None
        # Eliminar posibles code fences que el LLM pueda incluir
        result = raw.strip()
        # Quitar ```json ... ``` o ``` ... ```
        if result.startswith("```"):
            # Buscar el cierre del fence
            first_newline = result.find('\n')
            if first_newline != -1:
                result = result[first_newline + 1:]
            # Quitar ``` final si existe
            if result.endswith("```"):
                result = result[:-3].strip()
            elif "```" in result:
                result = result.rsplit("```", 1)[0].strip()
        return result

    # ── Delegación a Claude ───────────────────────────────────────────

    def delegate_to_claude(self, task: str, context: str = "",
                           files: Optional[List[str]] = None) -> bool:
        """Delegar una tarea a Claude Code.

        Returns True si la delegación fue exitosa.
        """
        bridge = self.bridge
        if not bridge:
            if self.verbose:
                print(f"  ⚠️  Claude Code bridge no disponible — "
                      f"no se pudo delegar: {task[:80]}...")
            return False

        task_id = self.memoria.add_task(
            task_type=self.name.lower(),
            description=task,
            delegated_to="claude"
        )

        if self.verbose:
            print(f"\n  {self.emoji} Delegando a Claude Code...")
            print(f"     🆔 {task_id}")
            print(f"     📋 {task[:120]}...")

        try:
            # delegate_and_review retorna (resultado_str, revision_str)
            resultado_str, _ = bridge.delegate_and_review(
                task=task,
                context=context,
                files=files or [],
                effort="medium",
                timeout=300,
            )
            success = resultado_str is not None and len(resultado_str) > 0
        except Exception as e:
            if self.verbose:
                print(f"     ❌ Error: {e}")
            success = False

        if success:
            self.memoria.complete_task(task_id, "Delegado a Claude exitosamente")
            if self.verbose:
                print(f"     ✅ Delegado exitosamente")
        else:
            # No marcar como completada — queda pendiente para reintento
            if self.verbose:
                print(f"     ❌ Falló la delegación")

        return success

    # ── Lógica de decisión (override en cada subclase) ────────────────

    def decidir_siguiente_tarea(self) -> Optional[Dict[str, Any]]:
        """Decidir qué tarea delegar a continuación.

        Returns:
            Dict con 'task', 'context', 'files' o None si no hay nada que hacer.
        """
        raise NotImplementedError("Cada agente define su propia lógica de decisión")

    # ── Loop principal ────────────────────────────────────────────────

    def run_once(self) -> bool:
        """Ejecutar un ciclo de decisión + delegación.

        Returns:
            True si se delegó alguna tarea.
        """
        ahora = datetime.now().strftime("%H:%M")
        if self.verbose:
            print(f"\n  {self.emoji} [{ahora}] {self.name} — ciclo de decisión")

        # 1. Revisar estado actual
        pendientes = self.memoria.pending_tasks()
        if pendientes:
            if self.verbose:
                print(f"     ⏳ {len(pendientes)} tarea(s) pendiente(s) de Claude")

        # 2. Decidir siguiente tarea
        decision = self.decidir_siguiente_tarea()
        if not decision:
            if self.verbose:
                print(f"     ℹ️  Sin tareas nuevas por ahora")
            return False

        # 3. Delegar
        ok = self.delegate_to_claude(
            task=decision.get("task", ""),
            context=decision.get("context", ""),
            files=decision.get("files"),
        )

        # 4. Registrar decisión
        self.memoria.add_decision(
            decision=f"Delegar: {decision.get('task', '')[:80]}...",
            context=json.dumps(decision, ensure_ascii=False)
        )

        return ok

    def run_daemon(self, interval_minutos: Optional[int] = None):
        """Ejecutar el agente en modo daemon (loop infinito).

        Args:
            interval_minutos: Intervalo entre ciclos (default: el de __init__)
        """
        if interval_minutos:
            self.interval = interval_minutos * 60

        banner = (
            f"\n  {'='*55}\n"
            f"  {self.emoji} {self.name} — Modo Autónomo\n"
            f"  {'='*55}\n"
            f"  Rol: {self.role}\n"
            f"  Modelo: {self.model}\n"
            f"  Intervalo: cada {self.interval//60} min\n"
            f"  Memoria: {self.memoria.mem_dir}\n"
            f"  {'='*55}\n"
        )
        print(banner)

        # Primer ciclo inmediato
        self.run_once()

        try:
            while True:
                proximo = datetime.now() + timedelta(seconds=self.interval)
                print(f"\n  ⏳ Próximo ciclo a las "
                      f"{proximo.strftime('%H:%M:%S')}...")
                print(f"  Presiona Ctrl+C para detener.\n")

                # Esperar en intervalos pequeños para permitir Ctrl+C
                tiempo_restante = self.interval
                while tiempo_restante > 0:
                    time.sleep(min(5, tiempo_restante))
                    tiempo_restante -= 5

                self.run_once()
        except KeyboardInterrupt:
            print(f"\n  🛑 {self.name} detenido.\n")
        except Exception as e:
            print(f"\n  ❌ Error en daemon: {e}\n")

    # ── Estado ────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Estado actual del agente."""
        bridge_ok = self.bridge is not None
        return {
            "name": self.name,
            "emoji": self.emoji,
            "role": self.role,
            "model": self.model,
            "bridge_disponible": bridge_ok,
            "tareas_totales": len(self.memoria._tasks),
            "tareas_pendientes": len(self.memoria.pending_tasks()),
            "ultimas_decisiones": self.memoria.recent_decisions(3),
        }

    def status_text(self) -> str:
        """Estado formateado como texto."""
        s = self.status()
        bridge_icon = "✅" if s["bridge_disponible"] else "❌"
        return (
            f"\n  {s['emoji']} {s['name']}\n"
            f"     Rol: {s['role']}\n"
            f"     Modelo: {s['model']}\n"
            f"     {bridge_icon} Bridge Claude: "
            f"{'disponible' if s['bridge_disponible'] else 'no disponible'}\n"
            f"     📊 {s['tareas_totales']} tareas, "
            f"{s['tareas_pendientes']} pendientes\n"
        )
