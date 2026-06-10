#!/usr/bin/env python3
"""
SIMMOON Asset Generator - ComfyUI Backend
Reads prompts from simmoon_prompts.json and generates images via ComfyUI API.
Supports configurable checkpoints, LoRAs, and per-category overrides.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import uuid
import random

# ---- Defaults (overridable via config.json) ----
DEFAULT_CHECKPOINT = "dreamshaper_8.safetensors"
DEFAULT_LORAS = []
SEED = -1  # -1 = random
STEPS = 28
CFG = 9
WIDTH = 512
HEIGHT = 512
SAMPLER = "euler_ancestral"
SCHEDULER = "karras"


def load_config(config_path=None):
    """Load config.json and extract comfyui backend settings."""
    if config_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config.json")

    if not os.path.exists(config_path):
        print(f"  [WARN] Config not found at {config_path}, using defaults")
        return {
            "checkpoint": DEFAULT_CHECKPOINT,
            "loras": list(DEFAULT_LORAS),
            "url": "http://127.0.0.1:8188",
            "steps": STEPS,
            "cfg": CFG,
            "width": WIDTH,
            "height": HEIGHT,
            "sampler": SAMPLER,
            "scheduler": SCHEDULER,
        }

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    comfy = config.get("backends", {}).get("comfyui", {})
    return {
        "checkpoint": comfy.get("checkpoint", DEFAULT_CHECKPOINT),
        "loras": comfy.get("loras", list(DEFAULT_LORAS)),
        "url": comfy.get("url", "http://127.0.0.1:8188"),
        "steps": config.get("image_settings", {}).get("steps", STEPS),
        "cfg": config.get("image_settings", {}).get("cfg_scale", CFG),
        "width": config.get("image_settings", {}).get("width", WIDTH),
        "height": config.get("image_settings", {}).get("height", HEIGHT),
        "sampler": comfy.get("sampler", SAMPLER),
        "scheduler": comfy.get("scheduler", SCHEDULER),
    }


def queue_prompt(workflow, comfy_url="http://127.0.0.1:8188"):
    """Send workflow JSON to ComfyUI /prompt endpoint."""
    payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{comfy_url}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_history(prompt_id, comfy_url="http://127.0.0.1:8188"):
    """Poll /history for completed prompt."""
    url = f"{comfy_url}/history/{prompt_id}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_image(filename, subfolder, folder_type, comfy_url="http://127.0.0.1:8188"):
    """Download generated image from ComfyUI /view endpoint."""
    params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    query = urllib.parse.urlencode(params)
    url = f"{comfy_url}/view?{query}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def wait_for_prompt(prompt_id, timeout=300, comfy_url="http://127.0.0.1:8188"):
    """Poll history until prompt completes or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        history = get_history(prompt_id, comfy_url)
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            if outputs:
                return outputs
        time.sleep(1)
    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def build_workflow(
    prompt_text,
    negative_text,
    seed,
    width,
    height,
    steps,
    cfg,
    output_prefix,
    checkpoint=None,
    loras=None,
    sampler_name=None,
    scheduler_name=None,
):
    """
    Build a ComfyUI txt2img workflow dict.

    Supports optional checkpoint name and chained LoRA loading.
    If loras is provided, LoraLoader nodes are inserted between the
    CheckpointLoaderSimple and the CLIPTextEncode / KSampler nodes.

    Args:
        prompt_text: Positive prompt string.
        negative_text: Negative prompt string.
        seed: RNG seed for generation.
        width, height: Output image dimensions.
        steps: Sampling steps.
        cfg: Classifier-free guidance scale.
        output_prefix: Prefix for saved filename.
        checkpoint: Checkpoint filename (e.g. "dreamshaper_8.safetensors").
        loras: List of dicts with keys: name, strength_model, strength_clip.
        sampler_name: Sampler name (e.g. "euler_ancestral").
        scheduler_name: Scheduler name (e.g. "karras").
    """
    checkpoint = checkpoint or DEFAULT_CHECKPOINT
    loras = loras or []
    sampler_name = sampler_name or SAMPLER
    scheduler_name = scheduler_name or SCHEDULER

    workflow = {}
    next_id = 1

    # ---- Node 1: CheckpointLoaderSimple ----
    workflow[str(next_id)] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint},
    }
    checkpoint_node = str(next_id)
    next_id += 1

    current_model = [checkpoint_node, 0]  # MODEL output
    current_clip = [checkpoint_node, 1]   # CLIP output

    # ---- Chain LoRAs: each LoraLoader wraps model + clip ----
    for lora in loras:
        lora_name = lora.get("name", "")
        if not lora_name:
            continue
        lora_strength_model = lora.get("strength_model", 1.0)
        lora_strength_clip = lora.get("strength_clip", 1.0)

        workflow[str(next_id)] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength_model,
                "strength_clip": lora_strength_clip,
                "model": current_model,
                "clip": current_clip,
            },
        }
        current_model = [str(next_id), 0]
        current_clip = [str(next_id), 1]
        next_id += 1

    # ---- CLIPTextEncode (positive) ----
    workflow[str(next_id)] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt_text, "clip": current_clip},
    }
    positive_node = str(next_id)
    next_id += 1

    # ---- CLIPTextEncode (negative) ----
    workflow[str(next_id)] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative_text, "clip": current_clip},
    }
    negative_node = str(next_id)
    next_id += 1

    # ---- EmptyLatentImage ----
    workflow[str(next_id)] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": width, "height": height, "batch_size": 1},
    }
    latent_node = str(next_id)
    next_id += 1

    # ---- KSampler ----
    workflow[str(next_id)] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler_name,
            "scheduler": scheduler_name,
            "model": current_model,
            "positive": [positive_node, 0],
            "negative": [negative_node, 0],
            "latent_image": [latent_node, 0],
            "denoise": 1.0,
        },
    }
    sampler_node = str(next_id)
    next_id += 1

    # ---- VAEDecode ----
    workflow[str(next_id)] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": [sampler_node, 0], "vae": [checkpoint_node, 2]},
    }
    decode_node = str(next_id)
    next_id += 1

    # ---- SaveImage ----
    workflow[str(next_id)] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": output_prefix,
            "images": [decode_node, 0],
        },
    }

    return workflow


