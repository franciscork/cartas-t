#!/usr/bin/env python3
"""
SIMMOON Pipeline — Orquestador del workflow de generacion de assets.
Chains: Prompts → ComfyUI → Pixel Art → PostgreSQL

La logica de generacion se ha extraido a pipeline_generator.py.

Usage:
    python simmoon_pipeline.py --category businesses
    python simmoon_pipeline.py --category vehicles greenhouses --run-suffix dreamshaper_v8
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pipeline_generator import PipelineState, node_generate

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_PATH = SCRIPT_DIR / "simmoon_prompts.json"
PIXELATOR = SCRIPT_DIR / "simmoon_pixelator.py"


# ─── Node 1: Load Config & Prompts ─────────────────────────────────────────

def node_load_config(state: PipelineState) -> PipelineState:
    """Load prompts and config into state."""
    print(f"\n{'='*60}")
    print(f"  SIMMOON Pipeline v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    if not PROMPTS_PATH.exists():
        state.errors.append(f"Prompts file not found: {PROMPTS_PATH}")
        return state

    with open(PROMPTS_PATH) as f:
        state.prompts_data = json.load(f)

    available = set(state.prompts_data.get("categories", {}).keys())
    requested = set(state.categories)
    if requested and not requested.issubset(available):
        missing = requested - available
        state.errors.append(f"Unknown categories: {missing}. Available: {sorted(available)}")
        return state

    cats = state.categories if state.categories else list(available)
    state.categories = cats

    total = sum(len(state.prompts_data["categories"][c].get("prompts", [])) for c in cats)
    print(f"  Categories: {len(cats)}  |  Total prompts: {total}")
    print(f"  Run suffix: '{state.run_suffix}'  |  Checkpoint: {state.checkpoint or 'default'}")
    return state


# ─── Node 3: Convert to Pixel Art ──────────────────────────────────────────

def node_pixelate(state: PipelineState) -> PipelineState:
    """Run simmoon_pixelator.py on each generated directory."""
    if state.skip_pixel:
        print(f"\n  [SKIP] Pixel art conversion disabled.")
        return state

    print(f"\n{'─'*60}")
    print(f"  [Node 3] Converting to pixel art...")
    print(f"{'─'*60}")

    CATEGORY_SETTINGS = {
        "businesses":      (64, 16), "vehicles":       (48, 16),
        "greenhouses":     (64, 16), "solar_energy":   (64, 16),
        "lunar_map":       (64, 16), "buildings_misc": (64, 16),
        "lunar_sites":     (128, 32),"ui_elements":    (32, 8),
        "roads":           (64, 16), "decorations":    (64, 16),
        "characters":      (64, 16), "lunar_flora":    (64, 16),
        "infrastructure":  (64, 16),
    }

    for cat in state.categories:
        res, colors = CATEGORY_SETTINGS.get(cat, (64, 16))
        input_dir = SCRIPT_DIR / cat

        if not input_dir.exists():
            print(f"    [SKIP] Directory not found: {cat}")
            continue

        print(f"\n  Category: {cat} ({res}px, {colors} colors)")

        cmd = [
            sys.executable, str(PIXELATOR),
            "--directory", str(input_dir),
            "--game-res", str(res),
            "--colors", str(colors),
            "--outline", "1.5",
        ]

        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"    [OK] {cat} pixelated")
            state.pixel_count += 1
        else:
            print(f"    [FAIL] {cat} pixelation failed")

    return state


# ─── Node 4: Insert into PostgreSQL ────────────────────────────────────────

def node_insert_db(state: PipelineState) -> PipelineState:
    """Run populate_db.py to insert generation metadata into PostgreSQL."""
    if state.skip_db:
        print(f"\n  [SKIP] DB insertion disabled.")
        return state

    print(f"\n{'─'*60}")
    print(f"  [Node 4] Inserting into PostgreSQL...")
    print(f"{'─'*60}")

    db_script = SCRIPT_DIR / "populate_db.py"
    if not db_script.exists():
        state.errors.append(f"DB script not found: {db_script}")
        return state

    cmd = [sys.executable, str(db_script)]
    if state.run_suffix:
        cmd.extend(["--run-suffix", state.run_suffix])

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode == 0:
        print(f"  [OK] Database updated successfully")
        state.db_inserted = 1
    else:
        print(f"  [FAIL] Database update failed (exit {result.returncode})")
        state.errors.append("DB insertion failed")

    return state


# ─── Node 5: Report ────────────────────────────────────────────────────────

def node_report(state: PipelineState) -> PipelineState:
    """Print final summary."""
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE — {state.elapsed}")
    print(f"{'='*60}")
    print(f"  Categories processed: {len(state.categories)}")
    print(f"  Generation:  {'OK' if state.generated_count > 0 else 'SKIP'}"
          f" ({state.generated_count} cats)")
    print(f"  Pixel art:   {'OK' if state.pixel_count > 0 else 'SKIP'}"
          f" ({state.pixel_count} cats)")
    print(f"  DB insert:   {'OK' if state.db_inserted > 0 else 'SKIP'}")
    if state.errors:
        print(f"\n  ⚠️  {len(state.errors)} errors:")
        for err in state.errors:
            print(f"    • {err}")
    print(f"{'='*60}\n")
    return state


# ─── Pipeline Runner ───────────────────────────────────────────────────────

def run_pipeline(state: PipelineState) -> PipelineState:
    """Execute the pipeline nodes in sequence (LangGraph-style)."""
    state = node_load_config(state)
    if state.errors:
        node_report(state)
        return state

    state = node_generate(state)  # From pipeline_generator.py - routes to backend
    if state.errors:
        print(f"\n  [STOP] Generation errors detected, skipping pixelate and DB.")
        node_report(state)
        return state

    state = node_pixelate(state)
    if state.errors:
        print(f"\n  [STOP] Pixelation errors detected, skipping DB.")
        node_report(state)
        return state

    state = node_insert_db(state)
    state = node_report(state)
    return state


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SIMMOON Pipeline - LangGraph workflow: ComfyUI -> Pixel -> PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python simmoon_pipeline.py --category businesses vehicles
  python simmoon_pipeline.py --category greenhouses --run-suffix counterfeit_v30
  python simmoon_pipeline.py --category all --backend diffusers
  python simmoon_pipeline.py --category all --skip-generation
        """,
    )

    parser.add_argument("--category", "-c", nargs="+", default=[],
                        help="Categories to process (default: all)")
    parser.add_argument("--run-suffix", default="",
                        help="Suffix for generated filenames")
    parser.add_argument("--checkpoint", default="",
                        help="ComfyUI checkpoint (e.g. 'counterfeit_v30.safetensors')")
    parser.add_argument("--no-loras", action="store_true",
                        help="Disable LoRAs")
    parser.add_argument("--lora", default="",
                        help="LoRA spec: 'name:strength_model:strength_clip'")
    parser.add_argument("--backend", "-b", default="factory",
                        choices=["factory", "diffusers", "comfyui"],
                        help="Generation backend: factory (auto), diffusers (WSL2), comfyui (legacy)")
    parser.add_argument("--skip-generation", action="store_true",
                        help="Skip generation step")
    parser.add_argument("--skip-pixel", action="store_true",
                        help="Skip pixel art conversion step")
    parser.add_argument("--skip-db", action="store_true",
                        help="Skip PostgreSQL insertion step")

    args = parser.parse_args()

    state = PipelineState(
        categories=args.category,
        run_suffix=args.run_suffix,
        checkpoint=args.checkpoint,
        no_loras=args.no_loras,
        lora=args.lora,
        skip_generation=args.skip_generation,
        skip_pixel=args.skip_pixel,
        skip_db=args.skip_db,
        backend=args.backend,
    )

    run_pipeline(state)

    if state.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
