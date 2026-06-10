#!/usr/bin/env python3
"""Fix remaining 3 buildings: biz_02, hou_01, site_08 stats."""
import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    lines = f.readlines()

cambios = 0

# ─── 1. biz_02: costo 300→400, energia -2→-3 ───
for i, line in enumerate(lines):
    if 'biz_02' in line and 'TipoEdificio' in line:
        # Next non-empty line with sprite
        sprite_line = lines[i+2]
        cost_line = lines[i+4]
        if 'costo=300' in cost_line:
            lines[i+4] = cost_line.replace('costo=300', 'costo=400').replace('produce_energia=-2', 'produce_energia=-3')
            cambios += 1
            print(f"  OK: biz_02 cost 300->400, energy -2->-3 (line {i+5})")
        else:
            print(f"  SKIP: biz_02 already has {cost_line.strip()}")
        break

# ─── 2. hou_01: costo 400→300, energia -3→-2, desc, alquiler ───
for i, line in enumerate(lines):
    if 'hou_01' in line and 'TipoEdificio' in line:
        sprite_line = lines[i+2]
        cost_line = lines[i+4]
        desc_line = lines[i+8]
        if 'costo=400' in cost_line:
            lines[i+4] = cost_line.replace('costo=400', 'costo=300').replace('produce_energia=-3', 'produce_energia=-2')
            cambios += 1
            print(f"  OK: hou_01 cost 400->300, energy -3->-2 (line {i+5})")
        else:
            print(f"  SKIP: hou_01 already has {cost_line.strip()}")
        # Update description and alquiler
        if 'Capsula subterranea' in desc_line or 'C\u00e1psula subterr\u00e1nea' in desc_line:
            old = desc_line
            new = desc_line.replace(
                'C\u00e1psula subterr\u00e1nea para 4-8 colonos. 1x1", alquiler=20',
                'Albergue econ\u00f3mico para 4-8 colonos. 1x1", alquiler=15'
            ).replace(
                'Capsula subterranea para 4-8 colonos. 1x1", alquiler=20',
                'Albergue economico para 4-8 colonos. 1x1", alquiler=15'
            )
            if old != new:
                lines[i+8] = new
                cambios += 1
                print(f"  OK: hou_01 descripcion+alquiler updated (line {i+9})")
            else:
                # Maybe already changed
                if 'Albergue econ' in desc_line:
                    print(f"  SKIP: hou_01 desc already updated")
        break

# ─── 3. site_08: costo 700→800, oxigeno -5→-3 ───
for i, line in enumerate(lines):
    if 'site_08' in line and 'TipoEdificio' in line:
        cost_line = lines[i+4]
        if 'costo=700' in cost_line:
            new = cost_line.replace('costo=700', 'costo=800').replace('produce_oxigeno=-5', 'produce_oxigeno=-3')
            if new != cost_line:
                lines[i+4] = new
                cambios += 1
                print(f"  OK: site_08 cost 700->800, oxigeno -5->-3 (line {i+5})")
            else:
                print(f"  WARN: site_08 replacement didn't change anything")
        else:
            print(f"  SKIP: site_08 already has {cost_line.strip()}")
        break

# ─── Write back ───
with open(RUTA, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"\n{'='*40}")
print(f"Total cambios: {cambios}")
if cambios == 0:
    print("  (nada que cambiar - ya estaba correcto)")
