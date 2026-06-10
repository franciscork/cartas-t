#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMMOON Agent — Simple AI agent that uses Ollama to decide what to generate next.

Analyzes the current state of assets in PostgreSQL / filesystem and asks an LLM
to recommend the next category, checkpoint, and generation parameters.

Usage:
    python Simmoon_arc/simmoon_agent.py --advise
    python Simmoon_arc/simmoon_agent.py --generate
    python Simmoon_arc/simmoon_agent.py --generate --category businesses --checkpoint dreamshaper_8.safetensors
    python Simmoon_arc/simmoon_agent.py --list-models
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_PATH = SCRIPT_DIR / "simmoon_prompts.json"
OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"

# ── Tool Definitions (Ollama function-calling format) ─────────────────────

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scan_assets",
            "description": "Escanea el sistema de archivos y devuelve el estado actual de todos los assets generados por categoría, incluyendo cuántas imágenes existen y qué runs se han hecho.",
            "parameters": {
                "type": "object",
                "properties": {
                    "verbose": {
                        "type": "boolean",
                        "description": "Si es true, incluye detalles extendidos (recomendado: true)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_models",
            "description": "Lista todos los modelos Ollama disponibles localmente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Filtro opcional por nombre"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_asset_run",
            "description": "Lanza una generación de assets para una categoría específica usando un checkpoint y sufijo determinados. ⚠️ SOLO usar si el usuario lo pide explícitamente. NO llamar durante recomendaciones automáticas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Categoría a generar (ej: businesses, vehicles, greenhouses, solar_energy, lunar_map, buildings_misc, lunar_sites, ui_elements, roads, decorations, characters, lunar_flora, infrastructure)",
                        "enum": ["businesses", "vehicles", "greenhouses", "solar_energy", "lunar_map", "buildings_misc", "lunar_sites", "ui_elements", "roads", "decorations", "characters", "lunar_flora", "infrastructure"]
                    },
                    "checkpoint": {
                        "type": "string",
                        "description": "Checkpoint a usar (ej: dreamshaper_8.safetensors, v1-5-pruned-emaonly.safetensors, revAnimated_v122.safetensors, pixelArtSpriteDiffusion_safetensors.safetensors, counterfeit_v30.safetensors)",
                        "enum": ["v1-5-pruned-emaonly.safetensors", "dreamshaper_8.safetensors", "revAnimated_v122.safetensors", "pixelArtSpriteDiffusion_safetensors.safetensors", "counterfeit_v30.safetensors"]
                    },
                    "suffix": {
                        "type": "string",
                        "description": "Sufijo único para esta tanda de generación (ej: gemma3_businesses_v1)"
                    },
                    "no_loras": {
                        "type": "boolean",
                        "description": "Si es true, deshabilita LoRAs (recomendado: true)"
                    }
                },
                "required": ["category", "checkpoint", "suffix"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_recommendation",
            "description": "Envía tu recomendación estructurada sobre qué generar a continuación. Usa esta herramienta después de analizar el estado de los assets para entregar tu veredicto final en formato JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recommendation": {"type": "string", "enum": ["generate", "improve", "done"]},
                    "category": {"type": "string"},
                    "checkpoint": {"type": "string"},
                    "reason": {"type": "string"},
                    "next_action": {"type": "string"}
                },
                "required": ["recommendation", "category", "checkpoint", "reason", "next_action"]
            }
        }
    }
]


# ── Ollama API ────────────────────────────────────────────────────────────

def ollama_chat(model, prompt=None, system=None, temperature=0.3, max_tokens=1000,
               messages=None, tools=None, tool_choice="auto"):
    """Call Ollama's chat API and return the full response (message dict).

    If 'prompt' is provided, it builds a simple messages list.
    If 'messages' is provided, it's used directly (for multi-turn tool loops).
    Returns dict with 'content' (str or None) and 'tool_calls' (list or None).
    """
    if messages is None:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if prompt:
            messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg = result.get("message", {})
            return {
                "content": msg.get("content", "") or None,
                "tool_calls": msg.get("tool_calls") or None,
            }
    except Exception as e:
        return {"content": f"[ERROR] Ollama call failed: {e}", "tool_calls": None}


def ollama_chat_text(model, prompt, system=None, temperature=0.3, max_tokens=1000):
    """Simple text-only Ollama call (backward-compatible wrapper)."""
    result = ollama_chat(model, prompt=prompt, system=system,
                         temperature=temperature, max_tokens=max_tokens)
    return result.get("content", "") or ""


