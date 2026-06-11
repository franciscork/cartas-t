#!/usr/bin/env python3
"""
SIMMOON Generator Factory — Unified image generation with automatic fallback.

Fallback chain: ComfyUI (local GPU) → HuggingFace (cloud free) → Leonardo.ai (cloud API)

Usage:
    from generator_factory import GeneratorFactory
    gen = GeneratorFactory()
    gen.generate_one(prompt, output_path, negative_prompt="", width=512, height=512)
    gen.generate_category("businesses", output_dir="./output")
"""

import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# ── Try importing ComfyUI generator functions ────────────────────────────
# These live in generate_comfyui.py in the same directory.
# We import dynamically so the factory works even if ComfyUI is offline.

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from generate_comfyui import (
        queue_prompt,
        wait_for_prompt,
        get_image,
        build_workflow,
        load_config,
    )
    _COMFYUI_AVAILABLE = True
except ImportError:
    _COMFYUI_AVAILABLE = False

try:
    from leonardo_client import LeonardoClient
    _LEONARDO_AVAILABLE = True
except ImportError:
    _LEONARDO_AVAILABLE = False

# Consistent requests detection
try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


class GeneratorFactory:
    """Unified generator that automatically falls back to cloud on failure.

    Priority:
      1. ComfyUI (local, port 8188) — if reachable and configured
      2. HuggingFace (cloud, free) — if API key is set
      3. Leonardo.ai (cloud, API key) — if API key is set

    Config is loaded from config.json in the script directory.
    """

    COMFYUI_HEALTH_ENDPOINT = "/queue"
    COMFYUI_DEFAULT_URL = "http://127.0.0.1:8188"

    def __init__(
        self,
        config_path: str = "",
        comfyui_url: str = "",
        leonardo_api_key: str = "",
    ):
        """Initialize the generator factory.

        Args:
            config_path: Path to config.json (defaults to script_dir/config.json).
            comfyui_url: Override ComfyUI URL.
            leonardo_api_key: Override Leonardo API key.
        """
        config_path = config_path or str(SCRIPT_DIR / "config.json")
        self.config_path = config_path

        # Load config
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

        backend_config = self.config.get("backends", {})

        # ComfyUI settings
        comfy_config = backend_config.get("comfyui", {})
        self.comfyui_url = (
            comfyui_url
            or comfy_config.get("url", self.COMFYUI_DEFAULT_URL)
        ).rstrip("/")
        self.comfyui_enabled = comfy_config.get("enabled", True)

        # HuggingFace settings
        hf_config = backend_config.get("huggingface", {})
        self.hf_api_key = os.environ.get(
            hf_config.get("api_key_env", "HF_API_KEY"), ""
        )
        self.hf_enabled = hf_config.get("enabled", False)
        self.hf_model = hf_config.get("model", "stabilityai/stable-diffusion-xl-base-1.0")
        self.hf_url_template = hf_config.get(
            "url_template", "https://api-inference.huggingface.co/models/{model}"
        )

        # Leonardo settings
        leo_config = backend_config.get("leonardo", {})
        self.leonardo_api_key = leonardo_api_key or os.environ.get(
            leo_config.get("api_key_env", "LEONARDO_API_KEY"), ""
        )
        self.leonardo_enabled = leo_config.get("enabled", False)
        self.leonardo_model_id = leo_config.get("model_id", "")
        self.leonardo_preset = leo_config.get("preset_style", "DYNAMIC")

        # Default LoRAs from config (used when no CLI override)
        self.default_checkpoint = comfy_config.get("checkpoint", "")
        self.default_loras = comfy_config.get("loras", [])

        # Image settings defaults
        img = self.config.get("image_settings", {})
        self.default_width = img.get("width", 512)
        self.default_height = img.get("height", 512)
        self.default_steps = img.get("steps", 28)
        self.default_cfg = img.get("cfg_scale", 9)

        # Backend status cache
        self._comfyui_healthy: Optional[bool] = None
        self._comfyui_check_time: float = 0
        self._comfyui_cache_ttl: float = 30  # seconds

        self._hf_available: Optional[bool] = None
        self._leonardo_client: Optional[LeonardoClient] = None

    # ── HuggingFace helpers ───────────────────────────────────────────

    def _get_hf_url(self) -> str:
        """Build the HuggingFace Inference API URL for the configured model."""
        return self.hf_url_template.format(model=self.hf_model)

    def _check_huggingface(self) -> bool:
        """Check if HuggingFace backend is available (cached)."""
        if self._hf_available is not None:
            return self._hf_available

        if not self.hf_enabled or not self.hf_api_key:
            self._hf_available = False
            return False

        self._hf_available = True
        return True

    def _generate_huggingface(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
        steps: int,
        cfg: float,
    ) -> str:
        """Generate via HuggingFace serverless Inference API.

        Returns output_path on success, raises on failure.
        """
        url = self._get_hf_url()

        # Build parameters
        params = {
            "negative_prompt": negative_prompt,
            "guidance_scale": cfg,
            "num_inference_steps": steps,
            "width": width,
            "height": height,
            "seed": seed,
        }

        payload = {"inputs": prompt, "parameters": params}
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json",
        }

        # Retry loop for model loading / rate limits
        max_retries = 4
        for attempt in range(max_retries):
            try:
                if not _HAS_REQUESTS:
                    raise RuntimeError("requests library required for HuggingFace backend")

                resp = _requests.post(url, data=data, headers=headers, timeout=120)
                status = resp.status_code

                if status == 200:
                    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    return output_path

                if status == 503:
                    # Model is loading — wait and retry
                    try:
                        body = resp.json()
                        wait = body.get("estimated_time", 30)
                    except Exception:
                        wait = 30
                    print(f"  [HF] Model loading, waiting {wait:.0f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(min(wait, 60))
                    continue

                if status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 15))
                    print(f"  [HF] Rate limited, waiting {retry_after}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_after)
                    continue

                # Other errors
                body_text = resp.text[:300] if hasattr(resp, "text") else str(resp.content[:300])
                raise RuntimeError(f"HTTP {status}: {body_text}")

            except (urllib.error.URLError, OSError) as e:
                if attempt < max_retries - 1:
                    print(f"  [HF] Connection error, retrying in 5s... ({e})")
                    time.sleep(5)
                    continue
                raise RuntimeError(f"HuggingFace connection failed: {e}")

        raise RuntimeError(f"HuggingFace generation failed after {max_retries} attempts")

    # ── Leonardo helpers ────────────────────────────────────────────────

    def _get_leonardo(self) -> Optional[LeonardoClient]:
        """Lazy-init Leonardo client."""
        if not _LEONARDO_AVAILABLE:
            return None
        if not self.leonardo_enabled or not self.leonardo_api_key:
            return None
        if self._leonardo_client is None:
            self._leonardo_client = LeonardoClient(
                api_key=self.leonardo_api_key,
                default_width=self.default_width,
                default_height=self.default_height,
            )
        return self._leonardo_client

    def _check_comfyui(self) -> bool:
        """Check if ComfyUI is reachable (with caching to avoid flooding)."""
        now = time.time()
        if self._comfyui_healthy is not None and (now - self._comfyui_check_time) < self._comfyui_cache_ttl:
            return self._comfyui_healthy

        if not self.comfyui_enabled or not _COMFYUI_AVAILABLE:
            self._comfyui_healthy = False
            return False

        try:
            url = f"{self.comfyui_url}{self.COMFYUI_HEALTH_ENDPOINT}"
            if _HAS_REQUESTS:
                resp = _requests.get(url, timeout=3)
                healthy = resp.status_code in (200, 404)  # 404 = no queue, server up
            else:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=3) as resp:
                    healthy = True
        except Exception:
            healthy = False

        self._comfyui_healthy = healthy
        self._comfyui_check_time = now
        return healthy

    def get_active_backend(self) -> str:
        """Return the current active backend name."""
        if self._check_comfyui():
            return "comfyui"
        if self._check_huggingface():
            return "huggingface"
        if self._get_leonardo() is not None:
            return "leonardo"
        return "none"

    def is_any_backend_available(self) -> bool:
        """Check if at least one backend is available."""
        return (
            self._check_comfyui()
            or self._check_huggingface()
            or self._get_leonardo() is not None
        )

    # ── Single image generation ─────────────────────────────────────────

    def generate_one(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str = "",
        width: int = 0,
        height: int = 0,
        seed: int = -1,
        steps: int = 0,
        cfg: float = 0,
        checkpoint: str = "",
        loras: Optional[list] = None,
        no_loras: bool = False,
        output_prefix: str = "simmoon_factory",
    ) -> str:
        """Generate a single image, falling back automatically.

        Args:
            prompt: Text prompt.
            output_path: Full path to save the image.
            negative_prompt: Negative prompt.
            width, height: Image dimensions (defaults from config).
            seed: RNG seed (-1 = random).
            steps: Sampling steps (defaults from config).
            cfg: CFG scale (defaults from config).
            checkpoint: ComfyUI checkpoint name.
            loras: List of LoRA dicts for ComfyUI.
            output_prefix: Prefix for ComfyUI's SaveImage node.

        Returns:
            Path to the saved image.

        Raises:
            RuntimeError: If no backend is available or generation fails on all.
        """
        w = width or self.default_width
        h = height or self.default_height
        s = steps or self.default_steps
        c = cfg or self.default_cfg
        seed_val = seed if seed >= 0 else random.randint(0, 2**32 - 1)

        # Resolve checkpoint and LoRAs with config defaults
        resolved_checkpoint = checkpoint or self.default_checkpoint
        resolved_loras = loras
        if resolved_loras is None:
            resolved_loras = [] if no_loras else self.default_loras
        elif no_loras:
            resolved_loras = []

        # ── Try ComfyUI first ──────────────────────────────────────────
        if self._check_comfyui():
            try:
                return self._generate_comfyui(
                    prompt=prompt,
                    output_path=output_path,
                    negative_prompt=negative_prompt,
                    width=w,
                    height=h,
                    seed=seed_val,
                    steps=s,
                    cfg=c,
                    checkpoint=resolved_checkpoint,
                    loras=resolved_loras,
                    output_prefix=output_prefix,
                )
            except Exception as e:
                print(f"  [WARN] ComfyUI generation failed: {e}")

        # ── Fallback to HuggingFace ─────────────────────────────────────
        if self._check_huggingface():
            try:
                print(f"  [FALLBACK] Using HuggingFace (previous backends unavailable)...")
                return self._generate_huggingface(
                    prompt=prompt,
                    output_path=output_path,
                    negative_prompt=negative_prompt,
                    width=w,
                    height=h,
                    seed=seed_val,
                    steps=s,
                    cfg=c,
                )
            except Exception as e:
                print(f"  [WARN] HuggingFace generation failed: {e}")

        # ── Fallback to Leonardo.ai ──────────────────────────────────────
        leo = self._get_leonardo()
        if leo is not None:
            try:
                print(f"  [FALLBACK] Using Leonardo.ai (previous backends unavailable)...")
                return self._generate_leonardo(
                    prompt=prompt,
                    output_path=output_path,
                    negative_prompt=negative_prompt,
                    width=w,
                    height=h,
                )
            except Exception as e:
                print(f"  [WARN] Leonardo.ai generation failed: {e}")

        raise RuntimeError(
            "No generation backend available. "
            "Start ComfyUI, or set HF_API_KEY / LEONARDO_API_KEY."
        )

    # ── ComfyUI implementation ──────────────────────────────────────────

    def _generate_comfyui(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
        steps: int,
        cfg: float,
        checkpoint: str,
        loras: Optional[list],
        output_prefix: str,
    ) -> str:
        """Generate via ComfyUI (local)."""
        workflow = build_workflow(
            prompt_text=prompt,
            negative_text=negative_prompt,
            seed=seed,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            output_prefix=output_prefix,
            checkpoint=checkpoint or None,
            loras=loras or [],
        )

        result = queue_prompt(workflow, self.comfyui_url)
        prompt_id = result["prompt_id"]

        outputs = wait_for_prompt(prompt_id, comfy_url=self.comfyui_url)

        # Extract image data
        image_data = None
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    image_data = get_image(
                        img_info["filename"],
                        img_info.get("subfolder", ""),
                        img_info["type"],
                        self.comfyui_url,
                    )
                    break
            if image_data:
                break

        if not image_data:
            raise RuntimeError(f"No image data for {output_prefix}")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_data)

        return output_path

    # ── Leonardo.ai implementation ──────────────────────────────────────

    def _generate_leonardo(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str,
        width: int,
        height: int,
    ) -> str:
        """Generate via Leonardo.ai (cloud)."""
        leo = self._get_leonardo()
        if leo is None:
            raise RuntimeError("Leonardo client not initialized")

        return leo.generate_and_save(
            prompt=prompt,
            output_path=output_path,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            model_id=self.leonardo_model_id or None,
            preset_style=self.leonardo_preset or None,
        )

    # ── Category-level generation ───────────────────────────────────────

    def generate_category(
        self,
        category: str,
        output_dir: str = "",
        run_suffix: str = "",
        checkpoint: str = "",
        no_loras: bool = False,
        loras: Optional[list] = None,
        prompts_file: str = "",
    ) -> dict:
        """Generate all images for a category from simmoon_prompts.json.

        Args:
            category: Category key (e.g. "businesses").
            output_dir: Output directory (defaults from prompts config).
            run_suffix: Prefix for filenames.
            checkpoint: ComfyUI checkpoint override.
            no_loras: Disable LoRAs for ComfyUI.
            loras: LoRA list for ComfyUI.
            prompts_file: Path to simmoon_prompts.json.

        Returns:
            Dict with keys: generated, failed, skipped, total, backend.
        """
        prompts_path = Path(prompts_file or SCRIPT_DIR / "simmoon_prompts.json")
        with open(prompts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        categories = data.get("categories", {})
        if category not in categories:
            raise ValueError(
                f"Unknown category '{category}'. Available: {list(categories.keys())}"
            )

        cat_data = categories[category]
        output = output_dir or os.path.join(
            str(SCRIPT_DIR), cat_data.get("output_dir", category)
        )
        os.makedirs(output, exist_ok=True)

        prompts = cat_data.get("prompts", [])
        negative_base = data.get("negative_prompt_base", "")

        backend = self.get_active_backend()
        if backend == "none":
            raise RuntimeError("No generation backend available")

        print(f"\n{'='*60}")
        print(f"  Generating category: {category} ({len(prompts)} items)")
        print(f"  Backend: {backend}")
        print(f"  Output: {output}")
        print(f"{'='*60}")

        stats = {"generated": 0, "failed": 0, "skipped": 0, "backend": backend}

        for p in prompts:
            name = p["name"]
            safe = name.lower().replace(" ", "_").replace("-", "_")
            prefix = f"{p['id']}_{safe}"
            if run_suffix:
                safe_suffix = run_suffix.strip().replace(" ", "_").replace("/", "_")
                prefix = f"{safe_suffix}_{prefix}"
            out_path = os.path.join(output, f"{prefix}.png")

            # Use per-item negative_prompt, fallback to base
            neg = p.get("negative_prompt", "") or negative_base

            # Skip if file exists
            if os.path.exists(out_path):
                stats["skipped"] += 1
                continue

            try:
                self.generate_one(
                    prompt=p.get("prompt", ""),
                    output_path=out_path,
                    negative_prompt=neg,
                    checkpoint=checkpoint,
                    no_loras=no_loras,
                    loras=None if no_loras else loras,
                    output_prefix=prefix,
                )
                stats["generated"] += 1
                print(f"  ✅ {prefix}.png")
            except Exception as e:
                stats["failed"] += 1
                print(f"  ❌ {prefix}: {e}")

            # Rate limiting for cloud APIs
            if backend == "leonardo":
                time.sleep(1.5)
            elif backend == "huggingface":
                time.sleep(1.0)
            # No rate limit for local backend (comfyui)

        # Summary
        total = len(prompts)
        print(f"\n  Category complete: {stats['generated']}/{total} generated, "
              f"{stats['failed']} failed, {stats['skipped']} skipped "
              f"(backend: {stats['backend']})")
        return stats


# ── Quick diagnostic ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("SIMMOON Generator Factory — Backend Status\n")
    gen = GeneratorFactory()

    print(f"  ComfyUI URL      : {gen.comfyui_url}")
    comfy_ok = gen._check_comfyui()
    print(f"  ComfyUI status   : {'✅ Reachable' if comfy_ok else '❌ Unreachable'}")

    hf_ok = gen._check_huggingface()
    print(f"  HuggingFace      : {'✅ Configured' if hf_ok else '❌ Not configured'}")
    if not hf_ok:
        print(f"     → Set HF_API_KEY in ~/.bashrc")
        print(f"     → Get free token: https://huggingface.co/settings/tokens")

    leo = gen._get_leonardo()
    leo_ok = leo is not None
    print(f"  Leonardo API     : {'✅ Configured' if leo_ok else '❌ Not configured'}")

    active = gen.get_active_backend()
    print(f"\n  ▶ Active backend : {active}")

    if active == "none":
        print("\n  💡 To enable generation:")
        print("     1. Start ComfyUI: cd ~/ComfyUI && python main.py")
        print("     2. Or set HF key: export HF_API_KEY='hf_...'")
        print("     3. Or set Leonardo key: export LEONARDO_API_KEY='your_key'")
    else:
        print(f"\n  ✅ Ready to generate. Try:")
        print(f"     gen.generate_one('test pixel art', 'test.png')")
