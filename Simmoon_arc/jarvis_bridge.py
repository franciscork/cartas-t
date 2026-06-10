#!/usr/bin/env python3
"""
Jarvis Bridge — Puerto entre Jarvis y el generador SIMMOON.
Jarvis puede llamar a este script con comandos simples y recibe JSON.

Uso (para Jarvis):
    python jarvis_bridge.py status
    python jarvis_bridge.py generate --category businesses
    python jarvis_bridge.py pixelate --category businesses
    python jarvis_bridge.py gif --category businesses --delay 100 --resize 256
    python jarvis_bridge.py run --category all --mode diffusers
    python jarvis_bridge.py help

Salida: Siempre JSON, facil de parsear.
  {"ok": true, "data": {...}}
  {"ok": false, "error": "..."}
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Helpers ────────────────────────────────────────────────────────────────

def json_out(ok: bool, **kwargs):
    """Print JSON output and exit."""
    result = {"ok": ok}
    if ok:
        result["data"] = kwargs
    else:
        result["error"] = kwargs.get("error", "Unknown error")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    sys.exit(0 if ok else 1)


def check_wsl() -> bool:
    """Check if WSL2 Ubuntu is available for Diffusers generation."""
    try:
        r = subprocess.run(
            ["wsl", "-d", "Ubuntu", "--", "bash", "-c", "echo ready"],
            capture_output=True, text=True, timeout=5
        )
        return r.returncode == 0 and r.stdout.strip() == "ready"
    except Exception:
        return False


def run_in_wsl(cmd_parts: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a command inside WSL2 Ubuntu."""
    full_cmd = ["wsl", "-d", "Ubuntu", "--", "bash", "-c", " ".join(cmd_parts)]
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)


# ── Command: help ──────────────────────────────────────────────────────────

def cmd_help():
    print("""
╔══════════════════════════════════════════════════════╗
║        Jarvis Bridge — SIMMOON Generator            ║
╠══════════════════════════════════════════════════════╣
║  USO:                                               ║
║    python jarvis_bridge.py <comando> [opciones]     ║
╠══════════════════════════════════════════════════════╣
║  COMANDOS:                                          ║
║    status        Estado de backends disponibles     ║
║    generate      Generar assets (categorias)        ║
║    pixelate      Convertir a pixel-art              ║
║    gif           Crear GIFs animados                ║
║    run           Pipeline completo                  ║
║    synthesis     Resumen/síntesis de Agatha Actas   ║
║    help          Esta ayuda                         ║
╠══════════════════════════════════════════════════════╣
║  OPCIONES COMUNES:                                  ║
║    --category, -c  Categorias (ej: businesses)      ║
║    --all           Todas las categorias              ║
║    --mode, -m      Backend: factory|diffusers       ║
║    --days, -d      Días atrás (para synthesis)     ║
║    --json          Salida JSON siempre              ║
╚══════════════════════════════════════════════════════╝
""")
    sys.exit(0)


# ── Command: status ────────────────────────────────────────────────────────

def cmd_status():
    """Check all available backends and return status."""
    status = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "backends": {},
        "wsl_available": check_wsl(),
    }

    # Check GeneratorFactory backends (Windows)
    try:
        from generator_factory import GeneratorFactory
        gen = GeneratorFactory()

        status["backends"]["comfyui"] = gen._check_comfyui()
        status["backends"]["invokeai"] = gen._check_invokeai()
        status["backends"]["huggingface_api"] = gen._check_huggingface()
        status["backends"]["leonardo"] = gen._get_leonardo() is not None

        active = gen.get_active_backend()
        status["active_backend"] = active
    except Exception as e:
        status["backends"]["error"] = str(e)
        status["active_backend"] = "error"

    # Check WSL2 / Diffusers
    if status["wsl_available"]:
        try:
            r = run_in_wsl([
                "/home/docus/simmoon-cuda-env/bin/python3", "-c",
                "'import torch; print(torch.cuda.is_available())'"
            ], timeout=10)
            status["wsl_cuda"] = r.stdout.strip() == "True" if r.returncode == 0 else False
        except Exception:
            status["wsl_cuda"] = False

    # Gather some stats
    pixel_dirs = [d for d in SCRIPT_DIR.iterdir() if d.is_dir() and d.name.endswith("_pixel")]
    total_pngs = sum(1 for d in pixel_dirs for f in d.iterdir() if f.suffix == ".png")
    status["total_assets"] = total_pngs
    status["categories"] = len(pixel_dirs)

    json_out(True, **status)


# ── Command: generate ──────────────────────────────────────────────────────

