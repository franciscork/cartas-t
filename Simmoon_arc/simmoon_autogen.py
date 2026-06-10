#!/usr/bin/env python3
"""
SIMMOON AutoGen — Multi-agent collaborative design for game assets.

Three AI agents chat with each other to design, critique, and refine
game asset prompts for SIMMOON using Ollama as the LLM backend.

Usage:
    python Simmoon_arc/simmoon_autogen.py                          # Interactive chat
    python Simmoon_arc/simmoon_autogen.py --design businesses      # Design a building
    python Simmoon_arc/simmoon_autogen.py --design lunar_sites     # Design a scene
    python Simmoon_arc/simmoon_autogen.py --quick                  # Quick single suggestion
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3-coder"

# Try importing AutoGen
try:
    import autogen
    from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
    HAS_AUTOGEN = True
except ImportError:
    HAS_AUTOGEN = False


# ── Ollama Direct API (fallback + bootstrapping) ──────────────────────────

def ollama_chat(model, prompt, system=None, temperature=0.7, max_tokens=800):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model, "messages": messages, "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("message", {}).get("content", "")
    except Exception as e:
        return f"[ERROR] {e}"


# ── System Prompts for Each Agent Role ────────────────────────────────────

SYSTEM_GENERATOR = """Eres un diseñador de assets pixel-art para SIMMOON, un juego de simulación de colonia lunar.
Tu especialidad es crear prompts detallados para generación de imágenes 2.5D isométricas.

Siempre incluyes en tus prompts:
- Estilo: professional 2.5D isometric, dimetric projection 2:1
- Técnica: sharp black outline, flat cel-shaded 3-tone depth
- Formato: single square tile footprint, clean readable silhouette
- Inspiración: SimCity 2000 + Factorio + Oxygen Not Included

Propones ideas creativas pero viables técnicamente."""

SYSTEM_CRITIC = """Eres un crítico de arte especializado en pixel-art para videojuegos.
Tu trabajo es revisar los prompts de diseño y sugerir mejoras concretas.

Te fijas en:
1. ¿El prompt especifica claramente la proyección isométrica 2:1?
2. ¿Incluye detalles de iluminación (highlight/mid/shadow)?
3. ¿La paleta de colores es limitada y apropiada?
4. ¿El silhouette es legible a tamaño pequeño?
5. ¿Es técnicamente factible generar con Stable Diffusion 1.5?

Siempre das feedback constructivo con sugerencias específicas."""

SYSTEM_CURATOR = """Eres el curador y director de arte de SIMMOON.
Tomas la decisión final sobre si un diseño es aprobado, necesita revisión, o es rechazado.

Criterios de aprobación:
- ✅ El prompt es completo y específico
- ✅ El diseño encaja en la categoría solicitada
- ✅ La paleta de colores es adecuada (8-32 colores)
- ✅ El estilo es consistente con el resto del juego

