#!/usr/bin/env python3
"""
start_aider.py — Lanza Aider con Ollama en una sesión tmux.
Usado por launch_simmoon.py para arrancar Aider como servicio.
"""

import os
import subprocess
import sys
import time

# Fix encoding for emoji in Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

TMUX_PATH = r"C:\Users\docus\AppData\Local\Microsoft\WinGet\Links"
AIDER_PATH = r"C:\Users\docus\AppData\Local\Programs\Python\Python311\Scripts\aider"
PROJECT_DIR = r"C:\Program Files\PowerShell\7\Simmoon_arc"
SESSION_NAME = "aider-simmoon"
MODEL = "ollama_chat/qwen2.5-coder:14b"


def ensure_tmux_in_path() -> str:
    """Add tmux directory to PATH if not there."""
    current_path = os.environ.get("PATH", "")
    if TMUX_PATH not in current_path:
        os.environ["PATH"] = f"{TMUX_PATH};{current_path}"
    return TMUX_PATH


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def launch_aider():
    """Launch Aider in a new tmux session."""
    ensure_tmux_in_path()

    # Check if already running
    if session_exists(SESSION_NAME):
        print(f"  ⏭️  Aider ya está corriendo (sesión tmux: {SESSION_NAME})")
        print(f"     Conéctate con: tmux attach -t {SESSION_NAME}")
        return True

    print(f"  🚀 Creando sesión tmux '{SESSION_NAME}'...")

    try:
        # Create new tmux session
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", SESSION_NAME, "-x", "120", "-y", "40"],
            capture_output=True, text=True, timeout=10
        )

        # Navigate to project directory
        subprocess.run(
            ["tmux", "send-keys", "-t", SESSION_NAME,
             f"cd /d {PROJECT_DIR}", "Enter"],
            capture_output=True, timeout=5
        )

        time.sleep(0.5)

        # Launch Aider
        subprocess.run(
            ["tmux", "send-keys", "-t", SESSION_NAME,
             f"export PATH=\"$PATH:{TMUX_PATH}\" && \"{AIDER_PATH}\" --model {MODEL}", "Enter"],
            capture_output=True, timeout=5
        )

        print(f"  ✅ Aider lanzado en sesión tmux: {SESSION_NAME}")
        print(f"  🎯 Modelo: {MODEL}")
        print(f"  🔗 Conéctate: tmux attach -t {SESSION_NAME}")
        print(f"  📋 Para desconectarte: Ctrl+B, luego D")
        return True

    except FileNotFoundError:
        print("  ❌ tmux no encontrado. ¿Está instalado?")
        print(f"     Buscando en: {TMUX_PATH}")
        return False
    except subprocess.TimeoutExpired:
        print("  ⚠️  Timeout creando sesión tmux")
        return False
    except Exception as e:
        print(f"  ❌ Error lanzando Aider: {e}")
        return False


def stop_aider():
    """Stop Aider by killing the tmux session."""
    ensure_tmux_in_path()

    if not session_exists(SESSION_NAME):
        print("  ⏭️  Aider no está corriendo")
        return True

    try:
        subprocess.run(
            ["tmux", "kill-session", "-t", SESSION_NAME],
            capture_output=True, text=True, timeout=10
        )
        print(f"  🛑 Aider detenido (sesión {SESSION_NAME})")
        return True
    except Exception as e:
        print(f"  ⚠️  Error deteniendo Aider: {e}")
        return False


def aider_status() -> bool:
    """Check if Aider is running."""
    ensure_tmux_in_path()
    return session_exists(SESSION_NAME)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"

    if action == "start":
        launch_aider()
    elif action == "stop":
        stop_aider()
    elif action == "status":
        running = aider_status()
        print(f"  {'🟢' if running else '⚫'} Aider: {'Corriendo' if running else 'Detenido'}")
        if running:
            print(f"     Sesión: {SESSION_NAME}")
            print(f"     Conéctate: tmux attach -t {SESSION_NAME}")
    else:
        print(f"Uso: python start_aider.py [start|stop|status]")
