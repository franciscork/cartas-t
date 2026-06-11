#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guardar el dialogo de Hermes (Creativo de Juegos) en el acta de reunion."""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

import json
from pathlib import Path

from obsidian_memory import ObsidianMemory

# Config REST desde obsidian_rest_config.json
cfg_path = Path("obsidian_rest_config.json")
if cfg_path.exists():
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

# 1. Leer acta actual
print(f"📖 Leyendo acta '{ACTA_ID}' desde Obsidian...")
acta = memory.get(ACTA_ID, memory_type="task")

if not acta:
    print(f"❌ Acta '{ACTA_ID}' no encontrada. Creando acta nueva...")
    contenido_actual = ""
    memory.save_task(
        key_name=ACTA_ID,
        content="# 🏢 Reunión 2026-06-11\n\n## 💡 Ideas Generadas\n\n_(Hermes dialogue added below)_\n\n",
        tags=["reunion", "semanal", "acta"],
        importance=5,
    )
    contenido_actual = "\n\n"
else:
    contenido_actual = acta.get("content", "")
    print(f"✅ Acta encontrada ({len(contenido_actual)} chars)")

# 2. El dialogo de Hermes (resultado del Creativo de Juegos)
dialogo_hermes = """
---

## 🤖 Diálogo con Hermes Agent — Creativo de Juegos

**Prompt enviado:** "Genera 3 mecanicas de juego innovadoras para un sistema de RECICLAJE AMBIENTAL en una base lunar"

**Modelo:** qwen2.5:3b vía Ollama (Hermes Bridge → WSL)
**Vía:** agent_creativo.py (fallback del Bridge)

### Mecánicas generadas:

1. 🎮 **Lunar Recicloners**
   - Sistema de recolección de basura espacial con vehículos miniaturizados ("Reciclones")
   - Los jugadores conducen Reciclones para recolectar desechos y rellenar estaciones de reciclaje
   - Combina control 3D con estrategia y competitividad social

2. 🌙 **Lunaípolis Limpiadores**
   - Mecánica de limpieza de contaminantes (plástico, metales) usando diversas herramientas
   - Puzzles mecánicos que requieren identificar el tipo de residuo y la herramienta correcta
   - Combina habilidades de navegación y resolución de problemas

3. 🔧 **Lunar Reciclonistas**
   - Mecánica de construcción donde los jugadores manipulan materiales reciclados
   - Los residuos se transforman en materia prima para nuevas estructuras o herramientas
   - Enfoque en ingeniería, diseño estratégico y sensación de progreso

### Estado del Hermes Bridge:
- ✅ Gateway Hermes activo en WSL (PID confirmado)
- ❌ HermesBridge.chat() falló para prompts largos (bug de escapado shell)
- ✅ agent_creativo.py funciona directamente vía Ollama

---

**🔬 Prueba realizada:** Simmoon — 2026-06-11
**Por:** Fran vía Buffy
"""

# 3. Agregar al acta
nuevo_contenido = contenido_actual.strip() + "\n" + dialogo_hermes.strip()

saved = memory.save_task(
    key_name=ACTA_ID,
    content=nuevo_contenido,
    tags=["reunion", "semanal", "acta", "hermes_dialogue", "creativo_juegos"],
    importance=5,
)

if saved:
    print(f"\n✅ Diálogo de Hermes guardado en acta '{ACTA_ID}'")
    print(f"   Acta actualizada: {len(nuevo_contenido)} chars")
else:
    print(f"\n❌ Error al guardar el acta")

# 4. Verificar
print(f"\n📋 Verificando acta guardada...")
verificada = memory.get(ACTA_ID, memory_type="task")
if verificada:
    content = verificada.get("content", "")
    lines = content.split("\n")
    print(f"   ✅ Acta confirmada ({len(content)} chars, {len(lines)} líneas)")
    print(f"   📌 Tags: {verificada.get('tags', [])}")
    # Mostrar primeras lineas tematicas
    for line in lines:
        if any(kw in line.lower() for kw in ["reciclon", "lunaípolis", "hermes bridge", "mecánica"]):
            print(f"     {line.strip()[:80]}")
else:
    print(f"   ❌ No se pudo verificar el acta guardada")
