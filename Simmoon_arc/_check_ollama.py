#!/usr/bin/env python3
"""Check Ollama installation and find the binary location."""
import json
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

# 1. API version
print("=== Ollama API Version ===")
try:
    req = urllib.request.Request("http://localhost:11434/api/version")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"  Version: {data}")
except Exception as e:
    print(f"  Error: {e}")

print()

# 2. Find ollama.exe
print("=== Finding ollama.exe ===")
# Common paths
home = os.path.expanduser("~")
paths = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
    os.path.join(os.environ.get("ProgramFiles", ""), "Ollama", "ollama.exe"),
    os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Ollama", "ollama.exe"),
    os.path.join(home, "AppData", "Local", "Programs", "Ollama", "ollama.exe"),
    r"C:\Program Files\Ollama\ollama.exe",
]

found_path = None
for p in paths:
    expanded = os.path.expandvars(p)
    if os.path.isfile(expanded):
        found_path = expanded
        print(f"  ✅ {expanded}")
        # Get version
        try:
            r = subprocess.run([expanded, "--version"], capture_output=True, text=True, timeout=10)
            print(f"     Version: {r.stdout.strip() or r.stderr.strip()}")
        except Exception as e:
            print(f"     Error getting version: {e}")
        break

if not found_path:
    print("  ❌ No encontrado en rutas comunes")
    # Try where.exe
    try:
        r = subprocess.run(["where.exe", "ollama"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            print(f"  where.exe: {r.stdout.strip()}")
    except:
        pass

print()

# 3. Check if we can update via API
print("=== Update Options ===")
print("  Web: https://ollama.com/download (Windows)")
print("  CLI: ollama.exe no esta en PATH")
print()
print("  Para actualizar en Windows:")
print("    1. Descargar installer de https://ollama.com/download")
print("    2. Ejecutar el installer (reemplaza la instalacion actual)")
print("    3. Verificar: ollama --version")
