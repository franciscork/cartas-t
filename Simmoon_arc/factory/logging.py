#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/logging.py — Sistema de Logging para FactoryGames

Wrapper estructurado sobre system_logger.py con niveles y formato consistente.
"""

import sys
from datetime import datetime
from typing import Optional

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Soft import of system_logger ──────────────────────────────────────────
_SYSTEM_LOGGER = None
def _get_system_logger():
    global _SYSTEM_LOGGER
    if _SYSTEM_LOGGER is None:
        try:
            import sys as _sys
            _sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.resolve()))
            from system_logger import log as _syslog
            _SYSTEM_LOGGER = _syslog
        except Exception:
            _SYSTEM_LOGGER = False
    return _SYSTEM_LOGGER if _SYSTEM_LOGGER else None


class FactoryLogger:
    """Logger estructurado con niveles: info, warn, error, task."""

    LEVEL_ICONS = {
        "info": "ℹ️",
        "warn": "⚠️",
        "error": "❌",
        "success": "✅",
        "task_start": "▶️",
        "task_end": "🏁",
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._entries: list = []
        self._syslog = _get_system_logger()

    def _log(self, level: str, source: str, message: str):
        """Registrar entrada en el log."""
        now = datetime.now().strftime("%H:%M:%S")
        icon = self.LEVEL_ICONS.get(level, "•")

        entry = {
            "ts": now,
            "level": level,
            "source": source,
            "icon": icon,
            "message": message,
        }
        self._entries.append(entry)

        if self.verbose:
            print(f"  {icon} [{source}] {message}")

        # También al system_logger (para el dashboard)
        if self._syslog:
            try:
                self._syslog(source, icon, message)
            except Exception:
                pass

    def info(self, source: str, message: str):
        self._log("info", source, message)

    def warn(self, source: str, message: str):
        self._log("warn", source, message)

    def error(self, source: str, message: str):
        self._log("error", source, message)

    def success(self, source: str, message: str):
        self._log("success", source, message)

    def task(self, agent: str, task_id: str, status: str, detail: str = ""):
        """Registrar evento de tarea."""
        msg = f"[{task_id}] {status}"
        if detail:
            msg += f" — {detail}"
        level = "success" if status in ("done", "ok", "success") else \
                "error" if status in ("failed", "error") else "info"
        self._log(level, agent, msg)

    def recent(self, n: int = 20) -> list:
        """Obtener las últimas n entradas."""
        return self._entries[-n:]

    def clear(self):
        self._entries.clear()
