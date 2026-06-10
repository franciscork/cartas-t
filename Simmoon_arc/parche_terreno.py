#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parche para integrar el sistema de terreno procedural en juego_simmoon.py"""

import re

RUTA = "juego_simmoon.py"

with open(RUTA, "r", encoding="utf-8") as f:
    codigo = f.read()

cambios = 0

# ─── 1. Import ─────────────────────────────────────────────────────────
if "simmoon_terrain" not in codigo:
    import_marker = "from typing import Optional, Tuple, List, Dict\n\n\n\n# \u2500\u2500\u2500 Inicializaci\u00f3n de Pygame"
    import_block = '''from typing import Optional, Tuple, List, Dict


# \u2500\u2500\u2500 Sistema de Terreno \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

from simmoon_terrain import (

    TERRAIN_TYPES, TERRAIN_HEIGHTS, TERRAIN_MINIMAP_COLORS,

    generar_mapa_terreno, generar_tiles_terreno,

)


# \u2500\u2500\u2500 Inicializaci\u00f3n de Pygame'''
    codigo = codigo.replace(import_marker, import_block, 1)
    cambios += 1
    print("  [1/7] Import agregado")

# ─── 2. Mapa.__init__ ─────────────────────────────────────────────────
if "generar_terreno" not in codigo:
    old = '        self.zonas: List[List[Optional[str]]] = [\n\n            [None for _ in range(self.tamanio)] for _ in range(self.tamanio)\n\n        ]\n\n    \n\n    def _footprint_libre'
    new = '''        self.zonas: List[List[Optional[str]]] = [

            [None for _ in range(self.tamanio)] for _ in range(self.tamanio)

        ]

        self.terrain: List[List[str]] = [

            ["regolith" for _ in range(self.tamanio)] for _ in range(self.tamanio)

        ]

        self.height: List[List[float]] = [

            [0.5 for _ in range(self.tamanio)] for _ in range(self.tamanio)

        ]

        self.generar_terreno()

    

    def generar_terreno(self, seed: int = 0) -> None:

        """Genera el terreno procedural con biomas y altura."""

        self.terrain, self.height = generar_mapa_terreno(self.tamanio, seed)



    def _footprint_libre'''
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("  [2/7] Mapa.__init__ actualizado")

# ─── 3. tiles_terreno dict en Renderizador ────────────────────────────
if "tiles_terreno" not in codigo:
    old = '        self.tile_terreno: Optional[pygame.Surface] = None\n\n        self.tile_terreno_base: Optional[pygame.Surface] = None\n\n        self.sprites_cache: Dict[str, pygame.Surface] = {}'
    new = '        self.tile_terreno: Optional[pygame.Surface] = None\n\n        self.tile_terreno_base: Optional[pygame.Surface] = None\n\n        self.tiles_terreno: Dict[str, pygame.Surface] = {}  # Multiples biomas\n\n        self.sprites_cache: Dict[str, pygame.Surface] = {}'
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("  [3/7] tiles_terreno agregado")

# ─── 4. _generar_tiles_terreno en init ────────────────────────────────
if "_generar_tiles_terreno" not in codigo:
    old = '        self._inicializar_fuentes()\n\n        self._cargar_terreno()'
    new = '        self._inicializar_fuentes()\n\n        self._generar_tiles_terreno()\n\n        self._cargar_terreno()'
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("  [4/7] _generar_tiles_terreno agregado al init")

