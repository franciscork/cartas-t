#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_blender_sprites.py — Pipeline completo: Blender 3D → Pixel Art → Post-proc

Flujo:
  1. blender_render_sprites.py → renders 512×512 en blender_renders/
  2. simmoon_pixelator.py → convierte a 64×64 pixel art
  3. post_process_asset.py → auto-contraste, borde, paleta indexada
  4. Copia al directorio _pixel de la categoría correspondiente

Uso:
  python generate_blender_sprites.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
BLENDER_SCRIPT = SCRIPT_DIR / "blender_render_sprites.py"
RENDERS_DIR = SCRIPT_DIR / "blender_renders"
PIXELATOR = SCRIPT_DIR / "simmoon_pixelator.py"
POSTPROC = SCRIPT_DIR / "post_process_asset.py"

# Mapeo de prefijos de render → categoría destino
SPRITE_MAP = {
    "char_drone_maintenance": ("characters_pixel", "char_dm_"),
    "flora_bioluminescent": ("lunar_flora_pixel", "flora_bl_"),
    "infra_sonic_extractor": ("infrastructure_pixel", "infra_se_"),
}


def run_blender():
    """Ejecuta Blender headless para generar los 3 renders.
    
    Si los renders ya existen, los salta automáticamente.
    """
    # Verificar si ya existen los renders
    all_exist = True
    for prefix in SPRITE_MAP:
        path = RENDERS_DIR / f"{prefix}.png"
        if path.exists():
            print(f"  ✅ {path.name} ya existe ({os.path.getsize(path)/1024:.1f} KB)")
        else:
            all_exist = False
    
    if all_exist:
        print(f"  ⏩ Los 3 renders ya existen, saltando Blender")
        return True
    
    if not os.path.isfile(BLENDER_EXE):
        print(f"❌ Blender no encontrado en: {BLENDER_EXE}")
        return False
    
    if not BLENDER_SCRIPT.exists():
        print(f"❌ Script no encontrado: {BLENDER_SCRIPT}")
        return False
    
    print(f"🧊 Ejecutando Blender 5.1 headless...")
    
    result = subprocess.run(
        [BLENDER_EXE, "--background", "--python", str(BLENDER_SCRIPT)],
        capture_output=True, text=True, timeout=180,
        cwd=str(SCRIPT_DIR),
        encoding="utf-8", errors="replace",
    )
    
    out = result.stdout or ""
    print(out[-2000:] if len(out) > 2000 else out)
    
    if result.returncode != 0:
        print(f"❌ Blender falló (exit {result.returncode})")
        err = result.stderr or ""
        if err:
            print(f"   STDERR: {err[-500:]}")
        return False
    
    # Verificar que los 3 renders existen
    for prefix in SPRITE_MAP:
        path = RENDERS_DIR / f"{prefix}.png"
        if not path.exists():
            print(f"❌ Falta render: {path}")
            return False
        print(f"  ✅ {path.name} ({os.path.getsize(path)/1024:.1f} KB)")
    
    return True


def pixelate_renders():
    """Convierte los renders 512×512 a pixel art 64×64."""
    if not PIXELATOR.exists():
        print(f"⚠️  Pixelator no encontrado, saltando pixelado")
        return True  # No es crítico
    
    print(f"\n🎨 Pixelando renders (64×64, 16 colores)...")
    
    for prefix in SPRITE_MAP:
        input_file = RENDERS_DIR / f"{prefix}.png"
        if not input_file.exists():
            continue
        
        # Crear directorio temporal para el pixelator
        tmp_dir = RENDERS_DIR / "tmp_pixel"
        tmp_dir.mkdir(exist_ok=True)
        tmp_copy = tmp_dir / input_file.name
        shutil.copy2(input_file, tmp_copy)
        
        result = subprocess.run(
            [sys.executable, str(PIXELATOR),
             "--directory", str(tmp_dir),
             "--game-res", "64",
             "--colors", "16",
             "--outline", "1.5"],
            capture_output=True, text=True, timeout=60,
            cwd=str(SCRIPT_DIR),
        )
        
        # Buscar el pixelado en _pixel/
        pixel_dir = tmp_dir.parent / f"{tmp_dir.name}_pixel"
        pixel_file = pixel_dir / input_file.name if pixel_dir.exists() else None
        
        if pixel_file and pixel_file.exists():
            # Copiar al directorio de renders
            output_file = RENDERS_DIR / f"{prefix}_pixel.png"
            shutil.copy2(pixel_file, output_file)
            print(f"  ✅ {prefix} → {output_file.name}")
        else:
            print(f"  ⚠️  Pixelado no generado para {prefix}, usando original")
            shutil.copy2(input_file, RENDERS_DIR / f"{prefix}_pixel.png")
        
        # Limpiar
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if pixel_dir and pixel_dir.exists():
            shutil.rmtree(pixel_dir, ignore_errors=True)
    
    return True


