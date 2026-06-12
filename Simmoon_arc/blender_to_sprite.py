#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_to_sprite.py — Integración Blender → SIMMOON

Convierte cualquier modelo 3D (.blend, .obj, .fbx, .glb) en un sprite
pixel art listo para SIMMOON en un solo comando.

Pipeline:
  1. Blender render isométrico (Cycles, 512×512)
  2. Pixel art (64×64, 16 colores, outline)
  3. Post-procesado (auto-contraste, borde 2px, paleta indexada)
  4. Copia al directorio de assets de la categoría

Uso:
  # Desde un .blend
  python blender_to_sprite.py --input nave.blend --category vehicles --name lunar_shuttle

  # Desde un .obj
  python blender_to_sprite.py --input roca.obj --category decorations --name moon_rock

  # Batch: todos los .blend de un directorio
  python blender_to_sprite.py --input models/ --category characters --batch

  # Saltar Blender si el render ya existe
  python blender_to_sprite.py --input modelo.obj --category buildings_misc --skip-blender
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Paths ──────────────────────────────────────────────────────────────────
BLENDER_EXE = os.environ.get("BLENDER_PATH",
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
BLENDER_RENDER_SCRIPT = SCRIPT_DIR / "_blender_isometric_render.py"
PIXELATOR = SCRIPT_DIR / "simmoon_pixelator.py"
POSTPROC = SCRIPT_DIR / "post_process_asset.py"
PIPELINE_DIR = SCRIPT_DIR / "blender_pipeline"

# ── Categorías válidas y sus directorios ───────────────────────────────────
CATEGORY_DIRS = {
    "characters": "characters_pixel",
    "lunar_flora": "lunar_flora_pixel",
    "infrastructure": "infrastructure_pixel",
    "vehicles": "vehicles_pixel",
    "buildings_misc": "buildings_misc_pixel",
    "decorations": "decorations_pixel",
    "robots": "robots_pixel",
    "greenhouses": "greenhouses_pixel",
    "businesses": "businesses_pixel",
    "roads": "roads_pixel",
    "solar_energy": "solar_energy_pixel",
    "lunar_sites": "lunar_sites_pixel",
    "transport": "transport_pixel",
    "industry": "industry_pixel",
    "government": "government_pixel",
    "housing": "housing_pixel",
    "life_support": "life_support_pixel",
    "civic": "civic_pixel",
    "risk_management": "risk_management_pixel",
    "anomalies": "anomalies_pixel",
}


def validate_category(category: str) -> bool:
    """Verifica que la categoría sea válida."""
    if category not in CATEGORY_DIRS:
        valid = ", ".join(sorted(CATEGORY_DIRS.keys()))
        print(f"  ⚠️  Categoría '{category}' no reconocida. Válidas: {valid}")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════
#  Paso 1: Blender Render
# ══════════════════════════════════════════════════════════════════════════

def blender_render(input_file: str, output_file: str,
                   render_size: int = 512) -> bool:
    """Ejecuta Blender headless para renderizar un modelo en isométrico.

    Args:
        input_file: Ruta al .blend, .obj, .fbx, o .glb
        output_file: Ruta de salida del PNG
        render_size: Resolución del render (default 512×512)

    Returns:
        True si el render se generó exitosamente
    """
    if not os.path.isfile(BLENDER_EXE):
        print(f"  ❌ Blender no encontrado: {BLENDER_EXE}")
        return False

    if not BLENDER_RENDER_SCRIPT.exists():
        print(f"  ❌ Script no encontrado: {BLENDER_RENDER_SCRIPT}")
        return False

    if output_file and os.path.isfile(output_file):
        size_kb = os.path.getsize(output_file) / 1024
        print(f"  ⏩ Render ya existe: {output_file} ({size_kb:.1f} KB)")
        return True

    env = os.environ.copy()
    env["BLENDER_INPUT"] = os.path.abspath(input_file)
    env["BLENDER_OUTPUT"] = os.path.abspath(output_file)
    env["BLENDER_SIZE"] = str(render_size)

    print(f"  🧊 Renderizando {os.path.basename(input_file)}...")

    try:
        result = subprocess.run(
            [BLENDER_EXE, "--background", "--python", str(BLENDER_RENDER_SCRIPT)],
            capture_output=True, text=True, timeout=300,
            cwd=str(SCRIPT_DIR),
            encoding="utf-8", errors="replace",
            env=env,
        )
    except subprocess.TimeoutExpired:
        print(f"  ❌ Blender tardó más de 300s — timeout")
        return False
    except Exception as e:
        print(f"  ❌ Error ejecutando Blender: {e}")
        return False

    # Mostrar output relevante
    for line in (result.stdout or "").split("\n"):
        if any(kw in line for kw in ["✅", "❌", "⚠️", "📐", "📦", "🎬", "Error", "error"]):
            print(f"     {line.strip()}")

    if not os.path.isfile(output_file):
        print(f"  ❌ Render no se generó")
        err = (result.stderr or "")[-300:]
        if err:
            print(f"     {err}")
        return False

    size_kb = os.path.getsize(output_file) / 1024
    print(f"  ✅ Render: {os.path.basename(output_file)} ({size_kb:.1f} KB)")
    return True


# ══════════════════════════════════════════════════════════════════════════
#  Paso 2: Pixel Art
# ══════════════════════════════════════════════════════════════════════════

def pixelate_sprite(input_file: str, output_file: str,
                    game_res: int = 64, colors: int = 16,
                    outline: float = 1.5) -> bool:
    """Convierte un render a pixel art.

    Args:
        input_file: PNG del render
        output_file: PNG pixelado de salida
        game_res: Resolución final (default 64)
        colors: Número de colores de la paleta (8, 16, o 32)
        outline: Grosor del outline (default 1.5)

    Returns:
        True si el pixel art se generó exitosamente
    """
    if not PIXELATOR.exists():
        print(f"  ⚠️  Pixelator no encontrado, usando render original")
        shutil.copy2(input_file, output_file)
        return True

    if output_file and os.path.isfile(output_file):
        print(f"  ⏩ Pixel art ya existe: {os.path.basename(output_file)}")
        return True

    print(f"  🎨 Pixelando → {game_res}×{game_res}, {colors} colores...")

    # El pixelator procesa directorios, así que usamos un dir temporal
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_input = os.path.join(tmpdir, os.path.basename(input_file))
        shutil.copy2(input_file, tmp_input)

    try:
        result = subprocess.run(
            [sys.executable, str(PIXELATOR),
             "--directory", tmpdir,
             "--game-res", str(game_res),
             "--colors", str(colors),
             "--outline", str(outline)],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Pixelator timeout (60s), usando original")
        shutil.copy2(input_file, output_file)
        return True
    except Exception as e:
        print(f"  ⚠️  Error en pixelator: {e}, usando original")
        shutil.copy2(input_file, output_file)
        return True

        # El pixelator crea {tmpdir}_pixel/
        pixel_dir = tmpdir + "_pixel"
        pixel_file = os.path.join(pixel_dir, os.path.basename(input_file))

        if os.path.isfile(pixel_file):
            shutil.copy2(pixel_file, output_file)
            size_kb = os.path.getsize(output_file) / 1024
            print(f"  ✅ Pixel art: {os.path.basename(output_file)} ({size_kb:.1f} KB)")
            return True
        else:
            print(f"  ⚠️  Pixelator no generó output, usando original")
            shutil.copy2(input_file, output_file)
            return True


# ══════════════════════════════════════════════════════════════════════════
#  Paso 3: Post-Procesado
# ══════════════════════════════════════════════════════════════════════════

def postprocess_sprite(input_file: str, output_dir: str,
                       scale: float = 1.0, border: int = 2) -> Optional[str]:
    """Post-procesa un sprite pixelado: auto-contraste, paleta, borde.

    Args:
        input_file: PNG a post-procesar
        output_dir: Directorio de salida
        scale: Factor de escala (default 1.0 = sin escalar)
        border: Borde en px (default 2)

    Returns:
        Ruta del archivo procesado, o None si falló
    """
    if not POSTPROC.exists():
        print(f"  ⚠️  Post-processor no encontrado, usando original")
        return input_file

    os.makedirs(output_dir, exist_ok=True)

    # Verificar si ya existe
    stem = Path(input_file).stem
    processed = os.path.join(output_dir, f"{stem}_processed.png")
    if os.path.isfile(processed):
        print(f"  ⏩ Post-proc ya existe: {os.path.basename(processed)}")
        return processed

    print(f"  🔧 Post-procesando...")

    try:
        result = subprocess.run(
            [sys.executable, str(POSTPROC),
             str(input_file),
             "--output", output_dir,
             "--scale", str(scale),
             "--border", str(border)],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Post-proc timeout (60s), usando original")
        return input_file
    except Exception as e:
        print(f"  ⚠️  Error en post-proc: {e}, usando original")
        return input_file

    if os.path.isfile(processed):
        size_kb = os.path.getsize(processed) / 1024
        print(f"  ✅ Post-proc: {os.path.basename(processed)} ({size_kb:.1f} KB)")
        return processed
    else:
        print(f"  ⚠️  Post-proc no generó output")
        return None


# ══════════════════════════════════════════════════════════════════════════
#  Paso 4: Copia a directorio de assets
# ══════════════════════════════════════════════════════════════════════════

def copy_to_assets(sprite_file: str, category: str, name: str) -> Optional[str]:
    """Copia el sprite final al directorio de assets del juego.

    Args:
        sprite_file: Ruta al sprite procesado
        category: Categoría del sprite
        name: Nombre base del sprite

    Returns:
        Ruta final del sprite en el directorio de assets
    """
    if not validate_category(category):
        return None

    asset_dir = SCRIPT_DIR / CATEGORY_DIRS[category]
    asset_dir.mkdir(exist_ok=True)

    # Nombre final: {name}_blender.png
    dest = asset_dir / f"{name}_blender.png"

    shutil.copy2(sprite_file, dest)
    size_kb = os.path.getsize(dest) / 1024
    print(f"  📁 {dest.relative_to(SCRIPT_DIR)} ({size_kb:.1f} KB)")
    return str(dest)


# ══════════════════════════════════════════════════════════════════════════
#  Pipeline completo
# ══════════════════════════════════════════════════════════════════════════

def process_single(input_file: str, category: str, name: str,
                   render_size: int = 512, game_res: int = 64,
                   colors: int = 16, outline: float = 1.5,
                   border: int = 2, skip_blender: bool = False,
                   skip_pixelate: bool = False,
                   skip_postproc: bool = False) -> Optional[str]:
    """Pipeline completo: un modelo 3D → un sprite pixel art.

    Args:
        input_file: Ruta al archivo 3D
        category: Categoría del sprite
        name: Nombre base del sprite
        render_size: Resolución del render Blender
        game_res: Resolución final del pixel art
        colors: Colores de la paleta
        outline: Grosor del outline pixelado
        border: Borde del post-procesado
        skip_blender: Saltar render Blender
        skip_pixelate: Saltar pixelado
        skip_postproc: Saltar post-procesado

    Returns:
        Ruta final del sprite, o None si falló
    """
    ext = Path(input_file).suffix.lower()
    input_stem = name or Path(input_file).stem

    print(f"\n{'─'*55}")
    print(f"  🎯 {input_stem} → [{category}]")
    print(f"{'─'*55}")

    # Directorios de trabajo
    PIPELINE_DIR.mkdir(exist_ok=True)
    work_dir = PIPELINE_DIR / input_stem
    work_dir.mkdir(exist_ok=True)

    # ── 1. Blender Render ──
    render_file = work_dir / f"{input_stem}_render.png"
    if not skip_blender:
        if not blender_render(input_file, str(render_file), render_size):
            return None
    else:
        if not render_file.exists():
            print(f"  ❌ Render no encontrado: {render_file}")
            return None
        print(f"  ⏩ Saltando Blender, usando: {render_file.name}")

    # ── 2. Pixel Art ──
    pixel_file = work_dir / f"{input_stem}_pixel.png"
    if not skip_pixelate:
        pixelate_sprite(str(render_file), str(pixel_file),
                        game_res=game_res, colors=colors, outline=outline)
    else:
        if not pixel_file.exists():
            shutil.copy2(render_file, pixel_file)
        print(f"  ⏩ Saltando pixelado, usando: {pixel_file.name}")

    # ── 3. Post-Procesado ──
    postproc_dir = work_dir / "postproc"
    sprite_final = str(pixel_file)
    if not skip_postproc:
        result = postprocess_sprite(str(pixel_file), str(postproc_dir),
                                    scale=1.0, border=border)
        if result:
            sprite_final = result
    else:
        print(f"  ⏩ Saltando post-proc")

    # ── 4. Copiar a assets ──
    final_path = copy_to_assets(sprite_final, category, input_stem)

    return final_path


def process_batch(input_dir: str, category: str,
                  **kwargs) -> List[str]:
    """Procesa todos los modelos 3D de un directorio en batch.

    Args:
        input_dir: Directorio con archivos .blend/.obj/.fbx/.glb
        category: Categoría para todos los sprites
        **kwargs: Opciones pasadas a process_single

    Returns:
        Lista de rutas finales de sprites generados
    """
    extensions = {'.blend', '.obj', '.fbx', '.glb', '.gltf'}
    files = sorted([
        f for f in Path(input_dir).iterdir()
        if f.suffix.lower() in extensions and f.is_file()
    ])

    if not files:
        print(f"  ⚠️  No se encontraron modelos 3D en: {input_dir}")
        return []

    print(f"\n{'='*60}")
    print(f"  📦 BATCH: {len(files)} modelos en {input_dir}")
    print(f"  Categoría: {category}")
    print(f"{'='*60}")

    results = []
    ok = fail = 0
    for i, f in enumerate(files, 1):
        print(f"\n  [{i}/{len(files)}]", end="")
        name = kwargs.get('name') or f"{category}_{f.stem}"
        result = process_single(
            str(f), category, name, **{k: v for k, v in kwargs.items() if k != 'name'}
        )
        if result:
            results.append(result)
            ok += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    print(f"  ✅ BATCH COMPLETADO: {ok} OK, {fail} FAIL de {len(files)}")
    print(f"{'='*60}")
    return results


# ══════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🧊 blender_to_sprite — Modelo 3D → Sprite Pixel Art para SIMMOON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Un modelo .blend
  python blender_to_sprite.py -i nave.blend -c vehicles -n lunar_shuttle

  # Un modelo .obj
  python blender_to_sprite.py -i roca.obj -c decorations -n moon_rock

  # Batch: todos los .blend de un directorio
  python blender_to_sprite.py -i mis_modelos/ -c characters --batch

  # Saltar Blender si el render ya existe
  python blender_to_sprite.py -i modelo.obj -c buildings_misc --skip-blender

  # Tamaño de pixel art personalizado
  python blender_to_sprite.py -i item.blend -c decorations -n item --game-res 32 --colors 8
        """,
    )

    # ── Argumentos principales ──
    parser.add_argument("--input", "-i", default=None,
                        help="Archivo 3D (.blend/.obj/.fbx/.glb) o directorio con --batch")
    parser.add_argument("--category", "-c", default=None,
                        help="Categoría SIMMOON (characters, vehicles, buildings_misc, etc.)")
    parser.add_argument("--name", "-n", default=None,
                        help="Nombre base del sprite (default: nombre del archivo)")

    # ── Pipeline ──
    parser.add_argument("--batch", action="store_true",
                        help="Procesar todos los modelos de un directorio")
    parser.add_argument("--skip-blender", action="store_true",
                        help="Saltar render Blender (usar render existente)")
    parser.add_argument("--skip-pixelate", action="store_true",
                        help="Saltar pixelado")
    parser.add_argument("--skip-postproc", action="store_true",
                        help="Saltar post-procesado")

    # ── Parámetros de calidad ──
    parser.add_argument("--render-size", type=int, default=512,
                        help="Resolución del render Blender (default: 512)")
    parser.add_argument("--game-res", type=int, default=64,
                        help="Resolución final del sprite (default: 64)")
    parser.add_argument("--colors", type=int, default=16,
                        choices=[8, 16, 32],
                        help="Colores de la paleta pixel art (default: 16)")
    parser.add_argument("--outline", type=float, default=1.5,
                        help="Grosor del outline pixelado (default: 1.5)")
    parser.add_argument("--border", type=int, default=2,
                        help="Borde del post-procesado en px (default: 2)")

    # ── Listar categorías ──
    parser.add_argument("--list-categories", action="store_true",
                        help="Listar categorías disponibles y salir")

    args = parser.parse_args()

    # ── Listar categorías ──
    if args.list_categories:
        print(f"\n  📂 Categorías SIMMOON disponibles:\n")
        for cat, dirname in sorted(CATEGORY_DIRS.items()):
            exists = "✅" if (SCRIPT_DIR / dirname).exists() else "⚫"
            print(f"     {exists} {cat:20s} → {dirname}/")
        print()
        return

    # ── Validar argumentos requeridos ──
    if not args.input:
        parser.error("--input es requerido (usa --list-categories para ver categorías)")
    if not args.category:
        parser.error("--category es requerido (usa --list-categories para ver categorías)")

    # ── Validar categoría ──
    if not validate_category(args.category):
        sys.exit(1)

    # ── Validar Blender (si no se salta) ──
    if not args.skip_blender and not os.path.isfile(BLENDER_EXE):
        print(f"\n  ❌ Blender no encontrado en: {BLENDER_EXE}")
        print(f"     Instálalo o usa --skip-blender si el render ya existe")
        print(f"     O define BLENDER_PATH en variables de entorno\n")
        sys.exit(1)

    # ── Mostrar configuración ──
    print(f"\n{'='*60}")
    print(f"  🧊 blender_to_sprite — Integración Blender → SIMMOON")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  Input:      {args.input}")
    print(f"  Categoría:  {args.category}")
    print(f"  Nombre:     {args.name or '(auto)'}")
    print(f"  Pipeline:   Blender {args.render_size}px → Pixel {args.game_res}px/{args.colors}col → Post-proc")
    if args.skip_blender:
        print(f"  ⏩ Saltando Blender")
    if args.skip_pixelate:
        print(f"  ⏩ Saltando pixelado")
    if args.skip_postproc:
        print(f"  ⏩ Saltando post-proc")

    # ── Ejecutar ──
    kwargs = {
        "render_size": args.render_size,
        "game_res": args.game_res,
        "colors": args.colors,
        "outline": args.outline,
        "border": args.border,
        "skip_blender": args.skip_blender,
        "skip_pixelate": args.skip_pixelate,
        "skip_postproc": args.skip_postproc,
    }

    if args.batch or os.path.isdir(args.input):
        results = process_batch(args.input, args.category, name=args.name, **kwargs)
    else:
        result = process_single(args.input, args.category,
                                args.name or Path(args.input).stem, **kwargs)
        results = [result] if result else []

    if results:
        print(f"\n{'='*60}")
        print(f"  ✅ {len(results)} sprite(s) generado(s)")
        for r in results:
            print(f"     📁 {r}")
        print(f"{'='*60}\n")
    else:
        print(f"\n  ❌ No se generaron sprites\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
