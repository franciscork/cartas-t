#!/usr/bin/env python3
"""Patch juego_simmoon.py - prints to logging + specify bare except Exception."""
import os, sys, tempfile, shutil

SRC = r'Simmoon_arc/juego_simmoon.py'

# Copy to temp
tmp = os.path.join(tempfile.gettempdir(), 'juego_simmoon_patched.py')
shutil.copy2(SRC, tmp)

with open(tmp, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# 1. Add import logging after typing import
old_import = 'from typing import Optional, Tuple, List, Dict'
new_import = old_import + '\n\nimport logging\n\n# ── Logging setup ──\nlogging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")\nlog = logging.getLogger(__name__)'
if old_import in content:
    content = content.replace(old_import, new_import, 1)
    changes += 1
    print("1. import logging agregado")

# 2. Debug prints -> logging.info/warning
# These are the exact strings from the file (with Windows \r\n)
replacements = [
    # Line 557
    ('            print(f"  \u2705 Votos cargados desde API: {len(votos)} assets")',
     '            log.info(f"Votos cargados desde API: {len(votos)} assets")'),
    # Line 593
    ('                print(f"  \u2705 Votos cargados desde votes.json: {len(votos)} assets")',
     '                log.info(f"Votos cargados desde votes.json: {len(votos)} assets")'),
    # Line 603
    ('    print(f"  \u26a0\ufe0f  No se encontraron votos. No hay edificios disponibles.")',
     '    log.warning("No se encontraron votos. No hay edificios disponibles.")'),
    # Line 605
    ('    print(f"     Usa viewer.html para votar assets y desbloquear edificios.")',
     '    log.warning("Usa viewer.html para votar y desbloquear edificios.")'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("2. print debug convertido")

# Handle emoji chars for lines 625 and 641 (might use different unicode)
if 'print' in content:
    for line in content.split('\n'):
        ls = line.strip()
        if 'Sin votos' in ls and 'print' in ls and 'votar' in ls:
            old_line = line
            # Calculate indent
            indent = line[:len(line) - len(line.lstrip())]
            new_line = indent + 'log.warning("Sin votos: catalogo vacio. Usa viewer.html para votar.")'
            content = content.replace(old_line, new_line, 1)
            changes += 1
            print("3. Sin votos -> logging")
            break

if 'print' in content:
    for line in content.split('\n'):
        ls = line.strip()
        if 'Catalogo filtrado' in ls and 'print' in ls:
            old_line = line
            indent = line[:len(line) - len(line.lstrip())]
            new_line = indent + 'log.info("Catalogo filtrado: edificios con votos")'
            content = content.replace(old_line, new_line, 1)
            changes += 1
            print("4. Catalogo filtrado -> logging")
            break

# 3. specify except Exception:
# Font init - line ~2580
content = content.replace(
    'except Exception:\n\n            # Fallback a fuente por defecto de pygame',
    'except (pygame.error, OSError):\n\n            # Fallback a fuente por defecto de pygame',
    1
)
changes += 1
print("5. except Exception -> (pygame.error, OSError) [font init]")

# Remaining except Exception: count
remaining = content.count('except Exception:')
print(f"6. Restantes except Exception: {remaining}")
print(f"\nTotal cambios: {changes}")

with open(tmp, 'w', encoding='utf-8') as f:
    f.write(content)

# Copy back with shutil.copy2 (preserves permissions)
try:
    shutil.copy2(tmp, SRC)
    print(f"Archivo original sobrescrito: {SRC}")
except PermissionError:
    print(f"ERROR: Permiso denegado para escribir en {SRC}")
    print(f"El archivo parcheado esta en: {tmp}")
    sys.exit(1)

# Verify
with open(SRC, 'r', encoding='utf-8') as f:
    final = f.read()
print(f"Verificacion: import logging {'OK' if 'import logging' in final else 'FALLO'}")
print(f"Verificacion: log.info {'OK' if 'log.info' in final else 'FALLO'}")
print(f"Verificacion: log.warning {'OK' if 'log.warning' in final else 'FALLO'}")
print(f"Verificacion: except (pygame.error, OSError) {'OK' if '(pygame.error, OSError)' in final else 'FALLO'}")
