"""
simmoon_transporte.py — 🚇 Red de Transporte Lunar

Analiza el grid del mapa de SIMMOON para detectar conexiones entre
edificios a través de carreteras (roads) y tubos de vacío (transport),
y calcula bonificaciones de eficiencia para los edificios conectados.

Arquitectura:
- RedTransporte: clase principal que mantiene el grafo de conectividad
- BFS sobre tiles de carretera para encontrar componentes conectados
- Cada edificio adyacente a la red recibe un bonus de eficiencia
  proporcional al tamaño del cluster al que está conectado

Uso:
    from simmoon_transporte import RedTransporte
    red = RedTransporte()
    red.analizar(mapa)
    eficiencias = red.obtener_eficiencias()  # {edificio_id: multiplicador}
    resumen = red.resumen()                  # Texto formateado para UI
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from collections import deque


# ── Constantes de Red ─────────────────────────────────────────────────────

# Categorías de edificios que actúan como CONECTORES de la red
CATEGORIAS_RED = {"roads", "transport"}

# IDs específicos de conectores avanzados (tubos de vacío, puentes)
TUBO_VACIO_ID = "tra_02"
CARRETERA_IDS = {"road_01", "road_02", "road_03", "road_04",
                 "road_05", "road_06", "road_07", "road_08"}

# Distancia máxima (en tiles) desde una carretera para considerar
# que un edificio está "conectado a la red"
RADIO_ADYACENCIA = 1

# Bonus base por estar conectado a la red (+20%)
BONUS_BASE = 0.20

# Bonus adicional proporcional al tamaño del cluster:
# por cada 10 tiles de carretera en el cluster, +2% adicional
BONUS_POR_TILE = 0.002


# ── Direcciones de adyacencia (4-direccional para carreteras) ──────────────
DIRECCIONES = [(0, -1), (0, 1), (-1, 0), (1, 0)]


def _es_conector(tipo: Any) -> bool:
    """Determina si un TipoEdificio es un conector de red (carretera/tubo)."""
    return tipo.categoria in CATEGORIAS_RED


def _es_tubo_vacio(tipo: Any) -> bool:
    """Determina si un TipoEdificio es un tubo de vacío (conector avanzado)."""
    return tipo.id == TUBO_VACIO_ID


def _es_carretera(tipo: Any) -> bool:
    """Determina si un TipoEdificio es una carretera."""
    return tipo.id in CARRETERA_IDS


# ── RedTransporte ─────────────────────────────────────────────────────────

class RedTransporte:
    """Analiza y mantiene el estado de la red de transporte en el mapa.

    La red se construye a partir de los tiles ocupados por carreteras y
    tubos de vacío. Los edificios adyacentes a la red reciben bonos de
    eficiencia.

    Attributes:
        clusters: Lista de clusters (componentes conectados). Cada cluster es
                  un set de coordenadas (x, y) de tiles de carretera/tubo.
        edificios_conectados: Dict {edificio_id: info_de_conexion}
        mapa_tamanio: Tamaño del grid analizado
    """

    def __init__(self):
        self.clusters: List[Set[Tuple[int, int]]] = []
        self.edificios_conectados: Dict[int, Dict[str, Any]] = {}
        self.mapa_tamanio: int = 0
        self._edificios_cache: Dict[int, Any] = {}  # id() -> EdificioColocado
        self._ultimo_analisis_valido = False

    # ── Análisis principal ──────────────────────────────────────────────

    def analizar(self, mapa: Any) -> None:
        """Analizar el grid completo y reconstruir la red de transporte.

        Args:
            mapa: Instancia de Mapa (juego_simmoon.Mapa) con grid, edificios.
        """
        self.clusters = []
        self.edificios_conectados = {}
        self._edificios_cache = {}
        self.mapa_tamanio = mapa.tamanio

        # Paso 1: recolectar todos los tiles de carretera/tubo
        tiles_red: Set[Tuple[int, int]] = set()
        for gy in range(mapa.tamanio):
            for gx in range(mapa.tamanio):
                edif = mapa.grid[gy][gx]
                if edif is not None and _es_conector(edif.tipo):
                    # Solo el tile origen del edificio conector
                    if edif.x == gx and edif.y == gy:
                        for dy in range(edif.alto):
                            for dx in range(edif.ancho):
                                tiles_red.add((edif.x + dx, edif.y + dy))

        # Paso 2: BFS para encontrar componentes conectados
        visitados: Set[Tuple[int, int]] = set()
        for tile in tiles_red:
            if tile in visitados:
                continue

            # BFS desde este tile
            cluster: Set[Tuple[int, int]] = set()
            cola = deque([tile])
            visitados.add(tile)

            while cola:
                cx, cy = cola.popleft()
                cluster.add((cx, cy))

                # Explorar vecinos 4-direccionales
                for dx, dy in DIRECCIONES:
                    nx, ny = cx + dx, cy + dy
                    vecino = (nx, ny)
                    if vecino in tiles_red and vecino not in visitados:
                        visitados.add(vecino)
                        cola.append(vecino)

            if cluster:
                self.clusters.append(cluster)

        # Paso 3: para cada edificio NO conector, verificar adyacencia
        for edif in mapa.edificios:
            if _es_conector(edif.tipo):
                continue

            # Buscar si el edificio está tocando algún tile de la red
            conectado = False
            indice_cluster = -1
            tiles_cercanos: List[Tuple[int, int]] = []

            # Revisar perímetro del edificio (footprint expandido por RADIO_ADYACENCIA)
            for dy in range(-RADIO_ADYACENCIA, edif.alto + RADIO_ADYACENCIA):
                for dx in range(-RADIO_ADYACENCIA, edif.ancho + RADIO_ADYACENCIA):
                    gx, gy = edif.x + dx, edif.y + dy
                    if (gx, gy) in tiles_red:
                        conectado = True
                        tiles_cercanos.append((gx, gy))

            if conectado and tiles_cercanos:
                # Encontrar a qué cluster pertenece
                for primer_tile in tiles_cercanos:
                    for idx, cluster in enumerate(self.clusters):
                        if primer_tile in cluster:
                            indice_cluster = idx
                            break
                    if indice_cluster >= 0:
                        break

            # Calcular información de conexión
            edificio_id = id(edif)
            self._edificios_cache[edificio_id] = edif

            # Bonus de eficiencia
            eficiencia = self._calcular_eficiencia(
                conectado, indice_cluster, edif
            )

            self.edificios_conectados[edificio_id] = {
                "edificio": edif,
                "conectado": conectado,
                "indice_cluster": indice_cluster,
                "tamano_cluster": len(self.clusters[indice_cluster]) if indice_cluster >= 0 else 0,
                "tiles_cercanos": tiles_cercanos,
                "eficiencia": eficiencia,
                "tiene_tubo": any(
                    _es_tubo_vacio(self._edificio_en_tile(tx, ty).tipo)
                    for tx, ty in tiles_cercanos
                    if self._edificio_en_tile(tx, ty)
                ) if tiles_cercanos else False,
            }

        self._ultimo_analisis_valido = True

    def _edificio_en_tile(self, gx: int, gy: int) -> Optional[Any]:
        """Busca el edificio que ocupa un tile específico (lazy, desde el cache)."""
        # No podemos acceder directamente al grid, así que buscamos en cache
        for edif in self._edificios_cache.values():
            if edif.x <= gx < edif.x + edif.ancho and edif.y <= gy < edif.y + edif.alto:
                return edif
        return None

    def _calcular_eficiencia(self, conectado: bool,
                              indice_cluster: int,
                              edif: Any) -> float:
        """Calcula el multiplicador de eficiencia para un edificio.

        Fórmula:
            base = 1.0
            si conectado:
                bonus = BONUS_BASE (20%)
                + tamano_cluster * BONUS_POR_TILE (2% cada 10 tiles)
                + extra si el edificio está al lado de un tubo de vacío
            limite: eficiencia entre 0.5 y 2.0
        """
        if not conectado:
            return 1.0  # Sin penalidad por ahora

        tamano = len(self.clusters[indice_cluster]) if indice_cluster >= 0 else 0
        bonus = BONUS_BASE + (tamano * BONUS_POR_TILE)

        # Bonus extra si el edificio está al lado de un tubo de vacío
        # (los tubos dan conectividad express)
        # Verificamos esto en el paso 3 del análisis

        eficiencia = 1.0 + bonus
        return max(0.5, min(2.0, eficiencia))

    # ── API pública ─────────────────────────────────────────────────────

    def obtener_eficiencias(self) -> Dict[int, float]:
        """Devuelve dict {id(edificio): multiplicador_eficiencia}."""
        return {
            eid: info["eficiencia"]
            for eid, info in self.edificios_conectados.items()
        }

    def esta_conectado(self, edificio: Any) -> bool:
        """Verifica si un edificio específico está conectado a la red."""
        info = self.edificios_conectados.get(id(edificio))
        return info["conectado"] if info else False

    def eficiencia_de(self, edificio: Any) -> float:
        """Devuelve el multiplicador de eficiencia de un edificio."""
        info = self.edificios_conectados.get(id(edificio))
        return info["eficiencia"] if info else 1.0

    def num_clusters(self) -> int:
        """Número de componentes conectados en la red."""
        return len(self.clusters)

    def tiles_totales_red(self) -> int:
        """Cantidad total de tiles ocupados por la red."""
        return sum(len(c) for c in self.clusters)

    def edificios_conectados_count(self) -> int:
        """Cantidad de edificios (no carreteras) conectados a la red."""
        return sum(1 for info in self.edificios_conectados.values()
                   if info["conectado"])

    def resumen(self) -> str:
        """Texto formateado con el estado de la red para mostrar en UI.

        Returns:
            String multi-línea con estadísticas de la red.
        """
        if not self._ultimo_analisis_valido:
            return "🚇 Red: sin datos"

        total_edificios = len(self.edificios_conectados)
        conectados = self.edificios_conectados_count()
        clusters = self.num_clusters()
        tiles = self.tiles_totales_red()

        if conectados == 0:
            return f"🚇 Red: {tiles} tiles | {clusters} tramo(s) | Sin edificios conectados"

        # Bonus promedio
        eficiencias = [info["eficiencia"] for info in self.edificios_conectados.values()
                      if info["conectado"]]
        prom = sum(eficiencias) / len(eficiencias) if eficiencias else 1.0
        bonus_pct = int((prom - 1.0) * 100)

        return (
            f"🚇 Red: {tiles} tiles | {clusters} tramo(s)\n"
            f"   Conectados: {conectados}/{total_edificios} edificios\n"
            f"   Bonus eficiencia promedio: +{bonus_pct}%"
        )

    def info_conexion(self, edificio: Any) -> str:
        """Texto descriptivo de la conexión de un edificio específico.

        Args:
            edificio: Instancia de EdificioColocado

        Returns:
            String como "🛣️ Conectado (+25%)" o "🚫 Sin conexión vial"
        """
        info = self.edificios_conectados.get(id(edificio))
        if not info:
            return "🚫 Sin analizar"

        if not info["conectado"]:
            return "🚫 Sin conexión vial"

        pct = int((info["eficiencia"] - 1.0) * 100)
        tubo = " 🚇 Tubo" if info.get("tiene_tubo") else ""
        return f"🛣️ Conectado (+{pct}%){tubo}"


# ── Función helper ───────────────────────────────────────────────────────

def analizar_red(mapa: Any) -> RedTransporte:
    """Atajo para crear RedTransporte, analizar y devolver.

    Args:
        mapa: Instancia de Mapa

    Returns:
        RedTransporte con el análisis ya ejecutado
    """
    red = RedTransporte()
    red.analizar(mapa)
    return red
