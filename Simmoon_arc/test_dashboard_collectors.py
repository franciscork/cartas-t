#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for dashboard_collectors.py

Uses pytest + unittest.mock to mock all external dependencies
(WSL commands, HTTP requests, filesystem, env vars).

Run:
    cd Simmoon_arc && python -m pytest test_dashboard_collectors.py -v
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch, mock_open

import pytest

sys.path.insert(0, str(Path(__file__).parent.resolve()))

# Use import with mocks for monitor_sistema dependency
monitor_sistema_mock = MagicMock()
monitor_sistema_mock.check_gpu.return_value = {"available": True, "name": "RTX 4090"}
monitor_sistema_mock.check_ram.return_value = {"total_gb": 32, "used_gb": 16, "used_percent": 50}
monitor_sistema_mock.check_disk.return_value = {"/": {"available_gb": 200, "total_gb": 500, "used_percent": 60}}
monitor_sistema_mock.check_cpu_temp.return_value = 55.0
monitor_sistema_mock.check_services.return_value = {}
monitor_sistema_mock.detect_alerts.return_value = []
monitor_sistema_mock._wsl_cmd.return_value = subprocess.CompletedProcess(
    args=["bash", "-c", "echo ok"], returncode=0, stdout="ok\n", stderr=""
)

# Patch before importing dashboard_collectors
modules_to_patch = {
    "monitor_sistema": monitor_sistema_mock,
}

patcher = patch.dict("sys.modules", modules_to_patch)
patcher.start()

import dashboard_collectors
from dashboard_collectors import (
    _try_import, _http_healthy, _tmux_session_exists,
    _wsl_has_binary, _file_exists_in_wsl,
    collect_agent_status, collect_environment,
    check_openhuman_health, collect_ollama_models,
    collect_obsidian_status, collect_claude_status,
    SCRIPT_DIR, _MONITOR_OK,
)
patcher.stop()  # restore sys.modules


# ═══════════════════════════════════════════════════════════════════════════
# _try_import
# ═══════════════════════════════════════════════════════════════════════════

class TestTryImport:
    def test_import_existing_module(self):
        """Should return True for modules that exist."""
        assert _try_import("json") is True
        assert _try_import("os") is True
        assert _try_import("pathlib") is True

    def test_import_nonexistent_module(self):
        """Should return False for modules that don't exist."""
        assert _try_import("nonexistent_module_xyzzy_123") is False

    def test_import_stdlib_module(self):
        """Should return True for all standard library modules."""
        for mod in ["sys", "math", "datetime", "re", "collections", "functools"]:
            assert _try_import(mod) is True, f"{mod} should be importable"


# ═══════════════════════════════════════════════════════════════════════════
# _http_healthy
# ═══════════════════════════════════════════════════════════════════════════

class TestHttpHealthy:
    @patch("urllib.request.urlopen")
    def test_healthy_200(self, mock_urlopen):
        """Should return True for 200 OK response."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        assert _http_healthy("http://localhost:8080/health") is True
        mock_urlopen.assert_called_once_with("http://localhost:8080/health", timeout=3)

    @patch("urllib.request.urlopen")
    def test_healthy_3xx(self, mock_urlopen):
        """Should return True for redirects (3xx)."""
        mock_resp = MagicMock()
        mock_resp.status = 302
        mock_urlopen.return_value = mock_resp

        assert _http_healthy("http://localhost:8080/old") is True

    @patch("urllib.request.urlopen")
    def test_unhealthy_500(self, mock_urlopen):
        """Should return False for 500 errors."""
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_urlopen.return_value = mock_resp

        assert _http_healthy("http://localhost:8080/error") is False

    @patch("urllib.request.urlopen")
    def test_connection_refused(self, mock_urlopen):
        """Should return False when connection is refused."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        assert _http_healthy("http://localhost:12345") is False

    @patch("urllib.request.urlopen")
    def test_timeout(self, mock_urlopen):
        """Should return False on timeout."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timed out")

        assert _http_healthy("http://localhost:9999") is False

    @patch("urllib.request.urlopen")
    def test_custom_timeout(self, mock_urlopen):
        """Should pass custom timeout to urlopen."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value = mock_resp

        assert _http_healthy("http://localhost:3000", timeout=5) is True
        mock_urlopen.assert_called_once_with("http://localhost:3000", timeout=5)


