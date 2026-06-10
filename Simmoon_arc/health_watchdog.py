#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
health_watchdog.py — Watchdog de servicios SIMMOON

Monitorea continuamente los 6 servicios del ecosistema y reinicia
automáticamente los que fallen tras 2 checks consecutivos.

Uso:
    python health_watchdog.py              # Modo daemon (monitoreo continuo)
    python health_watchdog.py --once        # Un solo chequeo
    python health_watchdog.py --interval 15 # Intervalo personalizado (default: 30s)

Servicios monitoreados:
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
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# ── Configuración ─────────────────────────────────────────────────────────
LOG_DIR = Path(os.environ.get("HOME", os.path.expanduser("~"))) / ".simmoon-logs"
LOG_FILE = LOG_DIR / "watchdog.log"
SIMIOON_DIR = Path(__file__).parent.resolve()

# Cada servicio: nombre, puerto, path HTTP, comando de reinicio
SERVICES = [
    {
        "name": "Ollama",
        "port": 11434,
        "path": "/api/tags",
        "type": "http",
        "restart_cmd": "pkill -f 'ollama serve' 2>/dev/null; sleep 1; ollama serve &",
        "desc": "LLM Server local",
    },
    {
        "name": "ComfyUI",
        "port": 8188,
        "path": "/queue",
        "type": "http",
        "restart_cmd": f"cd {SIMIOON_DIR} && bash launch_comfyui.sh &",
        "desc": "Generación de imágenes",
    },
    {
        "name": "PostgreSQL",
        "port": 5432,
        "path": None,
        "type": "pg",
        "restart_cmd": "service postgresql start 2>/dev/null || pg_ctlcluster 16 main start 2>/dev/null",
        "desc": "Base de datos",
    },
    {
        "name": "Dashboard",
        "port": 5000,
        "path": "/",
        "type": "http",
        "restart_cmd": f"cd {SIMIOON_DIR} && nohup python3 dashboard.py --port 5000 > /tmp/dashboard.log 2>&1 &",
        "desc": "Monitor web",
    },
    {
        "name": "InvokeAI",
        "port": 9090,
        "path": "/api/v1/app/version",
        "type": "http",
        "restart_cmd": f"cd {SIMIOON_DIR} && bash launch_invokeai.sh &",
        "desc": "Generación alternativa",
    },
    {
        "name": "Hermes",
        "port": 9119,
        "path": "/",
        "type": "http",
        "restart_cmd": f"cd {SIMIOON_DIR} && bash launch_hermes.sh &",
        "desc": "Agente multi-escritorio",
    },
]


def log(msg: str):
    """Escribir mensaje en el log del watchdog con timestamp."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def check_http(name: str, port: int, path: str, timeout: int = 3) -> Tuple[bool, str]:
    """Verificar servicio HTTP.

    Returns:
        (healthy, error_message)
    """
    url = f"http://localhost:{port}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 500, ""
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, str(e.reason)
    except Exception as e:
        return False, str(e)


def check_pg(timeout: int = 3) -> Tuple[bool, str]:
    """Verificar PostgreSQL con pg_isready.

    Returns:
        (healthy, error_message)
    """
    try:
        r = subprocess.run(
            ["pg_isready", "-h", "localhost", "-p", "5432", "-q"],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode == 0, "" if r.returncode == 0 else "pg_isready: no accepting connections"
    except FileNotFoundError:
        return False, "pg_isready no encontrado"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def check_all() -> Dict[str, bool]:
    """Verificar todos los servicios.

    Returns:
        Dict[name -> healthy]
    """
    status = {}
    for svc in SERVICES:
        if svc["type"] == "pg":
            healthy, err = check_pg()
        else:
            healthy, err = check_http(svc["name"], svc["port"], svc["path"])
        status[svc["name"]] = healthy
        if not healthy:
            log(f"❌ {svc['name']} :{svc['port']} CAÍDO — {err}")
    return status


def restart_service(svc: dict) -> bool:
    """Intentar reiniciar un servicio caído.

    Args:
        svc: Diccionario del servicio (de la lista SERVICES)

    Returns:
        True si el comando se ejecutó (no garantiza que el servicio arrancara)
    """
    log(f"🔄 Intentando reiniciar {svc['name']}...")
    try:
        subprocess.Popen(
            svc["restart_cmd"],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log(f"✅ Comando de reinicio ejecutado para {svc['name']}")
        return True
    except Exception as e:
        log(f"❌ Error al reiniciar {svc['name']}: {e}")
        return False


def run_once() -> Dict:
    """Ejecutar un solo chequeo de todos los servicios.

    Returns:
        Dict con estado de todos los servicios
    """
    results = []
    for svc in SERVICES:
        if svc["type"] == "pg":
            healthy, err = check_pg()
        else:
            healthy, err = check_http(svc["name"], svc["port"], svc["path"])

        results.append({
            "name": svc["name"],
            "port": svc["port"],
            "desc": svc["desc"],
            "healthy": healthy,
            "error": err,
        })

    summary = {
        "timestamp": datetime.now().isoformat(),
        "healthy": all(r["healthy"] for r in results),
        "total": len(results),
        "healthy_count": sum(1 for r in results if r["healthy"]),
        "services": results,
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def run_daemon(interval: int = 30, max_failures: int = 2):
    """Ejecutar el watchdog en modo daemon (monitoreo continuo).

    Args:
        interval: Segundos entre chequeos
        max_failures: Fallos consecutivos antes de intentar reinicio
    """
    log("🟢 WATCHDOG INICIADO — Modo daemon")
    log(f"   Intervalo: {interval}s | Fallos para reinicio: {max_failures}")
    log(f"   Servicios: {', '.join(s['name'] for s in SERVICES)}")
    log(f"   Log: {LOG_FILE}")

    # Contador de fallos consecutivos por servicio
    failure_counts: Dict[str, int] = {svc["name"]: 0 for svc in SERVICES}

    try:
        while True:
            status = check_all()

            all_ok = True
            for svc in SERVICES:
                name = svc["name"]
                if status.get(name, False):
                    # Servicio OK — resetear contador
                    if failure_counts[name] > 0:
                        log(f"✅ {name} recuperado tras {failure_counts[name]} fallos")
                    failure_counts[name] = 0
                else:
                    all_ok = False
                    failure_counts[name] += 1
                    if failure_counts[name] >= max_failures:
                        log(f"⚠️ {name} lleva {failure_counts[name]} fallos consecutivos — reiniciando...")
                        restart_service(svc)
                        failure_counts[name] = max_failures - 1  # Reintentar pronto si falla

            if all_ok:
                # Solo loguear periódicamente cuando todo está bien
                pass  # El check_all ya loguea solo fallos

            time.sleep(interval)

    except KeyboardInterrupt:
        log("🛑 WATCHDOG DETENIDO por el usuario")


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="🛡️ SIMMOON Health Watchdog — Monitor y reinicio automático de servicios"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Un solo chequeo (sin bucle de monitoreo)"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=30, metavar="SECONDS",
        help="Intervalo entre chequeos en modo daemon (default: 30s)"
    )
    parser.add_argument(
        "--max-failures", type=int, default=2, metavar="N",
        help="Fallos consecutivos antes de reiniciar (default: 2)"
    )
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_daemon(interval=args.interval, max_failures=args.max_failures)


if __name__ == "__main__":
    main()
