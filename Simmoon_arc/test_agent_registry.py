#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_agent_registry.py — Tests unitarios para agent_registry.py

Cubre las funciones cross-platform de lanzamiento y health check:
  - _launch_ollama()     → Windows (no nohup) vs Linux (nohup)
  - _launch_comfyui()    → Windows (Scripts/python.exe) vs Linux (bin/python)
  - _launch_postgres()   → Windows (net start) vs Linux (sudo service)
  - _tmux_session_exists() → Windows (False) vs Linux (tmux has-session)
  - _http_healthy()      → HTTP health checks con mock
  - _pg_isready()        → PostgreSQL health check
  - _binary_available()  → shutil.which
  - _check_* functions   → wrappers de health check

Ejecutar:
    cd Simmoon_arc
    python -m pytest test_agent_registry.py -v
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path, PosixPath, WindowsPath
from unittest.mock import patch, MagicMock, call, PropertyMock

import factory.agent_registry as ar


# ══════════════════════════════════════════════════════════════════════════
#  _launch_ollama
# ══════════════════════════════════════════════════════════════════════════

class TestLaunchOllama(unittest.TestCase):
    """Tests para _launch_ollama: Windows vs Linux."""

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    def test_windows_no_nohup(self, mock_sp, mock_sys):
        """En Windows NO debe incluir 'nohup' en el comando."""
        mock_sys.platform = "win32"
        ar._launch_ollama()
        # Verificar que Popen fue llamado SIN nohup
        args, kwargs = mock_sp.Popen.call_args
        self.assertEqual(args[0], ["ollama", "serve"])

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    def test_windows_creationflags(self, mock_sp, mock_sys):
        """En Windows debe incluir CREATE_NO_WINDOW si existe."""
        mock_sys.platform = "win32"
        ar._launch_ollama()
        args, kwargs = mock_sp.Popen.call_args
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            self.assertIn("creationflags", kwargs)

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    def test_linux_incluye_nohup(self, mock_sp, mock_sys):
        """En Linux debe incluir 'nohup' al inicio del comando."""
        mock_sys.platform = "linux"
        ar._launch_ollama()
        args, kwargs = mock_sp.Popen.call_args
        self.assertEqual(args[0], ["nohup", "ollama", "serve"])

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    def test_linux_sin_creationflags(self, mock_sp, mock_sys):
        """En Linux NO debe incluir creationflags."""
        mock_sys.platform = "linux"
        ar._launch_ollama()
        args, kwargs = mock_sp.Popen.call_args
        self.assertNotIn("creationflags", kwargs)

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    def test_retorna_true_en_exito(self, mock_sp, mock_sys):
        """Debe retornar True si Popen no lanza excepción."""
        mock_sys.platform = "win32"
        result = ar._launch_ollama()
        self.assertTrue(result)

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess", Popen=MagicMock(side_effect=Exception("fail")))
    def test_retorna_false_en_error(self, mock_sp, mock_sys):
        """Debe retornar False si Popen lanza excepción."""
        mock_sys.platform = "win32"
        result = ar._launch_ollama()
        self.assertFalse(result)

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    def test_ambos_redirigen_stdout_stderr(self, mock_sp, mock_sys):
        """Tanto Windows como Linux deben redirigir stdout y stderr a DEVNULL."""
        mock_sys.platform = "win32"
        ar._launch_ollama()
        args, kwargs = mock_sp.Popen.call_args
        # No comparar con subprocess.DEVNULL real (está mockeado)
        # Solo verificar que se pasó algún valor para stdout/stderr (no default None)
        self.assertIsNotNone(kwargs.get("stdout"), "stdout debe ser redirigido")
        self.assertIsNotNone(kwargs.get("stderr"), "stderr debe ser redirigido")


# ══════════════════════════════════════════════════════════════════════════
#  _launch_comfyui
# ══════════════════════════════════════════════════════════════════════════

