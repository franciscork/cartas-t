#!/usr/bin/env python3
"""Vota todos los assets faltantes: regulares 4⭐, oficios 5⭐"""
import json, os, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

from juego_simmoon import CATALOGO_EDIFICIOS

# Load current votes
with open('votes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

voted = {v['asset_id'] for v in data}
all_ids = set(CATALOGO_EDIFICIOS.keys())
missing = all_ids - voted

print(f"Votados actualmente: {len(voted)}")
print(f"Total catálogo: {len(all_ids)}")
print(f"Faltan: {len(missing)}")

# Add new votes
oficios = {a for a in missing if a.startswith('oficio_')}
regulares = missing - oficios

for aid in sorted(regulares):
    data.append({"asset_id": aid, "vote_value": 4, "session_id": "curador"})

for aid in sorted(oficios):
    data.append({"asset_id": aid, "vote_value": 5, "session_id": "curador"})

# Write back
with open('votes.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Añadidos {len(missing)} votos:")
print(f"   Regulares: {len(regulares)} × 4⭐")
print(f"   Oficios:   {len(oficios)} × 5⭐")
print(f"   Total:     {len(data)} votos en votes.json")
