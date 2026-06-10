#!/usr/bin/env python3
"""
_refactor_renderizador.py — Extrae la clase Renderizador de juego_simmoon.py
a renderizador.py, usando imports locales (lazy) para evitar circulares.

Ejecutar: python _refactor_renderizador.py
"""
import re
import shutil
import sys
from pathlib import Path

ORIGINAL = Path("juego_simmoon.py")
RENDERIZADOR = Path("renderizador.py")
BACKUP = Path("juego_simmoon_refactor_backup.py")

# ── 1. Read the original file ──
content = ORIGINAL.read_text(encoding="utf-8")

# ── 2. Locate the Renderizador class ──
# Find start: "class Renderizador:"
start_marker = "class Renderizador:"
start_idx = content.find(start_marker)
if start_idx < 0:
    print("ERROR: 'class Renderizador:' not found")
    sys.exit(1)

# Find end: next top-level class (JuegoSimmoon) or end of file
end_marker = "\nclass JuegoSimmoon:"
end_idx = content.find(end_marker, start_idx)
if end_idx < 0:
    print("ERROR: 'class JuegoSimmoon:' not found after Renderizador")
    sys.exit(1)

# Extract the class (including the blank line before the next class)
# We want: from start_marker to just before the blank line before JuegoSimmoon
class_start = start_idx
class_end = end_idx  # Stop at the blank line before "class JuegoSimmoon:"

renderizador_code = content[class_start:class_end]
# Remove trailing whitespace/newlines
renderizador_code = renderizador_code.rstrip("\n\r")

print(f"Renderizador class: {len(renderizador_code)} chars")
print(f"Lines: {renderizador_code.count(chr(10)) + 1}")

# ── 3. Build renderizador.py ──
# Collect unique imports needed from juego_simmoon
refs_needed = set()
for match in re.finditer(r'(Config\.\w+|CATALOGO_ZONAS|CATALOGO_EDIFICIOS|es_edificio_privado)', renderizador_code):
    refs_needed.add(match.group(1).split(".")[0])

# Also check method signatures for type hints
for match in re.finditer(r':\s*(Mapa|Camara|Recursos|TipoEdificio|EdificioColocado)\b', renderizador_code):
    refs_needed.add(match.group(1))

refs_needed.discard("Config")  # Config is used as Config.X, so we import Config
print(f"External refs needed: {refs_needed}")

# Build the import block for lazy imports inside methods
# We'll add a local import helper
imports_block = '''"""
renderizador.py — Renderizador isométrico para SIMMOON

Extraído de juego_simmoon.py. Usa imports locales (lazy) para
evitar dependencias circulares con juego_simmoon.
"""
import math
import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import pygame

# ── Lazy import helper ────────────────────────────────────────────
def _from_game(name):
    """Importa un nombre desde juego_simmoon (lazy, evita circular)."""
    import juego_simmoon as _gs
    return getattr(_gs, name)


'''

renderizador_py = imports_block + renderizador_code

# Replace direct references to external types with lazy imports
# For Config.X, we need to replace with _from_game("Config").X
# But this would be too invasive. Instead, we'll add a helper at the
# start of each method that uses external types.

# Simpler approach: replace module-level references with lazy versions
# For Config references, we need to do this inside methods

# Actually, let me just add lazy imports at the start of each public method
# that references Config, CATALOGO_ZONAS etc.

# The simplest approach: replace "Config." with "_from_game('Config')." everywhere
renderizador_py = renderizador_py.replace("Config.", "_from_game('Config').")
renderizador_py = renderizador_py.replace("CATALOGO_ZONAS", "_from_game('CATALOGO_ZONAS')")
renderizador_py = renderizador_py.replace("CATALOGO_EDIFICIOS", "_from_game('CATALOGO_EDIFICIOS')")
renderizador_py = renderizador_py.replace("es_edificio_privado(", "_from_game('es_edificio_privado')(")

# For type hints in method signatures, use string annotations
# Type hints: Mapa, Camara, Recursos, TipoEdificio
renderizador_py = renderizador_py.replace(": Mapa", ": '_from_game(\"Mapa\")'")
renderizador_py = renderizador_py.replace(": Camara", ": '_from_game(\"Camara\")'")
renderizador_py = renderizador_py.replace(": Recursos", ": '_from_game(\"Recursos\")'")
renderizador_py = renderizador_py.replace(": TipoEdificio", ": '_from_game(\"TipoEdificio\")'")

# Fix: The string replacements added literal quotes which might cause issues
# Actually for type hints, using strings (forward references) is valid Python

# ── 4. Write renderizador.py ──
RENDERIZADOR.write_text(renderizador_py, encoding="utf-8")
print(f"Created {RENDERIZADOR}: {len(renderizador_py)} chars")

# ── 5. Create backup ──
shutil.copy2(ORIGINAL, BACKUP)
print(f"Backup created: {BACKUP}")

# ── 6. Modify juego_simmono.py ──
# Remove the Renderizador class
new_content = content[:class_start] + content[class_end:]
# The import was already added, but we need to keep the import line.
# Actually the import is at the top. We should add an import.
# Find a good place to add the import
import_line = "\nfrom renderizador import Renderizador\n\n"

# Add import after the pygame init block or after the existing imports
# Look for a good insertion point
insert_after = "pygame.display.set_caption(\"☾ SIMMOON — Colonia Lunar\")"
insert_idx = new_content.find(insert_after)
if insert_idx > 0:
    # Find end of the line
    line_end = new_content.find("\n", insert_idx)
    if line_end > 0:
        new_content = new_content[:line_end+1] + "\n" + import_line + new_content[line_end+1:]
        print("Import added after pygame init")
    else:
        new_content += "\n" + import_line
        print("Import added at end")
else:
    new_content = import_line + new_content
    print("Import added at beginning")

# Clean up double blank lines that might have resulted from class removal
new_content = new_content.replace("\n\n\n\n", "\n\n\n")
new_content = new_content.replace("\n\n\n\n", "\n\n\n")

ORIGINAL.write_text(new_content, encoding="utf-8")
print(f"Updated {ORIGINAL}: {len(new_content)} chars (removed ~{len(content) - len(new_content)} chars)")

# ── 7. Verify ──
print("\nVerification:")
print(f"  renderizador.py exists: {RENDERIZADOR.exists()}")
print(f"  'class Renderizador:' in renderizador.py: {'class Renderizador:' in renderizador_py}")
print(f"  'from renderizador import Renderizador' in juego_simmoon.py: {'from renderizador import Renderizador' in new_content}")
print(f"  'class Renderizador:' removed from juego_simmoon.py: {'class Renderizador:' not in new_content}")
print("\n✅ Refactoring complete!")
print("Run: python -m py_compile juego_simmoon.py && python -m py_compile renderizador.py")
