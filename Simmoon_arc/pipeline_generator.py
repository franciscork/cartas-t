#!/usr/bin/env python3
"""
pipeline_generator.py — Modulo de generacion extraido de simmoon_pipeline.py

Contiene la logica de generacion de assets: PipelineState, backends
(Diffusers WSL2, GeneratorFactory), y el router de generacion.

Uso (importado por simmoon_pipeline.py):
    from pipeline_generator import PipelineState, node_generate, run_pipeline
"""

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"
PROMPTS_PATH = SCRIPT_DIR / "simmoon_prompts.json"

# Import unified generator factory with fallback
try:
    from generator_factory import GeneratorFactory
    _FACTORY_AVAILABLE = True
except ImportError:
    _FACTORY_AVAILABLE = False


# ─── LangGraph-style State ─────────────────────────────────────────────────

class PipelineState:
    """State object passed between pipeline nodes (LangGraph-style)."""

    def __init__(self, categories: list[str], run_suffix: str = "",
                 checkpoint: str = "", no_loras: bool = False,
                 lora: str = "", skip_generation: bool = False,
                 skip_pixel: bool = False, skip_db: bool = False,
                 backend: str = "factory"):
        self.categories = categories
        self.run_suffix = run_suffix
        self.checkpoint = checkpoint
        self.no_loras = no_loras
        self.lora = lora
        self.skip_generation = skip_generation
        self.skip_pixel = skip_pixel
        self.skip_db = skip_db
        self.backend = backend

        # Runtime state
        self.prompts_data: dict = {}
        self.generated_count: int = 0
        self.failed_count: int = 0
        self.pixel_count: int = 0
        self.db_inserted: int = 0
        self.errors: list[str] = []
        self.start_time: float = time.time()

    @property
    def elapsed(self) -> str:
        elapsed = time.time() - self.start_time
        return f"{elapsed / 60:.1f}m"


# ─── Helper: run command in WSL2 ──────────────────────────────────────

def _run_wsl(cmd_str: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run a command inside WSL2 Ubuntu and return result."""
    full_cmd = ["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd_str]
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)


# ─── Node 2a: Generate via Diffusers (WSL2) ────────────────────────────

def node_generate_diffusers(state: PipelineState) -> PipelineState:
    """Run generation via Diffusers in WSL2 (recommended for stability)."""
    if state.skip_generation:
        print("  [SKIP] Generation disabled.")
        return state

    print(f"\n{'─'*60}")
    print("  [Node 2a] Generating assets via Diffusers (WSL2)...")
    print(f"{'─'*60}")

    # Check WSL2 availability
    try:
        r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", "echo ready"],
                          capture_output=True, text=True, timeout=5)
        if r.returncode != 0 or r.stdout.strip() != "ready":
            state.errors.append("WSL2 Ubuntu not available")
            return state
    except FileNotFoundError:
        state.errors.append("WSL not installed on this system")
        return state

    print("  WSL2: OK")

    for cat in state.categories:
        print(f"\n  Category: {cat}")
        cmd = (f"cd ~ && /home/docus/simmoon-cuda-env/bin/python3 "
               f"~/Simmoon_arc/simmoon_diffusers.py --category '{cat}'")
        print("    Running Diffusers in WSL2...")
        sys.stdout.flush()

        try:
            result = _run_wsl(cmd, timeout=600)
            if result.returncode == 0:
                print(f"    [OK] {cat} generated successfully")
                state.generated_count += 1
            else:
                stderr_tail = result.stderr.strip()[-200:] if result.stderr else "unknown error"
                print(f"    [FAIL] {cat}: {stderr_tail}")
                state.failed_count += 1
                state.errors.append(f"{cat}: Diffusers generation failed")
        except subprocess.TimeoutExpired:
            print(f"    [FAIL] {cat}: timed out after 600s")
            state.failed_count += 1
            state.errors.append(f"{cat}: Diffusers timed out")
        except Exception as e:
            print(f"    [FAIL] {cat}: {e}")
            state.failed_count += 1
            state.errors.append(f"{cat}: {e}")
        sys.stdout.flush()

    return state


# ─── Node 2b: Generate via GeneratorFactory (ComfyUI → InvokeAI → HF) ──

def node_generate_factory(state: PipelineState) -> PipelineState:
    """Run generation via GeneratorFactory with fallback chain."""
    if state.skip_generation:
        print("  [SKIP] Generation disabled.")
        return state

    print(f"\n{'─'*60}")
    print("  [Node 2b] Generating assets via GeneratorFactory...")
    print(f"{'─'*60}")

    GENERATOR = SCRIPT_DIR / "generate_comfyui.py"

    # Try unified generator factory first (preferred)
    if _FACTORY_AVAILABLE:
        try:
            factory = GeneratorFactory(config_path=str(CONFIG_PATH))
            active_backend = factory.get_active_backend()

            if active_backend == "none":
                raise RuntimeError("No generation backend available")

            print(f"  Active backend: {active_backend}")

            for cat in state.categories:
                print(f"\n  Category: {cat}")

                lora_list = None
                if state.lora:
                    parts = state.lora.split(":")
                    lora_list = [{
                        "name": parts[0],
                        "strength_model": float(parts[1]) if len(parts) > 1 else 1.0,
                        "strength_clip": float(parts[2]) if len(parts) > 2 else float(parts[1]) if len(parts) > 1 else 1.0,
                    }]

                try:
                    stats = factory.generate_category(
                        category=cat,
                        run_suffix=state.run_suffix,
                        checkpoint=state.checkpoint or "",
                        no_loras=state.no_loras,
                        loras=lora_list,
                        prompts_file=str(PROMPTS_PATH),
                    )
                    if stats.get("failed", 0) > 0:
                        state.failed_count += stats["failed"]
                        state.errors.append(f"{stats['failed']} failed in {cat}")
                    else:
                        state.generated_count += 1
                except Exception as e:
                    print(f"    [FAIL] {cat}: {e}")
                    state.failed_count += 1
                    state.errors.append(f"Generation failed for {cat}: {e}")

            return state

        except Exception as e:
            print(f"  [WARN] Generator factory failed ({e}), falling back to raw ComfyUI...")

    # Fallback: run generate_comfyui.py directly for each category
    for cat in state.categories:
        print(f"\n  Category: {cat}")
        cmd = [sys.executable, str(GENERATOR), "--categories", cat]

        if state.run_suffix:
            cmd.extend(["--suffix", state.run_suffix])
        if state.checkpoint:
            cmd.extend(["--checkpoint", state.checkpoint])
        if state.no_loras:
            cmd.append("--no-loras")
        if state.lora:
            cmd.extend(["--lora", state.lora])

        print(f"    Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False, text=True)

        if result.returncode == 0:
            print(f"    [OK] {cat} generated successfully")
            state.generated_count += 1
        else:
            print(f"    [FAIL] {cat} failed (exit {result.returncode})")
            state.failed_count += 1
            state.errors.append(f"Generation failed for {cat}")

    return state


# ─── Node 2: Router ────────────────────────────────────────────────────────

def node_generate(state: PipelineState) -> PipelineState:
    """Route to the correct generation node based on state.backend."""
    if state.backend == "diffusers":
        return node_generate_diffusers(state)
    elif state.backend == "comfyui":
        return node_generate_factory(state)
    else:
        return node_generate_factory(state)