# ── Tool Execution Handler ────────────────────────────────────────────────

def execute_tool_call(tool_name, arguments):
    """Execute a tool call and return the result string."""
    if tool_name == "scan_assets":
        return get_asset_summary()

    elif tool_name == "list_available_models":
        models = ollama_list_models()
        if models:
            return "Modelos disponibles:\n" + "\n".join(f"  - {m}" for m in models)
        return "No se pudieron obtener modelos de Ollama."

    elif tool_name == "generate_asset_run":
        # _build_generate_command defined below
        category = arguments.get("category", "")
        checkpoint = arguments.get("checkpoint", "")
        suffix = arguments.get("suffix", "unnamed_run")
        no_loras = arguments.get("no_loras", True)
        cmd, err = _build_generate_command(category, checkpoint, suffix, no_loras)
        if err:
            return err
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return (
                f"[ACK] Generation launched (PID {proc.pid})\n"
                f"  Category: {category}\n"
                f"  Checkpoint: {checkpoint}\n"
                f"  Suffix: {suffix}\n"
                f"  No LoRAs: {no_loras}\n"
                f"  Command: {' '.join(cmd)}\n"
                f"  Monitor progress in Simmoon_arc/generation_log_*.txt"
            )
        except Exception as e:
            return f"[ERROR] Failed to launch generation: {e}"

    elif tool_name == "submit_recommendation":
        return json.dumps(arguments, indent=2, ensure_ascii=False)

    return f"[ERROR] Unknown tool: {tool_name}"


def ollama_chat_with_tools(model, prompt=None, system=None, messages=None,
                           tools=None, temperature=0.3, max_tokens=1000,
                           max_tool_rounds=8):
    """Chat loop that handles tool calling automatically.

    Sends prompt + tools to the model. If the model responds with tool_calls,
    executes them and feeds results back until the model gives a final text response.

    Returns:
        dict with 'final_text' (str), 'tool_calls_made' (list of str),
        'messages' (full conversation for debugging)
    """
    if tools is None:
        tools = AGENT_TOOLS

    if messages is None:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if prompt:
            messages.append({"role": "user", "content": prompt})

    tool_calls_made = []

    for round_num in range(max_tool_rounds):
        # First round: require tool use to force model to scan state.
        # Subsequent rounds: auto (model can call more tools or give final answer).
        current_choice = "required" if round_num == 0 else "auto"
        result = ollama_chat(
            model, messages=messages, tools=tools,
            temperature=temperature, max_tokens=max_tokens,
            tool_choice=current_choice,
        )

        tool_calls = result.get("tool_calls")
        content = result.get("content")

        # Handle empty/error response — retry once on any round
        if not tool_calls and not content:
            print(f"  [WARN] Model returned empty response (round {round_num + 1}). Retrying...")
            continue

        if tool_calls:
            # Model wants to call tools
            messages.append({"role": "assistant", "content": content or "",
                           "tool_calls": tool_calls})

            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                arguments = fn.get("arguments", {})

                tool_calls_made.append(tool_name)
                print(f"  [TOOL] {tool_name}({json.dumps(arguments, ensure_ascii=False)[:120]})")

                tool_result = execute_tool_call(tool_name, arguments)

                messages.append({
                    "role": "tool",
                    "content": tool_result[:4000],  # Truncate long results
                })
            continue  # Loop back to let model process tool results

        # No tool calls — model gave a final text response
        return {
            "final_text": content or "",
            "tool_calls_made": tool_calls_made,
            "messages": messages,
        }

    return {
        "final_text": "[WARN] Max tool rounds reached without final response.",
        "tool_calls_made": tool_calls_made,
        "messages": messages,
    }


