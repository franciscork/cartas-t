#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMMOON — Sistema de Terreno Procedural
Generación de mapas lunares con biomas, altura y tiles procedurales.

Dependencias: solo math, random, pygame (para generar los tiles)
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame


# ─── Tipos de Terreno ─────────────────────────────────────────────────────

@dataclass
class TerrainType:
    """Define un tipo de terreno lunar con colores y propiedades."""
    name: str
    base_color: Tuple[int, int, int]
    dot_color: Tuple[int, int, int]
    shadow_color: Tuple[int, int, int]


TERRAIN_TYPES: Dict[str, TerrainType] = {
    "regolith":     TerrainType("Regolito",       (60, 55, 65),   (80, 75, 85),   (40, 37, 47)),
    "highlands":    TerrainType("Tierras Altas",  (85, 78, 72),   (105, 98, 92),  (65, 58, 52)),
    "crater_floor": TerrainType("Fondo Cráter",   (40, 38, 48),   (55, 52, 62),   (28, 26, 35)),
    "maria":        TerrainType("Mare Lunar",     (45, 42, 55),   (60, 57, 70),   (30, 28, 40)),
    "crater_rim":   TerrainType("Borde Cráter",   (100, 92, 82),  (120, 112, 102),(78, 70, 60)),
    "ridge":        TerrainType("Cresta",         (110, 100, 85), (130, 120, 105),(88, 78, 63)),
    "basin":        TerrainType("Cuenca",         (35, 33, 42),   (48, 45, 55),   (22, 20, 28)),
}

# Alturas para cada bioma
TERRAIN_HEIGHTS = {
    "basin":        (0.00, 0.15),
    "crater_floor": (0.15, 0.25),
    "maria":        (0.25, 0.32),
    "regolith":     (0.32, 0.50),
    "highlands":    (0.50, 0.60),
    "crater_rim":   (0.60, 0.72),
    "ridge":        (0.72, 1.00),
}


# ─── Ruido Procedural ─────────────────────────────────────────────────────

def _hash_int(n: int) -> int:
    """Hash entero simple para ruido de valor."""
    n = (n ^ (n >> 13)) * 1274126177
    return (n ^ (n >> 16)) & 0x7fffffff


def _value_noise_2d(x: int, y: int, seed: int = 42) -> float:
    """Ruido de valor 2D usando hash entero."""
    n = x * 374761393 + y * 668265263 + seed
    return _hash_int(n) / 2147483647.0  # 0x7fffffff como float


def _smooth_noise(x: float, y: float, scale: float = 8.0, seed: int = 42) -> float:
    """Ruido suave interpolado bilinealmente."""
    sx, sy = x / scale, y / scale
    ix, fx = int(sx), sx - int(sx)
    iy, fy = int(sy), sy - int(sy)
    # Smoothstep
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)
    v00 = _value_noise_2d(ix, iy, seed)
    v10 = _value_noise_2d(ix + 1, iy, seed)
    v01 = _value_noise_2d(ix, iy + 1, seed)
    v11 = _value_noise_2d(ix + 1, iy + 1, seed)
    return v00 + (v10 - v00) * fx + (v01 - v00) * fy + (v11 - v10 - v01 + v00) * fx * fy


def _fbm_noise(x: float, y: float, octaves: int = 3, seed: int = 42) -> float:
    """Ruido fractal (FBM) combinando múltiples octavas."""
    val = 0.0
    amp = 1.0
    freq = 1.0
    max_val = 0.0
    for _ in range(octaves):
        val += amp * _smooth_noise(x * freq, y * freq, 8.0, seed)
        max_val += amp
        amp *= 0.5
        freq *= 2.0
        seed += 1
    return val / max_val


# ─── Generación de Mapa ───────────────────────────────────────────────────