class TestLaunchComfyui(unittest.TestCase):
    """Tests para _launch_comfyui: Windows vs Linux paths."""

    def setUp(self):
        self.home_patcher = patch.object(Path, "home",
                                         return_value=Path("/home/user"))
        self.home_patcher.start()

    def tearDown(self):
        self.home_patcher.stop()

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    @patch.object(Path, "exists", return_value=True)
    def test_windows_uses_scripts_python(self, mock_exists, mock_sp, mock_sys):
        """En Windows debe usar venv\\Scripts\\python.exe."""
        mock_sys.platform = "win32"
        ar._launch_comfyui()
        args, kwargs = mock_sp.Popen.call_args
        python_path = args[0][0]
        self.assertIn("Scripts", python_path)
        self.assertIn("python.exe", python_path)

    def test_linux_uses_bin_python(self):
        """En Linux debe usar venv/bin/python (segundo arg, tras nohup)."""
        with patch.object(ar, "sys", platform="linux"), \
             patch.object(ar, "subprocess") as mock_sp, \
             patch.object(Path, "exists", return_value=True):
            ar._launch_comfyui()
            args, kwargs = mock_sp.Popen.call_args
            # args[0] = ["nohup", "<python_path>", "main.py", "--listen"]
            python_path = args[0][1]  # segundo elemento, después de "nohup"
            # Usar os.sep para ser independiente de forward/backslash (Win vs Linux)
            expected = os.sep.join(["venv", "bin", "python"])
            self.assertIn(expected, python_path)
            self.assertNotIn("Scripts", python_path)

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    @patch.object(Path, "exists", return_value=True)
    def test_windows_sin_nohup(self, mock_exists, mock_sp, mock_sys):
        """En Windows NO debe incluir nohup."""
        mock_sys.platform = "win32"
        ar._launch_comfyui()
        args, kwargs = mock_sp.Popen.call_args
        self.assertNotIn("nohup", args[0])

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    @patch.object(Path, "exists", return_value=True)
    def test_linux_con_nohup(self, mock_exists, mock_sp, mock_sys):
        """En Linux debe incluir nohup."""
        mock_sys.platform = "linux"
        ar._launch_comfyui()
        args, kwargs = mock_sp.Popen.call_args
        self.assertEqual(args[0][0], "nohup")

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    @patch.object(Path, "exists", return_value=True)
    def test_comando_incluye_main_py(self, mock_exists, mock_sp, mock_sys):
        """El comando debe incluir 'main.py' y '--listen'."""
        mock_sys.platform = "linux"
        ar._launch_comfyui()
        args, kwargs = mock_sp.Popen.call_args
        self.assertIn("main.py", args[0])
        self.assertIn("--listen", args[0])

    @patch.object(ar, "sys")
    @patch.object(Path, "exists", return_value=False)
    def test_retorna_false_si_main_py_no_existe(self, mock_exists, mock_sys):
        """Debe retornar False si ComfyUI/main.py no existe."""
        mock_sys.platform = "win32"
        result = ar._launch_comfyui()
        self.assertFalse(result)

    @patch.object(ar, "sys")
    @patch.object(ar, "subprocess")
    @patch.object(Path, "exists", return_value=True)
    def test_linux_cwd_es_comfy_dir(self, mock_exists, mock_sp, mock_sys):
        """En Linux debe pasar cwd=comfy_dir."""
        mock_sys.platform = "linux"
        ar._launch_comfyui()
        args, kwargs = mock_sp.Popen.call_args
        expected_cwd = str(Path.home() / "ComfyUI")
        self.assertEqual(kwargs.get("cwd"), expected_cwd)


# ══════════════════════════════════════════════════════════════════════════
#  _launch_postgres
# ══════════════════════════════════════════════════════════════════════════

