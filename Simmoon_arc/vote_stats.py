#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vote_stats.py
=============

Script de análisis estadístico de los votos almacenados en ``../votes.json``
para el proyecto SIMMOON.

Funcionalidades:
    * Lectura del archivo JSON de votos.
    * Cálculo de estadísticas agregadas (totales, promedios, top N).
    * Distribución de votos por categoría de asset.
    * Generación de un reporte visual en consola con códigos ANSI.
    * Exportación de los mismos datos a ``votes_report.json``.

Uso:
    python vote_stats.py

Autor: Equipo SIMMOON
Licencia: MIT
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes de rutas y configuración
# ---------------------------------------------------------------------------
# Ruta del archivo de entrada (un nivel por encima del directorio actual).
RUTA_VOTES = str(Path(__file__).parent / "votes.json")
# Ruta del archivo de salida con el reporte en formato JSON.
RUTA_REPORTE = "votes_report.json"
# Tamaño máximo de la barra de progreso ASCII.
ANCHO_BARRA = 30
# Tamaños de los rankings a mostrar.
TOP_N = 10

# ---------------------------------------------------------------------------
# Códigos ANSI para colorear la salida por consola.
# Se desactivan automáticamente si la salida no es un terminal interactivo.
# ---------------------------------------------------------------------------
class Color:
    """Códigos ANSI para embellecer la salida por consola."""
    RESET = "\033[0m"
    NEGRITA = "\033[1m"
    SUBRAYADO = "\033[4m"
    ROJO = "\033[91m"
    VERDE = "\033[92m"
    AMARILLO = "\033[93m"
    AZUL = "\033[94m"
    MAGENTA = "\033[95m"
    CIAN = "\033[96m"
    BLANCO = "\033[97m"
    GRIS = "\033[90m"


# Si la salida estándar no es un terminal (por ejemplo, redirigida a un
# archivo), se desactivan los colores para evitar secuencias ANSI sucias.
if not sys.stdout.isatty():
    for atributo in dir(Color):
        if atributo.isupper():
            setattr(Color, atributo, "")


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------
def cargar_votos(ruta: str) -> dict:
    """
    Carga y valida el archivo JSON de votos.

    Parámetros:
        ruta (str): Ruta al archivo ``votes.json``.

    Retorna:
        dict: Diccionario con los datos de votos.

    Lanza:
        SystemExit: Si el archivo no existe o contiene un JSON inválido.
    """
    if not os.path.exists(ruta):
        print(f"{Color.ROJO}✘ Error:{Color.RESET} No se encontró el archivo "
              f"'{ruta}'.")
        print(f"{Color.AMARILLO}→{Color.RESET} Asegúrate de que el archivo "
              f"existe y vuelve a intentarlo.")
        sys.exit(1)

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except json.JSONDecodeError as error:
        print(f"{Color.ROJO}✘ Error:{Color.RESET} El archivo '{ruta}' no "
              f"contiene un JSON válido.")
        print(f"{Color.GRIS}Detalle: {error}{Color.RESET}")
        sys.exit(1)
    except OSError as error:
        print(f"{Color.ROJO}✘ Error:{Color.RESET} No se pudo leer el "
              f"archivo '{ruta}'.")
        print(f"{Color.GRIS}Detalle: {error}{Color.RESET}")
        sys.exit(1)

    return datos


def normalizar_votos(datos: dict) -> list:
    """
    Normaliza la estructura del JSON a una lista uniforme de diccionarios.

    Acepta dos formatos:
        1. ``{"votos": [ {...}, ... ]}`` (estructura jerárquica).
        2. ``[ {...}, ... ]`` (lista directa de votos).

    Parámetros:
        datos (dict | list): Contenido bruto del archivo JSON.

    Retorna:
        list: Lista de votos normalizados.
    """
    if isinstance(datos, dict):
        # Si el JSON tiene clave "votos", la usamos; si no, tratamos las
        # claves del diccionario como la lista de assets.
        if "votos" in datos and isinstance(datos["votos"], list):
            return datos["votos"]
        if "assets" in datos and isinstance(datos["assets"], list):
            return datos["assets"]
        # Última opción: los valores del propio diccionario.
        return list(datos.values())
    if isinstance(datos, list):
        return datos
    return []


