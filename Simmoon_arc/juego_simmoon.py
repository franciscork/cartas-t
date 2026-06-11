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

                           "biz_01_lunar_mining_office_pixel.png",

                           costo=500, produce_energia=-5, produce_oxigeno=-2,

                           mantenimiento=10, empleos=8, ancho_tiles=1, alto_tiles=1,

                           descripcion="Centro administrativo de minería lunar."),

    "biz_02": TipoEdificio("biz_02", "Puesto Comercial", "businesses",

                           "biz_02_lunar_trading_post_pixel.png",

                           costo=400, produce_energia=-3, produce_oxigeno=-1,

                           mantenimiento=5, empleos=5, ancho_tiles=1, alto_tiles=1,

                           descripcion="Mercado de intercambio de recursos.", alquiler=20),

    "biz_03": TipoEdificio("biz_03", "Hotel Lunar", "businesses",

                           "biz_03_lunar_hotel_pixel.png",

                           costo=800, produce_energia=-8, produce_oxigeno=-3, produce_agua=-2,

                           mantenimiento=15, empleos=10, ancho_tiles=2, alto_tiles=1,

                           descripcion="Alojamiento para visitantes y turistas. 2x1", alquiler=50),

    "biz_04": TipoEdificio("biz_04", "Restaurante Lunar", "businesses",

                           "biz_04_lunar_restaurant_pixel.png",

                           costo=350, produce_energia=-4, produce_oxigeno=-1, produce_agua=-1,

                           mantenimiento=8, empleos=6, ancho_tiles=1, alto_tiles=1,

                           produce_felicidad=8,
                           descripcion="Gastronomía para la colonia.", alquiler=20),

    "biz_05": TipoEdificio("biz_05", "Laboratorio", "businesses",

                           "biz_05_research_laboratory_pixel.png",

                           costo=1200, produce_energia=-10, produce_oxigeno=-2,

                           mantenimiento=20, empleos=12, ancho_tiles=2, alto_tiles=2,

                           descripcion="Investigación científica avanzada. 2x2"),

    "biz_06": TipoEdificio("biz_06", "Centro Médico", "businesses",

                           "biz_06_medical_center_pixel.png",

                           costo=900, produce_energia=-7, produce_oxigeno=-3,

                           mantenimiento=15, empleos=10, ancho_tiles=2, alto_tiles=1,

                           produce_felicidad=12,
                           descripcion="Atención médica para los colonos. 2x1"),

    "biz_07": TipoEdificio("biz_07", "Terminal Espacial", "businesses",

                           "biz_07_spaceport_terminal_pixel.png",

                           costo=2000, produce_energia=-15, produce_oxigeno=-5,

                           mantenimiento=30, empleos=20, ancho_tiles=3, alto_tiles=2,

                           descripcion="Puerto de llegada y salida de naves. 3x2", alquiler=80),

    "biz_08": TipoEdificio("biz_08", "Fábrica", "businesses",

                           "biz_08_manufacturing_plant_pixel.png",

                           costo=1500, produce_energia=-20, produce_oxigeno=-4, produce_agua=-3,

                           mantenimiento=25, empleos=15, ancho_tiles=2, alto_tiles=2,

                           descripcion="Planta de manufactura pesada. 2x2", alquiler=60),

    "biz_10": TipoEdificio("biz_10", "Banco Lunar", "businesses",

                           "biz_10_lunar_bank_pixel.png",

                           costo=600, produce_energia=-3, produce_oxigeno=-1,

                           mantenimiento=5, empleos=4, ancho_tiles=1, alto_tiles=1,

                           descripcion="Institución financiera de la colonia.", alquiler=30),

    "biz_11": TipoEdificio("biz_11", "Tienda Lunar", "businesses",

                           "biz_11_lunar_shop_pixel.png",

                           costo=300, produce_energia=-2, produce_oxigeno=-1,

                           mantenimiento=3, empleos=3, ancho_tiles=1, alto_tiles=1,

                           descripcion="Tienda de suministros generales.", alquiler=15),

    "biz_12": TipoEdificio("biz_12", "Almacén", "businesses",

                           "biz_12_lunar_warehouse_pixel.png",

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

                            "misc_02_water_processing_plant_pixel.png",

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

                            "misc_04_communication_tower_pixel.png",

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

                            "misc_07_school_academy_pixel.png",

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

                              "biz_04_lunar_restaurant_pixel.png",

                              costo=300, produce_energia=-3, produce_agua=-1,

                              mantenimiento=5, empleos=4,

                              descripcion="Copas en baja gravedad. ¡Los cocktails flotan!", alquiler=18),

    "oficio_02": TipoEdificio("oficio_02", "Tatuajes Low-G", "businesses",

                              "biz_11_lunar_shop_pixel.png",

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

                              "biz_05_research_laboratory_pixel.png",

                              costo=500, produce_energia=-6,

                              mantenimiento=8, empleos=5, ancho_tiles=2, alto_tiles=1,

                              produce_felicidad=12,
                              descripcion="Cine holográfico inmersivo. 2x1", alquiler=35),

    "oficio_06": TipoEdificio("oficio_06", "Taller de Trajes", "businesses",

                              "biz_01_lunar_mining_office_pixel.png",

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

                              "biz_08_manufacturing_plant_pixel.png",

                              costo=400, produce_energia=-5, produce_agua=-2,

                              mantenimiento=6, empleos=3,

                              descripcion="Whisky añejado en cráteres. Sabor... único.", alquiler=20),

    "oficio_10": TipoEdificio("oficio_10", "Museo de Artefactos", "decorations",

                              "dec_05_monument_statue_pixel.png",

                              costo=350, produce_energia=-2,

                              mantenimiento=4, empleos=2, ancho_tiles=2, alto_tiles=1,

                              descripcion="Restos de sondas y artefactos de la era espacial. 2x1", alquiler=15),

    "oficio_11": TipoEdificio("oficio_11", "Observatorio Privado", "buildings_misc",

                              "misc_04_communication_tower_pixel.png",

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

                            "biz_05_research_laboratory_pixel.png",

                            costo=2000, produce_energia=-12, produce_oxigeno=-4,

                            mantenimiento=25, empleos=20, ancho_tiles=3, alto_tiles=2,

                            descripcion="Ingeniería y tecnología lunar del MIT. 3x2", alquiler=90),

    "univ_02": TipoEdificio("univ_02", "Stanford Zero-G Center", "universities",

                            "site_02_research_laboratory_campus_pixel.png",

                            costo=1800, produce_energia=-10, produce_oxigeno=-3, produce_agua=-2,

                            mantenimiento=22, empleos=18, ancho_tiles=3, alto_tiles=2,

                            descripcion="Investigación en gravedad cero de Stanford. 3x2", alquiler=85),

    "univ_03": TipoEdificio("univ_03", "Oxford Astrobiology Inst.", "universities",

                            "biz_05_research_laboratory_pixel.png",

                            costo=1600, produce_energia=-8, produce_oxigeno=-2,

                            mantenimiento=18, empleos=15, ancho_tiles=2, alto_tiles=2,

                            descripcion="Instituto de astrobiología de Oxford. 2x2", alquiler=75),

    "univ_04": TipoEdificio("univ_04", "Tokyo Space Science Inst.", "universities",

                            "site_02_research_laboratory_campus_pixel.png",

                            costo=1700, produce_energia=-9, produce_oxigeno=-3,

                            mantenimiento=20, empleos=16, ancho_tiles=2, alto_tiles=2,

                            descripcion="Instituto de ciencia espacial de Tokio. 2x2", alquiler=80),

    "univ_05": TipoEdificio("univ_05", "Caltech Lunar Observatory", "universities",

                            "misc_04_communication_tower_pixel.png",

                            costo=2200, produce_energia=-14, produce_oxigeno=-3,

                            mantenimiento=28, empleos=22, ancho_tiles=2, alto_tiles=2,

                            descripcion="Observatorio astronómico de Caltech. 2x2", alquiler=95),

    "univ_06": TipoEdificio("univ_06", "ETH Zurich Materials Lab", "universities",

                            "biz_08_manufacturing_plant_pixel.png",

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

                            "misc_07_school_academy_pixel.png",

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

                           "hou_01_basic_habitat_module_pixel.png",

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

    

    def actualizar_balance(self, edificios: List['EdificioColocado']) -> None:

        """Recalcula producción y consumo basado en los edificios colocados."""

        self.energia_total = Config.ENERGIA_INICIAL

        self.oxigeno_total = Config.OXIGENO_INICIAL

        self.agua_total = Config.AGUA_INICIAL

        self.presion_total = Config.PRESION_INICIAL

        for edificio in edificios:

            if edificio.activo:

                self.energia_total += edificio.tipo.produce_energia

                self.oxigeno_total += edificio.tipo.produce_oxigeno

                self.agua_total += edificio.tipo.produce_agua

                self.presion_total += edificio.tipo.produce_presion

        # Aplicar bono/penalidad por felicidad

        self.energia = int(self.energia_total * self.bono_produccion)

        self.oxigeno = int(self.oxigeno_total * self.bono_produccion)

        self.agua = int(self.agua_total * self.bono_produccion)
        self.presion = int(self.presion_total * self.bono_produccion)
    

    def gastar(self, creditos: int = 0) -> bool:

        """Intenta gastar créditos. Retorna True si hay suficientes."""

        if self.creditos >= creditos:

            self.creditos -= creditos

            return True

        return False

    

    def ingresar(self, creditos: int) -> None:

        """Añade créditos."""

        self.creditos += creditos



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

        

        # Componentes del juego

        self.mapa = Mapa(Config.TAMANIO_GRID)

        self.recursos = Recursos()

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



        # Sistema de permisos (zonificacion) - legacy

        self.mostrando_permiso = False

        self.permiso_tipo: Optional[TipoEdificio] = None

        self.permiso_gx: int = 0

        self.permiso_gy: int = 0        # Sistema de zonificacion por rubros

        self.modo_zonificar = False

        self.zona_seleccionada: Optional[str] = None  # ID del rubro activo

        self.mostrando_info_zona = False




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

        self.es_de_noche = False  # Estado del ciclo d?a/noche

        self.contador_lunar = 0  # Contador de turnos en el ciclo actual



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

        self.recursos.actualizar_balance(self.mapa.edificios)



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


        if self.es_de_noche:

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



        # 4. Auto-settlement: emprendedores ocupan terrenos zonificados

        asentamientos = 0

        asentamientos_nombres: List[str] = []

        for zona_id, zona in CATALOGO_ZONAS.items():

            tiles_libres = self.mapa.tiles_zonificados(zona_id)

            if not tiles_libres:

                continue

            candidatos = edificios_para_zona(zona_id)

            if not candidatos:

                continue

            max_asentamientos = min(2, len(tiles_libres) // 3 + 1)

            intentos = random.randint(0, max_asentamientos)

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
            "es_noche": self.es_de_noche,

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

            txt_ciclo = r.fuente_pequenia.render(f"{ciclo_estado} lunar (turno {self.contador_lunar + 1}/{Config.DIAS_NOCHE if d['es_noche'] else Config.DIAS_LUZ})", True, Config.COLOR_TEXTO)

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

            # ── Cerrar overlays con click o ESC ──

            if self.mostrando_resumen or self.mostrando_permiso or self.mostrando_finanzas:

                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:

                    if self.tutorial_activo and self.tutorial_paso == 0:

                        # Salto de bienvenida -> paso 1

                        self.tutorial_paso = 1

                    elif self.tutorial_activo and self.tutorial_paso >= 7:

                        self.tutorial_activo = False

                        self.tutorial_paso = 0

        if self.tutorial_activo:
            self.renderizar_tutorial()

        elif self.mostrando_ayuda:
            self.renderizar_ayuda_estatica()



        elif self.mostrando_resumen:

            self.mostrando_resumen = False

            if self.mostrando_permiso:

                self.mostrando_permiso = False

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:

                    pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()

                    # Botón CERRAR de finanzas

                    if self.mostrando_finanzas:

                        ancho_f, alto_f = 700, 480

                        cx_f, cy_f = (pant_w - ancho_f) // 2, (pant_h - alto_f) // 2

                        btn_fin = pygame.Rect(cx_f + ancho_f // 2 - 60, cy_f + alto_f - 45, 120, 35)

                        if btn_fin.collidepoint(evento.pos):

                            self.mostrando_finanzas = False

            # continue removed (not in loop)

                    ancho, alto = 460, 540

                    cx, cy = (pant_w - ancho) // 2, (pant_h - alto) // 2

                    # Botón CERRAR del resumen

                    if self.mostrando_resumen:

                        btn_ok = pygame.Rect(cx + ancho // 2 - 70, cy + alto - 55, 140, 38)

                        if btn_ok.collidepoint(evento.pos):

                            self.mostrando_resumen = False

                    # Botones del permiso (APROBAR / CANCELAR)

                    if self.mostrando_permiso:

                        btn_aprobar = pygame.Rect(cx + 30, cy + alto - 55, 160, 38)

                        btn_cancelar = pygame.Rect(cx + ancho - 190, cy + alto - 55, 160, 38)

                        if btn_aprobar.collidepoint(evento.pos):

                            self._aprobar_permiso()

                        elif btn_cancelar.collidepoint(evento.pos):

                            self.mostrando_permiso = False

            if evento.type == pygame.QUIT:

                self.ejecutando = False

            # continue removed (not in loop)



            # ── Salir ──

            if evento.type == pygame.QUIT:

                self.ejecutando = False

            

            elif evento.type == pygame.KEYDOWN:

                if evento.key == pygame.K_ESCAPE:

                    self.ejecutando = False

                elif evento.key == pygame.K_b:

                    # Alternar modo construir

                    self.modo_construir = not self.modo_construir

                    self.modo_vender = False
                    if self.tutorial_activo and self.tutorial_paso == 6:
                        self.tutorial_z_hecho = True
                        self.tutorial_paso = 7

                    if not self.modo_construir:

                        self.edificio_seleccionado = None

                elif evento.key == pygame.K_v:

                    # Alternar modo vender

                    self.modo_vender = not self.modo_vender

                    self.modo_construir = False

                    self.edificio_seleccionado = None
                    if self.tutorial_activo and self.tutorial_paso == 3:
                        self.tutorial_b_hecho = True
                        self.tutorial_paso = 4

                elif evento.key == pygame.K_h:

                    # Alternar ayuda estatica (H)

                    if self.tutorial_activo:

                        self.tutorial_activo = False

                        self.mostrando_ayuda = True

                    else:

                        self.mostrando_ayuda = not self.mostrando_ayuda

                elif evento.key == pygame.K_SPACE:

                    # Atajo: espacio = siguiente turno

                    if self.tutorial_activo and self.tutorial_paso == 0:
                        self.tutorial_paso = 1
                    elif self.tutorial_activo and self.tutorial_paso == 5:
                        self.tutorial_espacio_hecho = True
                        self.tutorial_paso = 6
                    else:
                        if not self.mostrando_resumen:
                            self.procesar_siguiente_turno()

                        self.procesar_siguiente_turno()

                        SonidoProcedural.sonido_turno()

                elif evento.key == pygame.K_f:

                    # Alternar panel de finanzas

                    self.mostrando_finanzas = not self.mostrando_finanzas

                elif evento.key == pygame.K_z:

                    # Alternar modo zonificar

                    self.modo_zonificar = not self.modo_zonificar

                    self.modo_construir = False

                    self.modo_vender = False

                    self.edificio_seleccionado = None

                    self.zona_seleccionada = None

            

            elif evento.type == pygame.MOUSEBUTTONDOWN:

                self.mouse_click = True  # Marcar que hubo click

                grid_x, grid_y = self._obtener_tile_bajo_raton()

                

                if evento.button == 1:

                    panel_x = self.pantalla.get_width() - 320

                    if mouse_pos[0] >= panel_x:

                        pass  # was continue




                    # Modo zonificar: pintar zona

                    if self.modo_zonificar and self.zona_seleccionada:

                        if self.mapa.pintar_zona(grid_x, grid_y, self.zona_seleccionada):

                            self._mostrar_mensaje(f"Zona {CATALOGO_ZONAS[self.zona_seleccionada].nombre} [{grid_x},{grid_y}]")

                        else:

                            self._mostrar_mensaje("❌ Terreno ocupado, no se puede zonificar")

                            SonidoProcedural.sonido_alerta()

                        pass  # was continue




                    if self.modo_vender:

                        # Vender o reparar edificio

                        ox, oy = grid_x, grid_y

                        edif_danado = self.mapa.grid[oy][ox] if 0 <= ox < self.mapa.tamanio and 0 <= oy < self.mapa.tamanio else None

                        if edif_danado and not edif_danado.activo:

                            coste_rep = edif_danado.tipo.costo // 3

                            if self.recursos.gastar(coste_rep):

                                edif_danado.activo = True

                                self.recursos.actualizar_balance(self.mapa.edificios)

                                self._mostrar_mensaje(f"🔧 Reparado: {edif_danado.tipo.nombre} (-{coste_rep} 💰)")

                                SonidoProcedural.sonido_construir()

                            else:

                                self._mostrar_mensaje(f"❌ Necesitas {coste_rep}💰 para reparar")

                                SonidoProcedural.sonido_alerta()

                        elif edif_danado:

                            reembolso = edif_danado.tipo.costo // 2

                            self.mapa.vender_edificio(grid_x, grid_y)

                            self.recursos.ingresar(reembolso)

                            self.recursos.actualizar_balance(self.mapa.edificios)

                            self._mostrar_mensaje(f"✅ Vendido: {edif_danado.tipo.nombre} (+{reembolso} 💰)")

                            SonidoProcedural.sonido_vender()

                        else:

                            self._mostrar_mensaje("❌ No hay edificio aquí para vender")

                            SonidoProcedural.sonido_alerta()

                    

                    elif self.modo_construir and self.edificio_seleccionado:

                        # Colocar edificio (soporte multi-tile)

                        tipo = self.edificio_seleccionado



                        # Si es privado, abrir overlay de permiso en vez de colocar directo

                        if es_edificio_privado(tipo.id):

                            if self.mapa.tile_valido(grid_x, grid_y, tipo.ancho_tiles, tipo.alto_tiles):

                                self.permiso_tipo = tipo

                                self.permiso_gx = grid_x

                                self.permiso_gy = grid_y

                                self.mostrando_permiso = True

                            else:

                                if tipo.ancho_tiles > 1 or tipo.alto_tiles > 1:

                                    self._mostrar_mensaje(f"❌ No hay espacio ({tipo.ancho_tiles}x{tipo.alto_tiles} tiles)")

                                else:

                                    self._mostrar_mensaje("❌ Casilla ocupada o fuera del mapa")

                            pass  # was continue




                        # Público: colocación directa

                        if self.mapa.tile_valido(grid_x, grid_y, tipo.ancho_tiles, tipo.alto_tiles):

                            if self.recursos.gastar(tipo.costo):

                                sprite = self.renderizador.cargar_sprite(

                                    tipo.ruta_sprite, (64, 64)

                                )

                                self.mapa.colocar_edificio(grid_x, grid_y, tipo, sprite)

                                self.recursos.actualizar_balance(self.mapa.edificios)

                                tam_txt = "" if tipo.ancho_tiles == 1 and tipo.alto_tiles == 1 else f" ({tipo.ancho_tiles}x{tipo.alto_tiles})"

                                self._mostrar_mensaje(f"✅ Construido: {tipo.nombre}{tam_txt}")

                                SonidoProcedural.sonido_construir()

                            else:

                                self._mostrar_mensaje(f"❌ Créditos insuficientes (necesitas {tipo.costo} 💰)")

                        else:

                            if tipo.ancho_tiles > 1 or tipo.alto_tiles > 1:

                                self._mostrar_mensaje(f"❌ No hay espacio ({tipo.ancho_tiles}x{tipo.alto_tiles} tiles)")

                            else:

                                self._mostrar_mensaje("❌ Casilla ocupada o fuera del mapa")

                

                elif evento.button == 3:  # Click derecho

                    # Modo zonificar: borrar zona o cancelar seleccion

                    if self.modo_zonificar:

                        if self.zona_seleccionada:

                            self.zona_seleccionada = None

                        else:

                            self.mapa.borrar_zona(grid_x, grid_y)

                    else:

                        self.edificio_seleccionado = None

                        self.modo_construir = False

                        self.modo_vender = False

                

                elif evento.button == 4:  # Rueda arriba

                    self.camara.acercar(0.1)

                elif evento.button == 5:  # Rueda abajo

                    self.camara.acercar(-0.1)

            

            elif evento.type == pygame.VIDEORESIZE:

                self.camara.ancho_ventana = evento.w

                self.camara.alto_ventana = evento.h

                self.pantalla = pygame.display.set_mode((evento.w, evento.h), pygame.RESIZABLE)

        

        # ── Movimiento continuo de cámara con teclas ──

        teclas = pygame.key.get_pressed()

        if teclas[pygame.K_w] or teclas[pygame.K_UP]:

            self.camara.mover(0, -1)

        if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:

            self.camara.mover(0, 1)

        if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:

            self.camara.mover(-1, 0)
            if self.tutorial_activo and self.tutorial_paso == 1:
                self.tutorial_wasd_hecho = True
                self.tutorial_paso = 2

        if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:

            self.camara.mover(1, 0)
            if self.tutorial_activo and self.tutorial_paso == 1:
                self.tutorial_wasd_hecho = True
                self.tutorial_paso = 2

    

    def actualizar(self) -> None:

        """Actualiza la lógica del juego cada frame."""

        self.tile_hover_x, self.tile_hover_y = self._obtener_tile_bajo_raton()



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
        self.renderizador.es_de_noche = self.es_de_noche
        self.renderizador.contador_lunar = self.contador_lunar

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

        elif self.mostrando_ayuda:

            self.renderizar_ayuda_estatica()



        if self.manifestantes and not self.tutorial_activo and not self.mostrando_ayuda and not self.mostrando_resumen:
            self._renderizar_manifestantes()

        pygame.display.flip()    

    def ejecutar(self) -> None:

        """Bucle principal del juego."""

        while self.ejecutando:

            self.manejar_eventos()

            self.actualizar()

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

