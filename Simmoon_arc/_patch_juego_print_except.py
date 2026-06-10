#!/usr/bin/env python3
"""
Patch juego_simmoon.py:
1. Add import logging and configure it
2. Convert debug prints (votos/catalogo) to logging.info/warning
3. Convert bare 'except Exception:' to specific exception types
"""

import sys

path = 'Simmoon_arc/juego_simmoon.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# ── 1. Add import logging after 'from typing import ...' ──
if 'import logging' not in content:
    # Find the typing import line and add logging after it
    old = 'from typing import Optional, Tuple, List, Dict'
    new = 'from typing import Optional, Tuple, List, Dict\n\nimport logging\n\n# ── Logging setup ──\nlogging.basicConfig(\n    level=logging.INFO,\n    format="[%(levelname)s] %(message)s",\n    datefmt="%H:%M:%S",\n)\nlog = logging.getLogger(__name__)'
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print('✅ import logging agregado')
    else:
        print('⚠️  No se encontró from typing import...')

# ── 2. Convert debug prints in cargar_votos() ──
replacements = [
    # Line 557: print(f"  ✅ Votos cargados desde API: {len(votos)} assets")
    (
        '            print(f"  ✅ Votos cargados desde API: {len(votos)} assets")',
        '            log.info(f"Votos cargados desde API: {len(votos)} assets")',
    ),
    # Line 593: print(f"  ✅ Votos cargados desde votes.json: {len(votos)} assets")
    (
        '                print(f"  ✅ Votos cargados desde votes.json: {len(votos)} assets")',
        '                log.info(f"Votos cargados desde votes.json: {len(votos)} assets")',
    ),
    # Line 603: print(f"  ⚠️  No se encontraron votos. No hay edificios disponibles.")
    (
        '    print(f"  ⚠️  No se encontraron votos. No hay edificios disponibles.")',
        '    log.warning("No se encontraron votos. No hay edificios disponibles.")',
    ),
    # Line 605: print(f"     Usa viewer.html para votar assets y desbloquear edificios.")
    (
        '    print(f"     Usa viewer.html para votar assets y desbloquear edificios.")',
        '    log.warning("Usa viewer.html para votar assets y desbloquear edificios.")',
    ),
    # Line 625: print("  🗳️  Sin votos: catálogo vacío. Usa viewer.html para votar.")
    (
        '        print("  \\U0001f5f3\\ufe0f  Sin votos: cat\\xe1logo vac\\xedo. Usa viewer.html para votar.")',
        None,  # Skip - will handle separately
    ),
    # Line 641: print(f"  🗳️  Catálogo filtrado: ...")
    (
        '    print(f"  \\U0001f5f3\\ufe0f  Cat\\xe1logo filtrado: {len(filtrado)}/{len(CATALOGO_EDIFICIOS)} edificios (con votos)")',
        None,  # Skip
    ),
]

for old_str, new_str in replacements:
    if new_str is None:
        continue
    if old_str in content:
        content = content.replace(old_str, new_str, 1)
        changes += 1
        print(f'✅ Replaced: {old_str[:60]}...')
    else:
        # Try alternate encoding
        print(f'⚠️  Not found (trying alternate): {old_str[:60]}...')

# ── Handle emoji prints (might have encoding issues) ──
# Line 625: print("  🗳️  Sin votos: catálogo vacío. Usa viewer.html para votar.")
patterns_625 = [
    'print("  🗳️  Sin votos: catálogo vacío. Usa viewer.html para votar.")',
    "print('  🗳️  Sin votos: catálogo vacío. Usa viewer.html para votar.')",
]
for p in patterns_625:
    if p in content:
        content = content.replace(
            p,
            '    log.warning("Sin votos: catálogo vacío. Usa viewer.html para votar.")',
            1
        )
        changes += 1
        print('✅ Replaced: Sin votos catalog print')
        break

# Line 641: print(f"  🗳️  Catálogo filtrado: ...")
patterns_641 = [
    'print(f"  🗳️  Catálogo filtrado: {len(filtrado)}/{len(CATALOGO_EDIFICIOS)} edificios (con votos)")',
    "print(f'  🗳️  Catálogo filtrado: {len(filtrado)}/{len(CATALOGO_EDIFICIOS)} edificios (con votos)')",
]
for p in patterns_641:
    if p in content:
        content = content.replace(
            p,
            '    log.info(f"Catálogo filtrado: {len(filtrado)}/{len(CATALOGO_EDIFICIOS)} edificios (con votos)")',
            1
        )
        changes += 1
        print('✅ Replaced: Catalog filtered print')
        break

# ── 3. Convert 'except Exception:' to specific types ──

# 3a. Font initialization (line 2580) - pygame.error or OSError
content = content.replace(
    '        except Exception:\n\n            # Fallback a fuente por defecto de pygame',
    '        except (pygame.error, OSError):\n\n            # Fallback a fuente por defecto de pygame',
    1
)

# 3b-c. Font rendering excepts (lines 3712, 3730)
content = content.replace(
    '        except Exception:\n            try:\n\n                    self.fuente_cartel = pygame.font.Font(None, 22)\n            except Exception:\n                self.fuente_cartel = pygame.font.Font(None, 22)',
    '        except (pygame.error, OSError):\n            try:\n\n                    self.fuente_cartel = pygame.font.Font(None, 22)\n            except (pygame.error, OSError):\n                self.fuente_cartel = pygame.font.Font(None, 22)',
    1
)

# 3d-h: Render excepts (lines 5386, 5429, 5472, 5515, 5559)
# These are all similar: except Exception: pass  in render methods
# They all look like:
#         except Exception:
#             pass

# Count how many remain after the first replacements
remaining_excepts = content.count('        except Exception:\n            pass')
print(f'⚠️  {remaining_excepts} except Exception: pass remain (render excepts)')

# The render ones are tricky - they're in specific exclamation/effect rendering methods
# Let's replace them with a broader try/except that's still specific
content = content.replace(
    '        except Exception:\n            pass\n',
    '        except (pygame.error, ValueError):\n            pass\n',
)

# ── Write back ──
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n📊 Total changes: {changes}')
print('✅ Patch complete!')