def postprocess_renders():
    """Post-procesa los renders pixelados (auto-contraste, paleta, borde)."""
    if not POSTPROC.exists():
        print(f"⚠️  Post-processor no encontrado, saltando")
        return True
    
    print(f"\n🔧 Post-procesando renders...")
    
    for prefix in SPRITE_MAP:
        input_file = RENDERS_DIR / f"{prefix}_pixel.png"
        if not input_file.exists():
            input_file = RENDERS_DIR / f"{prefix}.png"
        if not input_file.exists():
            continue
        
        out_dir = RENDERS_DIR / "postproc"
        out_dir.mkdir(exist_ok=True)
        
        result = subprocess.run(
            [sys.executable, str(POSTPROC),
             str(input_file),
             "--output", str(out_dir),
             "--scale", "1.0",   # Ya está a 64×64
             "--border", "2"],
            capture_output=True, text=True, timeout=60,
            cwd=str(SCRIPT_DIR),
        )
        
        if result.returncode == 0:
            processed = out_dir / f"{input_file.stem}_processed.png"
            if processed.exists():
                print(f"  ✅ {prefix} → {processed.name}")
        else:
            print(f"  ⚠️  Post-proc falló para {prefix}: {result.stderr[:200]}")
    
    return True


def copy_to_asset_dirs():
    """Copia los sprites finales a los directorios de assets del juego."""
    print(f"\n📁 Copiando a directorios de assets...")
    
    for prefix, (asset_dir, new_name) in SPRITE_MAP.items():
        # Buscar la versión procesada, luego pixelada, luego original
        processed = RENDERS_DIR / "postproc" / f"{prefix}_pixel_processed.png"
        pixel = RENDERS_DIR / f"{prefix}_pixel.png"
        original = RENDERS_DIR / f"{prefix}.png"
        
        source = None
        if processed.exists():
            source = processed
        elif pixel.exists():
            source = pixel
        elif original.exists():
            source = original
        
        if source:
            dest_dir = SCRIPT_DIR / asset_dir
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / f"{new_name}blender_01.png"
            shutil.copy2(source, dest)
            print(f"  ✅ {source.name} → {dest}")
        else:
            print(f"  ❌ No se encontró sprite para {prefix}")


def main():
    print(f"\n{'='*60}")
    print(f"  🏭 PIPELINE BLENDER → SPRITES")
    print(f"  Conceptos: CreativoJuegos (Drone, Planta, Sonocreador)")
    print(f"  Blender 5.1 → 64×64 pixel art → post-proc")
    print(f"{'='*60}\n")
    
    # Paso 1: Blender
    if not run_blender():
        print("\n❌ Pipeline abortado en fase Blender")
        return 1
    
    # Paso 2: Pixelar
    pixelate_renders()
    
    # Paso 3: Post-procesar
    postprocess_renders()
    
    # Paso 4: Copiar a directorios de assets
    copy_to_asset_dirs()
    
    print(f"\n{'='*60}")
    print(f"  ✅ PIPELINE COMPLETADO")
    print(f"  Assets generados:")
    print(f"    📁 characters_pixel/char_dm_blender_01.png")
    print(f"    📁 lunar_flora_pixel/flora_bl_blender_01.png")
    print(f"    📁 infrastructure_pixel/infra_se_blender_01.png")
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
