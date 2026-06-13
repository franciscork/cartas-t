#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/agent_guionista.py — ✍️ Guionista

Especialista en narrativa, diálogos de personajes, arcos argumentales,
world-building y contenido textual para SIMMOON y otros proyectos.

Ahora con MODO AUTÓNOMO (--daemon): decide qué tareas narrativas delegar
a Claude Code y supervisa su progreso.

Uso:
    # Modo interactivo (existente)
    python factory/agent_guionista.py dialogo 'granjero' 'viajero' 'trueque'
    python factory/agent_guionista.py personaje 'anciana sabia'
    python factory/agent_guionista.py arco 'cristal lunar perdido'
    python factory/agent_guionista.py describir 'puesto de mercado'
    python factory/agent_guionista.py lore 'origen de los simmoon'
    python factory/agent_guionista.py health

    # Modo autónomo (NUEVO)
    python factory/agent_guionista.py daemon
    python factory/agent_guionista.py daemon --interval 60
    python factory/agent_guionista.py status
    python factory/agent_guionista.py once
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
DEFAULT_MODEL = "qwen3-14b-32k"  # qwen25-64k no disponible; qwen3-14b-32k es el más cercano con contexto largo

# ── System prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un **Guionista** experto, parte del equipo FactoryGames.
Tu especialidad es la **narrativa, diálogos y construcción de mundos**.

Tus habilidades:
- Escritura de diálogos con personalidad para cada personaje
- Desarrollo de arcos argumentales y tramas
- World-building: crear lore coherente y atractivo
- Descripciones evocadoras para escenarios y objetos
- Narrativa emergente: historias que surgen de las mecánicas
- Escritura de cartas, diarios, murales y textos del juego