def cmd_generate(categories: list[str], mode: str = "factory"):
    """Generate assets using the specified backend."""
    cats = categories or []
    if not cats:
        json_out(False, error="No categories specified. Use --category (e.g. --category businesses) or --all.")
    result = {
        "mode": mode,
        "categories": cats,
        "generated": 0,
        "failed": 0,
        "skipped": 0,
        "details": {},
    }

    if mode == "diffusers":
        # Use Diffusers from WSL2
        if not check_wsl():
            json_out(False, error="WSL2 no disponible para Diffusers")

        for cat in cats:
            print(f"  [{cat}] Running Diffusers generation in WSL2...", file=sys.stderr)
            r = run_in_wsl([
                f"cd ~ && /home/docus/simmoon-cuda-env/bin/python3 ~/Simmoon_arc/simmoon_diffusers.py",
                f"--category {cat}"
            ], timeout=600)

            if r.returncode == 0:
                result["generated"] += 1
                result["details"][cat] = "ok"
            else:
                result["failed"] += 1
                result["details"][cat] = r.stderr[:200] if r.stderr else "failed"

    else:
        # Use GeneratorFactory (Windows)
        try:
            from generator_factory import GeneratorFactory
            gen = GeneratorFactory()

            if not gen.is_any_backend_available():
                json_out(False, error="No generation backend available. Start ComfyUI or use --mode diffusers.")

            for cat in cats:
                try:
                    stats = gen.generate_category(category=cat)
                    result["generated"] += stats.get("generated", 0)
                    result["failed"] += stats.get("failed", 0)
                    result["skipped"] += stats.get("skipped", 0)
                    result["details"][cat] = {
                        "generated": stats.get("generated", 0),
                        "failed": stats.get("failed", 0),
                        "skipped": stats.get("skipped", 0),
                    }
                except Exception as e:
                    result["failed"] += 1
                    result["details"][cat] = str(e)[:200]
        except ImportError as e:
            json_out(False, error=f"GeneratorFactory no disponible: {e}")

    json_out(True, **result)


# ── Command: pixelate ──────────────────────────────────────────────────────

