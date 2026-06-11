#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test: Creativo de Juegos via Hermes Bridge."""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from hermes_bridge import HermesBridge

SYSTEM = """Eres el **Creativo de Juegos** de FactoryGames.
Tu especialidad es la direccion creativa y diseno de videojuegos.

Tus habilidades:
- Diseno de mecanicas de juego innovadoras
- Brainstorming de features y contenido
- Evaluacion de ideas desde perspectiva de game design
- Pensamiento lateral para resolver problemas de diseno
- Inspiracion en titulos clasicos y tendencias indie

Tono: entusiasta, creativo, concreto. Usa emojis de juegos (🎮 🎲 🎯 🕹️).
Siempre da ideas ACCIONABLES, no genericas."""

PROMPT = """Genera 3 mecanicas de juego innovadoras para un sistema de RECICLAJE AMBIENTAL en una base lunar.

Contexto: Es un juego de construccion y gestion de una colonia lunar. Los jugadores recolectan recursos, construyen instalaciones y gestionan residuos.

Para cada mecanica incluye:
1. 🏷️ Nombre creativo de la mecanica
2. 📝 Descripcion corta (1-2 lineas)
3. ⚙️ Como se implementaria en el juego
4. 🎯 Por que seria divertida / que decision interesante le da al jugador

Se concreto, original y evita cliches."""

bridge = HermesBridge(model='qwen2.5:3b', verbose=True)
print("=" * 60)
print("  🎮 Creativo de Juegos via Hermes Bridge")
print("  🌙 Tema: Reciclaje ambiental en base lunar")
print("=" * 60)
print()
print("🧠 Enviando prompt a Hermes (modelo: qwen2.5:3b)...")
print("   (esto puede tomar 30-60s)")
print()

response = bridge.chat(PROMPT, system=SYSTEM, max_turns=5, timeout=300)

print()
print("─" * 60)
print("  💬 RESPUESTA DEL CREATIVO DE JUEGOS")
print("─" * 60)
print()
print(response)
print()
print("─" * 60)

# Also test directo desde agent_creativo.py
print()
print("🧪 Comparando con agente nativo (agent_creativo.py)...")
from factory.agent_creativo import CreativoJuegos
creativo = CreativoJuegos(model='qwen2.5:3b', verbose=False)
directo = creativo.brainstorm_mecanicas("reciclaje ambiental en base lunar", cantidad=3)
print()
print("─" * 60)
print("  💬 RESPUESTA DEL AGENTE NATIVO")
print("─" * 60)
print()
print(directo)
print()
print("─" * 60)
