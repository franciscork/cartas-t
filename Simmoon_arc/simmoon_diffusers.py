#!/usr/bin/env python3
"""
SIMMOON Diffusers Generator - Generate game assets directly using diffusers.
Bypasses ComfyUI/HuggingFace APIs and loads the model directly.
Uses models from the ComfyUI checkpoints directory.

Usage:
    python simmoon_diffusers.py
    python simmoon_diffusers.py --category businesses
    python simmoon_diffusers.py --dry-run
"""

import argparse
import json
import sys
import time
import os
from pathlib import Path
from datetime import datetime

# --- Configuration ---------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"
PROMPTS_PATH = SCRIPT_DIR / "simmoon_prompts.json"

# Model options — Diffusers tries each in order until one works:
# 1. Local checkpoint from ComfyUI models directory
# 2. HuggingFace official SD 1.5 (auto-download, ~2GB cached)
LOCAL_MODEL_PATH = Path(os.path.expanduser("~/ComfyUI/models/checkpoints/v1-5-pruned-emaonly.safetensors"))
HF_MODEL_ID = "runwayml/stable-diffusion-v1-5"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompts():
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Generator -------------------------------------------------------------

class DiffusersGenerator:
    def __init__(self, categories=None, dry_run=False):
        self.config = load_config()
        self.prompts_data = load_prompts()
        self.dry_run = dry_run
        self.categories = categories
        self.stats = {"generated": 0, "failed": 0, "skipped": 0}
        self.pipe = None
        self.device = None

    def _load_model(self):
        """Load the Stable Diffusion model.
        Tries local pruned checkpoint first, then falls back to HuggingFace."""
        if self.dry_run:
            return

        import torch
        from diffusers import StableDiffusionPipeline

        start = time.time()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[*] Using device: {self.device}")
        sys.stdout.flush()

        # Strategy 1: Load from local pruned file (sd_v1-5_pruned.safetensors)
        local_ok = LOCAL_MODEL_PATH.exists() and LOCAL_MODEL_PATH.stat().st_size >= 1_000_000_000
        if local_ok:
            size_gb = LOCAL_MODEL_PATH.stat().st_size / 1e9
            print(f"[*] Attempt 1: Loading local model: {LOCAL_MODEL_PATH.name} ({size_gb:.1f} GB)")
            sys.stdout.flush()
            try:
                self.pipe = StableDiffusionPipeline.from_single_file(
                    str(LOCAL_MODEL_PATH),
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    safety_checker=None,
                    requires_safety_checker=False,
                )
                elapsed = time.time() - start
                print(f"[OK] Local model loaded in {elapsed:.1f}s")
                self._optimize()
                return
            except Exception as e:
                print(f"  [WARN] Local model failed: {e}")
                print(f"  [*] Falling back to HuggingFace model...")
                sys.stdout.flush()

        # Strategy 2: Download from HuggingFace (runwayml/stable-diffusion-v1-5)
        print(f"[*] Attempt 2: Loading HuggingFace model: {HF_MODEL_ID}")
        print(f"[*] This will download ~2GB on first run...")
        sys.stdout.flush()
        try:
            self.pipe = StableDiffusionPipeline.from_pretrained(
                HF_MODEL_ID,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
            )
            elapsed = time.time() - start
            print(f"[OK] HuggingFace model loaded in {elapsed:.1f}s")
            self._optimize()
            return
        except Exception as e:
            print(f"[ERROR] Both model loading strategies failed: {e}")
            print(f"[HINT] Ensure internet access for HuggingFace download, or place")
            print(f"       sd_v1-5_pruned.safetensors at: {LOCAL_MODEL_PATH}")
            sys.exit(1)

    def _optimize(self):
        """Apply device placement and memory optimizations."""
        self.pipe = self.pipe.to(self.device)
        if self.device == "cuda":
            self.pipe.enable_attention_slicing()
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
            except Exception:
                pass

    def _get_category_settings(self, cat_name):
        """Get per-category image settings."""
        game_settings = self.config.get("game_asset_settings", {})
        settings = dict(self.config["image_settings"])

        # Map category names to game_asset_settings keys
        cat_map = {
            "businesses": "buildings",
            "vehicles": "vehicles",
            "greenhouses": "buildings",
            "solar_energy": "buildings",
            "buildings_misc": "buildings",
            "lunar_map": "maps",
            "lunar_sites": "sites",
            "ui_elements": "ui_elements",
            "terrain": "terrain",
        }
        mapped = cat_map.get(cat_name)
        if mapped and mapped in game_settings:
            gs = game_settings[mapped]
            if "width" in gs:
                settings["width"] = gs["width"]
            if "height" in gs:
                settings["height"] = gs["height"]

        return settings

    def generate(self, prompt_data, output_path, category_settings):
        """Generate a single image with the given prompt."""
        # Accept both str and Path
        if not isinstance(output_path, Path):
            output_path = Path(output_path)

        negative_prompt = prompt_data.get("negative_prompt", self.config["negative_prompt"])

        generator = None
        import torch
        if self.device == "cuda":
            generator = torch.Generator(device=self.device).manual_seed(
                int(time.time() % (2**32))
            )

        image = self.pipe(
            prompt=prompt_data["prompt"],
            negative_prompt=negative_prompt,
            width=category_settings.get("width", 512),
            height=category_settings.get("height", 512),
            num_inference_steps=category_settings.get("steps", 25),
            guidance_scale=category_settings.get("cfg_scale", 7),
            generator=generator,
        ).images[0]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return True

    def run(self):
        print("=" * 70)
        print(f"  SIMMOON Diffusers Generator")
        print(f"  Model: {HF_MODEL_ID}")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        sys.stdout.flush()

        # Load model
        self._load_model()

        # Process categories
        categories = self.prompts_data["categories"]
        if self.categories:
            categories = {k: v for k, v in categories.items() if k in self.categories}

        total_images = sum(len(cat["prompts"]) for cat in categories.values())
        print(f"\n[*] Total images to generate: {total_images}")
        print(f"[*] Categories: {', '.join(categories.keys())}")

        if self.dry_run:
            self._dry_run(categories)
            return

        current = 0
        overall_start = time.time()

        for cat_name, cat_data in categories.items():
            print(f"\n{'-' * 50}")
            print(f"  Category: {cat_name} ({len(cat_data['prompts'])} images)")
            print(f"{'-' * 50}")

            output_dir = SCRIPT_DIR / cat_data["output_dir"].replace("Simmoon_arc/", "")
            cat_settings = self._get_category_settings(cat_name)

            for prompt_item in cat_data["prompts"]:
                current += 1
                filename = f"{prompt_item['id']}_{prompt_item['name'].lower().replace(' ', '_').replace('-', '_')}.png"
                output_path = output_dir / filename

                print(f"\n  [{current}/{total_images}] {prompt_item['name']}")
                print(f"    Prompt: {prompt_item['prompt'][:80]}...")

                if output_path.exists():
                    print(f"    [SKIP] Already exists: {filename}")
                    self.stats["skipped"] += 1
                    continue

                try:
                    start_time = time.time()
                    success = self.generate(prompt_item, output_path, cat_settings)
                    duration = time.time() - start_time

                    if success:
                        self.stats["generated"] += 1
                        print(f"    [OK] Saved: {filename} ({duration:.1f}s)")
                    else:
                        self.stats["failed"] += 1
                        print(f"    [FAIL] Could not generate: {filename}")
                except Exception as e:
                    self.stats["failed"] += 1
                    print(f"    [ERROR] {e}")

                # Brief pause between images
                time.sleep(1)

        total_duration = time.time() - overall_start
        self._print_summary(total_duration, total_images)

    def _dry_run(self, categories):
        print("\n[DRY RUN MODE] - Listing all prompts without generating.\n")
        total = 0
        for cat_name, cat_data in categories.items():
            print(f"\n{'=' * 60}")
            print(f"  CATEGORY: {cat_name}")
            print(f"  Output dir: {cat_data['output_dir']}")
            print(f"{'=' * 60}")
            cat_settings = self._get_category_settings(cat_name)
            print(f"  Settings: {cat_settings.get('width')}x{cat_settings.get('height')}, "
                  f"steps={cat_settings.get('steps')}, cfg={cat_settings.get('cfg_scale')}")
            for p in cat_data["prompts"]:
                total += 1
                print(f"\n  [{p['id']}] {p['name']}")
                print(f"    Prompt: {p['prompt'][:100]}...")
            print()
        print(f"\n[DRY RUN] Total prompts: {total}")
        print("[DRY RUN] No images were generated.")

    def _print_summary(self, duration, total_images):
        print(f"\n{'=' * 70}")
        print(f"  GENERATION COMPLETE")
        print(f"{'=' * 70}")
        print(f"  Generated: {self.stats['generated']}")
        print(f"  Failed:    {self.stats['failed']}")
        print(f"  Skipped:   {self.stats['skipped']}")
        print(f"  Duration:  {duration / 60:.1f} minutes")
        print(f"  Expected:  {total_images} total images")
        print(f"{'=' * 70}")


# --- Main ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON Diffusers Generator - Generate game assets using diffusers directly"
    )
    parser.add_argument(
        "--category", "-c",
        nargs="+",
        default=None,
        help="Specific categories to generate (default: all)"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="List all prompts without generating"
    )
    parser.add_argument(
        "--list-categories", "-l",
        action="store_true",
        help="List all available categories and exit"
    )

    args = parser.parse_args()

    # List categories
    if args.list_categories:
        prompts_data = load_prompts()
        print("\nAvailable categories:")
        for cat_name, cat_data in prompts_data["categories"].items():
            count = len(cat_data["prompts"])
            print(f"  {cat_name:25s} - {count:3d} images  ({cat_data['output_dir']})")
        total = sum(len(c["prompts"]) for c in prompts_data["categories"].values())
        print(f"\n  Total: {total} images")
        return

    generator = DiffusersGenerator(
        categories=args.category,
        dry_run=args.dry_run,
    )
    generator.run()


if __name__ == "__main__":
    main()
