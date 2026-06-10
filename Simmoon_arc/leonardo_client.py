#!/usr/bin/env python3
"""
Leonardo.ai REST Client — Pure HTTP, no SDK dependency.
Uses standard library (urllib) + requests when available.

Authentication: LEONARDO_API_KEY environment variable.
API docs: https://docs.leonardo.ai/

Usage:
    from leonardo_client import LeonardoClient
    client = LeonardoClient()
    img_data = client.generate(prompt="isometric lunar colony...", width=512, height=512)
    client.save_image(img_data, "output.png")
"""

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

# Try requests first, fall back to urllib
try:
    import requests as _requests

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


class LeonardoClient:
    """Pure REST client for Leonardo.ai image generation API."""

    API_BASE = "https://cloud.leonardo.ai/api/rest/v1"
    GENERATIONS = f"{API_BASE}/generations"

    # Default model IDs (may change — update as needed)
    DEFAULT_MODEL_ID = None  # Uses Leonardo's default model
    # Common options: "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3" (Phoenix)
    #                "b24e16ff-06e3-43eb-8d33-4416c2d75876" (Leonardo Creative)

    def __init__(
        self,
        api_key: str = "",
        default_width: int = 512,
        default_height: int = 512,
        default_num_images: int = 1,
        max_wait: int = 300,
        poll_interval: int = 3,
    ):
        """Initialize Leonardo client.

        Args:
            api_key: API key string. If empty, reads LEONARDO_API_KEY env var.
            default_width: Default image width.
            default_height: Default image height.
            default_num_images: Default number of images per generation.
            max_wait: Maximum seconds to wait for generation completion.
            poll_interval: Seconds between status checks.
        """
        self.api_key = api_key or os.environ.get("LEONARDO_API_KEY", "")
        self.default_width = default_width
        self.default_height = default_height
        self.default_num_images = default_num_images
        self.max_wait = max_wait
        self.poll_interval = poll_interval

    # ── Auth & HTTP helpers ──────────────────────────────────────────────

    @property
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, url: str, payload: dict) -> dict:
        """HTTP POST — uses requests if available, urllib fallback."""
        data = json.dumps(payload).encode("utf-8")
        headers = self._headers()

        if _HAS_REQUESTS:
            resp = _requests.post(url, data=data, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.json()

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    def _get(self, url: str) -> dict:
        """HTTP GET."""
        headers = self._headers()

        if _HAS_REQUESTS:
            resp = _requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    @staticmethod
    def _download(url: str) -> bytes:
        """Download image bytes from URL."""
        if _HAS_REQUESTS:
            resp = _requests.get(url, timeout=60)
            resp.raise_for_status()
            return resp.content

        req = urllib.request.Request(url, headers={"User-Agent": "SIMMOON/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    # ── Health Check ─────────────────────────────────────────────────────

    def check_connection(self) -> bool:
        """Quick connectivity test — checks if API key is valid.

        Returns True if API key is set (actual validation happens on generation).
        """
        if not self.is_configured:
            return False
        return True

    # ── Generation ───────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 0,
        height: int = 0,
        model_id: Optional[str] = None,
        num_images: int = 0,
        alchemy: bool = True,
        preset_style: str = "",
        wait: bool = True,
        max_wait: int = 0,
        poll_interval: int = 0,
    ) -> Tuple[str, list[str]]:
        """Generate images via Leonardo.ai API.

        Args:
            prompt: Positive text prompt.
            negative_prompt: Negative prompt (things to avoid).
            width: Image width (defaults to self.default_width).
            height: Image height (defaults to self.default_height).
            model_id: Leonardo model UUID (None = default).
            num_images: Number of images (defaults to self.default_num_images).
            alchemy: Enable Leonardo Alchemy enhancement.
            preset_style: Optional style preset (e.g. "DYNAMIC", "CREATIVE").
            wait: If True, poll until generation completes. If False, return
                  generation_id immediately for async workflow.

        Returns:
            Tuple of (generation_id, [image_urls]).

        Raises:
            RuntimeError: If API key not set or generation fails.
            TimeoutError: If generation exceeds max_wait.
        """
        if not self.is_configured:
            raise RuntimeError(
                "Leonardo API key not configured. "
                "Export LEONARDO_API_KEY or pass api_key to constructor."
            )

        w = width or self.default_width
        h = height or self.default_height
        n = num_images or self.default_num_images

        payload = {
            "prompt": prompt,
            "width": w,
            "height": h,
            "num_images": n,
            "alchemy": alchemy,
        }

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if model_id:
            payload["modelId"] = model_id
        if preset_style:
            payload["presetStyle"] = preset_style

        # Submit generation
        result = self._post(self.GENERATIONS, payload)

        sd_job = result.get("sdGenerationJob", {})
        generation_id = sd_job.get("generationId", "")
        if not generation_id:
            raise RuntimeError(f"No generationId in response: {result}")

        if not wait:
            return generation_id, []

        # Use per-call overrides or instance defaults
        poll_wait = poll_interval or self.poll_interval
        total_wait = max_wait or self.max_wait

        return generation_id, self._poll(generation_id, poll_wait, total_wait)

    def _poll(self, generation_id: str, poll_interval: int = 3, max_wait: int = 300) -> list[str]:
        """Poll /generations/{id} until COMPLETE or FAILED."""
        url = f"{self.GENERATIONS}/{generation_id}"
        start = time.time()

        while time.time() - start < max_wait:
            resp = self._get(url)

            gen = resp.get("generations_by_pk")
            if gen is None:
                time.sleep(poll_interval)
                continue

            status = gen.get("status", "PENDING")

            if status == "COMPLETE":
                images = gen.get("generated_images", [])
                return [img.get("url", "") for img in images if img.get("url")]

            if status in ("FAILED", "ERROR"):
                failure_reason = gen.get("failureReason", "Unknown error")
                raise RuntimeError(f"Generation {generation_id} failed: {failure_reason}")

            time.sleep(poll_interval)

        raise TimeoutError(
            f"Generation {generation_id} did not complete within {max_wait}s"
        )

    # ── Download helpers ─────────────────────────────────────────────────

    def download_image(self, url: str, output_path: str) -> str:
        """Download image from URL and save to output_path.

        Args:
            url: Image URL from generation result.
            output_path: Local file path to save.

        Returns:
            The output_path.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        data = self._download(url)
        with open(output_path, "wb") as f:
            f.write(data)
        return output_path

    def generate_and_save(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: str = "",
        width: int = 0,
        height: int = 0,
        num_images: int = 0,
        model_id: Optional[str] = None,
        alchemy: bool = True,
        preset_style: str = "",
        max_wait: int = 0,
    ) -> str:
        """Generate and save in one call. Returns output_path on success.

        Raises RuntimeError on failure.
        """
        gen_id, urls = self.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_images=num_images,
            model_id=model_id,
            alchemy=alchemy,
            preset_style=preset_style,
            wait=True,
            max_wait=max_wait,
        )

        if not urls:
            raise RuntimeError(f"Generation {gen_id} returned no image URLs")

        return self.download_image(urls[0], output_path)


# ── Quick test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    client = LeonardoClient()

    if not client.is_configured:
        print("⚠️  LEONARDO_API_KEY not set. Set it to test:")
        print("   export LEONARDO_API_KEY='your_key_here'")
        print("   Get a key: https://app.leonardo.ai → API Access")
        sys.exit(0)

    print("✅ Leonardo client configured")
    print(f"   Max wait: {client.max_wait}s")
    print(f"   Default size: {client.default_width}x{client.default_height}")

    # Quick connectivity check
    print("\n[TEST] Quick generation test...")
    try:
        gen_id, urls = client.generate(
            prompt="simple 2.5D isometric pixel art game sprite, clean black outline",
            width=256,
            height=256,
            max_wait=60,
        )
        if urls:
            print(f"  ✅ Generation {gen_id}: {len(urls)} image(s)")
            out = client.download_image(urls[0], "leonardo_test_output.png")
            print(f"  📁 Saved: {out}")
        else:
            print(f"  Generation {gen_id} submitted (async)")
    except Exception as e:
        print(f"  ❌ Error: {e}")
