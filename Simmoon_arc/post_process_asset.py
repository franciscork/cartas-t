#!/usr/bin/env python3
"""
SIMMOON - Post-procesado automatico de assets
Procesa un asset generado por ComfyUI: ajusta color, escala, anyade borde,
convierte a paleta indexada y genera miniatura.

Uso:
    python post_process_asset.py <archivo_entrada> [--output DIR] [--scale 0.5] [--border 2]
"""

import os
import sys
import subprocess
import tempfile
import argparse
import shutil
from pathlib import Path

# --- Detectar GIMP -----------------------------------------------------------
GIMP_PATH = None
_GIMP_CANDIDATES = [
    # GIMP 3.x (instalado via installer oficial o en AppData)
    r"C:\Users\docus\AppData\Local\Programs\GIMP 3\bin\gimp-3.2.exe",
    r"C:\Users\docus\AppData\Local\Programs\GIMP 3\bin\gimp-3.exe",
    r"C:\Program Files\GIMP 3\bin\gimp-console-3.0.exe",
    r"C:\Program Files\GIMP 3\bin\gimp-console.exe",
    # GIMP 2.x
    r"C:\Program Files\GIMP 2\bin\gimp-console-2.10.exe",
    r"C:\Program Files\GIMP 2\bin\gimp-console.exe",
    r"C:\Program Files\GIMP\bin\gimp-console-2.10.exe",
]
for _p in _GIMP_CANDIDATES:
    if os.path.isfile(_p):
        GIMP_PATH = _p
        break
if not GIMP_PATH:
    for _name in (
        "gimp-3.2", "gimp-3", "gimp-console-3.0",
        "gimp-console-2.10", "gimp-console", "gimp"
    ):
        _found = shutil.which(_name)
        if _found:
            GIMP_PATH = _found
            break

# --- PIL/Pillow --------------------------------------------------------------
try:
    from PIL import Image, ImageOps
    PIL_OK = True
except ImportError:
    PIL_OK = False


def process_pil(input_path, output_path, scale=0.5, border=2):
    """Post-procesa con PIL/Pillow: auto-contraste, escalado, borde, paleta."""
    img = Image.open(input_path).convert("RGBA")
    print(f"  Original: {img.size[0]}x{img.size[1]}")

    # 1. Auto-contraste (autocontrast no soporta RGBA, pasamos por RGB)
    alpha = img.split()[3] if img.mode == "RGBA" else None
    if alpha:
        rgb = img.convert("RGB")
        rgb = ImageOps.autocontrast(rgb, cutoff=2)
        r, g, b = rgb.split()
        img = Image.merge("RGBA", (r, g, b, alpha))
    else:
        img = ImageOps.autocontrast(img, cutoff=2)
    print("  + Auto-contraste")

    # 2. Escalar
    new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
    img = img.resize(new_size, Image.LANCZOS)
    print(f"  + Escalado: {new_size[0]}x{new_size[1]}")

    # 3. Borde
    if border > 0:
        img = ImageOps.expand(img, border=border, fill=(45, 52, 54, 255))
        print(f"  + Borde: {border}px")

    # 4. Paleta indexada (quantize no soporta RGBA, pasamos por RGB)
    alpha = img.split()[3]
    rgb = img.convert("RGB")
    rgb_q = rgb.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    # Convertir paleta de vuelta a RGB, luego añadir alpha original escalado
    rgb_q_rgba = rgb_q.convert("RGBA")
    # Escalar alpha al nuevo tamano si es necesario
    if rgb_q_rgba.size != alpha.size:
        alpha = alpha.resize(rgb_q_rgba.size, Image.LANCZOS)
    r2, g2, b2, _ = rgb_q_rgba.split()
    img = Image.merge("RGBA", (r2, g2, b2, alpha))
    print("  + Paleta: 64 colores")

    # Guardar
    out = Path(output_path)
    img.save(str(out), "PNG")
    size_kb = os.path.getsize(str(out)) / 1024
    print(f"  + Guardado: {out.name} ({size_kb:.1f} KB)")
    print(f"  + Tamano: {img.size[0]}x{img.size[1]}")

    # Miniatura
    thumb_path = out.with_name(out.stem + "_thumb.png")
    thumb = img.copy()
    thumb.thumbnail((128, 128), Image.LANCZOS)
    thumb.save(str(thumb_path), "PNG")
    print(f"  + Miniatura: {thumb_path.name}")

    return True


