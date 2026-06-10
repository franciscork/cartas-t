#!/usr/bin/env python3
"""Fix remaining housing->albergue changes with correct accented characters."""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    codigo = f.read()

c = 0

# 1. hou_01: Modulo Habitacional Basico -> Albergue Basico (with accents)
old = '"hou_01": TipoEdificio("hou_01", "Módulo Habitacional Básico", "housing",'
new = '"hou_01": TipoEdificio("hou_01", "Albergue Básico", "housing",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("1 OK: hou_01 -> Albergue Basico")
else:
    print("1 FAIL")

# hou_01 costo and description
old = 'costo=400, produce_energia=-3,\n                           mantenimiento=3, empleos=0, ancho_tiles=1, alto_tiles=1,\n                           descripcion="Cápsula subterránea para 4-8 colonos. 1x1", alquiler=20)'
new = 'costo=300, produce_energia=-2,\n                           mantenimiento=3, empleos=0, ancho_tiles=1, alto_tiles=1,\n                           descripcion="Cápsula económica para 4-8 colonos. 1x1", alquiler=12)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("2 OK: hou_01 costo 300, alquiler 12")
else:
    print("2 FAIL")

# 3. hou_02 description (with accents)
old = 'descripcion="Túneles de lava acondicionados. 2x2", alquiler=35)'
new = 'descripcion="Albergue compartido en túneles de lava. 2x2", alquiler=22)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("3 OK: hou_02 alquiler 22")
else:
    print("3 FAIL")

# 4. hou_03: Cupula de Lujo -> Hotel Cupula de Lujo, housing -> businesses
old = '"hou_03": TipoEdificio("hou_03", "Cúpula de Lujo", "housing",'
new = '"hou_03": TipoEdificio("hou_03", "Hotel Cúpula de Lujo", "businesses",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("4 OK: hou_03 -> Hotel, businesses")
else:
    print("4 FAIL")

# hou_03 description and alquiler
old = 'descripcion="Estructura geodésica con vistas al espacio. 2x2", alquiler=80)'
new = 'descripcion="Hotel premium con vistas al espacio. 2x2", alquiler=120)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("5 OK: hou_03 alquiler 120")
else:
    print("5 FAIL")

# 6. hou_04: Barrio Subterraneo -> Albergue Subterraneo
old = '"hou_04": TipoEdificio("hou_04", "Barrio Subterráneo", "housing",'
new = '"hou_04": TipoEdificio("hou_04", "Albergue Subterráneo", "housing",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("6 OK: hou_04 -> Albergue Subterraneo")
else:
    print("6 FAIL")

# hou_04 costo
old = 'costo=1000, produce_energia=-8,\n                           mantenimiento=7, empleos=2, ancho_tiles=3, alto_tiles=2,'
new = 'costo=700, produce_energia=-6,\n                           mantenimiento=7, empleos=2, ancho_tiles=3, alto_tiles=2,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("7 OK: hou_04 costo 700")
else:
    print("7 FAIL")

# 8. site_08: fix costo from 700 to 800 (was corrupted by earlier patch)
old_s08 = '"site_08": TipoEdificio("site_08", "Complejo de Albergues", "lunar_sites",\n                            "site_08_residential_colony_sector_pixel.png",\n                            costo=700, produce_energia=-6, produce_oxigeno=-5, produce_agua=-3,'
new_s08 = '"site_08": TipoEdificio("site_08", "Complejo de Albergues", "lunar_sites",\n                            "site_08_residential_colony_sector_pixel.png",\n                            costo=800, produce_energia=-6, produce_oxigeno=-3, produce_agua=-2,'
if old_s08 in codigo:
    codigo = codigo.replace(old_s08, new_s08, 1)
    c += 1
    print("8 OK: site_08 costo 800, oxigeno -3, agua -2")
else:
    print("8 FAIL")

# 9. Fix alojamiento zone - remove hou_03 from categorias_compatibles
old = 'categorias_compatibles=["hou_01", "hou_02", "hou_03", "hou_04",\n                                "misc_01", "site_08"],'
new = 'categorias_compatibles=["hou_01", "hou_02", "hou_04",\n                                "misc_01", "site_08"],'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("9 OK: hou_03 quitado de alojamiento zone")
else:
    print("9 FAIL")

# 10. Update panel button: Vivienda -> Alojamiento
old = '("Vivienda", "housing")'
new = '("Alojamiento", "housing")'
# Be careful - this could match other things, let's find it in context
idx = codigo.find(old)
if idx > 0:
    # Check context: should be in categorias list
    before = codigo[max(0,idx-40):idx]
    if 'Vivienda' in before or 'Gobierno' in before or 'categorias' in before:
        codigo = codigo[:idx] + new + codigo[idx+len(old):]
        c += 1
        print("10 OK: Boton Vivienda -> Alojamiento")
    else:
        # Try anyway - this is a unique string
        codigo = codigo.replace(old, new, 1)
        c += 1
        print("10b OK: Boton Vivienda -> Alojamiento (fallback)")
else:
    print("10 FAIL")

# 11. Fix boton emoji too
old = '("Vivienda", "housing")'
# already handled above

# 12. Update minimap color comment for housing -> alojamiento
old = 'cat == "housing":\n                        color = (70, 130, 180)  # Azul vivienda'
new = 'cat == "housing":\n                        color = (70, 130, 180)  # Azul alojamiento'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    c += 1
    print("11 OK: Minimap comment updated")
else:
    print("11 FAIL")

with open(RUTA, "w", encoding="utf-8") as f:
    f.write(codigo)

print(f"\nRESULTADO: {c} cambios aplicados")
