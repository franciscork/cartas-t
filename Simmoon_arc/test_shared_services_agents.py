#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_shared_services_agents.py — Tests unitarios para el módulo canónico
shared_services_agents.py.

Verifica:
  1. ENTITIES existe, no está vacío y todos los items tienen key+name+kinds
  2. SERVICES, AGENTS, WORKSTATIONS son vistas derivadas correctas
  3. No hay duplicación: los 4 servicios y 3 agentes aparecen como workstations
     pero NO se duplican en WORKSTATIONS (sólo en SERVICES / AGENTS)
  4. SERVICE_DEFINITIONS / AGENT_DEFINITIONS legacy mantienen shape
  5. SERVICE_DISPLAY tiene emoji/port/check para cada service
  6. SERVICE_BY_KEY / AGENT_BY_KEY / WORKSTATION_BY_KEY son lookups correctos
  7. KNOWN_*_TOTAL son dinámicos (cambian si cambia ENTITIES)

Ejecutar:
    cd Simmoon_arc
    PYTHONIOENCODING=utf-8 python -m unittest test_shared_services_agents.py -v
"""
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import shared_services_agents as ssa  # noqa: E402


class TestEntitesBase(unittest.TestCase):
    """Tests sobre la lista unificada ENTITIES."""

    def test_entities_not_empty(self):
        """ENTITIES debe tener al menos las 4 services + 3 agents + workstations únicos."""
        self.assertGreater(len(ssa.ENTITIES), 0)
        self.assertGreaterEqual(len(ssa.ENTITIES), 7, "Mínimo 4 services + 3 agents")

    def test_every_entity_has_required_fields(self):
        """Cada entidad debe tener key, name y kinds."""
        for e in ssa.ENTITIES:
            self.assertIn("key", e, f"Entidad sin 'key': {e}")
            self.assertIn("name", e, f"Entidad sin 'name': {e}")
            self.assertIn("kinds", e, f"Entidad sin 'kinds': {e}")
            self.assertIsInstance(e["kinds"], list)
            self.assertGreater(len(e["kinds"]), 0,
                               f"kinds vacío para {e.get('key')}")

    def test_no_duplicate_keys(self):
        """No debe haber dos entidades con la misma key."""
        keys = [e["key"] for e in ssa.ENTITIES]
        self.assertEqual(len(keys), len(set(keys)),
                         f"Keys duplicadas: {[k for k in keys if keys.count(k) > 1]}")


class TestDerivedViews(unittest.TestCase):
    """Tests sobre las vistas derivadas SERVICES/AGENTS/WORKSTATIONS."""

    def test_services_contains_only_service_kind(self):
        """SERVICES debe contener solo entidades con kind='service'."""
        for e in ssa.SERVICES:
            self.assertIn("service", e["kinds"],
                          f"{e['key']} está en SERVICES pero kinds={e['kinds']}")

    def test_agents_contains_only_agent_kind(self):
        """AGENTS debe contener solo entidades con kind='agent'."""
        for e in ssa.AGENTS:
            self.assertIn("agent", e["kinds"],
                          f"{e['key']} está en AGENTS pero kinds={e['kinds']}")

    def test_workstations_contains_only_workstation_kind(self):
        """WORKSTATIONS debe contener solo entidades con kind='workstation'."""
        for e in ssa.WORKSTATIONS:
            self.assertIn("workstation", e["kinds"],
                          f"{e['key']} está en WORKSTATIONS pero kinds={e['kinds']}")

    def test_known_services_count(self):
        """KNOWN_SERVICES_TOTAL debe coincidir con len(SERVICES)."""
        self.assertEqual(ssa.KNOWN_SERVICES_TOTAL, len(ssa.SERVICES))

    def test_known_agents_count(self):
        """KNOWN_AGENTS_TOTAL debe coincidir con len(AGENTS)."""
        self.assertEqual(ssa.KNOWN_AGENTS_TOTAL, len(ssa.AGENTS))


class TestNoDuplication(unittest.TestCase):
    """El test más importante: los services/agents NO deben duplicarse
    en WORKSTATIONS (sólo deben aparecer en su lista propia)."""

    def test_services_not_in_workstations_list_again(self):
        """Las 4 services NO deben aparecer como items separados en WORKSTATIONS
        (sí pueden aparecer porque tienen kind='workstation', pero NO debe haber
        una segunda entrada con los mismos metadatos).
        """
        # En realidad una service CON kind=workstation sí está en WORKSTATIONS
        # (diseño unificado). Lo que NO debe haber es DUPLICACIÓN de la misma
        # key con metadatos distintos.
        ws_keys = {e["key"] for e in ssa.WORKSTATIONS}
        svc_keys = {e["key"] for e in ssa.SERVICES}
        # Las keys pueden solapar (service puede ser workstation), pero no debe
        # haber keys duplicadas dentro de WORKSTATIONS.
        self.assertEqual(len(ws_keys), len(ssa.WORKSTATIONS),
                         "WORKSTATIONS contiene keys duplicadas")

    def test_openhuman_appears_in_all_three_lists(self):
        """openhuman es service + agent + workstation (caso especial)."""
        openhuman_in = {
            "service": "openhuman" in {e["key"] for e in ssa.SERVICES},
            "agent": "openhuman" in {e["key"] for e in ssa.AGENTS},
            "workstation": "openhuman" in {e["key"] for e in ssa.WORKSTATIONS},
        }
        self.assertTrue(all(openhuman_in.values()),
                        f"openhuman debería estar en las 3 listas, "
                        f"presencia: {openhuman_in}")

    def test_ollama_appears_in_services_and_workstations(self):
        """ollama es service + workstation."""
        ollama_in_services = "ollama" in {e["key"] for e in ssa.SERVICES}
        ollama_in_workstations = "ollama" in {e["key"] for e in ssa.WORKSTATIONS}
        self.assertTrue(ollama_in_services)
        self.assertTrue(ollama_in_workstations,
                        "ollama debe aparecer como workstation también")


class TestBackwardCompat(unittest.TestCase):
    """Los exports legacy deben seguir funcionando."""

    def test_service_definitions_is_4_tuples(self):
        """SERVICE_DEFINITIONS debe ser lista de tuplas de 4 elementos."""
        for item in ssa.SERVICE_DEFINITIONS:
            self.assertEqual(len(item), 4,
                             f"Service tupla no tiene 4 elementos: {item}")
            key, name, url, type_ = item
            self.assertIsInstance(key, str)
            self.assertIsInstance(name, str)
            self.assertIsInstance(url, str)
            self.assertIsInstance(type_, str)

    def test_agent_definitions_is_5_tuples(self):
        """AGENT_DEFINITIONS debe ser lista de tuplas de 5 elementos."""
        for item in ssa.AGENT_DEFINITIONS:
            self.assertEqual(len(item), 5,
                             f"Agent tupla no tiene 5 elementos: {item}")
            key, name, type_, health_url, check_type = item
            self.assertIsInstance(key, str)
            self.assertIsInstance(name, str)
            self.assertIsInstance(type_, str)
            # health_url puede ser None
            self.assertIsInstance(check_type, str)

    def test_service_display_has_emoji_port_check(self):
        """SERVICE_DISPLAY[key] debe tener emoji, port, check para cada service."""
        for key in {e["key"] for e in ssa.SERVICES}:
            self.assertIn(key, ssa.SERVICE_DISPLAY,
                          f"SERVICE_DISPLAY sin entrada para {key}")
            display = ssa.SERVICE_DISPLAY[key]
            self.assertIn("emoji", display)
            self.assertIn("port", display)
            self.assertIn("check", display)


class TestLookups(unittest.TestCase):
    """Tests sobre los diccionarios de lookup."""

    def test_service_by_key_complete(self):
        """SERVICE_BY_KEY debe tener una entrada por cada service."""
        for e in ssa.SERVICES:
            self.assertIn(e["key"], ssa.SERVICE_BY_KEY)
            self.assertEqual(ssa.SERVICE_BY_KEY[e["key"]]["key"], e["key"])

    def test_agent_by_key_complete(self):
        """AGENT_BY_KEY debe tener una entrada por cada agent."""
        for e in ssa.AGENTS:
            self.assertIn(e["key"], ssa.AGENT_BY_KEY)
            self.assertEqual(ssa.AGENT_BY_KEY[e["key"]]["key"], e["key"])

    def test_workstation_by_key_complete(self):
        """WORKSTATION_BY_KEY debe tener una entrada por cada workstation."""
        for e in ssa.WORKSTATIONS:
            self.assertIn(e["key"], ssa.WORKSTATION_BY_KEY)
            self.assertEqual(ssa.WORKSTATION_BY_KEY[e["key"]]["key"], e["key"])


class TestCheckTypes(unittest.TestCase):
    """Verifica que cada check_type usado tenga sentido y esté documentado."""

    def test_known_check_types(self):
        """Todos los check_types deben pertenecer al conjunto conocido."""
        known = {
            "always_on", "script_exists", "db_conn",
            "http", "wsl_http", "windows_process",
            "path_exists", "monitor_ok",
        }
        for e in ssa.ENTITIES:
            ct = e.get("check_type", "")
            if ct:
                self.assertIn(ct, known,
                              f"check_type desconocido '{ct}' en {e['key']}")

    def test_every_check_target_for_http_has_url(self):
        """check_type='http' o 'wsl_http' debe tener check_target con URL."""
        for e in ssa.ENTITIES:
            if e.get("check_type") in ("http", "wsl_http"):
                target = e.get("check_target", "")
                self.assertTrue(target.startswith("http"),
                                f"{e['key']}: check_target debe ser URL HTTP, "
                                f"got {target!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
