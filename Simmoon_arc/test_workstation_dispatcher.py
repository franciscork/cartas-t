#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_workstation_dispatcher.py — Tests unitarios para el dispatcher
_run_workstation_check() de agatha_actas.py.

El dispatcher reemplaza las lambdas hardcodeadas que vivían en
FACTORY_WORKSTATIONS. Cada check_type tiene su rama con semántica
específica que estos tests cubren.

Ejecutar:
    cd Simmoon_arc
    PYTHONIOENCODING=utf-8 python -m unittest test_workstation_dispatcher -v
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# Importar el módulo con un mock de monitor_sistema si no está disponible
import agatha_actas as ag  # noqa: E402


class TestAlwaysOn(unittest.TestCase):
    """check_type='always_on' siempre devuelve True."""

    def test_always_on_returns_true(self):
        ws = {"key": "agatha_actas", "check_type": "always_on"}
        self.assertTrue(ag._run_workstation_check(ws))

    def test_always_on_ignores_target(self):
        # No importa si tiene o no check_target
        ws = {"check_type": "always_on", "check_target": None}
        self.assertTrue(ag._run_workstation_check(ws))


class TestScriptExists(unittest.TestCase):
    """check_type='script_exists' → SCRIPT_DIR/<target>.exists()."""

    def test_existing_script_returns_true(self):
        # El propio agatha_actas.py existe, lo usamos como proxy
        ws = {
            "check_type": "script_exists",
            "check_target": "agatha_actas.py",
        }
        self.assertTrue(ag._run_workstation_check(ws))

    def test_missing_script_returns_false(self):
        ws = {
            "check_type": "script_exists",
            "check_target": "this_does_not_exist_xyz.py",
        }
        self.assertFalse(ag._run_workstation_check(ws))

    def test_nested_path_supported(self):
        # creativo_juegos: "factory/agent_creativo.py" (subdirectorio)
        # No necesariamente existe, pero la lógica Path.join debe funcionar
        ws = {
            "check_type": "script_exists",
            "check_target": "factory/some_script.py",
        }
        # No assertion sobre existencia — sólo que no crashea
        result = ag._run_workstation_check(ws)
        self.assertIsInstance(result, bool)

    def test_no_target_returns_false(self):
        ws = {"check_type": "script_exists", "check_target": None}
        self.assertFalse(ag._run_workstation_check(ws))

    def test_empty_target_returns_false(self):
        ws = {"check_type": "script_exists", "check_target": ""}
        self.assertFalse(ag._run_workstation_check(ws))


class TestDbConn(unittest.TestCase):
    """check_type='db_conn' → bool(get_db_conn())."""

    def test_db_conn_true_when_conn_ok(self):
        with patch.object(ag, "get_db_conn", return_value="<mock-conn>"):
            ws = {"check_type": "db_conn"}
            self.assertTrue(ag._run_workstation_check(ws))

    def test_db_conn_false_when_conn_none(self):
        with patch.object(ag, "get_db_conn", return_value=None):
            ws = {"check_type": "db_conn"}
            self.assertFalse(ag._run_workstation_check(ws))


class TestHttp(unittest.TestCase):
    """check_type='http' → check_http(target, timeout)."""

    def test_http_default_timeout_is_3s(self):
        """Sin check_timeout, http usa 3s por defecto."""
        ws = {
            "check_type": "http",
            "check_target": "http://localhost:11434",
        }
        with patch.object(ag, "check_http", return_value=True) as mock:
            ag._run_workstation_check(ws)
        mock.assert_called_once_with("http://localhost:11434", timeout=3)

    def test_http_explicit_timeout(self):
        ws = {
            "check_type": "http",
            "check_target": "http://example.com",
            "check_timeout": 10,
        }
        with patch.object(ag, "check_http", return_value=False) as mock:
            ag._run_workstation_check(ws)
        mock.assert_called_once_with("http://example.com", timeout=10)

    def test_http_no_target_returns_false(self):
        ws = {"check_type": "http", "check_target": None}
        self.assertFalse(ag._run_workstation_check(ws))


class TestWslHttp(unittest.TestCase):
    """check_type='wsl_http' → check_wsl_http(target, timeout).

    CRÍTICO: el default debe ser 5s (no 3s como http), preservando la
    semántica original del código.
    """

    def test_wsl_http_default_timeout_is_5s(self):
        """Sin check_timeout, wsl_http usa 5s (no 3s)."""
        ws = {
            "check_type": "wsl_http",
            "check_target": "http://localhost:9119",
        }
        with patch.object(ag, "check_wsl_http", return_value=True) as mock:
            ag._run_workstation_check(ws)
        mock.assert_called_once_with("http://localhost:9119", timeout=5)

    def test_wsl_http_explicit_timeout(self):
        ws = {
            "check_type": "wsl_http",
            "check_target": "http://example.com",
            "check_timeout": 15,
        }
        with patch.object(ag, "check_wsl_http", return_value=False) as mock:
            ag._run_workstation_check(ws)
        mock.assert_called_once_with("http://example.com", timeout=15)

    def test_wsl_http_no_target_returns_false(self):
        ws = {"check_type": "wsl_http", "check_target": None}
        self.assertFalse(ag._run_workstation_check(ws))


