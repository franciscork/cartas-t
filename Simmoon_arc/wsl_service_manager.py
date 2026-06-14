#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMMOON — WSL Service Manager
Ensures Ollama and ComfyUI are running in persistent WSL tmux sessions.

Usage:
    from wsl_service_manager import ensure_ollama, ensure_comfyui, ensure_all_services
    
    # Called by the bot before making requests:
    if ensure_all_services():
        # Both services are up, proceed
        ...

CLI:
    python wsl_service_manager.py start    # Start both services
    python wsl_service_manager.py stop     # Stop both services
    python wsl_service_manager.py status   # Show status
"""

import subprocess
import sys
import time
import urllib.request
from typing import Tuple

WSL_DISTRO = "Ubuntu"
WSL_USER = "docus"
COMFYUI_DIR = "/home/docus/ComfyUI"
OLLAMA_PORT = 11434
COMFYUI_PORT = 8188

# ── Helpers ────────────────────────────────────────────────────────────────

def _wsl_exec(cmd: str) -> subprocess.CompletedProcess:
    """Run a command inside WSL. Returns empty CompletedProcess on failure."""
    try:
        return subprocess.run(
            ["wsl", "-d", WSL_DISTRO, "-u", WSL_USER, "--", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # WSL not installed or hung — return empty result
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")


def check_ollama(timeout: int = 3) -> bool:
    """Check if Ollama is responding on localhost."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{OLLAMA_PORT}/api/tags", method="GET"
        )
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def check_comfyui(timeout: int = 3) -> bool:
    """Check if ComfyUI is responding on localhost."""
    try:
        req = urllib.request.Request(
            f"http://localhost:{COMFYUI_PORT}/queue", method="GET"
        )
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


# ── Service Management ─────────────────────────────────────────────────────

def start_ollama(timeout: int = 30) -> bool:
    """Start Ollama in a persistent tmux session inside WSL.
    
    Uses tmux so the process survives terminal close.
    Call ensure_ollama() instead if you want the fast-path check first.
    """
    # Kill old session if exists
    _wsl_exec("tmux kill-session -t ollama 2>/dev/null; true")
    
    # Start in detached tmux session
    tmux_cmd = (
        "tmux new-session -d -s ollama "
        "'ollama serve 2>&1 | tee /tmp/ollama.log; bash'"
    )
    _wsl_exec(tmux_cmd)
    
    # Wait for ready
    for _ in range(timeout):
        if check_ollama():
            return True
        time.sleep(1)
    return False


def start_comfyui(timeout: int = 90) -> bool:
    """Start ComfyUI in a persistent tmux session inside WSL.
    
    Uses tmux so the process survives terminal close.
    Call ensure_comfyui() instead if you want the fast-path check first.
    """
    # Kill old session if exists
    _wsl_exec("tmux kill-session -t comfyui 2>/dev/null; true")
    
    # Start in detached tmux session with --lowvram for 8GB GPUs
    tmux_cmd = (
        f"tmux new-session -d -s comfyui "
        f"'cd {COMFYUI_DIR}; "
        f"./venv/bin/python main.py --listen --port {COMFYUI_PORT} --lowvram "
        f"2>&1 | tee /tmp/comfyui.log; bash'"
    )
    _wsl_exec(tmux_cmd)
    
    # Wait for ready (ComfyUI takes longer)
    for i in range(timeout):
        if check_comfyui():
            return True
        if i > 0 and i % 15 == 0:
            print(f"  ... still waiting for ComfyUI ({i}s)")
        time.sleep(1)
    return False


def stop_ollama():
    """Stop Ollama tmux session."""
    _wsl_exec("tmux kill-session -t ollama 2>/dev/null; true")


def stop_comfyui():
    """Stop ComfyUI tmux session."""
    _wsl_exec("tmux kill-session -t comfyui 2>/dev/null; true")


def stop_all_services():
    """Stop all WSL services."""
    stop_ollama()
    stop_comfyui()


def ensure_ollama(timeout: int = 30) -> bool:
    """Ensure Ollama is running. Start it if not.
    
    Safe to call repeatedly - returns immediately if already running.
    """
    if check_ollama():
        return True
    return start_ollama(timeout=timeout)


def ensure_comfyui(timeout: int = 90) -> bool:
    """Ensure ComfyUI is running. Start it if not.
    
    Safe to call repeatedly - returns immediately if already running.
    """
    if check_comfyui():
        return True
    return start_comfyui(timeout=timeout)


def ensure_all_services() -> Tuple[bool, bool]:
    """Ensure both Ollama and ComfyUI are running.
    
    Returns:
        (ollama_ok, comfyui_ok) tuple
    """
    ollama_ok = ensure_ollama()
    if not ollama_ok:
        print("[WARN] Ollama failed to start", file=sys.stderr)
    
    comfyui_ok = ensure_comfyui()
    if not comfyui_ok:
        print("[WARN] ComfyUI failed to start", file=sys.stderr)
    
    return ollama_ok, comfyui_ok


def get_status() -> dict:
    """Get current status of all WSL services."""
    ollama_up = check_ollama()
    comfyui_up = check_comfyui()
    
    # VRAM
    vram_used = -1
    vram_total = 8192
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            vram_used = int(parts[0])
            vram_total = int(parts[1])
    except Exception:
        pass
    
    return {
        "ollama": ollama_up,
        "comfyui": comfyui_up,
        "vram_used_mb": vram_used,
        "vram_total_mb": vram_total,
    }


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python wsl_service_manager.py [start|stop|status|ensure]")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "start":
        print("Starting WSL services (persistent tmux)...")
        o, c = ensure_all_services()
        print(f"  Ollama: {'OK' if o else 'FAIL'}")
        print(f"  ComfyUI: {'OK' if c else 'FAIL'}")
        sys.exit(0 if o and c else 1)
    
    elif action == "stop":
        print("Stopping WSL services...")
        stop_all_services()
        print("  Done.")
    
    elif action == "status":
        s = get_status()
        print("=== SIMMOON WSL Services ===")
        print(f"  Ollama  :11434 -> {'UP' if s['ollama'] else 'DOWN'}")
        print(f"  ComfyUI :8188  -> {'UP' if s['comfyui'] else 'DOWN'}")
        print(f"  VRAM: {s['vram_used_mb']}MB / {s['vram_total_mb']}MB")
        
        # Tmux sessions
        try:
            result = _wsl_exec("tmux list-sessions 2>/dev/null || echo '(none)'")
            print(f"  Tmux: {result.stdout.strip()}")
        except Exception:
            pass
    
    elif action == "ensure":
        print("Ensuring services are running...")
        o, c = ensure_all_services()
        status = get_status()
        print(f"  Ollama: {'OK' if o else 'FAIL'}")
        print(f"  ComfyUI: {'OK' if c else 'FAIL'}")
        print(f"  VRAM: {status['vram_used_mb']}MB / {status['vram_total_mb']}MB")
        sys.exit(0 if o and c else 1)
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
