#!/usr/bin/env python3
"""Repara daños del parche anterior y completa los cambios restantes."""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    codigo = f.read()

cambios = 0

# --- 1. Reparar biz_02 (Puesto Comercial) - fue dañado por el parche anterior ---
old_biz02 = '''"biz_02": TipoEdificio("biz_02", "Puesto Comercial", "businesses",
                           "biz_02_lunar_trading_post_pixel.png",
                           costo=300, produce_energia=-2, produce_oxigeno=-1,
                           mantenimiento=5, empleos=5, ancho_tiles=1, alto_tiles=1,
                           descripcion="Mercado de intercambio de recursos.", alquiler=20),'''

new_biz02 = '''"biz_02": TipoEdificio("biz_02", "Puesto Comercial", "businesses",
                           "biz_02_lunar_trading_post_pixel.png",
                           costo=400, produce_energia=-3, produce_oxigeno=-1,
                           mantenimiento=5, empleos=5, ancho_tiles=1, alto_tiles=1,
                           descripcion="Mercado de intercambio de recursos.", alquiler=20),'''

if old_biz02 in codigo:
    codigo = codigo.replace(old_biz02, new_biz02, 1)
    cambios += 1
    print("1 OK: biz_02 restaurado (costo=400, energia=-3)")
else:
    # Maybe it was partially damaged differently - search for biz_02
    import re
    m = re.search(r'("biz_02".*?alquiler=\d+\),)', codigo, re.DOTALL)
    if m:
        print(f"  Found biz_02 block: {m.group(1)[:80]}...")
    print("1 FAIL: biz_02 no encontrado o ya fue corregido")

# --- 2. Reparar site_08 (Complejo de Albergues) - fue dañado por el parche anterior ---
old_site08 = '''"site_08": TipoEdificio("site_08", "Complejo de Albergues", "lunar_sites",
                            "site_08_residential_colony_sector_pixel.png",
                            costo=700, produce_energia=-6, produce_oxigeno=-5, produce_agua=-3,
                            mantenimiento=8, empleos=5, ancho_tiles=4, alto_tiles=4,
                            descripcion="Complejo de albergues para 50 colonos. 4x4", alquiler=35),'''

new_site08 = '''"site_08": TipoEdificio("site_08", "Complejo de Albergues", "lunar_sites",
                            "site_08_residential_colony_sector_pixel.png",
                            costo=800, produce_energia=-6, produce_oxigeno=-3, produce_agua=-2,
                            mantenimiento=8, empleos=5, ancho_tiles=4, alto_tiles=4,
                            descripcion="Complejo de albergues para 50 colonos. 4x4", alquiler=35),'''

if old_site08 in codigo:
    codigo = codigo.replace(old_site08, new_site08, 1)
    cambios += 1
    print("2 OK: site_08 corregido (costo=800, oxigeno=-3, agua=-2)")
else:
    print("2 FAIL: site_08 no coincide exactamente")

# --- 3. hou_01 -> Albergue Basico (usando bloque completo) ---
old_hou01 = '''"hou_01": TipoEdificio("hou_01", "Modulo Habitacional Basico", "housing",
                           "hou_01_basic_habitat_module_pixel.png",
                           costo=400, produce_energia=-3,
                           mantenimiento=3, empleos=0, ancho_tiles=1, alto_tiles=1,
                           descripcion="Capsula subterranea para 4-8 colonos. 1x1", alquiler=20),'''

new_hou01 = '''"hou_01": TipoEdificio("hou_01", "Albergue Basico", "housing",
                           "hou_01_basic_habitat_module_pixel.png",
                           costo=300, produce_energia=-2,
                           mantenimiento=3, empleos=0, ancho_tiles=1, alto_tiles=1,
                           descripcion="Capsula economica para 4-8 colonos. 1x1", alquiler=12),'''

if old_hou01 in codigo:
    codigo = codigo.replace(old_hou01, new_hou01, 1)
    cambios += 1
    print("3 OK: hou_01 -> Albergue Basico (nombre, costo=300, alquiler=12)")
else:
    # Try with accents
    old_hou01a = '''"hou_01": TipoEdificio("hou_01", "Modulo Habitacional Basico", "housing",
                           "hou_01_basic_habitat_module_pixel.png",
                           costo=400, produce_energia=-3,
                           mantenimiento=5, empleos=0, ancho_tiles=1, alto_tiles=1,
                           descripcion="Capsula subterranea para 4-8 colonos. 1x1", alquiler=20),'''
    if old_hou01a in codigo:
        codigo = codigo.replace(old_hou01a, new_hou01, 1)
        cambios += 1
        print("3b OK: hou_01 -> Albergue Basico (version con mantenimiento=5)")
    else:
        print("3 FAIL: hou_01 no coincide exactamente")