def ollama_list_models():
    """Return list of available model names from Ollama."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ── Asset State ───────────────────────────────────────────────────────────

def load_prompts():
    """Load prompts from simmoon_prompts.json."""
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_known_categories():
    """Return set of known category directory names from prompts."""
    try:
        data = load_prompts()
        return {cat.get("output_dir", slug).split("/")[-1] for slug, cat in data.get("categories", {}).items()}
    except Exception:
        return set()


def scan_filesystem():
    """Count existing images per category on disk, filtering to known categories."""
    known_cats = get_known_categories()
    categories = {}
    for cat_dir in sorted(SCRIPT_DIR.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith(".") or cat_dir.name.endswith("_pixel"):
            continue
        if cat_dir.name not in known_cats:
            continue
        pngs = list(cat_dir.glob("*.png"))
        if pngs:
            # Detect run prefixes
            prefixes = set()
            for p in pngs:
                parts = p.stem.split("_", 1)
                if len(parts) > 1 and not parts[0].startswith(("biz", "veh", "gh", "sol", "map", "misc", "site", "ui", "road", "dec", "char", "flora", "infra")):
                    prefixes.add(parts[0])
            categories[cat_dir.name] = {
                "total": len(pngs),
                "runs": sorted(prefixes) if prefixes else ["default"],
            }
    return categories


def get_asset_summary():
    """Build a text summary of current asset state for the LLM."""
    data = load_prompts()
    cats = data.get("categories", {})
    fs = scan_filesystem()

    lines = [f"# SIMMOON Asset State — {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    lines.append(f"Total categories defined: {len(cats)}")
    lines.append(f"Total prompts defined: {sum(len(c['prompts']) for c in cats.values())}")
    lines.append("")

    for slug, cat_data in cats.items():
        defined = len(cat_data["prompts"])
        on_disk = fs.get(slug, {}).get("total", 0)
        runs = fs.get(slug, {}).get("runs", [])
        lines.append(f"  {slug}: {defined} prompts defined, ~{on_disk} files on disk, runs: {', '.join(runs)}")

    # Available checkpoints
    lines.append("")
    lines.append("Available checkpoints (in ~/ComfyUI/models/checkpoints/):")
    lines.append("  - v1-5-pruned-emaonly.safetensors")
    lines.append("  - dreamshaper_8.safetensors")
    lines.append("  - revAnimated_v122.safetensors")
    lines.append("  - pixelArtSpriteDiffusion_safetensors.safetensors")
    lines.append("  - counterfeit_v30.safetensors")

    # Available models
    models = ollama_list_models()
    if models:
        lines.append("")
        lines.append("Available Ollama models:")
        for m in models:
            lines.append(f"  - {m}")

    return "\n".join(lines)


# ── Agent Decision ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un AI director de arte para el juego SIMMOON, una simulación de colonia lunar.
Tu trabajo es analizar el estado actual de los assets del juego y recomendar qué generar a continuación.

INSTRUCCIONES ESTRICTAS:
1. PRIMERO, llama a la herramienta 'scan_assets' para ver el estado actual.
2. DESPUÉS de recibir los resultados, DEBES llamar a 'submit_recommendation' con tu recomendación final.
   NO des respuestas de texto libre — SIEMPRE entrega tu recomendación usando submit_recommendation.
3. En submit_recommendation: elige 'generate' si faltan assets, 'improve' si hay que mejorar, 'done' si está completo.
4. Prioriza categorías con menos variantes de run.
5. Sugiere checkpoints que NO se hayan usado aún para esa categoría.
6. NO uses generate_asset_run — solo recomienda. El usuario decidirá si ejecutar."""


def get_recommendation(model=DEFAULT_MODEL, use_tools=True):
    """Ask Ollama for a generation recommendation, optionally using tool calling.

    When use_tools=True, the model can call scan_assets, list_models, and
    submit_recommendation tools. The recommendation JSON is extracted from
    tool calls or returned as the final text.
    """
    summary = get_asset_summary()
    prompt = f"""Analiza el estado actual de los assets y recomienda qué generar:

{summary}

Basado en estos datos, ¿qué deberíamos generar a continuación?"""

    if use_tools:
        result = ollama_chat_with_tools(
            model, prompt=prompt, system=SYSTEM_PROMPT,
            tools=AGENT_TOOLS, temperature=0.2, max_tokens=1200,
        )
        # Try to extract JSON from submit_recommendation tool results first,
        # then fall back to final_text
        for msg in result.get("messages", []):
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if content and content.strip().startswith("{"):
                    try:
                        return json.loads(content.strip())
                    except json.JSONDecodeError:
                        pass
        # Fallback: try parsing final_text as JSON, else return raw text
        final = result["final_text"]
        try:
            return json.loads(final)
        except (json.JSONDecodeError, TypeError):
            return final
    else:
        return ollama_chat_text(model, prompt, system=SYSTEM_PROMPT, temperature=0.2)


KNOWN_CATEGORIES = {
    "businesses", "vehicles", "greenhouses", "solar_energy", "lunar_map",
    "buildings_misc", "lunar_sites", "ui_elements", "roads", "decorations",
    "characters", "lunar_flora", "infrastructure",
}

KNOWN_CHECKPOINTS = {
    "v1-5-pruned-emaonly.safetensors", "dreamshaper_8.safetensors",
    "revAnimated_v122.safetensors", "pixelArtSpriteDiffusion_safetensors.safetensors",
    "counterfeit_v30.safetensors",
}


