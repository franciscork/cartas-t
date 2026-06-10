#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/orchestrator.py — Orquestador Principal FactoryGames 🏭

Buffy (DeepSeek) supervisa y delega. Este es el módulo central
que coordina agentes, tareas, salud, memoria y logging.

Uso:
    from factory.orchestrator import FactoryOrchestrator
    factory = FactoryOrchestrator(verbose=True)
    factory.boot()
    factory.delegate("coding", "Refactoriza esta función", files=["archivo.py"])
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.parent.resolve()

# ── Imports del package (siempre disponibles) ─────────────────────────────
from .logging import FactoryLogger
from .agent_registry import AgentRegistry
from .task_dispatcher import TaskDispatcher
from .health_monitor import HealthMonitor

# ── Archivo de última ejecución de pipeline (para la UI bash) ───────────────
_LAST_PIPELINE_FILE = SCRIPT_DIR / ".last_pipeline.json"

def _write_last_pipeline(data: dict):
    """Escribir métricas de la última ejecución de pipeline.

    Este archivo es leído por factory.sh para mostrar el indicador
    en la sección 'Salud del Sistema' del menú interactivo.
    """
    try:
        _LAST_PIPELINE_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        pass  # Silencioso — no es crítico


# ── Soft import: AgentMemory (opcional, requiere PostgreSQL) ────────────────
_AGENT_MEMORY = None
def _get_memory():
    """Importar AgentMemory de forma lazy."""
    global _AGENT_MEMORY
    if _AGENT_MEMORY is None:
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from agent_memory import AgentMemory
            _AGENT_MEMORY = AgentMemory('factory', project='FACTORY_GAMES')
        except Exception:
            _AGENT_MEMORY = None  # None = no disponible
    return _AGENT_MEMORY


# ── Soft import: ObsidianMemory (persistencia local, siempre disponible) ─────
_OBSIDIAN_MEMORY = None
def _get_obsidian_memory():
    """Importar ObsidianMemory de forma lazy.

    ObsidianMemory es un reemplazo de AgentMemory que persiste
    en archivos Markdown dentro de un vault de Obsidian.
    No requiere PostgreSQL — funciona con sistema de archivos.
    """
    global _OBSIDIAN_MEMORY
    if _OBSIDIAN_MEMORY is None:
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from obsidian_memory import ObsidianMemory
            vault = SCRIPT_DIR / "factory_memoria"
            vault.mkdir(parents=True, exist_ok=True)
            _OBSIDIAN_MEMORY = ObsidianMemory(
                vault_path=str(vault),
                agent_name="factory",
                project="FACTORY_GAMES",
            )
        except Exception as e:
            _OBSIDIAN_MEMORY = None
    return _OBSIDIAN_MEMORY


# ══════════════════════════════════════════════════════════════════════════
#  FactoryOrchestrator
# ══════════════════════════════════════════════════════════════════════════

class FactoryOrchestrator:
    """Orquestador principal de FactoryGames.

    Coordina todos los componentes del sistema:
      - AgentRegistry: registro de agentes disponibles
      - TaskDispatcher: despacho de tareas al agente correcto
      - HealthMonitor: monitoreo y recuperación de servicios
      - FactoryLogger: logging centralizado
      - AgentMemory: persistencia en PostgreSQL
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.started_at = datetime.now()

        # ── Inicializar componentes ──
        self.logger = None
        self.registry = None
        self.dispatcher = None
        self.monitor = None
        self.memory = None

        self._init_components()

    def _init_components(self):
        """Inicializar todos los componentes del sistema."""
        self.logger = FactoryLogger(verbose=self.verbose)
        self.registry = AgentRegistry()
        self.dispatcher = TaskDispatcher(verbose=self.verbose)
        self.monitor = HealthMonitor(verbose=self.verbose)
        self._register_health_checks()

        # Agent Memory (opcional, requiere PostgreSQL)
        self.memory = _get_memory()
        if self.memory:
            self.logger.info("Orquestador", "Memoria PostgreSQL conectada")
        else:
            self.logger.info("Orquestador", "PostgreSQL no disponible — usando persistencia local")

        # Obsidian Memory (persistencia local, vault en factory_memoria/)
        self.obsidian = _get_obsidian_memory()
        if self.obsidian:
            self.logger.info("Orquestador", "ObsidianMemory activa — pipeline persistirá localmente")
        else:
            self.logger.warn("Orquestador", "ObsidianMemory no disponible")

    def _register_health_checks(self):
        """Registrar health checks para todos los servicios conocidos."""
        # Usar las health check functions del AgentRegistry
        for agent in self.registry.all():
            if agent.health_check_fn:
                self.monitor.register_check(
                    name=agent.name,
                    health_fn=agent.health_check_fn,
                    launch_fn=agent.launch_fn,
                )

    # ══════════════════════════════════════════════════════════════════
    #  Arranque
    # ══════════════════════════════════════════════════════════════════

    def boot(self):
        """Inicializar el orquestador y mostrar estado inicial."""
        banner = f"""
  {'='*55}
    🏭  FACTORY GAMES — Orchestrator v1.0
    {'='*55}
    🤖  Supervisor: Buffy (DeepSeek)
    📅  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    💻  Sistema operativo: {sys.platform}
  {'='*55}