# --- 4. hou_04 -> Albergue Subterraneo ---
old_hou04 = '''"hou_04": TipoEdificio("hou_04", "Barrio Subterraneo", "housing",
                           "hou_04_underground_district_pixel.png",
                           costo=1000, produce_energia=-8,
                           mantenimiento=7, empleos=2, ancho_tiles=3, alto_tiles=2,
                           descripcion="Colonias excavadas bajo la superficie. 3x2", alquiler=45),'''

new_hou04 = '''"hou_04": TipoEdificio("hou_04", "Albergue Subterraneo", "housing",
                           "hou_04_underground_district_pixel.png",
                           costo=700, produce_energia=-6,
                           mantenimiento=7, empleos=2, ancho_tiles=3, alto_tiles=2,
                           descripcion="Albergue excavado bajo la superficie. 3x2", alquiler=30),'''

if old_hou04 in codigo:
    codigo = codigo.replace(old_hou04, new_hou04, 1)
    cambios += 1
    print("4 OK: hou_04 -> Albergue Subterraneo (costo=700, alquiler=30)")
else:
    # Try with mantenimiento=10 (original before parche)
    old_hou04b = '''"hou_04": TipoEdificio("hou_04", "Barrio Subterraneo", "housing",
                           "hou_04_underground_district_pixel.png",
                           costo=1000, produce_energia=-8,
                           mantenimiento=10, empleos=2, ancho_tiles=3, alto_tiles=2,
                           descripcion="Colonias excavadas bajo la superficie. 3x2", alquiler=45),'''
    if old_hou04b in codigo:
        codigo = codigo.replace(old_hou04b, new_hou04, 1)
        cambios += 1
        print("4b OK: hou_04 -> Albergue Subterraneo (mantenimiento=10 original)")
    else:
        print("4 FAIL: hou_04 no coincide exactamente")

# --- 5. hou_03 -> Hotel (bloque completo) ---
old_hou03 = '''"hou_03": TipoEdificio("hou_03", "Cupula de Lujo", "housing",
                           "hou_03_luxury_dome_pixel.png",
                           costo=1500, produce_energia=-10, produce_oxigeno=-3, produce_agua=-2,
                           mantenimiento=15, empleos=3, ancho_tiles=2, alto_tiles=2,
                           produce_felicidad=10,
                           descripcion="Estructura geodesica con vistas al espacio. 2x2", alquiler=80),'''

new_hou03 = '''"hou_03": TipoEdificio("hou_03", "Hotel Cupula de Lujo", "businesses",
                           "hou_03_luxury_dome_pixel.png",
                           costo=2000, produce_energia=-12, produce_oxigeno=-3, produce_agua=-2,
                           mantenimiento=18, empleos=8, ancho_tiles=2, alto_tiles=2,
                           produce_felicidad=15,
                           descripcion="Hotel premium con vistas al espacio. 2x2", alquiler=120),'''

if old_hou03 in codigo:
    codigo = codigo.replace(old_hou03, new_hou03, 1)
    cambios += 1
    print("5 OK: hou_03 -> Hotel Cupula de Lujo (businesses, costo=2000, alquiler=120)")
else:
    # Check if it was already partially changed
    if '"Hotel Cupula de Lujo"' in codigo or '"Hotel Cúpula de Lujo"' in codigo:
        print("5 SKIP: hou_03 ya fue cambiado a Hotel")
    else:
        print("5 FAIL: hou_03 no coincide exactamente")

# --- 6. Verificar que hou_03 esta en zona comercial ---
idx_com = codigo.find('"comercial": TipoZona("comercial"')
if idx_com > 0:
    bloque_com = codigo[idx_com:idx_com+2000]
    if '"hou_03"' not in bloque_com:
        # Insertar hou_03 en la zona comercial despues de biz_11
        old_biz = '"biz_02", "biz_03", "biz_04", "biz_06", "biz_07", "biz_10", "biz_11",'
        new_biz = '"biz_02", "biz_03", "biz_04", "biz_06", "biz_07", "biz_10", "biz_11",\n            "hou_03",'
        # Buscar SOLO dentro del bloque comercial
        idx_list = codigo.find(old_biz, idx_com, idx_com+2000)
        if idx_list > 0:
            codigo = codigo[:idx_list] + new_biz + codigo[idx_list+len(old_biz):]
            cambios += 1
            print("6 OK: hou_03 agregado a zona comercial")
        else:
            print("6 FAIL: No se encontro lista de biz en comercial")
    else:
        print("6 SKIP: hou_03 ya esta en zona comercial")
else:
    print("6 FAIL: No se encontro zona comercial")

# --- Guardar ---
with open(RUTA, "w", encoding="utf-8") as f:
    f.write(codigo)

print(f"\nRESULTADO: {cambios} cambios aplicados")

