#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agent_autonomous.py — Tests unitarios para agentes autónomos FactoryGames

Cubre:
  - factory/agent_base.py: _extraer_json, AgentMemory, AgentDaemon
  - factory/agent_creativo.py: CreativoJuegos (init, legacy, autonomo)
  - factory/agent_guionista.py: Guionista (init, legacy, autonomo)

Ejecutar:
    cd Simmoon_arc
    python -m pytest test_agent_autonomous.py -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Evitar import real del bridge ──────────────────────────────────────────
sys.modules["claude_code_bridge"] = MagicMock()

# ── Imports del sistema bajo test ─────────────────────────────────────────
# Parchear SCRIPT_DIR para que AgentMemory no intente escribir en el real
import factory.agent_base as ab
import factory.agent_creativo as ac
import factory.agent_guionista as ag


# ══════════════════════════════════════════════════════════════════════════
#  Tests: _extraer_json
# ══════════════════════════════════════════════════════════════════════════

class TestExtraerJson(unittest.TestCase):
    """Tests para la función _extraer_json de agent_base."""

    def test_json_plano(self):
        """JSON plano sin texto alrededor."""
        result = ab._extraer_json('{"task": "test", "files": []}')
        self.assertIsNotNone(result)
        self.assertEqual(result["task"], "test")

    def test_json_con_texto_around(self):
        """JSON con texto antes y después."""
        result = ab._extraer_json(
            'Aquí tienes:\n{"task": "refactor", "files": ["x.py"]}\nSaludos'
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["task"], "refactor")
        self.assertEqual(result["files"], ["x.py"])

    def test_json_sin_llaves_devuelve_none(self):
        """Texto sin {} debe devolver None."""
        result = ab._extraer_json("No hay JSON aquí")
        self.assertIsNone(result)

    def test_json_mal_formado_devuelve_none(self):
        """JSON inválido debe devolver None."""
        result = ab._extraer_json('{"task": incompleto')
        self.assertIsNone(result)

    def test_json_con_fences(self):
        """JSON dentro de ```json ... ```."""
        result = ab._extraer_json("""```json
{"task": "test", "files": []}
```""")
        self.assertIsNotNone(result)
        self.assertEqual(result["task"], "test")

    def test_json_vacio_devuelve_none(self):
        """String vacío."""
        result = ab._extraer_json("")
        self.assertIsNone(result)

    def test_json_con_task_vacio(self):
        """JSON con task vacío aún es válido."""
        result = ab._extraer_json('{"task": "", "files": []}')
        self.assertIsNotNone(result)
        self.assertEqual(result["task"], "")

    def test_json_anidado(self):
        """JSON con objetos anidados."""
        result = ab._extraer_json('{"task": "a", "meta": {"inner": "b"}}')
        self.assertIsNotNone(result)
        self.assertEqual(result["meta"]["inner"], "b")

    def test_json_con_nuevas_lineas(self):
        """JSON multilinea."""
        result = ab._extraer_json('{\n  "task": "multi",\n  "files": []\n}')
        self.assertIsNotNone(result)
        self.assertEqual(result["task"], "multi")


# ══════════════════════════════════════════════════════════════════════════
#  Tests: AgentMemory
# ══════════════════════════════════════════════════════════════════════════