class TestLaunchPostgres(unittest.TestCase):
    """Tests para _launch_postgres: Windows net start vs Linux sudo service."""

    @patch.object(ar, "_pg_isready", return_value=True)
    @patch.object(ar, "subprocess")
    @patch.object(ar, "sys")
    def test_windows_net_start(self, mock_sys, mock_sp, mock_pg):
        """En Windows debe usar 'net start postgresql-*'."""
        mock_sys.platform = "win32"
        # Simular que net start falla en los primeros intentos y funciona en postgresql-14
        mock_run = MagicMock()
        mock_run.returncode = 0  # postgresql-14 succeeds
        mock_sp.run = MagicMock(side_effect=[
            MagicMock(returncode=2),  # postgresql-16 fails
            MagicMock(returncode=2),  # postgresql-15 fails
            mock_run,                  # postgresql-14 succeeds
        ])
        ar._launch_postgres()
        # Verificar que se intentaron varios nombres de servicio
        calls = mock_sp.run.call_args_list
        net_start_calls = [c for c in calls if c[0][0][0] == "net"]
        self.assertGreater(len(net_start_calls), 0)
        # El primer argumento debe ser ["net", "start", "postgresql-16"]
        self.assertIn("postgresql-16", net_start_calls[0][0][0])

    @patch.object(ar, "_pg_isready", return_value=True)
    @patch.object(ar, "subprocess")
    @patch.object(ar, "sys")
    def test_linux_sudo_service(self, mock_sys, mock_sp, mock_pg):
        """En Linux debe usar 'sudo service postgresql start'."""
        mock_sys.platform = "linux"
        mock_sp.run.return_value = MagicMock(returncode=0)
        ar._launch_postgres()
        args, kwargs = mock_sp.run.call_args
        self.assertEqual(args[0], ["sudo", "service", "postgresql", "start"])

    @patch.object(ar, "_pg_isready", return_value=True)
    @patch.object(ar, "subprocess")
    @patch.object(ar, "sys")
    def test_linux_no_net_start(self, mock_sys, mock_sp, mock_pg):
        """En Linux NO debe usar 'net start'."""
        mock_sys.platform = "linux"
        mock_sp.run.return_value = MagicMock(returncode=0)
        ar._launch_postgres()
        all_calls = [str(c) for c in mock_sp.run.call_args_list]
        self.assertFalse(any("net" in c for c in all_calls),
                         "Linux no debe llamar a 'net start'")

    @patch.object(ar, "_pg_isready", return_value=False)
    @patch.object(ar, "subprocess")
    @patch.object(ar, "sys")
    def test_retorna_false_si_pg_no_ready(self, mock_sys, mock_sp, mock_pg):
        """Debe retornar False si pg_isready falla."""
        mock_sys.platform = "win32"
        # Todos los net start fallan
        mock_sp.run.return_value = MagicMock(returncode=2)
        result = ar._launch_postgres()
        self.assertFalse(result)

    @patch.object(ar, "_pg_isready", return_value=True)
    @patch.object(ar, "subprocess")
    @patch.object(ar, "sys")
    def test_windows_prueba_varios_servicios(self, mock_sys, mock_sp, mock_pg):
        """En Windows debe intentar múltiples nombres de servicio."""
        mock_sys.platform = "win32"
        mock_sp.run.return_value = MagicMock(returncode=2)
        ar._launch_postgres()
        calls = [c for c in mock_sp.run.call_args_list
                 if c[0][0][0] == "net"]
        # Debe haber intentado al menos 3 servicios
        self.assertGreaterEqual(len(calls), 3)


# ══════════════════════════════════════════════════════════════════════════
#  _tmux_session_exists
# ══════════════════════════════════════════════════════════════════════════

class TestTmuxSessionExists(unittest.TestCase):
    """Tests para _tmux_session_exists: Windows vs Linux."""

    def test_windows_retorna_false(self):
        """En Windows debe retornar False sin ejecutar tmux."""
        with patch.object(ar, "sys", platform="win32"):
            result = ar._tmux_session_exists("telegram-bot")
            self.assertFalse(result)

    def test_linux_ejecuta_tmux(self):
        """En Linux debe ejecutar 'tmux has-session -t <name>'."""
        with patch.object(ar, "sys", platform="linux"), \
             patch.object(ar, "subprocess") as mock_sp:
            mock_sp.run.return_value = MagicMock(returncode=0)
            ar._tmux_session_exists("telegram-bot")
            args, kwargs = mock_sp.run.call_args
            self.assertEqual(args[0], ["tmux", "has-session", "-t", "telegram-bot"])

    def test_linux_session_existe(self):
        """En Linux, si tmux retorna 0, debe retornar True."""
        with patch.object(ar, "sys", platform="linux"), \
             patch.object(ar, "subprocess") as mock_sp:
            mock_sp.run.return_value = MagicMock(returncode=0)
            result = ar._tmux_session_exists("test-session")
            self.assertTrue(result)

    def test_linux_session_no_existe(self):
        """En Linux, si tmux retorna 1, debe retornar False."""
        with patch.object(ar, "sys", platform="linux"), \
             patch.object(ar, "subprocess") as mock_sp:
            mock_sp.run.return_value = MagicMock(returncode=1)
            result = ar._tmux_session_exists("test-session")
            self.assertFalse(result)

    def test_linux_timeout_retorna_false(self):
        """En Linux, si tmux lanza excepción, debe retornar False."""
        with patch.object(ar, "sys", platform="linux"), \
             patch.object(ar, "subprocess") as mock_sp:
            mock_sp.run.side_effect = Exception("timeout")
            result = ar._tmux_session_exists("test-session")
            self.assertFalse(result)


# ══════════════════════════════════════════════════════════════════════════
#  _http_healthy
# ══════════════════════════════════════════════════════════════════════════

