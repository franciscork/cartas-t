#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/agent_creativo.py — 🎮 Creativo de Juegos

Especialista en diseño de juegos, mecánicas, dirección creativa y 
brainstorming. Genera ideas innovadoras para SIMMOON y otros proyectos.

Ahora con MODO AUTÓNOMO (--daemon): decide qué debe hacer Claude y delega.

Uso:
    # Modo interactivo (existente)
    python factory/agent_creativo.py brainstorm 'cultivos lunares'
    python factory/agent_creativo.py evaluar 'mineria de asteroides'
    python factory/agent_creativo.py mood 'base lunar al atardecer'
    python factory/agent_creativo.py features economia
    python factory/agent_creativo.py health

    # Modo autónomo (NUEVO)
    python factory/agent_creativo.py daemon
    python factory/agent_creativo.py daemon --interval 60
    python factory/agent_creativo.py status
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from factory.agent_base import AgentDaemon, _consulta_llm, _extraer_json

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:latest"

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


class CreativoJuegos(AgentDaemon):
    """Agente Creativo de Juegos — brainstorming, diseño y ahora autónomo.

    Extiende AgentDaemon para operar en modo autónomo: decide qué tareas
    delegar a Claude Code y supervisa su progreso.
    """

    def __init__(self, model: str = DEFAULT_MODEL, verbose: bool = True,
                 interval_minutos: int = 30):
        # Inicializar la parte AgentDaemon
        super().__init__(
            name="Creativo de Juegos",
            emoji="🎮",
            role="Dirección Creativa y Diseño de Mecánicas",
            model=model,
            system_prompt=SYSTEM_PROMPT,
            verbose=verbose,
            interval_minutos=interval_minutos,
        )
        # Atributos específicos del creativo
        self.capabilities = [
            "game_design", "mechanics_innovation", "creative_brainstorming",
            "mood_concept", "feature_design", "game_balance"
        ]

    # ── LLM call (legacy) ─────────────────────────────────────────────

    def _consulta(self, prompt: str, temperature: float = 0.8,
                  max_tokens: int = 2048) -> Optional[str]:
        """Consultar el LLM local con el system prompt del creativo.
        Mantenido por retrocompatibilidad.
        """
        return _consulta_llm(
            SYSTEM_PROMPT, prompt, self.model, temperature, max_tokens
        )

    # ── Brainstorming (legacy) ─────────────────────────────────────────

    def brainstorm_mecanicas(self, tema: str, cantidad: int = 5) -> str:
        """Generar ideas de mecánicas de juego para un tema específico."""
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
        """Evaluar una idea de juego desde perspectiva de game design."""
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
        """Generar descripción de mood/concepto visual para un escenario."""
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
        """Proponer nuevas features para un área del juego."""
        prompt = (
            f"Propón 3 nuevas features para el área de **{area}** "
            f"en nuestro juego SIMMOON.\n\n"
        )
        if limitaciones:
            prompt += f"Considera estas limitaciones: {limitaciones}\n\n"
        prompt += (
            f"Para cada feature:\n"
            f"1. Nombre atractivo\n"
            f"2. Qué problema resuelve o qué diversión aporta\n"
            f"3. Implementación simplificada (2-3 pasos)\n"
            f"4. Cómo afecta a las demás mecánicas\n\n"
            f"Prioriza features que maximicen diversión con mínimo esfuerzo técnico."
        )
        return self._consulta(prompt, temperature=0.8) or "❌ No se pudieron generar features."

    # ── Lógica autónoma ───────────────────────────────────────────────

    def decidir_siguiente_tarea(self) -> Optional[Dict[str, Any]]:
        """Decidir qué tarea creativa delegar a Claude.

        Evalúa el estado actual del proyecto y propone la siguiente
        tarea de diseño/creatividad que debería abordar Claude.
        """
        pendientes = self.memoria.pending_tasks()
        recientes = self.memoria.recent_tasks(3)

        contexto_pendientes = ""
        if pendientes:
            contexto_pendientes = (
                f"Tareas pendientes de Claude: "
                f"{', '.join(t['description'][:60] for t in pendientes[:3])}"
            )

        contexto_recientes = ""
        if recientes:
            contexto_recientes = (
                f"Últimas tareas delegadas: "
                f"{', '.join(t['description'][:60] for t in recientes)}"
            )

        prompt = (
            f"Eres el Director Creativo de FactoryGames. "
            f"Debes decidir QUÉ tarea delegar a Claude Code a continuación.\n\n"
            f"Contexto actual del proyecto:\n"
            f"- SimMoon: constructor de colonia lunar (PyGame, isométrico)\n"
            f"- 131 edificios en 22 categorías\n"
            f"- Sistema de turnos con recursos (créditos, energía, O2, agua, presión)\n"
            f"- Zonificación: 4 zonas (alojamiento, comercial, industrial, ecológico)\n\n"
            f"{contexto_pendientes}\n"
            f"{contexto_recientes}\n\n"
            f"Elige UNA tarea concreta de diseño/mecánicas para delegar a Claude.\n"
            f"Debe ser:\n"
            f"- Algo que MEJORE el juego (no mantenerlo igual)\n"
            f"- Implementable en 1-2 horas de trabajo\n"
            f"- Que use las capacidades de Claude (refactor, implementar, debuggear)\n\n"
            f"Responde SOLO con JSON:\n"
            f"{{\n"
            f'  "task": "descripción clara de la tarea (máx 200 chars)",\n'
            f'  "context": "contexto adicional para Claude (máx 300 chars)",\n'
            f'  "files": ["archivo1.py", "archivo2.py"],\n'
            f'  "razon": "por qué esta tarea es prioritaria"\n'
            f"}}\n\n"
            f"Si no hay nada que hacer, responde: {{\"task\": \"\"}}"
        )

        respuesta = self._preguntar(prompt, temperature=0.6)
        if not respuesta:
            return None

        decision = _extraer_json(respuesta)
        if not decision or not decision.get("task"):
            if self.verbose:
                print(f"     ⚠️  Respuesta no parseable como JSON")
                print(f"     Raw (primeros 200c): {respuesta[:200]}...")
            return None
        return {
            "task": decision["task"],
            "context": decision.get("context", ""),
            "files": decision.get("files", []),
        }

    # ── Utilidad ─────────────────────────────────────────────────────

    def resumen(self) -> dict:
        """Resumen del agente para registro."""
        return {
            "name": self.name,
            "emoji": self.emoji,
            "role": self.role,
            "model": self.model,
            "capabilities": self.capabilities,
            "available": self._consulta("Responde SOLO: OK", temperature=0.1) is not None,
            "modo_autonomo": True,
            "bridge_disponible": self.bridge is not None,
        }

    def __str__(self):
        return f"{self.emoji} {self.name} — {self.role}"


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    """Interfaz CLI para el Creativo de Juegos."""
    import argparse
    parser = argparse.ArgumentParser(
        description="🎮 Creativo de Juegos — Brainstorming y Diseño Autónomo"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama")
    parser.add_argument("--quiet", "-q", action="store_true", help="Modo silencioso")

    sub = parser.add_subparsers(dest="command")

    # Comandos existentes
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

    # Comandos nuevos (modo autónomo)
    p_daemon = sub.add_parser("daemon", help="🧠 Modo autónomo (decide y delega a Claude)")
    p_daemon.add_argument("--interval", "-i", type=int, default=30,
                          help="Intervalo entre ciclos en minutos (default: 30)")

    p_status = sub.add_parser("status", help="Estado del agente autónomo")

    p_once = sub.add_parser("once", help="Ejecutar un ciclo de decisión ahora")

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
        print(f"   🧠 Modo autónomo: {'✅' if info['modo_autonomo'] else '❌'}")
        print(f"   🔗 Bridge Claude: {'✅' if info['bridge_disponible'] else '❌'}")

    # ── Nuevos comandos autónomos ──
    elif args.command == "daemon":
        print(creativo.status_text())
        creativo.run_daemon(interval_minutos=args.interval)

    elif args.command == "status":
        print(creativo.status_text())

    elif args.command == "once":
        ok = creativo.run_once()
        print(f"\n  {'✅' if ok else 'ℹ️'} Ciclo completado")
        print(creativo.memoria.summary())

    else:
        parser.print_help()
        print("\n  Ejemplos:")
        print("    python factory/agent_creativo.py brainstorm 'cultivos lunares'")
        print("    python factory/agent_creativo.py evaluar 'mineria de asteroides'")
        print("    python factory/agent_creativo.py daemon          # 🆕 Autónomo")
        print("    python factory/agent_creativo.py daemon -i 60    # Cada 60 min")
        print("    python factory/agent_creativo.py once            # Un ciclo")
        print("    python factory/agent_creativo.py status          # Estado")
        print("    python factory/agent_creativo.py health")


if __name__ == "__main__":
    main()