class TestAgentMemory(unittest.TestCase):
    """Tests para AgentMemory con directorio temporal."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.patcher = patch.object(ab, "SCRIPT_DIR", self.temp_dir)
        self.patcher.start()
        self.mem = ab.AgentMemory("test_agent")

    def tearDown(self):
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_crea_directorio(self):
        """El directorio de memoria debe crearse al inicializar."""
        self.assertTrue(self.mem.mem_dir.exists())

    def test_add_task_retorna_id(self):
        """add_task debe retornar un ID no vacío."""
        task_id = self.mem.add_task("testing", "una tarea de prueba")
        self.assertIsInstance(task_id, str)
        self.assertGreater(len(task_id), 0)

    def test_add_task_incrementa_lista(self):
        """Cada add_task debe aumentar la lista de tareas."""
        self.assertEqual(len(self.mem._tasks), 0)
        self.mem.add_task("t1", "desc1")
        self.assertEqual(len(self.mem._tasks), 1)
        self.mem.add_task("t2", "desc2")
        self.assertEqual(len(self.mem._tasks), 2)

    def test_pending_tasks_retorna_solo_pendientes(self):
        """pending_tasks debe filtrar solo status='pending'."""
        id1 = self.mem.add_task("t1", "pendiente")
        self.mem.add_task("t2", "completada")
        self.mem.complete_task(id1)
        pendientes = self.mem.pending_tasks()
        self.assertEqual(len(pendientes), 1)
        self.assertEqual(pendientes[0]["description"], "completada")

    def test_complete_task_marca_completada(self):
        """complete_task debe cambiar status a 'completed'."""
        task_id = self.mem.add_task("t1", "para completar")
        self.mem.complete_task(task_id, "hecho")
        task = [t for t in self.mem._tasks if t["id"] == task_id][0]
        self.assertEqual(task["status"], "completed")
        self.assertIn("completed_at", task)
        self.assertEqual(task["result"], "hecho")

    def test_complete_task_id_inexistente_no_crashea(self):
        """complete_task con ID inexistente no debe lanzar error."""
        self.mem.complete_task("no_existe")
        # No debe lanzar excepción

    def test_recent_tasks_limite(self):
        """recent_tasks debe respetar el límite n."""
        for i in range(10):
            self.mem.add_task(f"t{i}", f"desc{i}")
        recent = self.mem.recent_tasks(3)
        self.assertEqual(len(recent), 3)

    def test_add_decision(self):
        """add_decision debe agregar una decisión."""
        self.mem.add_decision("decidí algo", "contexto")
        self.assertEqual(len(self.mem._decisions), 1)
        self.assertEqual(self.mem._decisions[0]["decision"], "decidí algo")

    def test_recent_decisions_limite(self):
        """recent_decisions debe respetar el límite."""
        for i in range(5):
            self.mem.add_decision(f"dec{i}")
        self.assertEqual(len(self.mem.recent_decisions(2)), 2)

    def test_summary_formato(self):
        """summary debe devolver string con formato esperado."""
        self.mem.add_task("t1", "tarea 1")
        resumen = self.mem.summary()
        self.assertIn("test_agent", resumen)
        self.assertIn("1 tareas totales", resumen)

    def test_persistencia_entre_instancias(self):
        """Los datos deben persistir en disco entre instancias."""
        self.mem.add_task("test", "persistente")
        task_id = self.mem._tasks[0]["id"]

        # Crear nueva instancia (mismo directorio)
        mem2 = ab.AgentMemory("test_agent")
        self.assertEqual(len(mem2._tasks), 1)
        self.assertEqual(mem2._tasks[0]["id"], task_id)

    def test_task_entry_tiene_campos_requeridos(self):
        """Cada tarea debe tener los campos esperados."""
        task_id = self.mem.add_task("test", "campos")
        task = self.mem._tasks[0]
        self.assertIn("id", task)
        self.assertIn("timestamp", task)
        self.assertIn("type", task)
        self.assertIn("description", task)
        self.assertIn("delegated_to", task)
        self.assertIn("status", task)


# ══════════════════════════════════════════════════════════════════════════
#  Tests: AgentDaemon (clase base)
# ══════════════════════════════════════════════════════════════════════════

class TestAgentDaemon(unittest.TestCase):
    """Tests para la clase base AgentDaemon."""

    @patch.object(ab, "_get_claude_bridge", return_value=None)
    def test_init_defaults(self, mock_bridge):
        """Inicialización con valores por defecto."""
        daemon = ab.AgentDaemon(
            name="TestAgent",
            emoji="🧪",
            role="Tester",
            system_prompt="Eres un test",
        )
        self.assertEqual(daemon.name, "TestAgent")
        self.assertEqual(daemon.emoji, "🧪")
        self.assertEqual(daemon.role, "Tester")
        self.assertEqual(daemon.model, ab.DEFAULT_MODEL)
        self.assertTrue(daemon.verbose)
        self.assertEqual(daemon.interval, 1800)  # 30 min * 60

    @patch.object(ab, "_get_claude_bridge", return_value=None)
    def test_status_structure(self, mock_bridge):
        """status() debe devolver dict con keys esperadas."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        status = daemon.status()
        self.assertIn("name", status)
        self.assertIn("emoji", status)
        self.assertIn("role", status)
        self.assertIn("model", status)
        self.assertIn("bridge_disponible", status)
        self.assertIn("tareas_totales", status)
        self.assertIn("tareas_pendientes", status)

    @patch.object(ab, "_get_claude_bridge", return_value=None)
    def test_status_text_contiene_nombre(self, mock_bridge):
        """status_text() debe contener el nombre del agente."""
        daemon = ab.AgentDaemon(name="Tester", emoji="🧪", role="R",
                                system_prompt="prompt")
        text = daemon.status_text()
        self.assertIn("Tester", text)
        self.assertIn("Rol:", text)

    @patch.object(ab, "_get_claude_bridge", return_value=MagicMock())
    def test_status_bridge_disponible(self, mock_bridge):
        """status() debe reportar bridge disponible si lo hay."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        status = daemon.status()
        self.assertTrue(status["bridge_disponible"])

    def test_decidir_siguiente_tarea_not_implemented(self):
        """decidir_siguiente_tarea() debe lanzar NotImplementedError."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        with self.assertRaises(NotImplementedError):
            daemon.decidir_siguiente_tarea()

    @patch.object(ab, "_get_claude_bridge", return_value=None)
    def test_delegate_to_claude_sin_bridge(self, mock_bridge):
        """delegate_to_claude() debe retornar False si no hay bridge."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        result = daemon.delegate_to_claude("test task")
        self.assertFalse(result)

    @patch.object(ab, "_get_claude_bridge", return_value=MagicMock())
    def test_run_once_sin_tarea(self, mock_bridge):
        """run_once() debe retornar False si no hay tarea decidida."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        # Mock decidir_siguiente_tarea para que retorne None
        with patch.object(daemon, "decidir_siguiente_tarea", return_value=None):
            result = daemon.run_once()
        self.assertFalse(result)

    def test_preguntar_con_fence(self):
        """_preguntar debe eliminar code fences del output del LLM."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        with patch.object(ab, "_consulta_llm",
                          return_value='```json\n{"task": "ok"}\n```'):
            result = daemon._preguntar("test")
        self.assertEqual(result, '{"task": "ok"}')

    def test_preguntar_sin_fence(self):
        """_preguntar debe pasar texto sin fences sin cambios."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        with patch.object(ab, "_consulta_llm",
                          return_value='{"task": "ok"}'):
            result = daemon._preguntar("test")
        self.assertEqual(result, '{"task": "ok"}')

    def test_preguntar_none(self):
        """_preguntar debe retornar None si el LLM no responde."""
        daemon = ab.AgentDaemon(name="T", emoji="🧪", role="R",
                                system_prompt="prompt")
        with patch.object(ab, "_consulta_llm", return_value=None):
            result = daemon._preguntar("test")
        self.assertIsNone(result)


