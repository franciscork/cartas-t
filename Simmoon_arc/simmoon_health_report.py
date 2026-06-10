#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simmoon_health_report.py — Generador de Reporte HTML de Salud del Ecosistema SIMMOON

Este script utiliza las funciones de check_services.py para verificar el estado
de los 6 servicios críticos del ecosistema (Ollama, ComfyUI, PostgreSQL, Dashboard,
InvokeAI, Hermes), lee los ultimos eventos del log del watchdog y genera un
reporte HTML con estilo oscuro moderno, ideal para vista rapida en navegador.

Uso:
    python simmoon_health_report.py

Salida:
    - Archivo: simmoon_health_report.html (en el directorio actual)
    - Mensaje por consola con la ruta absoluta del archivo generado

Autor: Buffy (orquestador SIMMOON) + Claude (asistencia)
Fecha: 2026-06-10
"""

import os
import sys
import json
import html
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# ── Importar funciones de check_services.py ───────────────────────────────
# Se importa el modulo hermano para reutilizar su logica de verificacion.
try:
    import check_services
except ImportError:
    print("ERROR: No se pudo importar check_services.py. Asegurate de que esta en el mismo directorio.", file=sys.stderr)
    sys.exit(1)


# ── Configuracion del reporte ─────────────────────────────────────────────
# Ruta del log del watchdog. Se expande el ~ al home del usuario.
WATCHDOG_LOG_PATH = Path(os.path.expanduser("~/.simmoon-logs/watchdog.log"))
WATCHDOG_LINES_TO_READ = 10  # Numero de ultimas lineas/eventos a incluir

# Ruta de salida del HTML generado
OUTPUT_HTML_PATH = Path(__file__).parent / "simmoon_health_report.html"


# ── Lectura del log del watchdog ──────────────────────────────────────────
def read_watchdog_events(path: Path, max_lines: int = WATCHDOG_LINES_TO_READ) -> List[str]:
    """Leer las ultimas N lineas del log del watchdog.

    Args:
        path: Ruta al archivo de log del watchdog.
        max_lines: Numero maximo de lineas a leer (por defecto 10).

    Returns:
        Lista de strings con las ultimas lineas del log. Si el archivo no
        existe o no se puede leer, devuelve una lista con un mensaje
        informativo.
    """
    if not path.exists():
        return [f"[INFO] Log del watchdog no encontrado en: {path}"]

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            # Leemos todas las lineas y nos quedamos con las ultimas N.
            # Esto es mas robusto que hacer seek() desde el final, que
            # podria partir lineas por la mitad.
            lines = f.readlines()
            return [line.rstrip("\n") for line in lines[-max_lines:]]
    except PermissionError:
        return [f"[ERROR] Sin permisos para leer el log: {path}"]
    except Exception as e:
        return [f"[ERROR] Fallo al leer log: {e}"]


# ── Generacion del HTML ───────────────────────────────────────────────────
def build_html(services: List[Dict], watchdog_events: List[str], generated_at: datetime) -> str:
    """Construir el HTML completo del reporte de salud.

    Args:
        services: Lista de resultados de check_services.check_all().
        watchdog_events: Lista de strings con los ultimos eventos del watchdog.
        generated_at: Datetime con la fecha/hora de generacion del reporte.

    Returns:
        String con el HTML completo listo para escribir a disco.
    """
    # Calcular el resumen X/Y servicios operativos
    healthy_count = sum(1 for s in services if s["healthy"])
    total_count = len(services)
    summary_class = "ok" if healthy_count == total_count else "warn"
    summary_text = f"{healthy_count}/{total_count} servicios operativos"

    # Generar las filas de la tabla de servicios
    service_rows_html = []
    for svc in services:
        # Determinar clase CSS segun estado
        status_class = "status-ok" if svc["healthy"] else "status-fail"
        status_label = "ONLINE" if svc["healthy"] else "OFFLINE"
        status_dot_class = "dot-ok" if svc["healthy"] else "dot-fail"
        # Latencia: si no responde, mostrar "—"
        latency_text = f"{svc['latency_ms']} ms" if svc["healthy"] else "—"
        # Error opcional (solo si existe y no esta vacio)
        error_text = html.escape(svc.get("error", "") or "")
        error_html = f'<div class="err">{error_text}</div>' if error_text and not svc["healthy"] else ""

        service_rows_html.append(f"""
        <tr>
          <td>
            <span class="dot {status_dot_class}"></span>
            <strong>{html.escape(svc['name'])}</strong>
            <div class="desc">{html.escape(svc.get('desc', ''))}</div>
          </td>
          <td><code>:{svc['port']}</code></td>
          <td class="{status_class}"><strong>{status_label}</strong></td>
          <td>{latency_text}</td>
          <td>{error_html}</td>
        </tr>
        """)

    # Generar lista HTML de eventos del watchdog
    if not watchdog_events:
        events_html = '<li class="empty">Sin eventos recientes del watchdog</li>'
    else:
        events_html = "\n".join(
            f'<li>{html.escape(line)}</li>' for line in watchdog_events
        )

    # Timestamp formateado para mostrar
    timestamp_str = generated_at.strftime("%Y-%m-%d %H:%M:%S")

    # Plantilla HTML completa con CSS oscuro embebido
    template = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SIMMOON Health Report</title>
<style>
  :root {{
    --bg: #0d1117;
    --bg-card: #161b22;
    --bg-row: #1c2128;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --accent: #6e40c9;
    --ok: #3fb950;
    --fail: #f85149;
    --warn: #d29922;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "SF Pro Display", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
    margin-bottom: 24px;
  }}
  h1 {{
    margin: 0;
    font-size: 28px;
    font-weight: 600;
    background: linear-gradient(90deg, #6e40c9, #a371f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .timestamp {{ color: var(--text-dim); font-size: 14px; }}
  .summary {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .summary.ok {{ border-left: 4px solid var(--ok); }}
  .summary.warn {{ border-left: 4px solid var(--warn); }}
  .summary .big {{
    font-size: 24px;
    font-weight: 700;
  }}
  .summary .label {{ color: var(--text-dim); font-size: 14px; }}
  section {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 24px;
  }}
  section h2 {{
    margin: 0 0 16px 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  th, td {{
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  th {{
    color: var(--text-dim);
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  tr:hover {{ background: var(--bg-row); }}
  code {{
    background: var(--bg-row);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    color: #a371f7;
  }}
  .dot {{
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: middle;
  }}
  .dot-ok {{ background: var(--ok); box-shadow: 0 0 8px var(--ok); }}
  .dot-fail {{ background: var(--fail); box-shadow: 0 0 8px var(--fail); }}
  .status-ok {{ color: var(--ok); }}
  .status-fail {{ color: var(--fail); }}
  .desc {{ color: var(--text-dim); font-size: 12px; margin-top: 2px; margin-left: 18px; }}
  .err {{ color: var(--fail); font-size: 12px; margin-top: 2px; }}
  .events {{
    list-style: none;
    padding: 0;
    margin: 0;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 13px;
  }}
  .events li {{
    padding: 8px 12px;
    border-left: 3px solid var(--accent);
    background: var(--bg-row);
    margin-bottom: 6px;
    border-radius: 4px;
    word-break: break-all;
  }}
  .events li.empty {{
    border-left-color: var(--text-dim);
    color: var(--text-dim);
    font-style: italic;
  }}
  footer {{
    text-align: center;
    color: var(--text-dim);
    font-size: 12px;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
  }}
</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>☾ SIMMOON Health Report</h1>
      <div class="timestamp">Generado: {timestamp_str}</div>
    </header>

    <div class="summary {summary_class}">
      <div>
        <div class="big">{summary_text}</div>
        <div class="label">Estado general del ecosistema</div>
      </div>
    </div>

    <section>
      <h2>Servicios del Ecosistema</h2>
      <table>
        <thead>
          <tr>
            <th>Servicio</th>
            <th>Puerto</th>
            <th>Estado</th>
            <th>Latencia</th>
            <th>Detalle</th>
          </tr>
        </thead>
        <tbody>
          {''.join(service_rows_html)}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Eventos Recientes del Watchdog</h2>
      <ul class="events">
        {events_html}
      </ul>
    </section>

    <footer>
      SIMMOON_arc · Reporte generado automaticamente · {timestamp_str}
    </footer>
  </div>
</body>
</html>
"""
    return template


