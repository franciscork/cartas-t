#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
game_config.py — Configuración y catálogo de edificios de SIMMOON

Extraído de juego_simmoon.py para modularizar el código.
Contiene: Config, TipoEdificio, CATALOGO_EDIFICIOS,
          EDIFICIOS_PRIVADOS, CATALOGO_ZONAS, y funciones de votos.
"""

import json
import random
import urllib.request
import urllib.error
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple

log = logging.getLogger(__name__)

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

                           "biz_banco_lunar_blender.png",

                           costo=600, produce_energia=-3, produce_oxigeno=-1,

                           mantenimiento=5, empleos=4, ancho_tiles=1, alto_tiles=1,

                           descripcion="Institución financiera de la colonia.", alquiler=30),

    "biz_11": TipoEdificio("biz_11", "Tienda Lunar", "businesses",

                           "biz_11_lunar_shop_pixel.png",

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



    # ── Personajes (characters) ──

    "char_01": TipoEdificio("char_01", "Astronauta Trabajador", "characters",

                            "char_01_astronaut_worker_pixel.png",

                            costo=100, produce_energia=-1,

                            mantenimiento=2, empleos=1,

                            produce_felicidad=3,

                            descripcion="Colono trabajador de la colonia lunar."),

    "char_02": TipoEdificio("char_02", "Científico", "characters",

                            "char_02_scientist_pixel.png",

                            costo=150, produce_energia=-1,

                            mantenimiento=2, empleos=2,

                            produce_felicidad=4,

                            descripcion="Investigador del laboratorio lunar."),

    "char_03": TipoEdificio("char_03", "Guardia de Seguridad", "characters",

                            "char_03_security_guard_pixel.png",

                            costo=120, produce_energia=-1,

                            mantenimiento=2, empleos=1,

                            produce_felicidad=2,

                            descripcion="Protege la colonia de amenazas."),

    "char_04": TipoEdificio("char_04", "Minero", "characters",

                            "char_04_miner_pixel.png",

                            costo=130, produce_energia=-2,

                            mantenimiento=3, empleos=1,

                            produce_felicidad=2,

                            descripcion="Excava recursos del regolito lunar."),

    "char_05": TipoEdificio("char_05", "Oficial Médico", "characters",

                            "char_05_medical_officer_pixel.png",

                            costo=180, produce_energia=-2,

                            mantenimiento=4, empleos=2,

                            produce_felicidad=6,

                            descripcion="Atiende la salud de los colonos."),

    "char_06": TipoEdificio("char_06", "Piloto", "characters",

                            "char_06_pilot_pixel.png",

                            costo=160, produce_energia=-2,

                            mantenimiento=3, empleos=2,

                            produce_felicidad=4,

                            descripcion="Pilota naves y lanzaderas lunares."),



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



    # ── Flora Lunar (lunar_flora) ──

    "flora_01": TipoEdificio("flora_01", "Hongo de Cristal", "lunar_flora",

                             "flora_01_crystal_fungus_pixel.png",

                             costo=30, mantenimiento=0,

                             produce_oxigeno=1,

                             descripcion="Hongo bioluminiscente que produce oxígeno."),

    "flora_02": TipoEdificio("flora_02", "Musgo Lunar", "lunar_flora",

                             "flora_02_lunar_moss_pixel.png",

                             costo=20, mantenimiento=0,

                             produce_oxigeno=2,

                             descripcion="Alfombra de musgo adaptado al vacío."),

    "flora_03": TipoEdificio("flora_03", "Planta Tubular", "lunar_flora",

                             "flora_03_tube_plant_pixel.png",

                             costo=40, mantenimiento=0,

                             produce_oxigeno=1, produce_felicidad=2,

                             descripcion="Planta alienígena de tallos huecos."),

    "flora_04": TipoEdificio("flora_04", "Flor Luminiscente", "lunar_flora",

                             "flora_04_glow_flower_pixel.png",

                             costo=50, mantenimiento=0,

                             produce_oxigeno=1, produce_felicidad=3,

                             descripcion="Flor que brilla en la oscuridad lunar."),



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

                            "misc_torre_comunicaciones_blender.png",

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



    # ── Infraestructura (infrastructure) ──

    "infra_01": TipoEdificio("infra_01", "Tubería de Presión", "infrastructure",

                             "infra_01_pressure_pipe_pixel.png",

                             costo=80, mantenimiento=0,

                             produce_presion=2,

                             descripcion="Mantiene la presión atmosférica."),

    "infra_02": TipoEdificio("infra_02", "Cable Eléctrico", "infrastructure",

                             "infra_02_power_cable_pixel.png",

                             costo=60, mantenimiento=0,

                             descripcion="Distribuye energía por la colonia."),

    "infra_03": TipoEdificio("infra_03", "Tubería de Agua", "infrastructure",

                             "infra_03_water_pipeline_pixel.png",

                             costo=70, mantenimiento=0,

                             produce_agua=1,

                             descripcion="Conduce agua a los edificios."),

    "infra_04": TipoEdificio("infra_04", "Tubo de Transporte", "infrastructure",

                             "infra_04_transport_tube_pixel.png",

                             costo=100, mantenimiento=0,

                             descripcion="Cápsula de transporte neumático."),



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

    # Personajes (privados — necesitan permiso del comisionado)

    "char_01", "char_02", "char_03", "char_04", "char_05", "char_06",

    # Alojamiento (albergues)

    "hou_01", "hou_02", "hou_03", "hou_04",

    # Recursos Vitales

    "life_01", "life_02", "life_03",

    # Industria

    "ind_01", "ind_02", "ind_03", "ind_04",

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

}


def edificios_para_zona(zona_id: str) -> List[str]:

    """Devuelve los IDs de edificios privados compatibles con una zona."""

    zona = CATALOGO_ZONAS.get(zona_id)

    if not zona:

        return []

    # Las categorias_compatibles ahora contienen IDs especificos de edificios

    return [aid for aid in zona.categorias_compatibles if aid in EDIFICIOS_PRIVADOS]


