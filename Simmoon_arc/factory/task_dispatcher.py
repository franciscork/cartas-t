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
import time
import urllib.parse
import urllib.request
import urllib.error
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
                         timeout: int = 300) -> DispatchResult:
        """Delegar tarea de código al BuffySupervisor.

        Usa BuffySupervisor que selecciona automáticamente:
          - Claude Code (si autenticado)
          - Ollama + qwen2.5-coder (local, gratis)
        """
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
                        **kwargs) -> DispatchResult:
        """Generar imagen usando GeneratorFactory (con fallback chain)."""
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
                      timeout: int = 120,
                      temperature: float = 0.3,
                      max_tokens: int = 4096) -> DispatchResult:
        """Consultar un modelo LLM vía Ollama.

        Args:
            prompt: El prompt a enviar
            model: Modelo Ollama (default: qwen2.5-coder:14b)
            timeout: Timeout en segundos
            temperature: Temperatura de generación
            max_tokens: Máximo de tokens a generar

        Returns:
            DispatchResult con la respuesta
        """
        start_time = time.time()

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
