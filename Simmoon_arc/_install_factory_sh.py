#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador del lanzador 'factory'.
Copia Simmoon_arc/factory.sh -> ~/factory.sh y agrega alias a .bashrc.

Uso:
    python Simmoon_arc/_install_factory_sh.py
"""
from pathlib import Path
import shutil
import sys
import os

# Fix encoding for Windows cp1252 terminals
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = Path.home()
BASHRC = HOME / ".bashrc"
FACTORY_SH_DEST = HOME / "factory.sh"
FACTORY_SH_SRC = Path(__file__).resolve().parent / "factory.sh"


def install():
    print()
    print("  == Instalando lanzador 'factory'...")
    print()

    # 1. Validate source exists
    if not FACTORY_SH_SRC.exists():
        print(f"  [ERROR] No encuentro: {FACTORY_SH_SRC}")
        print(f"     Asegurate de ejecutar desde Simmoon_arc/")
        sys.exit(1)

    # 2. Copy factory.sh to ~/
    shutil.copy2(str(FACTORY_SH_SRC), str(FACTORY_SH_DEST))
    FACTORY_SH_DEST.chmod(0o755)
    print(f"  [OK] Creado: {FACTORY_SH_DEST}")

    # 3. Add alias to .bashrc (avoid duplicates)
    alias_line = 'alias factory="bash ~/factory.sh"'
    if BASHRC.exists():
        existing = BASHRC.read_text(encoding="utf-8")
        if 'alias factory' in existing:
            print(f"  [INFO] Alias 'factory' ya existe en {BASHRC}")
        else:
            with open(str(BASHRC), "a", encoding="utf-8") as f:
                f.write(f"\n# --- FactoryGames Orchestrator ---\n{alias_line}\n")
            print(f"  [OK] Alias agregado a {BASHRC}")
    else:
        BASHRC.write_text(f"# --- FactoryGames Orchestrator ---\n{alias_line}\n", encoding="utf-8")
        print(f"  [OK] Creado {BASHRC} con alias 'factory'")

    # 4. Create factory.bat for Windows Explorer
    bat_path = HOME / "factory.bat"
    bat_content = [
        "@echo off",
        "REM ============================================",
        "REM  FACTORY GAMES - Orchestrator Launcher",
        "REM ============================================",
        f'cd /d "{FACTORY_SH_SRC.parent}"',
        "python factory.py %*",
        'if "%*"=="" pause',
        "",
    ]
    bat_path.write_text("\r\n".join(bat_content), encoding="ascii")
    print(f"  [OK] Creado: {bat_path}")

    print()
    print("  -------------------------------------------")
    print("  Instalacion completa!")
    print()
    print("  Para usar ahora, ejecuta:")
    print()
    print("    source ~/.bashrc")
    print("    factory status")
    print()
    print("  O abre una nueva terminal y escribe:")
    print()
    print("    factory")
    print("    factory --help")
    print("  -------------------------------------------")
    print()


if __name__ == "__main__":
    install()
