#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_factory_cli.py — Tests unitarios para la CLI de Factory (factory/cli.py).

Cubre:
  - build_parser() — construcción del parser de argumentos
  - get_factory() — singleton del orquestador
  - main() — ruteo de comandos
  - cmd_pipeline() — comando pipeline dedicado
  - cmd_recover() — recuperación de servicios
  - cmd_session(), cmd_monitor() — otros comandos
  - Comando help

Ejecutar:
    cd Simmoon_arc
    python -m pytest test_factory_cli.py -v
"""

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Mocks de dependencias ──────────────────────────────────────────────────
sys.modules["obsidian_memory"] = MagicMock()
sys.modules["agent_memory"] = MagicMock()

# ── Imports del sistema bajo test ─────────────────────────────────────────
from factory import cli


class TestBuildParser(unittest.TestCase):
    """Tests para build_parser()."""

    def test_parser_se_construye(self):
        """build_parser() debe retornar un ArgumentParser sin error."""
        parser = cli.build_parser()
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_parser_tiene_comando_status(self):
        """El parser debe tener subcomando 'status'."""
        parser = cli.build_parser()
        # Verificar accediendo a subparsers
        for action in parser._subparsers._group_actions:
            if action.dest == "command":
                self.assertIn("status", action.choices)

    def test_parser_tiene_todos_los_comandos(self):
        """El parser debe tener todos los subcomandos esperados."""
        parser = cli.build_parser()
        for action in parser._subparsers._group_actions:
            if action.dest == "command":
                expected = {"boot", "status", "agents", "delegate",
                            "pipeline", "recover", "session",
                            "monitor", "menu", "interactive", "help"}
                actual = set(action.choices.keys())
                for cmd in expected:
                    self.assertIn(cmd, actual,
                                  f"Falta el comando '{cmd}' en el parser")

    def test_parser_verbose_default_true(self):
        """--verbose debe tener default=True."""
        parser = cli.build_parser()
        ns = parser.parse_args(["status"])
        self.assertTrue(ns.verbose)

    def test_parser_quiet_setea_false(self):
        """--quiet debe poner verbose en False."""
        parser = cli.build_parser()
        ns = parser.parse_args(["--quiet", "status"])
        self.assertFalse(ns.verbose)

    def test_delegate_tiene_choices(self):
        """delegate type debe tener choices coding/image/llm/pipeline."""
        parser = cli.build_parser()
        for action in parser._subparsers._group_actions:
            if action.dest == "command":
                delegate_parser = action.choices.get("delegate")
                for delegate_action in delegate_parser._actions:
                    if delegate_action.dest == "type":
                        self.assertEqual(
                            set(delegate_action.choices),
                            {"coding", "image", "llm", "pipeline"}
                        )

    def test_pipeline_tiene_argumentos(self):
        """pipeline debe tener argumentos de configuración."""
        parser = cli.build_parser()
        for action in parser._subparsers._group_actions:
            if action.dest == "command":
                pipe_parser = action.choices.get("pipeline")
                pipe_args = {a.dest for a in pipe_parser._actions}
                self.assertIn("categories", pipe_args)
                self.assertIn("backend", pipe_args)
                self.assertIn("skip_generation", pipe_args)
                self.assertIn("skip_pixel", pipe_args)
                self.assertIn("skip_db", pipe_args)

    def test_recover_default_all(self):
        """recover service debe tener default='all'."""
        parser = cli.build_parser()
        for action in parser._subparsers._group_actions:
            if action.dest == "command":
                recover_parser = action.choices.get("recover")
                for recover_action in recover_parser._actions:
                    if recover_action.dest == "service":
                        self.assertEqual(recover_action.default, "all")
                        self.assertEqual(recover_action.nargs, "?")

    def test_monitor_tiene_interval(self):
        """monitor debe tener --interval con default 30."""
        parser = cli.build_parser()
        for action in parser._subparsers._group_actions:
            if action.dest == "command":
                mon_parser = action.choices.get("monitor")
                for mon_action in mon_parser._actions:
                    if mon_action.dest == "interval":
                        self.assertEqual(mon_action.default, 30)


class TestGetFactory(unittest.TestCase):
    """Tests para get_factory singleton."""

    def setUp(self):
        cli._ORCHESTRATOR = None

    @patch("factory.orchestrator.FactoryOrchestrator")
    def test_get_factory_crea_orquestador(self, mock_orch):
        """get_factory debe crear una instancia de FactoryOrchestrator."""
        factory = cli.get_factory(verbose=False)
        self.assertIsNotNone(factory)
        mock_orch.assert_called_once_with(verbose=False)

    @patch("factory.orchestrator.FactoryOrchestrator")
    def test_get_factory_singleton(self, mock_orch):
        """get_factory debe retornar la misma instancia (singleton)."""
        f1 = cli.get_factory(verbose=True)
        f2 = cli.get_factory(verbose=True)
        self.assertIs(f1, f2)
        # Solo debe crearse una vez
        mock_orch.assert_called_once_with(verbose=True)


class TestMainRouting(unittest.TestCase):
    """Tests para main() — ruteo de comandos."""

    @patch("factory.cli.cmd_status")
    @patch("factory.cli.cmd_boot")
    @patch("factory.cli.get_factory")
    def test_main_rutea_status(self, mock_get, mock_boot, mock_status):
        """main() con 'status' debe llamar a cmd_status."""
        with patch.object(sys, "argv", ["factory", "status"]):
            cli.main()
            mock_status.assert_called_once()

    @patch("factory.cli.cmd_pipeline")
    @patch("factory.cli.get_factory")
    def test_main_rutea_pipeline(self, mock_get, mock_pipeline):
        """main() con 'pipeline' debe llamar a cmd_pipeline."""
        with patch.object(sys, "argv", ["factory", "pipeline", "businesses"]):
            cli.main()
            mock_pipeline.assert_called_once()

    @patch("factory.cli.cmd_agents")
    @patch("factory.cli.get_factory")
    def test_main_rutea_agents(self, mock_get, mock_agents):
        """main() con 'agents' debe llamar a cmd_agents."""
        with patch.object(sys, "argv", ["factory", "agents"]):
            cli.main()
            mock_agents.assert_called_once()

    @patch("factory.cli.cmd_delegate")
    @patch("factory.cli.get_factory")
    def test_main_rutea_delegate(self, mock_get, mock_delegate):
        """main() con 'delegate' debe llamar a cmd_delegate."""
        with patch.object(sys, "argv", ["factory", "delegate", "llm", "hola"]):
            cli.main()
            mock_delegate.assert_called_once()

    @patch("factory.cli.cmd_recover")
    @patch("factory.cli.get_factory")
    def test_main_rutea_recover(self, mock_get, mock_recover):
        """main() con 'recover' debe llamar a cmd_recover."""
        with patch.object(sys, "argv", ["factory", "recover", "ollama"]):
            cli.main()
            mock_recover.assert_called_once()

    @patch("factory.cli.cmd_session")
    @patch("factory.cli.get_factory")
    def test_main_rutea_session(self, mock_get, mock_session):
        """main() con 'session' debe llamar a cmd_session."""
        with patch.object(sys, "argv", ["factory", "session"]):
            cli.main()
            mock_session.assert_called_once()

    @patch("factory.cli.cmd_monitor")
    @patch("factory.cli.get_factory")
    def test_main_rutea_monitor(self, mock_get, mock_monitor):
        """main() con 'monitor' debe llamar a cmd_monitor."""
        with patch.object(sys, "argv", ["factory", "monitor"]):
            cli.main()
            mock_monitor.assert_called_once()


class TestCmdRecover(unittest.TestCase):
    """Tests para cmd_recover()."""

    @patch("factory.cli.get_factory")
    def test_recover_all(self, mock_get):
        """recover con service='all' debe llamar a recover() sin args."""
        factory = MagicMock()
        factory.recover.return_value = {"ollama": True}
        mock_get.return_value = factory

        args = MagicMock()
        args.service = "all"
        args.verbose = True
        cli.cmd_recover(args)
        factory.recover.assert_called_once_with()

    @patch("factory.cli.get_factory")
    def test_recover_servicio_especifico(self, mock_get):
        """recover con nombre específico debe pasar el nombre."""
        factory = MagicMock()
        factory.recover.return_value = True
        mock_get.return_value = factory

        args = MagicMock()
        args.service = "ollama"
        args.verbose = True
        cli.cmd_recover(args)
        factory.recover.assert_called_once_with("ollama")


class TestCmdPipeline(unittest.TestCase):
    """Tests para cmd_pipeline()."""

    @patch("factory.cli.get_factory")
    def test_pipeline_con_categorias(self, mock_get):
        """pipeline con categorías debe delegar correctamente."""
        factory = MagicMock()
        # Configure delegate() to return a proper dict, not a MagicMock
        factory.delegate.return_value = {
            "success": True,
            "agent": "pipeline",
            "duration": 300.0,
            "output": "OK",
            "error": "",
            "files_modified": [],
            "task_id": "t1",
        }
        mock_get.return_value = factory

        args = MagicMock()
        args.categories = ["businesses", "vehicles"]
        args.verbose = True
        args.run_suffix = ""
        args.checkpoint = ""
        args.backend = "factory"
        args.no_loras = False
        args.lora = ""
        args.skip_generation = False
        args.skip_pixel = False
        args.skip_db = False

        cli.cmd_pipeline(args)
        factory.delegate.assert_called_once()
        call_kwargs = factory.delegate.call_args.kwargs
        self.assertEqual(call_kwargs["task_type"], "pipeline")
        self.assertEqual(call_kwargs["task"], "businesses vehicles")

    @patch("factory.cli.get_factory")
    def test_pipeline_sin_categorias_muestra_error(self, mock_get):
        """pipeline sin categorías debe mostrar error y retornar."""
        factory = MagicMock()
        mock_get.return_value = factory

        args = MagicMock()
        args.categories = []
        args.verbose = True

        with patch("builtins.print") as mock_print:
            cli.cmd_pipeline(args)
            mock_print.assert_any_call(
                "  ❌ Debes especificar al menos una categoría"
            )
            factory.delegate.assert_not_called()


class TestCmdSessionAndMonitor(unittest.TestCase):
    """Tests para cmd_session() y partes de cmd_monitor()."""

    @patch("factory.cli.get_factory")
    def test_session_llama_session_summary(self, mock_get):
        """cmd_session debe llamar a session_summary()."""
        factory = MagicMock()
        factory.session_summary.return_value = "Resumen de sesión"
        mock_get.return_value = factory

        args = MagicMock()
        args.verbose = True
        with patch("builtins.print") as mock_print:
            cli.cmd_session(args)
            factory.session_summary.assert_called_once()
            mock_print.assert_any_call("Resumen de sesión")


if __name__ == "__main__":
    unittest.main(verbosity=2)
