#!/usr/bin/env python3
"""Patch system_logger.py — add agent activity logging helpers."""
import sys

path = 'Simmoon_arc/system_logger.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already patched
if 'def log_buffy' in content:
    print('ALREADY_PATCHED')
    sys.exit(0)

marker = '# Quick self-test'
idx = content.find(marker)
if idx < 0:
    print('ERROR: marker not found')
    sys.exit(1)

helpers = """

# ── Helpers for Agent Activity Logging ────────────────────────────────────

def log_buffy(message: str):
    \"\"\"Registra actividad de Buffy para los reportes de Agatha.\"\"\"
    log(\"Buffy\", \"🦙\", message)


def log_claude(message: str):
    \"\"\"Registra actividad de Claude Code para los reportes de Agatha.\"\"\"
    log(\"Claude Code\", \"🤖\", message)


def get_agent_activity(source: str = None, limit: int = 5) -> list:
    \"\"\"Obtiene actividad reciente de un agente desde el log central.\"\"\"
    entries = get_recent(100)
    if source:
        entries = [e for e in entries if e.get(\"source\") == source]
    return entries[:limit]


"""

new_content = content[:idx] + helpers + content[idx:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

lines = len(new_content.split('\n'))
print(f'OK {lines} lines')