# ── Funcion principal ─────────────────────────────────────────────────────
def main() -> int:
    """Punto de entrada principal del script.

    Returns:
        Codigo de salida (0 exito, 1 error).
    """
    print("☾ Generando SIMMOON Health Report...")

    # 1. Verificar servicios usando check_services.py
    try:
        services = check_services.check_all()
    except Exception as e:
        print(f"ERROR al verificar servicios: {e}", file=sys.stderr)
        return 1

    # 2. Leer ultimos eventos del watchdog
    watchdog_events = read_watchdog_events(WATCHDOG_LOG_PATH, WATCHDOG_LINES_TO_READ)

    # 3. Generar timestamp y construir HTML
    now = datetime.now()
    html_content = build_html(services, watchdog_events, now)

    # 4. Escribir archivo HTML
    try:
        OUTPUT_HTML_PATH.write_text(html_content, encoding="utf-8")
    except OSError as e:
        print(f"ERROR al escribir el HTML: {e}", file=sys.stderr)
        return 1

    # 5. Mostrar resumen y ruta del archivo creado
    healthy_count = sum(1 for s in services if s["healthy"])
    total_count = len(services)
    abs_path = OUTPUT_HTML_PATH.resolve()

    print(f"✅ Reporte generado correctamente")
    print(f"   Servicios: {healthy_count}/{total_count} operativos")
    print(f"   Archivo:   {abs_path}")

    # Exit code: 0 siempre que se genere el HTML (el reporte refleja
    # el estado real, no aborta si hay servicios caidos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
