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
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LOG_DIR = Path(__file__).parent.resolve()
RETENTION_DAYS = 7   # Conservar logs de los últimos N días
MAX_LINES = 500      # Max entries per daily file before trim
TRIM_TO = 250        # Keep this many after trim
_last_cleanup_date = ""  # Cache para _cleanup_old_logs (una vez al día)


def _today_str() -> str:
    """Fecha de hoy en formato YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def _log_file(date_str: str = None) -> Path:
    """Ruta al archivo de log para una fecha (default: hoy)."""
    if date_str is None:
        date_str = _today_str()
    return LOG_DIR / f"system_log.{date_str}.jsonl"


def _list_log_files() -> list:
    """Lista archivos de log diarios ordenados del más reciente al más antiguo."""
    pattern = re.compile(r"system_log\.(\d{4}-\d{2}-\d{2})\.jsonl$")
    files = []
    try:
        for p in sorted(LOG_DIR.glob("system_log.*.jsonl"), reverse=True):
            m = pattern.match(p.name)
            if m:
                files.append((m.group(1), p))
    except Exception:
        pass
    return files


def log(source: str, icon: str, message: str):
    """Append a single log entry to today's JSONL file."""
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "icon": icon,
        "message": message,
    }
    try:
        log_path = _log_file()  # system_log.YYYY-MM-DD.jsonl
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Trim if today's file exceeds MAX_LINES
        _maybe_rotate(log_path)

        # Clean up old daily files beyond RETENTION_DAYS
        _cleanup_old_logs()
    except Exception:
        pass  # Fail silently — logging should never break the caller


def get_recent(n: int = 20, days: int = None) -> list:
    """Return the last `n` log entries (newest first).

    Lee de los archivos diarios, empezando por hoy y retrocediendo
    hasta `days` días (default: RETENTION_DAYS).

    Args:
        n: número máximo de entradas a devolver
        days: días hacia atrás para buscar (default: RETENTION_DAYS)
    """
    if days is None:
        days = RETENTION_DAYS

    entries = []
    try:
        daily_files = _list_log_files()
        for date_str, filepath in daily_files[:days]:
            if not filepath.exists():
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            if len(entries) >= n * 2:  # Suficiente margen
                break
    except Exception:
        return entries

    # Keep only the most recent n, newest first
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return entries[:n]


def _maybe_rotate(log_path: Path = None):
    """Trim a daily log file if it exceeds MAX_LINES."""
    try:
        if log_path is None:
            log_path = _log_file()
        if not log_path.exists():
            return
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > MAX_LINES:
            with open(log_path, "w", encoding="utf-8") as f:
                f.writelines(lines[-TRIM_TO:])
    except Exception:
        pass


def _cleanup_old_logs():
    """Eliminar archivos de log más antiguos que RETENTION_DAYS.

    Usa un cache de fecha para solo ejecutar la limpieza una vez al día.
    """
    global _last_cleanup_date
    today = _today_str()
    if _last_cleanup_date == today:
        return  # Ya se limpió hoy
    _last_cleanup_date = today

    try:
        cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        for date_str, filepath in _list_log_files():
            if date_str < cutoff_str:
                try:
                    filepath.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass


def clear():
    """Clear all daily log files."""
    try:
        for _, filepath in _list_log_files():
            try:
                filepath.unlink(missing_ok=True)
            except Exception:
                pass
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
    print(f"  📋 system_logger.py — Daily log files (retention: {RETENTION_DAYS} days)")
    all_files = _list_log_files()
    print(f"  Log files: {len(all_files)}")
    for d, fp in all_files[:7]:
        try:
            count = sum(1 for _ in open(fp, encoding="utf-8"))
        except Exception:
            count = 0
        print(f"    {fp.name}: {count} entries")
    print()
    print("  Recent entries:")
    for e in get_recent(10):
        print(f"    [{e['ts']}] {e['icon']} {e['source']}: {e['message']}")
