#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parche para reducir CATALOGO_ZONAS a 4 zonas en juego_simmoon.py"""

RUTA = "juego_simmoon.py"

with open(RUTA, "r", encoding="utf-8") as f:
    codigo = f.read()

cambios = 0

# ─── 1. Reemplazar CATALOGO_ZONAS completo (13 zonas -> 4) ──────────
old_zonas_marker = 'CATALOGO_ZONAS: Dict[str, TipoZona] = {'
# Find start and end of CATALOGO_ZONAS
start = codigo.find(old_zonas_marker)
if start >= 0:
    # Find the closing brace - look for the next function/class definition after CATALOGO_ZONAS
    end = codigo.find('\n\n\ndef edificios_para_zona', start)
    if end < 0:
        end = codigo.find('\n\n\ndef ', start + 100)
    
    if end > 0:
        new_zonas = '''CATALOGO_ZONAS: Dict[str, TipoZona] = {

    # ── 4 ZONAS ───────────────────────────────────────────────────

    "residencial": TipoZona("residencial", "Residencial", (70, 130, 180), "🏠",

        categorias_compatibles=["hou_01", "hou_02", "hou_03", "hou_04",

                                "misc_01", "site_08"],

        prima_min=60, prima_max=250, alquiler_min=10, alquiler_max=80),

    "comercial": TipoZona("comercial", "Comercial", (255, 180, 50), "🏢",

        categorias_compatibles=[

            # Negocios y servicios

            "biz_02", "biz_03", "biz_04", "biz_06", "biz_07", "biz_10", "biz_11",

            # Sitios comerciales

            "site_03", "site_09", "site_10",

            # Edificios varios

            "misc_04", "misc_07", "misc_08", "misc_10", "misc_11", "misc_12",

            # Civiles y riesgos

            "civ_01", "civ_02", "rsk_01", "rsk_02", "rsk_03",

            # Universidades

            "univ_01", "univ_02", "univ_03", "univ_04", "univ_05",

            "univ_06", "univ_07", "univ_08", "univ_09", "univ_10",

            # Gobierno

            "gov_01", "gov_02",

            # Oficios

            "oficio_01", "oficio_02", "oficio_04", "oficio_05", "oficio_06",

            "oficio_08", "oficio_10", "oficio_11",

        ],

        prima_min=60, prima_max=300, alquiler_min=12, alquiler_max=100),

    "industrial": TipoZona("industrial", "Industrial", (180, 120, 50), "🏭",

        categorias_compatibles=[

            # Negocios industriales

            "biz_01", "biz_05", "biz_08", "biz_12",

            # Sitios industriales

            "site_01", "site_02", "site_04", "site_05", "site_12",

            # Industria

            "ind_01", "ind_02", "ind_03", "ind_04",

            # Vehiculos

            "veh_01", "veh_02", "veh_03", "veh_04", "veh_05",

            "veh_06", "veh_07", "veh_08", "veh_09", "veh_10",

            # Transporte

            "tra_01", "tra_02",

            # Oficios industriales

            "oficio_07", "oficio_09", "oficio_12",

        ],

        prima_min=80, prima_max=400, alquiler_min=15, alquiler_max=120),

    "ecologico": TipoZona("ecologico", "Ecologico", (34, 139, 34), "🌱",

        categorias_compatibles=[

            # Invernaderos

            "gh_01", "gh_02", "gh_03", "gh_04", "gh_05", "gh_06", "gh_07",

            # Sitios ecologicos

            "site_06", "site_07",

            # Recursos vitales

            "life_01", "life_02", "life_03",

            # Decoracion

            "dec_01", "dec_02", "dec_03", "dec_04", "dec_05",

            "dec_06", "dec_07", "dec_08",

            # Oficios ecologicos

            "oficio_03",

        ],

        prima_min=30, prima_max=150, alquiler_min=8, alquiler_max=50),

}'''

        old_block = codigo[start:end]
        # Ensure we're replacing the right block
        if 'CATALOGO_ZONAS' in old_block and 'edificios_para_zona' not in old_block.split('}\n\n')[-1]:
            codigo = codigo[:start] + new_zonas + codigo[end:]
            cambios += 1
            print("[1/2] CATALOGO_ZONAS reducido a 4 zonas (residencial, comercial, industrial, ecologico)")
        else:
            print("! No se pudo encontrar el bloque exacto de CATALOGO_ZONAS")
    else:
        print("! No se encontro el final de CATALOGO_ZONAS")
else:
    print("! No se encontro CATALOGO_ZONAS")

# ─── 2. Verificar que no haya referencias a zonas eliminadas ────────
# Buscar referencias a las zonas viejas en el codigo (despues de CATALOGO_ZONAS)
zonas_eliminadas = [
    '"vivienda"', '"aeroespacial"', '"investigacion"',
    '"gubernamental"', '"logistica"', '"servicios"', '"militar"',
    '"academico"', '"entretenimiento"',
]

for z in zonas_eliminadas:
    # Solo buscar en referencias a CATALOGO_ZONAS (no en la definicion misma)
    # Buscar fuera del bloque de CATALOGO_ZONAS
    if start >= 0:
        after_catalog = codigo[start + len(old_block):]
    else:
        after_catalog = codigo
    
    # Check in CATALOGO_ZONAS references (getitem lookups)
    if f'CATALOGO_ZONAS[{z}' in after_catalog or f'CATALOGO_ZONAS.\\[{z}' in after_catalog:
        # Replace with "residencial" as default fallback
        codigo = codigo.replace(f'CATALOGO_ZONAS[{z}', 'CATALOGO_ZONAS["residencial"')
        print(f"  -> Referencia a {z} redirigida a residencial")

# ─── Guardar ──────────────────────────────────────────────────────────
if cambios > 0:
    with open(RUTA, "w", encoding="utf-8") as f:
        f.write(codigo)
    print(f"\n✅ {cambios} cambios aplicados a {RUTA}")
else:
    print("\n⚠️ No se aplicaron cambios")