def _validate_generate_args(category, checkpoint):
    """Validate category and checkpoint. Returns (ok, error_msg)."""
    if category not in KNOWN_CATEGORIES:
        return False, f"[ERROR] Invalid category: '{category}'. Must be one of: {', '.join(sorted(KNOWN_CATEGORIES))}"
    if checkpoint not in KNOWN_CHECKPOINTS:
        return False, f"[ERROR] Invalid checkpoint: '{checkpoint}'. Must be one of: {', '.join(sorted(KNOWN_CHECKPOINTS))}"
    return True, None


def _build_generate_command(category, checkpoint, suffix, no_loras=True):
    """Build the comfyui generation command. Returns (cmd_list, error_msg)."""
    ok, err = _validate_generate_args(category, checkpoint)
    if not ok:
        return None, err
    script = SCRIPT_DIR / "generate_comfyui.py"
    if not script.exists():
        return None, f"[ERROR] generate_comfyui.py not found at {script}"
    cmd = [
        sys.executable, str(script),
        "--categories", category,
        "--checkpoint", checkpoint,
        "--suffix", suffix,
    ]
    if no_loras:
        cmd.append("--no-loras")
    return cmd, None


def generate_run(category, checkpoint, suffix, no_loras=True):
    """Launch generate_comfyui.py for a specific category (blocking)."""
    cmd, err = _build_generate_command(category, checkpoint, suffix, no_loras)
    if err:
        return err

    print(f"[EXEC] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode == 0:
            return f"[OK] Generation complete:\n{result.stdout[-500:]}"
        else:
            return f"[FAIL] Exit code {result.returncode}:\n{result.stderr[-500:]}"
    except subprocess.TimeoutExpired:
        return "[TIMEOUT] Generation exceeded 3600 seconds (1 hour)"
    except Exception as e:
        return f"[ERROR] {e}"


# ── Main ──────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="SIMMOON Agent — AI-powered asset generation advisor",
    )
    parser.add_argument("--advise", action="store_true",
                        help="Get AI recommendation on what to generate next")
    parser.add_argument("--generate", action="store_true",
                        help="Generate assets (uses recommendation if no --category)")
    parser.add_argument("--category", type=str, default=None,
                        help="Category to generate (e.g. businesses)")
    parser.add_argument("--checkpoint", type=str, default=None,
                        help="Checkpoint to use (e.g. dreamshaper_8.safetensors)")
    parser.add_argument("--suffix", type=str, default=None,
                        help="Run suffix (default: auto-generated)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--list-models", action="store_true",
                        help="List available Ollama models")
    parser.add_argument("--scan", action="store_true",
                        help="Scan filesystem and print asset state")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list_models:
        models = ollama_list_models()
        print("\nAvailable Ollama models:")
        for m in models:
            print(f"  {m}")
        print()
        return

    if args.scan:
        print(get_asset_summary())
        return

    if args.advise:
        print("\n[AI] Consulting AI director (with tool calling)...\n")
        rec = get_recommendation(model=args.model, use_tools=True)
        print("-" * 50)
        print("AI Recommendation:")
        print("-" * 50)
        if isinstance(rec, dict):
            print(json.dumps(rec, indent=2, ensure_ascii=False))
        else:
            print(rec)
        print()
        return

    if args.generate:
        if args.category and args.checkpoint:
            suffix = args.suffix or f"{args.checkpoint.replace('.safetensors', '')}_{args.category}"
            print(f"\n[GEN] Generating: {args.category} with {args.checkpoint}\n")
            result = generate_run(args.category, args.checkpoint, suffix)
            print(result)
        else:
            print("\n[AI] Asking AI what to generate (with tools)...\n")
            rec = get_recommendation(model=args.model, use_tools=True)
            print("-" * 50)
            print("AI Recommendation:")
            print("-" * 50)
            if isinstance(rec, dict):
                print(json.dumps(rec, indent=2, ensure_ascii=False))
                if rec.get("recommendation") == "generate":
                    cat = rec.get("category")
                    ckpt = rec.get("checkpoint", "dreamshaper_8.safetensors")
                    suffix = args.suffix or f"{ckpt.replace('.safetensors', '')}_{cat}"
                    print(f"\n[GEN] Generating: {cat} with {ckpt}\n")
                    result = generate_run(cat, ckpt, suffix)
                    print(result)
                else:
                    print(f"\n[INFO] Recommendation: {rec.get('next_action', 'No action')}")
            else:
                print(rec)
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