def calcular_estadisticas(votos: list) -> dict:
    """
    Calcula las estadísticas agregadas a partir de la lista de votos.

    Parámetros:
        votos (list): Lista de diccionarios con la información de cada asset.

    Retorna:
        dict: Diccionario con todas las métricas calculadas.
    """
    total_votos = 0
    conteo_por_asset = defaultdict(int)
    categoria_por_asset = {}
    nombre_por_asset = {}

    for entrada in votos:
        # Cada entrada puede representar un asset ya sumado o un voto
        # individual. Detectamos la clave relevante.
        if not isinstance(entrada, dict):
            continue

        asset_id = (
            entrada.get("id")
            or entrada.get("asset_id")
            or entrada.get("nombre")
            or entrada.get("name")
        )
        if asset_id is None:
            continue

        asset_id = str(asset_id)
        nombre_por_asset[asset_id] = (
            entrada.get("nombre") or entrada.get("name") or asset_id
        )
        categoria_por_asset[asset_id] = (
            entrada.get("categoria")
            or entrada.get("category")
            or entrada.get("tipo")
            or "Sin categoría"
        )

        # Si la entrada ya contiene "votos" o "count", lo usamos tal cual.
        if "votos" in entrada:
            cantidad = int(entrada.get("votos", 0) or 0)
        elif "count" in entrada:
            cantidad = int(entrada.get("count", 0) or 0)
        else:
            # Si no hay clave de conteo, asumimos que la entrada es un voto
            # individual (valor 1).
            cantidad = 1

        conteo_por_asset[asset_id] += cantidad
        total_votos += cantidad

    # Construimos un ranking ordenado.
    ranking = sorted(
        (
            {
                "id": asset_id,
                "nombre": nombre_por_asset[asset_id],
                "categoria": categoria_por_asset[asset_id],
                "votos": cantidad,
            }
            for asset_id, cantidad in conteo_por_asset.items()
        ),
        key=lambda item: item["votos"],
        reverse=True,
    )

    # Distribución agregada por categoría.
    distribucion = defaultdict(int)
    for item in ranking:
        distribucion[item["categoria"]] += item["votos"]

    promedio = (total_votos / len(ranking)) if ranking else 0

    return {
        "total_votos": total_votos,
        "total_assets": len(ranking),
        "promedio": promedio,
        "ranking": ranking,
        "distribucion_categorias": dict(distribucion),
    }


def barra_progreso(valor: int, maximo: int, ancho: int = ANCHO_BARRA) -> str:
    """
    Genera una barra de progreso ASCII proporcional al valor recibido.

    Parámetros:
        valor (int): Valor actual a representar.
        maximo (int): Valor máximo de referencia.
        ancho (int): Ancho total de la barra en caracteres.

    Retorna:
        str: Cadena con la barra de progreso en formato ``[████░░░░]``.
    """
    if maximo <= 0:
        return f"[{'-' * ancho}]"
    proporcion = max(0.0, min(1.0, valor / maximo))
    lleno = int(round(proporcion * ancho))
    vacio = ancho - lleno
    return f"[{'█' * lleno}{'░' * vacio}]"


# ---------------------------------------------------------------------------
# Funciones de presentación (consola)
# ---------------------------------------------------------------------------
def banner() -> None:
    """Imprime el banner principal de SIMMOON Vote Stats."""
    print(f"{Color.CIAN}{Color.NEGRITA}")
    print("=" * 70)
    print("  SIMMOON VOTE STATS")
    print(f"{Color.RESET}")
    print(f"{Color.MAGENTA}{Color.NEGRITA}       S I M M O O N   V O T E   S T A T S{Color.RESET}")
    print(f"{Color.GRIS}       Reporte generado: "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Color.RESET}")
    print("=" * 70)


def imprimir_resumen(stats: dict) -> None:
    """Muestra el resumen general de los votos."""
    print(f"\n{Color.NEGRITA}{Color.BLANCO}▶ RESUMEN GENERAL{Color.RESET}")
    print("-" * 70)
    print(f"  {Color.VERDE}Total de votos:{Color.RESET}   "
          f"{Color.NEGRITA}{stats['total_votos']}{Color.RESET}")
    print(f"  {Color.VERDE}Total de assets:{Color.RESET}  "
          f"{Color.NEGRITA}{stats['total_assets']}{Color.RESET}")
    print(f"  {Color.VERDE}Promedio de votos:{Color.RESET} "
          f"{Color.NEGRITA}{stats['promedio']:.2f}{Color.RESET}")
    print()


