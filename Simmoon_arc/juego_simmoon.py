#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

╔══════════════════════════════════════════════════════════════╗

║  SIMMOON — Constructor de Colonia Lunar                    ║

║  Motor: Pygame 2.5+ | Estilo: SimCity 2000 + SimFarm       ║

║  Assets: 1536 sprites pixel-art generados con IA           ║

║  Comentarios: Español 🇪🇸                                  ║

╚══════════════════════════════════════════════════════════════╝



Controles:

  - Click izquierdo: colocar edificio seleccionado

  - Click derecho: cancelar selección / vender edificio

  - Rueda ratón: zoom (acercar/alejar)

  - WASD / Flechas: mover cámara

  - ESC: salir

  - 1-3: seleccionar categoría de construcción

  - B: modo construir

  - V: modo vender

"""



import os

import sys

import math

import random

import json

import struct

import urllib.request

import urllib.error

from pathlib import Path

from dataclasses import dataclass, field

from typing import Optional, Tuple, List, Dict

import logging

# ── Logging setup ──
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─── Sistema de Terreno ──────────────────────────────────────

from simmoon_terrain import (

    TERRAIN_TYPES, TERRAIN_HEIGHTS, TERRAIN_MINIMAP_COLORS,

    generar_mapa_terreno, generar_tiles_terreno,

)


# ─── Inicialización de Pygame ─────────────────────────────────────────────

try:

    import pygame

except ImportError:

    print("❌ Pygame no está instalado.")

    print("   Instálalo con: pip install pygame")

    sys.exit(1)



pygame.init()

pygame.display.set_caption("☾ SIMMOON — Colonia Lunar")

from renderizador import Renderizador# ─── Configuración ─────────────────────────────────────────────────────────


# ─── Sonidos Procedurales ──────────────────────────────────────────────────
from game_sound import SonidoProcedural


@dataclass

class Config:

    """Configuración global del juego."""

    # Ventana

    ANCHO_VENTANA: int = 1280

    ALTO_VENTANA: int = 720

    FPS: int = 60



    # Mapa

    TAMANIO_GRID: int = 40  # 40x40 tiles (colonia expandida)

    TAMANIO_TILE: int = 64  # px base del tile (se escala con zoom)



    # Colores (paleta retro Sci-Fi)

    COLOR_FONDO: Tuple[int, int, int] = (10, 10, 25)

    COLOR_GRID: Tuple[int, int, int] = (30, 30, 55, 80)

    COLOR_TILE_HOVER: Tuple[int, int, int] = (60, 180, 75, 120)

    COLOR_TILE_INVALIDO: Tuple[int, int, int] = (220, 60, 60, 100)

    COLOR_PANEL: Tuple[int, int, int] = (18, 18, 35)

    COLOR_PANEL_BORDE: Tuple[int, int, int] = (50, 50, 80)

    COLOR_TEXTO: Tuple[int, int, int] = (220, 220, 240)

    COLOR_TEXTO_VERDE: Tuple[int, int, int] = (0, 200, 150)

    COLOR_TEXTO_ROJO: Tuple[int, int, int] = (255, 100, 100)

    COLOR_TEXTO_AMARILLO: Tuple[int, int, int] = (255, 210, 80)

    COLOR_BOTON: Tuple[int, int, int] = (40, 40, 70)

    COLOR_BOTON_HOVER: Tuple[int, int, int] = (70, 60, 120)

    COLOR_BOTON_SELECCIONADO: Tuple[int, int, int] = (100, 80, 200)

    # Recursos iniciales

    CREDITOS_INICIALES: int = 5000

    ENERGIA_INICIAL: int = 100

    OXIGENO_INICIAL: int = 100

    AGUA_INICIAL: int = 100

    PRESION_INICIAL: int = 100



    # Ciclo lunar (14 turnos de día, 14 de noche)

    DIAS_LUZ: int = 14

    DIAS_NOCHE: int = 14

    # Felicidad de colonos
    FELICIDAD_INICIAL: int = 65
    FELICIDAD_MAX: int = 100
    FELICIDAD_MIN: int = 0
    FELICIDAD_UMBRAL_CONTENTO: int = 70
    FELICIDAD_UMBRAL_ENOJADO: int = 35
    BONUS_FELICIDAD: float = 1.25
    PENALTY_FELICIDAD: float = 0.75

# ─── Datos de Edificios ───────────────────────────────────────────────────

@dataclass

class TipoEdificio:

    """Define las propiedades de un tipo de edificio."""

    id: str                # Identificador único (ej: "biz_01")

    nombre: str            # Nombre para mostrar

    categoria: str         # Categoría (businesses, solar_energy, etc.)

    sprite_archivo: str    # Nombre del archivo PNG

    costo: int = 100       # Coste en créditos

    produce_energia: int = 0    # Energía generada (positivo) o consumida (negativo)

    produce_oxigeno: int = 0    # Oxígeno generado o consumido

    produce_agua: int = 0       # Agua generada o consumida

    produce_presion: int = 0        # Presi?n generada (positivo) o consumida (negativo)
    produce_felicidad: int = 0      # Felicidad que aporta a los colonos

    mantenimiento: int = 5      # Coste de mantenimiento por turno

    empleos: int = 0            # Puestos de trabajo que genera

    alquiler: int = 0           # Ingreso mensual por alquiler (0 = no genera)

    descripcion: str = ""       # Descripción del edificio

    ancho_tiles: int = 1        # Ancho en tiles (1-4)

    alto_tiles: int = 1         # Alto en tiles (1-4)



    @property

    def ruta_sprite(self) -> str:

        """Ruta al archivo pixel-art del sprite."""

        return f"{self.categoria}_pixel/{self.sprite_archivo}"



# ─── Sistema de Votos ────────────────────────────────────────────────────



# URL de la API de votos (puede no estar disponible)

VOTE_API_URL = "http://localhost:9099/api/votes"



def cargar_votos(dir_assets: str) -> Dict[str, int]:

    """

    Carga los votos desde la API o desde un archivo local votes.json.

    Retorna un diccionario {asset_id: vote_value} con los assets que tienen al menos 1 voto.

    Si no hay votos disponibles, retorna un diccionario vacío (no se muestran edificios).

    """

    votos = {}



    # Intentar 1: API de votos (servidor local)

    try:

        req = urllib.request.Request(VOTE_API_URL)

        with urllib.request.urlopen(req, timeout=2) as resp:

            data = json.loads(resp.read().decode())

            if isinstance(data, list):

                for v in data:

                    asset_id = v.get("asset_id", "")

                    vote_value = v.get("vote_value", 0)

                    if asset_id and vote_value >= 1:

                        votos[asset_id] = max(votos.get(asset_id, 0), vote_value)

        if votos:

            log.info(f"Votos cargados desde API: {len(votos)} assets")

            return votos

    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):

        pass  # API no disponible, intentar archivo local



    # Intentar 2: Archivo votes.json local

    ruta_json = Path(dir_assets) / "votes.json"

    if ruta_json.exists():

        try:

            with open(ruta_json, "r", encoding="utf-8") as f:

                data = json.load(f)

            if isinstance(data, list):

                for v in data:

                    asset_id = v.get("asset_id", "")

                    vote_value = v.get("vote_value", 0)

                    if asset_id and vote_value >= 1:

                        votos[asset_id] = max(votos.get(asset_id, 0), vote_value)

            if votos:

                log.info(f"Votos cargados desde votes.json: {len(votos)} assets")

                return votos

        except (json.JSONDecodeError, OSError):

            pass



    log.warning("No se encontraron votos. No hay edificios disponibles.")

    log.warning("Usa viewer.html para votar y desbloquear edificios.")

    return votos  # Diccionario vacío = sin edificios



def filtrar_catalogo_por_votos(votos: Dict[str, int]) -> Dict[str, TipoEdificio]:

    """

    Filtra el catálogo completo de edificios para incluir SOLO aquellos

    que tienen al menos un voto registrado.

    Si no hay votos, retorna un diccionario vacío.

    """

    if not votos:

        log.warning("Sin votos: catalogo vacio. Usa viewer.html para votar.")

        return {}



    filtrado = {}

    for asset_id, tipo in CATALOGO_EDIFICIOS.items():

        if asset_id in votos:

            filtrado[asset_id] = tipo



    print(f"  🗳️  Catálogo filtrado: {len(filtrado)}/{len(CATALOGO_EDIFICIOS)} edificios (con votos)")

    return filtrado



# ─── Catálogo de Edificios Disponibles ────────────────────────────────────

CATALOGO_EDIFICIOS: Dict[str, TipoEdificio] = {

    # ── Negocios (businesses) ── Tamaños: 1x1, 2x1, 2x2 ──

    "biz_01": TipoEdificio("biz_01", "Oficina Minera", "businesses",

                           "biz_oficina_minera_blender.png",

                           costo=500, produce_energia=-5, produce_oxigeno=-2,

                           mantenimiento=10, empleos=8, ancho_tiles=1, alto_tiles=1,

                           descripcion="Centro administrativo de minería lunar."),

    "biz_02": TipoEdificio("biz_02", "Puesto Comercial", "businesses",

                           "biz_02_lunar_trading_post_pixel.png",

                           costo=400, produce_energia=-3, produce_oxigeno=-1,

                           mantenimiento=5, empleos=5, ancho_tiles=1, alto_tiles=1,

                           descripcion="Mercado de intercambio de recursos.", alquiler=20),

    "biz_03": TipoEdificio("biz_03", "Hotel Lunar", "businesses",

                           "biz_hotel_lunar_blender.png",

                           costo=800, produce_energia=-8, produce_oxigeno=-3, produce_agua=-2,

                           mantenimiento=15, empleos=10, ancho_tiles=2, alto_tiles=1,

                           descripcion="Alojamiento para visitantes y turistas. 2x1", alquiler=50),

    "biz_04": TipoEdificio("biz_04", "Restaurante Lunar", "businesses",

                           "biz_restaurante_lunar_blender.png",

                           costo=350, produce_energia=-4, produce_oxigeno=-1, produce_agua=-1,

                           mantenimiento=8, empleos=6, ancho_tiles=1, alto_tiles=1,

                           produce_felicidad=8,
                           descripcion="Gastronomía para la colonia.", alquiler=20),

    "biz_05": TipoEdificio("biz_05", "Laboratorio", "businesses",

                           "biz_laboratorio_blender.png",

                           costo=1200, produce_energia=-10, produce_oxigeno=-2,

                           mantenimiento=20, empleos=12, ancho_tiles=2, alto_tiles=2,

                           descripcion="Investigación científica avanzada. 2x2"),

    "biz_06": TipoEdificio("biz_06", "Centro Médico", "businesses",

                           "biz_centro_medico_blender.png",

                           costo=900, produce_energia=-7, produce_oxigeno=-3,

                           mantenimiento=15, empleos=10, ancho_tiles=2, alto_tiles=1,

                           produce_felicidad=12,
                           descripcion="Atención médica para los colonos. 2x1"),

    "biz_07": TipoEdificio("biz_07", "Terminal Espacial", "businesses",

                           "biz_terminal_espacial_blender.png",

                           costo=2000, produce_energia=-15, produce_oxigeno=-5,

                           mantenimiento=30, empleos=20, ancho_tiles=3, alto_tiles=2,

                           descripcion="Puerto de llegada y salida de naves. 3x2", alquiler=80),

    "biz_08": TipoEdificio("biz_08", "Fábrica", "businesses",

                           "biz_fabrica_blender.png",

                           costo=1500, produce_energia=-20, produce_oxigeno=-4, produce_agua=-3,

                           mantenimiento=25, empleos=15, ancho_tiles=2, alto_tiles=2,

                           descripcion="Planta de manufactura pesada. 2x2", alquiler=60),

    "biz_10": TipoEdificio("biz_10", "Banco Lunar", "businesses",

                           "biz_banco_lunar_blender.png",

                           costo=600, produce_energia=-3, produce_oxigeno=-1,

                           mantenimiento=5, empleos=4, ancho_tiles=1, alto_tiles=1,

                           descripcion="Institución financiera de la colonia.", alquiler=30),

    "biz_11": TipoEdificio("biz_11", "Tienda Lunar", "businesses",

                           "biz_tienda_lunar_blender.png",

                           costo=300, produce_energia=-2, produce_oxigeno=-1,

                           mantenimiento=3, empleos=3, ancho_tiles=1, alto_tiles=1,

                           descripcion="Tienda de suministros generales.", alquiler=15),

    "biz_12": TipoEdificio("biz_12", "Almacén", "businesses",

                           "biz_almacen_blender.png",

                           costo=250, produce_energia=-2,

                           mantenimiento=3, empleos=2, ancho_tiles=2, alto_tiles=1,

                           descripcion="Almacenamiento de recursos y mercancías. 2x1", alquiler=25),



    # ── Energía Solar (solar_energy) ── Tamaños: 1x1, 2x1, 2x2 ──

    "sol_01": TipoEdificio("sol_01", "Paneles Solares", "solar_energy",

                           "sol_01_solar_panel_array_pixel.png",

                           costo=300, produce_energia=15,

                           mantenimiento=2, empleos=1, ancho_tiles=2, alto_tiles=1,

                           descripcion="Genera energía limpia del sol. 2x1"),

    "sol_02": TipoEdificio("sol_02", "Central Solar", "solar_energy",

                           "sol_02_solar_power_station_pixel.png",

                           costo=600, produce_energia=30,

                           mantenimiento=5, empleos=3, ancho_tiles=2, alto_tiles=2,

                           descripcion="Estación solar de alta potencia. 2x2"),

    "sol_03": TipoEdificio("sol_03", "Reactor Nuclear", "solar_energy",

                           "sol_03_nuclear_reactor_pixel.png",

                           costo=2500, produce_energia=100,

                           mantenimiento=30, empleos=8, ancho_tiles=2, alto_tiles=2,

                           descripcion="Generador masivo de energía. 2x2"),

    "sol_04": TipoEdificio("sol_04", "Baterías", "solar_energy",

                           "sol_04_battery_storage_pixel.png",

                           costo=400, produce_energia=0,

                           mantenimiento=1, empleos=0, ancho_tiles=1, alto_tiles=1,

                           descripcion="Almacena el exceso de energía."),

    "sol_07": TipoEdificio("sol_07", "Reactor Helio-3", "solar_energy",

                           "sol_07_helium_3_reactor_pixel.png",

                           costo=3500, produce_energia=200,

                           mantenimiento=40, empleos=12, ancho_tiles=3, alto_tiles=2,

                           descripcion="Fusión nuclear de helio-3. 3x2"),

    "sol_08": TipoEdificio("sol_08", "Subestación", "solar_energy",

                           "sol_08_power_substation_pixel.png",

                           costo=200, produce_energia=5,

                           mantenimiento=2, empleos=1, ancho_tiles=1, alto_tiles=1,

                           descripcion="Distribuye energía a la red de la colonia."),



    # ── Vehículos (vehicles) ──

    "veh_01": TipoEdificio("veh_01", "Lunar Rover", "vehicles",

                           "veh_01_lunar_rover_pixel.png",

                           costo=200, produce_energia=-3, mantenimiento=5, empleos=1,

                           descripcion="Explorador lunar todoterreno."),

    "veh_02": TipoEdificio("veh_02", "Camión Minero", "vehicles",

                           "veh_02_mining_truck_pixel.png",

                           costo=350, produce_energia=-5, mantenimiento=8, empleos=2,

                           ancho_tiles=2, alto_tiles=1,

                           descripcion="Transporte pesado de minerales. 2x1"),

    "veh_03": TipoEdificio("veh_03", "Lanzadera Pasajeros", "vehicles",

                           "veh_03_passenger_shuttle_pixel.png",

                           costo=400, produce_energia=-4, mantenimiento=6, empleos=2,

                           ancho_tiles=2, alto_tiles=1,

                           descripcion="Transporte de colonos. 2x1"),

    "veh_04": TipoEdificio("veh_04", "Carguero Pesado", "vehicles",

                           "veh_04_cargo_hauler_pixel.png",

                           costo=500, produce_energia=-8, mantenimiento=10, empleos=3,

                           ancho_tiles=2, alto_tiles=2,

                           descripcion="Transporte de carga intercolonial. 2x2"),

    "veh_05": TipoEdificio("veh_05", "Vehículo de Emergencia", "vehicles",

                           "veh_05_emergency_vehicle_pixel.png",

                           costo=250, produce_energia=-3, mantenimiento=4, empleos=1,

                           descripcion="Respuesta rápida a emergencias."),

    "veh_06": TipoEdificio("veh_06", "Excavadora", "vehicles",

                           "veh_06_construction_excavator_pixel.png",

                           costo=450, produce_energia=-6, mantenimiento=8, empleos=2,

                           ancho_tiles=2, alto_tiles=1,

                           descripcion="Maquinaria pesada de construcción. 2x1"),

    "veh_07": TipoEdificio("veh_07", "Moto Flotante", "vehicles",

                           "veh_07_hover_bike_pixel.png",

                           costo=150, produce_energia=-2, mantenimiento=3, empleos=1,

                           descripcion="Transporte personal rápido."),

    "veh_08": TipoEdificio("veh_08", "Autobús Lunar", "vehicles",

                           "veh_08_moon_bus_pixel.png",

                           costo=300, produce_energia=-4, mantenimiento=5, empleos=1,

                           ancho_tiles=2, alto_tiles=1,

                           descripcion="Transporte público de colonos. 2x1"),

    "veh_09": TipoEdificio("veh_09", "Dron de Suministro", "vehicles",

                           "veh_09_supply_drone_pixel.png",

                           costo=180, produce_energia=-1, mantenimiento=2, empleos=0,

                           descripcion="Entrega autónoma de suministros."),

    "veh_10": TipoEdificio("veh_10", "Tanque Lunar", "vehicles",

                           "veh_10_lunar_tank_pixel.png",

                           costo=600, produce_energia=-10, mantenimiento=12, empleos=3,

                           ancho_tiles=2, alto_tiles=2,

                           descripcion="Defensa y patrulla de la colonia. 2x2"),



    # ── Carreteras (roads) ──

    "road_01": TipoEdificio("road_01", "Carretera Recta", "roads",

                            "road_01_straight_road_pixel.png",

                            costo=50, mantenimiento=0,

                            descripcion="Conexión básica entre edificios."),

    "road_02": TipoEdificio("road_02", "Carretera Curva", "roads",

                            "road_02_curved_road_pixel.png",

                            costo=60, mantenimiento=0,

                            descripcion="Curva de carretera lunar."),

    "road_03": TipoEdificio("road_03", "Intersección T", "roads",

                            "road_03_t_junction_pixel.png",

                            costo=70, mantenimiento=0,

                            descripcion="Cruce en forma de T."),

    "road_04": TipoEdificio("road_04", "Cruce de Caminos", "roads",

                            "road_04_crossroad_intersection_pixel.png",

                            costo=80, mantenimiento=0,

                            descripcion="Intersección de 4 vías."),

    "road_05": TipoEdificio("road_05", "Túnel", "roads",

                            "road_05_tunnel_entrance_pixel.png",

                            costo=150, mantenimiento=2,

                            descripcion="Acceso subterráneo entre cráteres."),

    "road_06": TipoEdificio("road_06", "Puente", "roads",

                            "road_06_bridge_pixel.png",

                            costo=200, mantenimiento=3,

                            descripcion="Conexión elevada sobre terreno irregular."),

    "road_07": TipoEdificio("road_07", "Vía Férrea", "roads",

                            "road_07_rail_track_pixel.png",

                            costo=120, mantenimiento=1,

                            descripcion="Transporte ferroviario eficiente."),

    "road_08": TipoEdificio("road_08", "Estación Ferroviaria", "roads",

                            "road_08_rail_station_platform_pixel.png",

                            costo=300, produce_energia=-2, mantenimiento=5, empleos=3,

                            ancho_tiles=2, alto_tiles=1,

                            descripcion="Parada del tren lunar. 2x1"),



    # ── Decoración (decorations) ──

    "dec_01": TipoEdificio("dec_01", "Formación Rocosa", "decorations",

                           "dec_01_lunar_rock_formation_pixel.png",

                           costo=20, mantenimiento=0,

                           descripcion="Roca natural lunar decorativa."),

    "dec_02": TipoEdificio("dec_02", "Asta de Bandera", "decorations",

                           "dec_02_flag_pole_earth_pixel.png",

                           costo=15, mantenimiento=0,

                           descripcion="Bandera de la Tierra en la Luna."),

    "dec_03": TipoEdificio("dec_03", "Farola Lunar", "decorations",

                           "dec_03_street_lamp_pixel.png",

                           costo=10, produce_energia=-1, mantenimiento=0,

                           descripcion="Iluminación exterior para la colonia."),

    "dec_04": TipoEdificio("dec_04", "Banco de Parque", "decorations",

                           "dec_04_park_bench_pixel.png",

                           costo=25, mantenimiento=0,

                           descripcion="Zona de descanso para colonos."),

    "dec_05": TipoEdificio("dec_05", "Monumento", "decorations",

                           "dec_05_monument_statue_pixel.png",

                           costo=100, mantenimiento=1, ancho_tiles=2, alto_tiles=2,

                           produce_felicidad=5,
                           descripcion="Monumento a los pioneros lunares. 2x2"),

    "dec_06": TipoEdificio("dec_06", "Restos de Satélite", "decorations",

                           "dec_06_satellite_debris_pixel.png",

                           costo=0, mantenimiento=0,

                           descripcion="Chatarra espacial decorativa."),

    "dec_07": TipoEdificio("dec_07", "Baliza Solar", "decorations",

                           "dec_07_solar_beacon_pixel.png",

                           costo=50, produce_energia=2, mantenimiento=0,

                           descripcion="Pequeña baliza con panel solar."),

    "dec_08": TipoEdificio("dec_08", "Contenedores", "decorations",

                           "dec_08_cargo_container_stack_pixel.png",

                           costo=30, mantenimiento=0, ancho_tiles=2, alto_tiles=1,

                           descripcion="Almacenamiento temporal exterior. 2x1", alquiler=10),



    # ── Invernaderos (greenhouses) ──

    "gh_01": TipoEdificio("gh_01", "Cúpula Pequeña", "greenhouses",

                          "gh_01_small_dome_greenhouse_pixel.png",

                          costo=400, produce_oxigeno=10, produce_agua=5, produce_energia=-2,

                          mantenimiento=5, empleos=2, ancho_tiles=2, alto_tiles=2,

                          produce_presion=3,

                          descripcion="Invernadero básico. O2+10, Agua+5. 2x2"),

    "gh_02": TipoEdificio("gh_02", "Gran Invernadero", "greenhouses",

                          "gh_02_large_greenhouse_pixel.png",

                          costo=800, produce_oxigeno=25, produce_agua=10, produce_energia=-5,

                          mantenimiento=10, empleos=4, ancho_tiles=3, alto_tiles=2,

                          descripcion="Producción masiva de oxígeno. 3x2"),

    "gh_03": TipoEdificio("gh_03", "Granja Vertical", "greenhouses",

                          "gh_03_vertical_farm_pixel.png",

                          costo=300, produce_oxigeno=5, produce_energia=-2,

                          mantenimiento=3, empleos=2,

                          descripcion="Cultivo hidropónico vertical."),

    "gh_04": TipoEdificio("gh_04", "Lab. Hidropónico", "greenhouses",

                          "gh_04_hydroponics_lab_pixel.png",

                          costo=350, produce_oxigeno=8, produce_energia=-3,

                          mantenimiento=4, empleos=2, ancho_tiles=2, alto_tiles=1,

                          descripcion="Investigación de cultivos lunares. 2x1"),

    "gh_05": TipoEdificio("gh_05", "Bahía Acuapónica", "greenhouses",

                          "gh_05_aquaponics_bay_pixel.png",

                          costo=500, produce_oxigeno=12, produce_agua=15, produce_energia=-4,

                          mantenimiento=6, empleos=3, ancho_tiles=2, alto_tiles=2,

                          descripcion="Peces + plantas en simbiosis. 2x2"),

    "gh_06": TipoEdificio("gh_06", "Jardín de Hierbas", "greenhouses",

                          "gh_06_herb_garden_dome_pixel.png",

                          costo=200, produce_oxigeno=4, produce_energia=-1,

                          mantenimiento=2, empleos=1,

                          descripcion="Pequeño jardín de hierbas lunares."),

    "gh_07": TipoEdificio("gh_07", "Vivero de Árboles", "greenhouses",

                          "gh_07_tree_nursery_pixel.png",

                          costo=450, produce_oxigeno=18, produce_energia=-3,

                          mantenimiento=5, empleos=2, ancho_tiles=2, alto_tiles=2,

                          descripcion="Árboles para terraformación. 2x2"),



    # ── Edificios Varios (buildings_misc) ──

    "misc_01": TipoEdificio("misc_01", "Albergue Central", "buildings_misc",

                            "misc_01_living_quarters_dome_pixel.png",

                            costo=450, produce_energia=-4, mantenimiento=5,

                            ancho_tiles=2, alto_tiles=2,

                            descripcion="Albergue principal para 20 colonos. 2x2", alquiler=25),

    "misc_02": TipoEdificio("misc_02", "Planta de Agua", "buildings_misc",

                            "misc_planta_agua_blender.png",

                            produce_presion=5,

                            costo=500, produce_agua=20, produce_energia=-8,

                            mantenimiento=8, empleos=3, ancho_tiles=2, alto_tiles=2,

                            descripcion="Reciclaje y purificación de agua. 2x2"),

    "misc_03": TipoEdificio("misc_03", "Procesador Atmosférico", "buildings_misc",

                            "misc_03_atmosphere_processor_pixel.png",

                            produce_presion=15,

                            costo=700, produce_oxigeno=30, produce_energia=-10,

                            mantenimiento=10, empleos=4, ancho_tiles=2, alto_tiles=2,

                            descripcion="Genera oxígeno respirable. 2x2"),

    "misc_04": TipoEdificio("misc_04", "Torre de Comunicaciones", "buildings_misc",

                            "misc_torre_comunicaciones_blender.png",

                            costo=350, produce_energia=-3, mantenimiento=3, empleos=2,

                            descripcion="Enlace con la Tierra y otras colonias."),

    "misc_05": TipoEdificio("misc_05", "Base Ascensor Espacial", "buildings_misc",

                            "misc_05_space_elevator_base_pixel.png",

                            costo=2000, produce_energia=-15, mantenimiento=25, empleos=15,

                            ancho_tiles=3, alto_tiles=2,

                            descripcion="Conexión orbital directa. 3x2", alquiler=100),

    "misc_06": TipoEdificio("misc_06", "Centro de Reciclaje", "buildings_misc",

                            "misc_06_recycling_center_pixel.png",

                            costo=400, produce_agua=5, produce_energia=-4,

                            mantenimiento=5, empleos=2, ancho_tiles=2, alto_tiles=1,

                            descripcion="Recuperación de recursos. 2x1"),

    "misc_07": TipoEdificio("misc_07", "Academia Lunar", "buildings_misc",

                            "misc_academia_blender.png",

                            costo=800, produce_energia=-8, mantenimiento=12, empleos=10,

                            ancho_tiles=2, alto_tiles=2,

                            produce_felicidad=8,
                            descripcion="Educación e investigación. 2x2", alquiler=35),

    "misc_08": TipoEdificio("misc_08", "Parque Recreativo", "buildings_misc",

                            "misc_08_park_recreation_dome_pixel.png",

                            costo=300, produce_oxigeno=5, produce_energia=-2,

                            mantenimiento=3, ancho_tiles=2, alto_tiles=2,

                            produce_felicidad=18,
                            descripcion="Ocio y bienestar para colonos. 2x2"),

    "misc_09": TipoEdificio("misc_09", "Gestión de Residuos", "buildings_misc",

                            "misc_09_waste_management_pixel.png",

                            costo=350, produce_energia=-4, mantenimiento=5, empleos=2,

                            ancho_tiles=2, alto_tiles=1,

                            descripcion="Procesamiento de residuos. 2x1"),

    "misc_10": TipoEdificio("misc_10", "Estación de Bomberos", "buildings_misc",

                            "misc_10_fire_station_pixel.png",

                            costo=400, produce_energia=-3, mantenimiento=5, empleos=5,

                            produce_felicidad=5,
                            descripcion="Protección contra incendios."),

    "misc_11": TipoEdificio("misc_11", "Estación de Policía", "buildings_misc",

                            "misc_11_police_station_pixel.png",

                            costo=400, produce_energia=-3, mantenimiento=5, empleos=5,

                            produce_felicidad=5,
                            descripcion="Seguridad y orden en la colonia."),

    "misc_12": TipoEdificio("misc_12", "Plataforma Lanzamiento", "buildings_misc",

                            "misc_12_launch_pad_pixel.png",

                            costo=1500, produce_energia=-15, mantenimiento=20, empleos=10,

                            ancho_tiles=3, alto_tiles=2,

                            descripcion="Lanzamiento de cohetes. 3x2"),



    # ── Sitios Lunares (lunar_sites) ──

    "site_01": TipoEdificio("site_01", "Excavación Minera", "lunar_sites",

                            "site_01_mining_excavation_site_pixel.png",

                            costo=1200, produce_energia=-10, mantenimiento=15, empleos=12,

                            ancho_tiles=3, alto_tiles=2,

                            descripcion="Mina de recursos lunares. 3x2"),

    "site_02": TipoEdificio("site_02", "Campus Investigación", "lunar_sites",

                            "site_02_research_laboratory_campus_pixel.png",

                            costo=1500, produce_energia=-12, mantenimiento=18, empleos=18,

                            ancho_tiles=3, alto_tiles=2,

                            descripcion="Centro científico multidisciplinar. 3x2"),

    "site_03": TipoEdificio("site_03", "Resort Lunar", "lunar_sites",

                            "site_03_lunar_hotel_resort_pixel.png",

                            costo=2000, produce_energia=-8, produce_agua=-5,

                            mantenimiento=15, empleos=15, ancho_tiles=3, alto_tiles=2,

                            produce_felicidad=20,
                            descripcion="Turismo espacial de lujo. 3x2", alquiler=120),

    "site_04": TipoEdificio("site_04", "Complejo Lanzamiento", "lunar_sites",

                            "site_04_spaceport_launch_complex_pixel.png",

                            costo=3000, produce_energia=-20, mantenimiento=30, empleos=25,

                            ancho_tiles=4, alto_tiles=4,

                            descripcion="Puerto espacial completo. 4x4", alquiler=150),

    "site_05": TipoEdificio("site_05", "Distrito Almacenes", "lunar_sites",

                            "site_05_warehouse_storage_district_pixel.png",

                            costo=800, produce_energia=-4, mantenimiento=8, empleos=8,

                            ancho_tiles=3, alto_tiles=2,

                            descripcion="Zona logística de almacenamiento. 3x2", alquiler=60),

    "site_06": TipoEdificio("site_06", "Zona Agrícola", "lunar_sites",

                            "site_06_greenhouse_agriculture_zone_pixel.png",

                            costo=1200, produce_oxigeno=40, produce_agua=20, produce_energia=-6,

                            mantenimiento=10, empleos=10, ancho_tiles=4, alto_tiles=4,

                            descripcion="Agricultura a gran escala. 4x4"),

    "site_07": TipoEdificio("site_07", "Granja Solar", "lunar_sites",

                            "site_07_solar_energy_farm_pixel.png",

                            costo=1500, produce_energia=80, mantenimiento=8, empleos=6,

                            ancho_tiles=4, alto_tiles=4,

                            descripcion="Parque solar masivo. 4x4"),

    "site_08": TipoEdificio("site_08", "Complejo de Albergues", "lunar_sites",

                            "site_08_residential_colony_sector_pixel.png",

                            costo=800, produce_energia=-6, produce_oxigeno=-3, produce_agua=-3,

                            mantenimiento=8, empleos=5, ancho_tiles=4, alto_tiles=4,

                            descripcion="Complejo de albergues para 50 colonos. 4x4", alquiler=35),

    "site_09": TipoEdificio("site_09", "Plaza de Entretenimiento", "lunar_sites",

                            "site_09_entertainment_plaza_pixel.png",

                            costo=600, produce_energia=-5, mantenimiento=6, empleos=8,

                            ancho_tiles=3, alto_tiles=2,

                            produce_felicidad=22,
                            descripcion="Cines, teatros y ocio lunar. 3x2", alquiler=45),

    "site_10": TipoEdificio("site_10", "Complejo Médico", "lunar_sites",

                            "site_10_medical_center_complex_pixel.png",

                            costo=1800, produce_energia=-10, produce_oxigeno=-5,

                            mantenimiento=20, empleos=20, ancho_tiles=3, alto_tiles=2,

                            produce_felicidad=15,
                            descripcion="Hospital y centro de salud. 3x2", alquiler=50),

    "site_11": TipoEdificio("site_11", "Central Nuclear", "lunar_sites",

                            "site_11_nuclear_power_plant_pixel.png",

                            costo=2500, produce_energia=150, mantenimiento=30, empleos=12,

                            ancho_tiles=4, alto_tiles=4,

                            descripcion="Generación nuclear masiva. 4x4"),

    "site_12": TipoEdificio("site_12", "Hub de Comunicaciones", "lunar_sites",

                            "site_12_communications_hub_pixel.png",

                            costo=900, produce_energia=-6, mantenimiento=8, empleos=8,

                            ancho_tiles=3, alto_tiles=2,

                            descripcion="Centro de datos y comunicaciones. 3x2", alquiler=40),



    # ── Oficios Extraños (oficios_raros) ── Emprendedores lunares ──

    "oficio_01": TipoEdificio("oficio_01", "Bar Lunar Gravity", "businesses",

                              "biz_restaurante_lunar_blender.png",

                              costo=300, produce_energia=-3, produce_agua=-1,

                              mantenimiento=5, empleos=4,

                              descripcion="Copas en baja gravedad. ¡Los cocktails flotan!", alquiler=18),

    "oficio_02": TipoEdificio("oficio_02", "Tatuajes Low-G", "businesses",

                              "biz_tienda_lunar_blender.png",

                              costo=200, produce_energia=-2,

                              mantenimiento=3, empleos=2,

                              descripcion="Tinta que flota. Diseños imposibles en la Tierra.", alquiler=12),

    "oficio_03": TipoEdificio("oficio_03", "Granja de Insectos", "greenhouses",

                              "gh_03_vertical_farm_pixel.png",

                              costo=250, produce_oxigeno=3, produce_energia=-2,

                              mantenimiento=3, empleos=3,

                              descripcion="Proteína sostenible: grillos y larvas lunares.", alquiler=10),

    "oficio_04": TipoEdificio("oficio_04", "Gimnasio 1/6G", "buildings_misc",

                              "misc_08_park_recreation_dome_pixel.png",

                              costo=350, produce_energia=-4, produce_oxigeno=-2,

                              mantenimiento=6, empleos=3, ancho_tiles=2, alto_tiles=1,

                              produce_felicidad=8,
                              descripcion="Entrena con 1/6 de tu peso. ¡Records imposibles! 2x1", alquiler=22),

    "oficio_05": TipoEdificio("oficio_05", "Estudio Holocine", "businesses",

                              "biz_laboratorio_blender.png",

                              costo=500, produce_energia=-6,

                              mantenimiento=8, empleos=5, ancho_tiles=2, alto_tiles=1,

                              produce_felicidad=12,
                              descripcion="Cine holográfico inmersivo. 2x1", alquiler=35),

    "oficio_06": TipoEdificio("oficio_06", "Taller de Trajes", "businesses",

                              "biz_oficina_minera_blender.png",

                              costo=280, produce_energia=-3,

                              mantenimiento=4, empleos=3,

                              descripcion="Reparación y customización de trajes espaciales.", alquiler=15),

    "oficio_07": TipoEdificio("oficio_07", "Lab. Cristales Lunares", "greenhouses",

                              "gh_04_hydroponics_lab_pixel.png",

                              costo=450, produce_energia=-5, produce_oxigeno=2,

                              mantenimiento=7, empleos=4, ancho_tiles=2, alto_tiles=1,

                              descripcion="Cristales que solo crecen en baja gravedad. 2x1", alquiler=28),

    "oficio_08": TipoEdificio("oficio_08", "Spa Gravedad Cero", "lunar_sites",

                              "site_03_lunar_hotel_resort_pixel.png",

                              costo=600, produce_energia=-7, produce_agua=-3,

                              mantenimiento=10, empleos=6, ancho_tiles=2, alto_tiles=2,

                              produce_felicidad=14,
                              descripcion="Masajes flotantes y baños de regolito. 2x2", alquiler=45),

    "oficio_09": TipoEdificio("oficio_09", "Destilería Lunar", "businesses",

                              "biz_fabrica_blender.png",

                              costo=400, produce_energia=-5, produce_agua=-2,

                              mantenimiento=6, empleos=3,

                              descripcion="Whisky añejado en cráteres. Sabor... único.", alquiler=20),

    "oficio_10": TipoEdificio("oficio_10", "Museo de Artefactos", "decorations",

                              "dec_05_monument_statue_pixel.png",

                              costo=350, produce_energia=-2,

                              mantenimiento=4, empleos=2, ancho_tiles=2, alto_tiles=1,

                              descripcion="Restos de sondas y artefactos de la era espacial. 2x1", alquiler=15),

    "oficio_11": TipoEdificio("oficio_11", "Observatorio Privado", "buildings_misc",

                              "misc_torre_comunicaciones_blender.png",

                              costo=550, produce_energia=-4,

                              mantenimiento=6, empleos=3,

                              produce_felicidad=6,
                              descripcion="Turismo astronómico sin atmósfera. Visión perfecta.", alquiler=30),

    "oficio_12": TipoEdificio("oficio_12", "Fábrica de Oxígeno Artesanal", "buildings_misc",

                              "misc_03_atmosphere_processor_pixel.png",

                              costo=380, produce_oxigeno=8, produce_energia=-6,

                              mantenimiento=5, empleos=2, ancho_tiles=2, alto_tiles=1,

                              descripcion="O2 de luxe con aromas lunares. 2x1", alquiler=18),



    # ── Campus Universitarios (universities) ── Laboratorios de investigación en la Luna ──

    "univ_01": TipoEdificio("univ_01", "MIT Lunar Laboratory", "universities",

                            "biz_laboratorio_blender.png",

                            costo=2000, produce_energia=-12, produce_oxigeno=-4,

                            mantenimiento=25, empleos=20, ancho_tiles=3, alto_tiles=2,

                            descripcion="Ingeniería y tecnología lunar del MIT. 3x2", alquiler=90),

    "univ_02": TipoEdificio("univ_02", "Stanford Zero-G Center", "universities",

                            "site_02_research_laboratory_campus_pixel.png",

                            costo=1800, produce_energia=-10, produce_oxigeno=-3, produce_agua=-2,

                            mantenimiento=22, empleos=18, ancho_tiles=3, alto_tiles=2,

                            descripcion="Investigación en gravedad cero de Stanford. 3x2", alquiler=85),

    "univ_03": TipoEdificio("univ_03", "Oxford Astrobiology Inst.", "universities",

                            "biz_laboratorio_blender.png",

                            costo=1600, produce_energia=-8, produce_oxigeno=-2,

                            mantenimiento=18, empleos=15, ancho_tiles=2, alto_tiles=2,

                            descripcion="Instituto de astrobiología de Oxford. 2x2", alquiler=75),

    "univ_04": TipoEdificio("univ_04", "Tokyo Space Science Inst.", "universities",

                            "site_02_research_laboratory_campus_pixel.png",

                            costo=1700, produce_energia=-9, produce_oxigeno=-3,

                            mantenimiento=20, empleos=16, ancho_tiles=2, alto_tiles=2,

                            descripcion="Instituto de ciencia espacial de Tokio. 2x2", alquiler=80),

    "univ_05": TipoEdificio("univ_05", "Caltech Lunar Observatory", "universities",

                            "misc_torre_comunicaciones_blender.png",

                            costo=2200, produce_energia=-14, produce_oxigeno=-3,

                            mantenimiento=28, empleos=22, ancho_tiles=2, alto_tiles=2,

                            descripcion="Observatorio astronómico de Caltech. 2x2", alquiler=95),

    "univ_06": TipoEdificio("univ_06", "ETH Zurich Materials Lab", "universities",

                            "biz_fabrica_blender.png",

                            costo=1900, produce_energia=-15, produce_oxigeno=-4, produce_agua=-2,

                            mantenimiento=24, empleos=18, ancho_tiles=3, alto_tiles=2,

                            descripcion="Laboratorio de ciencia de materiales ETH. 3x2", alquiler=88),

    "univ_07": TipoEdificio("univ_07", "Cambridge Lunar Biology", "universities",

                            "gh_05_aquaponics_bay_pixel.png",

                            costo=1500, produce_oxigeno=10, produce_energia=-8,

                            mantenimiento=16, empleos=14, ancho_tiles=2, alto_tiles=2,

                            descripcion="Laboratorio de biología lunar de Cambridge. 2x2", alquiler=70),

    "univ_08": TipoEdificio("univ_08", "Tsinghua Space Engineering", "universities",

                            "site_01_mining_excavation_site_pixel.png",

                            costo=2100, produce_energia=-13, produce_oxigeno=-4,

                            mantenimiento=26, empleos=20, ancho_tiles=3, alto_tiles=2,

                            descripcion="Centro de ingeniería espacial Tsinghua. 3x2", alquiler=92),

    "univ_09": TipoEdificio("univ_09", "Sorbonne Lunar Humanities", "universities",

                            "misc_academia_blender.png",

                            costo=1200, produce_energia=-6, produce_oxigeno=-2,

                            mantenimiento=14, empleos=12, ancho_tiles=2, alto_tiles=2,

                            descripcion="Facultad de humanidades y ciencias sociales. 2x2", alquiler=60),

    "univ_10": TipoEdificio("univ_10", "MITEX Lunar Campus", "universities",

                            "site_12_communications_hub_pixel.png",

                            costo=2500, produce_energia=-16, produce_oxigeno=-5, produce_agua=-3,

                            mantenimiento=30, empleos=25, ancho_tiles=3, alto_tiles=2,

                            descripcion="Campus conjunto MIT-Exeter de investigación. 3x2", alquiler=110),



    # ── Gobierno / Administración (government) ──

    "gov_01": TipoEdificio("gov_01", "Oficina del Comisionado", "government",

                           "gov_01_commissioner_office_pixel.png",

                           costo=3000, produce_energia=-15, produce_oxigeno=-5,

                           mantenimiento=35, empleos=25, ancho_tiles=3, alto_tiles=2,

                           descripcion="Centro de mando con comunicaciones Tierra-Luna. 3x2", alquiler=60),

    "gov_02": TipoEdificio("gov_02", "Centro de Operaciones Lunares", "government",

                           "gov_02_lunar_operations_center_pixel.png",

                           costo=1800, produce_energia=-10, produce_oxigeno=-3,

                           mantenimiento=20, empleos=15, ancho_tiles=2, alto_tiles=2,

                           descripcion="Gestión y administración de la colonia. 2x2", alquiler=50),



    # ── Alojamiento (housing) ──

    "hou_01": TipoEdificio("hou_01", "Albergue Básico", "housing",

                           "hou_albergue_basico_blender.png",

                           costo=300, produce_energia=-2,

                           mantenimiento=3, empleos=0, ancho_tiles=1, alto_tiles=1,

                           descripcion="Albergue económico para 4-8 colonos. 1x1", alquiler=15),

    "hou_02": TipoEdificio("hou_02", "Albergue Comunitario", "housing",

                           "hou_02_residential_complex_pixel.png",

                           costo=500, produce_energia=-4,

                           mantenimiento=5, empleos=1, ancho_tiles=2, alto_tiles=2,

                           descripcion="Albergue compartido en túneles de lava. 2x2", alquiler=26),

    "hou_03": TipoEdificio("hou_03", "Hotel Cúpula de Lujo", "businesses",

                           "hou_03_luxury_dome_pixel.png",

                           costo=2000, produce_energia=-12, produce_oxigeno=-3, produce_agua=-2,

                           mantenimiento=18, empleos=8, ancho_tiles=2, alto_tiles=2,

                           produce_felicidad=15,
                           descripcion="Hotel premium con vistas al espacio. 2x2", alquiler=100),

    "hou_04": TipoEdificio("hou_04", "Albergue Subterráneo", "housing",

                           "hou_04_underground_district_pixel.png",

                           costo=700, produce_energia=-6,

                           mantenimiento=7, empleos=2, ancho_tiles=3, alto_tiles=2,

                           descripcion="Albergue excavado bajo la superficie. 3x2", alquiler=30),



    # ── Recursos Vitales (life_support) ──

    "life_01": TipoEdificio("life_01", "Extractor de Agua del Regolito", "life_support",

                            "life_01_water_extractor_pixel.png",

                            produce_presion=8,

                            costo=800, produce_agua=25, produce_energia=-10,

                            mantenimiento=10, empleos=4, ancho_tiles=2, alto_tiles=2,

                            descripcion="Extrae hielo de cráteres polares. Agua+25. 2x2"),

    "life_02": TipoEdificio("life_02", "Planta de Electrólisis", "life_support",

                            "life_02_electrolysis_plant_pixel.png",

                            produce_presion=12,

                            costo=600, produce_agua=10, produce_oxigeno=15, produce_energia=-12,

                            mantenimiento=8, empleos=3, ancho_tiles=2, alto_tiles=1,

                            descripcion="Separa H₂O en oxígeno y combustible. 2x1"),

    "life_03": TipoEdificio("life_03", "Cisterna de Regolito", "life_support",

                            "life_03_regolith_cistern_pixel.png",

                            costo=300, produce_energia=-2,

                            mantenimiento=3, empleos=1, ancho_tiles=2, alto_tiles=1,

                            descripcion="Almacenamiento de materiales excavados. 2x1", alquiler=15),



    # ── Industria / Producción (industry) ──

    "ind_01": TipoEdificio("ind_01", "Fundición de Regolito", "industry",

                           "ind_01_regolith_smelter_pixel.png",

                           costo=1400, produce_energia=-18, produce_oxigeno=-5,

                           mantenimiento=20, empleos=12, ancho_tiles=2, alto_tiles=2,

                           descripcion="Procesa suelo lunar en materiales. 2x2", alquiler=80),

    "ind_02": TipoEdificio("ind_02", "Fábrica de Impresión 3D", "industry",

                           "ind_02_3d_printing_factory_pixel.png",

                           costo=1200, produce_energia=-15, produce_oxigeno=-3,

                           mantenimiento=18, empleos=10, ancho_tiles=2, alto_tiles=2,

                           descripcion="Construye estructuras con polvo lunar. 2x2", alquiler=65),

    "ind_03": TipoEdificio("ind_03", "Laboratorio de Helio-3", "industry",

                           "ind_03_helium_3_lab_pixel.png",

                           costo=2000, produce_energia=-10, produce_oxigeno=-4,

                           mantenimiento=25, empleos=15, ancho_tiles=2, alto_tiles=2,

                           descripcion="Procesa y refina helio-3 para exportación. 2x2", alquiler=90),

    "ind_04": TipoEdificio("ind_04", "Puerto de Exportación", "industry",

                           "ind_04_export_harbor_pixel.png",

                           costo=2500, produce_energia=-20, produce_oxigeno=-6,

                           mantenimiento=30, empleos=18, ancho_tiles=3, alto_tiles=2,

                           descripcion="Rampa de lanzamiento para exportar recursos. 3x2", alquiler=120),

    "ind_05": TipoEdificio("ind_05", "EcoCentro Progreso", "industry",

                           "misc_06_recycling_center_pixel.png",

                           costo=1200, produce_energia=-20, produce_oxigeno=-4,

                           mantenimiento=18, empleos=10, ancho_tiles=3, alto_tiles=2,

                           produce_felicidad=8,

                           descripcion="Planta de reciclaje total: residuos en compost, metales refinados y fibras. 3x2", alquiler=45),



    # ── Transporte (transport) ──

    "tra_01": TipoEdificio("tra_01", "Garaje de Rovers", "transport",

                           "tra_01_rover_garage_pixel.png",

                           costo=500, produce_energia=-5,

                           mantenimiento=6, empleos=3, ancho_tiles=2, alto_tiles=2,

                           descripcion="Vehículos todoterreno para trabajo exterior. 2x2", alquiler=25),

    "tra_02": TipoEdificio("tra_02", "Tubo de Vacío", "transport",

                           "tra_02_vacuum_tube_station_pixel.png",

                           costo=350, produce_energia=-3,

                           mantenimiento=4, empleos=1, ancho_tiles=3, alto_tiles=1,

                           descripcion="Transporte ultrarrápido entre zonas. 3x1"),



    # ── Servicios / Civiles (civic) ──

    "civ_01": TipoEdificio("civ_01", "Centro de Entrenamiento EVA", "civic",

                           "civ_01_eva_training_center_pixel.png",

                           costo=700, produce_energia=-6, produce_oxigeno=-2,

                           mantenimiento=8, empleos=5, ancho_tiles=2, alto_tiles=2,

                           produce_felicidad=5,
                           descripcion="Entrenamiento para trabajo extravehicular. 2x2", alquiler=30),

    "civ_02": TipoEdificio("civ_02", "Cementerio de Cráteres", "civic",

                           "civ_02_crater_memorial_pixel.png",

                           costo=100, mantenimiento=1, empleos=0,

                           descripcion="Último descanso para colonos caídos en misión."),



    # ── Gestión de Riesgos (risk_management) ──

    "rsk_01": TipoEdificio("rsk_01", "Brigada de Presurización", "risk_management",

                           "rsk_01_pressurization_brigade_pixel.png",

                           produce_presion=15,

                           costo=500, produce_energia=-4,

                           mantenimiento=6, empleos=4,

                           descripcion="Atiende emergencias de pérdida de aire."),

    "rsk_02": TipoEdificio("rsk_02", "Control de Radiación Solar", "risk_management",

                           "rsk_02_solar_radiation_control_pixel.png",

                           produce_presion=10,

                           costo=600, produce_energia=-5,

                           mantenimiento=8, empleos=4, ancho_tiles=2, alto_tiles=1,

                           descripcion="Activa escudos durante tormentas solares. 2x1"),

    "rsk_03": TipoEdificio("rsk_03", "Centro de Evacuación Subterránea", "risk_management",

                           "rsk_03_evacuation_center_pixel.png",

                           produce_presion=20,

                           costo=800, produce_energia=-6,

                           mantenimiento=10, empleos=5, ancho_tiles=2, alto_tiles=2,

                           produce_felicidad=10,
                           descripcion="Refugio ante eventos extremos. 2x2"),



    # ── Energía (nuevos) ──

    "sol_10": TipoEdificio("sol_10", "Planta de Fusión", "solar_energy",

                           "sol_10_fusion_power_plant_pixel.png",

                           costo=4000, produce_energia=300,

                           mantenimiento=50, empleos=15, ancho_tiles=3, alto_tiles=2,

                           descripcion="Fusión nuclear avanzada para megacolonias. 3x2"),

}



# ─── Clasificación de propiedad (zonificación) ────────────────────────────

# Edificios públicos: colocación directa (carreteras, energía, servicios)

# Edificios privados: necesitan permiso del comisionado (negocios, viviendas, etc.)

EDIFICIOS_PRIVADOS = {

    # Negocios

    "biz_01", "biz_02", "biz_03", "biz_04", "biz_05", "biz_06", "biz_07", "biz_08",

    "biz_10", "biz_11", "biz_12",

    # Vehículos privados

    "veh_01", "veh_02", "veh_03", "veh_04", "veh_05", "veh_06", "veh_07", "veh_08", "veh_09", "veh_10",

    # Invernaderos

    "gh_01", "gh_02", "gh_03", "gh_04", "gh_05", "gh_06", "gh_07",

    # Edificios privados

    "misc_01", "misc_05", "misc_07",

    # Sitios privados

    "site_01", "site_02", "site_03", "site_04", "site_05", "site_06",

    "site_08", "site_09", "site_10", "site_12",

    # Oficios extraños

    "oficio_01", "oficio_02", "oficio_03", "oficio_04", "oficio_05", "oficio_06",

    "oficio_07", "oficio_08", "oficio_09", "oficio_10", "oficio_11", "oficio_12",

    # Campus Universitarios

    "univ_01", "univ_02", "univ_03", "univ_04", "univ_05", "univ_06", "univ_07", "univ_08", "univ_09", "univ_10",

    # Gobierno

    "gov_01", "gov_02",

    # Alojamiento (albergues)

    "hou_01", "hou_02", "hou_03", "hou_04",

    # Recursos Vitales

    "life_01", "life_02", "life_03",

    # Industria

    "ind_01", "ind_02", "ind_03", "ind_04", "ind_05",

    # Transporte

    "tra_01", "tra_02",

    # Servicios Civiles

    "civ_01", "civ_02",

    # Gestión de Riesgos

    "rsk_01", "rsk_02", "rsk_03",

}

# El resto (roads, decorations, solar_energy, servicios públicos) son públicos



def es_edificio_privado(edificio_id: str) -> bool:

    """Determina si un edificio es privado (necesita permiso)."""

    return edificio_id in EDIFICIOS_PRIVADOS



@dataclass

class TipoZona:

    """Define un rubro de zonificacion para recalificacion de terreno."""

    id: str

    nombre: str

    color: Tuple[int, int, int]

    icono: str

    categorias_compatibles: List[str] = field(default_factory=list)

    prima_min: int = 50

    prima_max: int = 200

    alquiler_min: int = 10

    alquiler_max: int = 80



CATALOGO_ZONAS: Dict[str, TipoZona] = {

    # ── 4 ZONAS ───────────────────────────────────────────────────

    "alojamiento": TipoZona("alojamiento", "Alojamiento", (70, 130, 180), "🏠",

                            categorias_compatibles=["hou_01", "hou_02", "hou_04",

                                                    "misc_01", "site_08"],

                            prima_min=60, prima_max=250, alquiler_min=8, alquiler_max=50),

    "comercial": TipoZona("comercial", "Comercial", (255, 180, 50), "🏢",

                          categorias_compatibles=[

        # Negocios y servicios

        "biz_02", "biz_03", "biz_04", "biz_06", "biz_07", "biz_10", "biz_11",
        "hou_03",

        # Sitios comerciales

        "site_03", "site_09", "site_10",

        # Edificios varios

        "misc_04", "misc_05", "misc_07", "misc_08", "misc_10", "misc_11", "misc_12",

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

        "ind_01", "ind_02", "ind_03", "ind_04", "ind_05",

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

}


def edificios_para_zona(zona_id: str) -> List[str]:

    """Devuelve los IDs de edificios privados compatibles con una zona."""

    zona = CATALOGO_ZONAS.get(zona_id)

    if not zona:

        return []

    # Las categorias_compatibles ahora contienen IDs especificos de edificios

    return [aid for aid in zona.categorias_compatibles if aid in EDIFICIOS_PRIVADOS]



class Recursos:

    """Gestiona los recursos de la colonia."""



    def __init__(self):

        self.creditos = Config.CREDITOS_INICIALES

        self.energia = Config.ENERGIA_INICIAL

        self.oxigeno = Config.OXIGENO_INICIAL

        self.agua = Config.AGUA_INICIAL

        self.presion = Config.PRESION_INICIAL

        self.energia_total = Config.ENERGIA_INICIAL

        self.oxigeno_total = Config.OXIGENO_INICIAL

        self.agua_total = Config.AGUA_INICIAL

        self.presion_total = Config.PRESION_INICIAL

        self.poblacion = 10

        self.turno = 0
        self.felicidad = Config.FELICIDAD_INICIAL
        self.bono_produccion = 1.0  # 1.0 = neutral, 1.25 = contentos, 0.75 = enojados



    def actualizar_balance(self, edificios: List['EdificioColocado'], es_de_noche: bool = False) -> None:

        """Recalcula producción y consumo basado en los edificios colocados."""

        self.energia_total = Config.ENERGIA_INICIAL

        self.oxigeno_total = Config.OXIGENO_INICIAL

        self.agua_total = Config.AGUA_INICIAL

        self.presion_total = Config.PRESION_INICIAL

        for edificio in edificios:

            if edificio.activo:

                energia_prod = edificio.tipo.produce_energia
                if es_de_noche and edificio.tipo.categoria == "solar_energy" and energia_prod > 0:
                    energia_prod = 0
                self.energia_total += energia_prod

                self.oxigeno_total += edificio.tipo.produce_oxigeno

                self.agua_total += edificio.tipo.produce_agua

                self.presion_total += edificio.tipo.produce_presion

        # Aplicar bono/penalidad por felicidad

        self.energia = int(self.energia_total * self.bono_produccion)

        self.oxigeno = int(self.oxigeno_total * self.bono_produccion)

        self.agua = int(self.agua_total * self.bono_produccion)
        self.presion = int(self.presion_total * self.bono_produccion)
        # Aplicar bonos del arbol de tecnologia
        if hasattr(self, '_juego') and self._juego:
            tech = self._juego.tecnologia
            b = tech.bonos_activos
            if b.get('energia_factor', 0) > 0:
                self.energia = int(self.energia * (1 + b['energia_factor']))
            if b.get('oxigeno_factor', 0) > 0:
                self.oxigeno = int(self.oxigeno * (1 + b['oxigeno_factor']))
            if b.get('agua_factor', 0) > 0:
                self.agua = int(self.agua * (1 + b['agua_factor']))
            if b.get('felicidad_factor', 0) > 0:
                self.felicidad = min(100, int(self.felicidad * (1 + b['felicidad_factor'])))




    def gastar(self, creditos: int = 0) -> bool:

        """Intenta gastar créditos. Retorna True si hay suficientes."""

        if self.creditos >= creditos:

            self.creditos -= creditos

            return True

        return False



    def ingresar(self, creditos: int) -> None:

        """Añade créditos."""

        self.creditos += creditos


# --- Panel de Flujo de Recursos ---

class PanelFlujoRecursos:
    def __init__(self, renderizador):
        self.renderizador = renderizador
        self.visible = False
        self.frames = 0
        self.recursos_nombres = ["energia", "oxigeno", "agua", "presion", "felicidad"]
        self.iconos = {
            "energia": chr(0x26A1), "oxigeno": chr(0x1FEC1),
            "agua": chr(0x1F4A7), "presion": chr(0x1F4A8),
            "felicidad": chr(0x1F60A),
        }
        self.datos = {}

    def actualizar(self, mapa) -> None:
        self.frames += 1
        if self.frames % 30 != 0:
            return
        self.datos = {
            z: {r: 0 for r in self.recursos_nombres}
            for z in list(CATALOGO_ZONAS.keys()) + ["sin_zona"]
        }
        for edif in mapa.edificios:
            if not edif.activo:
                continue
            zona_str = mapa.zonas[edif.y][edif.x] if (
                0 <= edif.y < len(mapa.zonas)
                and 0 <= edif.x < len(mapa.zonas[0])
            ) else None
            z_id = zona_str if zona_str in self.datos else "sin_zona"
            self.datos[z_id]["energia"] += edif.tipo.produce_energia
            self.datos[z_id]["oxigeno"] += edif.tipo.produce_oxigeno
            self.datos[z_id]["agua"] += edif.tipo.produce_agua
            self.datos[z_id]["presion"] += edif.tipo.produce_presion
            self.datos[z_id]["felicidad"] += edif.tipo.produce_felicidad

    def renderizar(self, pantalla, x, y, ancho, alto):
        if not self.visible:
            return
        pulse = (math.sin(self.frames * 0.15) + 1) / 2
        rect_p = pygame.Rect(x, y, ancho, alto)
        pygame.draw.rect(pantalla, (*Config.COLOR_PANEL, 245), rect_p, border_radius=10)
        pygame.draw.rect(pantalla, Config.COLOR_PANEL_BORDE, rect_p, 2, border_radius=10)
        r = self.renderizador
        titulo = chr(0x1F4CA) + " Flujo de Recursos"
        txt_tit = r.fuente_mediana.render(titulo, True, Config.COLOR_TEXTO_AMARILLO)
        pantalla.blit(txt_tit, (x + 15, y + 12))
        y_off = y + 45
        col_w = 42
        xs = x + 80
        for i, res in enumerate(self.recursos_nombres):
            txt_col = r.fuente_pequenia.render(self.iconos[res], True, Config.COLOR_TEXTO)
            pantalla.blit(txt_col, (xs + i * col_w, y_off))
        y_off += 25
        pygame.draw.line(pantalla, Config.COLOR_PANEL_BORDE, (x + 10, y_off), (x + ancho - 10, y_off))
        y_off += 8
        for z_id in list(CATALOGO_ZONAS.keys()) + ["sin_zona"]:
            if not self.datos:
                break
            nombre_zona = CATALOGO_ZONAS[z_id].nombre.upper() if z_id in CATALOGO_ZONAS else "SIN ZONA"
            txt_z = r.fuente_pequenia.render(nombre_zona[:9], True, Config.COLOR_TEXTO)
            pantalla.blit(txt_z, (x + 12, y_off))
            for i, res in enumerate(self.recursos_nombres):
                val = self.datos.get(z_id, {}).get(res, 0)
                color = Config.COLOR_TEXTO
                if val > 0:
                    color = Config.COLOR_TEXTO_VERDE
                elif val < 0:
                    color = (min(255, 180 + int(75 * pulse)), 50, 50)
                txt_val = r.fuente_pequenia.render(f"{val:+d}" if val != 0 else "0", True, color)
                pantalla.blit(txt_val, (xs + i * col_w, y_off))
                if val <= -10:
                    warn = r.fuente_pequenia.render(chr(0x26A0) + chr(0xFE0F), True, (255, 200, 0))
                    pantalla.blit(warn, (xs + i * col_w - 18, y_off - 2))
            y_off += 22
        txt_info = r.fuente_pequenia.render("R: Ocultar panel", True, Config.COLOR_TEXTO)
        pantalla.blit(txt_info, (x + 15, y_off + 10))




# --- Mercado Inter-Colonial Lunar ---

class MercadoInterColonial:
    """Mercado de import/export entre colonias con precios fluctuantes.

    Precios independientes del MercadoDinamico local. Fluctuan cada turno
    con random walks y eventos globales. El jugador puede comprar/vender
    recursos para equilibrar su economia.

    Tecla 'M' para mostrar/ocultar el panel.
    """

    def __init__(self):
        self.precios = {"energia": 4.0, "oxigeno": 6.0, "agua": 5.0, "presion": 3.0}
        self.base = dict(self.precios)
        self.visible = False
        self.turno = 0
        self.evento_activo = ""
        self.evento_duracion = 0
        self.historial = {r: [] for r in self.precios}
        # Limites: evita precios absurdos
        self.min_precio = {r: b * 0.2 for r, b in self.base.items()}
        self.max_precio = {r: b * 5.0 for r, b in self.base.items()}

    def actualizar(self, turno: int):
        """Actualiza precios cada turno con random walk y eventos."""
        self.turno = turno
        # Random walk: cada recurso fluctua +-15%
        for r in self.precios:
            cambio = random.uniform(-0.15, 0.15) * self.base[r]
            self.precios[r] += cambio
            # Reversion a la media (10% hacia el precio base)
            self.precios[r] += (self.base[r] - self.precios[r]) * 0.05

        # Evento activo?
        if self.evento_duracion > 0:
            self.evento_duracion -= 1
            if self.evento_duracion == 0:
                self.evento_activo = ""

        # Nuevo evento? (15% probabilidad, solo si no hay evento activo)
        if not self.evento_activo and random.random() < 0.15:
            self._generar_evento()

        # Clampear precios
        for r in self.precios:
            self.precios[r] = round(
                max(self.min_precio[r], min(self.max_precio[r], self.precios[r])), 1
            )
            self.historial[r].append(self.precios[r])
            if len(self.historial[r]) > 20:
                self.historial[r] = self.historial[r][-20:]

    def _generar_evento(self):
        """Genera un evento global que afecta los precios."""
        eventos = [
            ("Demanda terrestre de energia", "energia", 1.5, 3),
            ("Crisis de oxigeno en Marte", "oxigeno", 1.8, 4),
            ("Descubrimiento de acuifero lunar", "agua", 0.4, 5),
            ("Embargo comercial intercolonial", "presion", 1.6, 3),
            ("Auge del turismo espacial", "oxigeno", 1.4, 2),
            ("Sobrestock de paneles solares", "energia", 0.5, 4),
            ("Colapso de colonia vecina", "agua", 2.0, 3),
            ("Nueva ruta comercial abierta", "presion", 0.6, 5),
        ]
        nombre, recurso, factor, duracion = random.choice(eventos)
        self.precios[recurso] *= factor
        self.evento_activo = f"{nombre} ({recurso} x{factor:.1f})"
        self.evento_duracion = duracion

    def comprar(self, recurso: str, cantidad: int, recursos) -> bool:
        """Compra recursos del mercado intercolonial. Retorna True si exitoso."""
        if recurso not in self.precios:
            return False
        coste = int(cantidad * self.precios[recurso])
        if recursos.creditos >= coste:
            recursos.creditos -= coste
            if recurso == "energia":
                recursos.energia_total += cantidad
            elif recurso == "oxigeno":
                recursos.oxigeno_total += cantidad
            elif recurso == "agua":
                recursos.agua_total += cantidad
            elif recurso == "presion":
                recursos.presion_total += cantidad
            return True
        return False

    def vender(self, recurso: str, cantidad: int, recursos) -> bool:
        """Vende recursos al mercado intercolonial. Retorna True si exitoso."""
        if recurso not in self.precios:
            return False
        disponible = getattr(recursos, f"{recurso}_total", 0)
        if disponible >= cantidad and cantidad > 0:
            ingreso = int(cantidad * self.precios[recurso] * 0.8)
            recursos.creditos += ingreso
            if recurso == "energia":
                recursos.energia_total -= cantidad
            elif recurso == "oxigeno":
                recursos.oxigeno_total -= cantidad
            elif recurso == "agua":
                recursos.agua_total -= cantidad
            elif recurso == "presion":
                recursos.presion_total -= cantidad
            recursos.actualizar_balance([])
            return True
        return False

    def tendencia(self, recurso: str) -> str:
        """Flecha de tendencia de precios."""
        h = self.historial.get(recurso, [])
        if len(h) < 3:
            return chr(0x27A1) + chr(0xFE0F)  # ->
        if h[-1] > h[-3] * 1.02:
            return chr(0x2B06) + chr(0xFE0F)  # up
        if h[-1] < h[-3] * 0.98:
            return chr(0x2B07) + chr(0xFE0F)  # down
        return chr(0x27A1) + chr(0xFE0F)  # ->

    def linea_indicador(self) -> str:
        """Linea compacta para el panel."""
        iconos = {"energia": chr(0x26A1), "oxigeno": chr(0x1FEC1),
                   "agua": chr(0x1F4A7), "presion": chr(0x1F4A8)}
        partes = ["Mercado Intercolonial:"]
        for r in ["energia", "oxigeno", "agua", "presion"]:
            partes.append(f"{iconos[r]}{self.precios[r]:.0f}{self.tendencia(r)}")
        return " ".join(partes)

    def renderizar(self, pantalla, renderizador, x: int, y: int,
                   mouse_pos=None, mouse_click=False):
        """Renderiza el panel de mercado intercolonial con botones comprar/vender.

        Retorna (accion, recurso, cantidad) si se clickeo un boton,
        o None si no hubo click.
        """
        if not self.visible:
            return None
        ancho, alto = 340, 300
        rect_p = pygame.Rect(x, y, ancho, alto)
        pygame.draw.rect(pantalla, (*Config.COLOR_PANEL, 245), rect_p, border_radius=10)
        pygame.draw.rect(pantalla, Config.COLOR_PANEL_BORDE, rect_p, 2, border_radius=10)
        r = renderizador
        titulo = chr(0x1F30D) + " Mercado Inter-Colonial"
        txt_tit = r.fuente_mediana.render(titulo, True, Config.COLOR_TEXTO_AMARILLO)
        pantalla.blit(txt_tit, (x + 15, y + 12))
        y_off = y + 45
        iconos = {"energia": chr(0x26A1), "oxigeno": chr(0x1FEC1),
                   "agua": chr(0x1F4A7), "presion": chr(0x1F4A8)}
        nombres = {"energia": "Energia", "oxigeno": "Oxigeno",
                    "agua": "Agua", "presion": "Presion"}
        mx, my = mouse_pos if mouse_pos else (0, 0)
        accion = None
        for rec in ["energia", "oxigeno", "agua", "presion"]:
            precio = self.precios[rec]
            tend = self.tendencia(rec)
            color = Config.COLOR_TEXTO_VERDE if precio < self.base[rec] else (
                Config.COLOR_TEXTO_ROJO if precio > self.base[rec] * 1.3 else Config.COLOR_TEXTO)
            linea = f"{iconos[rec]} {nombres[rec]}: {precio:.1f} c/u {tend}"
            txt = r.fuente_pequenia.render(linea, True, color)
            pantalla.blit(txt, (x + 15, y_off))
            # Botones comprar/vender (derecha)
            btn_x = x + 210
            # Boton vender (-5)
            btn_v = pygame.Rect(btn_x, y_off, 28, 20)
            c_v = Config.COLOR_BOTON_HOVER if btn_v.collidepoint(mx - x, my - y) else Config.COLOR_BOTON
            pygame.draw.rect(pantalla, c_v, btn_v, border_radius=4)
            txt_v = r.fuente_pequenia.render("-5", True, Config.COLOR_TEXTO_ROJO)
            pantalla.blit(txt_v, (btn_x + 3, y_off + 1))
            if mouse_click and btn_v.collidepoint(mx - x, my - y):
                accion = ("vender", rec, 5)
            # Boton vender (-1)
            btn_v1 = pygame.Rect(btn_x + 32, y_off, 24, 20)
            c_v1 = Config.COLOR_BOTON_HOVER if btn_v1.collidepoint(mx - x, my - y) else Config.COLOR_BOTON
            pygame.draw.rect(pantalla, c_v1, btn_v1, border_radius=4)
            txt_v1 = r.fuente_pequenia.render("-1", True, Config.COLOR_TEXTO_ROJO)
            pantalla.blit(txt_v1, (btn_x + 34, y_off + 1))
            if mouse_click and btn_v1.collidepoint(mx - x, my - y):
                accion = ("vender", rec, 1)
            # Boton comprar (+1)
            btn_c1 = pygame.Rect(btn_x + 62, y_off, 24, 20)
            c_c1 = Config.COLOR_BOTON_HOVER if btn_c1.collidepoint(mx - x, my - y) else Config.COLOR_BOTON
            pygame.draw.rect(pantalla, c_c1, btn_c1, border_radius=4)
            txt_c1 = r.fuente_pequenia.render("+1", True, Config.COLOR_TEXTO_VERDE)
            pantalla.blit(txt_c1, (btn_x + 63, y_off + 1))
            if mouse_click and btn_c1.collidepoint(mx - x, my - y):
                accion = ("comprar", rec, 1)
            # Boton comprar (+5)
            btn_c = pygame.Rect(btn_x + 90, y_off, 28, 20)
            c_c = Config.COLOR_BOTON_HOVER if btn_c.collidepoint(mx - x, my - y) else Config.COLOR_BOTON
            pygame.draw.rect(pantalla, c_c, btn_c, border_radius=4)
            txt_c = r.fuente_pequenia.render("+5", True, Config.COLOR_TEXTO_VERDE)
            pantalla.blit(txt_c, (btn_x + 93, y_off + 1))
            if mouse_click and btn_c.collidepoint(mx - x, my - y):
                accion = ("comprar", rec, 5)
            y_off += 28
        if self.evento_activo:
            y_off += 5
            txt_ev = r.fuente_pequenia.render(
                f"Evento: {self.evento_activo} ({self.evento_duracion}t)",
                True, Config.COLOR_TEXTO_AMARILLO)
            pantalla.blit(txt_ev, (x + 15, y_off))
            y_off += 24
        txt_info = r.fuente_pequenia.render(
            "M: Ocultar | -vender +comprar", True, Config.COLOR_TEXTO)
        pantalla.blit(txt_info, (x + 15, y_off + 8))
        return accion




# ═══════════════════════════════════════════════════════════════
# COLONOS DINAMICOS - Sistema de NPCs con vida propia
# ═══════════════════════════════════════════════════════════════

NOMBRES_LUNARES = [
    "Apolo", "Selene", "Diana", "Artemisa", "Orion", "Casiopea", "Gagarin",
    "Valentina", "Armstrong", "Aldrin", "Collins", "Tycho", "Copernico",
    "Kepler", "Ares", "Helios", "Nova", "Astra", "Cosmo", "Luna",
]

COLORES_TAREA = {
    "descansar": (70, 130, 180),
    "construir": (60, 180, 75),
    "reparar": (255, 210, 80),
    "protestar": (220, 60, 60),
    "moverse": (180, 180, 180),
}


class Colono:
    """Un colono individual con necesidades, tareas y movimiento."""

    def __init__(self, x: int, y: int, nombre: str):
        self.nombre = nombre
        self.x = float(x)
        self.y = float(y)
        self.salud = 100.0
        self.felicidad = float(random.randint(50, 100))
        self.productividad = 100.0
        self.necesidad_actual = random.choice(["oxigeno", "agua", "energia", "felicidad"])
        self.tarea_actual = "descansar"
        self.destino_x = x
        self.destino_y = y
        self.frames_parado = 0
        self.frames_tarea = 0

    def asignar_destino(self, mapa, recursos):
        """Busca la zona mas adecuada segun la necesidad actual."""
        zona_map = {
            "oxigeno": "ecologico",
            "agua": "ecologico",
            "energia": "industrial",
            "felicidad": "comercial",
        }
        zona_objetivo = zona_map.get(self.necesidad_actual, "alojamiento")
        tiles = mapa.tiles_zonificados(zona_objetivo)
        if not tiles:
            tiles = mapa.tiles_zonificados("alojamiento")
        if tiles:
            self.destino_x, self.destino_y = random.choice(tiles)
            self.tarea_actual = "moverse"

    def mover_hacia_destino(self, es_de_noche: bool = False):
        """Movimiento suave hacia el destino."""
        dx = self.destino_x - self.x
        dy = self.destino_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.2:
            velocidad = (0.04 + random.random() * 0.03) * (0.5 if es_de_noche else 1.0)
            self.x += (dx / dist) * velocidad
            self.y += (dy / dist) * velocidad
            self.tarea_actual = "moverse"
            return False
        self.x = float(self.destino_x)
        self.y = float(self.destino_y)
        return True

    def ejecutar_tarea(self, mapa, recursos):
        """Ejecuta la tarea al llegar al destino."""
        ix, iy = int(self.x), int(self.y)
        zona_actual = None
        if 0 <= ix < mapa.tamanio and 0 <= iy < mapa.tamanio:
            zona_actual = mapa.zonas[iy][ix]

        if self.necesidad_actual == "oxigeno" and zona_actual == "ecologico":
            self.tarea_actual = "reparar"
            recursos.oxigeno += random.randint(1, 3)
        elif self.necesidad_actual == "energia" and zona_actual == "industrial":
            self.tarea_actual = "construir"
            recursos.energia += random.randint(1, 3)
        elif self.necesidad_actual == "agua" and zona_actual == "ecologico":
            self.tarea_actual = "reparar"
            recursos.agua += random.randint(1, 2)
        elif self.necesidad_actual == "felicidad" and zona_actual == "comercial":
            self.tarea_actual = "descansar"
            self.felicidad = min(100, self.felicidad + random.randint(2, 8))
        else:
            self.tarea_actual = "descansar"

    def actualizar(self, mapa, recursos, es_de_noche: bool = False):
        """Actualiza el estado del colono cada frame."""
        self.frames_parado += 1

        if self.frames_parado % 180 == 0:
            self.salud = max(0, self.salud - random.uniform(0, 0.5))
            self.felicidad = max(0, self.felicidad - random.uniform(0, 0.3))

        if self.tarea_actual == "moverse":
            llego = self.mover_hacia_destino(es_de_noche)
            if llego:
                self.ejecutar_tarea(mapa, recursos)
                self.frames_tarea = 0
            return

        self.frames_tarea += 1
        if self.frames_tarea > 300:
            self.necesidad_actual = random.choice(["oxigeno", "agua", "energia", "felicidad"])
            self.asignar_destino(mapa, recursos)
            self.frames_tarea = 0
            self.frames_parado = 0

        if self.felicidad < 20 and random.random() < 0.01:
            self.tarea_actual = "protestar"


class SistemaColonos:
    """Gestiona la poblacion de colonos y su panel overlay (tecla C)."""

    def __init__(self, renderizador, mapa):
        self.visible = False
        self.colonos: list = []
        self.renderizador = renderizador
        self.mapa = mapa
        self.frames = 0
        self.poblacion_objetivo = 0

    def spawn_colono(self):
        """Crea un nuevo colono en zona de alojamiento aleatoria."""
        tiles = self.mapa.tiles_zonificados("alojamiento")
        if not tiles:
            tiles = [(self.mapa.tamanio // 2, self.mapa.tamanio // 2)]
        tx, ty = random.choice(tiles)
        nombre = random.choice(NOMBRES_LUNARES)
        existentes = {c.nombre for c in self.colonos}
        intentos = 0
        while nombre in existentes and intentos < 30:
            nombre = random.choice(NOMBRES_LUNARES) + str(random.randint(1, 99))
            intentos += 1
        self.colonos.append(Colono(tx, ty, nombre))
        return True

    def actualizar(self, recursos, poblacion_total, es_de_noche: bool = False):
        """Actualiza el sistema de colonos cada frame."""
        self.frames += 1
        self.poblacion_objetivo = max(1, poblacion_total // 2)

        if len(self.colonos) < self.poblacion_objetivo and self.frames % 120 == 0:
            self.spawn_colono()

        while len(self.colonos) > self.poblacion_objetivo:
            self.colonos.pop()

        for colono in self.colonos:
            colono.actualizar(self.mapa, recursos, es_de_noche)

        for colono in self.colonos:
            if colono.tarea_actual != "moverse" and colono.frames_parado > 600:
                colono.asignar_destino(self.mapa, recursos)
                colono.frames_parado = 0

    def dibujar_en_mapa(self, pantalla, camara):
        """Dibuja los colonos como circulos de colores en el mapa."""
        for colono in self.colonos:
            px, py = camara.iso_a_pantalla(colono.x, colono.y)
            if 0 <= px <= camara.ancho_ventana and 0 <= py <= camara.alto_ventana:
                color = COLORES_TAREA.get(colono.tarea_actual, (255, 255, 255))
                radio = max(2, int(4 * camara.zoom))
                offset_y = int(math.sin(pygame.time.get_ticks() * 0.005 + hash(colono.nombre) % 100) * 2)
                pygame.draw.circle(pantalla, color, (int(px), int(py) - 10 + offset_y), radio)
                pygame.draw.circle(pantalla, Config.COLOR_TEXTO, (int(px), int(py) - 10 + offset_y), radio, 1)

    def renderizar(self, pantalla, renderizador):
        """Renderiza el panel overlay de Gestion de Colonos."""
        x, y = 10, 50
        ancho, alto = 380, 320

        overlay = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        overlay.fill((*Config.COLOR_PANEL, 240))
        pantalla.blit(overlay, (x, y))

        pygame.draw.rect(pantalla, Config.COLOR_PANEL_BORDE, (x, y, ancho, alto), 2, border_radius=8)

        fuente_m = renderizador.fuente_mediana
        fuente_p = renderizador.fuente_pequenia

        cabecera = "Gestion de Colonos"
        txt = fuente_m.render(cabecera, True, Config.COLOR_TEXTO_AMARILLO)
        pantalla.blit(txt, (x + 15, y + 10))

        total = len(self.colonos)
        if total > 0:
            salud_prom = sum(c.salud for c in self.colonos) / total
            fel_prom = sum(c.felicidad for c in self.colonos) / total
        else:
            salud_prom = fel_prom = 0

        stats_y = y + 42
        stats = [
            f"Poblacion: {total}",
            f"Salud: {salud_prom:.0f}%",
            f"Felicidad: {fel_prom:.0f}%",
        ]
        for i, s in enumerate(stats):
            txt = fuente_p.render(s, True, Config.COLOR_TEXTO)
            pantalla.blit(txt, (x + 15 + i * 120, stats_y))

        sep_y = y + 65
        pygame.draw.line(pantalla, Config.COLOR_PANEL_BORDE, (x + 10, sep_y), (x + ancho - 10, sep_y), 1)

        tabla_y = y + 72
        cabeceras = f"{'Nombre':<12} {'Tarea':<11} {'Sal':>4} {'Fel':>4}"
        txt = fuente_p.render(cabeceras, True, Config.COLOR_PANEL_BORDE)
        pantalla.blit(txt, (x + 15, tabla_y))

        for i, colono in enumerate(self.colonos[:8]):
            fila_y = tabla_y + 18 + i * 22

            nombre_txt = fuente_p.render(f"{colono.nombre:<12}", True, Config.COLOR_TEXTO)
            pantalla.blit(nombre_txt, (x + 15, fila_y))

            color_tarea = COLORES_TAREA.get(colono.tarea_actual, Config.COLOR_TEXTO)
            tarea_txt = fuente_p.render(f"{colono.tarea_actual:<11}", True, color_tarea)
            pantalla.blit(tarea_txt, (x + 120, fila_y))

            color_salud = (220, 60, 60) if colono.salud < 30 else (60, 180, 75) if colono.salud > 70 else Config.COLOR_TEXTO
            salud_txt = fuente_p.render(f"{colono.salud:>4.0f}", True, color_salud)
            pantalla.blit(salud_txt, (x + 245, fila_y))

            color_fel = (220, 60, 60) if colono.felicidad < 30 else (60, 180, 75) if colono.felicidad > 70 else Config.COLOR_TEXTO
            fel_txt = fuente_p.render(f"{colono.felicidad:>4.0f}", True, color_fel)
            pantalla.blit(fel_txt, (x + 290, fila_y))

        pie_y = y + alto - 22
        pie_txt = fuente_p.render("C: Ocultar panel  |  Colonos autonomos", True, Config.COLOR_PANEL_BORDE)
        pantalla.blit(pie_txt, (x + 15, pie_y))



@dataclass

class EdificioColocado:

    """Un edificio colocado en el mapa."""

    tipo: TipoEdificio

    x: int  # Posición en el grid (esquina superior-izquierda)

    y: int  # Posición en el grid (esquina superior-izquierda)

    activo: bool = True

    sprite: Optional[pygame.Surface] = None



    @property

    def ancho(self) -> int:

        return self.tipo.ancho_tiles



    @property

    def alto(self) -> int:

        return self.tipo.alto_tiles



    def ocupa_tile(self, gx: int, gy: int) -> bool:

        """Verifica si este edificio ocupa la celda (gx, gy) del grid."""

        return self.x <= gx < self.x + self.ancho and self.y <= gy < self.y + self.alto



class Mapa:

    """Mapa isometrico con grid para la colonia. Soporta edificios multi-tile y zonificacion."""



    def __init__(self, tamanio: int = None):

        self.tamanio = tamanio if tamanio is not None else Config.TAMANIO_GRID

        self.grid: List[List[Optional[EdificioColocado]]] = [

            [None for _ in range(self.tamanio)] for _ in range(self.tamanio)

        ]

        self.edificios: List[EdificioColocado] = []

        self.zonas: List[List[Optional[str]]] = [

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



    def _footprint_libre(self, x: int, y: int, ancho: int, alto: int) -> bool:

        """Verifica que todas las celdas del footprint estén dentro del mapa y libres."""

        for dy in range(alto):

            for dx in range(ancho):

                gx, gy = x + dx, y + dy

                if not (0 <= gx < self.tamanio and 0 <= gy < self.tamanio):

                    return False

                if self.grid[gy][gx] is not None:

                    return False

        return True



    def colocar_edificio(self, x: int, y: int, tipo: TipoEdificio, sprite: pygame.Surface) -> Optional[EdificioColocado]:

        """Coloca un edificio multi-tile en el grid."""

        if self._footprint_libre(x, y, tipo.ancho_tiles, tipo.alto_tiles):

            edificio = EdificioColocado(tipo=tipo, x=x, y=y, sprite=sprite)

            # Marcar todas las celdas del footprint

            for dy in range(tipo.alto_tiles):

                for dx in range(tipo.ancho_tiles):

                    self.grid[y + dy][x + dx] = edificio

            self.edificios.append(edificio)

            return edificio

        return None



    def vender_edificio(self, x: int, y: int) -> Optional[EdificioColocado]:

        """Elimina un edificio (incluyendo todo su footprint) y retorna el edificio."""

        if 0 <= x < self.tamanio and 0 <= y < self.tamanio:

            edificio = self.grid[y][x]

            if edificio:

                # Limpiar todas las celdas del footprint

                for dy in range(edificio.alto):

                    for dx in range(edificio.ancho):

                        self.grid[edificio.y + dy][edificio.x + dx] = None

                if edificio in self.edificios:

                    self.edificios.remove(edificio)

                return edificio

        return None



    def esta_ocupado(self, x: int, y: int) -> bool:

        """Verifica si una celda del grid está ocupada."""

        if 0 <= x < self.tamanio and 0 <= y < self.tamanio:

            return self.grid[y][x] is not None

        return True  # Fuera del mapa se considera ocupado



    def tile_valido(self, x: int, y: int, ancho: int = 1, alto: int = 1) -> bool:

        """Verifica si el footprint completo esta dentro del mapa y libre."""

        return self._footprint_libre(x, y, ancho, alto)



    def pintar_zona(self, x: int, y: int, zona_id: str) -> bool:

        """Pinta una zona en una celda del grid."""

        if 0 <= x < self.tamanio and 0 <= y < self.tamanio:

            if self.grid[y][x] is None:

                self.zonas[y][x] = zona_id

                return True

        return False



    def borrar_zona(self, x: int, y: int) -> bool:

        """Quita la zonificacion de una celda."""

        if 0 <= x < self.tamanio and 0 <= y < self.tamanio:

            self.zonas[y][x] = None

            return True

        return False



    def tiles_zonificados(self, zona_id: Optional[str] = None) -> List[Tuple[int, int]]:

        """Devuelve lista de tiles zonificados. Si zona_id es None, devuelve todos."""

        tiles = []

        for y in range(self.tamanio):

            for x in range(self.tamanio):

                z = self.zonas[y][x]

                if z is not None and (zona_id is None or z == zona_id):

                    if self.grid[y][x] is None:

                        tiles.append((x, y))

        return tiles



class Camara:

    """Cámara isométrica con zoom y desplazamiento."""



    def __init__(self, ancho_ventana: int, alto_ventana: int):

        self.offset_x: float = ancho_ventana // 2

        self.offset_y: float = 100.0

        self.zoom: float = 1.0

        self.ancho_ventana = ancho_ventana

        self.alto_ventana = alto_ventana



    def iso_a_pantalla(self, x: int, y: int) -> Tuple[float, float]:

        """Convierte coordenadas del grid isométrico a píxeles en pantalla."""

        tam = Config.TAMANIO_TILE * self.zoom

        px = self.offset_x + (x - y) * tam / 2

        py = self.offset_y + (x + y) * tam / 4

        return px, py



    def pantalla_a_iso(self, px: float, py: float) -> Tuple[int, int]:

        """Convierte coordenadas de pantalla a grid isométrico."""

        tam = Config.TAMANIO_TILE * self.zoom

        # Deshacer el offset

        rx = px - self.offset_x

        ry = py - self.offset_y

        # Fórmula inversa de isométrico 2:1

        grid_x = (rx / (tam / 2) + ry / (tam / 4)) / 2

        grid_y = (ry / (tam / 4) - rx / (tam / 2)) / 2

        return int(grid_x), int(grid_y)



    def mover(self, dx: float, dy: float) -> None:

        """Desplaza la cámara."""

        velocidad = 10.0 / self.zoom

        self.offset_x += dx * velocidad

        self.offset_y += dy * velocidad



    def acercar(self, cantidad: float) -> None:

        """Ajusta el zoom entre 0.5x y 2.0x."""

        self.zoom = max(0.5, min(2.0, self.zoom + cantidad))






# ═══════════════════════════════════════════════════════════════
# 💥 CRISIS LUNAR - Eventos catastroficos aleatorios
# ═══════════════════════════════════════════════════════════════

class CrisisLunar:
    """Sistema de emergencias y catastrofes para la colonia lunar (tecla X)."""

    def __init__(self):
        self.visible = False
        self.evento_activo = None
        self.enfriamiento = 5
        self.historial = []
        self.particulas = []
        self.tecnologia = None  # Referencia al arbol (se asigna externamente)

        self.TIPOS_EVENTOS = {
            "meteorito": {"nombre": "Impacto de Meteorito", "emoji": "Meteorito", "severidades": 3, "color": (255, 80, 50)},
            "tormenta_solar": {"nombre": "Tormenta Solar", "emoji": "Tormenta", "severidades": 3, "color": (255, 210, 80)},
            "fuga_oxigeno": {"nombre": "Fuga de Oxigeno", "emoji": "Fuga", "severidades": 2, "color": (50, 180, 255)},
            "plaga": {"nombre": "Plaga Botanica/Virica", "emoji": "Plaga", "severidades": 3, "color": (150, 50, 200)},
            "motin": {"nombre": "Motin de Colonos", "emoji": "Motin", "severidades": 2, "color": (220, 40, 40)},
            "fallo_reactor": {"nombre": "Fallo de Reactor", "emoji": "Reactor", "severidades": 3, "color": (50, 255, 50)},
        }

    def actualizar(self, recursos, sistema_colonos, mapa, turno):
        """Actualiza el sistema de crisis cada turno."""
        if self.evento_activo:
            self.evento_activo["duracion"] -= 1
            tipo = self.evento_activo["tipo"]
            sev = self.evento_activo["severidad"]
            if tipo == "tormenta_solar":
                factor = 0.75 if (self.tecnologia and self.tecnologia.bonos_activos.get('tormenta_proteccion')) else 0.5
                recursos.energia = int(recursos.energia * factor)
            elif tipo == "fuga_oxigeno":
                recursos.oxigeno -= 30 * sev
            elif tipo == "fallo_reactor":
                recursos.energia = int(recursos.energia * 0.2)
            if self.evento_activo["duracion"] <= 0:
                self.historial.insert(0, "Resuelto: " + self.evento_activo["mensaje"])
                self.evento_activo = None
                self.enfriamiento = random.randint(3, 5)
            return

        if self.enfriamiento > 0:
            self.enfriamiento -= 1
            return

        probabilidad = 0.10 + (len(mapa.edificios) / 10.0) * 0.01
        if random.random() < min(probabilidad, 0.35):
            self._generar_evento(recursos, sistema_colonos, mapa)

    def _generar_evento(self, recursos, sistema_colonos, mapa):
        tipo_k = random.choice(list(self.TIPOS_EVENTOS.keys()))
        info = self.TIPOS_EVENTOS[tipo_k]
        severidad = random.randint(1, info["severidades"])
        duracion = random.randint(1, 4)

        self.evento_activo = {
            "tipo": tipo_k, "severidad": severidad, "duracion": duracion,
            "mensaje": f"{info['nombre']} Nivel {severidad}",
            "zona_x": random.randint(0, mapa.tamanio - 1),
            "zona_y": random.randint(0, mapa.tamanio - 1),
            "costo": severidad * 400,
        }
        self.visible = True

        if tipo_k == "meteorito":
            recursos.oxigeno -= 20
            if mapa.edificios:
                objetivo = random.choice(mapa.edificios)
                self.evento_activo["zona_x"] = objetivo.x
                self.evento_activo["zona_y"] = objetivo.y
                if not (self.tecnologia and self.tecnologia.bonos_activos.get('meteorito_inmune')):
                    mapa.vender_edificio(objetivo.x, objetivo.y)
                else:
                    pass  # Protegido por Red de Refugios
        elif tipo_k == "plaga":
            n = max(1, int(len(sistema_colonos.colonos) * 0.3))
            for c in random.sample(sistema_colonos.colonos, n) if sistema_colonos.colonos else []:
                c.salud = max(0, c.salud - 15)
        elif tipo_k == "motin":
            recursos.felicidad = max(0, recursos.felicidad - 20)
            n = max(1, int(len(sistema_colonos.colonos) * 0.5))
            if sistema_colonos.colonos:
                for c in random.sample(sistema_colonos.colonos, min(n, len(sistema_colonos.colonos))):
                    c.tarea_actual = "protestar"

    def resolver(self, recursos):
        if not self.evento_activo:
            return False
        coste = self.evento_activo.get("costo", 500)
        if recursos.gastar(coste):
            self.historial.insert(0, "Resuelto: " + self.evento_activo["mensaje"])
            self.evento_activo = None
            self.enfriamiento = 3
            return True
        return False

    def renderizar(self, pantalla, renderizador, mouse_pos, mouse_click, recursos):
        if not self.visible:
            return
        ancho, alto = 400, 250
        x = (Config.ANCHO_VENTANA - ancho) // 2
        y = (Config.ALTO_VENTANA - alto) // 2

        if self.evento_activo:
            fondo_color = (60, 10, 10)
        else:
            fondo_color = Config.COLOR_PANEL
        rect = pygame.Rect(x, y, ancho, alto)
        pygame.draw.rect(pantalla, (*fondo_color, 240), rect, border_radius=10)
        pygame.draw.rect(pantalla, Config.COLOR_PANEL_BORDE, rect, 2, border_radius=10)

        r = renderizador
        mx, my = mouse_pos

        if self.evento_activo:
            evt = self.evento_activo
            info = self.TIPOS_EVENTOS[evt["tipo"]]
            txt_tit = r.fuente_mediana.render("CRISIS LUNAR", True, Config.COLOR_TEXTO_ROJO)
            pantalla.blit(txt_tit, (x + 20, y + 20))

            txt_desc = r.fuente_pequenia.render(evt["mensaje"], True, info["color"])
            pantalla.blit(txt_desc, (x + 20, y + 60))

            txt_dur = r.fuente_pequenia.render("Duracion: " + str(evt["duracion"]) + " turnos", True, Config.COLOR_TEXTO)
            pantalla.blit(txt_dur, (x + 20, y + 85))

            # Boton Resolver
            btn_res = pygame.Rect(x + 20, y + 180, 150, 40)
            cbtn = Config.COLOR_BOTON_HOVER if btn_res.collidepoint(mx, my) else Config.COLOR_BOTON
            pygame.draw.rect(pantalla, cbtn, btn_res, border_radius=5)
            txt_r = r.fuente_pequenia.render("Resolver C$" + str(evt["costo"]), True, Config.COLOR_TEXTO_VERDE)
            pantalla.blit(txt_r, (x + 30, y + 190))

            # Boton Ignorar
            btn_ign = pygame.Rect(x + 230, y + 180, 150, 40)
            cbtn_i = Config.COLOR_BOTON_HOVER if btn_ign.collidepoint(mx, my) else Config.COLOR_BOTON
            pygame.draw.rect(pantalla, cbtn_i, btn_ign, border_radius=5)
            txt_i = r.fuente_pequenia.render("Ignorar", True, Config.COLOR_TEXTO_ROJO)
            pantalla.blit(txt_i, (x + 270, y + 190))

            if mouse_click:
                if btn_res.collidepoint(mx, my):
                    self.resolver(recursos)
                    self.visible = False
                elif btn_ign.collidepoint(mx, my):
                    self.visible = False
        else:
            txt_tit = r.fuente_mediana.render("Centro de Crisis (Historial)", True, Config.COLOR_TEXTO_AMARILLO)
            pantalla.blit(txt_tit, (x + 20, y + 20))
            y_off = y + 60
            for h in self.historial[:5]:
                txt_h = r.fuente_pequenia.render(h, True, Config.COLOR_TEXTO)
                pantalla.blit(txt_h, (x + 20, y_off))
                y_off += 25
            if not self.historial:
                txt_h = r.fuente_pequenia.render("Sin incidentes... por ahora.", True, Config.COLOR_TEXTO)
                pantalla.blit(txt_h, (x + 20, y_off))

        txt_x = r.fuente_pequenia.render("X: Cerrar panel", True, Config.COLOR_PANEL_BORDE)
        pantalla.blit(txt_x, (x + 20, y + alto - 25))

    def dibujar_en_mapa(self, pantalla, camara):
        """Efectos visuales en el mapa."""
        if not self.evento_activo:
            return
        tipo = self.evento_activo["tipo"]

        if tipo == "tormenta_solar":
            alpha = int((math.sin(pygame.time.get_ticks() * 0.005) + 1) * 30)
            overlay = pygame.Surface((camara.ancho_ventana, camara.alto_ventana), pygame.SRCALPHA)
            overlay.fill((255, 210, 80, alpha))
            pantalla.blit(overlay, (0, 0))

        x, y = self.evento_activo["zona_x"], self.evento_activo["zona_y"]
        px, py = camara.iso_a_pantalla(x, y)
        if 0 <= px <= camara.ancho_ventana and 0 <= py <= camara.alto_ventana:
            color = self.TIPOS_EVENTOS[tipo]["color"]
            if tipo == "meteorito":
                pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.01)) * 20 * camara.zoom)
                pygame.draw.circle(pantalla, color, (int(px), int(py)), pulse, 2)
            elif tipo == "fuga_oxigeno":
                particle_y = int(py - (pygame.time.get_ticks() % 1000) / 20)
                pygame.draw.circle(pantalla, color, (int(px), particle_y), 5, 2)
            elif tipo == "plaga":
                pygame.draw.circle(pantalla, color, (int(px), int(py)), int(8 * camara.zoom), 2)





# ═══════════════════════════════════════════════════════════════
# ☀️🌙 CICLO DIA/NOCHE - Efectos reales en produccion, visibilidad y colonos
# ═══════════════════════════════════════════════════════════════

class CicloDiaNoche:
    """Sistema de ciclo dia/noche con efectos en energia solar, visibilidad y colonos."""

    def __init__(self, ancho: int, alto: int):
        self.turno_actual = 0
        self.es_de_noche = False
        self.dia_actual = 1
        self.noche_actual = 1
        self.overlay_noche = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        self.estrellas = [(random.randint(0, ancho), random.randint(0, alto // 2), random.uniform(0.3, 1.5)) for _ in range(120)]
        self.alpha_actual = 0.0
        self.alpha_objetivo = 0.0

    def avanzar(self):
        """Llamado al avanzar turno. Alterna dia(0-13) y noche(14-27)."""
        self.turno_actual = (self.turno_actual + 1) % 28
        self.es_de_noche = self.turno_actual >= 14
        if not self.es_de_noche:
            self.dia_actual = self.turno_actual + 1
        else:
            self.noche_actual = self.turno_actual - 13
        self.alpha_objetivo = 160.0 if self.es_de_noche else 0.0

    def actualizar(self):
        """Transicion suave del overlay de noche cada frame."""
        if self.alpha_actual < self.alpha_objetivo:
            self.alpha_actual = min(self.alpha_objetivo, self.alpha_actual + 1.5)
        elif self.alpha_actual > self.alpha_objetivo:
            self.alpha_actual = max(self.alpha_objetivo, self.alpha_actual - 1.5)


    def renderizar_overlay(self, pantalla):
        """Oscurece la pantalla + estrellas. Llamar al FINAL tras mapa pero antes de UI."""
        if self.alpha_actual > 1:
            self.overlay_noche.fill((3, 8, 28, int(self.alpha_actual)))
            if self.alpha_actual > 80:
                t = pygame.time.get_ticks() * 0.0015
                for x, y, vel in self.estrellas:
                    b = int((math.sin(t * vel) + 1) * 100 * (self.alpha_actual / 160))
                    pygame.draw.circle(self.overlay_noche, (255, 255, 240, b), (x, y), max(1, int(vel)))
            pantalla.blit(self.overlay_noche, (0, 0))

    def renderizar_ui(self, pantalla, renderizador, ancho_ventana):
        """Panel indicador dia/noche en esquina superior derecha."""
        fase = self.turno_actual + 1 if not self.es_de_noche else self.turno_actual - 13
        fase_str = f"Dia {fase}/14" if not self.es_de_noche else f"Noche {fase}/14"
        icono = "Sol" if not self.es_de_noche else "Luna"
        r = renderizador
        rect_p = pygame.Rect(ancho_ventana - 155, 8, 145, 42)
        pygame.draw.rect(pantalla, (*Config.COLOR_PANEL, 225), rect_p, border_radius=8)
        pygame.draw.rect(pantalla, Config.COLOR_PANEL_BORDE, rect_p, 2, border_radius=8)
        txt = r.fuente_pequenia.render(f"{icono} {fase_str}", True, Config.COLOR_TEXTO_AMARILLO)
        pantalla.blit(txt, (rect_p.x + 8, rect_p.y + 4))
        prog = self.turno_actual / 28.0
        pygame.draw.rect(pantalla, (40, 40, 70), (rect_p.x + 8, rect_p.y + 28, 128, 5))
        color_b = (255, 200, 50) if not self.es_de_noche else (80, 140, 240)
        pygame.draw.rect(pantalla, color_b, (rect_p.x + 8, rect_p.y + 28, int(128 * prog), 5))
# ═══════════════════════════════════════════════════════════════
# 🔬 ÁRBOL DE TECNOLOGÍA — Investigación y desbloqueo de edificios
# ═══════════════════════════════════════════════════════════════

TECNOLOGIAS = {
    # ── Energía ⚡ ──
    "energia_1": {
        "nombre": "Paneles Solares Avanzados", "rama": "energia", "tier": 1,
        "costo": 800, "turnos": 3, "emoji": chr(0x26A1),
        "descripcion": "Mejora la eficiencia solar +25%.",
        "desbloquea": ["sol_02", "sol_08"],
        "bono": {"energia_factor": 0.25},
        "requiere": None,
    },
    "energia_2": {
        "nombre": "Fusion Helio-3", "rama": "energia", "tier": 2,
        "costo": 2500, "turnos": 5, "emoji": chr(0x2622) + chr(0xFE0F),
        "descripcion": "Reactores de fusion avanzados.",
        "desbloquea": ["sol_07", "site_07"],
        "bono": {},
        "requiere": "energia_1",
    },
    "energia_3": {
        "nombre": "Energia de Fusion Total", "rama": "energia", "tier": 3,
        "costo": 5000, "turnos": 8, "emoji": chr(0x1F30C),
        "descripcion": "Planta de fusion para megacolonias.",
        "desbloquea": ["sol_10", "site_11"],
        "bono": {"energia_noche_factor": 0.5},
        "requiere": "energia_2",
    },
    # ── Habitabilidad 🏠 ──
    "hab_1": {
        "nombre": "Sistemas de Soporte Vital", "rama": "habitabilidad", "tier": 1,
        "costo": 600, "turnos": 2, "emoji": chr(0x1F3E0),
        "descripcion": "Extraccion de agua y reciclaje de aire.",
        "desbloquea": ["life_01", "life_03", "misc_02"],
        "bono": {"oxigeno_factor": 0.10},
        "requiere": None,
    },
    "hab_2": {
        "nombre": "Agricultura Lunar Avanzada", "rama": "habitabilidad", "tier": 2,
        "costo": 1800, "turnos": 4, "emoji": chr(0x1F331),
        "descripcion": "Invernaderos masivos y acuaponia.",
        "desbloquea": ["gh_02", "gh_05", "gh_07"],
        "bono": {"agua_factor": 0.15},
        "requiere": "hab_1",
    },
    "hab_3": {
        "nombre": "Terraformacion Lunar", "rama": "habitabilidad", "tier": 3,
        "costo": 4000, "turnos": 7, "emoji": chr(0x1F30D),
        "descripcion": "Agricultura a escala planetaria.",
        "desbloquea": ["site_06", "life_02", "site_08"],
        "bono": {"felicidad_factor": 0.10, "poblacion_extra": 10},
        "requiere": "hab_2",
    },
    # ── Industria 🏭 ──
    "ind_1": {
        "nombre": "Mineria Lunar Basica", "rama": "industria", "tier": 1,
        "costo": 1000, "turnos": 3, "emoji": chr(0x26CF) + chr(0xFE0F),
        "descripcion": "Excavacion y fundicion de regolito.",
        "desbloquea": ["site_01", "ind_01", "veh_02"],
        "bono": {},
        "requiere": None,
    },
    "ind_2": {
        "nombre": "Manufactura Avanzada 3D", "rama": "industria", "tier": 2,
        "costo": 3000, "turnos": 5, "emoji": chr(0x1F3ED),
        "descripcion": "Impresion 3D y exportacion.",
        "desbloquea": ["ind_02", "ind_04", "ind_05"],
        "bono": {"alquiler_factor": 0.20},
        "requiere": "ind_1",
    },
    "ind_3": {
        "nombre": "Economia Espacial", "rama": "industria", "tier": 3,
        "costo": 6000, "turnos": 8, "emoji": chr(0x1F680),
        "descripcion": "Puerto espacial y comercio interplanetario.",
        "desbloquea": ["site_04", "site_05", "ind_03"],
        "bono": {"ingreso_factor": 0.20},
        "requiere": "ind_2",
    },
    # ── Defensa 🛡️ ──
    "def_1": {
        "nombre": "Blindaje y Presurizacion", "rama": "defensa", "tier": 1,
        "costo": 700, "turnos": 2, "emoji": chr(0x1F6E1) + chr(0xFE0F),
        "descripcion": "Proteccion basica contra emergencias.",
        "desbloquea": ["rsk_01", "misc_10", "misc_11"],
        "bono": {},
        "requiere": None,
    },
    "def_2": {
        "nombre": "Escudos de Radiacion", "rama": "defensa", "tier": 2,
        "costo": 2000, "turnos": 4, "emoji": chr(0x1F300),
        "descripcion": "Proteccion contra tormentas solares.",
        "desbloquea": ["rsk_02", "civ_01"],
        "bono": {"tormenta_proteccion": True},
        "requiere": "def_1",
    },
    "def_3": {
        "nombre": "Red de Refugios Subterraneos", "rama": "defensa", "tier": 3,
        "costo": 4500, "turnos": 7, "emoji": chr(0x26F0) + chr(0xFE0F),
        "descripcion": "Evacuacion y refugios anti-catastrofes.",
        "desbloquea": ["rsk_03", "hou_04", "civ_02"],
        "bono": {"meteorito_inmune": True},
        "requiere": "def_2",
    },
}

COLORES_RAMA = {
    "energia": (255, 210, 80),
    "habitabilidad": (60, 180, 120),
    "industria": (180, 140, 60),
    "defensa": (120, 140, 220),
}

ICONOS_RAMA = {
    "energia": chr(0x26A1),
    "habitabilidad": chr(0x1F3E0),
    "industria": chr(0x1F3ED),
    "defensa": chr(0x1F6E1) + chr(0xFE0F),
}


class ArbolTecnologia:
    """Sistema de investigacion y desbloqueo progresivo de edificios (tecla T)."""

    def __init__(self):
        self.visible = False
        self.completadas: set = set()
        self.desbloqueadas: set = set()
        self.investigando: Optional[str] = None
        self.turnos_restantes: int = 0
        self.bonos_activos: dict = {}

        # Edificios iniciales disponibles desde el turno 0
        self.desbloqueadas = {
            "sol_01", "sol_04", "sol_08",  # Energia basica
            "biz_02", "biz_04", "biz_11",  # Negocios basicos
            "hou_01", "hou_02",  # Alojamiento basico
            "gh_01", "gh_03", "gh_06",  # Invernaderos basicos
            "misc_01", "misc_04", "misc_06", "misc_08",  # Servicios basicos
            "veh_01", "veh_07",  # Vehiculos basicos
            "dec_01", "dec_02", "dec_03", "dec_04",  # Decoracion basica
            "road_01", "road_02", "road_03", "road_04",  # Carreteras basicas
            "life_01", "life_03",  # Soporte vital basico
        }

    def esta_desbloqueada(self, tech_id: str) -> bool:
        return tech_id in self.completadas

    def puede_investigar(self, tech_id: str) -> bool:
        tech = TECNOLOGIAS[tech_id]
        req = tech.get("requiere")
        if req and not self.esta_desbloqueada(req):
            return False
        if self.investigando is not None:
            return False
        return True

    def investigar(self, tech_id: str, recursos) -> bool:
        tech = TECNOLOGIAS[tech_id]
        if not self.puede_investigar(tech_id):
            return False
        if not recursos.gastar(tech["costo"]):
            return False
        self.investigando = tech_id
        self.turnos_restantes = tech["turnos"]
        return True

    def cancelar_investigacion(self, recursos):
        if self.investigando:
            tech = TECNOLOGIAS[self.investigando]
            recursos.ingresar(tech["costo"] // 2)
            self.investigando = None
            self.turnos_restantes = 0

    def completar_investigacion(self, recursos=None):
        if not self.investigando:
            return
        tech = TECNOLOGIAS[self.investigando]
        tid = self.investigando
        self.completadas.add(tid)
        for bid in tech.get("desbloquea", []):
            self.desbloqueadas.add(bid)
        self._recalcular_bonos()
        # Aplicar poblacion_extra una sola vez
        if recursos and self.bonos_activos.get("poblacion_extra", 0) > 0:
            recursos.poblacion += int(self.bonos_activos["poblacion_extra"])
        # Aplicar poblacion_extra una sola vez
        if self.bonos_activos.get("poblacion_extra", 0) > 0:
            pass  # Se aplicara externamente via _juego
        self.investigando = None
        self.turnos_restantes = 0

    def _recalcular_bonos(self):
        self.bonos_activos = {}
        for tid in self.completadas:
            for k, v in TECNOLOGIAS[tid].get("bono", {}).items():
                if k not in self.bonos_activos:
                    self.bonos_activos[k] = 0
                self.bonos_activos[k] += v

    def actualizar(self, recursos, turno):
        if self.investigando:
            self.turnos_restantes -= 1
            if self.turnos_restantes <= 0:
                self.completar_investigacion(recursos)

    def edificio_desbloqueado(self, edificio_id: str) -> bool:
        return edificio_id in self.desbloqueadas

    def renderizar(self, pantalla, renderizador, mouse_pos, mouse_click, recursos):
        if not self.visible:
            return
        ancho, alto = 580, 380
        x = (Config.ANCHO_VENTANA - ancho) // 2
        y = (Config.ALTO_VENTANA - alto) // 2

        rect = pygame.Rect(x, y, ancho, alto)
        pygame.draw.rect(pantalla, (*Config.COLOR_PANEL, 245), rect, border_radius=10)
        pygame.draw.rect(pantalla, Config.COLOR_PANEL_BORDE, rect, 2, border_radius=10)

        r = renderizador
        mx, my = mouse_pos

        txt_tit = r.fuente_mediana.render(chr(0x1F52C) + " Arbol de Tecnologia", True, Config.COLOR_TEXTO_AMARILLO)
        pantalla.blit(txt_tit, (x + 15, y + 10))

        # ── Investigacion activa ──
        if self.investigando:
            tech = TECNOLOGIAS[self.investigando]
            inv_y = y + 38
            inv_txt = r.fuente_pequenia.render(
                f"Investigando: {tech['emoji']} {tech['nombre']} ({self.turnos_restantes} turnos restantes)",
                True, (100, 200, 255))
            pantalla.blit(inv_txt, (x + 15, inv_y))

            btn_cancel = pygame.Rect(x + 450, inv_y - 2, 110, 22)
            c_c = Config.COLOR_BOTON_HOVER if btn_cancel.collidepoint(mx, my) else Config.COLOR_BOTON
            pygame.draw.rect(pantalla, c_c, btn_cancel, border_radius=4)
            ct = r.fuente_pequenia.render("Cancelar", True, Config.COLOR_TEXTO_ROJO)
            pantalla.blit(ct, (x + 465, inv_y + 1))
            if mouse_click and btn_cancel.collidepoint(mx, my):
                self.cancelar_investigacion(recursos)

        # ── 4 ramas en 4 columnas ──
        columnas = ["energia", "habitabilidad", "industria", "defensa"]
        col_w = 130
        col_x_start = x + 15
        col_y_start = y + 70

        rama_nombres = {
            "energia": "Energia", "habitabilidad": "Habitar",
            "industria": "Industria", "defensa": "Defensa",
        }

        for ci, rama_id in enumerate(columnas):
            cx = col_x_start + ci * col_w
            cy = col_y_start

            color = COLORES_RAMA[rama_id]
            icono = ICONOS_RAMA[rama_id]

            encabezado = f"{icono} {rama_nombres[rama_id]}"
            txt_enc = r.fuente_pequenia.render(encabezado, True, color)
            pantalla.blit(txt_enc, (cx, cy))

            # Dibujar 3 tiers
            for tier in range(1, 4):
                tid = f"{rama_id}_{tier}"
                if tid not in TECNOLOGIAS:
                    continue
                tech = TECNOLOGIAS[tid]
                ty = cy + 22 + (tier - 1) * 72

                # Linea conectora vertical
                if tier > 1:
                    lx = cx + 60
                    pygame.draw.line(pantalla, color, (lx, ty - 10), (lx, ty), 1)

                completada = self.esta_desbloqueada(tid)
                investigando_esta = self.investigando == tid
                req = tech.get("requiere")
                req_cumplida = req is None or self.esta_desbloqueada(req)
                puede = req_cumplida and not self.investigando and not completada

                if completada:
                    bg = (20, 60, 20)
                elif investigando_esta:
                    bg = (20, 40, 80)
                elif puede:
                    bg = Config.COLOR_BOTON
                else:
                    bg = (30, 30, 50)

                btn = pygame.Rect(cx, ty, 122, 60)
                hover = btn.collidepoint(mx, my)
                if hover and puede:
                    bg = Config.COLOR_BOTON_HOVER
                pygame.draw.rect(pantalla, bg, btn, border_radius=5)
                pygame.draw.rect(pantalla, color if completada else Config.COLOR_PANEL_BORDE, btn, 1, border_radius=5)

                nombre = tech["nombre"][:14]
                t1 = r.fuente_pequenia.render(f"{tech['emoji']} {nombre}", True,
                    Config.COLOR_TEXTO_VERDE if completada else Config.COLOR_TEXTO)
                pantalla.blit(t1, (cx + 4, ty + 3))

                if completada:
                    t2 = r.fuente_pequenia.render("COMPLETADO", True, (60, 180, 60))
                elif investigando_esta:
                    t2 = r.fuente_pequenia.render(f"{self.turnos_restantes}t rest", True, (100, 200, 255))
                elif not req_cumplida:
                    t2 = r.fuente_pequenia.render("Bloqueado", True, Config.COLOR_TEXTO_ROJO)
                else:
                    t2 = r.fuente_pequenia.render(f"C${tech['costo']} · {tech['turnos']}t", True, Config.COLOR_TEXTO)
                pantalla.blit(t2, (cx + 4, ty + 22))

                t3 = r.fuente_pequenia.render(tech["descripcion"][:22], True, Config.COLOR_PANEL_BORDE)
                pantalla.blit(t3, (cx + 4, ty + 40))

                if mouse_click and hover and puede:
                    self.investigar(tid, recursos)

        # ── Bonos activos ──
        bonos_y = y + alto - 55
        if self.bonos_activos:
            partes = []
            for k, v in self.bonos_activos.items():
                partes.append(f"{k}: +{v*100:.0f}%")
            txt_bonos = r.fuente_pequenia.render("Bonos: " + " | ".join(partes[:4]), True, Config.COLOR_TEXTO_VERDE)
            pantalla.blit(txt_bonos, (x + 15, bonos_y))

        # ── Pie ──
        pie_txt = r.fuente_pequenia.render(
            "T: Cerrar  |  " + str(len(self.completadas)) + "/12 tecnologias  |  " +
            str(len(self.desbloqueadas)) + " edificios desbloqueados",
            True, Config.COLOR_PANEL_BORDE)
        pantalla.blit(pie_txt, (x + 15, y + alto - 28))
# ═══════════════════════════════════════════════════════════════
# 🔬 ÁRBOL DE TECNOLOGÍA — Investigación y desbloqueo de edificios
# ═══════════════════════════════════════════════════════════════


COLORES_RAMA = {
    "energia": (255, 210, 80),
    "habitabilidad": (60, 180, 120),
    "industria": (180, 140, 60),
    "defensa": (120, 140, 220),
}

ICONOS_RAMA = {
    "energia": chr(0x26A1),
    "habitabilidad": chr(0x1F3E0),
    "industria": chr(0x1F3ED),
    "defensa": chr(0x1F6E1) + chr(0xFE0F),
}


class JuegoSimmoon:

    """Motor principal del juego SIMMOON."""



    def __init__(self, votos: Optional[Dict[str, int]] = None):

        # Ventana

        self.pantalla = pygame.display.set_mode(

            (Config.ANCHO_VENTANA, Config.ALTO_VENTANA),

            pygame.RESIZABLE

        )

        self.reloj = pygame.time.Clock()

        self.ejecutando = True



        # Directorio de assets (relativo a este archivo)

        self.dir_assets = str(Path(__file__).parent)



        # Votos y catálogo filtrado

        self.votos = votos or {}

        self.catalogo = filtrar_catalogo_por_votos(self.votos) if votos else filtrar_catalogo_por_votos({})
        # Filtrar tambien por tecnologias desbloqueadas
        self.catalogo = {k: v for k, v in self.catalogo.items() if self.tecnologia.edificio_desbloqueado(k) or not es_edificio_privado(k)}



        # Componentes del juego

        self.mapa = Mapa(Config.TAMANIO_GRID)

        self.recursos = Recursos()
        self.recursos._juego = self  # Para acceder a tecnologia desde Recursos

        self.camara = Camara(Config.ANCHO_VENTANA, Config.ALTO_VENTANA)

        self.renderizador = Renderizador(self.dir_assets)



        # Estado del juego

        self.edificio_seleccionado: Optional[TipoEdificio] = None

        self.modo_construir = False

        self.modo_vender = False

        self.categoria_actual = "businesses"  # Categoría activa en el panel

        self.tile_hover_x = 0

        self.tile_hover_y = 0

        self.mensaje_error: Optional[str] = None

        self.tiempo_mensaje: float = 0.0

        self.mouse_click = False  # Indica si hubo click este frame



        # Sistema de turnos

        self.mostrando_resumen = False  # Overlay de resumen activo

        self.datos_resumen: Dict[str, int] = {}  # Datos del último turno

        self.historial_finanzas: List[Dict[str, int]] = []  # Últimos 10 turnos

        self.mostrando_finanzas = False  # Panel de finanzas (tecla F)
        self.sistema_colonos = SistemaColonos(self.renderizador, self.mapa)



        # Sistema de permisos (zonificacion) - legacy

        self.mostrando_permiso = False

        self.permiso_tipo: Optional[TipoEdificio] = None

        self.permiso_gx: int = 0

        self.permiso_gy: int = 0        # Sistema de zonificacion por rubros

        self.modo_zonificar = False

        self.zona_seleccionada: Optional[str] = None  # ID del rubro activo

        self.mostrando_info_zona = False

        # Panel de flujo de recursos
        self.panel_flujo = PanelFlujoRecursos(self.renderizador)
        # Mercado inter-colonial
        self.mercado_inter = MercadoInterColonial()
        self.crisis_lunar = CrisisLunar()



        # Estado de manifestaciones
        self.manifestantes: List[Dict] = []  # [{x, y, t_offset, mensaje, ...}]

        # Tutorial interactivo paso a paso

        self.tutorial_activo = True   # Tutorial al inicio

        self.tutorial_paso = 0        # 0=bienvenida, 1-6=pasos, 7=final

        self.tutorial_wasd_hecho = False

        self.tutorial_zoom_hecho = False

        self.tutorial_b_hecho = False

        self.tutorial_click_hecho = False

        self.tutorial_espacio_hecho = False

        self.tutorial_z_hecho = False

        self.mostrando_ayuda = False  # Ayuda estatica con tecla H

        self.ciclo = CicloDiaNoche(Config.ANCHO_VENTANA, Config.ALTO_VENTANA)
        self.tecnologia = ArbolTecnologia()
        self.crisis_lunar.tecnologia = self.tecnologia



        # Cargar sprites de edificios (solo los del catálogo filtrado)

        self._precargar_sprites()
        # ── Colocar carretera central derecha ↔ izquierda ──
        y_medio = Config.TAMANIO_GRID // 2
        tipo_carretera = CATALOGO_EDIFICIOS["road_01"]
        sprite_carretera = self.renderizador.cargar_sprite(tipo_carretera.ruta_sprite, (64, 64))
        for x in range(Config.TAMANIO_GRID):
            if self.mapa.tile_valido(x, y_medio):
                self.mapa.colocar_edificio(x, y_medio, tipo_carretera, sprite_carretera)
        # ── Carteles de la carretera ──
        self.carteles = [
            {"texto": "红月", "grid_x": 0, "grid_y": y_medio, "color": (220, 40, 40)},
            {"texto": "Лунный Город Запад", "grid_x": Config.TAMANIO_GRID - 1, "grid_y": y_medio, "color": (40, 140, 240)},
        ]
        self.fuente_cartel = None
        try:
            # Try system font first (supports Unicode: CJK, Cyrillic, etc.)
            self.fuente_cartel = pygame.font.SysFont("segoeui", 22)
            # Test if it can render Unicode (SysFont on some systems falls back to bitmap)
            test_surf = self.fuente_cartel.render("红", True, (255, 255, 255))
            if test_surf.get_width() < 10:
                raise ValueError("Glyph too narrow, fallback font needed")
        except Exception:
            try:
                # TTF fallbacks with full Unicode support
                import os as _os
                _wf = _os.path.join
                _paths = [
                    _wf("C:", "Windows", "Fonts", "segoeui.ttf"),
                    _wf("C:", "Windows", "Fonts", "msyh.ttc"),
                    _wf("C:", "Windows", "Fonts", "arial.ttf"),
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/TTF/DejaVuSans.ttf",
                ]
                for _fp in _paths:
                    if _os.path.exists(_fp):
                        self.fuente_cartel = pygame.font.Font(_fp, 22)
                        break
                if self.fuente_cartel is None:
                    self.fuente_cartel = pygame.font.Font(None, 22)
            except Exception:
                self.fuente_cartel = pygame.font.Font(None, 22)



    def _precargar_sprites(self) -> None:

        """Carga todos los sprites de edificios del catálogo filtrado en caché."""

        for tipo in self.catalogo.values():

            self.renderizador.cargar_sprite(tipo.ruta_sprite, (64, 64))



    def _obtener_tile_bajo_raton(self) -> Tuple[int, int]:

        """Obtiene las coordenadas del grid bajo el cursor del ratón."""

        mx, my = pygame.mouse.get_pos()

        return self.camara.pantalla_a_iso(mx, my)



    def _mostrar_mensaje(self, texto: str) -> None:

        """Muestra un mensaje temporal en pantalla."""

        self.mensaje_error = texto

        self.tiempo_mensaje = pygame.time.get_ticks()



    def _aprobar_permiso(self) -> None:

        """Aprueba el permiso del comisionado: coloca el edificio privado con coste extra."""

        tipo = self.permiso_tipo

        if not tipo:

            return

        # Tasa burocrática: 25% extra del coste

        tasa = tipo.costo // 4

        coste_total = tipo.costo + tasa

        if self.recursos.creditos >= coste_total:

            if self.mapa.tile_valido(self.permiso_gx, self.permiso_gy, tipo.ancho_tiles, tipo.alto_tiles):

                self.recursos.gastar(coste_total)

                sprite = self.renderizador.cargar_sprite(tipo.ruta_sprite, (64, 64))

                self.mapa.colocar_edificio(self.permiso_gx, self.permiso_gy, tipo, sprite)

                self.recursos.actualizar_balance(self.mapa.edificios)

                tam_txt = "" if tipo.ancho_tiles == 1 and tipo.alto_tiles == 1 else f" ({tipo.ancho_tiles}x{tipo.alto_tiles})"

                self._mostrar_mensaje(f"📋 Permiso aprobado: {tipo.nombre}{tam_txt} (tasa +{tasa}💰)")

                SonidoProcedural.sonido_construir()

            else:

                self._mostrar_mensaje("❌ El terreno ya no está disponible")

        else:

            self._mostrar_mensaje(f"❌ Créditos insuficientes (necesitas {coste_total} 💰, tasa +{tasa})")

        self.mostrando_permiso = False

        self.permiso_tipo = None



    def renderizar_overlay_permiso(self) -> None:

        """Renderiza el overlay de solicitud de permiso para edificios privados."""

        tipo = self.permiso_tipo

        if not tipo:

            return



        pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()

        fondo = pygame.Surface((pant_w, pant_h), pygame.SRCALPHA)

        fondo.fill((0, 0, 0, 180))

        self.pantalla.blit(fondo, (0, 0))



        ancho, alto = 420, 420

        cx, cy = (pant_w - ancho) // 2, (pant_h - alto) // 2

        rect_c = pygame.Rect(cx, cy, ancho, alto)

        pygame.draw.rect(self.pantalla, Config.COLOR_PANEL, rect_c, border_radius=14)

        pygame.draw.rect(self.pantalla, Config.COLOR_PANEL_BORDE, rect_c, 2, border_radius=14)



        r = self.renderizador

        x, y = cx + 30, cy + 20



        # Título

        txt = r.fuente_grande.render("📋 Solicitud de Permiso", True, Config.COLOR_TEXTO_AMARILLO)

        self.pantalla.blit(txt, (x, y))

        y += 48



        # Icono del edificio

        sprite = r.cargar_sprite(tipo.ruta_sprite, (80, 80))

        self.pantalla.blit(sprite, (x, y))



        # Datos del edificio

        dx = x + 100

        txt_nombre = r.fuente_mediana.render(tipo.nombre, True, Config.COLOR_TEXTO)

        self.pantalla.blit(txt_nombre, (dx, y))

        txt_cat = r.fuente_pequenia.render(f"🏛️ {tipo.categoria.replace('_',' ').title()} | 📐 {tipo.ancho_tiles}x{tipo.alto_tiles}", True, Config.COLOR_TEXTO)

        self.pantalla.blit(txt_cat, (dx, y + 28))

        y += 90



        # Descripción

        txt_desc = r.fuente_pequenia.render(f"📝 Actividad: {tipo.descripcion}", True, Config.COLOR_TEXTO)

        self.pantalla.blit(txt_desc, (x, y))

        y += 30



        # Papeles y garantías

        y += 5

        pygame.draw.line(self.pantalla, Config.COLOR_PANEL_BORDE, (x, y), (cx + ancho - 30, y), 1)

        y += 15

        txt_papeles = r.fuente_mediana.render("📄 Papeles y Garantías", True, Config.COLOR_TEXTO_VERDE)

        self.pantalla.blit(txt_papeles, (x, y))

        y += 30



        # Coste

        tasa = tipo.costo // 4

        txt_coste = r.fuente_pequenia.render(f"💰 Coste base: {tipo.costo}  +  Tasa burocrática: +{tasa}  =  TOTAL: {tipo.costo + tasa}", True, Config.COLOR_TEXTO_AMARILLO)

        self.pantalla.blit(txt_coste, (x, y))

        y += 24



        # Requisitos

        reqs = []

        if tipo.produce_energia < 0:

            reqs.append(f"⚡ Consume {abs(tipo.produce_energia)} energía")

        elif tipo.produce_energia > 0:

            reqs.append(f"⚡ Genera {tipo.produce_energia} energía")

        if tipo.produce_oxigeno < 0:

            reqs.append(f"🫁 Consume {abs(tipo.produce_oxigeno)} oxígeno")

        elif tipo.produce_oxigeno > 0:

            reqs.append(f"🫁 Genera {tipo.produce_oxigeno} oxígeno")

        if tipo.produce_agua < 0:

            reqs.append(f"💧 Consume {abs(tipo.produce_agua)} agua")

        elif tipo.produce_agua > 0:

            reqs.append(f"💧 Genera {tipo.produce_agua} agua")

        if tipo.empleos > 0:

            reqs.append(f"👨‍🚀 {tipo.empleos} empleos")

        if tipo.mantenimiento > 0:

            reqs.append(f"🔧 Mantenimiento: {tipo.mantenimiento}/turno")

        for req in reqs:

            txt_req = r.fuente_pequenia.render(req, True, Config.COLOR_TEXTO)

            self.pantalla.blit(txt_req, (x, y))

            y += 22



        # Botones

        y = cy + alto - 55

        btn_aprobar = pygame.Rect(x, y, 160, 38)

        color_ap = Config.COLOR_BOTON

        if btn_aprobar.collidepoint(pygame.mouse.get_pos()):

            color_ap = Config.COLOR_BOTON_HOVER

        pygame.draw.rect(self.pantalla, color_ap, btn_aprobar, border_radius=8)

        txt_ap = r.fuente_mediana.render("✅ APROBAR", True, Config.COLOR_TEXTO_VERDE)

        self.pantalla.blit(txt_ap, (x + 22, y + 7))



        btn_cancelar = pygame.Rect(cx + ancho - 190, y, 160, 38)

        color_cn = Config.COLOR_BOTON

        if btn_cancelar.collidepoint(pygame.mouse.get_pos()):

            color_cn = Config.COLOR_BOTON_HOVER

        pygame.draw.rect(self.pantalla, color_cn, btn_cancelar, border_radius=8)

        txt_cn = r.fuente_mediana.render("❌ CANCELAR", True, Config.COLOR_TEXTO_ROJO)

        self.pantalla.blit(txt_cn, (cx + ancho - 170, y + 7))



    def procesar_siguiente_turno(self) -> None:

        """Avanza un turno: producción, consumo, mantenimiento y crecimiento poblacional."""

        self.recursos.turno += 1
        self.ciclo.avanzar()
        self.tecnologia.actualizar(self.recursos, self.recursos.turno)
        self.mercado_inter.actualizar(self.recursos.turno)
        self.crisis_lunar.actualizar(self.recursos, self.sistema_colonos, self.mapa, self.recursos.turno)
        self.recursos.actualizar_balance(self.mapa.edificios, self.ciclo.es_de_noche)




        # Ajustar por ciclo lunar (noche)
        # --- Calculo de Felicidad ---
        felicidad = Config.FELICIDAD_INICIAL
        suficiencia = 0
        for r_actual, r_total in [
            (self.recursos.energia_total, max(1, abs(self.recursos.energia_total))),
            (self.recursos.oxigeno_total, max(1, abs(self.recursos.oxigeno_total))),
            (self.recursos.agua_total, max(1, abs(self.recursos.agua_total))),
            (self.recursos.presion_total, max(1, abs(self.recursos.presion_total))),
        ]:
            if r_total > 0:
                suficiencia += min(7.5, (r_actual / r_total) * 5)
            elif r_total < -5:
                suficiencia -= 5
            else:
                suficiencia += 3
        felicidad += max(-20, min(30, suficiencia))
        fel_edificios = sum(e.tipo.produce_felicidad for e in self.mapa.edificios if e.activo)
        felicidad += min(25, fel_edificios)
        empleos_calc = sum(e.tipo.empleos for e in self.mapa.edificios if e.activo)
        if self.recursos.poblacion > 0:
            tasa_empleo = min(1.0, empleos_calc / max(1, self.recursos.poblacion * 0.6))
        else:
            tasa_empleo = 0.5
        felicidad += tasa_empleo * 15
        for r_total in [self.recursos.energia_total, self.recursos.oxigeno_total,
                        self.recursos.agua_total, self.recursos.presion_total]:
            if r_total < -10:
                felicidad -= 5
            elif r_total < 0:
                felicidad -= 2
        felicidad = max(Config.FELICIDAD_MIN, min(Config.FELICIDAD_MAX, felicidad))
        self.recursos.felicidad = int(felicidad)
        if felicidad >= Config.FELICIDAD_UMBRAL_CONTENTO:
            self.recursos.bono_produccion = Config.BONUS_FELICIDAD
        elif felicidad < Config.FELICIDAD_UMBRAL_ENOJADO:
            self.recursos.bono_produccion = Config.PENALTY_FELICIDAD
        else:
            self.recursos.bono_produccion = 1.0

        if felicidad < Config.FELICIDAD_UMBRAL_ENOJADO and self.recursos.poblacion >= 5:
            tiles_libres = [(x, y) for y in range(self.mapa.tamanio) for x in range(self.mapa.tamanio) if self.mapa.grid[y][x] is None]
            import random as rnd_h
            rnd_h.shuffle(tiles_libres)
            num_protestas = min(3 + self.recursos.poblacion // 20, len(tiles_libres))
            mensajes_p = ["QUEREMOS AIRE!", "MAS OXIGENO!", "JUSTICIA LUNAR!", "AGUA YA!", "BAJEN IMPUESTOS!", "TRABAJO DIGNO!"]
            self.manifestantes = []
            for i in range(num_protestas):
                tx, ty = tiles_libres[i % len(tiles_libres)]
                self.manifestantes.append({
                    "x": tx, "y": ty,
                    "t_offset": rnd_h.uniform(0, 6.28),
                    "mensaje": rnd_h.choice(mensajes_p),
                    "color_hue": rnd_h.randint(0, 360),
                })
        elif felicidad >= Config.FELICIDAD_UMBRAL_CONTENTO:
            self.manifestantes = []


        if self.ciclo.es_de_noche:

            energia_solar = 0

            for edif in self.mapa.edificios:

                if edif.activo:

                    if edif.tipo.id in ("sol_01", "sol_02", "sol_08"):

                        energia_solar += edif.tipo.produce_energia

                    elif edif.tipo.id == "sol_04":

                        energia_solar += 10  # Baterias liberan energia

            self.recursos.energia_total -= energia_solar

            self.recursos.energia = self.recursos.energia_total



        # Calcular mantenimiento y empleos totales

        mantenimiento_total = 0

        empleos_totales = 0

        for edif in self.mapa.edificios:

            if edif.activo:

                mantenimiento_total += edif.tipo.mantenimiento

                empleos_totales += edif.tipo.empleos



        # ─── Ingresos del turno ───

        # 1. Impuesto progresivo por colono

        if self.recursos.poblacion > 100:

            tasa_impuesto = 8

        elif self.recursos.poblacion > 50:

            tasa_impuesto = 5

        else:

            tasa_impuesto = 3

        impuestos = self.recursos.poblacion * tasa_impuesto



        # 2. Alquileres de edificios activos (fijos + variables por rubro)

        alquileres = 0

        primas_turno = 0

        for edif in self.mapa.edificios:

            if edif.activo:

                alquileres += edif.tipo.alquiler



        # 3. Tasa de visa por visitar y trabajar en LaMoon

        visas = self.recursos.poblacion * 2



        # 4. Auto-settlement: priorizar zonas segun deficits de recursos

        # Calcular prioridad de cada zona basado en deficits criticos
        prioridad = {z: 0 for z in CATALOGO_ZONAS}
        if self.recursos.oxigeno_total < 15:
            prioridad["ecologico"] += 3  # Invernaderos producen O2
        if self.recursos.agua_total < 15:
            prioridad["ecologico"] += 2  # Extractores producen agua
        if self.recursos.felicidad < 40:
            prioridad["comercial"] += 3   # Servicios y ocio aumentan felicidad
        if self.recursos.energia_total > 15:
            prioridad["industrial"] += 2  # Solo expandir industria si hay energia
        if self.recursos.poblacion > empleos_totales * 0.8:
            prioridad["comercial"] += 1
            prioridad["alojamiento"] += 1

        asentamientos = 0
        asentamientos_nombres: List[str] = []
        zonas_ordenadas = sorted(CATALOGO_ZONAS.items(),
                                 key=lambda x: prioridad.get(x[0], 0), reverse=True)
        for zona_id, zona in zonas_ordenadas:
            tiles_libres = self.mapa.tiles_zonificados(zona_id)
            if not tiles_libres:
                continue
            candidatos = edificios_para_zona(zona_id)
            if not candidatos:
                continue
            max_asentamientos = min(2, len(tiles_libres) // 3 + 1)
            score = prioridad.get(zona_id, 0)
            if score >= 3:
                intentos = max_asentamientos  # Prioridad alta: max intentos
            elif score >= 1:
                intentos = random.randint(1, max_asentamientos)
            else:
                intentos = random.randint(0, max_asentamientos)  # Sin deficit: aleatorio

            if asentamientos >= 5:
                break

            for _ in range(intentos):
                if not tiles_libres:
                    break
                gx, gy = random.choice(tiles_libres)
                tiles_libres.remove((gx, gy))
                aid = random.choice(candidatos)
                tipo = CATALOGO_EDIFICIOS[aid]
                if self.mapa.tile_valido(gx, gy, tipo.ancho_tiles, tipo.alto_tiles):
                    sprite = self.renderizador.cargar_sprite(tipo.ruta_sprite, (64, 64))
                    if self.mapa.colocar_edificio(gx, gy, tipo, sprite):
                        prima = random.randint(zona.prima_min, zona.prima_max)
                        primas_turno += prima
                        asentamientos += 1
                        asentamientos_nombres.append(f"{zona.icono} {tipo.nombre} (+{prima}💰)")
                        tiles_libres = self.mapa.tiles_zonificados(zona_id)



        # Inicializar variables de eventos

        evento = None

        costo_evento = 0



        ingresos = impuestos + alquileres + visas + primas_turno

        cambio_creditos = ingresos - mantenimiento_total - costo_evento

        self.recursos.creditos = max(0, self.recursos.creditos + cambio_creditos)



        # Actualizar balance tras asentamientos automaticos

        self.recursos.actualizar_balance(self.mapa.edificios)



        # ─── Eventos aleatorios: caida de aerolitos ───

        tiene_bomberos = any(edif.activo and edif.tipo.id == "misc_10" for edif in self.mapa.edificios)

        tiene_policia = any(edif.activo and edif.tipo.id == "misc_11" for edif in self.mapa.edificios)

        proteccion = (1 if tiene_bomberos else 0) + (1 if tiene_policia else 0)



        if self.mapa.edificios and random.random() < 0.10:

            objetivo = random.choice(self.mapa.edificios)

            if objetivo.activo and objetivo.tipo.id not in ("misc_10", "misc_11"):

                severidad = random.randint(1, 3)

                if proteccion >= 1 and random.random() < 0.5 * proteccion:

                    evento = f"🌠 ¡Aerolito detectado! {objetivo.tipo.nombre} protegido por servicios de emergencia."

                else:

                    dano = objetivo.tipo.costo * severidad // 4

                    costo_evento = dano

                    objetivo.activo = False

                    evento = f"☄️ ¡IMPACTO de aerolito en {objetivo.tipo.nombre}! Daño: -{dano}💰. Requiere reparación."



        # ─── Evento: Tormenta solar (daña paneles solares) ───

        if not evento and random.random() < 0.10:

            solares = [e for e in self.mapa.edificios if e.activo and e.tipo.categoria == "solar_energy"]

            if solares:

                objetivo = random.choice(solares)

                dano = objetivo.tipo.costo // 5

                costo_evento = dano

                objetivo.activo = False

                evento = f"🌞 ¡Tormenta solar! {objetivo.tipo.nombre} dañado. -{dano}💰. Requiere reparación."



        # ─── Evento: Auge turístico (bonus de visas) ───

        if not evento and random.random() < 0.12 and self.recursos.poblacion > 15:

            bonus = random.randint(30, 80)

            self.recursos.ingresar(bonus)

            evento = f"🎉 ¡Auge turístico! Visitantes VIP gastan +{bonus}💰 en la colonia."



        # ─── Evento: Sabotaje industrial ───

        if not evento and random.random() < 0.08 and not tiene_policia:

            industriales = [e for e in self.mapa.edificios if e.activo and e.tipo.categoria == "businesses"]

            if industriales:

                objetivo = random.choice(industriales)

                dano = objetivo.tipo.costo // 6

                costo_evento = dano

                objetivo.activo = False

                evento = f"💥 ¡Sabotaje industrial en {objetivo.tipo.nombre}! Policía investiga. -{dano}💰."



        # ─── Evento: Inspectores de la Tierra ───

        if not evento and random.random() < 0.10 and self.recursos.poblacion > 20:

            if self.recursos.energia_total > 0 and self.recursos.oxigeno_total > 0:

                bonus = random.randint(20, 60)

                self.recursos.ingresar(bonus)

                evento = f"🛸 ¡Inspectores de la Tierra aprueban la colonia! Subvención +{bonus}💰."

            else:

                multa = random.randint(100, 300)

                costo_evento = multa

                evento = f"⚠️ ¡Inspectores de la Tierra imponen multa! -{multa}💰 por déficit de recursos."



        # Evaluar deficits vitales

        deficit_count = 0

        if self.recursos.energia_total < 0:

            deficit_count += 1

        if self.recursos.oxigeno_total < 0:

            deficit_count += 1

        if self.recursos.agua_total < 0:

            deficit_count += 1



        pob_anterior = self.recursos.poblacion



        # Crecimiento / decrecimiento poblacional

        if deficit_count > 0:

            # Colapso: la población huye si faltan recursos vitales

            mortalidad = int(self.recursos.poblacion * (0.15 * deficit_count)) + 1

            self.recursos.poblacion = max(0, self.recursos.poblacion - mortalidad)

        else:

            # Sin déficits: la población crece hacia los empleos disponibles

            if self.recursos.poblacion < empleos_totales:

                crecimiento = max(1, int((empleos_totales - self.recursos.poblacion) * 0.2))

                self.recursos.poblacion += crecimiento

            elif self.recursos.poblacion > empleos_totales and self.recursos.poblacion > 10:

                # Desempleo: emigración lenta

                emigracion = max(1, int((self.recursos.poblacion - empleos_totales) * 0.05))

                self.recursos.poblacion -= emigracion



        cambio_pob = self.recursos.poblacion - pob_anterior



        # Guardar datos para el overlay

        self.datos_resumen = {

            "turno": self.recursos.turno,

            "creditos": cambio_creditos,

            "impuestos": impuestos,

            "tasa_impuesto": tasa_impuesto,

            "alquileres": alquileres,

            "visas": visas,

            "primas": primas_turno,

            "asentamientos": asentamientos,

            "asentamientos_nombres": asentamientos_nombres,

            "evento": evento,

            "costo_dano": costo_evento,

            "mantenimiento": mantenimiento_total,

            "energia": self.recursos.energia_total,

            "oxigeno": self.recursos.oxigeno_total,

            "agua": self.recursos.agua_total,

            "presion": self.recursos.presion_total,

            "felicidad": self.recursos.felicidad,
            "bono": self.recursos.bono_produccion,
            "es_noche": self.ciclo.es_de_noche,

            "poblacion": cambio_pob,

            "empleos": empleos_totales,

            "deficits": deficit_count,

        }

        self.mostrando_resumen = True



        # Guardar en historial de finanzas (últimos 10 turnos)

        self.historial_finanzas.append(dict(self.datos_resumen))

        if len(self.historial_finanzas) > 10:

            self.historial_finanzas.pop(0)



    def renderizar_overlay_resumen(self) -> None:

        """Renderiza el overlay de resumen post-turno."""

        d = self.datos_resumen

        if not d:

            return



        # Capa oscura semitransparente

        pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()

        fondo = pygame.Surface((pant_w, pant_h), pygame.SRCALPHA)

        fondo.fill((0, 0, 0, 180))

        self.pantalla.blit(fondo, (0, 0))



        # Cuadro central

        ancho, alto = 460, 540

        cx, cy = (pant_w - ancho) // 2, (pant_h - alto) // 2

        rect_c = pygame.Rect(cx, cy, ancho, alto)

        pygame.draw.rect(self.pantalla, Config.COLOR_PANEL, rect_c, border_radius=14)

        pygame.draw.rect(self.pantalla, Config.COLOR_PANEL_BORDE, rect_c, 2, border_radius=14)



        r = self.renderizador

        x, y = cx + 30, cy + 25



        # Título

        txt = r.fuente_grande.render(f"📋 Resumen del Turno {d['turno']}", True, Config.COLOR_TEXTO)

        self.pantalla.blit(txt, (x, y))

        y += 50



        # Datos del resumen

        def _linea(icono, texto, valor, color, fmt=None):

            nonlocal y

            if fmt:

                txt = r.fuente_mediana.render(f"{icono} {texto}: {fmt}", True, color)

            elif isinstance(valor, int) and valor != 0:

                txt = r.fuente_mediana.render(f"{icono} {texto}: {valor:+d}", True, color)

            else:

                txt = r.fuente_mediana.render(f"{icono} {texto}: {valor}", True, color)

            self.pantalla.blit(txt, (x, y))

            y += 32



        # ── Ingresos detallados ──

        _linea("💰", f"Impuestos ({d.get('tasa_impuesto', 3)}/colono)", d.get("impuestos", 0), Config.COLOR_TEXTO_VERDE)

        _linea("🏠", "Alquileres mensuales", d.get("alquileres", 0), Config.COLOR_TEXTO_VERDE)

        _linea("🛂", "Tasa de visa LaMoon", d.get("visas", 0), Config.COLOR_TEXTO_VERDE)

        primas_val = d.get("primas", 0)

        asentamientos_count = d.get("asentamientos", 0)

        if primas_val > 0:

            _linea("📋", f"Primas asentamientos ({asentamientos_count} nuevos)", primas_val, Config.COLOR_TEXTO_VERDE)

        asentamientos_nombres = d.get("asentamientos_nombres", [])

        if asentamientos_nombres:

            for nombre in asentamientos_nombres[:4]:

                txt_n = r.fuente_pequenia.render(f"   {nombre}", True, Config.COLOR_TEXTO)

                self.pantalla.blit(txt_n, (x, y))

                y += 18

            if len(asentamientos_nombres) > 4:

                txt_mas = r.fuente_pequenia.render(f"   ...y {len(asentamientos_nombres)-4} mas", True, Config.COLOR_TEXTO)

                self.pantalla.blit(txt_mas, (x, y))

                y += 18

        _linea("🔧", "Mantenimiento", d.get("mantenimiento", 0), Config.COLOR_TEXTO_ROJO, fmt=f"-{d.get('mantenimiento', 0)}")



        y += 2

        pygame.draw.line(self.pantalla, Config.COLOR_PANEL_BORDE, (x, y), (cx + ancho - 30, y), 1)

        y += 8



        # Balance neto

        color_cred = Config.COLOR_TEXTO_VERDE if d["creditos"] >= 0 else Config.COLOR_TEXTO_ROJO

        _linea("💰", "Balance Neto", d["creditos"], color_cred)



        # Daño por aerolito (si hubo)

        costo_dano = d.get("costo_dano", 0)

        if costo_dano > 0:

            _linea("☄️", "Daño por aerolito", costo_dano, Config.COLOR_TEXTO_ROJO, fmt=f"-{costo_dano}")



        # Energía

        color_en = Config.COLOR_TEXTO_VERDE if d["energia"] >= 0 else Config.COLOR_TEXTO_ROJO

        tag_en = "✅" if d["energia"] >= 0 else "⚠️ DÉFICIT"

        _linea("⚡", f"Capacidad Energía {tag_en}", d["energia"], color_en)



        # Oxígeno

        color_ox = Config.COLOR_TEXTO_VERDE if d["oxigeno"] >= 0 else Config.COLOR_TEXTO_ROJO

        tag_ox = "✅" if d["oxigeno"] >= 0 else "⚠️ DÉFICIT"

        _linea("🫁", f"Capacidad Oxígeno {tag_ox}", d["oxigeno"], color_ox)



        # Agua

        color_ag = Config.COLOR_TEXTO_VERDE if d["agua"] >= 0 else Config.COLOR_TEXTO_ROJO

        tag_ag = "✅" if d["agua"] >= 0 else "⚠️ DÉFICIT"

        _linea("💧", f"Capacidad Agua {tag_ag}", d["agua"], color_ag)



        # Presión

        if "presion" in d:

            color_pr = Config.COLOR_TEXTO_VERDE if d["presion"] >= 0 else Config.COLOR_TEXTO_ROJO

            tag_pr = "✅" if d["presion"] >= 0 else "⚠️ DÉFICIT"

            _linea("💨", f"Capacidad Presión {tag_pr}", d["presion"], color_pr)



        # Población

        color_pob = Config.COLOR_TEXTO_VERDE if d["poblacion"] >= 0 else Config.COLOR_TEXTO_ROJO

        _linea("👨‍🚀", "Migración Población", d["poblacion"], color_pob)



        # Empleos

        _linea("🔧", "Empleos Totales", d["empleos"], Config.COLOR_TEXTO)



        # Evento aleatorio (si ocurrio)

        evento = d.get("evento")

        if evento:

            y += 6

            txt_ev = r.fuente_pequenia.render(evento, True, Config.COLOR_TEXTO_ROJO)

            self.pantalla.blit(txt_ev, (x, y))

            y += 22



        # Población actual

        y += 10

        txt_pob = r.fuente_mediana.render(f"👨‍🚀 Población actual: {self.recursos.poblacion}", True, Config.COLOR_TEXTO_AMARILLO)

        self.pantalla.blit(txt_pob, (x, y))

        y += 30

        # Estado del ciclo lunar

        if "es_noche" in d:

            ciclo_estado = "🌙 Noche" if d["es_noche"] else "☀️ Día"

            txt_ciclo = r.fuente_pequenia.render(f"{ciclo_estado} lunar (turno {self.ciclo.turno_actual + 1}/{Config.DIAS_NOCHE if d['es_noche'] else Config.DIAS_LUZ})", True, Config.COLOR_TEXTO)

            self.pantalla.blit(txt_ciclo, (x, y))

        y += 40



        # Botón CERRAR

        btn_ok_rect = pygame.Rect(cx + ancho // 2 - 70, cy + alto - 55, 140, 38)

        color_ok = Config.COLOR_BOTON

        if btn_ok_rect.collidepoint(pygame.mouse.get_pos()):

            color_ok = Config.COLOR_BOTON_HOVER

        pygame.draw.rect(self.pantalla, color_ok, btn_ok_rect, border_radius=8)

        txt_ok = r.fuente_mediana.render("✅ CERRAR", True, Config.COLOR_TEXTO_VERDE)

        self.pantalla.blit(txt_ok, (btn_ok_rect.x + 30, btn_ok_rect.y + 7))



    def renderizar_panel_finanzas(self) -> None:

        """Renderiza el panel de finanzas con historial de los últimos 10 turnos."""

        pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()

        fondo = pygame.Surface((pant_w, pant_h), pygame.SRCALPHA)

        fondo.fill((0, 0, 0, 180))

        self.pantalla.blit(fondo, (0, 0))



        ancho, alto = 700, 480

        cx, cy = (pant_w - ancho) // 2, (pant_h - alto) // 2

        rect_c = pygame.Rect(cx, cy, ancho, alto)

        pygame.draw.rect(self.pantalla, Config.COLOR_PANEL, rect_c, border_radius=14)

        pygame.draw.rect(self.pantalla, Config.COLOR_PANEL_BORDE, rect_c, 2, border_radius=14)



        r = self.renderizador

        x, y = cx + 25, cy + 18



        # Título

        txt = r.fuente_grande.render("📊 Finanzas — Últimos Turnos", True, Config.COLOR_TEXTO_AMARILLO)

        self.pantalla.blit(txt, (x, y))

        y += 40



        # Leyenda

        txt_ley = r.fuente_pequenia.render("🟢 Impuestos  🟡 Alquileres  🔵 Visas  🔴 Mantenimiento (barras: 1 char = 10💰)", True, Config.COLOR_TEXTO)

        self.pantalla.blit(txt_ley, (x, y))

        y += 30



        if not self.historial_finanzas:

            txt_vacio = r.fuente_mediana.render("Sin datos aún. ¡Avanza algunos turnos!", True, Config.COLOR_TEXTO)

            self.pantalla.blit(txt_vacio, (x, y + 20))

            y += 60

        else:

            # Encontrar el valor máximo para escalar las barras (solo ingresos)

            max_val = 1

            for h in self.historial_finanzas:

                for k in ["impuestos", "alquileres", "visas"]:

                    max_val = max(max_val, h.get(k, 0))

            escala = max(1, max_val // 40)  # 40 chars max



            # Barras por turno

            bar_x = x + 100

            for i, h in enumerate(self.historial_finanzas):

                turno = h.get("turno", i + 1)

                imp = h.get("impuestos", 0)

                alq = h.get("alquileres", 0)

                vis = h.get("visas", 0)

                man = h.get("mantenimiento", 0)

                neto = h.get("creditos", 0)



                # Etiqueta del turno

                txt_t = r.fuente_pequenia.render(f"T{turno}", True, Config.COLOR_TEXTO)

                self.pantalla.blit(txt_t, (x, y + 4))



                # Barras horizontales apiladas

                bw_imp = max(1, imp // escala)

                bw_alq = max(0, alq // escala)

                bw_vis = max(0, vis // escala)

                bw_man = max(1, man // escala)



                bar_h = 21

                # Impuestos (verde)

                pygame.draw.rect(self.pantalla, (0, 180, 100), (bar_x, y, bw_imp * 6, bar_h), border_radius=2)

                # Alquileres (amarillo)

                if alq > 0:

                    pygame.draw.rect(self.pantalla, (220, 180, 40), (bar_x + bw_imp * 6, y, bw_alq * 6, bar_h), border_radius=2)

                # Visas (azul)

                if vis > 0:

                    pygame.draw.rect(self.pantalla, (60, 150, 220), (bar_x + (bw_imp + bw_alq) * 6, y, bw_vis * 6, bar_h), border_radius=2)

                # Mantenimiento (rojo, desde la derecha hacia atrás)

                if man > 0:

                    man_x = bar_x + (bw_imp + bw_alq + bw_vis) * 6 + 4

                    pygame.draw.rect(self.pantalla, (200, 60, 60), (man_x, y, bw_man * 6, bar_h), border_radius=2)



                # Neto

                color_neto = Config.COLOR_TEXTO_VERDE if neto >= 0 else Config.COLOR_TEXTO_ROJO

                txt_neto = r.fuente_pequenia.render(f"Neto: {neto:+d}", True, color_neto)

                self.pantalla.blit(txt_neto, (bar_x + 260, y + 3))



                y += bar_h + 4



            # Tabla resumen

            y += 8

            pygame.draw.line(self.pantalla, Config.COLOR_PANEL_BORDE, (x, y), (cx + ancho - 25, y), 1)

            y += 10



            # Calcular promedios

            n = len(self.historial_finanzas)

            prom_imp = sum(h.get("impuestos", 0) for h in self.historial_finanzas) // n

            prom_alq = sum(h.get("alquileres", 0) for h in self.historial_finanzas) // n

            prom_vis = sum(h.get("visas", 0) for h in self.historial_finanzas) // n

            prom_man = sum(h.get("mantenimiento", 0) for h in self.historial_finanzas) // n

            prom_neto = sum(h.get("creditos", 0) for h in self.historial_finanzas) // n



            encabezados = ["", "Impuestos", "Alquileres", "Visas", "Manten.", "Neto"]

            valores = ["Promedio", f"{prom_imp}", f"{prom_alq}", f"{prom_vis}", f"{prom_man}", f"{prom_neto:+d}"]



            col_xs = [x, x + 100, x + 200, x + 300, x + 400, x + 500]

            for i, (enc, val) in enumerate(zip(encabezados, valores)):

                color = Config.COLOR_TEXTO_AMARILLO if i == 0 else Config.COLOR_TEXTO

                txt_enc = r.fuente_pequenia.render(enc, True, color)

                self.pantalla.blit(txt_enc, (col_xs[i], y + 2))



                color_val = Config.COLOR_TEXTO_VERDE if (i == 5 and prom_neto >= 0) else (Config.COLOR_TEXTO_ROJO if i == 5 else Config.COLOR_TEXTO)

                txt_val = r.fuente_pequenia.render(val, True, color_val)

                self.pantalla.blit(txt_val, (col_xs[i], y + 20))



        # Botón CERRAR

        btn_ok_rect = pygame.Rect(cx + ancho // 2 - 60, cy + alto - 45, 120, 35)

        color_ok = Config.COLOR_BOTON

        if btn_ok_rect.collidepoint(pygame.mouse.get_pos()):

            color_ok = Config.COLOR_BOTON_HOVER

        pygame.draw.rect(self.pantalla, color_ok, btn_ok_rect, border_radius=8)

        txt_ok = r.fuente_mediana.render("F: CERRAR", True, Config.COLOR_TEXTO_VERDE)

        self.pantalla.blit(txt_ok, (btn_ok_rect.x + 12, btn_ok_rect.y + 6))



    def manejar_eventos(self) -> None:
        """Procesa todos los eventos de entrada."""
        mouse_pos = pygame.mouse.get_pos()
        self.mouse_click = False  # Resetear flag de click

        for evento in pygame.event.get():
            # ── Cerrar overlays con ESC ──
            if self.mostrando_resumen or self.mostrando_permiso or self.mostrando_finanzas:
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    if self.tutorial_activo and self.tutorial_paso == 0:
                        self.tutorial_paso = 1
                    elif self.tutorial_activo and self.tutorial_paso >= 7:
                        self.tutorial_activo = False
                        self.tutorial_paso = 0

            # ── Click handling for overlays ──
            if self.mostrando_resumen:
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()
                    # Boton CERRAR de finanzas
                    if self.mostrando_finanzas:
                        ancho_f, alto_f = 700, 480
                        cx_f, cy_f = (pant_w - ancho_f) // 2, (pant_h - alto_f) // 2
                        btn_fin = pygame.Rect(cx_f + ancho_f // 2 - 60, cy_f + alto_f - 45, 120, 35)
                        if btn_fin.collidepoint(evento.pos):
                            self.mostrando_finanzas = False
                    # Boton CERRAR del resumen + permisos
                    ancho, alto = 460, 540
                    cx, cy = (pant_w - ancho) // 2, (pant_h - alto) // 2
                    if self.mostrando_resumen:
                        btn_ok = pygame.Rect(cx + ancho // 2 - 70, cy + alto - 55, 140, 38)
                        if btn_ok.collidepoint(evento.pos):
                            self.mostrando_resumen = False
                    if self.mostrando_permiso:
                        btn_aprobar = pygame.Rect(cx + 30, cy + alto - 55, 160, 38)
                        btn_cancelar = pygame.Rect(cx + ancho - 190, cy + alto - 55, 160, 38)
                        if btn_aprobar.collidepoint(evento.pos):
                            self._aprobar_permiso()
                        elif btn_cancelar.collidepoint(evento.pos):
                            self.mostrando_permiso = False

            # ── KEY HANDLING ──
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    if self.tutorial_activo and self.tutorial_paso == 0:
                        self.tutorial_paso = 1
                    else:
                        self.ejecutando = False
                elif evento.key == pygame.K_b:
                    self.modo_construir = not self.modo_construir
                    self.modo_vender = False
                    if self.tutorial_activo and self.tutorial_paso == 6:
                        self.tutorial_z_hecho = True
                        self.tutorial_paso = 7
                    if not self.modo_construir:
                        self.edificio_seleccionado = None
                elif evento.key == pygame.K_v:
                    self.modo_vender = not self.modo_vender
                    self.modo_construir = False
                    self.edificio_seleccionado = None
                    if self.tutorial_activo and self.tutorial_paso == 3:
                        self.tutorial_b_hecho = True
                        self.tutorial_paso = 4
                elif evento.key == pygame.K_h:
                    if self.tutorial_activo:
                        self.tutorial_activo = False
                        self.mostrando_ayuda = True
                    else:
                        self.mostrando_ayuda = not self.mostrando_ayuda
                elif evento.key in (pygame.K_w, pygame.K_UP):
                    self.camara.mover(0, -1)
                    if self.tutorial_activo and self.tutorial_paso == 1:
                        self.tutorial_paso = 2
                elif evento.key in (pygame.K_s, pygame.K_DOWN):
                    self.camara.mover(0, 1)
                    if self.tutorial_activo and self.tutorial_paso == 1:
                        self.tutorial_paso = 2
                elif evento.key in (pygame.K_a, pygame.K_LEFT):
                    self.camara.mover(-1, 0)
                    if self.tutorial_activo and self.tutorial_paso == 1:
                        self.tutorial_paso = 2
                elif evento.key in (pygame.K_d, pygame.K_RIGHT):
                    self.camara.mover(1, 0)
                    if self.tutorial_activo and self.tutorial_paso == 1:
                        self.tutorial_paso = 2
                elif evento.key == pygame.K_SPACE:
                    if self.tutorial_activo and self.tutorial_paso == 0:
                        self.tutorial_paso = 1
                    elif self.tutorial_activo and self.tutorial_paso == 5:
                        self.tutorial_espacio_hecho = True
                        self.tutorial_paso = 6
                    else:
                        if not self.mostrando_resumen:
                            self.procesar_siguiente_turno()
                        else:
                            self.mostrando_resumen = False
                        SonidoProcedural.sonido_turno()
                elif evento.key == pygame.K_f:
                    self.mostrando_finanzas = not self.mostrando_finanzas
                elif evento.key == pygame.K_r:
                    self.panel_flujo.visible = not self.panel_flujo.visible
                    if self.panel_flujo.visible:
                        self.panel_flujo.frames = 29
                elif evento.key == pygame.K_z:
                    self.modo_zonificar = not self.modo_zonificar
                    self.modo_construir = False
                    self.modo_vender = False
                    self.edificio_seleccionado = None
                    self.zona_seleccionada = None
                    if self.tutorial_activo and self.tutorial_paso == 2:
                        self.tutorial_paso = 3
                    self.mercado_inter.visible = not self.mercado_inter.visible

                elif evento.key == pygame.K_m:
                    self.mercado_inter.visible = not self.mercado_inter.visible

                elif evento.key == pygame.K_t:
                    self.tecnologia.visible = not self.tecnologia.visible
            # ── MOUSE HANDLING ──
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self.mouse_click = True
                if self.modo_construir and self.edificio_seleccionado:
                    gx, gy = self.camara.pantalla_a_iso(*evento.pos)
                    tipo = self.edificio_seleccionado
                    if not self.mapa.tile_valido(gx, gy, tipo.ancho_tiles, tipo.alto_tiles):
                        self._mostrar_mensaje("No hay espacio suficiente aqui")
                        SonidoProcedural.sonido_error()
                    elif self.recursos.creditos < tipo.costo:
                        self._mostrar_mensaje(f"Creditos insuficientes ({tipo.costo} necesarios)")
                        SonidoProcedural.sonido_error()
                    elif es_edificio_privado(tipo.id):
                        self.permiso_tipo = tipo
                        self.permiso_gx = gx
                        self.permiso_gy = gy
                        self.mostrando_permiso = True
                    else:
                        sprite = self.renderizador.cargar_sprite(tipo.ruta_sprite, (64, 64))
                        if self.mapa.colocar_edificio(gx, gy, tipo, sprite):
                            self.recursos.gastar(tipo.costo)
                            self.recursos.actualizar_balance(self.mapa.edificios)
                            SonidoProcedural.sonido_construir()
                            if self.tutorial_activo and self.tutorial_paso == 4:
                                self.tutorial_click_hecho = True
                                self.tutorial_paso = 5
                        else:
                            self._mostrar_mensaje("No se puede colocar aqui")
                            SonidoProcedural.sonido_error()
                elif self.modo_vender:
                    gx, gy = self.camara.pantalla_a_iso(*evento.pos)
                    if self.mapa.esta_ocupado(gx, gy):
                        edificio = self.mapa.vender_edificio(gx, gy)
                        if edificio:
                            reembolso = int(edificio.tipo.costo * 0.5)
                            self.recursos.ingresar(reembolso)
                            self.recursos.actualizar_balance(self.mapa.edificios)
                            self._mostrar_mensaje(f"Vendido: {edificio.tipo.nombre} (+{reembolso})")
                            SonidoProcedural.sonido_construir()
                elif self.modo_zonificar and self.zona_seleccionada:
                    gx, gy = self.camara.pantalla_a_iso(*evento.pos)
                    if self.mapa.pintar_zona(gx, gy, self.zona_seleccionada):
                        self._mostrar_mensaje(f"Zona pintada: {CATALOGO_ZONAS[self.zona_seleccionada].nombre}")
                    else:
                        self._mostrar_mensaje("No se puede zonificar aqui")

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 3:
                if self.modo_construir:
                    self.modo_construir = False
                    self.edificio_seleccionado = None
                    self._mostrar_mensaje("Construccion cancelada")
                elif self.modo_vender:
                    self.modo_vender = False
                    self._mostrar_mensaje("Modo vender desactivado")

            elif evento.type == pygame.MOUSEWHEEL:
                self.camara.acercar(evento.y * 0.1)

            elif evento.type == pygame.VIDEORESIZE:
                self.camara.ancho_ventana = evento.w
                self.camara.alto_ventana = evento.h

            elif evento.type == pygame.QUIT:
                self.ejecutando = False

        # ── Overlay rendering (outside loop, once per frame) ──
        # UI indicador dia/noche
        self.ciclo.renderizar_ui(self.pantalla, self.renderizador, Config.ANCHO_VENTANA)

        if self.tutorial_activo:
            self.renderizar_tutorial()
        if self.mostrando_ayuda:
            self.renderizar_ayuda_estatica()


    def actualizar(self) -> None:

        """Actualiza la lógica del juego cada frame."""

        self.tile_hover_x, self.tile_hover_y = self._obtener_tile_bajo_raton()
        self.ciclo.actualizar()
        self.sistema_colonos.actualizar(self.recursos, self.recursos.poblacion, self.ciclo.es_de_noche)



    def _renderizar_manifestantes(self) -> None:
        try:
            ahora = pygame.time.get_ticks() / 1000.0
            tam = int(Config.TAMANIO_TILE * self.camara.zoom)
            r = self.renderizador
            for m in self.manifestantes:
                if not self.camara:
                    continue
                px, py = self.camara.iso_a_pantalla(m["x"], m["y"])
                if px < -tam or px > self.pantalla.get_width() + tam:
                    continue
                if py < -tam or py > self.pantalla.get_height() + tam:
                    continue
                flotar = math.sin(ahora * 1.5 + m["t_offset"]) * 12
                balanceo = math.sin(ahora * 0.8 + m["t_offset"]) * 4
                hue = m["color_hue"]
                r_col = min(255, hue % 360 // 2 + 30)
                g_col = min(255, (hue * 7) % 200 + 40)
                b_col = min(255, (hue * 3) % 200 + 100)
                cx_px = int(px + balanceo)
                cy_px = int(py - tam // 4 + flotar - 10)
                pygame.draw.ellipse(self.pantalla, (r_col, g_col, b_col), (cx_px - 8, cy_px - 20, 16, 24))
                pygame.draw.circle(self.pantalla, (200, 210, 220), (cx_px, cy_px - 28), 8)
                pygame.draw.circle(self.pantalla, (160, 180, 200), (cx_px, cy_px - 28), 8, 2)
                pygame.draw.ellipse(self.pantalla, (120, 200, 255), (cx_px - 5, cy_px - 32, 10, 7))
                cartel_x = cx_px + 14
                cartel_y = cy_px - 32
                pygame.draw.line(self.pantalla, (180, 150, 100), (cartel_x, cartel_y + 40), (cartel_x, cartel_y - 10), 2)
                lineas = m["mensaje"].split("\n")
                alto_cartel = len(lineas) * 14 + 8
                ancho_cartel = max((len(l) for l in lineas), default=10) * 7 + 8
                cartel_surf = pygame.Surface((ancho_cartel, alto_cartel), pygame.SRCALPHA)
                cartel_surf.fill((230, 80, 80, 220))
                pygame.draw.rect(cartel_surf, (200, 50, 50), (0, 0, ancho_cartel, alto_cartel), 2)
                for i, linea in enumerate(lineas):
                    txt = r.fuente_pequenia.render(linea.strip(), True, (255, 255, 255))
                    cartel_surf.blit(txt, (4, 4 + i * 14))
                self.pantalla.blit(cartel_surf, (cartel_x - ancho_cartel // 2, cartel_y + flotar * 0.5 + 10))
                exc_txt = r.fuente_grande.render(chr(9888), True, (255, 80, 80))
                exc_alpha = int(abs(math.sin(ahora * 3 + m["t_offset"])) * 200 + 55)
                exc_txt.set_alpha(exc_alpha)
                self.pantalla.blit(exc_txt, (cx_px - 18, cy_px - 60 + flotar * 0.3))
        except Exception:
            pass

    def _renderizar_manifestantes(self) -> None:
        try:
            ahora = pygame.time.get_ticks() / 1000.0
            tam = int(Config.TAMANIO_TILE * self.camara.zoom)
            r = self.renderizador
            for m in self.manifestantes:
                px, py = self.camara.iso_a_pantalla(m["x"], m["y"])
                if px < -tam or px > self.pantalla.get_width() + tam:
                    continue
                if py < -tam or py > self.pantalla.get_height() + tam:
                    continue
                flotar = math.sin(ahora * 1.5 + m["t_offset"]) * 12
                balanceo = math.sin(ahora * 0.8 + m["t_offset"]) * 4
                hue = m["color_hue"]
                r_col = min(255, hue % 360 // 2 + 30)
                g_col = min(255, (hue * 7) % 200 + 40)
                b_col = min(255, (hue * 3) % 200 + 100)
                cx_px = int(px + balanceo)
                cy_px = int(py - tam // 4 + flotar - 10)
                pygame.draw.ellipse(self.pantalla, (r_col, g_col, b_col), (cx_px - 8, cy_px - 20, 16, 24))
                pygame.draw.circle(self.pantalla, (200, 210, 220), (cx_px, cy_px - 28), 8)
                pygame.draw.circle(self.pantalla, (160, 180, 200), (cx_px, cy_px - 28), 8, 2)
                pygame.draw.ellipse(self.pantalla, (120, 200, 255), (cx_px - 5, cy_px - 32, 10, 7))
                cartel_x = cx_px + 14
                cartel_y = cy_px - 32
                pygame.draw.line(self.pantalla, (180, 150, 100), (cartel_x, cartel_y + 40), (cartel_x, cartel_y - 10), 2)
                lineas = m["mensaje"].split(chr(92) + "n")  # backslash-n line split
                alto_cartel = len(lineas) * 14 + 8
                ancho_cartel = max((len(l) for l in lineas), default=10) * 7 + 8
                cartel_surf = pygame.Surface((ancho_cartel, alto_cartel), pygame.SRCALPHA)
                cartel_surf.fill((230, 80, 80, 220))
                pygame.draw.rect(cartel_surf, (200, 50, 50), (0, 0, ancho_cartel, alto_cartel), 2)
                for i, linea in enumerate(lineas):
                    txt = r.fuente_pequenia.render(linea.strip(), True, (255, 255, 255))
                    cartel_surf.blit(txt, (4, 4 + i * 14))
                self.pantalla.blit(cartel_surf, (cartel_x - ancho_cartel // 2, cartel_y + flotar * 0.5 + 10))
                exc_txt = r.fuente_grande.render(chr(9888), True, (255, 80, 80))
                exc_alpha = int(abs(math.sin(ahora * 3 + m["t_offset"])) * 200 + 55)
                exc_txt.set_alpha(exc_alpha)
                self.pantalla.blit(exc_txt, (cx_px - 18, cy_px - 60 + flotar * 0.3))
        except Exception:
            pass

    def _renderizar_manifestantes(self) -> None:
        try:
            ahora = pygame.time.get_ticks() / 1000.0
            tam = int(Config.TAMANIO_TILE * self.camara.zoom)
            r = self.renderizador
            for m in self.manifestantes:
                px, py = self.camara.iso_a_pantalla(m["x"], m["y"])
                if px < -tam or px > self.pantalla.get_width() + tam:
                    continue
                if py < -tam or py > self.pantalla.get_height() + tam:
                    continue
                flotar = math.sin(ahora * 1.5 + m["t_offset"]) * 12
                balanceo = math.sin(ahora * 0.8 + m["t_offset"]) * 4
                hue = m["color_hue"]
                r_col = min(255, hue % 360 // 2 + 30)
                g_col = min(255, (hue * 7) % 200 + 40)
                b_col = min(255, (hue * 3) % 200 + 100)
                cx_px = int(px + balanceo)
                cy_px = int(py - tam // 4 + flotar - 10)
                pygame.draw.ellipse(self.pantalla, (r_col, g_col, b_col), (cx_px - 8, cy_px - 20, 16, 24))
                pygame.draw.circle(self.pantalla, (200, 210, 220), (cx_px, cy_px - 28), 8)
                pygame.draw.circle(self.pantalla, (160, 180, 200), (cx_px, cy_px - 28), 8, 2)
                pygame.draw.ellipse(self.pantalla, (120, 200, 255), (cx_px - 5, cy_px - 32, 10, 7))
                cartel_x = cx_px + 14
                cartel_y = cy_px - 32
                pygame.draw.line(self.pantalla, (180, 150, 100), (cartel_x, cartel_y + 40), (cartel_x, cartel_y - 10), 2)
                lineas = m["mensaje"].split("\\n")
                alto_cartel = len(lineas) * 14 + 8
                ancho_cartel = max((len(l) for l in lineas), default=10) * 7 + 8
                cartel_surf = pygame.Surface((ancho_cartel, alto_cartel), pygame.SRCALPHA)
                cartel_surf.fill((230, 80, 80, 220))
                pygame.draw.rect(cartel_surf, (200, 50, 50), (0, 0, ancho_cartel, alto_cartel), 2)
                for i, linea in enumerate(lineas):
                    txt = r.fuente_pequenia.render(linea.strip(), True, (255, 255, 255))
                    cartel_surf.blit(txt, (4, 4 + i * 14))
                self.pantalla.blit(cartel_surf, (cartel_x - ancho_cartel // 2, cartel_y + flotar * 0.5 + 10))
                exc_txt = r.fuente_grande.render(chr(9888), True, (255, 80, 80))
                exc_alpha = int(abs(math.sin(ahora * 3 + m["t_offset"])) * 200 + 55)
                exc_txt.set_alpha(exc_alpha)
                self.pantalla.blit(exc_txt, (cx_px - 18, cy_px - 60 + flotar * 0.3))
        except Exception:
            pass

    def _renderizar_manifestantes(self) -> None:
        try:
            ahora = pygame.time.get_ticks() / 1000.0
            tam = int(Config.TAMANIO_TILE * self.camara.zoom)
            r = self.renderizador
            for m in self.manifestantes:
                px, py = self.camara.iso_a_pantalla(m["x"], m["y"])
                if px < -tam or px > self.pantalla.get_width() + tam:
                    continue
                if py < -tam or py > self.pantalla.get_height() + tam:
                    continue
                flotar = math.sin(ahora * 1.5 + m["t_offset"]) * 12
                balanceo = math.sin(ahora * 0.8 + m["t_offset"]) * 4
                hue = m["color_hue"]
                r_col = min(255, hue % 360 // 2 + 30)
                g_col = min(255, (hue * 7) % 200 + 40)
                b_col = min(255, (hue * 3) % 200 + 100)
                cx_px = int(px + balanceo)
                cy_px = int(py - tam // 4 + flotar - 10)
                pygame.draw.ellipse(self.pantalla, (r_col, g_col, b_col), (cx_px - 8, cy_px - 20, 16, 24))
                pygame.draw.circle(self.pantalla, (200, 210, 220), (cx_px, cy_px - 28), 8)
                pygame.draw.circle(self.pantalla, (160, 180, 200), (cx_px, cy_px - 28), 8, 2)
                pygame.draw.ellipse(self.pantalla, (120, 200, 255), (cx_px - 5, cy_px - 32, 10, 7))
                cartel_x = cx_px + 14
                cartel_y = cy_px - 32
                pygame.draw.line(self.pantalla, (180, 150, 100), (cartel_x, cartel_y + 40), (cartel_x, cartel_y - 10), 2)
                lineas = m["mensaje"].split("\\n")
                alto_cartel = len(lineas) * 14 + 8
                ancho_cartel = max((len(l) for l in lineas), default=10) * 7 + 8
                cartel_surf = pygame.Surface((ancho_cartel, alto_cartel), pygame.SRCALPHA)
                cartel_surf.fill((230, 80, 80, 220))
                pygame.draw.rect(cartel_surf, (200, 50, 50), (0, 0, ancho_cartel, alto_cartel), 2)
                for i, linea in enumerate(lineas):
                    txt = r.fuente_pequenia.render(linea.strip(), True, (255, 255, 255))
                    cartel_surf.blit(txt, (4, 4 + i * 14))
                self.pantalla.blit(cartel_surf, (cartel_x - ancho_cartel // 2, cartel_y + flotar * 0.5 + 10))
                exc_txt = r.fuente_grande.render(chr(9888), True, (255, 80, 80))
                exc_alpha = int(abs(math.sin(ahora * 3 + m["t_offset"])) * 200 + 55)
                exc_txt.set_alpha(exc_alpha)
                self.pantalla.blit(exc_txt, (cx_px - 18, cy_px - 60 + flotar * 0.3))
        except Exception:
            pass

    def _renderizar_manifestantes(self) -> None:
        """Renderiza colonos flotando con pancartas de protesta."""
        try:
            ahora = pygame.time.get_ticks() / 1000.0
            tam = int(Config.TAMANIO_TILE * self.camara.zoom)
            r = self.renderizador
            for m in self.manifestantes:
                px, py = self.camara.iso_a_pantalla(m["x"], m["y"])
                if px < -tam or px > self.pantalla.get_width() + tam:
                    continue
                if py < -tam or py > self.pantalla.get_height() + tam:
                    continue
                flotar = math.sin(ahora * 1.5 + m["t_offset"]) * 12
                balanceo = math.sin(ahora * 0.8 + m["t_offset"]) * 4
                hue = m["color_hue"]
                r_col = min(255, hue % 360 // 2 + 30)
                g_col = min(255, (hue * 7) % 200 + 40)
                b_col = min(255, (hue * 3) % 200 + 100)
                cx_px = int(px + balanceo)
                cy_px = int(py - tam // 4 + flotar - 10)
                pygame.draw.ellipse(self.pantalla, (r_col, g_col, b_col), (cx_px - 8, cy_px - 20, 16, 24))
                pygame.draw.circle(self.pantalla, (200, 210, 220), (cx_px, cy_px - 28), 8)
                pygame.draw.circle(self.pantalla, (160, 180, 200), (cx_px, cy_px - 28), 8, 2)
                pygame.draw.ellipse(self.pantalla, (120, 200, 255), (cx_px - 5, cy_px - 32, 10, 7))
                cartel_x = cx_px + 14
                cartel_y = cy_px - 32
                pygame.draw.line(self.pantalla, (180, 150, 100), (cartel_x, cartel_y + 40), (cartel_x, cartel_y - 10), 2)
                lineas = m["mensaje"].split("\\n")
                alto_cartel = len(lineas) * 14 + 8
                ancho_cartel = max((len(l) for l in lineas), default=10) * 7 + 8
                cartel_surf = pygame.Surface((ancho_cartel, alto_cartel), pygame.SRCALPHA)
                cartel_surf.fill((230, 80, 80, 220))
                pygame.draw.rect(cartel_surf, (200, 50, 50), (0, 0, ancho_cartel, alto_cartel), 2)
                for i, linea in enumerate(lineas):
                    txt = r.fuente_pequenia.render(linea.strip(), True, (255, 255, 255))
                    cartel_surf.blit(txt, (4, 4 + i * 14))
                self.pantalla.blit(cartel_surf, (cartel_x - ancho_cartel // 2, cartel_y + flotar * 0.5 + 10))
                exc_txt = r.fuente_grande.render(chr(9888), True, (255, 80, 80))
                exc_alpha = int(abs(math.sin(ahora * 3 + m["t_offset"])) * 200 + 55)
                exc_txt.set_alpha(exc_alpha)
                self.pantalla.blit(exc_txt, (cx_px - 18, cy_px - 60 + flotar * 0.3))
        except Exception:
            pass

    def renderizar_tutorial(self) -> None:
        """Renderiza el tutorial interactivo paso a paso."""
        if not self.tutorial_activo:
            return

        paso = self.tutorial_paso
        r = self.renderizador
        pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()

        pasos = [
            { "titulo": "SIMMOON - Colonia Lunar", "fullscreen": True,
              "texto": ["Eres el Comisionado de la primera colonia en la Luna.","","Tu mision: construir, gestionar recursos y hacer","prosperar este asentamiento fronterizo.","","Este tutorial te guiara en los primeros pasos.","Vamos alla, Comisionado!"] },
            { "titulo": "Paso 1/6 - CAMARA", "fullscreen": False,
              "texto": ["Usa WASD o las FLECHAS del teclado para mover","la camara por el mapa de la colonia.","","Explora un poco - veras la carretera central","que cruza el asentamiento de este a oeste."] },
            { "titulo": "Paso 2/6 - ZOOM", "fullscreen": False,
              "texto": ["Usa la RUEDA del raton para acercar y alejar.","","Acerkate para ver los detalles de los edificios,","alejate para tener una vista panoramica."] },
            { "titulo": "Paso 3/6 - MODO CONSTRUIR", "fullscreen": False,
              "texto": ["Presiona la tecla B para entrar en modo CONSTRUIR.","","Veras que el panel lateral se ilumina y aparecen","los edificios disponibles para construir."] },
            { "titulo": "Paso 4/6 - COLOCAR", "fullscreen": False,
              "texto": ["Selecciona un edificio publico del panel lateral","(ej: Paneles Solares en la categoria Energia)","y haz CLICK IZQUIERDO en el mapa para colocarlo.","","Los edificios publicos se colocan directamente.","Los privados necesitan zonificacion (Paso 6)."] },
            { "titulo": "Paso 5/6 - AVANZAR TURNO", "fullscreen": False,
              "texto": ["Presiona ESPACIO o haz click en SIGUIENTE TURNO","para avanzar un turno.","","Cada turno: colonos producen, pagan impuestos,","y la economia de la colonia evoluciona."] },
            { "titulo": "Paso 6/6 - ZONIFICAR", "fullscreen": False,
              "texto": ["Presiona la tecla Z para entrar en modo ZONIFICAR.","","Elige un rubro (Alojamiento, Comercial, Industrial,","Ecologico) y pinta areas en el mapa.","","Al avanzar turno, emprendedores construiran","edificios privados automaticamente en las zonas."] },
            { "titulo": "MISION CUMPLIDA, COMISIONADO!", "fullscreen": True,
              "texto": ["Has completado el tutorial basico.","","Recuerda: gestiona Energia, Oxigeno, Agua y Presion.","Construye servicios de emergencia contra meteoritos.","Exporta excedentes, importa lo que falte.","","Presiona ESC o H para mas ayuda en cualquier momento.","Buena suerte en la Luna!"] },
        ]

        p = pasos[min(paso, len(pasos) - 1)]

        if paso == 0 or paso >= 7:
            # Full-screen overlay
            fondo = pygame.Surface((pant_w, pant_h), pygame.SRCALPHA)
            fondo.fill((0, 0, 0, 200))
            self.pantalla.blit(fondo, (0, 0))

            ancho, alto = 500, 380
            cx, cy = (pant_w - ancho) // 2, (pant_h - alto) // 2
            rect_c = pygame.Rect(cx, cy, ancho, alto)
            pygame.draw.rect(self.pantalla, Config.COLOR_PANEL, rect_c, border_radius=14)
            pygame.draw.rect(self.pantalla, Config.COLOR_PANEL_BORDE, rect_c, 2, border_radius=14)

            x, y = cx + 30, cy + 25
            titulo = r.fuente_grande.render(p["titulo"], True, Config.COLOR_TEXTO_AMARILLO)
            self.pantalla.blit(titulo, (x, y))
            y += 50

            for linea in p["texto"]:
                if linea == "":
                    y += 8
                    continue
                color = Config.COLOR_TEXTO_VERDE if "Presiona" in linea else Config.COLOR_TEXTO
                txt = r.fuente_mediana.render(linea, True, color)
                self.pantalla.blit(txt, (x + 10, y))
                y += 28

            y = cy + alto - 35
            hint_text = "Presiona ESPACIO o ESC para continuar" if paso == 0 else "Presiona ESC para cerrar"
            hint = r.fuente_pequenia.render(hint_text, True, Config.COLOR_TEXTO)
            self.pantalla.blit(hint, (x, y))
        else:
            # Bottom instruction bar (no bloquea la interaccion)
            alto_barra = 120
            barra_y = pant_h - alto_barra - 10

            fondo = pygame.Surface((pant_w - 20, alto_barra), pygame.SRCALPHA)
            fondo.fill((*Config.COLOR_PANEL, 230))
            self.pantalla.blit(fondo, (10, barra_y))
            pygame.draw.rect(self.pantalla, (80, 60, 140), (10, barra_y, pant_w - 20, alto_barra), 2, border_radius=8)

            x, y = 25, barra_y + 12
            step_tag = r.fuente_pequenia.render(p["titulo"], True, Config.COLOR_TEXTO_VERDE)
            self.pantalla.blit(step_tag, (x, y))

            prog_w = pant_w - 80
            prog_y = barra_y + 30
            pygame.draw.rect(self.pantalla, (40, 40, 60), (x, prog_y, prog_w, 8), border_radius=4)
            fill_w = int(prog_w * (min(paso, 6) / 6))
            pygame.draw.rect(self.pantalla, (80, 200, 120), (x, prog_y, fill_w, 8), border_radius=4)

            y = barra_y + 48
            for linea in p["texto"]:
                if linea == "":
                    y += 4
                    continue
                color = Config.COLOR_TEXTO_AMARILLO if "Presiona" in linea else Config.COLOR_TEXTO
                txt = r.fuente_pequenia.render(linea, True, color)
                self.pantalla.blit(txt, (x, y))
                y += 20

            # Skip button
            btn_skip = pygame.Rect(pant_w - 130, barra_y + 8, 100, 24)
            pygame.draw.rect(self.pantalla, (60, 40, 40), btn_skip, border_radius=6)
            txt_skip = r.fuente_pequenia.render("Saltar", True, (255, 100, 100))
            self.pantalla.blit(txt_skip, (pant_w - 120, barra_y + 10))

    def renderizar_ayuda_estatica(self) -> None:
        """Renderiza la pantalla de ayuda estatica (tecla H)."""
        pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()
        fondo = pygame.Surface((pant_w, pant_h), pygame.SRCALPHA)
        fondo.fill((0, 0, 0, 220))
        self.pantalla.blit(fondo, (0, 0))

        r = self.renderizador
        cx, cy = 60, 30

        txt = r.fuente_titulo.render("SIMMOON - Guia del Comisionado", True, Config.COLOR_TEXTO_AMARILLO)
        self.pantalla.blit(txt, (cx, cy))
        cy += 55

        txt = r.fuente_grande.render("Controles", True, Config.COLOR_TEXTO_VERDE)
        self.pantalla.blit(txt, (cx, cy))
        cy += 32

        controles = [
            "WASD / Flechas:  Mover camara por la colonia",
            "Rueda raton:     Zoom (acercar/alejar)",
            "Click izquierdo:  Colocar edificio / pintar zona",
            "Click derecho:    Cancelar / borrar zona",
            "B:               Modo construir",
            "V:               Modo vender (click en edificio)",
            "Z:               Modo zonificar (pintar zonas)",
            "H:               Alternar esta ayuda",
            "F:               Panel de finanzas (ultimos 10 turnos)",
            "Espacio:         Siguiente turno",
            "ESC:             Salir / cerrar ventana",
        ]
        for ctrl in controles:
            txt = r.fuente_mediana.render(ctrl, True, Config.COLOR_TEXTO)
            self.pantalla.blit(txt, (cx, cy))
            cy += 26

        cy += 10
        pygame.draw.line(self.pantalla, Config.COLOR_PANEL_BORDE, (cx, cy), (pant_w - 60, cy), 1)
        cy += 15

        txt = r.fuente_grande.render("Como Jugar?", True, Config.COLOR_TEXTO_VERDE)
        self.pantalla.blit(txt, (cx, cy))
        cy += 32

        instrucciones = [
            "1. ZONIFICA: Presiona Z, elige un rubro y pinta areas en el mapa",
            "2. AVANZA: Presiona Espacio para avanzar un turno",
            "3. CONSTRUYE: Los edificios privados se auto-construyen en sus zonas",
            "4. GESTIONA: Manten Energia, Oxigeno, Agua y Presion en positivo",
            "5. RECAUDACION: Ganas creditos por impuestos, alquileres y exportaciones",
            "6. PROTEJE: Construye servicios de emergencia contra meteoritos y tormentas",
        ]
        for instr in instrucciones:
            txt = r.fuente_mediana.render(instr, True, Config.COLOR_TEXTO)
            self.pantalla.blit(txt, (cx, cy))
            cy += 26

        cy += 10
        pygame.draw.line(self.pantalla, Config.COLOR_PANEL_BORDE, (cx, cy), (pant_w - 60, cy), 1)
        cy += 15
        txt = r.fuente_pequenia.render("Presiona ESC para cerrar o H para alternar", True, Config.COLOR_TEXTO)
        self.pantalla.blit(txt, (cx, cy))

    def renderizar_overlay_ayuda(self) -> None:
        """Alias legacy: redirects to tutorial system."""
        if self.tutorial_activo:
            self.renderizar_tutorial()
        else:
            self.renderizar_ayuda_estatica()
    def renderizar(self) -> None:

        """Renderiza todo el juego."""

        # Sincronizar ciclo lunar con el renderizador
        self.renderizador.es_de_noche = self.ciclo.es_de_noche
        self.renderizador.contador_lunar = self.ciclo.turno_actual

        # Limpiar pantalla

        self.pantalla.fill(Config.COLOR_FONDO)



        # Renderizar mapa

        self.renderizador.renderizar_mapa(self.pantalla, self.mapa, self.camara)



        # Renderizar cursor de zonificacion

        if self.modo_zonificar and self.zona_seleccionada:

            zona = CATALOGO_ZONAS.get(self.zona_seleccionada)

            if zona:

                tam = int(Config.TAMANIO_TILE * self.camara.zoom)

                px, py = self.camara.iso_a_pantalla(self.tile_hover_x, self.tile_hover_y)

                valido = not self.mapa.esta_ocupado(self.tile_hover_x, self.tile_hover_y)

                alpha = 130 if valido else 80

                cursor_surf = pygame.Surface((tam, tam), pygame.SRCALPHA)

                puntos = [(tam // 2, 0), (tam, tam // 4), (tam // 2, tam // 2), (0, tam // 4)]

                pygame.draw.polygon(cursor_surf, (*zona.color, alpha), puntos)

                pygame.draw.polygon(cursor_surf, (*zona.color, 220), puntos, 2)

                self.pantalla.blit(cursor_surf, (px - tam // 2, py - tam // 4))



        # Renderizar cursor de construcción (multi-tile)

        if self.modo_construir and self.edificio_seleccionado:

            tipo = self.edificio_seleccionado

            valido = self.mapa.tile_valido(self.tile_hover_x, self.tile_hover_y, tipo.ancho_tiles, tipo.alto_tiles)

            sprite_preview = self.renderizador.cargar_sprite(

                tipo.ruta_sprite, (64, 64)

            )

            self.renderizador.renderizar_cursor(

                self.pantalla, self.camara, self.tile_hover_x, self.tile_hover_y,

                valido, sprite_preview, tipo.ancho_tiles, tipo.alto_tiles

            )

        elif self.modo_vender:

            # Cursor rojo para vender

            valido = self.mapa.esta_ocupado(self.tile_hover_x, self.tile_hover_y)

            self.renderizador.renderizar_cursor(

                self.pantalla, self.camara, self.tile_hover_x, self.tile_hover_y,

                False, None  # Rojo si no está ocupado

            )

            if valido:

                # Mostrar el edificio que se vendería

                edificio = self.mapa.grid[self.tile_hover_y][self.tile_hover_x]

                if edificio and edificio.sprite:

                    self.renderizador.renderizar_cursor(

                        self.pantalla, self.camara, self.tile_hover_x, self.tile_hover_y,

                        True, None

                    )



        # Renderizar panel UI y manejar clicks

        mouse_pos = pygame.mouse.get_pos()



        if self.modo_zonificar:

            # Panel de zonificacion

            zona_click = self.renderizador.renderizar_panel_zonificar(

                self.pantalla, self.zona_seleccionada, mouse_pos, self.mouse_click

            )

            if zona_click:

                self.zona_seleccionada = zona_click

            edificio_id, cat_clickeada, click_turno = None, self.categoria_actual, False

        else:

            edificio_id, cat_clickeada, click_turno = self.renderizador.renderizar_panel(

                self.pantalla, self.recursos,

                self.edificio_seleccionado,

                self.modo_construir, self.modo_vender,

                self.categoria_actual, self.catalogo, self.votos,

                mouse_pos, self.mouse_click

            )

        self.categoria_actual = cat_clickeada  # Actualizar categoría activa



        # Procesar click en botón de turno

        if click_turno and not self.mostrando_resumen:

            self.procesar_siguiente_turno()

            SonidoProcedural.sonido_turno()



        # Si se clickeó un edificio en el panel, seleccionarlo

        if edificio_id and edificio_id in self.catalogo:

            self.edificio_seleccionado = self.catalogo[edificio_id]

            self.modo_construir = True

            self.modo_vender = False



        # ── Minimapa de navegación ──

        if not self.mostrando_finanzas and not self.mostrando_resumen and not self.mostrando_permiso:

            self.renderizador.renderizar_minimapa(self.pantalla, self.mapa, self.camara)



        # ── Overlay de resumen del turno ──

        if self.mostrando_resumen:

            self.renderizar_overlay_resumen()



        # ── Overlay de permiso de construcción ──

        if self.mostrando_permiso:

            self.renderizar_overlay_permiso()



        # ── Panel de finanzas (tecla F) ──

        if self.mostrando_finanzas:

            self.renderizar_panel_finanzas()

        # Panel de flujo (R)
        if self.panel_flujo.visible:
            self.panel_flujo.renderizar(
                self.pantalla,
                x=10, y=self.pantalla.get_height() // 2 - 120,
                ancho=310, alto=230,
            )

        # Mercado inter-colonial (M)
        if self.mercado_inter.visible:
            accion = self.mercado_inter.renderizar(
                self.pantalla, self.renderizador,
                x=10, y=50,
                mouse_pos=pygame.mouse.get_pos(),
                mouse_click=self.mouse_click,
            )
            if accion and self.mouse_click:
                acc, rec, cant = accion
                if acc == "comprar":
                    ok = self.mercado_inter.comprar(rec, cant, self.recursos)
                    if ok:
                        self._mostrar_mensaje(f"Mercado: +{cant} {rec} comprado")
                    else:
                        self._mostrar_mensaje(f"Mercado: creditos insuficientes")
                elif acc == "vender":
                    ok = self.mercado_inter.vender(rec, cant, self.recursos)
                    if ok:
                        self._mostrar_mensaje(f"Mercado: -{cant} {rec} vendido")
                    else:
                        self._mostrar_mensaje(f"Mercado: no hay suficiente {rec}")

        # Crisis panel (tecla X)
        mx, my = pygame.mouse.get_pos()
        self.crisis_lunar.renderizar(self.pantalla, self.renderizador, (mx, my), self.mouse_click, self.recursos)
        self.tecnologia.renderizar(self.pantalla, self.renderizador, (mx, my), self.mouse_click, self.recursos)

        # Colonos panel (tecla C)
        if self.sistema_colonos.visible:
            self.sistema_colonos.renderizar(self.pantalla, self.renderizador)

        # Colonos en el mapa
        self.sistema_colonos.dibujar_en_mapa(self.pantalla, self.camara)
        self.crisis_lunar.dibujar_en_mapa(self.pantalla, self.camara)

        # Overlay de noche + estrellas
        self.ciclo.renderizar_overlay(self.pantalla)

        # ── Mensaje temporal ──

        if self.mensaje_error and pygame.time.get_ticks() - self.tiempo_mensaje < 3000:

            txt_msg = self.renderizador.fuente_grande.render(

                self.mensaje_error, True, Config.COLOR_TEXTO_AMARILLO

            )

            msg_rect = txt_msg.get_rect(center=(self.pantalla.get_width() // 2 - 160, 60))

            # Fondo semitransparente

            fondo_msg = pygame.Surface((txt_msg.get_width() + 20, txt_msg.get_height() + 10), pygame.SRCALPHA)

            fondo_msg.fill((0, 0, 0, 180))

            self.pantalla.blit(fondo_msg, (msg_rect.x - 10, msg_rect.y - 5))

            self.pantalla.blit(txt_msg, msg_rect)



        # ── Tooltip del tile bajo el ratón ──

        if 0 <= self.tile_hover_x < self.mapa.tamanio and 0 <= self.tile_hover_y < self.mapa.tamanio:

            edificio = self.mapa.grid[self.tile_hover_y][self.tile_hover_x]

            if edificio:

                estado = " 💀 DAÑADO" if not edificio.activo else ""

                txt_tile = self.renderizador.fuente_pequenia.render(

                    f"{edificio.tipo.nombre}{estado} [{self.tile_hover_x},{self.tile_hover_y}]",

                    True, Config.COLOR_TEXTO

                )

                self.pantalla.blit(txt_tile, (10, self.pantalla.get_height() - 25))



        # Actualizar pantalla

                # Mostrar overlay de ayuda si está activo

        if self.tutorial_activo:

            self.renderizar_tutorial()

        if self.mostrando_ayuda:

            self.renderizar_ayuda_estatica()



        if self.manifestantes and not self.tutorial_activo and not self.mostrando_ayuda and not self.mostrando_resumen:
            self._renderizar_manifestantes()

        pygame.display.flip()    

    def ejecutar(self) -> None:

        """Bucle principal del juego."""

        while self.ejecutando:

            self.manejar_eventos()

            self.actualizar()
            self.panel_flujo.actualizar(self.mapa)

            self.renderizar()

            self.reloj.tick(Config.FPS)



        pygame.quit()



# ─── Punto de Entrada ─────────────────────────────────────────────────────



if __name__ == "__main__":

    print("╔══════════════════════════════════════════╗")

    print("║   ☾ SIMMOON — Constructor de Colonia   ║")

    print("║   Motor: Pygame | Estilo: SimCity 2000 ║")

    print("╚══════════════════════════════════════════╝")

    print()

    print("  Cargando votos...")



    # Cargar votos y filtrar catálogo

    dir_assets = str(Path(__file__).parent)

    votos = cargar_votos(dir_assets)

    catalogo_filtrado = filtrar_catalogo_por_votos(votos)



    print(f"  Edificios disponibles: {len(catalogo_filtrado)}")

    print()

    print("  Controles:")

    print("    B: Modo construir | V: Modo vender")

    print("    Click izq: colocar/vender edificio")

    print("    Click der: cancelar")

    print("    WASD/Flechas: mover cámara")

    print("    Rueda ratón: zoom")

    print("    ESC: salir")

    print()



    juego = JuegoSimmoon(votos=votos)

    juego.ejecutar()

