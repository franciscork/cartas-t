#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
system_logger.py — Sistema de Log Ligero para el Dashboard

Almacena eventos del sistema en un archivo JSONL rotativo.
Las entradas se pueden consultar desde el dashboard y desde
cualquier agente que importe este módulo.

Uso:
    from system_logger import log, get_recent
    log("Agatha Actas", "📋", "Reporte horario enviado")
    entries = get_recent(20)
"""

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LOG_DIR = Path(__file__).parent.resolve()
LOG_FILE = LOG_DIR / "system_log.jsonl"
MAX_LINES = 500      # Max entries before rotation
TRIM_TO = 250        # Keep this many after rotation


def log(source: str, icon: str, message: str):
    """Append a single log entry to the JSONL file."""
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "icon": icon,
        "message": message,
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Rotate if too large (check approx line count)
        _maybe_rotate()
    except Exception:
        pass  # Fail silently — logging should never break the caller


def get_recent(n: int = 20) -> list:
    """Return the last `n` log entries (newest first)."""
    entries = []
    try:
        if not LOG_FILE.exists():
            return entries
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return entries

    return entries[-n:][::-1]  # newest first


def _maybe_rotate():
    """Trim the log file if it exceeds MAX_LINES."""
    try:
        if not LOG_FILE.exists():
            return
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > MAX_LINES:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[-TRIM_TO:])
    except Exception:
        pass


def clear():
    """Clear all log entries."""
    try:
        LOG_FILE.unlink(missing_ok=True)
    except Exception:
        pass





# ── Error Logging ──────────────────────────────────────────────────────────

def log_exception(source: str, icon: str = "❌", exc: BaseException = None, context: str = ""):
    """Log an exception with full traceback.

    Captura y registra hasta 20 frames del traceback.
    Si no se pasa exc explícitamente, usa sys.exc_info().
    """
    try:
        if exc is None:
            exc_info = sys.exc_info()
            if exc_info[1] is None:
                return  # No active exception
            tb_str = "".join(traceback.format_exception(*exc_info, limit=10))
            exc_name = type(exc_info[1]).__name__
            exc_msg = str(exc_info[1])
        else:
            tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=10))
            exc_name = type(exc).__name__
            exc_msg = str(exc)

        msg = f"{exc_name}: {exc_msg}"
        if context:
            msg = f"[{context}] {msg}"

        log(source, icon, msg)

        # Log traceback as a multi-line entry
        for line in tb_str.strip().split('\n'):
            if line.strip():
                log(source, "·", line)
    except Exception:
        pass  # Never break the caller


# ── Helpers for Agent Activity Logging ────────────────────────────────────

def log_buffy(message: str):
    """Registra actividad de Buffy para los reportes de Agatha."""
    log("Buffy", "🦙", message)


def log_claude(message: str):
    """Registra actividad de Claude Code para los reportes de Agatha."""
    log("Claude Code", "🤖", message)


def get_agent_activity(source: str = None, limit: int = 5) -> list:
    """Obtiene actividad reciente de un agente desde el log central."""
    entries = get_recent(100)
    if source:
        entries = [e for e in entries if e.get("source") == source]
    return entries[:limit]


# Quick self-test when run directly
if __name__ == "__main__":
    print(f"  📋 system_logger.py — Log file: {LOG_FILE}")
    print(f"  Entries: {len(get_recent(9999))}")
    print()
    print("  Recent entries:")
    for e in get_recent(10):
        print(f"    [{e['ts']}] {e['icon']} {e['source']}: {e['message']}")
