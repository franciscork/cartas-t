#!/usr/bin/env python3
"""Fix alquiler_min=10 -> 8 and alquiler_max=80 -> 50 in alojamiento zone."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    content = f.read()

target = 'alquiler_min=10, alquiler_max=80)'
replacement = 'alquiler_min=8, alquiler_max=50)'

if target in content:
    content = content.replace(target, replacement)
    with open(RUTA, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: alquiler_min 10->8, alquiler_max 80->50")
else:
    print("FAIL: target string not found")

# Verify
if 'alquiler_min=8, alquiler_max=50)' in content and 'alquiler_min=10' not in content:
    print("OK: Verification passed")
else:
    print("WARN: Verification - check manually")
