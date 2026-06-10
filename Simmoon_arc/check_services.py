#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_services.py — Verificador rápido de servicios SIMMOON

Comprueba que los servicios críticos del ecosistema estén respondiendo.
Usa códigos ANSI para output colorido en terminal.

Uso:
    python check_services.py              # Verifica todos los servicios
    python check_services.py --json       # Salida en formato JSON
    python check_services.py --watch 10   # Monitoreo continuo cada 10s

Servicios verificados:
    - Ollama      :11434  (LLM server)
    - ComfyUI     :8188   (Generación de imágenes)
    - PostgreSQL  :5432   (Base de datos)
    - Dashboard   :5000   (Monitor web)
    - InvokeAI    :9090   (Generación alternativa)
    - Hermes      :9119   (Agente multi-escritorio)

Creado por: Buffy (DeepSeek v4) — Orquestador SIMMOON
Fecha: 2026-06-10
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Tuple

# ── Colores ANSI ──────────────────────────────────────────────────────────
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"  # No Color

# ── Configuración de servicios ────────────────────────────────────────────
SERVICES = [
    {"name": "Ollama",       "port": 11434, "path": "/api/tags",             "desc": "LLM Server local"},
    {"name": "ComfyUI",      "port": 8188,  "path": "/queue",                "desc": "Generación de imágenes"},
    {"name": "PostgreSQL",   "port": 5432,  "path": None,                    "desc": "Base de datos", "type": "pg"},
    {"name": "Dashboard",    "port": 5000,  "path": "/",                     "desc": "Monitor web"},
    {"name": "InvokeAI",     "port": 9090,  "path": "/api/v1/app/version",   "desc": "Generación alternativa"},
    {"name": "Hermes",       "port": 9119,  "path": "/",                     "desc": "Agente multi-escritorio"},
]


def check_http_service(name: str, port: int, path: str, timeout: int = 3) -> Tuple[bool, int, str]:
    """Verificar si un servicio HTTP está respondiendo.

    Args:
        name: Nombre del servicio
        port: Puerto
        path: Ruta del endpoint
        timeout: Timeout en segundos

    Returns:
        (healthy, latency_ms, error_message)
    """
    url = f"http://localhost:{port}{path}"
    start = time.time()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = round((time.time() - start) * 1000)
            return resp.status < 500, latency, ""
    except urllib.error.HTTPError as e:
        latency = round((time.time() - start) * 1000)
        return False, latency, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        latency = round((time.time() - start) * 1000)
        return False, latency, str(e.reason)
    except Exception as e:
        latency = round((time.time() - start) * 1000)
        return False, latency, str(e)


def check_postgresql(timeout: int = 3) -> Tuple[bool, int, str]:
    """Verificar si PostgreSQL acepta conexiones usando pg_isready.

    Returns:
        (healthy, latency_ms, error_message)
    """
    import subprocess
    start = time.time()
    try:
        r = subprocess.run(
            ["pg_isready", "-h", "localhost", "-p", "5432", "-q"],
            capture_output=True, text=True, timeout=timeout,
        )
        latency = round((time.time() - start) * 1000)
        return r.returncode == 0, latency, ""
    except subprocess.TimeoutExpired:
        latency = round((time.time() - start) * 1000)
        return False, latency, "timeout"
    except FileNotFoundError:
        latency = round((time.time() - start) * 1000)
        return False, latency, "pg_isready no encontrado"
    except Exception as e:
        latency = round((time.time() - start) * 1000)
        return False, latency, str(e)


def check_all() -> List[Dict]:
    """Verificar todos los servicios configurados.

    Returns:
        Lista de dicts con estado de cada servicio
    """
    results = []
    for svc in SERVICES:
        if svc.get("type") == "pg":
            healthy, latency, error = check_postgresql()
        else:
            healthy, latency, error = check_http_service(
                svc["name"], svc["port"], svc["path"]
            )
        results.append({
            "name": svc["name"],
            "port": svc["port"],
            "desc": svc["desc"],
            "healthy": healthy,
            "latency_ms": latency,
            "error": error,
        })
    return results


def format_report(results: List[Dict]) -> str:
    """Formatear resultados como reporte de consola con colores.

    Args:
        results: Lista de resultados de check_all()

    Returns:
        String formateado con colores ANSI
    """
    now = datetime.now().strftime("%H:%M:%S")
    healthy_count = sum(1 for r in results if r["healthy"])
    total = len(results)
    failed = total - healthy_count

    lines = []
    lines.append(f"{CYAN}{'='*55}{NC}")
    lines.append(f"{BOLD}  ☾ SIMMOON — Verificación de Servicios{NC}")
    lines.append(f"  {DIM}{now}{NC}")
    lines.append(f"{CYAN}{'='*55}{NC}")
    lines.append("")

    for r in results:
        if r["healthy"]:
            icon = f"{GREEN}✅{NC}"
            status = f"{GREEN}ON{NC}"
        else:
            icon = f"{RED}❌{NC}"
            status = f"{RED}OFF{NC}"

        name = r["name"]
        port = f":{r['port']}"
        latency = f"{r['latency_ms']}ms"
        desc = r["desc"]

        line = f"  {icon} {name:15s} {DIM}{port:6s}{NC}  {status}  {DIM}{latency:>6s}{NC}  {desc}"
        if not r["healthy"] and r["error"]:
            line += f"  {RED}({r['error'][:30]}){NC}"
        lines.append(line)

    lines.append("")
    lines.append(f"{CYAN}{'─'*55}{NC}")

    if failed == 0:
        lines.append(f"  {GREEN}{BOLD}✅ Todos los servicios operativos ({healthy_count}/{total}){NC}")
    else:
        lines.append(f"  {YELLOW}{BOLD}⚠️  {failed} servicio(s) caído(s) ({healthy_count}/{total} operativos){NC}")
        # Listar caídos
        for r in results:
            if not r["healthy"]:
                lines.append(f"     {RED}❌{NC} {r['name']} :{r['port']} — {r.get('error', 'sin respuesta')}")

    lines.append(f"{CYAN}{'='*55}{NC}")
    return "\n".join(lines)


def to_json(results: List[Dict]) -> str:
    """Convertir resultados a JSON."""
    return json.dumps({
        "timestamp": datetime.now().isoformat(),
        "healthy": all(r["healthy"] for r in results),
        "total": len(results),
        "healthy_count": sum(1 for r in results if r["healthy"]),
        "services": results,
    }, indent=2, ensure_ascii=False)


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="☾ SIMMOON — Verificador rápido de servicios"
    )
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON")
    parser.add_argument("--watch", "-w", type=int, default=0, metavar="SECONDS",
                        help="Monitoreo continuo cada N segundos")
    args = parser.parse_args()

    if args.watch > 0:
        print(f"{CYAN}⏱️  Monitoreo cada {args.watch}s — Ctrl+C para detener{NC}\n")
        try:
            while True:
                results = check_all()
                if args.json:
                    print(to_json(results))
                else:
                    # Limpiar pantalla
                    os.system("cls" if os.name == "nt" else "clear")
                    print(format_report(results))
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print(f"\n{GREEN}✅ Monitoreo detenido.{NC}")
        return

    results = check_all()

    if args.json:
        print(to_json(results))
    else:
        print(format_report(results))

    # Exit code: 0 si todo ok, 1 si hay servicios caídos
    sys.exit(0 if all(r["healthy"] for r in results) else 1)


if __name__ == "__main__":
    main()
