#!/usr/bin/env python3
"""
SIMMOOM ↔ Hermes Bridge — Conecta los agentes de Simmoon a Hermes Agent.

Hermes (Nous Research) maneja tool calling de forma nativa. Este módulo
usa `hermes chat` via subprocess para enviar prompts y recibir respuestas.

Usage:
    from hermes_bridge import HermesBridge

    bridge = HermesBridge()
    response = bridge.chat("Genera assets para businesses con dreamshaper_8")
    print(response)
"""

import json
import os
import random
import subprocess
import tempfile
from pathlib import Path
from shutil import which

# ── Configuration ──────────────────────────────────────────────────────────

HERMES_DEFAULT_MODEL = "qwen2.5:3b"
WSL_DISTRO = "Ubuntu"

# Common hermes binary locations
_COMMON_PATHS = [
    os.path.expanduser("~/.local/bin/hermes"),
    "/usr/local/bin/hermes",
]


def _find_hermes():
    """Find the hermes binary. Returns the filesystem path or None.

    Tries:
      1. WSL2 (runs detection inside the WSL distro)
      2. Common hardcoded paths (for when already inside WSL2)
      3. Native PATH scan
      4. shutil.which
    """
    # 1. WSL2 detection (when running from Windows)
    try:
        result = subprocess.run(
            ["wsl", "-d", WSL_DISTRO, "--", "bash", "-c",
             "test -x ~/.local/bin/hermes && echo WSL_READY || echo WSL_NOT_FOUND"],
            capture_output=True, text=True, timeout=10,
        )
        if "WSL_READY" in result.stdout:
            return "wsl:~/.local/bin/hermes"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # Not on Windows with WSL, or already inside WSL

    # 2. Common hardcoded paths (works when running inside WSL2)
    for p in _COMMON_PATHS:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p

    # 3. Native PATH scan
    for d in os.environ.get("PATH", "").split(os.pathsep):
        for name in ("hermes", "hermes.exe"):
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

    # 4. shutil.which as last resort
    return which("hermes")


# ── Bridge Class ───────────────────────────────────────────────────────────