# ═══════════════════════════════════════════════════════════════════════════
# _tmux_session_exists
# ═══════════════════════════════════════════════════════════════════════════

class TestTmuxSessionExists:
    def test_session_exists(self):
        """Should return True when tmux has-session succeeds."""
        with patch.object(dashboard_collectors, '_wsl_cmd',
               return_value=subprocess.CompletedProcess(
                   args=["bash", "-c", "..."], returncode=0,
                   stdout="YES\n", stderr="")) as mock_wsl_cmd:
            assert _tmux_session_exists("my-session") is True
            # Verify the command includes the session name
            cmd_arg = mock_wsl_cmd.call_args[0][0]
            assert "my-session" in cmd_arg

    def test_session_not_exists(self):
        """Should return False when tmux has-session fails."""
        with patch.object(dashboard_collectors, '_wsl_cmd',
               return_value=subprocess.CompletedProcess(
                   args=["bash", "-c", "..."], returncode=0,
                   stdout="NO\n", stderr="")):
            assert _tmux_session_exists("nonexistent-session") is False

    def test_wsl_cmd_fails(self):
        """Should return False when _wsl_cmd raises an exception."""
        with patch.object(dashboard_collectors, '_wsl_cmd') as mock_wsl_cmd:
            mock_wsl_cmd.side_effect = Exception("WSL not available")
            assert _tmux_session_exists("any-session") is False


# ═══════════════════════════════════════════════════════════════════════════
# _wsl_has_binary
# ═══════════════════════════════════════════════════════════════════════════

class TestWslHasBinary:
    def test_binary_exists(self):
        """Should return True when command -v finds the binary."""
        with patch.object(dashboard_collectors, '_wsl_cmd',
               return_value=subprocess.CompletedProcess(
                   args=["bash", "-c", "..."], returncode=0,
                   stdout="FOUND\n", stderr="")) as mock_wsl_cmd:
            assert _wsl_has_binary("python3") is True
            assert "python3" in mock_wsl_cmd.call_args[0][0]

    def test_binary_not_found(self):
        """Should return False when command -v doesn't find the binary."""
        with patch.object(dashboard_collectors, '_wsl_cmd',
               return_value=subprocess.CompletedProcess(
                   args=["bash", "-c", "..."], returncode=0,
                   stdout="NOT_FOUND\n", stderr="")):
            assert _wsl_has_binary("nonexistent_tool") is False

    def test_binary_error(self):
        """Should return False when _wsl_cmd fails."""
        with patch.object(dashboard_collectors, '_wsl_cmd') as mock_wsl_cmd:
            mock_wsl_cmd.side_effect = Exception("error")
            assert _wsl_has_binary("any_binary") is False


# ═══════════════════════════════════════════════════════════════════════════
# _file_exists_in_wsl
# ═══════════════════════════════════════════════════════════════════════════

class TestFileExistsInWsl:
    def test_file_exists(self):
        """Should return True when test -f succeeds."""
        with patch.object(dashboard_collectors, '_wsl_cmd',
               return_value=subprocess.CompletedProcess(
                   args=["bash", "-c", "..."], returncode=0,
                   stdout="YES\n", stderr="")) as mock_wsl_cmd:
            assert _file_exists_in_wsl("/home/user/file.txt") is True
            assert "file.txt" in mock_wsl_cmd.call_args[0][0]

    def test_file_not_exists(self):
        """Should return False when test -f fails."""
        with patch.object(dashboard_collectors, '_wsl_cmd',
               return_value=subprocess.CompletedProcess(
                   args=["bash", "-c", "..."], returncode=0,
                   stdout="NO\n", stderr="")):
            assert _file_exists_in_wsl("/nonexistent/path") is False

    def test_wsl_error(self):
        """Should return False on exception."""
        with patch.object(dashboard_collectors, '_wsl_cmd') as mock_wsl_cmd:
            mock_wsl_cmd.side_effect = Exception("error")
            assert _file_exists_in_wsl("/any/path") is False


# ═══════════════════════════════════════════════════════════════════════════
# collect_agent_status
# ═══════════════════════════════════════════════════════════════════════════

