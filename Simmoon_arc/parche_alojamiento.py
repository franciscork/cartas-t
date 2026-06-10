#!/usr/bin/env python3
"""Parche: Sistema de Alojamiento - convierte viviendas en albergues + hoteles"""
import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    codigo = f.read()

cambios = 0

# 1. Zona residencial -> alojamiento
old = '"residencial": TipoZona("residencial", "Residencial",'
new = '"alojamiento": TipoZona("alojamiento", "Alojamiento",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("1 OK: zona residencial -> alojamiento")

# 2. Quitar hou_03 de alojamiento
old = 'categorias_compatibles=["hou_01", "hou_02", "hou_03", "hou_04",\n                                "misc_01", "site_08"],'
new = 'categorias_compatibles=["hou_01", "hou_02", "hou_04",\n                                "misc_01", "site_08"],'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("2 OK: hou_03 quitado de alojamiento")

# 3. hou_01 nombre
old = '"hou_01": TipoEdificio("hou_01", "Modulo Habitacional Basico", "housing",'
new = '"hou_01": TipoEdificio("hou_01", "Albergue Basico", "housing",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("3 OK: hou_01 -> Albergue Basico")

# 4. hou_01 costo/energia
old = 'costo=400, produce_energia=-3,'
new = 'costo=300, produce_energia=-2,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("4 OK: hou_01 costo 300")

# 5. hou_01 mantenimiento
old = 'mantenimiento=5, empleos=0, ancho_tiles=1, alto_tiles=1,'
new = 'mantenimiento=3, empleos=0, ancho_tiles=1, alto_tiles=1,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("5 OK: hou_01 mantenimiento 3")

# 6. hou_01 descripcion/alquiler
old = 'descripcion="Capsula subterranea para 4-8 colonos. 1x1", alquiler=20)'
new = 'descripcion="Capsula economica para 4-8 colonos. 1x1", alquiler=12)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("6 OK: hou_01 alquiler 12")

# 7. hou_02 nombre
old = '"hou_02": TipoEdificio("hou_02", "Complejo Residencial", "housing",'
new = '"hou_02": TipoEdificio("hou_02", "Albergue Comunitario", "housing",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("7 OK: hou_02 -> Albergue Comunitario")

# 8. hou_02 costo
old = 'costo=700, produce_energia=-6,'
new = 'costo=500, produce_energia=-4,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("8 OK: hou_02 costo 500")

# 9. hou_02 mantenimiento
old = 'mantenimiento=8, empleos=1, ancho_tiles=2, alto_tiles=2,'
new = 'mantenimiento=5, empleos=1, ancho_tiles=2, alto_tiles=2,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("9 OK: hou_02 mantenimiento 5")

# 10. hou_02 descripcion/alquiler
old = 'descripcion="Tuneles de lava acondicionados. 2x2", alquiler=35)'
new = 'descripcion="Albergue compartido en tuneles de lava. 2x2", alquiler=22)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("10 OK: hou_02 alquiler 22")

# 11. hou_03 -> Hotel
old = '"hou_03": TipoEdificio("hou_03", "Cupula de Lujo", "housing",'
new = '"hou_03": TipoEdificio("hou_03", "Hotel Cupula de Lujo", "businesses",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("11 OK: hou_03 -> Hotel (businesses)")

# 12. hou_03 costo
old = 'costo=1500, produce_energia=-10, produce_oxigeno=-3, produce_agua=-2,'
new = 'costo=2000, produce_energia=-12, produce_oxigeno=-3, produce_agua=-2,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("12 OK: hou_03 costo 2000")

# 13. hou_03 mantenimiento
old = 'mantenimiento=15, empleos=3, ancho_tiles=2, alto_tiles=2,'
new = 'mantenimiento=18, empleos=8, ancho_tiles=2, alto_tiles=2,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("13 OK: hou_03 empleos 8")

# 14. hou_03 felicidad
old = 'produce_felicidad=10,'
new = 'produce_felicidad=15,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("14 OK: hou_03 felicidad 15")

# 15. hou_03 descripcion
old = 'descripcion="Estructura geodesica con vistas al espacio. 2x2", alquiler=80)'
new = 'descripcion="Hotel premium con vistas al espacio. 2x2", alquiler=120)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("15 OK: hou_03 alquiler 120")

