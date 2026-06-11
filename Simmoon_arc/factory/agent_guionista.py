#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/agent_guionista.py — ✍️ Guionista

Especialista en narrativa, diálogos de personajes, arcos argumentales,
world-building y contenido textual para SIMMOON y otros proyectos.

Uso:
    from agent_guionista import Guionista
    guion = Guionista()
    dialogo = guion.escribir_dialogo("granjero", "mercader", "trueque")
    print(guion.desarrollar_arco("El misterio del cráter luminoso"))
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, List

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

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

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen25-64k"


class Guionista:
    """Agente Guionista — narrativa, diálogos y world-building."""

    def __init__(self, model: str = DEFAULT_MODEL, verbose: bool = True):
        self.model = model
        self.verbose = verbose
        self.name = "Guionista"
        self.emoji = "✍️"
        self.role = "Narrativa, Diálogos y World-Building"
        self.capabilities = [
            "narrative_design", "dialog_writing", "story_development",
            "world_building", "character_creation", "descriptive_text"
        ]

    # ── LLM call ─────────────────────────────────────────────────────────

    def _consulta(self, prompt: str, temperature: float = 0.7,
                  max_tokens: int = 2048) -> Optional[str]:
        """Consultar el LLM local con el system prompt del guionista."""
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

    # ── Diálogos ─────────────────────────────────────────────────────────

    def escribir_dialogo(self, personaje1: str, personaje2: str,
                         situacion: str, tono: str = "natural") -> str:
        """Escribir un diálogo entre dos personajes.

        Args:
            personaje1: Nombre y descripción breve del primer personaje
            personaje2: Nombre y descripción breve del segundo
            situacion: Contexto de la conversación
            tono: natural, humorístico, dramático, misterioso

        Returns:
            Diálogo formateado para el juego
        """
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
        """Crear un personaje completo con personalidad y voz.

        Args:
            rol: Rol del personaje (ej: "anciana sabia", "mercader ambulante")
            contexto: Contexto del mundo donde vive

        Returns:
            Ficha de personaje formateada
        """
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

    # ── Narrativa ────────────────────────────────────────────────────────

    def desarrollar_arco(self, premisa: str, actos: int = 3) -> str:
        """Desarrollar un arco argumental a partir de una premisa.

        Args:
            premisa: Idea central del arco
            actos: Número de actos/capítulos

        Returns:
            Estructura del arco argumental
        """
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
        """Escribir una descripción evocadora para un elemento del juego.

        Args:
            elemento: Qué describir (ej: "puesto de mercado", "cristal lunar")
            contexto: Contexto adicional

        Returns:
            Texto descriptivo listo para usar en el juego
        """
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
            f"- Si aplica, incluir un detalle interactivo (qué pasa si el jugador..."
            f" acciona/toca/interactúa)"
        )
        return self._consulta(prompt, temperature=0.65) or "❌ No se pudo generar descripción."

    # ── World-building ───────────────────────────────────────────────────

    def escribir_lore(self, tema: str, extension: str = "corta") -> str:
        """Escribir lore para el mundo del juego.

        Args:
            tema: Tema del lore (ej: "origen de los cristales lunares")
            extension: 'corta' (1 párrafo) o 'larga' (3 párrafos)

        Returns:
            Texto de lore
        """
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
    """Interfaz CLI para el Guionista."""
    import argparse
    parser = argparse.ArgumentParser(
        description="✍️ Guionista — Narrativa, Diálogos y World-Building"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama")
    parser.add_argument("--quiet", "-q", action="store_true", help="Modo silencioso")

    sub = parser.add_subparsers(dest="command")

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
    else:
        parser.print_help()
        print("\n  Ejemplos:")
        print("    python factory/agent_guionista.py dialogo 'granjero' 'viajero' 'trueque'")
        print("    python factory/agent_guionista.py personaje 'anciana sabia'")
        print("    python factory/agent_guionista.py arco 'cristal lunar perdido'")
        print("    python factory/agent_guionista.py describir 'puesto de mercado'")
        print("    python factory/agent_guionista.py lore 'origen de los simmoon'")
        print("    python factory/agent_guionista.py health")


if __name__ == "__main__":
    main()
