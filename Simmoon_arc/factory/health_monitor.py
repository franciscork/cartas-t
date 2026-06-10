#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/health_monitor.py — Monitor de Salud FactoryGames

Verifica periódicamente el estado de todos los servicios y agentes,
genera alertas y ofrece auto-recuperación.
"""

import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.parent.resolve()


# ══════════════════════════════════════════════════════════════════════════
#  HealthMonitor
# ══════════════════════════════════════════════════════════════════════════

class HealthMonitor:
    """Monitor de salud de servicios y agentes.

    Verifica periódicamente el estado de cada servicio registrado.
    Genera alertas cuando un servicio está caído.
    Ofrece auto-recuperación usando funciones de launch predefinidas.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._checks: Dict[str, Callable[[], bool]] = {}
        self._launchers: Dict[str, Callable[[], bool]] = {}
        self._results: Dict[str, bool] = {}
        self._last_check: Dict[str, float] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ── Registro de checks ───────────────────────────────────────────

    def register_check(self, name: str,
                       health_fn: Callable[[], bool],
                       launch_fn: Optional[Callable[[], bool]] = None):
        """Registrar un servicio para monitoreo.

        Args:
            name: Nombre del servicio (ej: 'ollama', 'comfyui')
            health_fn: Función que retorna True si el servicio está saludable
            launch_fn: Función opcional para lanzar/recuperar el servicio
        """
        self._checks[name] = health_fn
        if launch_fn:
            self._launchers[name] = launch_fn

    def unregister_check(self, name: str):
        """Eliminar un servicio del monitoreo."""
        self._checks.pop(name, None)
        self._launchers.pop(name, None)
        self._results.pop(name, None)
        self._last_check.pop(name, None)

    # ── Health checks ────────────────────────────────────────────────

    def check_service(self, name: str) -> bool:
        """Verificar salud de un servicio específico.

        Returns:
            True si está saludable, False si no
        """
        fn = self._checks.get(name)
        if not fn:
            return False
        try:
            result = fn()
            with self._lock:
                self._results[name] = result
                self._last_check[name] = time.time()
            return result
        except Exception as e:
            with self._lock:
                self._results[name] = False
                self._last_check[name] = time.time()
            if self.verbose:
                print(f"  ⚠️  [{name}] Health check error: {e}")
            return False

    def check_all(self, names: Optional[List[str]] = None) -> Dict[str, bool]:
        """Verificar salud de todos los servicios registrados.

        Args:
            names: Lista opcional de servicios a verificar (todos si None)

        Returns:
            Dict {service_name: is_healthy}
        """
        targets = names if names else list(self._checks.keys())
        results = {}
        for name in targets:
            results[name] = self.check_service(name)
        return results

    def all_healthy(self) -> bool:
        """Verificar si todos los servicios están saludables."""
        results = self.check_all()
        return all(results.values())

    # ── Resultados cacheados ─────────────────────────────────────────

    def get_results(self) -> Dict[str, bool]:
        """Obtener últimos resultados de health checks."""
        with self._lock:
            return dict(self._results)

    def get_healthy(self) -> List[str]:
        """Obtener lista de servicios saludables."""
        return [name for name, ok in self.get_results().items() if ok]

    def get_unhealthy(self) -> List[str]:
        """Obtener lista de servicios no saludables."""
        return [name for name, ok in self.get_results().items() if not ok]

    # ── Alertas ──────────────────────────────────────────────────────

    def check_alerts(self) -> List[str]:
        """Generar alertas para servicios caídos.

        Returns:
            Lista de strings de alerta
        """
        results = self.check_all()
        alerts = []
        for name, healthy in results.items():
            if not healthy:
                alerts.append(f"❌ {name} — servicio no disponible")
        return alerts

    # ── Recuperación ─────────────────────────────────────────────────

    def recover_service(self, name: str) -> bool:
        """Intentar recuperar un servicio caído.

        Args:
            name: Nombre del servicio

        Returns:
            True si se recuperó exitosamente
        """
        fn = self._launchers.get(name)
        if not fn:
            if self.verbose:
                print(f"  ⚠️  [{name}] No hay función de recuperación registrada")
            return False

        if self.verbose:
            print(f"  🔄 Recuperando {name}...")

        try:
            result = fn()
            # Esperar un momento y verificar
            time.sleep(3)
            healthy = self.check_service(name)
            if healthy:
                if self.verbose:
                    print(f"  ✅ {name} recuperado exitosamente")
                return True
            else:
                if self.verbose:
                    print(f"  ❌ {name} no responde después del intento de recuperación")
                return result
        except Exception as e:
            if self.verbose:
                print(f"  ❌ [{name}] Error en recuperación: {e}")
            return False

    def recover_all(self) -> Dict[str, bool]:
        """Intentar recuperar todos los servicios caídos.

        Returns:
            Dict {service_name: recovered_successfully}
        """
        unhealthy = self.get_unhealthy()
        results = {}
        for name in unhealthy:
            results[name] = self.recover_service(name)
        return results

    # ── Periodic checks (background thread) ──────────────────────────

    def _check_loop(self, interval: int = 30):
        """Loop de health checks en background."""
        while self._running:
            try:
                self.check_all()
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️  Health check loop error: {e}")
            time.sleep(interval)

    def start_periodic_check(self, interval: int = 30):
        """Iniciar health checks periódicos en background thread.

        Args:
            interval: Intervalo en segundos entre checks
        """
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._check_loop,
            args=(interval,),
            daemon=True,
            name="health-monitor",
        )
        self._thread.start()

        if self.verbose:
            print(f"  🔍 Health Monitor: checks periódicos cada {interval}s (background)")

    def stop_periodic_check(self):
        """Detener health checks periódicos."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        if self.verbose:
            print("  Health Monitor: checks periódicos detenidos")

    # ── Reportes formateados ─────────────────────────────────────────

    def format_status(self, results: Optional[Dict[str, bool]] = None) -> str:
        """Formatear estado de salud como texto.

        Args:
            results: Resultados de health check (si None, hace check ahora)

        Returns:
            String formateado con el estado de cada servicio
        """
        if results is None:
            results = self.check_all()

        lines = ["", "  📊 Estado de Servicios:"]
        for name, healthy in sorted(results.items()):
            icon = "✅" if healthy else "⚫"
            lines.append(f"     {icon} {name}")
        lines.append("")

        return "\n".join(lines)

    # ── Estado interno ───────────────────────────────────────────────

    def status(self) -> dict:
        """Obtener estado completo del monitor.

        Returns:
            Dict con resultados, alertas, estadísticas
        """
        results = self.get_results()
        unhealthy = [n for n, h in results.items() if not h]
        return {
            "services": len(self._checks),
            "healthy": sum(1 for h in results.values() if h),
            "unhealthy": len(unhealthy),
            "unhealthy_services": unhealthy,
            "results": results,
            "alerts": self.check_alerts(),
            "periodic_check": self._running,
        }


# ── Quick test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    monitor = HealthMonitor(verbose=True)

    # Registrar algunos checks de prueba
    def check_true():
        return True
    def check_false():
        return False

    monitor.register_check("test-ok", check_true)
    monitor.register_check("test-fail", check_false)

    print(f"\n  🏭 FactoryGames — Health Monitor Test\n")
    print(f"  {'='*55}\n")

    results = monitor.check_all()
    print(monitor.format_status(results))

    alerts = monitor.check_alerts()
    if alerts:
        print("  🚨 Alertas:")
        for a in alerts:
            print(f"     {a}")
    else:
        print("  ✅ Sin alertas\n")
