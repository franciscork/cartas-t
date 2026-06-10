"""
simmoon_economia.py — Sistema de Economía Dinámica

Ofrece precios fluctuantes para recursos según oferta/demanda,
alquileres y primas dinámicos, e índice económico general.
Sin dependencias del juego — solo Python estándar.
"""

from typing import Dict, List, Optional, Any


class MercadoDinamico:
    """
    Mercado con oferta/demanda para la colonia lunar.

    Cada turno:
     1. Analiza producción neta de edificios (oferta vs demanda)
     2. Ajusta precios de recursos (energía, oxígeno, agua)
     3. Calcula índice económico general
     4. Deriva alquileres, primas e impuestos dinámicos
    """

    def __init__(self) -> None:
        # Precios base por unidad de recurso
        self.precio_energia: float = 3.0
        self.precio_oxigeno: float = 5.0
        self.precio_agua: float = 4.0
        self.precio_presion: float = 2.0

        # Historial de precios (hasta 20 turnos)
        self.historial: Dict[str, List[float]] = {
            "energia": [],
            "oxigeno": [],
            "agua": [],
            "presion": [],
            "indice": [],
        }

        self.indice_economico: float = 1.0
        # 0.5 = recesión | 1.0 = neutral | 2.0 = auge

        # Oferta y demanda del turno actual
        self.oferta_energia: int = 0
        self.demanda_energia: int = 0
        self.oferta_oxigeno: int = 0
        self.demanda_oxigeno: int = 0
        self.oferta_agua: int = 0
        self.demanda_agua: int = 0

        self.turno: int = 0

    # ─── Actualización principal ─────────────────────────────────

    def actualizar(self, edificios: List[Any], poblacion: int, turno: int) -> None:
        """Actualiza precios, oferta/demanda e índice económico."""
        self.turno = turno

        oferta_energia, oferta_oxigeno, oferta_agua, oferta_presion = 0, 0, 0, 0
        demanda_energia, demanda_oxigeno, demanda_agua = 0, 0, 0

        for edif in edificios:
            if getattr(edif, "activo", True):
                t = edif.tipo
                if t.produce_energia > 0:
                    oferta_energia += t.produce_energia
                elif t.produce_energia < 0:
                    demanda_energia += abs(t.produce_energia)

                if t.produce_oxigeno > 0:
                    oferta_oxigeno += t.produce_oxigeno
                elif t.produce_oxigeno < 0:
                    demanda_oxigeno += abs(t.produce_oxigeno)

                if t.produce_agua > 0:
                    oferta_agua += t.produce_agua
                elif t.produce_agua < 0:
                    demanda_agua += abs(t.produce_agua)

                if t.produce_presion > 0:
                    oferta_presion += t.produce_presion

        self.oferta_energia = oferta_energia
        self.demanda_energia = demanda_energia
        self.oferta_oxigeno = oferta_oxigeno
        self.demanda_oxigeno = demanda_oxigeno
        self.oferta_agua = oferta_agua
        self.demanda_agua = demanda_agua

        # Precios según oferta/demanda
        self.precio_energia = self._calcular_precio(
            oferta_energia, demanda_energia, 3.0, "energia"
        )
        self.precio_oxigeno = self._calcular_precio(
            oferta_oxigeno, demanda_oxigeno, 5.0, "oxigeno"
        )
        self.precio_agua = self._calcular_precio(
            oferta_agua, demanda_agua, 4.0, "agua"
        )
        self.precio_presion = self._calcular_precio(
            oferta_presion, int(demanda_energia * 0.15), 2.0, "presion"
        )

        # Índice económico general
        self.indice_economico = self._calcular_indice(edificios, poblacion)

        # Guardar historial
        self.historial["energia"].append(self.precio_energia)
        self.historial["oxigeno"].append(self.precio_oxigeno)
        self.historial["agua"].append(self.precio_agua)
        self.historial["presion"].append(self.precio_presion)
        self.historial["indice"].append(self.indice_economico)

        # Limitar historial a 20 turnos
        for key in self.historial:
            if len(self.historial[key]) > 20:
                self.historial[key] = self.historial[key][-20:]

    # ─── Cálculo de precios ──────────────────────────────────────

    def _calcular_precio(
        self, oferta: int, demanda: int, precio_base: float, clave: str
    ) -> float:
        """Precio según ratio oferta/demanda, suavizado con histórico."""
        if oferta <= 0 and demanda <= 0:
            return precio_base
        if oferta <= 0:
            return round(precio_base * 2.0, 1)  # Escasez total
        if demanda <= 0:
            return round(precio_base * 0.5, 1)  # Sin demanda

        ratio = demanda / oferta
        precio = precio_base * max(0.3, min(3.0, ratio))

        # Suavizar con precio anterior
        anterior = self.historial.get(clave, [precio_base])
        precio_prev = anterior[-1] if anterior else precio_base
        return round(precio * 0.6 + precio_prev * 0.4, 1)

    # ─── Índice económico ──────────────────────────────────────

    def _calcular_indice(self, edificios: List[Any], poblacion: int) -> float:
        """Índice económico compuesto (0.5–2.0)."""
        activos = [e for e in edificios if getattr(e, "activo", True)]
        num_edificios = len(activos)
        num_categorias = len(set(e.tipo.categoria for e in activos))

        # Factor de actividad
        factor_actividad = min(2.0, 0.5 + num_edificios * 0.012 + poblacion * 0.006)

        # Factor de diversidad económica
        factor_diversidad = min(1.5, 0.5 + num_categorias * 0.07)

        # Factor de déficit: escasez reduce el índice
        deficit_energia = max(0, self.demanda_energia - self.oferta_energia)
        deficit_oxigeno = max(0, self.demanda_oxigeno - self.oferta_oxigeno)
        deficit_agua = max(0, self.demanda_agua - self.oferta_agua)
        factor_deficit = max(0.5, 1.0 - (deficit_energia + deficit_oxigeno + deficit_agua) * 0.002)

        return max(0.5, min(2.0, round(factor_actividad * factor_diversidad * factor_deficit, 2)))

    # ─── Consultas públicas ──────────────────────────────────────

    def alquiler_dinamico(self, alquiler_base: int) -> int:
        """Ajusta alquiler según índice económico."""
        if alquiler_base <= 0:
            return 0
        return max(1, int(alquiler_base * self.indice_economico))

    def prima_dinamica(self, prima_base: int) -> int:
        """Ajusta prima de zonificación según índice económico."""
        return max(5, int(prima_base * self.indice_economico))

    def impuesto_dinamico(self, poblacion: int) -> int:
        """Tasa de impuesto por colono, ajustada por economía.

        En auge → impuestos más altos (mayor actividad económica)
        En recesión → impuestos más bajos (estímulo fiscal)
        """
        if poblacion > 100:
            base = 8
        elif poblacion > 50:
            base = 5
        else:
            base = 3
        # 0.85 = damping fiscal: evita que el impuesto fluctúe tan brusco como el índice
        # 0.6  = piso fiscal: recaudación mínima incluso en recesión profunda
        return max(1, int(base * max(0.6, self.indice_economico * 0.85)))

    def visa_dinamica(self, poblacion: int) -> int:
        """Ingreso por visas, ajustado por índice económico."""
        return max(1, poblacion * max(1, int(2 * self.indice_economico)))

    def valor_recursos(
        self, energia_total: int, oxigeno_total: int, agua_total: int, presion_total: int
    ) -> int:
        """Valor monetario de los recursos producidos en el turno."""
        valor = 0
        if energia_total > 0:
            valor += energia_total * self.precio_energia
        if oxigeno_total > 0:
            valor += oxigeno_total * self.precio_oxigeno
        if agua_total > 0:
            valor += agua_total * self.precio_agua
        return int(valor)

    def costo_deficits(
        self, energia_total: int, oxigeno_total: int, agua_total: int
    ) -> int:
        """Costo de cubrir déficits a precios de mercado."""
        costo = 0
        if energia_total < 0:
            costo += abs(energia_total) * self.precio_energia
        if oxigeno_total < 0:
            costo += abs(oxigeno_total) * self.precio_oxigeno
        if agua_total < 0:
            costo += abs(agua_total) * self.precio_agua
        return int(costo)

    def tendencia(self, clave: str) -> str:
        """Tendencia de precios: ⬆️, ➡️, ⬇️"""
        hist = self.historial.get(clave, [])
        if len(hist) < 3:
            return "➡️"
        reciente = sum(hist[-3:]) / 3
        medio = len(hist) // 2
        anterior = sum(hist[medio - 1:medio + 2]) / 3 if len(hist) >= 6 else sum(hist[:3]) / 3
        if reciente > anterior * 1.02:
            return "⬆️"
        elif reciente < anterior * 0.98:
            return "⬇️"
        return "➡️"

    # ─── Estado económico (para etiqueta en UI) ──────────────────

    @property
    def estado_texto(self) -> str:
        """Texto legible del estado económico."""
        if self.indice_economico >= 1.3:
            return "📈 AUGE"
        elif self.indice_economico >= 0.8:
            return "📊 ESTABLE"
        return "📉 RECESIÓN"

    def resumen(self) -> str:
        """Texto de resumen para mostrar en UI del juego."""
        return (
            f"📊 Economía: {self.estado_texto} ({self.indice_economico:.2f}x)\n"
            f"⚡ Energía: {self.precio_energia:.1f}💰/u {self.tendencia('energia')}\n"
            f"🫁 Oxígeno: {self.precio_oxigeno:.1f}💰/u {self.tendencia('oxigeno')}\n"
            f"💧 Agua: {self.precio_agua:.1f}💰/u {self.tendencia('agua')}"
        )

    def linea_indicador(self) -> str:
        """Línea compacta para el panel del juego."""
        return (
            f"{self.estado_texto} ({self.indice_economico:.2f}x) | "
            f"⚡{self.precio_energia:.0f} {self.tendencia('energia')} "
            f"🫁{self.precio_oxigeno:.0f} {self.tendencia('oxigeno')} "
            f"💧{self.precio_agua:.0f} {self.tendencia('agua')}"
        )