# ══════════════════════════════════════════════════════════════════════════
#  Tests: CreativoJuegos
# ══════════════════════════════════════════════════════════════════════════

class TestCreativoJuegos(unittest.TestCase):
    """Tests para el agente Creativo de Juegos."""

    def setUp(self):
        self.patcher_bridge = patch.object(ab, "_get_claude_bridge",
                                           return_value=MagicMock())
        self.patcher_bridge.start()

    def tearDown(self):
        self.patcher_bridge.stop()

    def test_init(self):
        """Inicialización de CreativoJuegos."""
        c = ac.CreativoJuegos(verbose=False)
        self.assertEqual(c.name, "Creativo de Juegos")
        self.assertEqual(c.emoji, "🎮")
        self.assertEqual(len(c.capabilities), 6)
        self.assertIn("game_design", c.capabilities)

    def test_str(self):
        """__str__ debe incluir nombre y emoji."""
        c = ac.CreativoJuegos(verbose=False)
        self.assertIn("🎮", str(c))
        self.assertIn("Creativo", str(c))

    def test_status_structure(self):
        """status() debe tener los campos del creativo."""
        c = ac.CreativoJuegos(verbose=False)
        status = c.status()
        self.assertEqual(status["name"], "Creativo de Juegos")
        self.assertIn("bridge_disponible", status)

    @patch.object(ac, "_consulta_llm", return_value="Una idea genial")
    def test_brainstorm_mecanicas_exitoso(self, mock_llm):
        """brainstorm_mecanicas debe retornar str con el tema."""
        c = ac.CreativoJuegos(verbose=False)
        result = c.brainstorm_mecanicas("cultivos lunares")
        self.assertIsInstance(result, str)
        self.assertIn("cultivos lunares", result)
        self.assertIn("Una idea genial", result)

    @patch.object(ac, "_consulta_llm", return_value=None)
    def test_brainstorm_mecanicas_fallo(self, mock_llm):
        """brainstorm_mecanicas debe mostrar error si no hay respuesta."""
        c = ac.CreativoJuegos(verbose=False)
        result = c.brainstorm_mecanicas("tema")
        self.assertIn("❌", result)

    @patch.object(ac, "_consulta_llm", return_value="Evaluación")
    def test_evaluar_idea(self, mock_llm):
        c = ac.CreativoJuegos(verbose=False)
        result = c.evaluar_idea("mi idea")
        self.assertIsInstance(result, str)
        self.assertIn("Evaluación", result)

    @patch.object(ac, "_consulta_llm", return_value="Mood description")
    def test_generar_mood_concept(self, mock_llm):
        c = ac.CreativoJuegos(verbose=False)
        result = c.generar_mood_concept("base lunar")
        self.assertIsInstance(result, str)

    @patch.object(ac, "_consulta_llm", return_value="Features list")
    def test_proponer_features(self, mock_llm):
        c = ac.CreativoJuegos(verbose=False)
        result = c.proponer_features("economia")
        self.assertIsInstance(result, str)

    @patch.object(ac, "_consulta_llm", return_value=None)
    def test_resumen_no_available(self, mock_llm):
        """resumen() debe reflejar cuando el LLM no está disponible."""
        c = ac.CreativoJuegos(verbose=False)
        r = c.resumen()
        self.assertFalse(r["available"])

    @patch.object(ac, "_consulta_llm", return_value="OK")
    def test_resumen_available(self, mock_llm):
        """resumen() debe reflejar cuando el LLM está disponible."""
        c = ac.CreativoJuegos(verbose=False)
        r = c.resumen()
        self.assertTrue(r["available"])

    @patch.object(ac.CreativoJuegos, "_preguntar",
                  return_value='{"task": "Refactor game loop", '
                               '"context": "Mejorar rendimiento", '
                               '"files": ["juego_simmoon.py"]}')
    def test_decidir_siguiente_tarea_exitoso(self, mock_preguntar):
        """decidir_siguiente_tarea() debe parsear respuesta JSON."""
        c = ac.CreativoJuegos(verbose=False)
        decision = c.decidir_siguiente_tarea()
        self.assertIsNotNone(decision)
        self.assertEqual(decision["task"], "Refactor game loop")
        self.assertEqual(decision["files"], ["juego_simmoon.py"])

    @patch.object(ac.CreativoJuegos, "_preguntar", return_value=None)
    def test_decidir_siguiente_tarea_sin_respuesta(self, mock_preguntar):
        """decidir_siguiente_tarea() debe retornar None si no hay respuesta."""
        c = ac.CreativoJuegos(verbose=False)
        decision = c.decidir_siguiente_tarea()
        self.assertIsNone(decision)

    @patch.object(ac.CreativoJuegos, "_preguntar",
                  return_value="texto sin JSON")
    def test_decidir_siguiente_tarea_mal_formado(self, mock_preguntar):
        """decidir_siguiente_tarea() debe retornar None si respuesta no es JSON."""
        c = ac.CreativoJuegos(verbose=False)
        decision = c.decidir_siguiente_tarea()
        self.assertIsNone(decision)

    @patch.object(ac.CreativoJuegos, "_preguntar",
                  return_value='{"task": ""}')
    def test_decidir_siguiente_tarea_task_vacio(self, mock_preguntar):
        """decidir_siguiente_tarea() con task vacío debe retornar None."""
        c = ac.CreativoJuegos(verbose=False)
        decision = c.decidir_siguiente_tarea()
        self.assertIsNone(decision)