def cmd_pixelate(categories: list[str]):
    """Convert generated images to pixel art."""
    cats = categories or []
    if not cats:
        json_out(False, error="No categories specified. Use --category (e.g. --category businesses) or --all.")
    result = {"categories": cats, "pixelated": 0, "failed": 0, "details": {}}

    PIXELATOR = SCRIPT_DIR / "simmoon_pixelator.py"
    if not PIXELATOR.exists():
        json_out(False, error="simmoon_pixelator.py no encontrado")

    CAT_SETTINGS = {
        "businesses": (64, 16), "vehicles": (48, 16),
        "greenhouses": (64, 16), "solar_energy": (64, 16),
        "lunar_map": (64, 16), "buildings_misc": (64, 16),
        "lunar_sites": (128, 32), "ui_elements": (32, 8),
        "roads": (64, 16), "decorations": (64, 16),
        "characters": (64, 16), "lunar_flora": (64, 16),
        "infrastructure": (64, 16), "civic": (64, 16),
        "government": (64, 16), "housing": (64, 16),
        "industry": (64, 16), "life_support": (64, 16),
        "risk_management": (64, 16), "transport": (64, 16),
    }

    for cat in cats:
        res, colors = CAT_SETTINGS.get(cat, (64, 16))
        input_dir = SCRIPT_DIR / cat
        if not input_dir.exists():
            result["details"][cat] = "directory not found"
            result["failed"] += 1
            continue

        cmd = [
            sys.executable, str(PIXELATOR),
            "--directory", str(input_dir),
            "--game-res", str(res),
            "--colors", str(colors),
            "--outline", "1.5",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            result["pixelated"] += 1
            result["details"][cat] = "ok"
        else:
            result["failed"] += 1
            result["details"][cat] = r.stderr[:200] if r.stderr else "failed"

    json_out(True, **result)


# ── Command: gif ───────────────────────────────────────────────────────────

def cmd_gif(categories: list[str], delay: int = 150, resize: int = 0):
    """Create animated GIF previews for categories."""
    cats = categories or []
    if not cats:
        json_out(False, error="No categories specified. Use --category (e.g. --category businesses) or --all.")
    result = {"categories": cats, "gifs_generated": 0, "failed": 0, "details": {}}

    gif_script = SCRIPT_DIR / "simmoon_gifs.py"
    if not gif_script.exists():
        json_out(False, error="simmoon_gifs.py no encontrado")

    args = [sys.executable, str(gif_script), "--delay", str(delay)]
    if cats:
        args.extend(["--categories"] + cats)
    if resize > 0:
        args.extend(["--resize", str(resize)])

    r = subprocess.run(args, capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        # simmoon_gifs.py outputs human-readable text, just report success
        result["gifs_generated"] = len(cats)
        result["details"]["status"] = "ok"
        result["details"]["output"] = r.stdout.strip()[:300]
    else:
        result["failed"] = len(cats)
        result["details"]["_error"] = r.stderr.strip()[:300] if r.stderr else "failed"

    json_out(True, **result)


# ── Command: synthesis (resumen de Agatha) ───────────────────────────────

def cmd_synthesis(days: int = 7):
    """Get the latest daily synthesis from Agatha Actas via PostgreSQL.
    
    This allows Jarvis to read Agatha's hourly reports and daily summaries
    and deliver them to the user.
    """
    agatha_script = SCRIPT_DIR / "agatha_actas.py"
    if not agatha_script.exists():
        json_out(False, error="agatha_actas.py no encontrado")
    
    cmd = [sys.executable, str(agatha_script), "--synthesis", "--days", str(days), "--json"]
    # Use encoding='utf-8' + errors='replace' to handle Unicode in Windows pipes
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=30)
    
    if r.returncode != 0:
        json_out(False, error=f"agatha_actas.py failed: {r.stderr[:300] if r.stderr else 'unknown'}")
    
    stdout = r.stdout or ''
    if not stdout.strip():
        json_out(False, error="agatha_actas.py devolvió salida vacía (¿PostgreSQL no disponible?)")
    
    try:
        data = json.loads(stdout)
        if data.get("ok") and data.get("summaries"):
            # Return the most recent summary with all details
            latest = data["summaries"][0]
            result = {
                "days": days,
                "count": data["count"],
                "latest": latest,
                "all_dates": [s["date"] for s in data["summaries"]],
            }
            json_out(True, source="agatha_actas", **result)
        else:
            json_out(True, source="agatha_actas", count=0, message="No hay síntesis disponibles en PostgreSQL. Agatha aún no ha generado ninguna.")
    except (json.JSONDecodeError, KeyError) as e:
        json_out(False, error=f"Error parsing Agatha output: {e}")


# ── Command: run (pipeline completo) ───────────────────────────────────────

def cmd_run(categories: list[str], mode: str = "factory"):
    """Run the full pipeline: generate -> pixelate -> report."""
    cats = categories or []
    if not cats:
        json_out(False, error="No categories specified. Use --category (e.g. --category businesses) or --all.")
    result = {
        "mode": mode,
        "categories": cats,
        "generate_ok": False,
        "pixelate_ok": False,
        "errors": [],
    }

    print(f"[Run] Pipeline started for {len(cats)} categories", file=sys.stderr)

    for cat in cats:
        print(f"  [{cat}] Generating...", file=sys.stderr)
        gen_cmd = [sys.executable, __file__, "generate", "--category", cat, "--mode", mode]
        gr = subprocess.run(gen_cmd, capture_output=True, text=True, timeout=600)
        if gr.returncode == 0:
            result["generate_ok"] = True
            # Pixelate
            print(f"  [{cat}] Pixelating...", file=sys.stderr)
            pix_cmd = [sys.executable, __file__, "pixelate", "--category", cat]
            pr = subprocess.run(pix_cmd, capture_output=True, text=True, timeout=120)
            if pr.returncode == 0:
                result["pixelate_ok"] = True
            else:
                result["errors"].append(f"{cat}: pixelate failed")
        else:
            result["errors"].append(f"{cat}: generate failed")

    json_out(True, **result)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        cmd_help()

    command = sys.argv[1]

    # Simple arg parser
    args = sys.argv[2:]
    categories = []
    mode = "factory"
    delay = 150
    resize = 0
    days = 7

    i = 0
    while i < len(args):
        if args[i] in ("--category", "-c"):
            i += 1
            # Accept multiple values after --category until next flag
            while i < len(args) and not args[i].startswith("--"):
                categories.append(args[i])
                i += 1
            continue  # Skip bottom i += 1 (already advanced past values)
        elif args[i] == "--all":
            # Find all categories from pixel dirs
            categories = [d.name[:-6] for d in SCRIPT_DIR.iterdir()
                          if d.is_dir() and d.name.endswith("_pixel")]
        elif args[i] in ("--mode", "-m"):
            i += 1
            if i < len(args):
                mode = args[i]
        elif args[i] == "--delay":
            i += 1
            if i < len(args):
                delay = int(args[i])
        elif args[i] == "--resize":
            i += 1
            if i < len(args):
                resize = int(args[i])
        elif args[i] in ("--days", "-d"):
            i += 1
            if i < len(args):
                days = int(args[i])
        elif args[i] == "--json":
            pass  # Always JSON
        i += 1


    # Route commands
    if command == "help":
        cmd_help()
    elif command == "status":
        cmd_status()
    elif command == "generate":
        cmd_generate(categories, mode)
    elif command == "pixelate":
        cmd_pixelate(categories)
    elif command == "gif":
        cmd_gif(categories, delay, resize)
    elif command == "synthesis":
        cmd_synthesis(days)
    elif command == "run":
        cmd_run(categories, mode)
    else:
        json_out(False, error=f"Comando desconocido: {command}. Usa 'help' para ayuda.")


if __name__ == "__main__":
    main()
