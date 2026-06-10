#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏭 FactoryGames — Entry Point

Uso:
    python factory.py status         Estado del sistema
    python factory.py agents         Listar agentes
    python factory.py coding "..."   Delegar tarea de código
    python factory.py image "..."    Generar imagen
    python factory.py llm "..."      Consultar LLM
    python factory.py recover ollama Recuperar servicio
    python factory.py                Menú interactivo
"""

import sys
from pathlib import Path

# ── Asegurar que podemos importar el package factory/ ──────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    """Delegar al CLI del orquestador."""
    try:
        from factory.cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"\n  ❌ Error al cargar el orquestador: {e}")
        print(f"\n  Asegúrate de que la estructura factory/ existe:")
        print(f"     {SCRIPT_DIR / 'factory/'}")
        print(f"     ├── __init__.py")
        print(f"     ├── orchestrator.py")
        print(f"     ├── agent_registry.py")
        print(f"     ├── task_dispatcher.py")
        print(f"     ├── health_monitor.py")
        print(f"     ├── logging.py")
        print(f"     └── cli.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