def resolve_category_config(cat_data, backend_config):
    """
    Merge per-category overrides on top of global backend config.

    Each category in simmoon_prompts.json can optionally specify:
      - "checkpoint": override the global checkpoint for this category
      - "loras": override the global LoRAs for this category (list of dicts)

    Returns a dict with keys: checkpoint, loras (plus other backend keys).
    """
    cfg = dict(backend_config)  # shallow copy of all backend config keys

    cat_checkpoint = cat_data.get("checkpoint")
    if cat_checkpoint:
        cfg["checkpoint"] = cat_checkpoint

    cat_loras = cat_data.get("loras")
    if cat_loras is not None:
        # Category provides its own LoRA list -> replace global
        cfg["loras"] = list(cat_loras)

    return cfg


def generate_image(
    prompt_data,
    output_dir,
    output_prefix,
    backend_config,
    comfy_url=None,
):
    """Generate one image via ComfyUI and return the local save path."""
    os.makedirs(output_dir, exist_ok=True)

    seed_val = random.randint(0, 2**32 - 1) if SEED == -1 else SEED

    workflow = build_workflow(
        prompt_text=prompt_data["prompt"],
        negative_text=prompt_data.get("negative_prompt", ""),
        seed=seed_val,
        width=backend_config.get("width", WIDTH),
        height=backend_config.get("height", HEIGHT),
        steps=backend_config.get("steps", STEPS),
        cfg=backend_config.get("cfg", CFG),
        output_prefix=output_prefix,
        checkpoint=backend_config.get("checkpoint"),
        loras=backend_config.get("loras", []),
        sampler_name=backend_config.get("sampler", SAMPLER),
        scheduler_name=backend_config.get("scheduler", SCHEDULER),
    )

    print(f"  Queueing: {output_prefix} (seed={seed_val})")
    print(f"  Checkpoint: {backend_config.get('checkpoint', 'default')}")
    lora_names = [l["name"] for l in backend_config.get("loras", []) if l.get("name")]
    if lora_names:
        print(f"  LoRAs: {', '.join(lora_names)}")

    result = queue_prompt(workflow, comfy_url)
    prompt_id = result["prompt_id"]
    print(f"  Prompt ID: {prompt_id}")

    outputs = wait_for_prompt(prompt_id, comfy_url=comfy_url)
    print(f"  Outputs received: {list(outputs.keys())}")

    # Find the SaveImage node output
    image_data = None
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for img_info in node_output["images"]:
                image_data = get_image(
                    img_info["filename"],
                    img_info.get("subfolder", ""),
                    img_info["type"],
                    comfy_url,
                )
                break
        if image_data:
            break

    if not image_data:
        raise RuntimeError(f"No image data returned for {output_prefix}")

    output_path = os.path.join(output_dir, f"{output_prefix}.png")
    with open(output_path, "wb") as f:
        f.write(image_data)
    print(f"  Saved: {output_path}")
    return output_path


