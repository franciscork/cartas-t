#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parche para agregar misc_05 a la zona comercial"""

RUTA = "juego_simmoon.py"

with open(RUTA, "r", encoding="utf-8") as f:
    codigo = f.read()

# Find and fix: add misc_05 to comercial zone's misc building list
old = '"misc_04", "misc_07", "misc_08", "misc_10", "misc_11", "misc_12"'
new = '"misc_04", "misc_05", "misc_07", "misc_08", "misc_10", "misc_11", "misc_12"'

if old in codigo and "misc_05" not in codigo:
    codigo = codigo.replace(old, new, 1)
    with open(RUTA, "w", encoding="utf-8") as f:
        f.write(codigo)
    print("✅ misc_05 agregado a zona comercial")
else:
    print("⚠️ misc_05 ya estaba presente o no se encontro")
