#!/usr/bin/env python3
"""Lee lineas especificas de juego_simmoon.py, forzando salida UTF-8."""

import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('juego_simmoon.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace emoji with safe placeholders for printing
def safe(line):
    return line.encode('utf-8', errors='replace').decode('utf-8')

print('=== ZONA ALOJAMIENTO ===')
for i, line in enumerate(lines):
    if '"alojamiento": TipoZona("alojamiento"' in line:
        for j in range(i, min(i+7, len(lines))):
            print(f'L{j+1}: {safe(lines[j].rstrip())}')
        break

print()
print('=== ZONA COMERCIAL ===')
for i, line in enumerate(lines):
    if '"comercial": TipoZona("comercial"' in line:
        for j in range(i, min(i+15, len(lines))):
            if 'hou_03' in lines[j] or 'categorias' in lines[j] or 'alquiler' in lines[j] or 'prima' in lines[j]:
                print(f'L{j+1}: ... {safe(lines[j].strip())}')
        print(f'  (zone starts at line {i+1})')
        break

print()
print('=== HOU_04 BLOCK ===')
for i, line in enumerate(lines):
    if '"hou_04": TipoEdificio' in line:
        for j in range(i, min(i+6, len(lines))):
            print(f'L{j+1}: {safe(lines[j].rstrip())}')
        break

print()
print('=== HOU_03 REFS OUTSIDE DEFS ===')
for i, line in enumerate(lines):
    if 'hou_03' in line:
        # Skip definition lines and EDIFICIOS_PRIVADOS
        if 'TipoEdificio' in line or 'EDIFICIOS_PRIVADOS' in line:
            continue
        print(f'L{i+1}: {safe(line.rstrip())}')
