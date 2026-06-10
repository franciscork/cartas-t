#!/usr/bin/env python3
"""
SIMMOON — Leonardo.ai API Test (via leonardo_client REST client)

Genera imágenes usando la API cloud de Leonardo.ai.
No requiere SDK — usa el cliente REST puro (leonardo_client.py).

Requisito:
    export LEONARDO_API_KEY="tu_api_key"

Uso:
    python test_leonardo.py --prompt "lunar colony isometric pixel art"
    python test_leonardo.py --category businesses --prompts-file simmoon_prompts.json
    python test_leonardo.py --health  # solo verificar conectividad
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from leonardo_client import LeonardoClient


def get_client(api_key=None):
    """Inicializa el cliente REST de Leonardo.ai."""
    if api_key is None:
        api_key = os.environ.get("LEONARDO_API_KEY", "")
    if not api_key:
        print("[ERROR] LEONARDO_API_KEY no encontrada.")
        print("  Exportala: export LEONARDO_API_KEY=\"tu_key\"")
        print("  O crea una en: https://app.leonardo.ai → API Access")
        sys.exit(1)
    return LeonardoClient(api_key=api_key)


def generate_single(client, prompt, negative_prompt="", width=512, height=512,
                    model_id=None, num_images=1, max_wait=300):
    """Genera una imagen y espera a que termine (polling)."""
    print(f"  Prompt: {prompt[:80]}...")
    print(f"  Size: {width}x{height}")

    gen_id, urls = client.generate(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        model_id=model_id or None,
        num_images=num_images,
        max_wait=max_wait,
    )
    return gen_id, urls


def download_image(url, output_path):
    """Descarga una imagen desde una URL usando urllib."""
    print(f"  Downloading: {url[:60]}...")
    req = urllib.request.Request(url, headers={"User-Agent": "SIMMON/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(data)
    print(f"  Saved: {output_path}")
    return output_path


def generate_from_prompts(client, prompts_file, category, output_dir=None,
                          model_id=None, preset_style=None):
    """Genera todas las imágenes de una categoría desde simmoon_prompts.json."""
    with open(prompts_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = data.get("categories", {})
    if category not in categories:
        print(f"[ERROR] Categoría '{category}' no encontrada.")
        print(f"  Disponibles: {list(categories.keys())}")
        sys.exit(1)

    cat_data = categories[category]
    output = output_dir or os.path.join(SCRIPT_DIR, f"leonardo_{category}")
    os.makedirs(output, exist_ok=True)

    prompts = cat_data.get("prompts", [])
    negative_base = data.get("negative_prompt_base", "")

    print(f"\nCategoría: {category} ({len(prompts)} items)")
    print(f"Output: {output}")
    print("=" * 50)

    ok = 0
    fail = 0
    for p in prompts:
        name = p["name"]
        safe = name.lower().replace(" ", "_").replace("-", "_")
        out_path = os.path.join(output, f"{p['id']}_{safe}.png")

        # Skip if already exists
        if os.path.exists(out_path):
            print(f"  [SKIP] {p['id']}_{safe}.png (already exists)")
            ok += 1
            continue

        try:
            neg = p.get("negative_prompt", "") or negative_base
            output_path = client.generate_and_save(
                prompt=p.get("prompt", ""),
                output_path=out_path,
                negative_prompt=neg,
                model_id=model_id or None,
                preset_style=preset_style or None,
                max_wait=180,
            )
            ok += 1
            print(f"  ✅ {p['id']}_{safe}.png")
        except Exception as e:
            print(f"  [FAIL] {p['id']}: {e}")
            fail += 1

        # Rate limiting
        time.sleep(1.5)

    print(f"\n{'='*50}")
    print(f"Completado: {ok} ok, {fail} fallos")


def check_health(client):
    """Verifica conectividad con Leonardo.ai."""
    print("Verificando conectividad con Leonardo.ai...")
    try:
        # Quick test: try to fetch user info
        info = client._get("me")
        if info:
            user = info.get("user_details", [{}])[0] if isinstance(info.get("user_details"), list) else {}
            username = user.get("username", "desconocido")
            print(f"  ✅ Conectado como: {username}")
            print(f"  API key válida.")
        else:
            print("  ⚠️  Conectado pero no se pudo obtener info de usuario.")
        return True
    except Exception as e:
        print(f"  ❌ Error de conexión: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON — Leonardo.ai API Test (REST client)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python test_leonardo.py --prompt "lunar mining office isometric pixel art"
  python test_leonardo.py --category businesses
  python test_leonardo.py --category vehicles --output-dir ./leo_vehicles
  python test_leonardo.py --health
        """,
    )
    parser.add_argument("--prompt", type=str, help="Prompt único para prueba rápida")
    parser.add_argument("--negative", type=str, default="", help="Negative prompt")
    parser.add_argument("--category", type=str, help="Categoría de simmoon_prompts.json")
    parser.add_argument("--prompts-file", type=str,
                        default=str(SCRIPT_DIR / "simmoon_prompts.json"),
                        help="Ruta al archivo de prompts")
    parser.add_argument("--output-dir", type=str, help="Directorio de salida")
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--model-id", type=str, default=None,
                        help="Model ID de Leonardo.ai (opcional)")
    parser.add_argument("--preset-style", type=str, default="DYNAMIC",
                        help="Preset style (default: DYNAMIC)")
    parser.add_argument("--num-images", type=int, default=1)
    parser.add_argument("--api-key", type=str, default=None,
                        help="API key (o usar LEONARDO_API_KEY env var)")
    parser.add_argument("--health", action="store_true",
                        help="Solo verificar conectividad con la API")

    args = parser.parse_args()

    client = get_client(args.api_key)

    if args.health:
        check_health(client)
        return

    if args.category:
        generate_from_prompts(
            client, args.prompts_file, args.category,
            output_dir=args.output_dir,
            model_id=args.model_id,
            preset_style=args.preset_style,
        )
    elif args.prompt:
        gen_id, urls = generate_single(
            client,
            prompt=args.prompt,
            negative_prompt=args.negative,
            width=args.width,
            height=args.height,
            model_id=args.model_id,
            num_images=args.num_images,
        )
        if urls:
            out_dir = args.output_dir or os.path.join(SCRIPT_DIR, "leonardo_test")
            for i, url in enumerate(urls):
                suffix = f"_{i}" if len(urls) > 1 else ""
                download_image(url, os.path.join(out_dir, f"test{suffix}.png"))
        else:
            print("[WARN] No se generaron imágenes.")
    else:
        parser.print_help()
        print("\n[INFO] Especifica --prompt para una prueba rápida")
        print("       o --category para generar una categoría completa.")
        print("       o --health para verificar conectividad.")


if __name__ == "__main__":
    main()