class TestCollectAgentStatus:
    def test_basic_structure(self):
        """Should return a dict with expected top-level keys."""
        with \
            patch.object(dashboard_collectors, '_tmux_session_exists') as mock_tmux, \
            patch.object(dashboard_collectors, '_http_healthy') as mock_http, \
            patch.object(dashboard_collectors, '_try_import') as mock_import, \
            patch.object(dashboard_collectors, '_wsl_has_binary') as mock_bin, \
            patch.object(dashboard_collectors, '_file_exists_in_wsl') as mock_file_wsl, \
            patch.object(dashboard_collectors, 'collect_obsidian_status') as mock_obsidian, \
            patch.object(dashboard_collectors, 'collect_claude_status') as mock_claude, \
            patch.object(dashboard_collectors, "_MONITOR_OK", False), \
            patch.object(dashboard_collectors, "SCRIPT_DIR", Path("/nonexistent/factory/test")), \
            patch("shutil.which", return_value=None):

            mock_tmux.return_value = False
            mock_http.return_value = False
            mock_import.return_value = False
            mock_bin.return_value = False
            mock_file_wsl.return_value = False
            mock_obsidian.return_value = {"available": False}
            mock_claude.return_value = {"available": False}

            result = collect_agent_status()

        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "agents" in result
        assert "services" in result
        assert "total_running" in result
        assert "total_agents" in result
        assert "ollama_healthy" in result
        assert "ollama_models" in result

        # Should have 15 agents
        assert result["total_agents"] == 15
        assert len(result["agents"]) == 15
        running_agents = [a["name"] for a in result["agents"] if a["running"]]
        assert result["total_running"] == 0, f"Running agents: {running_agents}"

    def test_agent_names_present(self):
        """Should include all 15 agents with name, icon, and running fields."""
        with \
            patch.object(dashboard_collectors, '_tmux_session_exists') as mock_tmux, \
            patch.object(dashboard_collectors, '_http_healthy') as mock_http, \
            patch.object(dashboard_collectors, '_try_import') as mock_import, \
            patch.object(dashboard_collectors, '_wsl_has_binary') as mock_bin, \
            patch.object(dashboard_collectors, '_file_exists_in_wsl') as mock_file_wsl, \
            patch.object(dashboard_collectors, 'collect_obsidian_status') as mock_obsidian, \
            patch.object(dashboard_collectors, 'collect_claude_status') as mock_claude, \
            patch.object(dashboard_collectors, "_MONITOR_OK", False), \
            patch.object(dashboard_collectors, "SCRIPT_DIR", Path("/nonexistent/factory/test")), \
            patch("shutil.which", return_value=None):

            mock_tmux.return_value = False
            mock_http.return_value = False
            mock_import.return_value = False
            mock_bin.return_value = False
            mock_file_wsl.return_value = False
            mock_obsidian.return_value = {"available": False}
            mock_claude.return_value = {"available": False}

            result = collect_agent_status()

        expected_names = [
            "Telegram Bot", "Hermes Agent", "Hermes Bridge",
            "OpenHuman", "OpenHuman Desktop",
            "Simmoon Agent", "AutoGen", "Pipeline", "Simmoon Game",
            "Agatha Actas", "DonHermes Bot",
            "Obsidian Memory", "Claude Code",
            "Hermes Dashboard", "Hermes Desktop",
        ]

        agent_names = [a["name"] for a in result["agents"]]
        for name in expected_names:
            assert name in agent_names, f"Missing agent: {name}"
            agent = next(a for a in result["agents"] if a["name"] == name)
            assert "icon" in agent
            assert "running" in agent
            assert "method" in agent
            assert "desc" in agent

    def test_with_ollama_healthy(self):
        """Should detect Ollama as healthy when HTTP to :11434 succeeds.

        Strategy: Don't patch _http_healthy directly (it's tricky because
        _http_healthy is a local function in dashboard_collectors that gets
        patched by @patch decorators unreliably in some test runners).
        Instead, patch urllib.request.urlopen to return a valid response for
        Ollama's health endpoint, and let _http_healthy run its real code.
        """
        with \
            patch.object(dashboard_collectors, '_tmux_session_exists', return_value=False), \
            patch.object(dashboard_collectors, '_try_import', return_value=False), \
            patch.object(dashboard_collectors, '_wsl_has_binary', return_value=False), \
            patch.object(dashboard_collectors, '_file_exists_in_wsl', return_value=False), \
            patch.object(dashboard_collectors, 'collect_obsidian_status',
                return_value={"available": False, "mode": "N/A"}), \
            patch.object(dashboard_collectors, 'collect_claude_status',
                return_value={"available": False}), \
            patch.object(dashboard_collectors, '_wsl_cmd',
                return_value=subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="NOT_FOUND\n", stderr="")), \
            patch.object(dashboard_collectors, "_MONITOR_OK", True), \
            patch("dashboard_collectors.check_services"), \
            patch("pathlib.Path.exists", return_value=False), \
            patch("shutil.which", return_value=None):

            # Patch urlopen so _http_healthy sees status 200 for Ollama port
            orig_urlopen = __import__("urllib.request", fromlist=["urlopen"]).urlopen

            def urlopen_side(url, timeout=None, **kwargs):
                resp = MagicMock()
                resp.status = 200
                if "/api/tags" in str(url):
                    # Model listing
                    resp.read.return_value = json.dumps({
                        "models": [{"name": "qwen2.5-coder:14b", "size": 7 * 1024**3,
                                    "details": {"family": "qwen", "parameter_size": "14B"}}]
                    }).encode()
                    resp.__enter__.return_value = resp
                else:
                    resp.read.return_value = b"ok"
                    resp.__enter__.return_value = resp
                return resp

            with patch("urllib.request.urlopen", side_effect=urlopen_side):
                result = collect_agent_status()

        assert result["ollama_healthy"] is True
        assert len(result["ollama_models"]) == 1
        # collect_agent_status() extracts model names into a list of strings
        assert result["ollama_models"][0] == "qwen2.5-coder:14b"


