#!/usr/bin/env python3
"""Valida el estado de los albergues en el juego (solo ASCII)."""

import re
import sys
import py_compile

def main():
    # Force UTF-8 output
    sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None

    with open('juego_simmoon.py', 'r', encoding='utf-8') as f:
        c = f.read()

    errores = 0
    ok_count = 0

    def check(nombre, condicion, detalle=""):
        nonlocal errores, ok_count
        if condicion:
            ok_count += 1
            print(f"  [OK] {nombre}")
        else:
            errores += 1
            print(f"  [FAIL] {nombre}" + (f" -- {detalle}" if detalle else ""))

    print("=" * 60)
    print("VALIDACION COMPLETA DE ALBERGUES")
    print("=" * 60)

    # --- 1. ZONA ALOJAMIENTO ---
    print("\n--- ZONA ALOJAMIENTO ---")
    idx_zona = c.find('"alojamiento": TipoZona("alojamiento"')
    if idx_zona >= 0:
        end_zona = c.find('),', idx_zona) + 2
        bloque_zona = c[idx_zona:end_zona]
        print(f"  Bloque: {bloque_zona[:100]}...")

        check("hou_03 eliminado de alojamiento zone",
              'hou_03' not in bloque_zona,
              "hou_03 SI esta")

        for pid in ["hou_01", "hou_02", "hou_04", "misc_01", "site_08"]:
            check(f"{pid} presente en alojamiento zone", pid in bloque_zona)

        check("alquiler_min=8, alquiler_max=50",
              'alquiler_min=8, alquiler_max=50' in bloque_zona)

        # Also check hou_03 is NOT present (redundant but explicit)
        check("hou_03 NO esta en alojamiento zone", 'hou_03' not in bloque_zona)

        # Check alquiler_min=10 is NOT present (old value)
        check("NO hay alquiler_min=10 (old value)", 'alquiler_min=10' not in bloque_zona)
    else:
        print("  [FAIL] Zona alojamiento NO encontrada!")
        errores += 1

    # --- 2. ZONA COMERCIAL (hou_03 debe estar aqui) ---
    print("\n--- ZONA COMERCIAL ---")
    idx_com = c.find('"comercial": TipoZona("comercial"')
    if idx_com >= 0:
        end_com = c.find('),', idx_com) + 2
        bloque_com = c[idx_com:end_com]
        check("hou_03 presente en comercial zone", 'hou_03' in bloque_com,
              "No se encontro hou_03 en comercial")
    else:
        print("  [FAIL] Zona comercial NO encontrada!")
        errores += 1

    # --- 3. EDIFICIOS INDIVIDUALES ---
    print("\n--- EDIFICIOS ---")

    # Define checks for each building
    building_checks = {
        'hou_01': {
            'nombre': ('Albergue Basico', 'Albergue'),
            'stats': ['costo=300, produce_energia=-2,', 'alquiler=15'],
        },
        'hou_02': {
            'nombre': ('Albergue Comunitario', 'Albergue'),
            'stats': ['costo=500,', 'alquiler=22'],
        },
        'hou_03': {
            'nombre': ('Hotel', 'Hotel'),
            'categoria': 'businesses',
            'stats': ['costo=2000,'],
        },
        'hou_04': {
            'nombre': ('Albergue Subterraneo', 'Albergue Subterr'),
            'stats': ['costo=700,', 'produce_energia=-6,'],
        },
        'misc_01': {
            'nombre': ('Albergue Central', 'Albergue'),
            'stats': ['costo=450,', 'alquiler=25'],
        },
        'site_08': {
            'nombre': ('Complejo de Albergues', 'Albergues'),
            'stats': ['costo=800,', 'produce_oxigeno=-3,'],
        },
        'biz_02': {
            'nombre': ('Puesto Comercial', 'Puesto'),
            'stats': ['costo=400, produce_energia=-3, produce_oxigeno=-1,'],
        },
    }

    for pid, checks in building_checks.items():
        idx = c.find(f'"{pid}": TipoEdificio("{pid}"')
        if idx < 0:
            print(f"  [FAIL] {pid}: NO ENCONTRADO!")
            errores += 1
            continue

        end = c.find('),', idx) + 2
        bloque = c[idx:end]

        # Check nombre
        nombre_full, nombre_short = checks['nombre']
        if nombre_full in bloque or nombre_short in bloque:
            print(f"  [OK] {pid}: nombre correcto ({nombre_full})")
            ok_count += 1
        else:
            print(f"  [FAIL] {pid}: nombre incorrecto (esperado: {nombre_full})")
            print(f"    bloque: {bloque[:120]}...")
            errores += 1

        # Check categoria (only for hou_03)
        if 'categoria' in checks:
            if checks['categoria'] in bloque:
                print(f"  [OK] {pid}: categoria = {checks['categoria']}")
                ok_count += 1
            else:
                print(f"  [FAIL] {pid}: categoria NO es {checks['categoria']}")
                errores += 1

        # Check stats
        for stat in checks['stats']:
            if stat in bloque:
                print(f"  [OK] {pid}: {stat}")
                ok_count += 1
            else:
                print(f"  [FAIL] {pid}: NO contiene '{stat}'")
                errores += 1

    # --- 4. PANEL BUTTON ---
    print("\n--- PANEL DE CATEGORIAS ---")
    # Find the categorias list in the panel/draw code
    idx_vivienda = c.find('Vivienda')
    idx_alojamiento_panel = c.find('Alojamiento')
    
    if idx_vivienda >= 0:
        # Check if Vivienda is ONLY in valid contexts (not the panel button)
        context = c[max(0, idx_vivienda-5):idx_vivienda+40]
        print(f"  Vivienda found at ...{context}...")
        # The panel should show Alojamiento, not Vivienda
        # But Vivienda could appear in other contexts (old comments, etc.)
        # Let's check specifically for the panel entry
        idx_panel_line = c.find('("')
        # Search around line 3035 area for the housing category entry
        lines = c.split('\n')
        panel_found = False
        for i, line in enumerate(lines):
            if 'housing' in line and ('Vivienda' in line or 'Alojamiento' in line):
                line_stripped = line.strip()
                if 'Alojamiento' in line_stripped:
                    print(f"  [OK] Panel line {i+1}: {line_stripped.strip()}")
                    ok_count += 1
                else:
                    print(f"  [FAIL] Panel line {i+1}: {line_stripped.strip()} (aun dice Vivienda)")
                    errores += 1
                panel_found = True
                break
        if not panel_found:
            print("  [FAIL] No se encontro la linea del panel con housing")
            errores += 1
    else:
        print("  [OK] No hay 'Vivienda' en el archivo (ya cambiado)")
        ok_count += 1

    # --- 5. EDIFICIOS_PRIVADOS ---
    print("\n--- EDIFICIOS_PRIVADOS ---")
    idx_priv = c.find('EDIFICIOS_PRIVADOS = {')
    if idx_priv >= 0:
        end_priv = c.find('}', idx_priv)
        bloque_priv = c[idx_priv:end_priv + 1]
        for pid in ['hou_01', 'hou_02', 'hou_03', 'hou_04', 'misc_01', 'site_08']:
            check(f"{pid} en EDIFICIOS_PRIVADOS", pid in bloque_priv)
    else:
        print("  [FAIL] EDIFICIOS_PRIVADOS no encontrado!")
        errores += 1

    # --- 6. COMPILACION ---
    print("\n--- COMPILACION ---")
    try:
        py_compile.compile('juego_simmoon.py', doraise=True)
        check("Archivo compila sin errores", True)
    except py_compile.PyCompileError as e:
        check("Archivo compila sin errores", False, str(e))

    # --- SUMMARY ---
    print()
    print("=" * 60)
    total = ok_count + errores
    print(f"RESULTADO: {ok_count}/{total} correctos, {errores} errores")
    print("=" * 60)

    return 1 if errores > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
