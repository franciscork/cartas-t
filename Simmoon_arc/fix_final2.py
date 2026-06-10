#!/usr/bin/env python3
"""Simple robust fixer - lee el archivo, aplica cambios exactos, guarda."""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    codigo = f.read()

c = 0

def aplicar(viejo, nuevo, desc):
    global c
    if viejo in codigo:
        global codigo
        codigo = codigo.replace(viejo, nuevo, 1)
        c += 1
        print(f"OK: {desc}")
    else:
        print(f"FAIL: {desc}")

# 1. hou_01 nombre
aplicar('"hou_01": TipoEdificio("hou_01", "Modulo Habitacional Basico", "housing"',
        '"hou_01": TipoEdificio("hou_01", "Albergue Basico", "housing"',
        "hou_01 nombre")

# 2. hou_01 con acentos
aplicar('"hou_01": TipoEdificio("hou_01", "M\u00f3dulo Habitacional B\u00e1sico", "housing"',
        '"hou_01": TipoEdificio("hou_01", "Albergue B\u00e1sico", "housing"',
        "hou_01 nombre (con acentos)")

# 3. hou_01 costo
aplicar("costo=400, produce_energia=-3,", "costo=300, produce_energia=-2,", "hou_01 costo")

# 4. hou_01 descripcion
aplicar("alquiler=20)", "alquiler=12)", "hou_01 alquiler")

# 5. hou_02 descripcion
aplicar('"T\u00faneles de lava acondicionados. 2x2", alquiler=35)',
        '"Albergue compartido en t\u00faneles de lava. 2x2", alquiler=22)',
        "hou_02 descripcion y alquiler")

# 6. hou_03 nombre
aplicar('"hou_03": TipoEdificio("hou_03", "C\u00fapula de Lujo", "housing"',
        '"hou_03": TipoEdificio("hou_03", "Hotel C\u00fapula de Lujo", "businesses"',
        "hou_03 -> Hotel, businesses")

# 7. hou_03 descripcion
aplicar('"Estructura geod\u00e9sica con vistas al espacio. 2x2", alquiler=80)',
        '"Hotel premium con vistas al espacio. 2x2", alquiler=120)',
        "hou_03 descripcion/alquiler")

# 8. hou_04 nombre
aplicar('"hou_04": TipoEdificio("hou_04", "Barrio Subterr\u00e1neo", "housing"',
        '"hou_04": TipoEdificio("hou_04", "Albergue Subterr\u00e1neo", "housing"',
        "hou_04 nombre")

# 9. hou_04 costo
aplicar("costo=1000, produce_energia=-8,", "costo=700, produce_energia=-6,", "hou_04 costo")

# 10. hou_04 descripcion
aplicar('"Colonias excavadas bajo la superficie. 3x2", alquiler=45)',
        '"Albergue excavado bajo la superficie. 3x2", alquiler=30)',
        "hou_04 descripcion/alquiler")

# 11. biz_02 restauracion (fue corrompido)
aplicar('"biz_02": TipoEdificio("biz_02", "Puesto Comercial", "businesses",',
        '"biz_02": TipoEdificio("biz_02", "Puesto Comercial", "businesses",',
        "biz_02 check")  # no-op, solo verifica que existe

# biz_02 costo
aplicar("costo=300, produce_energia=-2,", "costo=400, produce_energia=-3,", "biz_02 costo restaurado")

# 12. site_08 costo corregido
aplicar("costo=700, produce_energia=-6, produce_oxigeno=-5, produce_agua=-3,",
        "costo=800, produce_energia=-6, produce_oxigeno=-3, produce_agua=-2,",
        "site_08 costo corregido")

# 13. Quitar hou_03 de alojamiento
aplicar('categorias_compatibles=["hou_01", "hou_02", "hou_03", "hou_04",',
        'categorias_compatibles=["hou_01", "hou_02", "hou_04",',
        "hou_03 quitado de alojamiento zone")

# 14. Boton panel
aplicar('("Vivienda", "housing")', '("Alojamiento", "housing")', "boton Vivienda -> Alojamiento")

# 15. Minimap comentario
aplicar("Azul vivienda", "Azul alojamiento", "minimap comentario")

with open(RUTA, "w", encoding="utf-8") as f:
    f.write(codigo)

print(f"\nRESULTADO: {c} cambios")