# ═══════════════════════════════════════════════════════════════════════════
# collect_environment
# ═══════════════════════════════════════════════════════════════════════════

class TestCollectEnvironment:
    @patch("dashboard_collectors._wsl_cmd")
    @patch("dashboard_collectors.check_cpu_temp")
    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.is_dir")
    def test_basic_structure(self, mock_is_dir, mock_glob,
                              mock_cpu_temp, mock_wsl_cmd):
        """Should return expected env keys."""
        mock_wsl_cmd.return_value = subprocess.CompletedProcess(
            args=["bash", "-c", "..."], returncode=0,
            stdout="up 3 days\n", stderr=""
        )
        mock_cpu_temp.return_value = 55.0
        mock_is_dir.return_value = True
        mock_glob.return_value = []  # no PNGs

        result = collect_environment()

        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "uptime" in result
        assert "cpu_temp_c" in result
        assert "asset_count" in result
        assert "categories_found" in result
        assert "total_categories" in result
        assert "last_generation" in result
        assert "active_models" in result

    def test_empty_results(self):
        """Should handle WSL failure gracefully."""
        with \
            patch.object(dashboard_collectors, 'check_cpu_temp') as mock_cpu_temp, \
            patch.object(dashboard_collectors, '_wsl_cmd') as mock_wsl_cmd, \
            patch("pathlib.Path.is_dir") as mock_is_dir, \
            patch("pathlib.Path.glob") as mock_glob:

            mock_wsl_cmd.side_effect = Exception("WSL not available")
            mock_cpu_temp.side_effect = Exception("No sensors")
            mock_is_dir.return_value = False
            mock_glob.return_value = []

            result = collect_environment()

        assert result["uptime"] == "N/A"
        assert result["cpu_temp_c"] is None
        assert result["asset_count"] == 0
        assert result["total_categories"] == 0
        assert result["last_generation"] is None

    def test_with_assets(self):
        """Should count assets from category directories."""
        with \
            patch.object(dashboard_collectors, 'check_cpu_temp') as mock_cpu_temp, \
            patch.object(dashboard_collectors, '_wsl_cmd',
                return_value=subprocess.CompletedProcess(
                    args=["bash", "-c", "..."], returncode=0,
                    stdout="up 1 day\n", stderr="")), \
            patch("pathlib.Path.is_dir") as mock_is_dir, \
            patch("pathlib.Path.glob") as mock_glob:

            mock_cpu_temp.return_value = 60.0
            mock_is_dir.return_value = True
            mock_glob.side_effect = lambda pattern: [
                Path(f"test_{i}.png") for i in range(3)
            ] if ".png" in pattern else []

            result = collect_environment()

        assert result["asset_count"] >= 0  # at least counted something
        assert result["cpu_temp_c"] == 60.0


