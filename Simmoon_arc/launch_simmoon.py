#!/usr/bin/env python3
"""
SIMMOON — Unified Launcher
Lanza todos los servicios del ecosistema SIMMOON en orden.

Uso:
    python launch_simmoon.py                     # Modo interactivo (menú)
    python launch_simmoon.py --all               # Lanzar todo
    python launch_simmoon.py --comfyui           # Solo ComfyUI
    python launch_simmoon.py --ollama            # Solo Ollama
    python launch_simmoon.py --monitor           # Solo dashboard de monitoreo
    python launch_simmoon.py --status            # Ver estado de servicios
    python launch_simmoon.py --stop              # Detener todos los servicios
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, List

SCRIPT_DIR = Path(__file__).parent.resolve()

# Fix encoding for emoji in Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ── Service Definitions ───────────────────────────────────────────────────

SERVICES = {
    "ollama": {
        "name": "Ollama (LLM Server)",
        "port": 11434,
        "cmd": "ollama serve",
        "env": {},
        "depends": [],
    },
    "comfyui": {
        "name": "ComfyUI (Image Gen)",
        "port": 8188,
        "cmd": "cd ~/ComfyUI && python main.py --listen 0.0.0.0",
        "env": {},
        "depends": ["ollama"],
    },
    "postgresql": {
        "name": "PostgreSQL",
        "port": 5432,
        "cmd": "sudo service postgresql start",
        "env": {},
        "depends": [],
    },
    "openhuman": {
        "name": "OpenHuman (AI Assistant GUI)",
        "port": 7788,
        "cmd": "cd ~/openhuman && LD_LIBRARY_PATH=~/openhuman ./openhuman-core",
        "env": {"OLLAMA_BASE_URL": "http://localhost:11434"},
        "depends": ["ollama"],
    },
    "dashboard": {
        "name": "Dashboard (Monitoring)",
        "port": 5000,
        "cmd": f"cd {SCRIPT_DIR} && python dashboard.py",
        "env": {},
        "depends": [],
    },
    "backup": {
        "name": "Backup PostgreSQL",
        "port": None,
        "cmd": "bash ~/backup_postgres.sh",
        "env": {},
        "depends": ["postgresql"],
    },
    "aider": {
        "name": "Aider (AI Coding w/ Ollama)",
        "port": None,
        "cmd": f"python {SCRIPT_DIR / 'start_aider.py'} start",
        "stop_cmd": f"python {SCRIPT_DIR / 'start_aider.py'} stop",
        "status_cmd": f"python {SCRIPT_DIR / 'start_aider.py'} status",
        "env": {},
        "depends": ["ollama"],
        "windows_native": True,
    },
}


# ── Health Checks ─────────────────────────────────────────────────────────

def _wsl_cmd(cmd: str, timeout: int = 5, as_root: bool = False) -> subprocess.CompletedProcess:
    """Run a command in WSL2."""
    user = "root" if as_root else "docus"
    return subprocess.run(
        ["wsl", "-d", "Ubuntu", "-u", user, "--", "bash", "-c", cmd],
        capture_output=True, text=True, timeout=timeout
    )


def check_port(port: int, timeout: int = 3) -> bool:
    """Check if a port is open on localhost."""
    try:
        proc = _wsl_cmd(
            f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout {timeout} http://localhost:{port} 2>/dev/null",
            timeout=timeout + 2
        )
        if proc.returncode == 0:
            code = proc.stdout.strip()
            return code.isdigit() and int(code) < 500
    except subprocess.TimeoutExpired:
        pass
    return False


def check_service(service_key: str) -> dict:
    """Check if a service is running."""
    svc = SERVICES[service_key]
    result = {
        "key": service_key,
        "name": svc["name"],
        "running": False,
        "port": svc.get("port"),
    }
    if svc.get("port"):
        result["running"] = check_port(svc["port"])
    return result


def check_all_services() -> list:
    """Check status of all services."""
    return [check_service(k) for k in SERVICES]


# ── Service Launcher ──────────────────────────────────────────────────────

def launch_service(service_key: str, background: bool = True) -> Optional[subprocess.Popen]:
    """Launch a single service. Returns Popen if background, None if foreground."""
    svc = SERVICES[service_key]
    print(f"\n  🚀 Starting {svc['name']}...")

    # Check if already running (port-based)
    port = svc.get("port")
    if port and check_port(port, timeout=2):
        print(f"     ⏭️  Already running on port {port}")
        return None

    # Check if already running (Windows-native)
    if not port and svc.get("windows_native") and svc.get("status_cmd"):
        result = subprocess.run(
            shlex.split(svc["status_cmd"]),
            capture_output=True, text=True, timeout=10
        )
        if "🟢" in result.stdout:
            print(f"     ⏭️  Already running")
            return None

    env = os.environ.copy()
    env.update(svc.get("env", {}))

    cmd = svc["cmd"]

    # Windows-native service (Aider runs on Windows, not WSL2)
    if svc.get("windows_native"):
        print(f"     {cmd[:80]}...")
        cmd_parts = shlex.split(cmd)
        creation_flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        if background:
            proc = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                creationflags=creation_flags,
            )
            print(f"     PID: {proc.pid}")
            return proc
        else:
            subprocess.run(cmd_parts, env=env)
            return None

    # WSL2 service (default)
    log_file = f"/tmp/simmoon_{service_key}.log"
    print(f"     {cmd[:80]}...")
    print(f"     Log: {log_file}")

    if background:
        with open(log_file, "w") as log:
            proc = subprocess.Popen(
                ["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd],
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
            )
        print(f"     PID: {proc.pid} (background)")
        return proc

    # Foreground: run interactively
    subprocess.run(
        ["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd],
        env=env,
    )
    return None


def wait_for_service(service_key: str, timeout: int = 30) -> bool:
    """Wait for a service to become available on its port."""
    svc = SERVICES[service_key]
    port = svc.get("port")
    if not port:
        return True

    print(f"     Waiting for {svc['name']} on port {port}...", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_port(port, timeout=2):
            print(" ✅")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    print(" ❌ Timeout")
    return False


def stop_service(service_key: str, procs: Optional[List[subprocess.Popen]] = None) -> bool:
    """Stop a service by killing its port or process."""
    svc = SERVICES[service_key]
    port = svc.get("port")

    # Try terminating Popen handles first
    if procs:
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass

    # Windows-native stop
    if not port and svc.get("windows_native") and svc.get("stop_cmd"):
        try:
            subprocess.run(shlex.split(svc["stop_cmd"]), capture_output=True, text=True, timeout=10)
            print(f"  🛑 Stopped {svc['name']}")
            return True
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Could not stop {svc['name']}")
            return False

    if not port:
        return True

    try:
        # Use root bypass since sudo is broken
        _wsl_cmd(f"fuser -k {port}/tcp 2>/dev/null", timeout=5, as_root=True)
        print(f"  🛑 Stopped {svc['name']} (port {port})")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Could not stop {svc['name']}")
        return False


# ── Launch All ────────────────────────────────────────────────────────────

def launch_all(services_list: list, sequential: bool = True) -> tuple:
    """Launch multiple services in order, respecting dependencies.
    
    Returns:
        Tuple of (launched_service_keys, process_handles).
    """
    launched = []
    processes = []

    for svc_key in services_list:
        svc = SERVICES[svc_key]

        # Check dependencies
        for dep in svc.get("depends", []):
            if dep not in launched:
                # Ensure dependency is running
                dep_port = SERVICES[dep].get("port")
                if dep_port and not check_port(dep_port, timeout=2):
                    print(f"  ⚠️  {svc['name']} requires {SERVICES[dep]['name']} — launching it first...")
                    proc = launch_service(dep)
                    if proc:
                        processes.append(proc)
                    wait_for_service(dep)
                launched.append(dep)

        proc = launch_service(svc_key)
        if proc:
            processes.append(proc)
        launched.append(svc_key)

        if sequential:
            wait_for_service(svc_key)

    return launched, processes


# ── Interactive Menu ──────────────────────────────────────────────────────

def interactive_menu():
    """Display interactive service launcher menu."""
    procs: List[subprocess.Popen] = []

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=" * 55)
        print("  🎮 SIMMOON — Service Launcher")
        print("=" * 55)

        statuses = check_all_services()
        for s in statuses:
            icon = "🟢" if s["running"] else "⚫"
            port_str = f":{s['port']}" if s.get("port") else ""
            print(f"  {icon}  {s['name']:30s} {port_str}")

        print("-" * 55)
        print("  [a] Launch ALL")
        print("  [1] Ollama       [2] ComfyUI      [3] PostgreSQL")
        print("  [4] OpenHuman    [5] Dashboard    [6] Aider")
        print("  [b] Backup DB")
        print("  [s] Stop all     [q] Quit")
        print("-" * 55)

        choice = input("  > ").strip().lower()

        if choice == "q":
            # Kill background processes before quitting
            for p in procs:
                try:
                    p.terminate()
                except Exception:
                    pass
            break
        elif choice == "a":
            _, new_procs = launch_all(["ollama", "comfyui", "postgresql", "dashboard", "aider"])
            procs.extend(new_procs)
            input("\n  Press Enter to continue...")
        elif choice == "1":
            p = launch_service("ollama")
            if p: procs.append(p)
            input("\n  Press Enter to continue...")
        elif choice == "2":
            p = launch_service("comfyui")
            if p: procs.append(p)
            input("\n  Press Enter to continue...")
        elif choice == "3":
            p = launch_service("postgresql")
            if p: procs.append(p)
            input("\n  Press Enter to continue...")
        elif choice == "4":
            p = launch_service("openhuman")
            if p: procs.append(p)
            input("\n  Press Enter to continue...")
        elif choice == "5":
            p = launch_service("dashboard")
            if p: procs.append(p)
            input("\n  Press Enter to continue...")
        elif choice == "6":
            launch_service("aider")
            input("\n  Press Enter to continue...")
        elif choice == "b":
            launch_service("backup", background=False)
            input("\n  Press Enter to continue...")
        elif choice == "s":
            for svc_key in SERVICES:
                stop_service(svc_key, procs)
            procs.clear()
            input("\n  Press Enter to continue...")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON — Unified Service Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python launch_simmoon.py\n  python launch_simmoon.py --all\n  python launch_simmoon.py --ollama --comfyui --monitor"
    )
    parser.add_argument("--all", "-a", action="store_true", help="Launch all services")
    parser.add_argument("--ollama", action="store_true", help="Launch Ollama")
    parser.add_argument("--comfyui", action="store_true", help="Launch ComfyUI")
    parser.add_argument("--postgres", action="store_true", help="Launch PostgreSQL")
    parser.add_argument("--openhuman", action="store_true", help="Launch OpenHuman")
    parser.add_argument("--dashboard", "--monitor", action="store_true", help="Launch Dashboard")
    parser.add_argument("--aider", action="store_true", help="Launch Aider (AI coding assistant)")
    parser.add_argument("--backup", action="store_true", help="Run PostgreSQL backup")
    parser.add_argument("--status", "-s", action="store_true", help="Show service status")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground (blocking)")
    args = parser.parse_args()

    # --status
    if args.status:
        print("\n  SIMMOON Service Status\n")
        for s in check_all_services():
            icon = "✅" if s["running"] else "❌"
            print(f"  {icon} {s['name']}")
        return

    # --stop
    if args.stop:
        print("\n  Stopping all services...")
        for svc_key in SERVICES:
            stop_service(svc_key)
        print("  Done.")
        return

    # Collect requested services
    requested = []
    if args.all:
        requested = ["ollama", "comfyui", "postgresql", "dashboard", "aider"]
    else:
        if args.ollama: requested.append("ollama")
        if args.comfyui: requested.append("comfyui")
        if args.postgres: requested.append("postgresql")
        if args.openhuman: requested.append("openhuman")
        if args.dashboard: requested.append("dashboard")
        if args.aider: requested.append("aider")
        if args.backup: requested.append("backup")

    # Remove duplicates while preserving order
    requested = list(dict.fromkeys(requested))

    if requested:
        if args.foreground and len(requested) == 1:
            launch_service(requested[0], background=False)
        else:
            launched_keys, procs = launch_all(requested, sequential=True)
            print(f"\n  ✅ {len(launched_keys)} services launched. Press Ctrl+C to stop all.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n  Stopping all services...")
                for p in procs:
                    try:
                        p.terminate()
                    except Exception:
                        pass
                for svc_key in launched_keys:
                    stop_service(svc_key)
                print("  Done.")
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