"""
        print(banner)

        self.logger.info("Orquestador", "Sistema iniciado")
        self.logger.info("Orquestador",
                         f"Agentes registrados: {len(self.registry.all())}")

        # Mostrar estado inicial rápido
        if self.verbose:
            print(f"  📋 Agentes registrados:")
            for agent in self.registry.all():
                print(f"     • {agent.name:20s} [{agent.agent_type}] {agent.endpoint}")
            print()

            print(f"  🔍 Verificando salud de servicios...")
            self.monitor.check_all()
            results = self.monitor.get_results()
            healthy = sum(1 for h in results.values() if h)
            total = len(results)
            print(f"     ✅ {healthy}/{total} servicios saludables\n")

            if self.memory:
                print(f"  💾 Memoria: PostgreSQL activa\n")

    # ══════════════════════════════════════════════════════════════════
    #  Delegación de tareas
    # ══════════════════════════════════════════════════════════════════

    def delegate(self, task_type: str, task: str,
                 files: Optional[List[str]] = None,
                 context: str = "",
                 effort: str = "high",
                 **kwargs) -> dict:
        """Delegar una tarea al mejor agente disponible.

        Args:
            task_type: Tipo ('coding', 'image', 'llm', 'pipeline')
            task: Descripción de la tarea
            files: Archivos relevantes
            context: Contexto adicional
            effort: Esfuerzo (low, medium, high)

        Returns:
            Dict con resultado de la tarea
        """
        self.logger.task("Orquestador", task[:50], "start",
                         f"Delegando a {task_type}")

        result = self.dispatcher.dispatch(
            task_type=task_type,
            task=task,
            files=files,
            context=context,
            effort=effort,
            **kwargs
        )

        # ── Pipeline: logging detallado + persistencia rica ──────────
        if task_type == "pipeline":
            duration_min = round(result.duration / 60, 1)
            cat_count = len(task.strip().split()) if task.strip() else 0

            # Parsear métricas del output
            output = result.output or ""
            gen_count = "0"
            pix_count = "0"
            db_status = "SKIP"
            for line in output.split("\n"):
                ls = line.strip()
                if "Generacion:" in ls:
                    gen_count = ls.split(":", 1)[-1].strip().split()[0]
                elif "Pixel art:" in ls:
                    pix_count = ls.split(":", 1)[-1].strip().split()[0]
                elif "DB insert:" in ls:
                    db_status = ls.split(":", 1)[-1].strip()

            # Logging detallado a FactoryLogger
            if result.success:
                self.logger.success(
                    "Pipeline",
                    f"{cat_count} cats, {duration_min}m, "
                    f"gen:{gen_count} pix:{pix_count} db:{db_status}"
                )
            else:
                self.logger.warn(
                    "Pipeline",
                    f"Falló tras {duration_min}m — {result.error[:100]}"
                )

            self.logger.task(
                result.agent, result.task_id,
                "done" if result.success else "failed",
                f"{cat_count} cats en {duration_min}m | gen:{gen_count} pix:{pix_count} db:{db_status}"
            )

            # ── Persistir en memoria: PostgreSQL u Obsidian ──────────
            memory_content = (
                f"[PIPELINE] Categorias: {task} | "
                f"Duracion: {duration_min}m | "
                f"Generacion: {gen_count} | "
                f"Pixel art: {pix_count} | "
                f"DB: {db_status} | "
                f"Resultado: {'EXITO' if result.success else 'FALLO'}"
            )
            tags = ['factory', 'pipeline',
                    'success' if result.success else 'failed']
            mem_key = f"pipeline_{result.task_id}"

            # Intentar PostgreSQL primero
            if self.memory:
                try:
                    self.memory.save(
                        key_name=mem_key,
                        content=memory_content,
                        memory_type='task',
                        tags=tags,
                        importance=4 if result.success else 5,
                        related_agent="pipeline",
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"  [WARN] No se pudo persistir pipeline en PostgreSQL: {e}")

            # Siempre persistir en Obsidian (capa local)
            if self.obsidian:
                try:
                    self.obsidian.save(
                        key_name=mem_key,
                        content=memory_content,
                        memory_type='task',
                        tags=tags,
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"  [WARN] No se pudo persistir pipeline en Obsidian: {e}")

            # ── Escribir .last_pipeline.json para la UI bash ──────────
            _write_last_pipeline({
                "timestamp": datetime.now().isoformat(),
                "task_id": result.task_id,
                "categories": task,
                "cat_count": cat_count,
                "duration_min": duration_min,
                "gen_count": gen_count,
                "pix_count": pix_count,
                "db_status": db_status,
                "success": result.success,
                "error": result.error[:200] if result.error else None,
            })

        # ── Otras tareas: persistencia genérica ─────────────────────
        else:
            if self.memory and result.success:
                try:
                    self.memory.save(
                        key_name=f"task_{result.task_id}",
                        content=f"[{task_type}] {task[:100]} — {'✅' if result.success else '❌'} ({result.duration:.1f}s)",
                        memory_type='task',
                        tags=['factory', task_type, 'success' if result.success else 'failed'],
                        importance=3 if result.success else 4,
                        related_agent=result.agent,
                    )
                except Exception:
                    pass

            self.logger.task(result.agent, result.task_id,
                             "done" if result.success else "failed",
                             f"{task_type} ({result.duration:.1f}s)")

        return result.to_dict()

    # ══════════════════════════════════════════════════════════════════
    #  Estado del sistema
    # ══════════════════════════════════════════════════════════════════

    def status(self) -> dict:
        """Obtener estado completo del sistema.

        Returns:
            Dict con estado de agentes, salud, sesión y memoria
        """
        health_results = self.monitor.check_all()
        agent_health = self.registry.health()

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime": str(datetime.now() - self.started_at).split(".")[0],
            "agents": {
                "total": len(self.registry.all()),
                "types": self.registry.types(),
                "health": agent_health,
                "healthy": sum(1 for h in agent_health.values() if h),
            },
            "services": {
                "health": health_results,
                "healthy": sum(1 for h in health_results.values() if h),
                "total": len(health_results),
            },
            "dispatcher": self.dispatcher.summary(),
            "memory": self.memory is not None,
            "platform": sys.platform,
        }

    def status_text(self) -> str:
        """Obtener estado formateado como texto."""
        status = self.status()
        agents = status["agents"]
        services = status["services"]

        lines = [
            f"\n  {'='*55}",
            f"  🏭  FACTORY GAMES — Estado del Sistema",
            f"     Uptime: {status['uptime']}",
            f"     {status['timestamp']}",
            f"  {'='*55}\n",
            f"  🤖 Agentes: {agents['healthy']}/{agents['total']} saludables\n",
        ]

        for agent_type, names in agents["types"].items():
            lines.append(f"  📂 {agent_type.upper()}:")
            for name in names:
                healthy = agents["health"].get(name, False)
                icon = "✅" if healthy else "⚫"
                lines.append(f"     {icon} {name}")
            lines.append("")

        lines.append(f"  🔌 Servicios: {services['healthy']}/{services['total']} activos\n")

        for name, healthy in services["health"].items():
            icon = "✅" if healthy else "⚫"
            lines.append(f"     {icon} {name}")

        # Últimas tareas
        history = self.dispatcher.get_history(5)
        if history:
            lines.append(f"\n  📋 Últimas tareas:")
            for h in reversed(history):
                icon = "✅" if h["success"] else "❌"
                lines.append(f"     {icon} {h['agent']} — {h['task_type']} ({h['duration']}s)")

        lines.append(f"\n  💾 Memoria: {'✅ PostgreSQL' if status['memory'] else '⚫ No disponible'}\n")
        lines.append(f"  {'='*55}\n")

        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════
    #  Agentes
    # ══════════════════════════════════════════════════════════════════

    def agents(self) -> List[dict]:
        """Listar agentes registrados con sus capacidades.

        Returns:
            Lista de dicts con info de cada agente
        """
        return [a.to_dict() for a in self.registry.all()]

    def agents_text(self) -> str:
        """Listar agentes formateados como texto."""
        agents = self.agents()
        health = self.registry.health()

        lines = [
            f"\n  {'='*55}",
            f"  🏭  FACTORY GAMES — Agentes Registrados",
            f"  {'='*55}\n",
        ]

        for agent_type in set(a["agent_type"] for a in agents):
            type_agents = [a for a in agents if a["agent_type"] == agent_type]
            lines.append(f"  📂 {agent_type.upper()} ({len(type_agents)}):")

            for a in type_agents:
                healthy = health.get(a["name"], False)
                icon = "✅" if healthy else "⚫"
                caps = ", ".join(a["capabilities"])
                lines.append(f"     {icon} {a['name']:20s} → {a['endpoint']}")
                if caps:
                    lines.append(f"          Capacidades: {caps}")
            lines.append("")

        lines.append(f"  {'='*55}\n")
        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════
    #  Recuperación
    # ══════════════════════════════════════════════════════════════════

    def recover(self, service_name: Optional[str] = None) -> Union[bool, dict]:
        """Recuperar servicio(s) caído(s).

        Args:
            service_name: Nombre del servicio (None = todos los caídos)

        Returns:
            bool si es un servicio específico, dict si es --all
        """
        if service_name:
            self.logger.info("Orquestador", f"Recuperando servicio: {service_name}")
            result = self.monitor.recover_service(service_name)
            if result:
                self.logger.success("Orquestador", f"{service_name} recuperado")
            else:
                self.logger.warn("Orquestador", f"No se pudo recuperar {service_name}")
            return result
        else:
            self.logger.info("Orquestador", "Recuperando todos los servicios caídos...")
            results = self.monitor.recover_all()
            ok = sum(1 for r in results.values() if r)
            fail = sum(1 for r in results.values() if not r)
            self.logger.info("Orquestador", f"Recuperación: {ok} OK, {fail} fallidos")
            return results

    # ══════════════════════════════════════════════════════════════════
    #  Resumen de sesión
    # ══════════════════════════════════════════════════════════════════

    def session_summary(self) -> str:
        """Generar resumen de la sesión actual.

        Returns:
            String formateado con el resumen
        """
        now = datetime.now()
        duration = now - self.started_at
        hours = duration.total_seconds() / 3600

        agent_health = self.registry.health()
        healthy_agents = sum(1 for h in agent_health.values() if h)
        total_agents = len(agent_health)

        dispatch_summary = self.dispatcher.summary()
        history = self.dispatcher.get_history(10)

        lines = [
            f"\n  {'='*55}",
            f"  📋 RESUMEN DE SESIÓN — FactoryGames",
            f"  {'='*55}",
            f"  🕐  Inicio:      {self.started_at.strftime('%H:%M:%S')}",
            f"  ⏱️  Duración:     {duration.total_seconds() / 60:.1f} min ({hours:.2f}h)",
            f"  🤖  Agentes:      {healthy_agents}/{total_agents} saludables",
            f"  📊  Tareas:       {dispatch_summary['total']} totales "
            f"({dispatch_summary['success']}✅ / {dispatch_summary['failed']}❌)",
            f"  {'='*55}",
        ]

        if history:
            lines.append("")
            for h in reversed(history):
                icon = "✅" if h["success"] else "❌"
                lines.append(f"     {icon} {h['task_type']:8s} → {h['agent']:15s} "
                            f"({h['duration']}s)")

        lines.append(f"\n  {'='*55}\n")
        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════
    #  Mantenimiento
    # ══════════════════════════════════════════════════════════════════

    def cleanup(self):
        """Limpiar recursos al finalizar la sesión."""
        self.monitor.stop_periodic_check()
        self.logger.info("Orquestador", "Sesión finalizada")


# ── Quick test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    factory = FactoryOrchestrator(verbose=True)
    factory.boot()

    print(factory.status_text())

    # Test: delegar una tarea LLM simple a Ollama
    result = factory.delegate(
        "llm",
        "Responde solo: 'FactoryGames Online!'",
    )

    print(factory.session_summary())
