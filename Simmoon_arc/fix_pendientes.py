#!/usr/bin/env python3
"""Fix remaining issues: hou_04 costs and alojamiento zone cleanup."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    lines = f.readlines()

cambios = 0

# ─── 1. hou_04: costo 1000→700, energia -8→-6 ───
# The block looks like (fixed offsets):
# line N:     "hou_04": TipoEdificio("hou_04", "Albergue Subterraneo", "housing",
# line N+1:   (blank)
# line N+2:   "hou_04_underground_district_pixel.png",
# line N+3:   (blank)
# line N+4:   costo=1000, produce_energia=-8,
# line N+5:   (blank)
# line N+6:   mantenimiento=7, empleos=2, ancho_tiles=3, alto_tiles=2,

for i, line in enumerate(lines):
    if '"hou_04": TipoEdificio' in line:
        # Find the cost line (should be i+4)
        cost_idx = i + 4
        if cost_idx < len(lines) and 'costo=1000' in lines[cost_idx]:
            old = lines[cost_idx]
            lines[cost_idx] = old.replace('costo=1000, produce_energia=-8,',
                                          'costo=700, produce_energia=-6,')
            if lines[cost_idx] != old:
                cambios += 1
                print(f"  OK: hou_04 costo 1000->700, energia -8->-6 (line {cost_idx+1})")
            else:
                print(f"  FAIL: hou_04 replacement didn't match (line {cost_idx+1}: {old.strip()})")
        else:
            print(f"  SKIP: hou_04 cost line not found or already changed (line {cost_idx+1 if cost_idx < len(lines) else 'N/A'})")
        break

# ─── 2. alojamiento zone: remove hou_03, fix alquiler values ───
for i, line in enumerate(lines):
    if '"alojamiento": TipoZona("alojamiento"' in line:
        # Find the categorias_compatibles line
        for j in range(i, min(i+6, len(lines))):
            if 'categorias_compatibles' in lines[j]:
                # Remove hou_03 from the list
                old = lines[j]
                new = old.replace('"hou_03", ', '').replace(', "hou_03"', '')
                if 'hou_03' in old and 'hou_03' not in new:
                    lines[j] = new
                    cambios += 1
                    print(f"  OK: removed hou_03 from alojamiento (line {j+1})")
                else:
                    print(f"  SKIP: hou_03 not found in line {j+1}: {old.strip()}")
                break

        # Find alquiler_min / alquiler_max line
        for j in range(i, min(i+6, len(lines))):
            if 'alquiler_min=10, alquiler_max=80' in lines[j]:
                old = lines[j]
                lines[j] = old.replace('alquiler_min=10, alquiler_max=80',
                                       'alquiler_min=8, alquiler_max=50')
                cambios += 1
                print(f"  OK: alquiler_min 10->8, alquiler_max 80->50 (line {j+1})")
                break
            elif 'alquiler_min' in lines[j]:
                print(f"  INFO: alquiler line found but different: {lines[j].strip()}")
                break
        break

# ─── Write back ───
with open(RUTA, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"\n{'='*40}")
print(f"Total cambios: {cambios}")
if cambios == 0:
    print("  (nada que cambiar - ya estaba correcto)")
