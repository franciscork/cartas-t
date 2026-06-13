#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_factory_orchestrator.py — Tests unitarios para FactoryOrchestrator.

Cubre:
  - _write_last_pipeline() (module-level function)
  - _get_memory() y _get_obsidian_memory() (soft imports)
  - FactoryOrchestrator.__init__, _init_components, boot
  - status(), status_text(), agents(), agents_text()
  - delegate() (pipeline y otros tipos)
  - recover() (individual y --all)
  - session_summary(), cleanup()

Ejecutar:
    cd Simmoon_arc
    python -m pytest test_factory_orchestrator.py -v
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, call

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Mocks de dependencias externas ────────────────────────────────────────
# Estas dependencias no deben importarse realmente durante los tests
sys.modules["obsidian_memory"] = MagicMock()
sys.modules["agent_memory"] = MagicMock()

# ── Imports del sistema bajo test ─────────────────────────────────────────
from factory import orchestrator as orch
from factory.agent_registry import AgentRegistry
from factory.health_monitor import HealthMonitor


# ══════════════════════════════════════════════════════════════════════════
#  Tests: _write_last_pipeline
# ══════════════════════════════════════════════════════════════════════════

class TestWriteLastPipeline(unittest.TestCase):
    """Tests para la función _write_last_pipeline del módulo."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.patcher = patch.object(orch, "_LAST_PIPELINE_FILE",
                                    self.temp_dir / ".last_pipeline.json")
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_escribe_json_valido(self):
        """Debe escribir un archivo JSON válido."""
        data = {"success": True, "cat_count": 5}
        orch._write_last_pipeline(data)
        dest = self.temp_dir / ".last_pipeline.json"
        self.assertTrue(dest.exists())
        loaded = json.loads(dest.read_text(encoding="utf-8"))
        self.assertEqual(loaded["success"], True)
        self.assertEqual(loaded["cat_count"], 5)

    def test_no_crashea_si_excepcion(self):
        """No debe lanzar excepción si falla la escritura."""
        with patch.object(Path, "write_text", side_effect=PermissionError):
            orch._write_last_pipeline({"test": True})  # No debe lanzar

    def test_escribe_con_indentacion(self):
        """El JSON debe tener indentación para legibilidad."""
        data = {"success": True}
        orch._write_last_pipeline(data)
        content = (self.temp_dir / ".last_pipeline.json").read_text(encoding="utf-8")
        self.assertIn("  ", content)  # indentación
        self.assertIn("\n", content)  # multilínea

    def test_incluye_todos_los_campos(self):
        """Debe preservar todos los campos del dict."""
        data = {
            "timestamp": "2026-01-01T00:00:00",
            "task_id": "task_123",
            "categories": "businesses vehicles",
            "cat_count": 2,
            "duration_min": 5.5,
            "gen_count": "15",
            "pix_count": "15",
            "db_status": "OK",
            "success": True,
            "error": None,
        }
        orch._write_last_pipeline(data)
        loaded = json.loads((self.temp_dir / ".last_pipeline.json").read_text(encoding="utf-8"))
        self.assertEqual(loaded["categories"], "businesses vehicles")
        self.assertEqual(loaded["error"], None)


# ══════════════════════════════════════════════════════════════════════════
#  Tests: _get_memory y _get_obsidian_memory
# ══════════════════════════════════════════════════════════════════════════

class TestGetMemory(unittest.TestCase):
    """Tests para soft imports de memoria."""

    def tearDown(self):
        orch._AGENT_MEMORY = None
        orch._OBSIDIAN_MEMORY = None

    def test_get_memory_retorna_none_sin_agent_memory(self):
        """Sin agent_memory, _get_memory debe retornar None."""
        with patch.dict("sys.modules", {"agent_memory": None}):
            result = orch._get_memory()
            self.assertIsNone(result)

    def test_get_memory_cachea_resultado(self):
        """El resultado debe cachearse (singleton)."""
        orch._AGENT_MEMORY = "cached"
        result = orch._get_memory()
        self.assertEqual(result, "cached")

    def test_get_obsidian_memory_retorna_none_sin_obsidian(self):
        """Sin obsidian_memory, _get_obsidian_memory debe retornar None."""
        with patch.dict("sys.modules", {"obsidian_memory": None}):
            result = orch._get_obsidian_memory()
            self.assertIsNone(result)

    def test_get_obsidian_memory_cachea_resultado(self):
        """El resultado de obsidian debe cachearse."""
        orch._OBSIDIAN_MEMORY = "cached_obs"
        result = orch._get_obsidian_memory()
        self.assertEqual(result, "cached_obs")


# ══════════════════════════════════════════════════════════════════════════
#  Tests: FactoryOrchestrator
# ══════════════════════════════════════════════════════════════════════════

class TestFactoryOrchestratorInit(unittest.TestCase):
    """Tests de inicialización del orquestador."""

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_init_crea_componentes(self, mock_obs, mock_mem):
        """__init__ debe crear todos los componentes."""
        factory = orch.FactoryOrchestrator(verbose=False)
        self.assertIsNotNone(factory.logger)
        self.assertIsNotNone(factory.registry)
        self.assertIsNotNone(factory.dispatcher)
        self.assertIsNotNone(factory.monitor)
        self.assertIsNone(factory.memory)  # sin PostgreSQL
        self.assertIsNone(factory.obsidian)

    @patch.object(orch, "_get_memory", return_value=MagicMock())
    @patch.object(orch, "_get_obsidian_memory", return_value=MagicMock())
    def test_init_con_memoria(self, mock_obs, mock_mem):
        """Con memoria disponible, debe asignarse."""
        factory = orch.FactoryOrchestrator(verbose=False)
        self.assertIsNotNone(factory.memory)
        self.assertIsNotNone(factory.obsidian)

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_init_registra_health_checks(self, mock_obs, mock_mem):
        """_init_components debe registrar health checks."""
        factory = orch.FactoryOrchestrator(verbose=False)
        # Debería tener checks registrados (los agentes del registry)
        self.assertGreater(len(factory.monitor._checks), 0)

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_init_stores_started_at(self, mock_obs, mock_mem):
        """Debe guardar la hora de inicio."""
        factory = orch.FactoryOrchestrator(verbose=False)
        self.assertIsNotNone(factory.started_at)
        self.assertIsInstance(factory.started_at, datetime)


class TestFactoryOrchestratorBoot(unittest.TestCase):
    """Tests del método boot()."""

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_boot_no_crashea(self, mock_obs, mock_mem):
        """boot() no debe lanzar excepción."""
        factory = orch.FactoryOrchestrator(verbose=False)
        factory.boot()  # Solo verificar que no crashea

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_boot_logs_sistema_iniciado(self, mock_obs, mock_mem):
        """boot() debe loguear que el sistema inició."""
        factory = orch.FactoryOrchestrator(verbose=False)
        with patch.object(factory.logger, "info") as mock_log:
            factory.boot()
            mock_log.assert_any_call("Orquestador", "Sistema iniciado")


class TestFactoryOrchestratorStatus(unittest.TestCase):
    """Tests de status() y status_text().

    Atención: patchamos HealthMonitor.check_all() para evitar que
    `status()` haga peticiones HTTP reales a servicios como Ollama,
    ComfyUI, Hermes, etc., que causarían timeouts en los tests.
    """

    def setUp(self):
        self.check_patcher = patch.object(HealthMonitor, "check_all",
                                          return_value={})
        self.check_patcher.start()

    def tearDown(self):
        self.check_patcher.stop()

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_status_retorna_dict(self, mock_obs, mock_mem):
        """status() debe retornar un dict con las keys esperadas."""
        factory = orch.FactoryOrchestrator(verbose=False)
        s = factory.status()
        self.assertIn("timestamp", s)
        self.assertIn("uptime", s)
        self.assertIn("agents", s)
        self.assertIn("services", s)
        self.assertIn("dispatcher", s)
        self.assertIn("memory", s)
        self.assertIn("platform", s)

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_status_agents_estructura(self, mock_obs, mock_mem):
        """El sub-dict agents debe tener total, types, health, healthy."""
        factory = orch.FactoryOrchestrator(verbose=False)
        agents = factory.status()["agents"]
        self.assertIn("total", agents)
        self.assertIn("types", agents)
        self.assertIn("health", agents)
        self.assertIn("healthy", agents)
        self.assertGreater(agents["total"], 0)

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_status_services_estructura(self, mock_obs, mock_mem):
        """El sub-dict services debe tener health, healthy, total."""
        factory = orch.FactoryOrchestrator(verbose=False)
        services = factory.status()["services"]
        self.assertIn("health", services)
        self.assertIn("healthy", services)
        self.assertIn("total", services)

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_status_text_es_string(self, mock_obs, mock_mem):
        """status_text() debe retornar un string no vacío."""
        factory = orch.FactoryOrchestrator(verbose=False)
        text = factory.status_text()
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_status_text_contiene_titulo(self, mock_obs, mock_mem):
        """status_text() debe contener el título del sistema."""
        factory = orch.FactoryOrchestrator(verbose=False)
        text = factory.status_text()
        self.assertIn("FACTORY GAMES", text)


class TestFactoryOrchestratorAgents(unittest.TestCase):
    """Tests de agents() y agents_text()."""

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_agents_retorna_lista(self, mock_obs, mock_mem):
        """agents() debe retornar una lista de dicts."""
        factory = orch.FactoryOrchestrator(verbose=False)
        agents = factory.agents()
        self.assertIsInstance(agents, list)
        self.assertGreater(len(agents), 0)
        for a in agents:
            self.assertIn("name", a)
            self.assertIn("agent_type", a)
            self.assertIn("capabilities", a)

    @patch.object(orch, "_get_memory", return_value=None)
    @patch.object(orch, "_get_obsidian_memory", return_value=None)
    def test_agents_text_es_string(self, mock_obs, mock_mem):
        """agents_text() debe retornar un string."""
        factory = orch.FactoryOrchestrator(verbose=False)
        text = factory.agents_text()
        self.assertIsInstance(text, str)
        self.assertIn("AGENTES REGISTRADOS", text.upper())


class TestFactoryOrchestratorDelegate(unittest.TestCase):
    """Tests del método delegate()."""

    def setUp(self):
        self.mem_patcher = patch.object(orch, "_get_memory", return_value=None)
        self.obs_patcher = patch.object(orch, "_get_obsidian_memory", return_value=None)
        self.mem_patcher.start()
        self.obs_patcher.start()
        self.factory = orch.FactoryOrchestrator(verbose=False)

    def tearDown(self):
        self.mem_patcher.stop()
        self.obs_patcher.stop()

    @patch.object(orch.TaskDispatcher, "dispatch")
    def test_delegate_llm_retorna_dict(self, mock_dispatch):
        """delegate() con tipo llm debe retornar un dict con success."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.agent = "ollama/model"
        mock_result.task_type = "llm"
        mock_result.duration = 1.5
        mock_result.output = "OK"
        mock_result.error = ""
        mock_result.files_modified = []
        mock_result.task_id = "task_123"
        mock_result.to_dict.return_value = {
            "success": True, "agent": "ollama/model",
            "task_type": "llm", "output": "OK",
            "error": "", "duration": 1.5,
            "files_modified": [], "task_id": "task_123",
        }
        mock_dispatch.return_value = mock_result

        result = self.factory.delegate("llm", "Hola")
        self.assertTrue(result["success"])
        self.assertEqual(result["agent"], "ollama/model")

    @patch.object(orch.TaskDispatcher, "dispatch")
    def test_delegate_coding_pasa_effort(self, mock_dispatch):
        """delegate() coding debe pasar effort al dispatcher."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.agent = "claude-code"
        mock_result.task_type = "coding"
        mock_result.duration = 10.0
        mock_result.output = "refactored"
        mock_result.error = ""
        mock_result.files_modified = ["file.py"]
        mock_result.task_id = "task_456"
        mock_result.to_dict.return_value = {
            "success": True, "agent": "claude-code",
            "task_type": "coding", "output": "refactored",
            "error": "", "duration": 10.0,
            "files_modified": ["file.py"], "task_id": "task_456",
        }
        mock_dispatch.return_value = mock_result

        self.factory.delegate("coding", "Refactor X",
                              files=["x.py"], context="urgent", effort="high")
        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        self.assertEqual(kwargs["effort"], "high")
        self.assertEqual(kwargs["files"], ["x.py"])
        self.assertEqual(kwargs["context"], "urgent")

    @patch.object(orch.TaskDispatcher, "dispatch")
    def test_delegate_pipeline_parsea_output(self, mock_dispatch):
        """delegate() pipeline debe parsear el output."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.agent = "pipeline"
        mock_result.task_type = "pipeline"
        mock_result.duration = 300.0  # 5 min
        mock_result.output = (
            "Generacion: 3 categorias completadas\n"
            "Pixel art: 2 categorias\n"
            "DB insert: OK\n"
        )
        mock_result.error = ""
        mock_result.files_modified = []
        mock_result.task_id = "task_pipe_1"
        mock_result.to_dict.return_value = {
            "success": True, "agent": "pipeline",
            "task_type": "pipeline", "output": mock_result.output,
            "error": "", "duration": 300.0,
            "files_modified": [], "task_id": "task_pipe_1",
        }
        mock_dispatch.return_value = mock_result

        result = self.factory.delegate("pipeline", "businesses vehicles")
        self.assertTrue(result["success"])
        self.assertEqual(result["agent"], "pipeline")

    @patch.object(orch.TaskDispatcher, "dispatch")
    def test_delegate_pipeline_fallido_loggea_warn(self, mock_dispatch):
        """delegate() pipeline fallido debe loguear warn."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.agent = "pipeline"
        mock_result.task_type = "pipeline"
        mock_result.duration = 60.0
        mock_result.output = ""
        mock_result.error = "Error de generación"
        mock_result.files_modified = []
        mock_result.task_id = "task_fail"
        mock_result.to_dict.return_value = {
            "success": False, "agent": "pipeline",
            "task_type": "pipeline", "output": "",
            "error": "Error de generación", "duration": 60.0,
            "files_modified": [], "task_id": "task_fail",
        }
        mock_dispatch.return_value = mock_result

        with patch.object(self.factory.logger, "warn") as mock_warn:
            self.factory.delegate("pipeline", "businesses")
            mock_warn.assert_called_once()
            args = mock_warn.call_args[0]
            self.assertIn("Falló", args[1])


class TestFactoryOrchestratorRecover(unittest.TestCase):
    """Tests de recover()."""

    def setUp(self):
        self.mem_patcher = patch.object(orch, "_get_memory", return_value=None)
        self.obs_patcher = patch.object(orch, "_get_obsidian_memory", return_value=None)
        self.mem_patcher.start()
        self.obs_patcher.start()
        self.factory = orch.FactoryOrchestrator(verbose=False)

    def tearDown(self):
        self.mem_patcher.stop()
        self.obs_patcher.stop()

    @patch.object(HealthMonitor, "recover_service", return_value=True)
    def test_recover_servicio_especifico(self, mock_recover):
        """recover con nombre de servicio debe retornar bool True."""
        result = self.factory.recover("ollama")
        self.assertTrue(result)
        mock_recover.assert_called_once_with("ollama")

    @patch.object(HealthMonitor, "recover_service", return_value=False)
    def test_recover_servicio_fallido_retorna_false(self, mock_recover):
        """recover con servicio que falla debe retornar False."""
        result = self.factory.recover("nonexistent")
        self.assertFalse(result)

    @patch.object(HealthMonitor, "recover_all",
                  return_value={"svc1": True, "svc2": False})
    def test_recover_all_retorna_dict(self, mock_recover_all):
        """recover() sin args debe retornar dict con resultados."""
        result = self.factory.recover()
        self.assertIsInstance(result, dict)
        self.assertIn("svc1", result)
        self.assertIn("svc2", result)

    @patch.object(HealthMonitor, "recover_all",
                  return_value={"svc1": True})
    def test_recover_all_contador_correcto(self, mock_recover_all):
        """recover() debe loguear contadores correctos."""
        with patch.object(self.factory.logger, "info") as mock_info:
            self.factory.recover()
            mock_info.assert_called_with(
                "Orquestador",
                "Recuperación: 1 OK, 0 fallidos"
            )


class TestFactoryOrchestratorSession(unittest.TestCase):
    """Tests de session_summary() y cleanup()."""

    def setUp(self):
        self.mem_patcher = patch.object(orch, "_get_memory", return_value=None)
        self.obs_patcher = patch.object(orch, "_get_obsidian_memory", return_value=None)
        self.mem_patcher.start()
        self.obs_patcher.start()
        self.factory = orch.FactoryOrchestrator(verbose=False)

    def tearDown(self):
        self.mem_patcher.stop()
        self.obs_patcher.stop()

    def test_session_summary_es_string(self):
        """session_summary() debe retornar un string."""
        text = self.factory.session_summary()
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)

    def test_session_summary_contiene_inicio(self):
        """session_summary() debe incluir la hora de inicio."""
        text = self.factory.session_summary()
        self.assertIn("Inicio:", text)

    @patch.object(HealthMonitor, "stop_periodic_check")
    def test_cleanup_detiene_monitor(self, mock_stop):
        """cleanup() debe detener el monitor periódico."""
        self.factory.cleanup()
        mock_stop.assert_called_once()

    @patch.object(HealthMonitor, "stop_periodic_check")
    def test_cleanup_loggea_fin(self, mock_stop):
        """cleanup() debe loguear que la sesión finalizó."""
        with patch.object(self.factory.logger, "info") as mock_info:
            self.factory.cleanup()
            mock_info.assert_called_with("Orquestador", "Sesión finalizada")


class TestFactoryOrchestratorEdgeCases(unittest.TestCase):
    """Tests de casos borde."""

    def setUp(self):
        self.mem_patcher = patch.object(orch, "_get_memory", return_value=None)
        self.obs_patcher = patch.object(orch, "_get_obsidian_memory", return_value=None)
        self.mem_patcher.start()
        self.obs_patcher.start()

    def tearDown(self):
        self.mem_patcher.stop()
        self.obs_patcher.stop()

    def test_init_sin_verbose_no_crashea(self):
        """init con verbose=False no debe lanzar error."""
        factory = orch.FactoryOrchestrator(verbose=False)
        self.assertFalse(factory.verbose)

    def test_dos_instancias_independientes(self):
        """Dos instancias deben tener started_at diferentes."""
        f1 = orch.FactoryOrchestrator(verbose=False)
        import time
        time.sleep(0.01)
        f2 = orch.FactoryOrchestrator(verbose=False)
        self.assertNotEqual(f1.started_at, f2.started_at)

    @patch.object(orch.TaskDispatcher, "dispatch")
    def test_delegate_tipo_desconocido_retorna_error(self, mock_dispatch):
        """delegate con tipo no soportado debe retornar error."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.agent = "unknown"
        mock_result.task_type = "unknown"
        mock_result.duration = 0.0
        mock_result.output = ""
        mock_result.error = "Tipo de tarea no soportado: unknown"
        mock_result.files_modified = []
        mock_result.task_id = "task_err"
        mock_result.to_dict.return_value = {
            "success": False, "agent": "unknown",
            "task_type": "unknown", "output": "",
            "error": "Tipo de tarea no soportado: unknown",
            "duration": 0.0,
            "files_modified": [], "task_id": "task_err",
        }
        mock_dispatch.return_value = mock_result

        factory = orch.FactoryOrchestrator(verbose=False)
        result = factory.delegate("unknown", "test")
        self.assertFalse(result["success"])
        self.assertIn("no soportado", result["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