def imprimir_top(stats: dict, n: int = TOP_N, ascendente: bool = False,
                 titulo: str = "TOP", color_barra: str = "") -> None:
    """
    Imprime un ranking Top N con barras de progreso ASCII.

    Parámetros:
        stats (dict): Estadísticas calculadas.
        n (int): Cantidad de elementos a mostrar.
        ascendente (bool): Si es ``True`` muestra los menos votados.
        titulo (str): Encabezado del bloque.
        color_barra (str): Código ANSI de color para la barra.
    """
    ranking = stats["ranking"]
    if not ranking:
        print(f"{Color.AMARILLO}No hay datos suficientes para mostrar "
              f"el ranking.{Color.RESET}")
        return

    elementos = ranking[::-1] if ascendente else ranking
    elementos = elementos[:n]
    max_votos = elementos[0]["votos"] if elementos else 0

    print(f"\n{Color.NEGRITA}{color_barra}▶ {titulo}{Color.RESET}")
    print("-" * 70)
    print(f"  {Color.GRIS}{'#':<4}{'ID':<24}{'NOMBRE':<22}{'VOTOS':>6}  "
          f"BARRA{Color.RESET}")
    for indice, item in enumerate(elementos, start=1):
        barra = barra_progreso(item["votos"], max_votos)
        # Truncamos el id y el nombre para que encajen en la tabla.
        id_corto = (item["id"][:22] + "..") if len(item["id"]) > 24 else item["id"]
        nombre_corto = (item["nombre"][:20] + "..") if len(item["nombre"]) > 22 else item["nombre"]
        print(f"  {indice:<4}{id_corto:<24}{nombre_corto:<22}"
              f"{item['votos']:>6}  {color_barra}{barra}{Color.RESET}")
    print()


def imprimir_distribucion(stats: dict) -> None:
    """Muestra la distribución de votos agrupada por categoría."""
    distribucion = stats["distribucion_categorias"]
    if not distribucion:
        print(f"{Color.AMARILLO}No hay categorías registradas.{Color.RESET}")
        return

    total = sum(distribucion.values()) or 1
    max_votos = max(distribucion.values()) or 1

    print(f"\n{Color.NEGRITA}{Color.AMARILLO}▶ DISTRIBUCIÓN POR CATEGORÍA"
          f"{Color.RESET}")
    print("-" * 70)
    print(f"  {Color.GRIS}{'CATEGORÍA':<28}{'VOTOS':>8}  {'%':>6}  BARRA"
          f"{Color.RESET}")

    # Ordenamos las categorías de mayor a menor número de votos.
    for categoria, cantidad in sorted(
        distribucion.items(), key=lambda x: x[1], reverse=True
    ):
        porcentaje = (cantidad / total) * 100
        barra = barra_progreso(cantidad, max_votos, ANCHO_BARRA // 2)
        cat_corta = (categoria[:26] + "..") if len(categoria) > 28 else categoria
        print(f"  {cat_corta:<28}{cantidad:>8}  {porcentaje:>5.1f}%  "
              f"{Color.AMARILLO}{barra}{Color.RESET}")
    print()


# ---------------------------------------------------------------------------
# Persistencia del reporte
# ---------------------------------------------------------------------------
def guardar_reporte(stats: dict, ruta: str) -> None:
    """
    Serializa las estadísticas a un archivo JSON legible y bien formateado.

    Parámetros:
        stats (dict): Estadísticas calculadas.
        ruta (str): Ruta de salida del archivo ``votes_report.json``.
    """
    reporte = {
        "generado_en": datetime.now().isoformat(timespec="seconds"),
        "resumen": {
            "total_votos": stats["total_votos"],
            "total_assets": stats["total_assets"],
            "promedio_votos": round(stats["promedio"], 2),
        },
        "top_mas_votados": stats["ranking"][:TOP_N],
        "top_menos_votados": list(reversed(stats["ranking"][-TOP_N:])),
        "distribucion_categorias": stats["distribucion_categorias"],
    }
    try:
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(reporte, archivo, ensure_ascii=False, indent=2)
        print(f"{Color.VERDE}✔ Reporte guardado correctamente en "
              f"'{ruta}'.{Color.RESET}")
    except OSError as error:
        print(f"{Color.ROJO}✘ No se pudo guardar el reporte: "
              f"{error}{Color.RESET}")


# ---------------------------------------------------------------------------
# Punto de entrada principal
# ---------------------------------------------------------------------------
def main() -> None:
    """Función principal: orquesta la lectura, cálculo y reporte de votos."""
    banner()
    datos = cargar_votos(RUTA_VOTES)
    votos = normalizar_votos(datos)
    if not votos:
        print(f"{Color.AMARILLO}⚠ El archivo '{RUTA_VOTES}' no contiene "
              f"votos válidos.{Color.RESET}")
        sys.exit(0)

    stats = calcular_estadisticas(votos)
    imprimir_resumen(stats)
    imprimir_top(
        stats,
        n=TOP_N,
        ascendente=False,
        titulo=f"TOP {TOP_N} ASSETS MÁS VOTADOS",
        color_barra=Color.VERDE,
    )
    imprimir_top(
        stats,
        n=TOP_N,
        ascendente=True,
        titulo=f"TOP {TOP_N} ASSETS MENOS VOTADOS",
        color_barra=Color.ROJO,
    )
    imprimir_distribucion(stats)
    guardar_reporte(stats, RUTA_REPORTE)
    print(f"{Color.CIAN}{Color.NEGRITA}¡Análisis finalizado con éxito!"
          f"{Color.RESET}\n")


if __name__ == "__main__":
    main()