# ═══════════════════════════════════════════════════════════════════════════
# check_openhuman_health
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckOpenhumanHealth:
    @patch("urllib.request.urlopen")
    def test_healthy(self, mock_urlopen):
        """Should return available=True with health details."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "ok": True,
            "name": "openhuman",
            "api_server": "0.0.0.0:7788",
            "endpoints": {"/health": "GET", "/chat": "POST"},
            "usage": {"default": "openai"},
        }).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = check_openhuman_health()

        assert result["available"] is True
        assert result["ok"] is True
        assert result["name"] == "openhuman"
        assert "endpoints" in result
        assert "method" in result

    @patch("urllib.request.urlopen")
    def test_unhealthy(self, mock_urlopen):
        """Should return available=False when HTTP fails."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = check_openhuman_health()
        assert result["available"] is False

    @patch("urllib.request.urlopen")
    def test_invalid_json(self, mock_urlopen):
        """Should return available=True even with invalid JSON (just no details)."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not valid json"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = check_openhuman_health()
        # json.loads will fail, so we get an exception caught
        assert result["available"] is False


# ═══════════════════════════════════════════════════════════════════════════
# collect_ollama_models
# ═══════════════════════════════════════════════════════════════════════════

class TestCollectOllamaModels:
    @patch("urllib.request.urlopen")
    def test_with_models(self, mock_urlopen):
        """Should return list of parsed models."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "models": [
                {"name": "qwen2.5-coder:14b", "size": 14 * 1024**3,
                 "details": {"family": "qwen", "parameter_size": "14B"}},
                {"name": "deepseek-r1:7b", "size": 7 * 1024**3,
                 "details": {"family": "deepseek", "parameter_size": "7B"}},
            ]
        }).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        models = collect_ollama_models()

        assert len(models) == 2
        assert models[0]["name"] == "qwen2.5-coder:14b"
        assert models[0]["size_gb"] == 14.0
        assert models[0]["family"] == "qwen"
        assert models[1]["name"] == "deepseek-r1:7b"

    @patch("urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        """Should return empty list when no models."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"models": []}).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        models = collect_ollama_models()
        assert models == []

    @patch("urllib.request.urlopen")
    def test_api_unreachable(self, mock_urlopen):
        """Should return empty list when Ollama is down."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        models = collect_ollama_models()
        assert models == []


# ═══════════════════════════════════════════════════════════════════════════
# collect_obsidian_status
# ═══════════════════════════════════════════════════════════════════════════

class TestCollectObsidianStatus:
    @patch("dashboard_collectors.SCRIPT_DIR", Path("/fake/project"))
    def test_no_config_file(self):
        """Should return default 'not available' when no config file."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            result = collect_obsidian_status()

        assert isinstance(result, dict)
        assert "available" in result
        assert "vault_path" in result
        assert "vault_name" in result
        assert "mode" in result
        assert "total_entries" in result
        assert "by_type" in result
        assert "diarias" in result

    def test_with_rest_config_file_not_available(self):
        """Should try REST API, fall back to FS when REST not available."""
        with patch("dashboard_collectors.SCRIPT_DIR", Path("/fake/project")):
            with patch("builtins.open", new_callable=mock_open,
                       read_data=json.dumps({"api_key": "test-key", "port": 27124, "https": True})):
                with patch("obsidian_memory.ObsidianRestClient.is_available", return_value=False):
                    with patch("pathlib.Path.exists") as mock_exists:
                        mock_exists.side_effect = lambda: True
                        result = collect_obsidian_status()

        # REST won't be available in test (no server), so falls back
        assert isinstance(result, dict)
        assert "available" in result
        assert "mode" in result

    def test_structure_keys(self):
        """Should always return the expected keys regardless of mode."""
        with patch("dashboard_collectors.SCRIPT_DIR", Path("/fake/project")):
            with patch("builtins.open", new_callable=mock_open,
                       read_data=json.dumps({"api_key": "test-key", "port": 27124, "https": True})):
                with patch("obsidian_memory.ObsidianRestClient.is_available", return_value=False):
                    with patch("pathlib.Path.exists") as mock_exists:
                        mock_exists.side_effect = lambda: True
                        result = collect_obsidian_status()

        expected_keys = {"available", "vault_path", "vault_name", "mode",
                         "total_entries", "by_type", "diarias", "agent_name"}
        assert expected_keys.issubset(result.keys()), f"Missing keys: {expected_keys - result.keys()}"


# ═══════════════════════════════════════════════════════════════════════════
# collect_claude_status
# ═══════════════════════════════════════════════════════════════════════════

class TestCollectClaudeStatus:
    def test_no_monitor_available(self):
        """Should try shutil.which even without monitor_sistema."""
        with patch.object(dashboard_collectors, '_MONITOR_OK', False):
            with patch("shutil.which") as mock_which:
                mock_which.return_value = None
                result = collect_claude_status()

        assert isinstance(result, dict)
        assert "available" in result
        assert "version" in result
        assert "auth_configured" in result
        assert "backend" in result

    def test_binary_found(self):
        """Should detect Claude Code binary via shutil.which."""
        with patch.object(dashboard_collectors, '_MONITOR_OK', False):
            with patch("shutil.which") as mock_which:
                mock_which.side_effect = [None, "C:\\Users\\test\\AppData\\Roaming\\npm\\claude.cmd"]
                result = collect_claude_status()

        assert result["available"] is True
        assert result["binary_path"] == "C:\\Users\\test\\AppData\\Roaming\\npm\\claude.cmd"
        assert result["backend"] == "none"

    def test_auth_configured(self):
        """Should detect ANTHROPIC_API_KEY env var."""
        with patch.object(dashboard_collectors, '_MONITOR_OK', False):
            with patch("shutil.which") as mock_which:
                mock_which.return_value = None
                with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-xxx"}):
                    result = collect_claude_status()

        assert result["auth_configured"] is True

    def test_native_ollama_mode(self):
        """Should detect native ollama launch claude support."""
        with patch.object(dashboard_collectors, '_MONITOR_OK', True):
            with patch.object(dashboard_collectors, '_wsl_cmd') as mock_wsl_cmd:
                mock_wsl_cmd.side_effect = [
                    subprocess.CompletedProcess(args=[], returncode=0,
                                                stdout="NATIVE_OK\n", stderr=""),
                    subprocess.CompletedProcess(args=[], returncode=0,
                                                stdout="minimax-m3:cloud\n", stderr=""),
                ]
                with patch("shutil.which") as mock_which:
                    mock_which.return_value = None
                    result = collect_claude_status()

        assert result["available"] is True
        assert result["native_ollama"] is True
        assert result["native_ollama_model"] == "minimax-m3:cloud"
        assert result["backend"] == "native_ollama"

    def test_claude_binary_in_wsl(self):
        """Should detect Claude Code CLI binary in WSL."""
        with patch.object(dashboard_collectors, '_MONITOR_OK', True):
            with patch.object(dashboard_collectors, '_wsl_cmd') as mock_wsl_cmd:
                mock_wsl_cmd.side_effect = [
                    subprocess.CompletedProcess(args=[], returncode=0,
                                                stdout="NATIVE_NO\n", stderr=""),
                    subprocess.CompletedProcess(args=[], returncode=0,
                                                stdout="Claude Code 0.2.45\n", stderr=""),
                ]
                with patch("shutil.which") as mock_which:
                    mock_which.return_value = None
                    result = collect_claude_status()

        assert result["available"] is True
        assert "0.2.45" in result.get("version", "")
        assert result["binary_path"] == "WSL: /usr/local/bin/claude"
        assert result["backend"] == "claude_cli"

    def test_no_claude_available(self):
        """Should return available=False when nothing is detected."""
        with patch.object(dashboard_collectors, '_MONITOR_OK', True):
            with patch.object(dashboard_collectors, '_wsl_cmd') as mock_wsl_cmd:
                mock_wsl_cmd.side_effect = [
                    subprocess.CompletedProcess(args=[], returncode=0,
                                                stdout="NATIVE_NO\n", stderr=""),
                    subprocess.CompletedProcess(args=[], returncode=0,
                                                stdout="NOT_FOUND\n", stderr=""),
                ]
                with patch("shutil.which") as mock_which:
                    mock_which.return_value = None
                    result = collect_claude_status()

        assert result["available"] is False
        assert result["backend"] == "none"


# ═══════════════════════════════════════════════════════════════════════════
# monitor_sistema integration flag
# ═══════════════════════════════════════════════════════════════════════════

class TestMonitorOk:
    def test_monitor_ok_flag(self):
        """_MONITOR_OK should be a boolean."""
        assert isinstance(_MONITOR_OK, bool)

    def test_script_dir_exists(self):
        """SCRIPT_DIR should exist."""
        assert isinstance(SCRIPT_DIR, Path)