# ─── 5. Reemplazar _cargar_terreno y eliminar _crear_tile_por_defecto ─
if "_generar_tiles_terreno" not in codigo or True:  # check again
    # Find and replace _cargar_terreno + _crear_tile_por_defecto
    pattern = r'    def _cargar_terreno\(self\) -> None:.*?return surf'
    replacement = '''    def _generar_tiles_terreno(self) -> None:

        """Genera tiles procedurales para todos los biomas del terreno."""

        self.tiles_terreno = generar_tiles_terreno(64)

        self.tile_terreno = self.tiles_terreno.get("regolith")

        self.tile_terreno_base = self._crear_tile_base()

    

    def _cargar_terreno(self) -> None:

        """Carga los tiles de terreno base (legacy: usa procedural)."""

        pass'''
    
    # Use a simpler approach - just find the first occurrence
    start = codigo.find('    def _cargar_terreno(self) -> None:')
    if start >= 0:
        # Find the function body - look for the next function or class def
        end = codigo.find('\n    def ', start + 10)
        if end < 0:
            end = codigo.find('\n    class ', start + 10)
        
        # But _crear_tile_por_defecto comes right after, so include it too
        end2 = codigo.find('\n    def _crear_tile_base', start + 10)
        if end2 > 0:
            end = end2
        
        old_funcs = codigo[start:end]
        if '_crear_tile_por_defecto' in old_funcs:
            codigo = codigo[:start] + replacement + codigo[end:]
            cambios += 1
            print("  [5/7] _cargar_terreno + _crear_tile_por_defecto reemplazados")
        else:
            print("  ! _crear_tile_por_defecto no encontrado junto a _cargar_terreno")
    else:
        print("  ! _cargar_terreno no encontrado")

# ─── 6. renderizar_mapa multi-bioma ───────────────────────────────────
if "tipo_terreno = mapa.terrain" not in codigo:
    old = '                # Renderizar tile de terreno\n\n                if self.tile_terreno:\n\n                    tile_escalado = pygame.transform.scale(self.tile_terreno, (tam, tam))\n\n                else:\n\n                    tile_escalado = pygame.transform.scale(self.tile_terreno_base, (tam, tam))\n\n                \n\n                pantalla.blit(tile_escalado, (px - tam // 2, py - tam // 4))\n\n\n\n                # Overlay de zona (si existe)'
    new = '''                # Renderizar tile de terreno (por bioma)

                tipo_terreno = "regolith"

                if hasattr(mapa, "terrain") and y < len(mapa.terrain) and x < len(mapa.terrain[y]):

                    tipo_terreno = mapa.terrain[y][x]

                tile = self.tiles_terreno.get(tipo_terreno, self.tile_terreno)

                if tile:

                    tile_escalado = pygame.transform.scale(tile, (tam, tam))

                elif self.tile_terreno:

                    tile_escalado = pygame.transform.scale(self.tile_terreno, (tam, tam))

                else:

                    tile_escalado = pygame.transform.scale(self.tile_terreno_base, (tam, tam))

                

                # Sombra de elevacion

                if hasattr(mapa, "height") and y < len(mapa.height) and x < len(mapa.height[y]):

                    h = mapa.height[y][x]

                    bright = int((h - 0.5) * 40)

                    if bright != 0:

                        overlay = pygame.Surface((tam, tam), pygame.SRCALPHA)

                        if bright > 0:

                            overlay.fill((bright, bright, bright, 30))

                        else:

                            overlay.fill((-bright, -bright, -bright, 20))

                        pantalla.blit(overlay, (px - tam // 2, py - tam // 4))

                

                pantalla.blit(tile_escalado, (px - tam // 2, py - tam // 4))



                # Overlay de zona (si existe)'''
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("  [6/7] renderizar_mapa con multi-bioma")

# ─── 7. Minimapa con colores de terreno ───────────────────────────────
if "TERRAIN_MINIMAP_COLORS" not in codigo:
    old = '                color = (40, 38, 50)\n\n                edif = mapa.grid[gy][gx]\n\n                zona_id = mapa.zonas[gy][gx]\n\n                if edif:'
    new = '''                color = (40, 38, 50)

                # Color del terreno

                if hasattr(mapa, "terrain") and gy < len(mapa.terrain) and gx < len(mapa.terrain[gy]):

                    color = TERRAIN_MINIMAP_COLORS.get(mapa.terrain[gy][gx], (40, 38, 50))

                edif = mapa.grid[gy][gx]

                zona_id = mapa.zonas[gy][gx]

                if edif:'''
    codigo = codigo.replace(old, new, 1)
    cambios += 1
    print("  [7/7] Minimapa con colores de terreno")

# ─── Guardar ──────────────────────────────────────────────────────────
if cambios > 0:
    with open(RUTA, "w", encoding="utf-8") as f:
        f.write(codigo)
    print(f"\n\u2705 {cambios}/7 cambios aplicados a {RUTA}")
else:
    print("\n\u26a0\ufe0f No se aplicaron cambios")
