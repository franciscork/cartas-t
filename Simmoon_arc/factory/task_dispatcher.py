#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/task_dispatcher.py — Despachador de Tareas FactoryGames

Enruta tareas al agente correcto según el tipo de trabajo:
  - coding → Claude Code (via BuffySupervisor / OllamaAnthropicClient)
  - image  → GeneratorFactory (ComfyUI → InvokeAI → cloud)
  - llm    → Ollama directo
"""

import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.parent.resolve()

# ── Config (override desde dispatcher_config.json) ────────────────────────
_DISPATCHER_CONFIG: dict = {}
_config_path = SCRIPT_DIR / "dispatcher_config.json"
if _config_path.exists():
    try:
        _DISPATCHER_CONFIG = json.loads(_config_path.read_text(encoding="utf-8"))
    except Exception:
        pass


def _validar_timeout(valor: object, clave: str, default: int) -> int:
    """Validar que un valor de timeout sea entero positivo; loguear warning si no."""
    if isinstance(valor, int) and valor > 0:
        return valor
    if isinstance(valor, int) and valor <= 0:
        print(f"  [WARN] dispatcher_config.json: '{clave}' debe ser positivo "
              f"(recibido {valor!r}), usando default {default}", file=sys.stderr)
    else:
        print(f"  [WARN] dispatcher_config.json: '{clave}' debe ser un entero "
              f"(recibido {type(valor).__name__}: {valor!r}), usando default {default}",
              file=sys.stderr)
    return default


# Timeouts por defecto (override via config.json)
# Ej: {"llm_timeout": 600, "coding_timeout": 600}
DEFAULT_LLM_TIMEOUT: int = _validar_timeout(
    _DISPATCHER_CONFIG.get("llm_timeout", 300), "llm_timeout", 300)
DEFAULT_CODING_TIMEOUT: int = _validar_timeout(
    _DISPATCHER_CONFIG.get("coding_timeout", 300), "coding_timeout", 300)
DEFAULT_IMAGE_TIMEOUT: int = _validar_timeout(
    _DISPATCHER_CONFIG.get("image_timeout", 300), "image_timeout", 300)
DEFAULT_PIPELINE_TIMEOUT: int = _validar_timeout(
    _DISPATCHER_CONFIG.get("pipeline_timeout", 3600), "pipeline_timeout", 3600)

# Timeout global del lote (dispatch_multi) — None = sin limite
# Ej: {"multi_timeout": 600}
_MULTI_RAW = _DISPATCHER_CONFIG.get("multi_timeout")
if isinstance(_MULTI_RAW, int) and _MULTI_RAW > 0:
    DEFAULT_MULTI_TIMEOUT: Optional[int] = _MULTI_RAW
else:
    if _MULTI_RAW is not None:
        if isinstance(_MULTI_RAW, int) and _MULTI_RAW <= 0:
            print(f"  [WARN] dispatcher_config.json: 'multi_timeout' debe ser positivo "
                  f"(recibido {_MULTI_RAW!r}), sin l\u00edmite global", file=sys.stderr)
        else:
            print(f"  [WARN] dispatcher_config.json: 'multi_timeout' debe ser un entero "
                  f"(recibido {type(_MULTI_RAW).__name__}: {_MULTI_RAW!r}), sin l\u00edmite global",
                  file=sys.stderr)
    DEFAULT_MULTI_TIMEOUT: Optional[int] = None

# ── Result type ───────────────────────────────────────────────────────────
class DispatchResult:
    """Resultado de una tarea despachada."""

    def __init__(self, success: bool, agent: str, task_type: str,
                 output: str = "", error: str = "",
                 duration: float = 0.0, files_modified: List[str] = None,
                 task_id: str = ""):
        self.success = success
        self.agent = agent
        self.task_type = task_type
        self.output = output
        self.error = error
        self.duration = duration
        self.files_modified = files_modified or []
        self.task_id = task_id or f"task_{int(datetime.now().timestamp())}"

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "agent": self.agent,
            "task_type": self.task_type,
            "output": self.output[:500],
            "error": self.error[:500],
            "duration": round(self.duration, 1),
            "files_modified": self.files_modified,
            "task_id": self.task_id,
        }

    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} [{self.agent}] {self.task_type} ({self.duration:.1f}s)"


# ── Parallel batch result ──────────────────────────────────────────────
class ParallelBatchResult:
    """Resultado de multiples tareas despachadas en paralelo."""

    def __init__(self, results: List[DispatchResult]):
        self.results = results
        self.total = len(results)
        self.success = sum(1 for r in results if r.success)
        self.failed = self.total - self.success
        self.total_duration = sum(r.duration for r in results)
        self.wall_clock = 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "total_duration": round(self.total_duration, 1),
            "wall_clock": round(self.wall_clock, 1),
            "results": [r.to_dict() for r in self.results],
        }

    def __str__(self):
        speedup = self.total_duration / max(self.wall_clock, 0.1) if self.wall_clock > 0 else 1.0
        return (f"📦 Parallel batch: {self.success}/{self.total} OK "
                f"({self.total_duration:.1f}s total / {self.wall_clock:.1f}s wall = {speedup:.1f}x speedup)")


# ── Soft imports ─────────────────────────────────────────────────────────
_BUFFY_SUPERVISOR = None
def _get_buffy_supervisor(verbose: bool = False):
    """Importar BuffySupervisor de forma lazy."""
    global _BUFFY_SUPERVISOR
    if _BUFFY_SUPERVISOR is None:
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from claude_code_bridge import BuffySupervisor
            _BUFFY_SUPERVISOR = BuffySupervisor(verbose=verbose)
        except Exception as e:
            if verbose:
                print(f"  [WARN] BuffySupervisor no disponible: {e}")
            _BUFFY_SUPERVISOR = False
    return _BUFFY_SUPERVISOR if _BUFFY_SUPERVISOR else None


_GENERATOR_FACTORY = None
def _get_generator_factory():
    """Importar GeneratorFactory de forma lazy."""
    global _GENERATOR_FACTORY
    if _GENERATOR_FACTORY is None:
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from generator_factory import GeneratorFactory
            _GENERATOR_FACTORY = GeneratorFactory()
        except Exception as e:
            _GENERATOR_FACTORY = False
    return _GENERATOR_FACTORY if _GENERATOR_FACTORY else None


# ══════════════════════════════════════════════════════════════════════════
#  TaskDispatcher
# ══════════════════════════════════════════════════════════════════════════

class TaskDispatcher:
    """Despachador de tareas — enruta al agente correcto según el tipo.

    Tipos de tarea soportados:
      - coding:   refactor, implementar, debuggear (→ Claude Code / Ollama)
      - image:    generar imágenes (→ GeneratorFactory)
      - llm:      consultas a modelos de lenguaje (→ Ollama)
      - pipeline: ejecutar pipeline completo de assets (→ simmoon_pipeline)
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.history: List[DispatchResult] = []

    def dispatch(self, task_type: str, task: str,
                 files: Optional[List[str]] = None,
                 context: str = "",
                 effort: str = "high",
                 **kwargs) -> DispatchResult:
        """Enrutar tarea al agente más adecuado.

        Args:
            task_type: Tipo de tarea ('coding', 'image', 'llm')
            task: Descripción de la tarea a realizar
            files: Archivos relevantes para la tarea
            context: Contexto adicional
            effort: Nivel de esfuerzo (low, medium, high)
            **kwargs: Argumentos adicionales específicos del tipo

        Returns:
            DispatchResult con el resultado
        """
        if self.verbose:
            print(f"\n  🚀 Despachando tarea [{task_type}]: {task[:80]}...")

        start = datetime.now()

        try:
            if task_type == "coding":
                result = self._dispatch_coding(task, files, context, effort, **kwargs)
            elif task_type == "image":
                result = self._dispatch_image(task, files, context, **kwargs)
            elif task_type == "llm":
                result = self._dispatch_llm(task, **kwargs)
            elif task_type == "pipeline":
                result = self._dispatch_pipeline(task, **kwargs)
            else:
                result = DispatchResult(
                    success=False, agent="unknown",
                    task_type=task_type,
                    error=f"Tipo de tarea no soportado: {task_type}"
                )
        except Exception as e:
            result = DispatchResult(
                success=False, agent="error",
                task_type=task_type,
                error=str(e)
            )

        # Calcular duración
        duration = (datetime.now() - start).total_seconds()
        result.duration = duration

        # Registrar en historial
        self.history.append(result)

        if self.verbose:
            status = "✅" if result.success else "❌"
            print(f"  {status} Completado en {duration:.1f}s — {result.agent}")
            if result.error:
                print(f"     ⚠️  {result.error[:200]}")
            if result.files_modified:
                for f in result.files_modified[:3]:
                    print(f"     📄 {f}")

        return result

    # ── Coding: BuffySupervisor → Claude Code / Ollama ──────────────

    def _dispatch_coding(self, task: str,
                         files: Optional[List[str]] = None,
                         context: str = "",
                         effort: str = "high",
                         model: Optional[str] = None,
                         timeout: Optional[int] = None) -> DispatchResult:
        """Delegar tarea de código al BuffySupervisor.

        Usa BuffySupervisor que selecciona automáticamente:
          - Claude Code (si autenticado)
          - Ollama + qwen2.5-coder (local, gratis)
        """
        # Usar timeout del config si no se pasó explícitamente
        if timeout is None:
            timeout = DEFAULT_CODING_TIMEOUT

        supervisor = _get_buffy_supervisor(self.verbose)
        if supervisor:
            result = supervisor.delegate(
                task=task,
                files=files,
                context=context,
                effort=effort,
                timeout=timeout,
            )
            return DispatchResult(
                success=result.success,
                agent="claude-code",
                task_type="coding",
                output=result.summary or result.stdout[:500],
                error=result.stderr[:500] if not result.success else "",
                duration=result.duration,
                files_modified=result.files_modified,
                task_id=result.task_id,
            )

        # Fallback: Ollama directo
        if self.verbose:
            print("  [FALLBACK] BuffySupervisor no disponible, usando Ollama directo")
        return self._dispatch_llm(
            f"Eres un asistente de código experto. Completa esta tarea:\n\n{task}\n\n"
            f"{'Archivos: ' + ', '.join(files) if files else ''}\n\n"
            f"{'Contexto: ' + context if context else ''}",
            model=model or "qwen2.5-coder:14b",
            timeout=timeout,
        )

    # ── Image: GeneratorFactory ────────────────────────────────────

    def _dispatch_image(self, prompt: str,
                        files: Optional[List[str]] = None,
                        context: str = "",
                        output_path: Optional[str] = None,
                        width: int = 512,
                        height: int = 512,
                        timeout: Optional[int] = None,
                        **kwargs) -> DispatchResult:
        """Generar imagen usando GeneratorFactory (con fallback chain)."""
        # Usar timeout del config si no se pas\u00f3 expl\u00edcitamente
        if timeout is None:
            timeout = DEFAULT_IMAGE_TIMEOUT

        gen = _get_generator_factory()
        if not gen:
            return DispatchResult(
                success=False, agent="generator-factory",
                task_type="image",
                error="GeneratorFactory no disponible"
            )

        if not gen.is_any_backend_available():
            return DispatchResult(
                success=False, agent="generator-factory",
                task_type="image",
                error="Ningún backend de generación disponible"
            )

        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(SCRIPT_DIR / f"generated_{timestamp}.png")

        try:
            result_path = gen.generate_one(
                prompt=prompt,
                output_path=output_path,
                width=width,
                height=height,
                **kwargs
            )
            return DispatchResult(
                success=True,
                agent=gen.get_active_backend(),
                task_type="image",
                output=f"Imagen generada: {result_path}",
                files_modified=[result_path],
            )
        except Exception as e:
            return DispatchResult(
                success=False, agent="generator-factory",
                task_type="image",
                error=str(e)
            )

    # ── LLM: Ollama directo ─────────────────────────────────────────

    def _dispatch_llm(self, prompt: str,
                      model: str = "qwen2.5-coder:14b",
                      timeout: Optional[int] = None,
                      temperature: float = 0.3,
                      max_tokens: int = 4096) -> DispatchResult:
        """Consultar un modelo LLM vía Ollama.

        Args:
            prompt: El prompt a enviar
            model: Modelo Ollama (default: qwen2.5-coder:14b)
            timeout: Timeout en segundos (default: DEFAULT_LLM_TIMEOUT del config)
            temperature: Temperatura de generación
            max_tokens: Máximo de tokens a generar

        Returns:
            DispatchResult con la respuesta
        """
        start_time = time.time()
        # Usar timeout del config si no se pasó explícitamente
        if timeout is None:
            timeout = DEFAULT_LLM_TIMEOUT

        # Verificar que Ollama esté disponible
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status != 200:
                    return DispatchResult(
                        success=False, agent="ollama",
                        task_type="llm",
                        error="Ollama no está disponible"
                    )
        except Exception as e:
            return DispatchResult(
                success=False, agent="ollama",
                task_type="llm",
                error=f"Ollama no responde: {e}"
            )

        # Enviar prompt a Ollama
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                response = result.get("response", "")

            duration = time.time() - start_time
            return DispatchResult(
                success=True,
                agent=f"ollama/{model}",
                task_type="llm",
                output=response[:1000],
                duration=duration,
            )
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            return DispatchResult(
                success=False, agent="ollama",
                task_type="llm",
                error=f"HTTP {e.code}: {body}"
            )
        except Exception as e:
            return DispatchResult(
                success=False, agent="ollama",
                task_type="llm",
                error=str(e)
            )

    # ── Pipeline: simmoon_pipeline ────────────────────────────────

    def _dispatch_pipeline(self, categories: str,
                           run_suffix: str = "",
                           checkpoint: str = "",
                           backend: str = "factory",
                           no_loras: bool = False,
                           lora: str = "",
                           skip_generation: bool = False,
                           skip_pixel: bool = False,
                           skip_db: bool = False,
                           timeout: Optional[int] = None,
                           **kwargs) -> DispatchResult:
        """Ejecutar pipeline completo de generación de assets.

        Llama a simmoon_pipeline.run_pipeline() con las categorías
        especificadas y los parámetros de generación.

        Args:
            categories: Categorías separadas por espacio (e.g. "businesses vehicles")
            run_suffix: Sufijo para archivos generados
            checkpoint: Checkpoint de ComfyUI
            backend: Backend de generación (factory, diffusers, comfyui)
            no_loras: Deshabilitar LoRAs
            lora: Especificación de LoRA
            skip_generation: Saltar generación
            skip_pixel: Saltar pixel art
            skip_db: Saltar inserción en BD

        Returns:
            DispatchResult con el resultado del pipeline
        """
        start_time = time.time()
        # Usar timeout del config si no se pas\u00f3 expl\u00edcitamente
        if timeout is None:
            timeout = DEFAULT_PIPELINE_TIMEOUT

        # Importar pipeline_generator y simmoon_pipeline (soft import)
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from pipeline_generator import PipelineState
            from simmoon_pipeline import run_pipeline
        except ImportError as e:
            return DispatchResult(
                success=False, agent="pipeline",
                task_type="pipeline",
                error=f"No se pudo importar el pipeline: {e}"
            )

        # Parsear categorías
        cat_list = categories.strip().split()
        if not cat_list:
            return DispatchResult(
                success=False, agent="pipeline",
                task_type="pipeline",
                error="Debes especificar al menos una categoría"
            )

        if self.verbose:
            print(f"\n  {'═'*55}")
            print(f"  🏭  PIPELINE — Generación de Assets")
            print(f"  {'═'*55}")
            print(f"     Categorías: {', '.join(cat_list)}")
            print(f"     Backend:    {backend}")
            print(f"     Checkpoint: {checkpoint or 'default'}")
            print(f"     Run suffix: {run_suffix or '(none)'}")
            print(f"  {'─'*55}")

        # Crear estado del pipeline
        state = PipelineState(
            categories=cat_list,
            run_suffix=run_suffix,
            checkpoint=checkpoint,
            no_loras=no_loras,
            lora=lora,
            skip_generation=skip_generation,
            skip_pixel=skip_pixel,
            skip_db=skip_db,
            backend=backend,
        )

        # Ejecutar pipeline
        try:
            run_pipeline(state)
            duration = time.time() - start_time

            success = len(state.errors) == 0
            return DispatchResult(
                success=success,
                agent="pipeline",
                task_type="pipeline",
                output=(
                    f"Pipeline completado en {duration/60:.1f}m\n"
                    f"  Categorias: {len(state.categories)}\n"
                    f"  Generacion: {state.generated_count} categorias\n"
                    f"  Pixel art:  {state.pixel_count} categorias\n"
                    f"  DB insert:  {'OK' if state.db_inserted else 'SKIP'}"
                ),
                error="; ".join(state.errors) if state.errors else "",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return DispatchResult(
                success=False, agent="pipeline",
                task_type="pipeline",
                error=f"Pipeline falló: {e}",
                duration=duration,
            )

    # ── Parallel dispatch ──────────────────────────────────────────

    def dispatch_multi(self, tasks: List[Dict[str, Any]],
                       max_workers: Optional[int] = None,
                       stop_on_error: bool = False,
                       timeout: Optional[int] = None) -> ParallelBatchResult:
        """Despachar multiples tareas en paralelo usando ThreadPoolExecutor.

        Cada tarea se define como un dict con los argumentos de dispatch():
          - task_type (obligatorio)
          - task (obligatorio)
          - files, context, effort, etc. (opcionales)

        Los agentes trabajan concurrentemente en lugar de en serie.

        Args:
            tasks: Lista de dicts con especificaciones de tarea
            max_workers: Max workers (default: min(4, cpu_count))
            stop_on_error: Si True, detiene todas las tareas si una falla
            timeout: Timeout global en segundos para todo el lote
                (default: DEFAULT_MULTI_TIMEOUT del config; None = sin l\u00edmite)

        Returns:
            ParallelBatchResult con el resultado de todas las tareas
        """
        # Usar timeout global del config si no se pas\u00f3 expl\u00edcitamente
        if timeout is None:
            timeout = DEFAULT_MULTI_TIMEOUT

        if not tasks:
            return ParallelBatchResult([])

        cpu_count = os.cpu_count() or 1
        workers = max_workers or min(4, cpu_count)

        if self.verbose:
            print(f"\n  ⚡ Despachando {len(tasks)} tarea(s) en paralelo "
                  f"({workers} workers)...")
            print(f"  {'─'*55}")
            for i, t in enumerate(tasks, 1):
                tt = t.get("task_type", "?")
                tk = t.get("task", "")[:60]
                print(f"     [{i}] {tt}: {tk}...")
            print(f"  {'─'*55}")

        start_wall = datetime.now()
        indexed_results: Dict[int, DispatchResult] = {}
        error_event = threading.Event() if stop_on_error else None

        def _dispatch_one(task_spec: dict, task_idx: int) -> DispatchResult:
            if stop_on_error and error_event and error_event.is_set():
                return DispatchResult(
                    success=False,
                    agent="cancelled",
                    task_type=task_spec.get("task_type", "unknown"),
                    error="Cancelada por error en otra tarea del lote",
                )
            return self.dispatch(**task_spec)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_dispatch_one, t, i): i
                      for i, t in enumerate(tasks)}

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result(timeout=timeout)
                    indexed_results[idx] = result
                    if stop_on_error and not result.success and error_event:
                        error_event.set()
                except Exception as e:
                    task_spec = tasks[idx]
                    indexed_results[idx] = DispatchResult(
                        success=False,
                        agent="exception",
                        task_type=task_spec.get("task_type", "unknown"),
                        error=f"Excepcion/timeout en tarea #{idx}: {e}",
                    )
                    if stop_on_error and error_event:
                        error_event.set()

        # Reconstruir lista ordenada por indice original
        ordered_results = [indexed_results[i] for i in range(len(tasks))
                          if i in indexed_results]
        wall_clock = (datetime.now() - start_wall).total_seconds()
        batch = ParallelBatchResult(ordered_results)
        batch.wall_clock = wall_clock

        if self.verbose:
            print(f"\n  {batch}")
            if batch.failed > 0:
                for r in ordered_results:
                    if not r.success:
                        print(f"     ❌ [{r.task_type}] {r.error[:100]}")
            print(f"  {'─'*55}")

        return batch

    def dispatch_parallel(self, *task_specs: Dict[str, Any],
                          **kwargs) -> ParallelBatchResult:
        """Conveniencia: dispatchea multiples tareas en paralelo.

        Uso:
            disp.dispatch_parallel(
                {"task_type": "llm", "task": "tarea 1"},
                {"task_type": "coding", "task": "tarea 2", "files": ["x.py"]},
                max_workers=3,
            )
        """
        return self.dispatch_multi(list(task_specs), **kwargs)

    # ── Utilidades ───────────────────────────────────────────────────

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener historial de tareas despachadas."""
        return [r.to_dict() for r in self.history[-limit:]]

    def summary(self) -> dict:
        """Resumen de actividad del dispatcher."""
        total = len(self.history)
        success = sum(1 for r in self.history if r.success)
        by_type = {}
        for r in self.history:
            by_type[r.task_type] = by_type.get(r.task_type, 0) + 1
        return {
            "total": total,
            "success": success,
            "failed": total - success,
            "by_type": by_type,
        }


# ── Quick test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    disp = TaskDispatcher(verbose=True)

    print(f"\n  🏭 FactoryGames — Task Dispatcher Test\n")
    print(f"  {'='*55}\n")

    result = disp.dispatch("llm", "Responde solo: 'Hola desde FactoryGames!'")
    print(f"\n  Resultado: {result}")
    if result.success:
        print(f"  Output: {result.output[:200]}")

    print(f"\n  📊 Historial:")
    for item in disp.get_history():
        print(f"     {item['success'] and '✅' or '❌'} {item['agent']} — {item['task_type']} ({item['duration']}s)")