Tono: literario, evocador, concreto. Usa emojis narrativos (✍️ 📜 🎭 🏰).
Cada texto debe servir AL JUEGO: ser útil, integrable y coherente con el lore.
"""


class Guionista(AgentDaemon):
    """Agente Guionista — narrativa, diálogos y world-building.

    Extiende AgentDaemon para operar en modo autónomo: decide qué tareas
    narrativas delegar a Claude Code y supervisa su progreso.
    """

    def __init__(self, model: str = DEFAULT_MODEL, verbose: bool = True,
                 interval_minutos: int = 45):
        # Inicializar la parte AgentDaemon
        super().__init__(
            name="Guionista",
            emoji="✍️",
            role="Narrativa, Diálogos y World-Building",
            model=model,
            system_prompt=SYSTEM_PROMPT,
            verbose=verbose,
            interval_minutos=interval_minutos,
        )
        # Atributos específicos del guionista
        self.capabilities = [
            "narrative_design", "dialog_writing", "story_development",
            "world_building", "character_creation", "descriptive_text"
        ]

    # ── LLM call (legacy) ─────────────────────────────────────────────

    def _consulta(self, prompt: str, temperature: float = 0.7,
                  max_tokens: int = 2048) -> Optional[str]:
        """Consultar el LLM local con el system prompt del guionista.
        Mantenido por retrocompatibilidad.
        """
        return _consulta_llm(
            SYSTEM_PROMPT, prompt, self.model, temperature, max_tokens
        )

    # ── Diálogos (legacy) ─────────────────────────────────────────────

    def escribir_dialogo(self, personaje1: str, personaje2: str,
                         situacion: str, tono: str = "natural") -> str:
        """Escribir un diálogo entre dos personajes."""
        prompt = (
            f"Escribe un diálogo entre estos personajes:\n\n"
            f"**{personaje1}** y **{personaje2}**\n\n"
            f"Situación: {situacion}\n"
            f"Tono: {tono}\n\n"
            f"Reglas:\n"
            f"- Cada personaje debe tener voz propia (vocabulario, actitud)\n"
            f"- Máximo 8 intercambios (líneas)\n"
            f"- El diálogo debe revelar algo: personalidad, lore, o pista\n"
            f"- Incluye acotaciones breves de acción/emoción entre líneas\n"
            f"- Que sea útil directamente en el juego (NPCs, eventos, tutorial)"
        )
        return self._consulta(prompt, temperature=0.8) or "❌ No se pudo generar diálogo."

    def crear_personaje(self, rol: str, contexto: str = "") -> str:
        """Crear un personaje completo con personalidad y voz."""
        prompt = (
            f"Crea un personaje para nuestro juego:\n\n"
            f"Rol: **{rol}**\n"
        )
        if contexto:
            prompt += f"Contexto del mundo: {contexto}\n\n"
        prompt += (
            f"Incluye:\n"
            f"1. Nombre (con gancho narrativo)\n"
            f"2. Apariencia (3-4 frases, que se pueda pixel-artear)\n"
            f"3. Personalidad (virtud + defecto)\n"
            f"4. Voz: cómo habla (ej: 'pausado, usa refranes antiguos')\n"
            f"5. Qué sabe / qué secretos conoce\n"
            f"6. Qué necesita del jugador\n"
            f"7. Frase célebre (una línea que lo defina)"
        )
        return self._consulta(prompt, temperature=0.75) or "❌ No se pudo crear personaje."

    # ── Narrativa (legacy) ───────────────────────────────────────────

    def desarrollar_arco(self, premisa: str, actos: int = 3) -> str:
        """Desarrollar un arco argumental a partir de una premisa."""
        prompt = (
            f"Desarrolla un arco argumental en {actos} actos para:\n\n"
            f"**{premisa}**\n\n"
            f"Para cada acto:\n"
            f"- Evento principal (qué pasa)\n"
            f"- Conflicto (qué desafía al jugador)\n"
            f"- Revelación (qué aprende o descubre)\n"
            f"- Personajes involucrados\n"
            f"- Cómo conecta con las mecánicas del juego\n\n"
            f"El arco debe poder contarse SIN texto extenso (juego pixel-art),\n"
            f"usando imágenes, acciones y mínimos diálogos."
        )
        return self._consulta(prompt, temperature=0.8) or "❌ No se pudo desarrollar arco."

    def escribir_descripcion(self, elemento: str, contexto: str = "") -> str:
        """Escribir una descripción evocadora para un elemento del juego."""
        prompt = (
            f"Escribe una descripción evocadora y concisa para:\n\n"
            f"**{elemento}**\n"
        )
        if contexto:
            prompt += f"Contexto: {contexto}\n\n"
        prompt += (
            f"La descripción debe:\n"
            f"- Ser de 2-4 líneas (máximo 300 caracteres)\n"
            f"- Usar lenguaje sensorial (vista, oído, olfato)\n"
            f"- Sugerir una historia detrás del objeto/lugar\n"
            f"- Ser integrable directamente en tooltips o pop-ups del juego\n"
            f"- Si aplica, incluir un detalle interactivo (qué pasa si el jugador "
            f"acciona/toca/interactúa)"
        )
        return self._consulta(prompt, temperature=0.65) or "❌ No se pudo generar descripción."

    # ── World-building (legacy) ──────────────────────────────────────

    def escribir_lore(self, tema: str, extension: str = "corta") -> str:
        """Escribir lore para el mundo del juego."""
        prompt = (
            f"Escribe lore para nuestro mundo SIMMOON sobre:\n\n"
            f"**{tema}**\n\n"
        )
        if extension == "corta":
            prompt += "Máximo 1 párrafo (4-6 líneas). Debe ser impactante y memorable.\n"
        else:
            prompt += "3 párrafos. El primero: el mito/leyenda. El segundo: lo que se sabe.\n"
            prompt += "El tercero: la verdad oculta (solo nosotros sabemos esto).\n"
        prompt += (
            f"\nEl lore debe:\n"
            f"- Sentir que pertenece a un mundo vivo\n"
            f"- Tener gancho para una misión o secreto\n"
            f"- Ser coherente con el tono del juego (ciencia ficción rural)\n"
            f"- Poder fragmentarse en objetos coleccionables (diarios, murales, NPCs)"
        )
        return self._consulta(prompt, temperature=0.8) or "❌ No se pudo generar lore."

    # ── Lógica autónoma ──────────────────────────────────────────────

    def decidir_siguiente_tarea(self) -> Optional[Dict[str, Any]]:
        """Decidir qué tarea narrativa delegar a Claude.

        Evalúa el estado del proyecto (qué lore/diálogos hay pendientes)
        y propone la siguiente tarea narrativa para Claude.
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
            f"Eres el Guionista de FactoryGames. "
            f"Debes decidir QUÉ tarea narrativa delegar a Claude Code a continuación.\n\n"
            f"Contexto del proyecto:\n"
            f"- SimMoon: constructor de colonia lunar (PyGame, isométrico)\n"
            f"- 131 edificios en 22 categorías\n"
            f"- Sistema de turnos con recursos\n"
            f"- Ambientación: ciencia ficción rural / colonia minera en la Luna\n"
            f"- NPCs: comerciantes, mineros, científicos, agricultores lunares\n\n"
            f"{contexto_pendientes}\n"
            f"{contexto_recientes}\n\n"
            f"Elige UNA tarea concreta de narrativa/diálogos/lore para delegar a Claude.\n"
            f"Debe ser:\n"
            f"- Algo que ENRIQUEZCA la narrativa del juego\n"
            f"- Implementable en 1-2 horas de trabajo\n"
            f"- Texto/lore utilizable directamente en el juego\n\n"
            f"Responde SOLO con JSON:\n"
            f"{{\n"
            f'  "task": "descripción clara de la tarea narrativa (máx 200 chars)",\n'
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
    """Interfaz CLI para el Guionista."""
    import argparse
    parser = argparse.ArgumentParser(
        description="✍️ Guionista — Narrativa, Diálogos y World-Building Autónomo"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama")
    parser.add_argument("--quiet", "-q", action="store_true", help="Modo silencioso")

    sub = parser.add_subparsers(dest="command")

    # Comandos existentes
    p_dialogo = sub.add_parser("dialogo", help="Escribir diálogo")
    p_dialogo.add_argument("personaje1", help="Primer personaje")
    p_dialogo.add_argument("personaje2", help="Segundo personaje")
    p_dialogo.add_argument("situacion", help="Situación/contexto")
    p_dialogo.add_argument("--tono", default="natural", help="Tono del diálogo")

    p_personaje = sub.add_parser("personaje", help="Crear personaje")
    p_personaje.add_argument("rol", help="Rol del personaje")
    p_personaje.add_argument("--contexto", "-c", default="", help="Contexto del mundo")

    p_arco = sub.add_parser("arco", help="Desarrollar arco argumental")
    p_arco.add_argument("premisa", help="Premisa del arco")
    p_arco.add_argument("--actos", type=int, default=3, help="Número de actos")

    p_desc = sub.add_parser("describir", help="Escribir descripción")
    p_desc.add_argument("elemento", help="Elemento a describir")
    p_desc.add_argument("--contexto", "-c", default="", help="Contexto")

    p_lore = sub.add_parser("lore", help="Escribir lore del mundo")
    p_lore.add_argument("tema", help="Tema del lore")
    p_lore.add_argument("--extension", "-e", default="corta",
                        choices=["corta", "larga"], help="Extensión")

    p_health = sub.add_parser("health", help="Verificar disponibilidad")

    # Comandos nuevos (modo autónomo)
    p_daemon = sub.add_parser("daemon", help="🧠 Modo autónomo (decide y delega a Claude)")
    p_daemon.add_argument("--interval", "-i", type=int, default=45,
                          help="Intervalo entre ciclos en minutos (default: 45)")

    p_status = sub.add_parser("status", help="Estado del agente autónomo")

    p_once = sub.add_parser("once", help="Ejecutar un ciclo de decisión ahora")

    args = parser.parse_args()

    guion = Guionista(model=args.model, verbose=not args.quiet)

    if args.command == "dialogo":
        print(guion.escribir_dialogo(args.personaje1, args.personaje2,
                                      args.situacion, args.tono))
    elif args.command == "personaje":
        print(guion.crear_personaje(args.rol, args.contexto))
    elif args.command == "arco":
        print(guion.desarrollar_arco(args.premisa, args.actos))
    elif args.command == "describir":
        print(guion.escribir_descripcion(args.elemento, args.contexto))
    elif args.command == "lore":
        print(guion.escribir_lore(args.tema, args.extension))
    elif args.command == "health":
        info = guion.resumen()
        icon = "✅" if info["available"] else "❌"
        print(f"{icon} {info['name']}")
        print(f"   Role: {info['role']}")
        print(f"   Modelo: {info['model']}")
        print(f"   Capacidades: {', '.join(info['capabilities'])}")
        print(f"   🧠 Modo autónomo: {'✅' if info['modo_autonomo'] else '❌'}")
        print(f"   🔗 Bridge Claude: {'✅' if info['bridge_disponible'] else '❌'}")

    # ── Nuevos comandos autónomos ──
    elif args.command == "daemon":
        print(guion.status_text())
        guion.run_daemon(interval_minutos=args.interval)

    elif args.command == "status":
        print(guion.status_text())

    elif args.command == "once":
        ok = guion.run_once()
        print(f"\n  {'✅' if ok else 'ℹ️'} Ciclo completado")
        print(guion.memoria.summary())

    else:
        parser.print_help()
        print("\n  Ejemplos:")
        print("    python factory/agent_guionista.py dialogo 'granjero' 'viajero' 'trueque'")
        print("    python factory/agent_guionista.py personaje 'anciana sabia'")
        print("    python factory/agent_guionista.py arco 'cristal lunar perdido'")
        print("    python factory/agent_guionista.py daemon          # 🆕 Autónomo")
        print("    python factory/agent_guionista.py daemon -i 60    # Cada 60 min")
        print("    python factory/agent_guionista.py once            # Un ciclo")
        print("    python factory/agent_guionista.py status          # Estado")
        print("    python factory/agent_guionista.py health")


if __name__ == "__main__":
    main()