class TestWindowsProcess(unittest.TestCase):
    """check_type='windows_process' → check_windows_process OR check_tmux_session."""

    def test_windows_process_true(self):
        ws = {
            "check_type": "windows_process",
            "check_target": "telegram_bot",
        }
        with patch.object(ag, "check_windows_process", return_value=True), \
             patch.object(ag, "check_tmux_session", return_value=False):
            self.assertTrue(ag._run_workstation_check(ws))

    def test_tmux_fallback_uses_hyphen(self):
        """CRÍTICO: telegram_bot debe probar también la sesión tmux 'telegram-bot'
        (convención: guion_bajo en keys, guion en sesiones tmux).
        """
        ws = {
            "check_type": "windows_process",
            "check_target": "telegram_bot",
        }
        with patch.object(ag, "check_windows_process", return_value=False), \
             patch.object(ag, "check_tmux_session", return_value=True) as mock_tmux:
            result = ag._run_workstation_check(ws)
        self.assertTrue(result)
        # Verificar que se llamó con la versión con guion, no con guion_bajo
        mock_tmux.assert_called_once_with("telegram-bot")

    def test_windows_process_no_target_returns_false(self):
        ws = {"check_type": "windows_process", "check_target": None}
        self.assertFalse(ag._run_workstation_check(ws))

    def test_both_false_returns_false(self):
        ws = {
            "check_type": "windows_process",
            "check_target": "some_proc",
        }
        with patch.object(ag, "check_windows_process", return_value=False), \
             patch.object(ag, "check_tmux_session", return_value=False):
            self.assertFalse(ag._run_workstation_check(ws))


class TestPathExists(unittest.TestCase):
    """check_type='path_exists' → os.path.isdir(target)."""

    def test_existing_dir_returns_true(self):
        # SCRIPT_DIR es un directorio que existe
        ws = {
            "check_type": "path_exists",
            "check_target": str(ag.SCRIPT_DIR),
        }
        self.assertTrue(ag._run_workstation_check(ws))

    def test_nonexistent_dir_returns_false(self):
        ws = {
            "check_type": "path_exists",
            "check_target": "C:\\this\\path\\does\\not\\exist\\xyz123",
        }
        self.assertFalse(ag._run_workstation_check(ws))

    def test_existing_file_returns_false(self):
        """CRÍTICO: path_exists es solo para directorios, no archivos sueltos.
        Esto preserva la semántica original (os.path.isdir, no os.path.exists).
        """
        # agatha_actas.py existe como archivo
        ws = {
            "check_type": "path_exists",
            "check_target": str(ag.SCRIPT_DIR / "agatha_actas.py"),
        }
        self.assertFalse(
            ag._run_workstation_check(ws),
            "path_exists debe rechazar archivos, solo directorios",
        )

    def test_no_target_returns_false(self):
        ws = {"check_type": "path_exists", "check_target": None}
        self.assertFalse(ag._run_workstation_check(ws))


class TestMonitorOk(unittest.TestCase):
    """check_type='monitor_ok' → _MONITOR_OK and bool(collect_report())."""

    def test_monitor_ok_true_when_both_ok(self):
        with patch.object(ag, "_MONITOR_OK", True), \
             patch.object(ag, "collect_report", return_value={"ok": True}):
            ws = {"check_type": "monitor_ok"}
            self.assertTrue(ag._run_workstation_check(ws))

    def test_monitor_ok_false_when_monitor_not_ok(self):
        with patch.object(ag, "_MONITOR_OK", False), \
             patch.object(ag, "collect_report", return_value={"ok": True}):
            ws = {"check_type": "monitor_ok"}
            self.assertFalse(ag._run_workstation_check(ws))

    def test_monitor_ok_false_when_report_empty(self):
        with patch.object(ag, "_MONITOR_OK", True), \
             patch.object(ag, "collect_report", return_value=None):
            ws = {"check_type": "monitor_ok"}
            self.assertFalse(ag._run_workstation_check(ws))


class TestUnknownCheckType(unittest.TestCase):
    """check_type desconocido → False (no asumir nada)."""

    def test_unknown_check_type_returns_false(self):
        ws = {"check_type": "inventado_xyz", "check_target": "anything"}
        self.assertFalse(ag._run_workstation_check(ws))

    def test_empty_check_type_returns_false(self):
        ws = {"check_type": "", "check_target": "anything"}
        self.assertFalse(ag._run_workstation_check(ws))

    def test_missing_check_type_returns_false(self):
        ws = {"key": "foo", "check_target": "anything"}
        self.assertFalse(ag._run_workstation_check(ws))


if __name__ == "__main__":
    unittest.main(verbosity=2)