class HermesBridge:
    """Bridge to Hermes Agent for tool-enabled chat via CLI."""

    def __init__(self, model=None, verbose=False):
        """
        Args:
            model: Override default model (default: gemma3-64k)
            verbose: Print debug info
        """
        self.model = model or HERMES_DEFAULT_MODEL
        self.verbose = verbose
        self._hermes_path = None

    @property
    def hermes_path(self):
        if self._hermes_path is None:
            self._hermes_path = _find_hermes()
        return self._hermes_path

    def _wsl_write_file(self, path: str, content: str) -> bool:
        """Write a text file inside WSL from Windows using the \\wsl$ UNC path.

        Uses binary mode + LF-only newlines to avoid Windows CRLF translation
        breaking Linux shebangs (e.g., /bin/bash^M).
        """
        try:
            unc_path = f"\\\\wsl.localhost\\{WSL_DISTRO}\\{path.lstrip('/').replace('/', '\\\\')}"
            # Binary mode + LF-only newlines evita CRLF translation de Windows
            content_lf = content.replace('\r\n', '\n').replace('\r', '\n')
            with open(unc_path, 'wb') as f:
                f.write(content_lf.encode('utf-8'))
            return True
        except Exception as e:
            if self.verbose:
                print(f"[BRIDGE] WSL write failed: {e}")
            return False

    def _wsl_delete_file(self, path: str):
        """Delete a file inside WSL via the \\wsl$ UNC path."""
        try:
            unc_path = f"\\\\wsl.localhost\\{WSL_DISTRO}\\{path.lstrip('/').replace('/', '\\\\')}"
            if os.path.exists(unc_path):
                os.unlink(unc_path)
        except Exception:
            pass

    def chat(self, prompt, system=None, max_turns=10, timeout=180):
        """Send a prompt to Hermes and get the response.

        Hermes handles tool calling internally — the response already
        includes any tool execution results.

        Query is passed via a temp file (\\wsl$ UNC mount) to avoid
        shell escaping bugs with long or complex prompts.

        Args:
            prompt: User prompt text
            system: Optional system message (prepended to prompt)
            max_turns: Max tool-calling turns in Hermes (default 10)
            timeout: Max seconds to wait

        Returns:
            str: Final response text (after any internal tool calls)
        """
        hp = self.hermes_path
        if not hp:
            return "[ERROR] Hermes binary not found. Install Hermes Agent first."

        # Build query — prepend system message if provided
        query = prompt
        if system:
            query = f"{system}\n\n---\n\n{prompt}"

        try:
            if hp.startswith("wsl:"):
                # ── WSL MODE: write wrapper script a /tmp via \\wsl$ UNC, ejecutar ──
                inner_path = hp.split(":", 1)[1]
                rand = random.randint(10000, 99999)
                wrapper_sh = f"/tmp/hermes_wrapper_{rand}.sh"

                try:
                    # Escape query para bash single-quotes: ' -> '\\''
                    # Single quotes evitan TODO shell expansion
                    escaped_query = query.replace("'", "'\\''")
                    wrapper_content = (
                        f"#!/bin/bash\n"
                        f"exec {inner_path} chat --model {self.model} --cli "
                        f"--max-turns {max_turns} --query '{escaped_query}'\n"
                    )

                    if self.verbose:
                        print(f"[BRIDGE] Writing wrapper to {wrapper_sh} ({len(query)} chars in query)...")

                    ok = self._wsl_write_file(wrapper_sh, wrapper_content)
                    if not ok:
                        return "[ERROR] Could not write wrapper script to WSL."

                    # chmod +x && execute
                    runner_cmd = f"chmod +x {wrapper_sh} && {wrapper_sh}"
                    if self.verbose:
                        print(f"[BRIDGE] Running: {inner_path} chat --model {self.model} --cli --max-turns {max_turns} --query '...'")

                    result = subprocess.run(
                        ["wsl", "-d", WSL_DISTRO, "--", "bash", "-c", runner_cmd],
                        capture_output=True, text=False,
                        timeout=timeout,
                    )
                finally:
                    # Clean up wrapper script siempre, incluso si hay excepcion
                    self._wsl_delete_file(wrapper_sh)
            else:
                # ── NATIVE MODE: write local temp file, run via stdin redirect ──
                rand = random.randint(10000, 99999)
                tmp_native = os.path.join(
                    tempfile.gettempdir(), f"hermes_query_{rand}.txt"
                )
                try:
                    with open(tmp_native, 'w', encoding='utf-8') as f:
                        f.write(query)

                    cmd = [
                        hp, "chat",
                        "--model", self.model,
                        "--cli",
                        "--max-turns", str(max_turns),
                    ]
                    if self.verbose:
                        print(f"[BRIDGE] Running (native): {hp} chat...")

                    with open(tmp_native, 'r', encoding='utf-8') as f:
                        result = subprocess.run(
                            cmd, stdin=f,
                            capture_output=True, text=False,  # text=False -> read raw bytes
                            timeout=timeout,
                        )
                finally:
                    try:
                        os.unlink(tmp_native)
                    except Exception:
                        pass

            # Manual decode with errors='replace' to handle non-UTF-8 output
            stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
            stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""

            if result.returncode == 0:
                return stdout.strip()
            else:
                return (
                    f"[ERROR] Hermes exit {result.returncode}: "
                    f"{stderr[:500]}"
                )
        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] Hermes chat exceeded {timeout}s."
        except FileNotFoundError:
            return f"[ERROR] Hermes binary not found: {hp}"
        except Exception as e:
            return f"[ERROR] {e}"

    def status(self):
        """Returns dict with bridge status info."""
        hp = self.hermes_path or "NOT FOUND"
        return {
            "hermes_path": hp,
            "default_model": self.model,
            "status": "ready" if self.hermes_path else "missing binary",
        }


# ── Quick Test ─────────────────────────────────────────────────────────────

def test_bridge():
    """Quick connectivity test."""
    bridge = HermesBridge(verbose=True)
    status = bridge.status()
    print("Hermes Bridge Status:")
    print(json.dumps(status, indent=2, ensure_ascii=False))

    if not bridge.hermes_path:
        print("\nHermes binary not found. Install Hermes Agent first.")
        return

    print("\nTesting chat...")
    response = bridge.chat(
        "Di 'Hola desde Simmoon!' en una frase.",
        system="Eres un asistente conciso. Responde en español.",
        max_turns=3, timeout=300,
    )
    print(f"Response: {response}")


if __name__ == "__main__":
    test_bridge()