Respondes con: APROBADO, NECESITA REVISIÓN, o RECHAZADO, seguido de tu justificación."""


# ── AutoGen Configuration ────────────────────────────────────────────────

def get_llm_config(model=DEFAULT_MODEL):
    """Create LLM config for AutoGen pointing to local Ollama.
    AutoGen 0.7.x uses OpenAI-compatible format for Ollama."""
    # Try both config formats: AutoGen 0.2.x (api_type='ollama') and 0.7.x (OpenAI-compatible)
    config = {
        "config_list": [
            {
                "model": model,
                "base_url": f"{OLLAMA_URL}/v1",  # OpenAI-compatible endpoint
                "api_type": "openai",
                "temperature": 0.7,
            },
            {
                "model": model,
                "base_url": OLLAMA_URL,
                "api_type": "ollama",
                "temperature": 0.7,
            }
        ],
        "timeout": 120,
    }
    return config


def setup_agents(model=DEFAULT_MODEL):
    """Create the three AutoGen agents."""
    llm_config = get_llm_config(model)

    generator = AssistantAgent(
        name="Generator",
        system_message=SYSTEM_GENERATOR,
        llm_config=llm_config,
    )

    critic = AssistantAgent(
        name="Critic",
        system_message=SYSTEM_CRITIC,
        llm_config=llm_config,
    )

    curator = AssistantAgent(
        name="Curator",
        system_message=SYSTEM_CURATOR,
        llm_config=llm_config,
    )

    return generator, critic, curator


# ── Design Session (Group Chat) ───────────────────────────────────────────

def run_design_session(category, model=DEFAULT_MODEL):
    """Run a multi-agent design session for a specific category."""
    cat_info = {
        "businesses": "edificios comerciales y de oficinas",
        "vehicles": "vehículos y naves de transporte",
        "greenhouses": "invernaderos y granjas",
        "solar_energy": "plantas de energía y paneles solares",
        "lunar_map": "mapas y terrenos lunares",
        "buildings_misc": "edificios varios e infraestructura",
        "lunar_sites": "escenas y zonas completas de la colonia",
        "ui_elements": "elementos de interfaz de usuario e iconos",
        "roads": "carreteras, raíles y caminos",
        "decorations": "decoraciones y objetos del entorno",
        "characters": "personajes y astronautas",
        "lunar_flora": "flora y vegetación lunar alienígena",
        "infrastructure": "tuberías, cables y conductos",
    }
    desc = cat_info.get(category, category)

    if not HAS_AUTOGEN:
        print(f"[INFO] AutoGen not available. Using direct Ollama chat for design session.\n")
        return run_direct_design_session(category, desc, model)

    print(f"\n{'='*60}")
    print(f"  SIMMOON Design Session -- {category} ({desc})")
    print(f"  Agents: Generator + Critic + Curator")
    print(f"{'='*60}\n")

    generator, critic, curator = setup_agents(model)

    user_proxy = UserProxyAgent(
        name="Admin",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    group_chat = GroupChat(
        agents=[user_proxy, generator, critic, curator],
        messages=[],
        max_round=15,
        speaker_selection_method="round_robin",
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=get_llm_config(model),
    )

    task = (
        f"Diseña un asset para la categoría '{category}' ({desc}) del juego SIMMOON.\n\n"
        f"Generator: propón un diseño con prompt detallado.\n"
        f"Critic: revisa el prompt y sugiere mejoras.\n"
        f"Generator: actualiza el prompt con las sugerencias.\n"
        f"Curator: evalúa y da el veredicto final.\n"
    )

    user_proxy.initiate_chat(manager, message=task)
    return


# ── Direct Ollama Fallback ────────────────────────────────────────────────

def run_direct_design_session(category, desc, model=DEFAULT_MODEL):
    """Run design chat directly via Ollama API (no AutoGen)."""
    print(f"Category: {category} ({desc})\n")

    # Round 1: Generator
    sep = "-" * 50
    print(sep)
    print("[Generator] Proposes design...")
    gen_prompt = (
        f"Propón un diseño detallado para un asset de la categoría '{category}' ({desc}) "
        f"para el juego SIMMOON. Incluye un prompt completo en estilo 2.5D isométrico "
        f"(dimetric projection 2:1, sharp black outline, flat cel-shaded 3-tone depth)."
    )
    gen_response = ollama_chat(model, gen_prompt, system=SYSTEM_GENERATOR, temperature=0.8, max_tokens=600)
    print(f"\n{gen_response}\n")

    # Round 2: Critic
    print(sep)
    print("[Critic] Reviews design...")
    crit_prompt = (
        f"Revisa este prompt para un asset de SIMMOON ({category}):\n\n{gen_response}\n\n"
        f"Sugiere mejoras concretas para hacerlo más específico y viable técnicamente."
    )
    crit_response = ollama_chat(model, crit_prompt, system=SYSTEM_CRITIC, temperature=0.5, max_tokens=500)
    print(f"\n{crit_response}\n")

    # Round 3: Curator
    print(sep)
    print("[Curator] Gives final verdict...")
    cur_prompt = (
        f"Prompt original:\n{gen_response}\n\n"
        f"Feedback del crítico:\n{crit_response}\n\n"
        f"Decide: ¿APROBADO, NECESITA REVISIÓN o RECHAZADO? Justifica."
    )
    cur_response = ollama_chat(model, cur_prompt, system=SYSTEM_CURATOR, temperature=0.3, max_tokens=300)
    print(f"\n{cur_response}\n")
    print(sep)
    print("[OK] Design session complete!")


# ── Quick Single Suggestion ───────────────────────────────────────────────

def quick_suggestion(category=None, model=DEFAULT_MODEL):
    """Get a single quick design suggestion from Ollama."""
    cat_filter = f" para la categoría '{category}'" if category else ""
    prompt = (
        f"Dame una sugerencia rápida de diseño para un asset de SIMMOON{cat_filter}. "
        f"Incluye: nombre, prompt completo (estilo 2.5D isométrico), y colores sugeridos. "
        f"Responde en formato JSON: {{\"name\": \"...\", \"prompt\": \"...\", \"palette\": [...]}}"
    )
    system = "Eres un diseñador de assets pixel-art. Responde SOLO con JSON."
    response = ollama_chat(model, prompt, system=system, temperature=0.7, max_tokens=600)
    try:
        parsed = json.loads(response)
        s = "=" * 50
        print(f"\n{s}")
        print(f"  [Quick] Design Suggestion")
        print(f"{s}")
        print(f"  Name:   {parsed.get('name', 'N/A')}")
        print(f"  Prompt: {parsed.get('prompt', 'N/A')[:200]}...")
        print(f"  Palette:{parsed.get('palette', [])}")
        print(f"{'='*50}\n")
    except json.JSONDecodeError:
        print(f"\n{response}\n")


# ── Main ──────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="SIMMOON AutoGen — Multi-agent design collaboration")
    parser.add_argument("--design", type=str, default=None, help="Category to design for (e.g. businesses)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama model")
    parser.add_argument("--quick", type=str, nargs="?", const="random", default=None, help="Quick single suggestion (optional category)")
    parser.add_argument("--list-categories", action="store_true", help="List available categories")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list_categories:
        categories = [
            "businesses", "vehicles", "greenhouses", "solar_energy", "lunar_map",
            "buildings_misc", "lunar_sites", "ui_elements", "roads", "decorations",
            "characters", "lunar_flora", "infrastructure",
        ]
        print("\nAvailable categories:")
        for c in categories:
            print(f"  {c}")
        print()
        return

    if args.quick:
        cat = args.quick if args.quick != "random" else args.design
        quick_suggestion(cat, args.model)
        return

    if args.design:
        run_design_session(args.design, args.model)
        return

    # Interactive mode
    s = "=" * 55
    print(f"\n{s}")
    print(f"  SIMMOON AutoGen -- Multi-Agent Design Studio")
    print(f"{s}")
    print("\nCommands:")
    print("  design <category>  — Design session for a category")
    print("  quick [category]   — Quick suggestion")
    print("  list               — List categories")
    print("  quit               — Exit\n")

    while True:
        try:
            cmd = input("simmoon> ").strip()
            if not cmd:
                continue
            if cmd == "quit":
                break
            if cmd == "list":
                for c in ["businesses", "vehicles", "greenhouses", "solar_energy",
                          "lunar_map", "buildings_misc", "lunar_sites", "ui_elements",
                          "roads", "decorations", "characters", "lunar_flora", "infrastructure"]:
                    print(f"  {c}")
                continue
            if cmd.startswith("design "):
                cat = cmd.split(" ", 1)[1]
                run_design_session(cat, args.model)
                continue
            if cmd.startswith("quick"):
                parts = cmd.split(" ", 1)
                cat = parts[1] if len(parts) > 1 else None
                quick_suggestion(cat, args.model)
                continue
            print(f"Unknown command: {cmd}")
        except KeyboardInterrupt:
            print()
            break
        except EOFError:
            break

    print("Goodbye!")


if __name__ == "__main__":
    main()
