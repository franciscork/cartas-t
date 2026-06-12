#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/agent_creativo.py — 🎮 Creativo de Juegos

Especialista en diseño de juegos, mecánicas, dirección creativa y 
brainstorming. Genera ideas innovadoras para SIMMOON y otros proyectos.

Uso:
    from agent_creativo import CreativoJuegos
    creativo = CreativoJuegos()
    ideas = creativo.brainstorm_mecanicas("cultivos lunares")
    print(creativo.evaluar_idea("nueva mecánica de riego con asteroides"))
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── System prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un **Creativo de Juegos** experto, parte del equipo FactoryGames.
Tu especialidad es la **dirección creativa y diseño de videojuegos**.

Tus habilidades:
- Diseño de mecánicas de juego innovadoras
- Brainstorming de features y contenido
- Evaluación de ideas desde perspectiva de game design
- Creación de mood boards conceptuales (descripción textual)
- Pensamiento lateral para resolver problemas de diseño
- Inspiración en títulos clásicos y tendencias indie

Tono: entusiasta, creativo, concreto. Usa emojis de juegos (🎮 🎲 🎯 🕹️).
Siempre da ideas ACCIONABLES, no genéricas. Piensa en "¿cómo se implementa esto?"
"""

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:latest"


class CreativoJuegos:
    """Agente Creativo de Juegos — brainstorming y diseño de mecánicas."""

    def __init__(self, model: str = DEFAULT_MODEL, verbose: bool = True):
        self.model = model
        self.verbose = verbose
        self.name = "Creativo de Juegos"
        self.emoji = "🎮"
        self.role = "Dirección Creativa y Diseño de Mecánicas"
        self.capabilities = [
            "game_design", "mechanics_innovation", "creative_brainstorming",
            "mood_concept", "feature_design", "game_balance"
        ]

    # ── LLM call ─────────────────────────────────────────────────────────

    def _consulta(self, prompt: str, temperature: float = 0.8,
                  max_tokens: int = 2048) -> Optional[str]:
        """Consultar el LLM local con el system prompt del creativo."""
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        payload = json.dumps({
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "").strip()
        except Exception as e:
            if self.verbose:
                print(f"  [WARN] Error consultando LLM: {e}")
            return None

    # ── Brainstorming ────────────────────────────────────────────────────

    def brainstorm_mecanicas(self, tema: str, cantidad: int = 5) -> str:
        """Generar ideas de mecánicas de juego para un tema específico.

        Args:
            tema: Tema o área del juego (ej: "cultivos lunares", "transporte")
            cantidad: Número de ideas a generar

        Returns:
            Texto formateado con las ideas
        """
        prompt = (
            f"Genera {cantidad} ideas de mecánicas de juego para: **{tema}**\n\n"
            f"Cada idea debe incluir:\n"
            f"1. Nombre creativo de la mecánica\n"
            f"2. Descripción corta (1-2 líneas)\n"
            f"3. Cómo se implementaría en el juego\n"
            f"4. Por qué sería divertida\n\n"
            f"Sé concreto, original y evita clichés de juegos casual."
        )
        resultado = self._consulta(prompt, temperature=0.85)
        if resultado:
            return f"🎮 *Brainstorming: {tema}*\n\n{resultado}"
        return "❌ No se pudo generar brainstorming ahora."

    def evaluar_idea(self, idea: str) -> str:
        """Evaluar una idea de juego desde perspectiva de game design.

        Args:
            idea: Descripción de la idea a evaluar

        Returns:
            Texto formateado con evaluación
        """
        prompt = (
            f"Evalúa esta idea de juego como un diseñador senior:\n\n"
            f"**Idea:** {idea}\n\n"
            f"Puntos a cubrir:\n"
            f"1. 👍 Fortalezas (qué funciona)\n"
            f"2. 👎 Debilidades (qué mejorar)\n"
            f"3. 🎯 Dificultad de implementación (baja/media/alta)\n"
            f"4. 💡 Sugerencia para mejorarla\n"
            f"5. 🔗 Conexiones con otras mecánicas existentes\n\n"
            f"Sé honesto pero constructivo."
        )
        return self._consulta(prompt, temperature=0.4) or "❌ No se pudo evaluar."

    def generar_mood_concept(self, descripcion: str) -> str:
        """Generar descripción de mood/concepto visual para un escenario.

        Args:
            descripcion: Descripción del escenario o elemento visual

        Returns:
            Descripción detallada del concepto visual
        """
        prompt = (
            f"Crea una descripción detallada de concepto visual para:\n\n"
            f"**{descripcion}**\n\n"
            f"Incluye:\n"
            f"- Paleta de colores\n"
            f"- Estilo artístico\n"
            f"- Elementos clave\n"
            f"- Referencias visuales\n"
            f"- Ambiente/atmósfera\n\n"
            f"Que sirva como guía para un artista conceptual."
        )
        return self._consulta(prompt, temperature=0.75) or "❌ No se pudo generar concepto."

    def proponer_features(self, area: str, limitaciones: str = "") -> str:
        """Proponer nuevas features para un área del juego.

        Args:
            area: Área del juego (ej: "economía", "combate", "construcción")
            limitaciones: Limitaciones técnicas o de diseño a considerar

        Returns:
            Propuesta de features
        """
        prompt = (
            f"Propón 3 nuevas features para el área de **{area}** "
            f"en nuestro juego SIMMOON.\n\n"
        )
        if limitaciones:
            prompt += f"Considera estas limitaciones: {limitaciones}\n\n"
        prompt += (
            "Para cada feature:\n"
            f"1. Nombre atractivo\n"
            f"2. Qué problema resuelve o qué diversión aporta\n"
            f"3. Implementación simplificada (2-3 pasos)\n"
            f"4. Cómo afecta a las demás mecánicas\n\n"
            f"Prioriza features que maximicen diversión con mínimo esfuerzo técnico."
        )
        return self._consulta(prompt, temperature=0.8) or "❌ No se pudieron generar features."

    # ── Utilidad ─────────────────────────────────────────────────────────

    def resumen(self) -> dict:
        """Resumen del agente para registro."""
        return {
            "name": self.name,
            "emoji": self.emoji,
            "role": self.role,
            "model": self.model,
            "capabilities": self.capabilities,
            "available": self._consulta("Responde SOLO: OK", temperature=0.1) is not None,
        }

    def __str__(self):
        return f"{self.emoji} {self.name} — {self.role}"


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    """Interfaz CLI para el Creativo de Juegos."""
    import argparse
    parser = argparse.ArgumentParser(
        description=f"🎮 Creativo de Juegos — Brainstorming y Diseño de Mecánicas"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama")
    parser.add_argument("--quiet", "-q", action="store_true", help="Modo silencioso")

    sub = parser.add_subparsers(dest="command")

    p_brain = sub.add_parser("brainstorm", help="Brainstorming de mecánicas")
    p_brain.add_argument("tema", help="Tema para brainstormear")

    p_eval = sub.add_parser("evaluar", help="Evaluar una idea")
    p_eval.add_argument("idea", help="Idea a evaluar")

    p_mood = sub.add_parser("mood", help="Generar concepto visual")
    p_mood.add_argument("descripcion", help="Descripción del concepto")

    p_feat = sub.add_parser("features", help="Proponer features")
    p_feat.add_argument("area", help="Área del juego")
    p_feat.add_argument("--limitaciones", "-l", default="", help="Limitaciones")

    p_health = sub.add_parser("health", help="Verificar disponibilidad")

    args = parser.parse_args()

    creativo = CreativoJuegos(model=args.model, verbose=not args.quiet)

    if args.command == "brainstorm":
        print(creativo.brainstorm_mecanicas(args.tema))
    elif args.command == "evaluar":
        print(creativo.evaluar_idea(args.idea))
    elif args.command == "mood":
        print(creativo.generar_mood_concept(args.descripcion))
    elif args.command == "features":
        print(creativo.proponer_features(args.area, args.limitaciones))
    elif args.command == "health":
        info = creativo.resumen()
        icon = "✅" if info["available"] else "❌"
        print(f"{icon} {info['name']}")
        print(f"   Role: {info['role']}")
        print(f"   Modelo: {info['model']}")
        print(f"   Capacidades: {', '.join(info['capabilities'])}")
    else:
        parser.print_help()
        print("\n  Ejemplos:")
        print("    python factory/agent_creativo.py brainstorm 'cultivos lunares'")
        print("    python factory/agent_creativo.py evaluar 'mineria de asteroides'")
        print("    python factory/agent_creativo.py mood 'base lunar al atardecer'")
        print("    python factory/agent_creativo.py features economia")
        print("    python factory/agent_creativo.py health")


if __name__ == "__main__":
    main()
