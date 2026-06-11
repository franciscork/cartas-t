#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guardar la respuesta de Hermes Bridge en el acta de reunion."""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

import json
from pathlib import Path
from obsidian_memory import ObsidianMemory

# Config REST
cfg_path = Path("obsidian_rest_config.json")
with open(cfg_path) as f:
    rc = json.load(f)

memory = ObsidianMemory(
    agent_name="Buffy",
    project="SIMMOON",
    rest_port=int(rc.get("port", 27124)),
    rest_api_key=rc.get("api_key", ""),
    rest_https=rc.get("https", True),
    rest_host=rc.get("host", "127.0.0.1"),
)

ACTA_ID = "reunion_20260611_1135"

# Ultima respuesta de Hermes Bridge (test con system prompt moderado)
NUEVA_ENTRADA = """
---

### 🧪 Test #2 — Hermes Bridge con system prompt moderado

**Prompt:** "Genera 1 mecanica de juego para reciclaje lunar."
**System:** "Eres un creativo de juegos. Responde en 3 lineas."
**Modelo:** qwen2.5:3b via Hermes Gateway en WSL
**Tiempo:** 8 segundos
**Estado:** ✅ Funcionó correctamente

**Respuesta de Hermes:**
> Mecánica: En cada nivel, el jugador debe recoger los desperfectos espaciales que atentan contra la nave mientras evade obstáculos e infrarrojos activados por la Luna. El objetivo es completar 5 niveles antes del tiempo agotándose semanalmente.

**Observación:** El Hermes Bridge funciona con system prompts cortos/moderados (~50 chars).
El bug anterior era con system prompts largos (>500 chars) que rompían el escapado del shell.
"""

# Leer acta actual
print(f"📖 Leyendo acta '{ACTA_ID}' desde Obsidian...")
acta = memory.get(ACTA_ID, memory_type="task")

if acta:
    contenido_actual = acta.get("content", "")
    print(f"✅ Acta encontrada ({len(contenido_actual)} chars)")
    
    # Append nueva entrada
    nuevo_contenido = contenido_actual.strip() + "\n" + NUEVA_ENTRADA.strip()
    
    saved = memory.save_task(
        key_name=ACTA_ID,
        content=nuevo_contenido,
        tags=["reunion", "semanal", "acta", "hermes_dialogue", "test_bridge"],
        importance=5,
    )
    
    if saved:
        print(f"\n✅ Respuesta de Hermes guardada en acta '{ACTA_ID}'")
        print(f"   Acta actualizada: {len(contenido_actual)} → {len(nuevo_contenido)} chars")
    else:
        print(f"\n❌ Error al guardar")
else:
    print(f"❌ Acta no encontrada")
