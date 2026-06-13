#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_cargar_ayer_counts.py — Tests unitarios para el conteo de
services_active en _cargar_ayer_obsidian.py.

Casos cubiertos:
  1. 10 eventos con source='ollama' → services_active=1 (cada servicio
     se cuenta como máximo una vez, no se multiplica por nº de eventos)
  2. Mensajes con 'llamó al cliente' / 'llamando' NO deben sumar al
     conteo de 'ollama' (el word-boundary regex previene el falso positivo)
  3. Día sin eventos → services_active=0 (no se rellena al total)

Ejecutar:
    cd Simmoon_arc
    PYTHONIOENCODING=utf-8 python -m unittest test_cargar_ayer_counts.py -v
"""
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from _cargar_ayer_obsidian import _count_services_active  # noqa: E402


class TestCountServicesActive(unittest.TestCase):
    """Tests para _count_services_active(events)."""

    def test_ten_ollama_events_count_one(self):
        """10 eventos con source='ollama' deben contar como 1 servicio."""
        events = [
            {"source": "ollama", "message": f"event {i}"}
            for i in range(10)
        ]
        count = _count_services_active(events)
        # Solo 'ollama' matchea. Los demás 3 servicios (comfyui, postgresql,
        # openhuman) no aparecen, así que services_active == 1.
        self.assertEqual(count, 1,
                         f"Esperaba 1 (solo ollama), obtuve {count}")

    def test_llamo_al_cliente_no_false_positive(self):
        """Mensajes con 'llamó' / 'llamando' NO deben contar como ollama."""
        # Caso explícito del bug que vino a arreglar el refactor:
        # substring 'ollama' NO debe matchear dentro de 'llamó al cliente'.
        events = [
            {"source": "user_support", "message": "llamó al cliente por teléfono"},
            {"source": "user_support", "message": "El usuario llamó para pedir info"},
            {"source": "user_support", "message": "Llamando al soporte técnico"},
            {"source": "user_support", "message": "Por favor llama mañana"},
        ]
        count = _count_services_active(events)
        # Ningún servicio tiene match (ningún source == key, ningún
        # \b{key}\b aparece en los messages).
        self.assertEqual(count, 0,
                         f"Esperaba 0 (ningún servicio matchea), obtuve {count}")

    def test_no_events_returns_zero(self):
        """Día sin eventos debe dar services_active=0."""
        events = []
        count = _count_services_active(events)
        self.assertEqual(count, 0,
                         f"Esperaba 0 (sin eventos), obtuve {count}")

    # ── Tests bonus (cobertura adicional) ─────────────────────────────────

    def test_exact_source_match_is_case_insensitive(self):
        """Match exacto en source funciona case-insensitive."""
        events = [
            {"source": "OLLAMA", "message": "engine started"},
            {"source": "Ollama", "message": "inference done"},
        ]
        count = _count_services_active(events)
        # Ambos eventos tienen source 'ollama' (case-insensitive),
        # pero el servicio se cuenta UNA sola vez.
        self.assertEqual(count, 1)

    def test_word_boundary_match_in_message(self):
        """Match por word-boundary en message funciona para 'comfyui' y 'ollama'."""
        events = [
            {"source": "monitor", "message": "ComfyUI: inference complete"},
            {"source": "monitor", "message": "Started ollama service"},
            {"source": "monitor", "message": "PostgreSQL connection pool ready"},
        ]
        count = _count_services_active(events)
        # 3 servicios matchean (comfyui, ollama, postgresql).
        # openhuman no aparece → no se cuenta.
        self.assertEqual(count, 3)

    def test_word_boundary_prevents_partial_match(self):
        """El word-boundary previene matches tipo 'ollama' en 'ollamamiento'."""
        # 'ollamamiento' empieza con 'ollama' pero NO es la palabra completa.
        # \bollama\b no debe matchear dentro de 'ollamamiento' porque el
        # carácter siguiente ('m') es \w (no hay límite de palabra).
        events = [
            {"source": "user", "message": "Hicimos un ollamamiento público"},
        ]
        count = _count_services_active(events)
        self.assertEqual(count, 0,
                         f"Esperaba 0 (word-boundary previene match parcial "
                         f"dentro de palabra compuesta), obtuve {count}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
