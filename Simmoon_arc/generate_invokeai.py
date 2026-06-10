#!/usr/bin/env python3
"""
SIMMOON Asset Generator - InvokeAI Backend
Generates images from simmoon_prompts.json via InvokeAI REST API.

Usage:
    source ~/invokeai-env/bin/activate
    python generate_invokeai.py
    python generate_invokeai.py --model dreamshaper_8 --categories businesses
    python generate_invokeai.py --model counterfeit_v30 --steps 28 --cfg 9

Requirements:
    - InvokeAI running on http://127.0.0.1:9090
    - invokeai-env virtualenv activated
    - Models imported via InvokeAI Model Manager
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import uuid
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_PATH = SCRIPT_DIR / "simmoon_prompts.json"
INVOKEAI_URL = "http://127.0.0.1:9090"

# ─── Defaults ────────────────────────────────────────────────────────────
DEFAULT_MODEL = "v1-5-pruned-emaonly"
STEPS = 28
CFG = 9
WIDTH = 512
HEIGHT = 512
SEED = -1

# Model key mapping (UUIDs from InvokeAI database)
MODEL_KEYS = {
    "v1-5-pruned-emaonly": ("b75a0357-280d-4646-9ebe-ba43a6e734be", "sd-1"),
    "dreamshaper_8": ("89fedde5-3626-49d7-b0b0-121dbe51dba0", "sd-1"),
    "counterfeit_v30": ("873417e2-45b3-4174-a0c9-d305bfb36f5d", "sd-1"),
    "pixelArtSpriteDiffusion_safetensors": ("916dd15e-8b0c-48c4-ae6e-2e8989056412", "sd-1"),
    "revAnimated_v122": ("629dcc72-f2bd-4d1b-8166-5000e8ae8a00", "sd-1"),
}


def build_txt2img_graph(prompt, negative_prompt, model_name, seed, width, height, steps, cfg):
    """
    Build an InvokeAI txt2img graph as a dict.
    
    InvokeAI v6 uses a graph of "invocations" (nodes) connected by "edges".
    The standard txt2img pipeline requires:
      1. MainModelLoader - loads the checkpoint
      2. Compel (positive) - encodes the prompt
      3. Compel (negative) - encodes the negative prompt  
      4. Noise - generates random noise latents
      5. DenoiseLatents - runs the sampler
      6. LatentsToImage - decodes latents to image
    """
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)

    nodes = {}

    # Get model key info
    model_key, model_base = MODEL_KEYS.get(model_name, (model_name, "sd-1"))

    # Node 1: MainModelLoader - load the model
    nodes["1"] = {
        "type": "main_model_loader",
        "id": "1",
        "is_intermediate": False,
        "model": {"key": model_key, "hash": "", "name": model_name, "base": model_base, "type": "main"},
    }

    # Node 2: Compel (positive prompt)
    nodes["2"] = {
        "type": "compel",
        "id": "2",
        "is_intermediate": False,
        "prompt": prompt,
    }

    # Node 3: Compel (negative prompt)
    nodes["3"] = {
        "type": "compel",
        "id": "3",
        "is_intermediate": False,
        "prompt": negative_prompt,
    }

    # Node 4: Noise
    nodes["4"] = {
        "type": "noise",
        "id": "4",
        "is_intermediate": False,
        "seed": seed,
        "width": width,
        "height": height,
    }

    # Node 5: DenoiseLatents
    nodes["5"] = {
        "type": "denoise_latents",
        "id": "5",
        "is_intermediate": False,
        "steps": steps,
        "cfg_scale": cfg,
        "scheduler": "euler",
        "denoising_start": 0.0,
        "denoising_end": 1.0,
    }

    # Node 6: LatentsToImage
    nodes["6"] = {
        "type": "l2i",
        "id": "6",
        "is_intermediate": False,
    }

    # Edges connecting the nodes
    edges = [
        # Model loader -> Compel nodes (model key for conditioning)
        {"source": {"node_id": "1", "field": "unet"}, "destination": {"node_id": "5", "field": "unet"}},
        {"source": {"node_id": "1", "field": "clip"}, "destination": {"node_id": "2", "field": "clip"}},
        {"source": {"node_id": "1", "field": "clip"}, "destination": {"node_id": "3", "field": "clip"}},
        {"source": {"node_id": "1", "field": "vae"}, "destination": {"node_id": "6", "field": "vae"}},
        # Compel -> DenoiseLatents
        {"source": {"node_id": "2", "field": "conditioning"}, "destination": {"node_id": "5", "field": "positive_conditioning"}},
        {"source": {"node_id": "3", "field": "conditioning"}, "destination": {"node_id": "5", "field": "negative_conditioning"}},
        # Noise -> DenoiseLatents
        {"source": {"node_id": "4", "field": "noise"}, "destination": {"node_id": "5", "field": "noise"}},
        # DenoiseLatents -> LatentsToImage
        {"source": {"node_id": "5", "field": "latents"}, "destination": {"node_id": "6", "field": "latents"}},
    ]

    return {
        "graph": {"nodes": nodes, "edges": edges},
        "runs": 1,
    }


def enqueue_batch(batch_payload):
    """Submit a batch to InvokeAI queue and return the batch_id."""
    url = f"{INVOKEAI_URL}/api/v1/queue/default/enqueue_batch"
    data = json.dumps({"batch": batch_payload}).encode("utf-8")

    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("batch_id") or result.get("queue_id")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  [ERROR] HTTP {e.code}: {error_body[:500]}")
        return None


def wait_for_batch(batch_id, timeout=300):
    """Poll for batch completion. Returns list of output image paths."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            url = f"{INVOKEAI_URL}/api/v1/queue/default/status"
            with urllib.request.urlopen(url, timeout=10) as resp:
                status = json.loads(resp.read().decode())
        except Exception:
            time.sleep(2)
            continue

        # Check if queue is idle (batch completed)
        queue_status = status.get("queue", {})
        pending = queue_status.get("pending", 0)
        in_progress = queue_status.get("in_progress", 0)

        if pending == 0 and in_progress == 0:
            print(f"  Queue idle after {time.time() - start:.0f}s")
            break

        time.sleep(2)

    # Retrieve outputs from the images directory
    output_dir = Path.home() / "invokeai" / "outputs" / "images"
    if output_dir.exists():
        images = sorted(output_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        return images[:1]  # Return most recent image
    return []


def generate_image(prompt_data, output_dir, output_prefix, model_name):
    """Generate one image via InvokeAI and save to output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    prompt_text = prompt_data["prompt"]
    negative_text = prompt_data.get("negative_prompt", "")
    seed_val = random.randint(0, 2**32 - 1) if SEED == -1 else SEED

    print(f"  Prompt: {prompt_text[:80]}...")
    print(f"  Model: {model_name}, Seed: {seed_val}")

    batch = build_txt2img_graph(
        prompt=prompt_text,
        negative_prompt=negative_text,
        model_name=model_name,
        seed=seed_val,
        width=WIDTH,
        height=HEIGHT,
        steps=STEPS,
        cfg=CFG,
    )

    batch_id = enqueue_batch(batch)
    if not batch_id:
        print(f"  [FAIL] Could not enqueue batch for {output_prefix}")
        return None

    print(f"  Batch enqueued: {batch_id}")

    outputs = wait_for_batch(batch_id)
    if outputs:
        # Copy the generated image to our output directory
        src = outputs[0]
        dst = Path(output_dir) / f"{output_prefix}.png"
        with open(src, "rb") as f_src:
            with open(dst, "wb") as f_dst:
                f_dst.write(f_src.read())
        print(f"  [OK] Saved: {dst}")
        return str(dst)
    else:
        print(f"  [FAIL] No output for {output_prefix}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON Asset Generator - InvokeAI Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_invokeai.py
  python generate_invokeai.py --model dreamshaper_8 --categories businesses
  python generate_invokeai.py --model counterfeit_v30 --categories all
        """,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Model name in InvokeAI (default: {DEFAULT_MODEL})")
    parser.add_argument("--categories", default=None,
                        help="Comma-separated categories (default: all)")
    parser.add_argument("--steps", type=int, default=STEPS)
    parser.add_argument("--cfg", type=float, default=CFG)
    parser.add_argument("--width", type=int, default=WIDTH)
    parser.add_argument("--height", type=int, default=HEIGHT)
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: Simmoon_arc/invokeai_output/)")
    parser.add_argument("--prefix", default="invokeai",
                        help="Filename prefix (default: invokeai)")
    args = parser.parse_args()

    # Load prompts
    if not PROMPTS_PATH.exists():
        print(f"[ERROR] Prompts file not found: {PROMPTS_PATH}")
        sys.exit(1)

    with open(PROMPTS_PATH) as f:
        data = json.load(f)

    categories = data["categories"]

    # Filter categories
    if args.categories and args.categories != "all":
        requested = [c.strip() for c in args.categories.split(",")]
        categories = {k: v for k, v in categories.items() if k in requested}

    # Output dir
    if args.output_dir:
        output_base = Path(args.output_dir)
    else:
        output_base = SCRIPT_DIR / "invokeai_output"

    negative_prompt_base = data.get("negative_prompt_base", "")

    total = sum(len(cat["prompts"]) for cat in categories.values())
    print(f"SIMMOON InvokeAI Generator")
    print(f"Model: {args.model}")
    print(f"Categories: {len(categories)} | Total prompts: {total}")
    print(f"Output: {output_base}")
    print("=" * 50)

    generated = 0
    failed = 0

    for cat_key, cat_data in categories.items():
        output_dir = output_base / cat_key
        print(f"\n[CAT] {cat_key} ({len(cat_data['prompts'])} items)")

        for prompt_item in cat_data["prompts"]:
            item_id = prompt_item["id"]
            name = prompt_item["name"]
            safe_name = name.lower().replace(" ", "_").replace("-", "_")
            output_prefix = f"{args.prefix}_{item_id}_{safe_name}"

            neg = prompt_item.get("negative_prompt", "") or negative_prompt_base
            prompt_data = dict(prompt_item)
            prompt_data["negative_prompt"] = neg

            try:
                result = generate_image(prompt_data, output_dir, output_prefix, args.model)
                if result:
                    generated += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  [FAIL] {output_prefix}: {e}")
                failed += 1

    print("\n" + "=" * 50)
    print(f"Generation complete: {generated} generated, {failed} failed")


if __name__ == "__main__":
    main()
