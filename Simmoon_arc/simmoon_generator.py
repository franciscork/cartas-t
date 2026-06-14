#!/usr/bin/env python3
"""
SIMMOON Image Generator - Multi-Backend AI Image Generation
Connects to ComfyUI or HuggingFace API to generate game assets.

Supports both txt2img and img2img generation modes.

Usage:
    python simmoon_generator.py --backend comfyui [--category businesses] [--dry-run]
    python simmoon_generator.py --backend comfyui --category vehicles
    python simmoon_generator.py --backend huggingface --category greenhouses
    python simmoon_generator.py --backend comfyui --img2img --input-image path/to/image.png
"""

import argparse
import base64
import json
import os
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library required. Install with: pip install requests")
    sys.exit(1)

# --- Configuration ---------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.json"
PROMPTS_PATH = SCRIPT_DIR / "simmoon_prompts.json"

# Import ComfyUI workflow builder from canonical source (generate_comfyui.py)
try:
    from generate_comfyui import build_workflow as _build_workflow_comfyui
    _COMFYUI_WORKFLOW_AVAILABLE = True
except ImportError:
    _COMFYUI_WORKFLOW_AVAILABLE = False


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompts():
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def encode_image_to_base64(image_path, with_prefix=False):
    """Read an image file and return a base64-encoded string.

    Args:
        image_path: Path to the image file.
        with_prefix: If True, prepend 'data:mime;base64,' prefix.
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    if with_prefix:
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "bmp": "image/bmp"}
        mime = mime_map.get(ext, "image/png")
        return f"data:{mime};base64,{b64}"
    return b64


# --- ComfyUI Backend -------------------------------------------------------

class ComfyUIBackend:
    """Connects to ComfyUI API via HTTP (queue) and WebSocket (progress)."""

    def __init__(self, config):
        self.config = config
        self.base_url = config["backends"]["comfyui"]["url"]
        self.prompt_endpoint = f"{self.base_url}/prompt"
        self.history_endpoint = f"{self.base_url}/history"
        self.view_endpoint = f"{self.base_url}/view"
        self.upload_endpoint = f"{self.base_url}/upload/image"
        self.client_id = str(uuid.uuid4())
        self.settings = config["image_settings"]

    def check_connection(self):
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return r.status_code == 200
        except requests.ConnectionError:
            return False

    def _build_txt2img_workflow(self, prompt_text, negative_text, width, height, steps, cfg, seed, ckpt_name=None):
        """Build a basic txt2img ComfyUI workflow.
        
        Uses the canonical build_workflow from generate_comfyui.py when available,
        falling back to inline builder for standalone usage.
        """
        if _COMFYUI_WORKFLOW_AVAILABLE:
            return _build_workflow_comfyui(
                prompt_text=prompt_text,
                negative_text=negative_text,
                seed=seed if seed > 0 else int(time.time() % (2**32)),
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                output_prefix="simmoon",
                checkpoint=ckpt_name or None,
                loras=[],
                sampler_name="dpmpp_2m",
                scheduler_name="karras",
            )
        # Fallback inline builder (standalone mode without generate_comfyui.py)
        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": ckpt_name or "sd_xl_base_1.0.safetensors"}
            },
            "2": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt_text, "clip": ["1", 1]}
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_text, "clip": ["1", 1]}
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
                    "latent_image": ["2", 0],
                    "seed": seed if seed > 0 else int(time.time() % (2**32)),
                    "steps": steps, "cfg": cfg,
                    "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"images": ["6", 0], "filename_prefix": "simmoon"}
            }
        }
        return workflow

    def _build_img2img_workflow(self, prompt_text, negative_text, width, height, steps, cfg, seed, denoise, image_filename, ckpt_name=None):
        """Build an img2img ComfyUI workflow using LoadImage + VAEEncode."""
        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": ckpt_name or "sd_xl_base_1.0.safetensors"}
            },
            "2": {
                "class_type": "LoadImage",
                "inputs": {"image": image_filename}
            },
            "3": {
                "class_type": "ImageScale",
                "inputs": {
                    "image": ["2", 0], "upscale_method": "lanczos",
                    "width": width, "height": height, "crop": "center"
                }
            },
            "4": {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["3", 0], "vae": ["1", 2]}
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt_text, "clip": ["1", 1]}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_text, "clip": ["1", 1]}
            },
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0], "positive": ["5", 0], "negative": ["6", 0],
                    "latent_image": ["4", 0],
                    "seed": seed if seed > 0 else int(time.time() % (2**32)),
                    "steps": steps, "cfg": cfg,
                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                    "denoise": denoise
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["7", 0], "vae": ["1", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"images": ["8", 0], "filename_prefix": "simmoon_img2img"}
            }
        }
        return workflow

    def _build_img2img_controlnet_workflow(self, prompt_text, negative_text, width, height, steps, cfg, seed, denoise, image_filename, controlnet_filename, cn_module, cn_model, cn_weight, ckpt_name=None):
        """Build an img2img + ControlNet ComfyUI workflow."""
        # Map preprocessor names to ComfyUI node class types
        preprocessor_map = {
            "canny": "CannyEdgePreprocessor",
            "depth": "DepthAnythingPreprocessor",
            "depth_midas": "DepthAnythingPreprocessor",
            "lineart": "LineartPreprocessor",
            "openpose": "OpenPosePreprocessor",
            "softedge": "SoftEdgePreprocessor",
            "scribble": "FakeScribblePreprocessor",
            "mlsd": "MLSDDetectorPreprocessor",
            "normal": "NormalBaePreprocessor",
            "shuffle": "ShufflePreprocessor",
        }
        preprocessor_class = preprocessor_map.get(cn_module, "CannyEdgePreprocessor")

        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": ckpt_name or "sd_xl_base_1.0.safetensors"}
            },
            "2": {
                "class_type": "LoadImage",
                "inputs": {"image": image_filename}
            },
            "3": {
                "class_type": "ImageScale",
                "inputs": {
                    "image": ["2", 0], "upscale_method": "lanczos",
                    "width": width, "height": height, "crop": "center"
                }
            },
            "4": {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["3", 0], "vae": ["1", 2]}
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt_text, "clip": ["1", 1]}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_text, "clip": ["1", 1]}
            },
            "10": {
                "class_type": "ControlNetLoader",
                "inputs": {"control_net_name": cn_model}
            },
            "11": {
                "class_type": preprocessor_class,
                "inputs": {"image": ["3", 0]}
            },
            "12": {
                "class_type": "ControlNetApply",
                "inputs": {
                    "conditioning": ["5", 0],
                    "control_net": ["10", 0],
                    "image": ["11", 0],
                    "strength": cn_weight
                }
            },
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0], "positive": ["12", 0], "negative": ["6", 0],
                    "latent_image": ["4", 0],
                    "seed": seed if seed > 0 else int(time.time() % (2**32)),
                    "steps": steps, "cfg": cfg,
                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                    "denoise": denoise
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["7", 0], "vae": ["1", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"images": ["8", 0], "filename_prefix": "simmoon_controlnet"}
            }
        }
        return workflow

    def _upload_image(self, image_path):
        """Upload an image to ComfyUI's input folder. Returns the filename."""
        path = Path(image_path)
        try:
            with open(path, "rb") as f:
                files = {"image": (path.name, f, "image/png")}
                data = {"overwrite": "true"}
                r = requests.post(self.upload_endpoint, files=files, data=data, timeout=30)
                r.raise_for_status()
                result = r.json()
                return result.get("name", path.name)
        except requests.ConnectionError:
            print(f"  [ERROR] Could not upload to ComfyUI - server unreachable")
            raise
        except requests.RequestException as e:
            print(f"  [ERROR] Upload failed: {e}")
            raise

    def _queue_and_wait(self, workflow, timeout=180):
        """Submit a workflow and wait for completion. Returns True if image saved."""
        payload = {"prompt": workflow, "client_id": self.client_id}

        try:
            r = requests.post(self.prompt_endpoint, json=payload, timeout=30)
            r.raise_for_status()
            result = r.json()
            prompt_id = result.get("prompt_id")

            if not prompt_id:
                print(f"  [ERROR] No prompt_id returned: {result}")
                return False

            print(f"    Waiting for prompt_id: {prompt_id}")
            deadline = time.time() + timeout
            while time.time() < deadline:
                time.sleep(2)
                hist_r = requests.get(f"{self.history_endpoint}/{prompt_id}", timeout=10)
                if hist_r.status_code == 200:
                    history = hist_r.json()
                    if prompt_id in history:
                        return history[prompt_id]
            print(f"  [ERROR] Timed out waiting for ComfyUI generation")
            return False
        except Exception as e:
            print(f"  [ERROR] ComfyUI generation failed: {e}")
            return False

    def _download_result(self, history_entry, output_path):
        """Download the generated image from ComfyUI history."""
        outputs = history_entry.get("outputs", {})
        for node_id, node_output in outputs.items():
            images = node_output.get("images", [])
            if images:
                img_info = images[0]
                filename = img_info["filename"]
                subfolder = img_info.get("subfolder", "")
                img_type = img_info.get("type", "output")

                img_url = f"{self.view_endpoint}?filename={filename}&subfolder={subfolder}&type={img_type}"
                img_r = requests.get(img_url, timeout=30)
                if img_r.status_code == 200:
                    output_path = Path(output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(img_r.content)
                    return True
        return False

    def generate(self, prompt_data, output_path, category_settings=None, controlnet_config=None):
        """Standard txt2img generation."""
        if controlnet_config:
            print("  [WARN] ControlNet in txt2img mode requires img2img. Use --img2img flag.")

        settings = {**self.settings}
        if category_settings:
            settings.update(category_settings)

        workflow = self._build_txt2img_workflow(
            prompt_data["prompt"],
            prompt_data.get("negative_prompt", ""),
            settings.get("width", 512), settings.get("height", 512),
            settings.get("steps", 25), settings.get("cfg_scale", 7),
            settings.get("seed", -1)
        )

        history = self._queue_and_wait(workflow)
        if history:
            return self._download_result(history, output_path)
        return False

    def generate_img2img(self, prompt_data, output_path, input_image_path, denoising=0.6,
                         variations=1, category_settings=None, controlnet_config=None):
        """img2img generation via ComfyUI with optional ControlNet."""
        settings = {**self.settings}
        if category_settings:
            settings.update(category_settings)

        input_path = Path(input_image_path)
        if not input_path.exists():
            print(f"  [ERROR] Input image not found: {input_path}")
            return False

        # Upload source image to ComfyUI input folder
        print(f"    Uploading {input_path.name} to ComfyUI...")
        try:
            uploaded_name = self._upload_image(str(input_path))
        except Exception:
            return False

        ckpt_name = self.config.get("backends", {}).get("comfyui", {}).get("checkpoint")
        output_path = Path(output_path)
        output_dir = output_path.parent
        stem = output_path.stem

        for var_idx in range(variations):
            if variations > 1:
                print(f"    Generating variation {var_idx + 1}/{variations}...")
                var_output = output_dir / f"{stem}_var{var_idx + 1}.png"
            else:
                var_output = output_path

            if controlnet_config:
                # Use ControlNet workflow
                cn_image_path = controlnet_config.get("image", input_image_path)
                cn_image_name = Path(cn_image_path).name
                if cn_image_path != input_image_path:
                    print(f"    Uploading ControlNet image: {cn_image_name}...")
                    try:
                        cn_image_name = self._upload_image(cn_image_path)
                    except Exception:
                        print("    [WARN] ControlNet image upload failed, skipping ControlNet")
                        cn_image_name = None
                else:
                    cn_image_name = uploaded_name

                if cn_image_name:
                    workflow = self._build_img2img_controlnet_workflow(
                        prompt_data["prompt"],
                        prompt_data.get("negative_prompt", ""),
                        settings.get("width", 512), settings.get("height", 512),
                        settings.get("steps", 25), settings.get("cfg_scale", 7),
                        -1, denoising, uploaded_name, cn_image_name,
                        controlnet_config.get("module", "canny"),
                        controlnet_config.get("model", "control_v11p_sd15_canny.pth"),
                        controlnet_config.get("weight", 1.0),
                        ckpt_name=ckpt_name
                    )
                    print(f"    ControlNet: {controlnet_config.get('module', 'canny')} / {controlnet_config.get('model', 'default')}")
                else:
                    # Fallback to regular img2img
                    workflow = self._build_img2img_workflow(
                        prompt_data["prompt"],
                        prompt_data.get("negative_prompt", ""),
                        settings.get("width", 512), settings.get("height", 512),
                        settings.get("steps", 25), settings.get("cfg_scale", 7),
                        -1, denoising, uploaded_name, ckpt_name=ckpt_name
                    )
            else:
                workflow = self._build_img2img_workflow(
                    prompt_data["prompt"],
                    prompt_data.get("negative_prompt", ""),
                    settings.get("width", 512), settings.get("height", 512),
                    settings.get("steps", 25), settings.get("cfg_scale", 7),
                    -1, denoising, uploaded_name, ckpt_name=ckpt_name
                )

            history = self._queue_and_wait(workflow)
            if history:
                self._download_result(history, var_output)
            else:
                print(f"    [WARN] Variation {var_idx + 1} failed")

        return output_path.exists() or any(
            (output_dir / f"{stem}_var{i+1}.png").exists()
            for i in range(variations)
        )


# --- HuggingFace Backend ---------------------------------------------------

class HuggingFaceBackend:
    """Connects to HuggingFace Inference API for image generation.

    Uses the serverless Inference API with SDXL or SD 1.5 models.
    Supports full parameter control: negative prompts, guidance, steps, size.
    Includes automatic retry with backoff for rate limits and model loading.
    """

    MAX_RETRIES = 4

    def __init__(self, config):
        self.model = config["backends"]["huggingface"]["model"]
        self.url = config["backends"]["huggingface"]["url_template"].format(model=self.model)
        api_key_env = config["backends"]["huggingface"]["api_key_env"]
        self.api_key = os.environ.get(api_key_env, "")
        self.settings = config["image_settings"]
        self.negative_prompt = config["negative_prompt"]
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def check_connection(self):
        if not self.api_key:
            print("  [!] No HF API key found. Set HF_API_KEY environment variable.")
            print("  [!] Get token at: https://huggingface.co/settings/tokens")
            return False
        try:
            r = requests.get(
                f"https://huggingface.co/api/models/{self.model}",
                headers=self.headers,
                timeout=10
            )
            return r.status_code == 200
        except requests.ConnectionError:
            return False

    def _build_payload(self, prompt_data, settings):
        """Build HuggingFace Inference API payload with full parameters."""
        payload = {
            "inputs": prompt_data["prompt"],
            "parameters": {
                "negative_prompt": prompt_data.get("negative_prompt", self.negative_prompt),
                "guidance_scale": settings.get("cfg_scale", 7),
                "num_inference_steps": settings.get("steps", 25),
                "width": settings.get("width", 1024),
                "height": settings.get("height", 1024),
            }
        }
        return payload

    def _request_with_retry(self, payload, max_retries=None):
        """Send request with retry logic for 503 (loading) and 429 (rate limit)."""
        if max_retries is None:
            max_retries = self.MAX_RETRIES

        for attempt in range(max_retries + 1):
            try:
                r = requests.post(self.url, headers=self.headers, json=payload, timeout=120)

                if r.status_code == 200:
                    return r.content

                if r.status_code == 503:
                    info = r.json()
                    wait_time = info.get("estimated_time", 30)
                    print(f"    Model loading, waiting {wait_time:.0f}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(min(wait_time, 60))
                    continue

                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", 30))
                    print(f"    Rate limited, waiting {retry_after}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_after)
                    continue

                # Other errors - don't retry
                print(f"  [ERROR] HF API returned {r.status_code}: {r.text[:200]}")
                return None

            except requests.ConnectionError:
                print(f"  [ERROR] HF API connection failed (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                return None
            except Exception as e:
                print(f"  [ERROR] HF generation failed: {e}")
                return None

        print(f"  [ERROR] HF API: exhausted {max_retries} retries")
        return None

    def generate(self, prompt_data, output_path, category_settings=None, controlnet_config=None):
        """Standard txt2img generation via HuggingFace API."""
        settings = {**self.settings}
        if category_settings:
            settings.update(category_settings)

        payload = self._build_payload(prompt_data, settings)

        print(f"    Sending request to HF API (model: {self.model})...")
        image_bytes = self._request_with_retry(payload)

        if image_bytes:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            return True
        return False

    def generate_img2img(self, prompt_data, output_path, input_image_path, denoising=0.6,
                         variations=1, category_settings=None, controlnet_config=None):
        """HuggingFace serverless API does not support img2img."""
        print("  [WARN] HuggingFace serverless API does not support img2img.")
        print("  [HINT] Use ComfyUI for img2img generation.")
        return False


# --- Standalone Single Generation (for Telegram bot /gen) -------------------

def generate_single(prompt: str, backend: str = "comfyui",
                    width: int = 512, height: int = 512,
                    steps: int = 20, cfg: float = 7.0,
                    output_dir: str = None, seed: int = -1,
                    negative_prompt: str = "") -> dict:
    """Generate a single image — used by Telegram bot /gen command.

    Args:
        prompt: The image generation prompt
        backend: "comfyui" or "huggingface"
        width, height: Output dimensions
        steps: Inference steps
        cfg: CFG scale
        output_dir: Directory for output (default: SCRIPT_DIR / 'generated')
        seed: Random seed (-1 = random)
        negative_prompt: Optional negative prompt

    Returns:
        dict with keys: success, image_path, backend, prompt, error (if failed)
    """
    import re

    config = load_config()
    script_dir = Path(__file__).parent.resolve()

    # Output directory
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = script_dir / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prompt = re.sub(r'[<>:"/\\|?*\s]', '_', prompt[:30])
    output_path = out_dir / f"gen_{timestamp}_{safe_prompt}.png"

    prompt_data = {
        "prompt": prompt,
        "negative_prompt": negative_prompt or config.get("negative_prompt", ""),
    }

    try:
        if backend == "comfyui":
            be = ComfyUIBackend(config)
            success = be.generate(prompt_data, str(output_path), category_settings={
                "width": width, "height": height,
                "steps": steps, "cfg_scale": cfg, "seed": seed,
            })
        elif backend == "huggingface":
            be = HuggingFaceBackend(config)
            success = be.generate(prompt_data, str(output_path), category_settings={
                "width": width, "height": height,
                "steps": steps, "cfg_scale": cfg,
            })
        else:
            return {"success": False, "error": f"Backend desconocido: {backend}"}

        if success and output_path.exists():
            return {
                "success": True,
                "image_path": str(output_path),
                "backend": backend,
                "prompt": prompt,
                "width": width,
                "height": height,
            }
        else:
            return {"success": False, "error": "Generación falló — el backend no devolvió imagen"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Generator Orchestrator ------------------------------------------------

class SimmoonGenerator:
    """Orchestrates image generation across all categories and backends."""

    def __init__(self, backend_name, categories=None, dry_run=False,
                 img2img=False, input_image=None, denoising=0.6, variations=1,
                 controlnet_config=None, refine_denoising=0.4,
                 refine_variations=2):
        self.config = load_config()
        self.prompts_data = load_prompts()
        self.dry_run = dry_run
        self.categories = categories
        self.img2img = img2img
        self.input_image = input_image
        self.denoising = denoising
        self.variations = variations
        self.controlnet_config = controlnet_config

        self.refine_denoising = refine_denoising
        self.refine_variations = refine_variations
        self.stats = {"generated": 0, "failed": 0, "skipped": 0}

        # Initialize backend
        if backend_name == "comfyui":
            self.backend = ComfyUIBackend(self.config)
            self.backend_name = "ComfyUI"
        elif backend_name == "huggingface":
            self.backend = HuggingFaceBackend(self.config)
            self.backend_name = "HuggingFace"
        else:
            print(f"Unknown backend: {backend_name}")
            sys.exit(1)

    def run(self):
        print("=" * 70)
        mode = "img2img" if self.img2img else "txt2img"
        print(f"  SIMMOON Image Generator - Backend: {self.backend_name} ({mode})")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        sys.stdout.flush()

        if self.img2img:
            print(f"\n[*] img2img mode enabled")
            print(f"    Source image: {self.input_image}")
            print(f"    Denoising strength: {self.denoising}")
            print(f"    Variations per prompt: {self.variations}")

        # Check connection
        if not self.dry_run:
            print(f"\n[*] Checking {self.backend_name} connection...")
            if self.backend.check_connection():
                print(f"  [OK] {self.backend_name} is running and accessible.")
            else:
                print(f"  [FAIL] Cannot connect to {self.backend_name}.")
                if self.backend_name == "A1111":
                    print("  => Start A1111 with: python launch.py --api")
                    print(f"  => Expected at: {self.config['backends']['a1111']['url']}")
                elif self.backend_name == "ComfyUI":
                    print("  => Start ComfyUI: python main.py")
                    print(f"  => Expected at: {self.config['backends']['comfyui']['url']}")
                elif self.backend_name == "HuggingFace":
                    print("  => Set HF_API_KEY environment variable")
                    print("  => Get key at: https://huggingface.co/settings/tokens")
                return

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
        for cat_name, cat_data in categories.items():
            print(f"\n{'-' * 50}")
            print(f"  Category: {cat_name} ({len(cat_data['prompts'])} images)")
            print(f"  Output: {cat_data['output_dir']}")
            print(f"{'-' * 50}")

            output_dir = SCRIPT_DIR / cat_data["output_dir"].replace("Simmoon_arc/", "")
            game_settings = self.config.get("game_asset_settings", {}).get(cat_name, {})

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

                if self.img2img:
                    success = self.backend.generate_img2img(
                        prompt_item, output_path, self.input_image,
                        denoising=self.denoising, variations=self.variations,
                        category_settings=game_settings,
                        controlnet_config=self.controlnet_config
                    )
                else:
                    success = self.backend.generate(
                        prompt_item, output_path, game_settings,
                        controlnet_config=self.controlnet_config
                    )

                if success:
                    if self.img2img and self.variations > 1:
                        self.stats["generated"] += self.variations
                        print(f"    [OK] Generated {self.variations} variations")
                    else:
                        self.stats["generated"] += 1
                        print(f"    [OK] Saved: {filename}")
                else:
                    self.stats["failed"] += 1
                    print(f"    [FAIL] Could not generate: {filename}")

                # Rate limiting
                time.sleep(1)

        self._print_summary()

    def _dry_run(self, categories):
        print("\n[DRY RUN MODE] - Listing all prompts without generating.\n")
        total = 0
        for cat_name, cat_data in categories.items():
            print(f"\n{'=' * 60}")
            print(f"  CATEGORY: {cat_name}")
            print(f"  Output dir: {cat_data['output_dir']}")
            print(f"{'=' * 60}")
            for p in cat_data["prompts"]:
                total += 1
                print(f"\n  [{p['id']}] {p['name']}")
                print(f"    Prompt: {p['prompt'][:100]}...")
                if p.get("negative_prompt"):
                    print(f"    Negative: {p['negative_prompt'][:80]}...")
            print()
        print(f"\n[DRY RUN] Total prompts: {total}")
        print("[DRY RUN] No images were generated.")

    def batch_refine(self):
        """Scan all category output dirs for existing PNGs and run img2img on each."""
        print("=" * 70)
        print(f"  SIMMOON Batch Refine - Backend: {self.backend_name}")
        print(f"  Denoising: {self.refine_denoising} | Variations: {self.refine_variations}")
        print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        sys.stdout.flush()

        # Check connection
        if not self.dry_run:
            print(f"\n[*] Checking {self.backend_name} connection...")
            if self.backend.check_connection():
                print(f"  [OK] {self.backend_name} is running and accessible.")
            else:
                print(f"  [FAIL] Cannot connect to {self.backend_name}.")
                return

        # Build filename -> prompt_data lookup (avoids fragile ID extraction)
        prompts_data = load_prompts()
        filename_lookup = {}
        categories = prompts_data["categories"]
        if self.categories:
            categories = {k: v for k, v in categories.items() if k in self.categories}

        for cat_name, cat_data in categories.items():
            game_settings = self.config.get("game_asset_settings", {}).get(cat_name, {})
            for p in cat_data["prompts"]:
                fname = f"{p['id']}_{p['name'].lower().replace(' ', '_').replace('-', '_')}.png"
                filename_lookup[fname] = (cat_name, cat_data, p, game_settings)

        # Scan all category output directories for existing PNGs
        print("\n[*] Scanning for existing generated images...")
        images_to_refine = []

        for cat_name, cat_data in categories.items():
            output_dir = SCRIPT_DIR / cat_data["output_dir"].replace("Simmoon_arc/", "")
            if not output_dir.exists():
                continue

            for png_file in sorted(output_dir.glob("*.png")):
                # Skip already-refined files (variations)
                if "_var" in png_file.stem:
                    continue

                # Match filename to prompt data
                if png_file.name in filename_lookup:
                    cat_name_found, cat_data_found, prompt_item, game_settings = filename_lookup[png_file.name]
                    images_to_refine.append({
                        "image_path": png_file,
                        "prompt_data": prompt_item,
                        "category_settings": game_settings,
                        "category": cat_name_found,
                    })

        if not images_to_refine:
            print("  [WARN] No generated images found to refine.")
            print("  [HINT] Run txt2img generation first with: python simmoon_generator.py -b a1111")
            return

        total = len(images_to_refine)
        total_variants = total * self.refine_variations
        print(f"  Found {total} images to refine ({total_variants} total variations)")
        print(f"  Denoising: {self.refine_denoising} | Variations per image: {self.refine_variations}")

        if self.dry_run:
            print("\n[DRY RUN MODE] - Listing images that would be refined:\n")
            for i, item in enumerate(images_to_refine, 1):
                print(f"  [{i}/{total}] {item['image_path'].name}")
                print(f"    Prompt: {item['prompt_data']['prompt'][:80]}...")
                print(f"    Output: {item['category']}/\n")
            print(f"[DRY RUN] Would refine {total} images into {total_variants} variations.")
            return

        # Process each image
        current = 0
        start_time = time.time()
        for item in images_to_refine:
            current += 1
            img_path = item["image_path"]
            prompt_item = item["prompt_data"]
            game_settings = item["category_settings"]

            print(f"\n  [{current}/{total}] Refining: {img_path.name}")
            print(f"    Prompt: {prompt_item['prompt'][:70]}...")

            # Build output path: same name in a 'refined' subfolder
            refined_dir = img_path.parent / "refined"
            refined_path = refined_dir / img_path.name

            if self.refine_variations == 1 and refined_path.exists():
                print(f"    [SKIP] Already refined: {refined_path.name}")
                self.stats["skipped"] += 1
                continue
            elif self.refine_variations > 1:
                existing = list(refined_dir.glob(f"{img_path.stem}_var*.png"))
                if len(existing) >= self.refine_variations:
                    print(f"    [SKIP] Already has {len(existing)} variations")
                    self.stats["skipped"] += self.refine_variations
                    continue

            success = self.backend.generate_img2img(
                prompt_item, refined_path, str(img_path),
                denoising=self.refine_denoising,
                variations=self.refine_variations,
                category_settings=game_settings
            )

            if success:
                self.stats["generated"] += self.refine_variations
                print(f"    [OK] Refined {self.refine_variations} variations")
            else:
                self.stats["failed"] += 1
                print(f"    [FAIL] Could not refine: {img_path.name}")

            # Rate limiting
            time.sleep(1)

        elapsed = time.time() - start_time
        print(f"\n[*] Batch refine completed in {elapsed / 60:.1f} minutes")
        self._print_summary()

    def _print_summary(self):
        print(f"\n{'=' * 70}")
        print(f"  GENERATION COMPLETE")
        print(f"{'=' * 70}")
        print(f"  Generated: {self.stats['generated']}")
        print(f"  Failed:    {self.stats['failed']}")
        print(f"  Skipped:   {self.stats['skipped']}")
        print(f"  Total:     {self.stats['generated'] + self.stats['failed'] + self.stats['skipped']}")
        print(f"{'=' * 70}")


# --- Main Entry Point ------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON Image Generator - Generate game assets for lunar colony sim",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (txt2img):
  python simmoon_generator.py --backend comfyui
  python simmoon_generator.py --backend comfyui --category businesses vehicles
  python simmoon_generator.py --backend huggingface --category greenhouses

Examples (img2img):
  python simmoon_generator.py --backend comfyui --img2img -i img.png --denoising 0.5 --variations 3

Other:
  python simmoon_generator.py --dry-run
  python simmoon_generator.py --list-categories
        """
    )

    parser.add_argument(
        "--backend", "-b",
        choices=["comfyui", "huggingface"],
        default="comfyui",
        help="Image generation backend (default: comfyui)"
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

    # img2img options
    parser.add_argument(
        "--img2img",
        action="store_true",
        help="Enable img2img mode: refine an existing image with prompts"
    )
    parser.add_argument(
        "--input-image", "-i",
        type=str,
        default=None,
        help="Path to source image for img2img mode"
    )
    parser.add_argument(
        "--denoising",
        type=float,
        default=0.6,
        help="Denoising strength for img2img (0.0=preserve, 1.0=full regen, default: 0.6)"
    )
    parser.add_argument(
        "--variations", "-v",
        type=int,
        default=1,
        help="Number of img2img variations to generate per prompt (default: 1)"
    )

    # ControlNet options
    parser.add_argument(
        "--controlnet",
        action="store_true",
        help="Enable ControlNet for structural guidance (requires --controlnet-image)"
    )
    parser.add_argument(
        "--controlnet-image",
        type=str,
        default=None,
        help="Path to ControlNet control image (edge map, depth map, pose, etc.)"
    )
    parser.add_argument(
        "--cn-module",
        type=str,
        default="canny",
        choices=["canny", "depth", "lineart", "openpose", "softedge", "scribble", "mlsd", "normal", "shuffle"],
        help="ControlNet preprocessor module (default: canny)"
    )
    parser.add_argument(
        "--cn-model",
        type=str,
        default=None,
        help="ControlNet model name (auto-detected if not specified)"
    )
    parser.add_argument(
        "--cn-weight",
        type=float,
        default=1.0,
        help="ControlNet influence weight 0.0-2.0 (default: 1.0)"
    )
    parser.add_argument(
        "--list-controlnet",
        action="store_true",
        help="List available ControlNet models and modules"
    )

    # Batch refine options
    parser.add_argument(
        "--batch-refine",
        action="store_true",
        help="Batch refine: scan for existing txt2img images and run img2img on each"
    )
    parser.add_argument(
        "--refine-denoising",
        type=float,
        default=0.4,
        help="Denoising strength for batch refine (default: 0.4)"
    )
    parser.add_argument(
        "--refine-variations",
        type=int,
        default=2,
        help="Number of img2img variations per image in batch refine (default: 2)"
    )

    args = parser.parse_args()

    # Validate img2img args
    if args.img2img and not args.input_image:
        parser.error("--img2img requires --input-image (-i) to specify the source image")
    if args.input_image and not Path(args.input_image).exists():
        parser.error(f"Input image not found: {args.input_image}")
    if not 0.0 <= args.denoising <= 1.0:
        parser.error("--denoising must be between 0.0 and 1.0")

    # Validate ControlNet args
    if args.controlnet and not args.controlnet_image:
        parser.error("--controlnet requires --controlnet-image to specify the control image")
    if args.controlnet_image and not Path(args.controlnet_image).exists():
        parser.error(f"ControlNet image not found: {args.controlnet_image}")
    if not 0.0 <= args.cn_weight <= 2.0:
        parser.error("--cn-weight must be between 0.0 and 2.0")

    # Validate batch-refine args
    if not 0.0 <= args.refine_denoising <= 1.0:
        parser.error("--refine-denoising must be between 0.0 and 1.0")
    if args.refine_variations < 1:
        parser.error("--refine-variations must be at least 1")

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

    # List ControlNet models/modules (deprecated - ComfyUI handles ControlNet natively)
    if args.list_controlnet:
        print("\n[INFO] ControlNet is handled natively by ComfyUI workflows.")
        print("  Use ComfyUI's node editor or generate_comfyui.py for ControlNet.")
        return

    # Build ControlNet config
    controlnet_config = None
    if args.controlnet:
        controlnet_config = {
            "image": args.controlnet_image,
            "module": args.cn_module,
            "model": args.cn_model or "control_v11p_sd15_canny [d14c016b]",
            "weight": args.cn_weight,
            "pixel_perfect": True,
        }
        if args.cn_model:
            controlnet_config["model"] = args.cn_model

    generator = SimmoonGenerator(
        backend_name=args.backend,
        categories=args.category,
        dry_run=args.dry_run,
        img2img=args.img2img,
        input_image=args.input_image,
        denoising=args.denoising,
        variations=args.variations,
        controlnet_config=controlnet_config,
        refine_denoising=args.refine_denoising,
        refine_variations=args.refine_variations,
    )

    if args.batch_refine:
        generator.batch_refine()
    else:
        generator.run()


if __name__ == "__main__":
    main()
