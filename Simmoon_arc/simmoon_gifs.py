#!/usr/bin/env python3
"""
SIMMOON GIF Generator — Crea GIFs animados por categoría de assets pixel-art.
Usa ImageMagick (magick) para procesamiento por lote.

Uso:
    python simmoon_gifs.py                          # GIFs de todas las categorías
    python simmoon_gifs.py --categories businesses vehicles  # Solo esas
    python simmoon_gifs.py --delay 150               # 150 centésimas entre frames (default)
    python simmoon_gifs.py --resize 256              # Redimensionar a 256px de ancho
    python simmoon_gifs.py --loop 0                  # Loop infinito (default)
    python simmoon_gifs.py --output-dir ../simmoon_gifs  # Directorio de salida
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_OUTPUT = SCRIPT_DIR / "gifs"
DEFAULT_DELAY = 150  # centésimas de segundo (1.5s por frame)
DEFAULT_RESIZE = 0   # 0 = no redimensionar
DEFAULT_LOOP = 0     # 0 = loop infinito

# Mapa de nombres descriptivos para categorías
CATEGORY_NAMES = {
    "buildings_misc": "Edificios",
    "businesses": "Negocios",
    "characters": "Personajes",
    "civic": "Cívico",
    "decorations": "Decoración",
    "government": "Gobierno",
    "greenhouses": "Invernaderos",
    "housing": "Vivienda",
    "industry": "Industria",
    "infrastructure": "Infraestructura",
    "life_support": "Soporte Vital",
    "lunar_flora": "Flora Lunar",
    "lunar_map": "Mapa Lunar",
    "lunar_sites": "Sitios Lunares",
    "risk_management": "Gestión de Riesgos",
    "roads": "Carreteras",
    "solar_energy": "Energía",
    "transport": "Transporte",
    "ui_elements": "UI / Iconos",
    "vehicles": "Vehículos",
}


def find_magick() -> str:
    """Find ImageMagick executable."""
    candidates = [
        "magick",
        "magick.exe",
        r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe",
        r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\convert.exe",
    ]
    for cmd in candidates:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    # Try with PATH
    for path in os.environ.get("PATH", "").split(os.pathsep):
        for name in ("magick.exe", "magick", "convert.exe"):
            full = Path(path) / name
            if full.exists():
                return str(full)
    return ""


def get_pixel_dirs() -> list[tuple[str, Path]]:
    """Find all *_pixel directories and return (category_name, path) pairs."""
    dirs = []
    for d in sorted(SCRIPT_DIR.iterdir()):
        if d.is_dir() and d.name.endswith("_pixel"):
            cat = d.name[:-6]  # Remove '_pixel' suffix
            dirs.append((cat, d))
    return dirs


def get_png_files(pixel_dir: Path) -> list[Path]:
    """Get sorted list of PNG files in a pixel directory."""
    return sorted(p for p in pixel_dir.iterdir() if p.suffix.lower() == ".png")


def generate_gif(
    magick_cmd: str,
    png_files: list[Path],
    output_path: Path,
    delay: int,
    resize: int,
    loop: int,
) -> bool:
    """Generate an animated GIF from a list of PNG files using ImageMagick."""
    if not png_files:
        print(f"    [!] No hay PNGs en este directorio")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build ImageMagick command
    # Order: magick input1 input2 ... [settings] output
    cmd = [magick_cmd]

    # Add input files first
    for f in png_files:
        cmd.append(str(f))

    # Add -resize if specified (after inputs, before output)
    if resize > 0:
        cmd.extend(["-resize", f"{resize}x{resize}"])  # no '>' suffix on Windows

    # GIF options and output
    cmd.extend([
        "-delay", str(delay),
        "-loop", str(loop),
        "-layers", "Optimize",
        str(output_path),
    ])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"    [FAIL] Error: {result.stderr.strip()[:200]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    [FAIL] Timeout (120s)")
        return False
    except Exception as e:
        print(f"    [FAIL] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON GIF Generator — Crea GIFs animados de assets pixel-art",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--categories", "-c", nargs="*", default=None,
                        help="Categorías a procesar (default: todas)")
    parser.add_argument("--delay", "-d", type=int, default=DEFAULT_DELAY,
                        help=f"Delay entre frames en centésimas (default: {DEFAULT_DELAY} = 1.5s)")
    parser.add_argument("--resize", "-r", type=int, default=DEFAULT_RESIZE,
                        help=f"Redimensionar ancho en px (default: {DEFAULT_RESIZE} = original)")
    parser.add_argument("--loop", "-l", type=int, default=DEFAULT_LOOP,
                        help=f"Número de loops (default: {DEFAULT_LOOP} = infinito)")
    parser.add_argument("--output-dir", "-o", type=str, default=str(DEFAULT_OUTPUT),
                        help=f"Directorio de salida (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--fps", type=float, default=0,
                        help="Fotogramas por segundo (alternativa a --delay, ej: 2 = 2 fps)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo mostrar qué se generaría")

    args = parser.parse_args()

    # Resolve delay from fps if specified
    delay = args.delay
    if args.fps > 0:
        delay = int(100 / args.fps)  # Convert fps to centiseconds

    output_dir = Path(args.output_dir).resolve()

    # Find ImageMagick
    magick_cmd = find_magick()
    if not magick_cmd:
        print("[FAIL] ImageMagick no encontrado.")
        print("   Instálalo con: choco install imagemagick")
        print("   O descarga: https://imagemagick.org/script/download.php")
        sys.exit(1)

    print(f"[OK] ImageMagick: {magick_cmd}")
    print(f"[OK] Output dir: {output_dir}")
    print(f"[OK] Delay: {delay}cs ({delay / 100:.1f}s por frame)")
    print(f"[OK] Loop: {'inf' if args.loop == 0 else args.loop}")
    if args.resize:
        print(f"[OK] Resize: {args.resize}px ancho max")
    print()

    # Find pixel directories
    all_dirs = get_pixel_dirs()

    if args.categories:
        filtered = [(c, p) for c, p in all_dirs if c in args.categories]
        not_found = [c for c in args.categories if c not in dict(all_dirs)]
        if not_found:
            print(f"    [!] Categorias no encontradas: {', '.join(not_found)}")
        all_dirs = filtered

    if not all_dirs:
        print("[FAIL] No se encontraron directorios de assets pixel-art.")
        print("   Buscando en:", SCRIPT_DIR)
        sys.exit(1)

    # Generate GIFs
    total = len(all_dirs)
    ok = 0
    fail = 0

    print(f"[START] Generando {total} GIFs...\n")

    for i, (cat, pixel_dir) in enumerate(all_dirs, 1):
        pngs = get_png_files(pixel_dir)
        cat_name = CATEGORY_NAMES.get(cat, cat)
        out_file = output_dir / f"{cat}_preview.gif"

        print(f"  [{i}/{total}] {cat_name} ({cat}) - {len(pngs)} assets")

        if not pngs:
            print(f"    [!] Sin PNGs, saltando")
            fail += 1
            continue

        if args.dry_run:
            print(f"    -> {out_file.name}")
            for p in pngs:
                print(f"      - {p.name}")
            ok += 1
            continue

        # Generate the GIF
        success = generate_gif(magick_cmd, pngs, out_file, delay, args.resize, args.loop)
        if success:
            size_kb = out_file.stat().st_size / 1024
            print(f"    [OK] {out_file.name} ({size_kb:.0f} KB)")
            ok += 1
        else:
            print(f"    [FAIL] Fallo")
            fail += 1

    # Summary
    print(f"\n{'='*50}")
    if args.dry_run:
        print(f"  Dry run: {ok} GIFs listos para generar, {fail} errores")
    else:
        print(f"  [OK] {ok} GIFs generados en: {output_dir}")
        if fail:
            print(f"  [FAIL] {fail} fallos")
        print(f"\n  Para verlos:")
        print(f"    start {output_dir}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