def generar_mapa_terreno(tamanio: int, seed: int = 0
                         ) -> Tuple[List[List[str]], List[List[float]]]:
    """Genera mapa de terreno completo con biomas y altura.
    
    Returns:
        (terrain_grid, height_grid): matrices tamanio x tamanio
        - terrain_grid: tipo de terreno (str key de TERRAIN_TYPES)
        - height_grid: altura normalizada (0.0 - 1.0)
    """
    rng = random.Random(seed + 100)

    # Ruido a gran escala para continentes
    continent = [
        [_fbm_noise(x, y, 3, seed) for x in range(tamanio)]
        for y in range(tamanio)
    ]

    # Ruido a media escala
    mid_noise = [
        [_fbm_noise(x, y, 2, seed + 10) for x in range(tamanio)]
        for y in range(tamanio)
    ]

    # Ruido fino para detalles
    detail = [
        [_fbm_noise(x, y, 1, seed + 20) for x in range(tamanio)]
        for y in range(tamanio)
    ]

    # Cráteres procedurales (5-12 por mapa)
    num_craters = rng.randint(5, 12)
    craters = []
    for i in range(num_craters):
        cx = rng.randint(4, tamanio - 5)
        cy = rng.randint(4, tamanio - 5)
        radius = rng.randint(2, 6)
        depth = rng.uniform(0.3, 0.7)
        craters.append((cx, cy, radius, depth))

    terrain = [["regolith" for _ in range(tamanio)] for _ in range(tamanio)]
    height = [[0.0 for _ in range(tamanio)] for _ in range(tamanio)]

    for y in range(tamanio):
        for x in range(tamanio):
            c = continent[y][x]
            d = detail[y][x]

            # Altura base del continente (0.2 - 0.8)
            h = 0.2 + c * 0.6

            # Aplicar cráteres
            for cx, cy, radius, depth in craters:
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < radius:
                    # Borde elevado
                    rim_factor = 1.0 - abs(dist - radius * 0.7) / (radius * 0.3 + 0.01)
                    if rim_factor > 0:
                        h += rim_factor * 0.15 * depth
                    # Fondo hundido
                    floor_factor = 1.0 - dist / (radius * 0.7 + 0.01)
                    if floor_factor > 0:
                        h -= floor_factor * 0.3 * depth

            # Detalle fino
            h += (d - 0.5) * 0.08

            # Normalizar
            h = max(0.0, min(1.0, h))
            height[y][x] = h

            # Asignar bioma según altura
            if h < 0.15:
                terrain[y][x] = "basin"
            elif h < 0.25:
                terrain[y][x] = "crater_floor"
            elif h < 0.32:
                terrain[y][x] = "maria"
            elif h < 0.50:
                terrain[y][x] = "regolith"
            elif h < 0.60:
                terrain[y][x] = "highlands"
            elif h < 0.72:
                terrain[y][x] = "crater_rim"
            else:
                terrain[y][x] = "ridge"

    return terrain, height


# ─── Generación de Tiles Procedurales ─────────────────────────────────────

def _crear_tile_terreno(tipo: str, tamanio: int = 64) -> pygame.Surface:
    """Crea un tile de terreno procedural para un tipo de bioma.
    
    Cada tile tiene textura única con variaciones de puntos, líneas
    y sombreado que simulan la superficie lunar.
    """
    tt = TERRAIN_TYPES.get(tipo, TERRAIN_TYPES["regolith"])
    surf = pygame.Surface((tamanio, tamanio), pygame.SRCALPHA)
    rng = random.Random(hash(tipo))

    # Fondo base
    surf.fill(tt.base_color)

    # Textura de regolito: puntos dispersos
    num_puntos = rng.randint(6, 14)
    for _ in range(num_puntos):
        rx = rng.randint(2, tamanio - 3)
        ry = rng.randint(2, tamanio - 3)
        radio = rng.randint(1, 4)
        color = tt.dot_color
        pygame.draw.circle(surf, color, (rx, ry), radio)

    # Sombras / cráteres pequeños
    num_sombras = rng.randint(2, 5)
    for _ in range(num_sombras):
        sx = rng.randint(8, tamanio - 8)
        sy = rng.randint(8, tamanio - 8)
        sr = rng.randint(3, 8)
        # Sombra
        pygame.draw.circle(surf, tt.shadow_color, (sx + 1, sy + 1), sr)
        # Resalte
        resalte = tuple(min(255, c + 25) for c in tt.base_color)
        pygame.draw.circle(surf, resalte, (sx - 1, sy - 1), sr)

    # Líneas de fractura (grietas) — solo en algunos tiles
    if rng.random() < 0.35:
        color_grieta = tt.shadow_color
        x1 = rng.randint(0, tamanio)
        y1 = rng.randint(0, tamanio)
        for _ in range(rng.randint(3, 6)):
            ang = rng.uniform(0, math.pi * 2)
            dist = rng.randint(4, 14)
            x2 = int(x1 + math.cos(ang) * dist)
            y2 = int(y1 + math.sin(ang) * dist)
            x2 = max(0, min(tamanio - 1, x2))
            y2 = max(0, min(tamanio - 1, y2))
            pygame.draw.line(surf, color_grieta, (x1, y1), (x2, y2), 1)
            x1, y1 = x2, y2

    # Borde isométrico (más oscuro en bordes inferior y derecho)
    for i in range(4):
        alpha = 40 - i * 8
        if alpha > 0:
            # Borde inferior
            pygame.draw.line(surf, (0, 0, 0, alpha),
                           (0, tamanio - 1 - i), (tamanio - 1, tamanio - 1 - i), 1)
            # Borde derecho
            pygame.draw.line(surf, (0, 0, 0, alpha),
                           (tamanio - 1 - i, 0), (tamanio - 1 - i, tamanio - 1 - i), 1)

    return surf


def generar_tiles_terreno(tamanio: int = 64) -> Dict[str, pygame.Surface]:
    """Genera tiles procedurales para todos los tipos de terreno."""
    tiles = {}
    for tipo in TERRAIN_TYPES:
        tiles[tipo] = _crear_tile_terreno(tipo, tamanio)
    return tiles


# ─── Paleta de colores para minimapa ──────────────────────────────────────

TERRAIN_MINIMAP_COLORS: Dict[str, Tuple[int, int, int]] = {
    "regolith":     (80, 75, 85),
    "highlands":    (105, 98, 92),
    "crater_floor": (55, 52, 62),
    "maria":        (60, 57, 70),
    "crater_rim":   (120, 112, 102),
    "ridge":        (130, 120, 105),
    "basin":        (48, 45, 55),
}