def process_gimp(input_path, output_path, scale=0.5, border=2):
    """Post-procesa con GIMP batch mode via Script-Fu.

    Si GIMP 3.x se cuelga en Windows (bug conocido), hace fallback a PIL.
    """
    in_path = str(input_path).replace("\\", "/")
    out_path = str(output_path).replace("\\", "/")

    script = f"""(define (simmoon-process infile outfile scale border)
  (let* ((image (car (gimp-file-load RUN-NONINTERACTIVE infile infile)))
         (drawable (car (gimp-image-get-active-layer image)))
         (width (car (gimp-image-width image)))
         (height (car (gimp-image-height image))))
    (gimp-levels-stretch drawable)
    (gimp-image-scale image (* width scale) (* height scale))
    (gimp-image-resize image
      (+ (* width scale) (* 2 border))
      (+ (* height scale) (* 2 border))
      border border)
    (gimp-layer-resize-to-image-size drawable)
    (gimp-image-flatten image)
    (gimp-file-save RUN-NONINTERACTIVE image drawable outfile outfile)
    (gimp-image-delete image)))

(simmoon-process "{in_path}" "{out_path}" {scale} {border})
(gimp-quit 0)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".scm", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            [GIMP_PATH, "--no-splash", "-i", "-b", f"(load \"{script_path}\")"],
            capture_output=True, text=True, timeout=20,
        )
        os.unlink(script_path)
        if result.returncode == 0:
            print(f"  + GIMP: procesado -> {output_path.name}")
            return True
        else:
            print(f"  ! GIMP error (rc={result.returncode}): {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ! GIMP timeout (20s) — bug conocido de GIMP 3.x en Windows")
        if os.path.exists(script_path):
            os.unlink(script_path)
        # Fallback a PIL
        if PIL_OK:
            print("  [FALLBACK] Usando PIL/Pillow en vez de GIMP")
            return process_pil(str(input_path), str(output_path), scale, border)
        return False
    except Exception as e:
        print(f"  ! GIMP fallo: {e}")
        if os.path.exists(script_path):
            os.unlink(script_path)
        return False


def process_single(input_path, output_dir, scale, border, use_gimp):
    """Process a single asset file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}_processed.png"

    print(f"\n[POST-PROC] {input_path.name}")
    print(f"  Escala: {scale} | Borde: {border}px")
    print(f"  Salida: {output_path}")

    if use_gimp:
        if GIMP_PATH:
            print("  [GIMP] Usando GIMP batch mode")
            ok = process_gimp(str(input_path), str(output_path), scale, border)
        else:
            print("  [!] GIMP no encontrado, usando PIL como alternativa")
            ok = process_pil(str(input_path), str(output_path), scale, border)
    elif PIL_OK:
        print("  [PIL] Usando PIL/Pillow")
        ok = process_pil(str(input_path), str(output_path), scale, border)
    else:
        print("  [ERROR] No hay motor de procesado. Instala Pillow: pip install Pillow")
        return False

    if ok:
        print(f"  [OK] {output_path.name}")
    else:
        print(f"  [ERROR] Fallo: {input_path.name}")
    return ok


def process_directory(input_dir, output_base_dir, scale, border, use_gimp):
    """Batch process all PNG files in a directory."""
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        print(f"[ERROR] Directorio no encontrado: {input_dir}")
        return 0, 0

    png_files = sorted(input_dir.glob("*.png"))
    if not png_files:
        print(f"[WARN] No hay archivos PNG en {input_dir}")
        return 0, 0

    output_dir = Path(output_base_dir) if output_base_dir else input_dir / "postproc"
    print(f"\n{'='*60}")
    print(f"[BATCH] Procesando {len(png_files)} PNGs en: {input_dir.name}")
    print(f"[BATCH] Salida: {output_dir}")
    print(f"{'='*60}")

    ok_count = 0
    fail_count = 0
    for i, f in enumerate(png_files, 1):
        print(f"\n  [{i}/{len(png_files)}]", end="")
        if process_single(f, output_dir, scale, border, use_gimp):
            ok_count += 1
        else:
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"[BATCH] Completado: {ok_count} OK, {fail_count} FAIL de {len(png_files)} total")
    print(f"{'='*60}")
    return ok_count, fail_count


def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON - Post-procesado automatico de assets"
    )
    parser.add_argument("input", nargs="?", default=None,
                        help="Archivo PNG de entrada (omite para --directory)")
    parser.add_argument("--directory", "-d", default=None,
                        help="Directorio con PNGs para procesamiento batch")
    parser.add_argument("--output", "-o", default=None,
                        help="Directorio de salida")
    parser.add_argument("--scale", type=float, default=0.5,
                        help="Factor de escala (defecto: 0.5)")
    parser.add_argument("--border", type=int, default=2,
                        help="Borde en px (defecto: 2)")
    parser.add_argument("--gimp", action="store_true",
                        help="Forzar GIMP en vez de PIL")
    args = parser.parse_args()

    use_gimp = args.gimp

    if args.directory:
        process_directory(args.directory, args.output, args.scale, args.border, use_gimp)
        return

    if not args.input:
        print("[ERROR] Especifica un archivo de entrada o usa --directory para batch")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"[ERROR] Archivo no encontrado: {input_path}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else input_path.parent / "postproc"
    ok = process_single(input_path, output_dir, args.scale, args.border, use_gimp)
    if ok:
        print(f"\n[OK] Post-procesado completado")
    else:
        print(f"\n[ERROR] Fallo en post-procesado")
        sys.exit(1)


if __name__ == "__main__":
    main()