def list_available_models(config_path):
    """Print available checkpoints and LoRAs found on disk."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Try to find ComfyUI models directory via WSL or local
    candidates = [
        os.path.expanduser("~/ComfyUI/models"),
        # Windows path (when running natively without WSL)
        os.path.expanduser("~\\ComfyUI\\models"),
    ]

    models_dir = None
    for c in candidates:
        if os.path.isdir(c):
            models_dir = c
            break

    # Try WSL
    if not models_dir:
        import subprocess
        try:
            result = subprocess.run(
                ["wsl", "-d", "Ubuntu", "-e", "bash", "-c", "ls ~/ComfyUI/models/checkpoints/ ~/ComfyUI/models/loras/ 2>/dev/null"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = [l for l in result.stdout.split("\n") if l.strip()]
                print("Models on WSL2:")
                for line in lines:
                    print(f"  {line}")
                return
        except Exception:
            pass

    # Local check
    if models_dir:
        print(f"Models in {models_dir}:")
        for root, dirs, files in os.walk(models_dir):
            rel = os.path.relpath(root, models_dir)
            if rel == ".":
                continue
            safetensors = [f for f in files if f.endswith(".safetensors")]
            if safetensors:
                print(f"\n  {rel}/:")
                for f in safetensors:
                    size = os.path.getsize(os.path.join(root, f))
                    size_mb = size / (1024 * 1024)
                    print(f"    {f}  ({size_mb:.1f} MB)")
    else:
        print("[WARN] Could not locate ComfyUI models directory.")
        print("   Expected at ~/ComfyUI/models/ (WSL2) or ~\\ComfyUI\\models\\ (Windows)")


def parse_args(argv=None):
    """Parse CLI arguments for config overrides."""
    parser = argparse.ArgumentParser(
        description="SIMMOON Asset Generator - ComfyUI Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python generate_comfyui.py                                 # use defaults from config.json\n"
            "  python generate_comfyui.py --checkpoint dreamshaper_8.safetensors\n"
            "  python generate_comfyui.py --checkpoint pixelArtSpriteDiffusion_safetensors.safetensors \\\n"
            "      --lora pixhell_15.safetensors:1.0:1.0\n"
            "  python generate_comfyui.py --list-models                    # show available models\n"
            "  python generate_comfyui.py --no-loras                       # disable all LoRAs\n"
            "  python generate_comfyui.py --suffix dreamshaper_v8           # save files with run prefix\n"
            "  python generate_comfyui.py --suffix pixelart --checkpoint pixelArtSpriteDiffusion_safetensors.safetensors --lora pixhell_15.safetensors:1.0:1.0"
        ),
    )
    parser.add_argument(
        "--checkpoint", type=str, default=None,
        help="Override checkpoint (e.g. dreamshaper_8.safetensors)",
    )
    parser.add_argument(
        "--lora", type=str, action="append", dest="lora_overrides",
        help="Add a LoRA (format: name.safetensors:strength_model:strength_clip). Can be repeated.",
    )
    parser.add_argument(
        "--no-loras", action="store_true", default=False,
        help="Disable all LoRAs from config",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config.json (default: config.json in script directory)",
    )
    parser.add_argument(
        "--list-models", action="store_true", default=False,
        help="List available checkpoints and LoRAs on disk",
    )
    parser.add_argument(
        "--suffix", type=str, default=None,
        help="Run suffix to prevent file overwrites (e.g. --suffix dreamshaper_v8)",
    )
    parser.add_argument(
        "--categories", type=str, default=None,
        help="Comma-separated list of categories to generate (e.g. --categories businesses,vehicles)",
    )
    return parser.parse_args(argv)


def merge_cli_args(backend_config, args):
    """Apply CLI argument overrides on top of config-based settings."""
    cfg = dict(backend_config)

    if args.checkpoint:
        cfg["checkpoint"] = args.checkpoint

    if args.no_loras:
        cfg["loras"] = []
    elif args.lora_overrides:
        # Parse --lora name:strength_model:strength_clip
        loras = []
        for lora_str in args.lora_overrides:
            parts = lora_str.split(":")
            name = parts[0]
            strength_model = float(parts[1]) if len(parts) > 1 else 1.0
            strength_clip = float(parts[2]) if len(parts) > 2 else strength_model
            loras.append({
                "name": name,
                "strength_model": strength_model,
                "strength_clip": strength_clip,
            })
        cfg["loras"] = loras

    return cfg


def main():
    args = parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Resolve config path
    config_path = args.config
    if not config_path:
        config_path = os.path.join(script_dir, "config.json")

    # --list-models flag
    if args.list_models:
        list_available_models(config_path)
        return

    # Load backend config
    backend_config = load_config(config_path)

    # Apply CLI overrides
    backend_config = merge_cli_args(backend_config, args)

    # Load prompts
    prompts_path = os.path.join(script_dir, "simmoon_prompts.json")
    with open(prompts_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = data["categories"]
    total = sum(len(cat["prompts"]) for cat in categories.values())
    print(f"SIMMOON ComfyUI Generator")
    print(f"Total prompts to generate: {total}")
    print(f"Default checkpoint: {backend_config['checkpoint']}")
    print(f"Default LoRAs: {[l['name'] for l in backend_config.get('loras', []) if l.get('name')]}")
    if args.suffix:
        print(f"Run suffix: {args.suffix}")
    print("=" * 50)
    generated = 0
    failed = 0

    # Grab the global negative_prompt_base from prompts file as fallback
    negative_prompt_base = data.get("negative_prompt_base", "")

    # Filter by --categories if specified
    selected_categories = categories
    if args.categories:
        requested = [c.strip() for c in args.categories.split(",")]
        selected_categories = {k: v for k, v in categories.items() if k in requested}
        missed = [c for c in requested if c not in selected_categories]
        if missed:
            print(f"[WARN] Unknown categories: {', '.join(missed)}")
        if not selected_categories:
            print("[ERROR] No valid categories specified.")
            sys.exit(1)
        print(f"Filtered to categories: {', '.join(selected_categories.keys())}")

    for cat_key, cat_data in selected_categories.items():
        # Resolve config for this category (allows per-category overrides)
        cat_config = resolve_category_config(cat_data, backend_config)

        # Derive output dir from the category's output_dir
        output_dir = os.path.join(script_dir, cat_data["output_dir"].split("/")[-1])
        print(f"\n[CAT] Category: {cat_key} ({len(cat_data['prompts'])} items)")
        print(f"   Output: {output_dir}")
        print(f"   Checkpoint: {cat_config['checkpoint']}")
        print(f"   ComfyUI URL: {cat_config.get('url', 'http://127.0.0.1:8188')}")
        lora_names = [l["name"] for l in cat_config.get("loras", []) if l.get("name")]
        if lora_names:
            print(f"   LoRAs: {', '.join(lora_names)}")

        for prompt_item in cat_data["prompts"]:
            item_id = prompt_item["id"]
            name = prompt_item["name"]
            safe_name = name.lower().replace(" ", "_").replace("-", "_")
            output_prefix = f"{item_id}_{safe_name}"
            if args.suffix:
                safe_suffix = args.suffix.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
                output_prefix = f"{safe_suffix}_{output_prefix}"

            # Use per-item negative_prompt, fallback to category level, then base
            negative_text = prompt_item.get("negative_prompt", "")
            if not negative_text:
                negative_text = negative_prompt_base

            prompt_data = dict(prompt_item)
            prompt_data["negative_prompt"] = negative_text

            try:
                generate_image(
                    prompt_data,
                    output_dir,
                    output_prefix,
                    cat_config,
                    comfy_url=cat_config.get("url"),
                )
                generated += 1
            except Exception as e:
                print(f"  [FAIL] {output_prefix} - {e}")
                failed += 1

    print("\n" + "=" * 50)
    print(f"Generation complete: {generated} generated, {failed} failed")


if __name__ == "__main__":
    main()
