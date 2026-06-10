#!/usr/bin/env python3
"""
SIMMOON Pixelator Batch Runner
Ejecuta simmoon_pixelator.py en todos los directorios de imagenes generadas.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PIXELATOR = SCRIPT_DIR / "simmoon_pixelator.py"

DIRECTORIES = [
    ("businesses", 64, 16),
    ("vehicles", 48, 16),
    ("greenhouses", 64, 16),
    ("solar_energy", 64, 16),
    ("lunar_map", 64, 16),
    ("buildings_misc", 64, 16),
    ("lunar_sites", 128, 32),
    ("ui_elements", 32, 8),
]


def main():
    total_processed = 0
    total_failed = 0

    for dirname, game_res, colors in DIRECTORIES:
        input_dir = SCRIPT_DIR / dirname
        if not input_dir.exists():
            print(f"[SKIP] Directory not found: {input_dir}")
            total_failed += 1
            continue

        print(f"\n{'='*50}")
        print(f"Processing: {dirname} (res={game_res}, colors={colors})")
        print(f"{'='*50}")

        cmd = [
            sys.executable, str(PIXELATOR),
            "--directory", str(input_dir),
            "--game-res", str(game_res),
            "--colors", str(colors),
            "--outline", "1.5",
        ]

        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            total_processed += 1
        else:
            print(f"[ERROR] {dirname} failed with code {result.returncode}")
            total_failed += 1

    print(f"\n{'='*50}")
    print(f"DONE: {total_processed} dirs processed, {total_failed} failed")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