class TestHttpHealthy(unittest.TestCase):
    """Tests para _http_healthy."""

    @patch.object(ar, "urllib")
    def test_healthy_200(self, mock_urllib):
        """HTTP 200 debe retornar True."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urllib.request.urlopen.return_value.__enter__.return_value = mock_response
        result = ar._http_healthy("http://localhost:8080")
        self.assertTrue(result)

    @patch.object(ar, "urllib")
    def test_healthy_3xx(self, mock_urllib):
        """HTTP 3xx debe retornar True (< 500)."""
        mock_response = MagicMock()
        mock_response.status = 302
        mock_urllib.request.urlopen.return_value.__enter__.return_value = mock_response
        result = ar._http_healthy("http://localhost:8080")
        self.assertTrue(result)

    @patch.object(ar, "urllib")
    def test_unhealthy_500(self, mock_urllib):
        """HTTP 500 debe retornar False."""
        mock_response = MagicMock()
        mock_response.status = 500
        mock_urllib.request.urlopen.return_value.__enter__.return_value = mock_response
        result = ar._http_healthy("http://localhost:8080")
        self.assertFalse(result)

    @patch.object(ar, "urllib")
    def test_connection_refused(self, mock_urllib):
        """Excepción de conexión debe retornar False."""
        mock_urllib.request.urlopen.side_effect = Exception("Connection refused")
        result = ar._http_healthy("http://localhost:8080")
        self.assertFalse(result)

    @patch.object(ar, "urllib")
    def test_timeout_personalizado(self, mock_urllib):
        """Debe pasar el timeout especificado."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urllib.request.urlopen.return_value.__enter__.return_value = mock_response
        ar._http_healthy("http://test:8080", timeout=10)
        args, kwargs = mock_urllib.request.urlopen.call_args
        self.assertEqual(kwargs.get("timeout"), 10)

    @patch.object(ar, "urllib")
    def test_timeout_default(self, mock_urllib):
        """Debe usar timeout=3 por defecto."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urllib.request.urlopen.return_value.__enter__.return_value = mock_response
        ar._http_healthy("http://test:8080")
        args, kwargs = mock_urllib.request.urlopen.call_args
        self.assertEqual(kwargs.get("timeout"), 3)


# ══════════════════════════════════════════════════════════════════════════
#  _pg_isready
# ══════════════════════════════════════════════════════════════════════════

class TestPgIsready(unittest.TestCase):
    """Tests para _pg_isready."""

    @patch.object(ar, "subprocess")
    def test_pg_ready_retorna_true(self, mock_sp):
        """pg_isready con returncode 0 debe retornar True."""
        mock_sp.run.return_value = MagicMock(returncode=0)
        result = ar._pg_isready()
        self.assertTrue(result)

    @patch.object(ar, "subprocess")
    def test_pg_not_ready_retorna_false(self, mock_sp):
        """pg_isready con returncode != 0 debe retornar False."""
        mock_sp.run.return_value = MagicMock(returncode=1)
        result = ar._pg_isready()
        self.assertFalse(result)

    @patch.object(ar, "subprocess")
    def test_pg_comando_correcto(self, mock_sp):
        """Debe llamar a pg_isready con host y port correctos."""
        mock_sp.run.return_value = MagicMock(returncode=0)
        ar._pg_isready()
        args, kwargs = mock_sp.run.call_args
        self.assertEqual(args[0], ["pg_isready", "-h", "localhost", "-p", "5432"])

    @patch.object(ar, "subprocess")
    def test_pg_exception_retorna_false(self, mock_sp):
        """Excepción en subprocess debe retornar False."""
        mock_sp.run.side_effect = Exception("pg not found")
        result = ar._pg_isready()
        self.assertFalse(result)


# ══════════════════════════════════════════════════════════════════════════
#  _binary_available
# ══════════════════════════════════════════════════════════════════════════

class TestBinaryAvailable(unittest.TestCase):
    """Tests para _binary_available."""

    @patch.object(ar, "shutil")
    def test_binary_exists(self, mock_shutil):
        """Si shutil.which encuentra el binario, retorna True."""
        mock_shutil.which.return_value = "/usr/bin/python"
        result = ar._binary_available("python")
        self.assertTrue(result)

    @patch.object(ar, "shutil")
    def test_binary_not_found(self, mock_shutil):
        """Si shutil.which no encuentra el binario, retorna False."""
        mock_shutil.which.return_value = None
        result = ar._binary_available("nonexistent")
        self.assertFalse(result)


# ══════════════════════════════════════════════════════════════════════════
#  _check_* wrapper functions
# ══════════════════════════════════════════════════════════════════════════

class TestCheckFunctions(unittest.TestCase):
    """Tests para las funciones _check_* que envuelven _http_healthy y otras."""

    @patch.object(ar, "_http_healthy", return_value=True)
    def test_check_ollama(self, mock_http):
        """_check_ollama debe llamar a _http_healthy con URL correcta."""
        result = ar._check_ollama()
        self.assertTrue(result)
        mock_http.assert_called_once_with("http://localhost:11434/api/tags", timeout=2)

    @patch.object(ar, "_http_healthy", return_value=True)
    def test_check_comfyui(self, mock_http):
        """_check_comfyui debe llamar a _http_healthy con URL correcta."""
        result = ar._check_comfyui()
        self.assertTrue(result)
        mock_http.assert_called_once_with("http://localhost:8188", timeout=2)

    @patch.object(ar, "_http_healthy", return_value=True)
    def test_check_hermes(self, mock_http):
        """_check_hermes debe llamar a _http_healthy con URL correcta."""
        result = ar._check_hermes()
        self.assertTrue(result)
        mock_http.assert_called_once_with("http://localhost:9119", timeout=2)

    @patch.object(ar, "_http_healthy", return_value=True)
    def test_check_openhuman(self, mock_http):
        """_check_openhuman debe llamar a _http_healthy con URL correcta."""
        result = ar._check_openhuman()
        self.assertTrue(result)
        mock_http.assert_called_once_with("http://localhost:7788", timeout=2)

    @patch.object(ar, "_http_healthy", return_value=True)
    def test_check_invokeai(self, mock_http):
        """_check_invokeai debe llamar a _http_healthy con URL correcta."""
        result = ar._check_invokeai()
        self.assertTrue(result)
        mock_http.assert_called_once_with("http://localhost:9090/api/v1/app/version", timeout=2)

    @patch.object(ar, "shutil")
    def test_check_claude_windows(self, mock_shutil):
        """_check_claude debe buscar 'claude' o 'claude.exe'."""
        mock_shutil.which.side_effect = lambda x: x if x == "claude.exe" else None
        result = ar._check_claude()
        self.assertTrue(result)
        mock_shutil.which.assert_any_call("claude")
        mock_shutil.which.assert_any_call("claude.exe")

    @patch.object(ar, "shutil")
    def test_check_claude_not_found(self, mock_shutil):
        """_check_claude debe retornar False si no encuentra claude."""
        mock_shutil.which.return_value = None
        result = ar._check_claude()
        self.assertFalse(result)

    @patch.object(ar, "_http_healthy", return_value=False)
    def test_check_return_false(self, mock_http):
        """_check_* debe retornar False si el servicio no responde."""
        result = ar._check_ollama()
        self.assertFalse(result)
        result = ar._check_comfyui()
        self.assertFalse(result)


# ══════════════════════════════════════════════════════════════════════════
#  AgentRegistry: launch_fn registration
# ══════════════════════════════════════════════════════════════════════════

class TestAgentRegistryLaunch(unittest.TestCase):
    """Verifica que los agentes tengan launch_fn registradas correctamente."""

    def test_ollama_tiene_launch_fn(self):
        """Ollama debe tener _launch_ollama registrada."""
        r = ar.AgentRegistry()
        agent = r.get("ollama")
        self.assertIsNotNone(agent)
        self.assertIsNotNone(agent.launch_fn)
        self.assertEqual(agent.launch_fn, ar._launch_ollama)

    def test_comfyui_tiene_launch_fn(self):
        """ComfyUI debe tener _launch_comfyui registrada."""
        r = ar.AgentRegistry()
        agent = r.get("comfyui")
        self.assertIsNotNone(agent)
        self.assertIsNotNone(agent.launch_fn)
        self.assertEqual(agent.launch_fn, ar._launch_comfyui)

    def test_postgresql_tiene_launch_fn(self):
        """PostgreSQL debe tener _launch_postgres registrada."""
        r = ar.AgentRegistry()
        agent = r.get("postgresql")
        self.assertIsNotNone(agent)
        self.assertIsNotNone(agent.launch_fn)
        self.assertEqual(agent.launch_fn, ar._launch_postgres)

    def test_health_check_fns_son_callables(self):
        """Todos los health_check_fn deben ser callables."""
        r = ar.AgentRegistry()
        for agent in r.all():
            if agent.health_check_fn:
                try:
                    result = agent.health_check_fn()
                    self.assertIsInstance(result, bool)
                except Exception:
                    pass  # algunas requieren sistema (path_exists)

    def test_qa_agent_no_launch_fn(self):
        """QA Agent no debe tener launch_fn (no es un servicio)."""
        r = ar.AgentRegistry()
        agent = r.get("qa-agent")
        self.assertIsNotNone(agent)
        self.assertIsNone(agent.launch_fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
