#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 SIMMOON Quality Inspector — Control de Calidad de FactoryGames

Inspecciona los assets generados, detecta anomalías, verifica integridad
y se integra con el sistema de votación para mantener la calidad.

Uso:
    python simmoon_quality_inspector.py                   # Inspección completa
    python simmoon_quality_inspector.py --category businesses vehicles
    python simmoon_quality_inspector.py --summary          # Solo resumen
    python simmoon_quality_inspector.py --bad-only         # Solo assets con fallos
    python simmoon_quality_inspector.py --json             # Salida JSON
    python simmoon_quality_inspector.py --daemon           # Loop continuo
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Quality thresholds ──────────────────────────────────────────────────
MIN_FILE_SIZE_BYTES = 1024        # 1KB mínimo para un asset válido
SUSPICIOUS_FILE_SIZE = 512         # Por debajo de esto = corrupto
MIN_PIXEL_SIZE = 16                # Mínimo 16px para pixel art válido
MAX_PIXEL_SIZE = 256               # Máximo esperado

# Categorías de assets con resoluciones esperadas
CATEGORY_SPECS = {
    "businesses":      {"res": (512, 512), "pixel_res": (64, 64), "count": 12},
    "vehicles":        {"res": (512, 512), "pixel_res": (48, 48), "count": 10},
    "greenhouses":     {"res": (512, 512), "pixel_res": (64, 64), "count": 7},
    "solar_energy":    {"res": (512, 512), "pixel_res": (64, 64), "count": 8},
    "lunar_map":       {"res": (512, 512), "pixel_res": (64, 64), "count": 1},
    "buildings_misc":  {"res": (512, 512), "pixel_res": (64, 64), "count": 12},
    "lunar_sites":     {"res": (512, 512), "pixel_res": (128, 128), "count": 12},
    "ui_elements":     {"res": (256, 256), "pixel_res": (32, 32), "count": 9},
    "roads":           {"res": (512, 512), "pixel_res": (64, 64), "count": 8},
    "decorations":     {"res": (512, 512), "pixel_res": (64, 64), "count": 8},
    "characters":      {"res": (512, 512), "pixel_res": (64, 64), "count": 6},
    "lunar_flora":     {"res": (512, 512), "pixel_res": (64, 64), "count": 6},
    "infrastructure":  {"res": (512, 512), "pixel_res": (64, 64), "count": 6},
    "anomalies":       {"res": (512, 512), "pixel_res": (64, 64), "count": 5},
    "robots":          {"res": (512, 512), "pixel_res": (64, 64), "count": 5},
}

ASSET_CATEGORIES = list(CATEGORY_SPECS.keys())
PIXEL_SUFFIX = "_pixel"


