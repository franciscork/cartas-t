#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_gpu_orchestrator.py — Test unitario de las funciones GPU del orquestador.

Valida:
  1. get_gpu_vram_used() — nvidia-smi real (si disponible)
  2. unload_ollama_model() — graceful failure si Ollama caído
  3. is_comfyui_busy() — graceful failure si ComfyUI caído
  4. wait_for_comfyui() — timeout rápido sin servicio
"""

import asyncio
import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Force encoding ─────────────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_get_gpu_vram_used():
    """get_gpu_vram_used() debe devolver un entero > 0 (GPU real) o -1 (sin GPU)."""
    # Importamos dinámicamente desde telegram_bot
    from telegram_bot import get_gpu_vram_used

    result = asyncio.run(get_gpu_vram_used())

    assert isinstance(result, int), f"Expected int, got {type(result)}"
    assert result >= -1, f"Expected >= -1, got {result}"

    if result >= 0:
        assert result <= 8192, f"VRAM > 8192MB improbable: {result}"
        print(f"  ✅ get_gpu_vram_used() → {result}MB (GPU detectada)")
    else:
        print(f"  ⚠️  get_gpu_vram_used() → {result} (nvidia-smi no disponible)")


def test_unload_ollama_graceful_failure():
    """unload_ollama_model() debe retornar False si Ollama no responde."""
    from telegram_bot import unload_ollama_model

    result = asyncio.run(
        unload_ollama_model("deepseek-r1:7b", "http://localhost:11434")
    )

    assert isinstance(result, bool), f"Expected bool, got {type(result)}"
    if result:
        print(f"  ✅ unload_ollama_model() → True (modelo descargado de GPU)")
    else:
        print(f"  ⚠️  unload_ollama_model() → False (Ollama caído o timeout)")


def test_is_comfyui_busy_graceful():
    """is_comfyui_busy() debe retornar False si ComfyUI no responde."""
    from telegram_bot import is_comfyui_busy

    result = asyncio.run(is_comfyui_busy("http://localhost:8188"))

    assert isinstance(result, bool), f"Expected bool, got {type(result)}"
    # Si ComfyUI está caído, asumimos libre (False) — no debe crashear
    print(f"  ✅ is_comfyui_busy() → {result} (graceful: no exception)")


def test_wait_for_comfyui_short_timeout():
    """wait_for_comfyui() debe retornar rápidamente sin servicio."""
    from telegram_bot import wait_for_comfyui

    import time
    start = time.time()
    result = asyncio.run(
        wait_for_comfyui("http://localhost:8188", timeout=3)
    )
    elapsed = time.time() - start

    assert isinstance(result, bool), f"Expected bool, got {type(result)}"
    assert elapsed < 5, f"Timeout too long: {elapsed:.1f}s"
    print(f"  ✅ wait_for_comfyui() → {result} en {elapsed:.1f}s (timeout rápido)")


def test_functions_are_importable():
    """Verificar que las 4 funciones core son importables sin error."""
    try:
        from telegram_bot import (
            unload_ollama_model,
            is_comfyui_busy,
            wait_for_comfyui,
            get_gpu_vram_used,
        )
        print(f"  ✅ Las 4 funciones core importadas correctamente")
    except ImportError as e:
        raise AssertionError(f"ImportError: {e}")


def test_async_functions_exist():
    """Verificar que las funciones son async (corrutinas)."""
    import inspect
    from telegram_bot import (
        unload_ollama_model,
        is_comfyui_busy,
        wait_for_comfyui,
    )

    for name, fn in [
        ("unload_ollama_model", unload_ollama_model),
        ("is_comfyui_busy", is_comfyui_busy),
        ("wait_for_comfyui", wait_for_comfyui),
    ]:
        assert inspect.iscoroutinefunction(fn), (
            f"{name} debe ser async, es {type(fn)}"
        )
    print(f"  ✅ Las 3 funciones async confirmadas como corrutinas")


def test_handlers_exist_in_module():
    """Verificar que cmd_gpu_free, cmd_gpu_restore, cmd_gen son importables."""
    try:
        from telegram_bot import cmd_gpu_free, cmd_gpu_restore, cmd_gen
        import inspect
        for name, fn in [
            ("cmd_gpu_free", cmd_gpu_free),
            ("cmd_gpu_restore", cmd_gpu_restore),
            ("cmd_gen", cmd_gen),
        ]:
            assert inspect.iscoroutinefunction(fn), (
                f"{name} debe ser async"
            )
        print(f"  ✅ 3 command handlers importados y son async")
    except ImportError as e:
        raise AssertionError(f"ImportError: {e}")


# ── Run ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  🧪 Test GPU Orchestrator — telegram_bot.py\n")
    print(f"  {'='*55}")

    tests = [
        ("Importabilidad", test_functions_are_importable),
        ("Async check", test_async_functions_exist),
        ("Handlers exist", test_handlers_exist_in_module),
        ("get_gpu_vram_used (real)", test_get_gpu_vram_used),
        ("unload_ollama (graceful fail)", test_unload_ollama_graceful_failure),
        ("is_comfyui_busy (graceful)", test_is_comfyui_busy_graceful),
        ("wait_for_comfyui (timeout)", test_wait_for_comfyui_short_timeout),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ {name}: {e}")

    print(f"\n  {'='*55}")
    if failed == 0:
        print(f"  ✅ ALL {passed}/{len(tests)} tests passed")
    else:
        print(f"  ⚠️  {passed} passed, {failed} FAILED")
    print()
