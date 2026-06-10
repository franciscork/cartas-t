#!/usr/bin/env python3
"""
SIMMOON Master Generator - Professional pixel art game sprite pipeline.
1. Generates images using diffusers at optimal resolution
2. Converts to genuine retro pixel art (SimCity 2000 style)
3. Saves both raw and pixelated versions

For buildings/tiles: game_res=64, colors=16
For larger scenes:  game_res=128, colors=32
For UI icons:       game_res=32, colors=8
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"
PROMPTS_PATH = SCRIPT_DIR / "simmoon_prompts.json"

GENERATOR_SCRIPT = SCRIPT_DIR / "simmoon_diffusers.py"
PIXELATOR_SCRIPT = SCRIPT_DIR / "simmoon_pixelator.py"

VENV_PYTHON = os.path.expanduser("~/ComfyUI/venv/bin/python")


# Pixel art settings per category (game resolution, colors)
CATEGORY_PIXEL_SETTINGS = {
    "businesses":      {"game_res": 64, "colors": 16},
    "vehicles":        {"game_res": 48, "colors": 16},
    "greenhouses":     {"game_res": 64, "colors": 16},
    "solar_energy":    {"game_res": 64, "colors": 16},
    "lunar_map":       {"game_res": 128, "colors": 32},
    "game_assets_misc": {"game_res": 64, "colors": 16},
    "ui_elements":     {"game_res": 32, "colors": 8},
    "lunar_sites":     {"game_res": 128, "colors": 32},
}


def run_cmd(cmd, timeout=600):
    """Run a command and return output."""
    print(f"  $ {cmd[:120]}...")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def generate_pixel_art(categories=None, dry_run=False, only_pixelate=False):
    """Full pipeline: generate + pixelate."""
    config = json.load(open(CONFIG_PATH))
    prompts = json.load(open(PROMPTS_PATH))

    print("=" * 70)
    print(f"  SIMMOON Master Pixel Art Generator")
    print(f"  Mode: {'DRY RUN' if dry_run else 'FULL GENERATION'}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Determine which categories to process
    cats = prompts["categories"]
    if categories:
        cats = {k: v for k, v in cats.items() if k in categories}

    total = sum(len(c["prompts"]) for c in cats.values())
    print(f"\n[*] Categories to process: {', '.join(cats.keys())}")
    print(f"[*] Total images: {total}")

    if dry_run:
        print("\n[DRY RUN] Settings per category:")
        for cat_name, cat_data in cats.items():
            ps = CATEGORY_PIXEL_SETTINGS.get(cat_name, {"game_res": 64, "colors": 16})
            print(f"  {cat_name:20s} -> {ps['game_res']}x{ps['game_res']}px, {ps['colors']} colors")
        print(f"\n[DRY RUN] Pipeline steps:")
        print(f"  1. Generate with diffusers (512x512 base)")
        print(f"  2. Pixelate: downsample -> quantize -> outline -> upscale")
        print(f"  3. Save as: {{name}}_pixel.png")
        print("[DRY RUN] No images were generated.")
        return

    # Step 1: Generate raw images (skip if already exist)
    print(f"\n{'='*60}")
    print(f"  STEP 1: Generate raw images with diffusers")
    print(f"{'='*60}")

    if only_pixelate:
        print("  [SKIP] Only pixelating existing images")
    else:
        for cat_name in cats:
            print(f"\n  --- Generating {cat_name}...")
            cmd = f"{VENV_PYTHON} {GENERATOR_SCRIPT} --category {cat_name}"
            rc, out, err = run_cmd(cmd, timeout=1800)
            if rc != 0:
                print(f"  [WARN] Generation for {cat_name} had issues:")
                print(err[-500:] if err else out[-500:])
            else:
                print(f"  [OK] {cat_name} generated")

    # Step 2: Pixelate all images
    print(f"\n{'='*60}")
    print(f"  STEP 2: Convert to pixel art")
    print(f"{'='*60}")

    total_pixelated = 0
    for cat_name, cat_data in cats.items():
        output_dir_name = cat_data["output_dir"].replace("Simmoon_arc/", "")
        source_dir = SCRIPT_DIR / output_dir_name

        ps = CATEGORY_PIXEL_SETTINGS.get(cat_name, {"game_res": 64, "colors": 16})
        pixel_output_dir = SCRIPT_DIR / f"{output_dir_name}_pixel"

        if not source_dir.exists():
            print(f"  [SKIP] {cat_name}: source directory not found ({source_dir})")
            continue

        print(f"\n  --- Pixelating {cat_name}...")
        os.makedirs(pixel_output_dir, exist_ok=True)

        cmd = (
            f"{VENV_PYTHON} {PIXELATOR_SCRIPT} "
            f"--directory {source_dir} "
            f"--output-dir {pixel_output_dir} "
            f"--game-res {ps['game_res']} "
            f"--colors {ps['colors']} "
            f"--outline 1.5 "
            f"--suffix _pixel"
        )
        rc, out, err = run_cmd(cmd, timeout=120)
        if rc != 0:
            print(f"  [WARN] Pixelation for {cat_name} had issues:")
            print(err[-300:] if err else out[-300:])
        else:
            # Count pixelated files
            pixel_files = list(pixel_output_dir.glob("*_pixel.png"))
            print(f"  [OK] {cat_name}: {len(pixel_files)} pixel art images created")
            total_pixelated += len(pixel_files)

        time.sleep(1)

    # Summary
    print(f"\n{'='*70}")
    print(f"  PIXEL ART GENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"  Total pixel art images created: {total_pixelated}")
    print(f"  Pixelated versions saved in: *_pixel/ directories")
    print(f"  Original versions preserved in: original directories")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON Master Generator - Full pixel art game sprite pipeline"
    )
    parser.add_argument(
        "--category", "-c",
        nargs="+",
        default=None,
        help="Specific categories to process (default: all)"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Show what would be done without generating"
    )
    parser.add_argument(
        "--only-pixelate",
        action="store_true",
        help="Skip generation, only pixelate existing images"
    )
    parser.add_argument(
        "--list-settings",
        action="store_true",
        help="Show pixel art settings per category"
    )

    args = parser.parse_args()

    if args.list_settings:
        print("\nPixel art settings per category:")
        for cat, ps in sorted(CATEGORY_PIXEL_SETTINGS.items()):
            print(f"  {cat:20s} game_res={ps['game_res']:3d}px, colors={ps['colors']:2d}")
        return

    generate_pixel_art(
        categories=args.category,
        dry_run=args.dry_run,
        only_pixelate=args.only_pixelate,
    )


if __name__ == "__main__":
    main()