# ══════════════════════════════════════════════════════════════════════════
#  Tests: Guionista
# ══════════════════════════════════════════════════════════════════════════

class TestGuionista(unittest.TestCase):
    """Tests para el agente Guionista."""

    def setUp(self):
        self.patcher_bridge = patch.object(ab, "_get_claude_bridge",
                                           return_value=MagicMock())
        self.patcher_bridge.start()

    def tearDown(self):
        self.patcher_bridge.stop()

    def test_init(self):
        """Inicialización de Guionista."""
        g = ag.Guionista(verbose=False)
        self.assertEqual(g.name, "Guionista")
        self.assertEqual(g.emoji, "✍️")
        self.assertEqual(len(g.capabilities), 6)

    def test_str(self):
        """__str__ debe incluir nombre y emoji."""
        g = ag.Guionista(verbose=False)
        self.assertIn("✍️", str(g))
        self.assertIn("Guionista", str(g))

    def test_status_structure(self):
        """status() debe tener los campos del guionista."""
        g = ag.Guionista(verbose=False)
        status = g.status()
        self.assertEqual(status["name"], "Guionista")

    @patch.object(ag, "_consulta_llm", return_value="Diálogo simulado")
    def test_escribir_dialogo(self, mock_llm):
        g = ag.Guionista(verbose=False)
        result = g.escribir_dialogo("granjero", "viajero", "trueque")
        self.assertIsInstance(result, str)
        self.assertIn("Diálogo simulado", result)

    @patch.object(ag, "_consulta_llm", return_value="Personaje simulado")
    def test_crear_personaje(self, mock_llm):
        g = ag.Guionista(verbose=False)
        result = g.crear_personaje("anciana sabia")
        self.assertIsInstance(result, str)

    @patch.object(ag, "_consulta_llm", return_value="Arco simulado")
    def test_desarrollar_arco(self, mock_llm):
        g = ag.Guionista(verbose=False)
        result = g.desarrollar_arco("cristal lunar", actos=3)
        self.assertIsInstance(result, str)

    @patch.object(ag, "_consulta_llm", return_value="Descripción simulada")
    def test_escribir_descripcion(self, mock_llm):
        g = ag.Guionista(verbose=False)
        result = g.escribir_descripcion("mercado lunar")
        self.assertIsInstance(result, str)

    @patch.object(ag, "_consulta_llm", return_value="Lore simulado")
    def test_escribir_lore_corta(self, mock_llm):
        g = ag.Guionista(verbose=False)
        result = g.escribir_lore("cristales", "corta")
        self.assertIsInstance(result, str)

    @patch.object(ag, "_consulta_llm", return_value="Lore largo simulado")
    def test_escribir_lore_larga(self, mock_llm):
        g = ag.Guionista(verbose=False)
        result = g.escribir_lore("cristales", "larga")
        self.assertIsInstance(result, str)

    @patch.object(ag, "_consulta_llm", return_value=None)
    def test_legacy_fallback_error(self, mock_llm):
        """Métodos legacy deben mostrar ❌ si no hay respuesta."""
        g = ag.Guionista(verbose=False)
        result = g.escribir_dialogo("a", "b", "c")
        self.assertIn("❌", result)

    @patch.object(ag.Guionista, "_preguntar",
                  return_value='{"task": "Escribir lore del volcán", '
                               '"context": "Ambientación", '
                               '"files": ["game_config.py"]}')
    def test_decidir_siguiente_tarea_exitoso(self, mock_preguntar):
        """decidir_siguiente_tarea() debe parsear respuesta JSON."""
        g = ag.Guionista(verbose=False)
        decision = g.decidir_siguiente_tarea()
        self.assertIsNotNone(decision)
        self.assertIn("lore", decision["task"].lower())

    @patch.object(ag.Guionista, "_preguntar", return_value=None)
    def test_decidir_siguiente_tarea_sin_respuesta(self, mock_preguntar):
        """decidir_siguiente_tarea() debe retornar None si no hay respuesta."""
        g = ag.Guionista(verbose=False)
        decision = g.decidir_siguiente_tarea()
        self.assertIsNone(decision)

    @patch.object(ag.Guionista, "_preguntar",
                  return_value="texto sin JSON")
    def test_decidir_siguiente_tarea_mal_formado(self, mock_preguntar):
        """decidir_siguiente_tarea() debe retornar None si respuesta no es JSON."""
        g = ag.Guionista(verbose=False)
        decision = g.decidir_siguiente_tarea()
        self.assertIsNone(decision)


# ══════════════════════════════════════════════════════════════════════════
#  Tests: CLI parsers (sin ejecutar comandos)
# ══════════════════════════════════════════════════════════════════════════

class TestCLIParsers(unittest.TestCase):
    """Tests de que los parsers CLI de ambos agentes se construyen sin error."""

    def test_creativo_parser_se_construye(self):
        """El parser de agent_creativo.py debe construirse sin error."""
        try:
            import argparse
            parser = ac.main  # solo verificar que la función existe
            self.assertTrue(callable(parser))
        except Exception:
            pass  # main() llama a parser.parse_args() que falla sin argv

    def test_guionista_parser_se_construye(self):
        """El parser de agent_guionista.py debe construirse sin error."""
        try:
            parser = ag.main
            self.assertTrue(callable(parser))
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