# ── Vote System Integration ────────────────────────────────────────────
def load_votes() -> dict:
    """Load votes from votes.json for quality cross-reference.
    
    Returns dict mapping asset_id -> vote_value
    """
    votes_path = SCRIPT_DIR / "votes.json"
    if not votes_path.exists():
        return {}
    
    try:
        with open(votes_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        votes = {}
        for entry in data:
            aid = entry.get("asset_id", "")
            val = entry.get("vote_value", 0)
            votes[aid] = val
        return votes
    except Exception:
        return {}


# ── Asset Scanner ──────────────────────────────────────────────────────
def scan_assets(categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Scan all category directories and return asset metadata.
    
    Returns list of asset dicts with: path, name, category, size_bytes,
    has_pixel_version, pixel_path, etc.
    """
    cats = categories or ASSET_CATEGORIES
    assets = []
    
    for cat in cats:
        cat_dir = SCRIPT_DIR / cat
        if not cat_dir.is_dir():
            continue
        
        # Pixel art directory
        pixel_dir = SCRIPT_DIR / f"{cat}{PIXEL_SUFFIX}"
        has_pixel_dir = pixel_dir.is_dir()
        
        for png_file in sorted(cat_dir.glob("*.png")):
            try:
                stat = png_file.stat()
                pixel_version = None
                
                if has_pixel_dir:
                    pixel_name = png_file.stem + "_pixel.png"
                    pixel_path = pixel_dir / pixel_name
                    if pixel_path.exists():
                        pixel_version = str(pixel_path)
                
                # Extract asset_id from filename (e.g., "biz_01" from "dreamshaper_v8_biz_01_lunar_mining_office.png")
                # or use the full stem
                
                assets.append({
                    "path": str(png_file),
                    "name": png_file.stem,
                    "category": cat,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "has_pixel_version": pixel_version is not None,
                    "pixel_path": pixel_version,
                })
            except Exception:
                continue
    
    return assets


# ── Quality Checks ─────────────────────────────────────────────────────
def check_file_size(asset: dict) -> Dict[str, Any]:
    """Check if file size is reasonable."""
    size = asset["size_bytes"]
    
    if size < SUSPICIOUS_FILE_SIZE:
        return {
            "status": "fail",
            "severity": "critical",
            "message": f"Archivo corrupto o vacío: {size} bytes (mínimo {MIN_FILE_SIZE_BYTES})",
            "score": 0,
        }
    elif size < MIN_FILE_SIZE_BYTES:
        return {
            "status": "warn",
            "severity": "high",
            "message": f"Archivo sospechosamente pequeño: {size} bytes",
            "score": 2,
        }
    elif size < 10000:  # 10KB
        return {
            "status": "warn",
            "severity": "low",
            "message": f"Tamaño reducido: {size} bytes",
            "score": 7,
        }
    else:
        return {
            "status": "pass",
            "severity": "ok",
            "message": f"OK: {size} bytes",
            "score": 10,
        }


def check_dimensions(asset: dict) -> Dict[str, Any]:
    """Check image dimensions if possible (via PIL)."""
    try:
        from PIL import Image
        img = Image.open(asset["path"])
        w, h = img.size
        
        spec = CATEGORY_SPECS.get(asset["category"], {})
        expected = spec.get("res", (512, 512))
        
        if (w, h) == expected:
            return {
                "status": "pass",
                "severity": "ok",
                "message": f"Dimensión correcta: {w}x{h}",
                "score": 10,
                "dimensions": (w, h),
            }
        elif w < 64 or h < 64:
            return {
                "status": "fail",
                "severity": "high",
                "message": f"Dimensión muy pequeña: {w}x{h} (esperada: {expected[0]}x{expected[1]})",
                "score": 2,
                "dimensions": (w, h),
            }
        else:
            return {
                "status": "warn",
                "severity": "low",
                "message": f"Dimensión inesperada: {w}x{h} (esperada: {expected[0]}x{expected[1]})",
                "score": 6,
                "dimensions": (w, h),
            }
    except ImportError:
        return {"status": "skip", "severity": "info", "message": "PIL no disponible", "score": -1}
    except Exception:
        return {"status": "fail", "severity": "critical", "message": "No se pudo leer la imagen", "score": 0}


def check_pixel_version(asset: dict) -> Dict[str, Any]:
    """Check if pixel art version exists and validate it."""
    if not asset["has_pixel_version"]:
        return {
            "status": "warn",
            "severity": "medium",
            "message": "No tiene versión pixel-art",
            "score": 4,
        }
    
    pixel_path = Path(asset["pixel_path"])
    if not pixel_path.exists():
        return {
            "status": "fail",
            "severity": "high",
            "message": "Referencia a pixel-art que no existe",
            "score": 1,
        }
    
    try:
        px_size = pixel_path.stat().st_size
        if px_size < 256:  # Even a tiny pixel art should be >256 bytes
            return {
                "status": "fail",
                "severity": "high",
                "message": f"Pixel-art corrupto: {px_size} bytes",
                "score": 2,
            }
        
        # Check pixel-art dimensions if PIL available
        try:
            from PIL import Image
            px_img = Image.open(pixel_path)
            pw, ph = px_img.size
            
            spec = CATEGORY_SPECS.get(asset["category"], {})
            expected_px = spec.get("pixel_res", (64, 64))
            
            if (pw, ph) != expected_px:
                return {
                    "status": "warn",
                    "severity": "low",
                    "message": f"Pixel-art {pw}x{ph} (esperado: {expected_px[0]}x{expected_px[1]})",
                    "score": 6,
                }
        except ImportError:
            pass
        
        return {
            "status": "pass",
            "severity": "ok",
            "message": "Pixel-art OK",
            "score": 10,
        }
    except Exception:
        return {
            "status": "fail",
            "severity": "high",
            "message": "Error al leer pixel-art",
            "score": 2,
        }


def check_vote_score(asset: dict, votes: dict) -> Dict[str, Any]:
    """Cross-reference with voting system if available."""
    # Extract asset base ID from filename
    # e.g., "biz_01" from "dreamshaper_v8_biz_01_lunar_mining_office"
    # or "biz_01" from "biz_01_lunar_mining_office"
    stem = asset["name"]
    
    # Try to find the asset ID pattern (like biz_01, veh_05, etc.)
    asset_id = None
    for prefix in ["biz_", "veh_", "gh_", "sol_", "site_", "misc_", "road_",
                     "dec_", "char_", "flora_", "infra_", "ui_", "oficio_",
                     "civ_", "tra_", "rsk_", "sol_", "anom_", "rob_"]:
        if prefix in stem:
            # Extract the ID part: e.g., "biz_01" from "biz_01_lunar_mining_office"
            parts = stem.split("_")
            for i, p in enumerate(parts):
                if p == prefix.rstrip("_") and i + 1 < len(parts) and parts[i+1].isdigit():
                    asset_id = f"{p}_{parts[i+1]}"
                    break
            if asset_id:
                break
    
    if not asset_id or asset_id not in votes:
        return {
            "status": "skip",
            "severity": "info",
            "message": "Sin voto registrado",
            "score": -1,
        }
    
    vote = votes[asset_id]
    if vote >= 4:
        return {
            "status": "pass",
            "severity": "ok",
            "message": f"Voto: {vote}⭐",
            "score": 10,
        }
    elif vote >= 3:
        return {
            "status": "warn",
            "severity": "low",
            "message": f"Voto medio: {vote}⭐",
            "score": 6,
        }
    else:
        return {
            "status": "warn",
            "severity": "medium",
            "message": f"Voto bajo: {vote}⭐",
            "score": 3,
        }


def check_duplicates(asset: dict, all_assets: List[dict]) -> Dict[str, Any]:
    """Check for exact duplicate files (same name pattern, different prefix)."""
    stem = asset["name"]
    
    # Find similar names (same base name, different prefix like dreamshaper_v8_, counterfeit_v30_, etc.)
    base_name = stem.split("_", 2)[-1] if "_" in stem else stem  # Get everything after prefix
    
    similar = [a for a in all_assets if a["name"].endswith(base_name) and a["path"] != asset["path"]]
    
    if similar:
        return {
            "status": "info",
            "severity": "info",
            "message": f"Tiene {len(similar)} variante(s) (mismo asset, distinto modelo)",
            "score": 8,
            "variants": len(similar),
        }
    
    return {"status": "pass", "severity": "ok", "message": "Asset único", "score": 10, "variants": 0}


# ── Full Inspection ────────────────────────────────────────────────────
def inspect_asset(asset: dict, all_assets: List[dict], votes: dict) -> Dict[str, Any]:
    """Run all quality checks on a single asset."""
    checks = {
        "file_size": check_file_size(asset),
        "dimensions": check_dimensions(asset),
        "pixel_version": check_pixel_version(asset),
        "vote_score": check_vote_score(asset, votes),
        "duplicates": check_duplicates(asset, all_assets),
    }
    
    # Calculate overall score (0-100)
    scores = [c["score"] for c in checks.values() if c["score"] >= 0]
    overall = round(sum(scores) / len(scores) * 10, 1) if scores else 50.0
    
    # Determine status
    failures = [c for c in checks.values() if c["status"] == "fail"]
    warnings = [c for c in checks.values() if c["status"] == "warn"]
    
    if failures:
        status = "fail"
        grade = "❌"
    elif warnings:
        status = "warn"
        grade = "⚠️"
    else:
        status = "pass"
        grade = "✅"
    
    return {
        "asset": asset,
        "status": status,
        "grade": grade,
        "overall_score": overall,
        "checks": checks,
        "failures": [c["message"] for c in failures],
        "warnings": [c["message"] for c in warnings],
    }


def inspect_all(categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """Inspect all assets in the given categories."""
    votes = load_votes()
    all_assets = scan_assets(categories)
    
    results = []
    for asset in all_assets:
        result = inspect_asset(asset, all_assets, votes)
        results.append(result)
    
    # Calculate summary stats
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    warned = sum(1 for r in results if r["status"] == "warn")
    failed = sum(1 for r in results if r["status"] == "fail")
    
    avg_score = round(sum(r["overall_score"] for r in results) / total, 1) if total > 0 else 0
    
    # By category
    by_category = {}
    for r in results:
        cat = r["asset"]["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0, "warned": 0, "failed": 0, "score": 0}
        by_category[cat]["total"] += 1
        status_key = {"pass": "passed", "warn": "warned", "fail": "failed"}.get(r["status"], "passed")
        by_category[cat][status_key] += 1
        by_category[cat]["score"] += r["overall_score"]
    
    for cat, stats in by_category.items():
        stats["avg_score"] = round(stats["score"] / stats["total"], 1) if stats["total"] > 0 else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "avg_score": avg_score,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        },
        "by_category": by_category,
        "assets": results,
    }


# ── Report Formatting ──────────────────────────────────────────────────
def format_report(inspection: dict, bad_only: bool = False) -> str:
    """Format inspection results as a readable report."""
    summary = inspection["summary"]
    
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  🎯 FACTORYGAMES — INFORME DE CALIDAD")
    lines.append(f"  {inspection['timestamp']}")
    lines.append(f"{'='*60}")
    
    lines.append(f"\n📊 *Resumen:*")
    lines.append(f"  Total: {summary['total']} assets")
    lines.append(f"  ✅ Pass: {summary['passed']}")
    lines.append(f"  ⚠️  Warn: {summary['warned']}")
    lines.append(f"  ❌ Fail: {summary['failed']}")
    lines.append(f"  📈 Score: {summary['avg_score']}/100")
    lines.append(f"  📊 Pass rate: {summary['pass_rate']}%")
    
    lines.append(f"\n📁 *Por categoría:*")
    for cat, stats in sorted(inspection["by_category"].items()):
        grade = "✅" if stats["failed"] == 0 else "⚠️" if stats["failed"] < 3 else "❌"
        lines.append(f"  {grade} {cat}: {stats['total']} assets | "
                     f"{stats['passed']}✅/{stats['warned']}⚠️/{stats['failed']}❌ | "
                     f"Score: {stats['avg_score']}/100")
    
    if bad_only:
        bad = [r for r in inspection["assets"] if r["status"] in ("fail", "warn")]
        lines.append(f"\n⚠️ *Assets con problemas ({len(bad)}):*")
        for r in bad:
            lines.append(f"\n  {r['grade']} {r['asset']['name']} [{r['asset']['category']}]")
            lines.append(f"     Score: {r['overall_score']}/100")
            for msg in r["failures"] + r["warnings"][:2]:
                lines.append(f"     • {msg}")
    else:
        lines.append(f"\n{'─'*60}")
        lines.append(f"*Detalle por asset:*")
        lines.append(f"{'─'*60}")
        
        for r in inspection["assets"]:
            lines.append(f"\n  {r['grade']} {r['asset']['name']}.png ({r['asset']['category']})")
            lines.append(f"     Score: {r['overall_score']}/100 | "
                         f"Size: {r['asset']['size_bytes']}b | "
                         f"Pixel: {'✅' if r['asset']['has_pixel_version'] else '❌'}")
            for c_name, c_result in r["checks"].items():
                icon = "✅" if c_result["status"] == "pass" else "⚠️" if c_result["status"] == "warn" else "❌" if c_result["status"] == "fail" else "ℹ️"
                lines.append(f"     {icon} {c_name}: {c_result['message']}")
    
    lines.append(f"\n{'='*60}")
    lines.append(f"  🎯 Quality Inspector — {summary['pass_rate']}% pass rate")
    lines.append(f"{'='*60}")
    
    return "\n".join(lines)


def format_json_report(inspection: dict) -> str:
    """Format inspection as JSON for agent consumption."""
    summary = inspection["summary"]
    return json.dumps({
        "ok": True,
        "source": "Quality Inspector",
        "timestamp": inspection["timestamp"],
        "total_assets": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "avg_score": summary["avg_score"],
        "pass_rate": summary["pass_rate"],
        "categories": {
            cat: {
                "total": s["total"],
                "passed": s["passed"],
                "failed": s["failed"],
                "avg_score": s["avg_score"],
            }
            for cat, s in inspection["by_category"].items()
        },
        "bad_assets": [
            {
                "name": r["asset"]["name"],
                "category": r["asset"]["category"],
                "score": r["overall_score"],
                "issues": r["failures"] + r["warnings"][:2],
            }
            for r in inspection["assets"]
            if r["status"] in ("fail", "warn")
        ],
    }, indent=2, ensure_ascii=False)


# ─── Daemon Mode ───────────────────────────────────────────────────────
def daemon_loop(interval: int = 3600):
    """Run inspections periodically."""
    print(f"\n  🎯 Quality Inspector — Modo Demonio")
    print(f"  ⏱️  Inspección cada {interval // 60} minutos")
    print(f"  {'='*50}")
    
    while True:
        print(f"\n  🔍 Inspeccionando assets...")
        inspection = inspect_all()
        s = inspection["summary"]
        print(f"     {s['total']} assets | Score: {s['avg_score']}/100 | "
              f"{s['passed']}✅ {s['warned']}⚠️ {s['failed']}❌")
        
        if s["failed"] > 0:
            print(f"     ❌ {s['failed']} asset(s) con fallos críticos:")
            for r in inspection["assets"]:
                if r["status"] == "fail":
                    for msg in r["failures"]:
                        print(f"        • {r['asset']['name']}: {msg}")
        
        next_time = time.time() + interval
        next_str = datetime.fromtimestamp(next_time).strftime("%H:%M:%S")
        print(f"  ⏳ Próxima inspección a las {next_str}...")
        
        try:
            while time.time() < next_time:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n  🛑 Inspector detenido.\n")
            break
    
    return inspection


# ── CLI ─────────────────────────────────────────────────────────────────
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🎯 SIMMOON Quality Inspector — Control de Calidad de FactoryGames"
    )
    parser.add_argument("--category", "-c", nargs="+", default=None,
                        help="Categorías a inspeccionar (default: todas)")
    parser.add_argument("--summary", action="store_true",
                        help="Solo resumen, sin detalle por asset")
    parser.add_argument("--bad-only", action="store_true",
                        help="Solo mostrar assets con problemas")
    parser.add_argument("--json", action="store_true",
                        help="Salida en JSON")
    parser.add_argument("--daemon", action="store_true",
                        help="Modo demonio (loop continuo)")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Intervalo en segundos para modo demonio (default: 3600)")
    parser.add_argument("--list-categories", action="store_true",
                        help="Listar categorías disponibles")
    
    args = parser.parse_args()
    
    if args.list_categories:
        print("\n  📁 Categorías de assets:")
        for cat, spec in CATEGORY_SPECS.items():
            cat_dir = SCRIPT_DIR / cat
            count = len(list(cat_dir.glob("*.png"))) if cat_dir.is_dir() else 0
            pixel_dir = SCRIPT_DIR / f"{cat}{PIXEL_SUFFIX}"
            pixel_count = len(list(pixel_dir.glob("*.png"))) if pixel_dir.is_dir() else 0
            print(f"  {cat:20s} {count:4d} assets | pixel: {pixel_count:4d} | "
                  f"res: {spec['res'][0]}x{spec['res'][1]} → {spec['pixel_res'][0]}x{spec['pixel_res'][1]}")
        print()
        return
    
    if args.daemon:
        daemon_loop(args.interval)
        return
    
    # Run inspection
    inspection = inspect_all(args.category)
    
    if args.json:
        print(format_json_report(inspection))
    elif args.summary:
        s = inspection["summary"]
        print(f"\n  🎯 Quality Inspector — Resumen")
        print(f"  {'='*40}")
        print(f"  Total: {s['total']} assets | Score: {s['avg_score']}/100")
        print(f"  ✅ Pass: {s['passed']}  ⚠️ Warn: {s['warned']}  ❌ Fail: {s['failed']}")
        print(f"  📊 Pass rate: {s['pass_rate']}%")
        print(f"\n  📁 Por categoría:")
        for cat, stats in sorted(inspection["by_category"].items()):
            print(f"  {cat:20s} {stats['total']:4d} assets | "
                  f"{stats['passed']}✅/{stats['warned']}⚠️/{stats['failed']}❌ | "
                  f"Score: {stats['avg_score']}/100")
        print()
    else:
        print(format_report(inspection, bad_only=args.bad_only))


if __name__ == "__main__":
    main()