# 16. hou_04 nombre
old = '"hou_04": TipoEdificio("hou_04", "Barrio Subterraneo", "housing",'
new = '"hou_04": TipoEdificio("hou_04", "Albergue Subterraneo", "housing",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("16 OK: hou_04 -> Albergue Subterraneo")

# 17. hou_04 costo
old = 'costo=1000, produce_energia=-8,'
new = 'costo=700, produce_energia=-6,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("17 OK: hou_04 costo 700")

# 18. hou_04 mantenimiento
old = 'mantenimiento=10, empleos=2, ancho_tiles=3, alto_tiles=2,'
new = 'mantenimiento=7, empleos=2, ancho_tiles=3, alto_tiles=2,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("18 OK: hou_04 mantenimiento 7")

# 19. hou_04 descripcion
old = 'descripcion="Colonias excavadas bajo la superficie. 3x2", alquiler=45)'
new = 'descripcion="Albergue excavado bajo la superficie. 3x2", alquiler=30)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("19 OK: hou_04 alquiler 30")

# 20. misc_01 nombre
old = '"misc_01": TipoEdificio("misc_01", "Viviendas", "buildings_misc",'
new = '"misc_01": TipoEdificio("misc_01", "Albergue Central", "buildings_misc",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("20 OK: misc_01 -> Albergue Central")

# 21. misc_01 costo
old = 'costo=600, produce_energia=-5, mantenimiento=8,'
new = 'costo=450, produce_energia=-4, mantenimiento=5,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("21 OK: misc_01 costo 450")

# 22. misc_01 desc
old = 'descripcion="Residencia para 20 colonos. 2x2", alquiler=40)'
new = 'descripcion="Albergue principal para 20 colonos. 2x2", alquiler=25)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("22 OK: misc_01 alquiler 25")

# 23. site_08 nombre
old = '"site_08": TipoEdificio("site_08", "Sector Residencial", "lunar_sites",'
new = '"site_08": TipoEdificio("site_08", "Complejo de Albergues", "lunar_sites",'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("23 OK: site_08 -> Complejo de Albergues")

# 24. site_08 costo
old = 'costo=1000, produce_energia=-8, produce_oxigeno=-5, produce_agua=-3,'
new = 'costo=800, produce_energia=-6, produce_oxigeno=-3, produce_agua=-2,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("24 OK: site_08 costo 800")

# 25. site_08 mantenimiento
old = 'mantenimiento=12, empleos=5, ancho_tiles=4, alto_tiles=4,'
new = 'mantenimiento=8, empleos=5, ancho_tiles=4, alto_tiles=4,'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("25 OK: site_08 mantenimiento 8")

# 26. site_08 desc
old = 'descripcion="Viviendas para 50 colonos. 4x4", alquiler=80)'
new = 'descripcion="Complejo de albergues para 50 colonos. 4x4", alquiler=35)'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("26 OK: site_08 alquiler 35")

# 27. Agregar hou_03 a zona comercial
old = '"biz_02", "biz_03", "biz_04", "biz_06", "biz_07", "biz_10", "biz_11",'
new = '"biz_02", "biz_03", "biz_04", "biz_06", "biz_07", "biz_10", "biz_11",\n            "hou_03",'
idx = codigo.find(old)
if idx > 0 and 'hou_03' not in codigo[idx:idx+600]:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("27 OK: hou_03 agregado a comercial")
else:
    print("27 SKIP: hou_03 ya esta en comercial o no encontrado")

# 28. Boton panel Vivienda -> Alojamiento
if '("Vivienda", "housing")' in codigo:
    codigo = codigo.replace('("Vivienda", "housing")', '("Alojamiento", "housing")', 1)
    cambios += 1
    print("28 OK: Boton Vivienda -> Alojamiento")

# 29. Comentario seccion
old = '# --- Vivienda (housing) ---'
new = '# --- Alojamiento / Albergues (housing) ---'
if old in codigo:
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("29 OK: Comentario actualizado")

# 30. Comentario EDIFICIOS_PRIVADOS
if '    # Vivienda' in codigo:
    codigo = codigo.replace('    # Vivienda', '    # Alojamiento (albergues)', 1)
    cambios += 1
    print("30 OK: Comentario EDIFICIOS_PRIVADOS")

# Guardar
with open(RUTA, "w", encoding="utf-8") as f:
    f.write(codigo)

print()
print(f"RESULTADO: {cambios} cambios aplicados")

