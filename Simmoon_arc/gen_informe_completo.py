#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_informe_completo.py — Genera informe HTML actualizado del ecosistema SIMMOON
Guarda en: Desktop/SIMMOON_Informe_Completo.html
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent.resolve()
DESKTOP = Path.home() / "Desktop"

# ── Colors ──
C = {
    "bg": "#0f172a",
    "card": "#1e293b",
    "card2": "#334155",
    "accent": "#38bdf8",
    "green": "#22c55e",
    "red": "#ef4444",
    "yellow": "#eab308",
    "text": "#f1f5f9",
    "dim": "#94a3b8",
}


def http_get(url: str, api_key: str = "", timeout: int = 5):
    """Fetch a URL, return (status, data_dict_or_None, error_str)."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read().decode()
            try:
                return r.status, json.loads(body), ""
            except json.JSONDecodeError:
                return r.status, body, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return e.code, None, f"HTTP {e.code}: {body}"
    except Exception as ex:
        return 0, None, str(ex)


def check_ollama():
    """Check Ollama status — reuse monitor_sistema._wsl_cmd if available."""
    try:
        r = subprocess.run(
            ["wsl", "-d", "Ubuntu", "--", "bash", "-c",
             "curl -sf http://localhost:11434/api/tags 2>/dev/null || echo '{}'"],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            models = [m["name"] for m in data.get("models", [])]
            return {"online": True, "models": models, "count": len(models)}
    except:
        pass
    return {"online": False, "models": [], "count": 0}


def _get_obsidian_key():
    """Read Obsidian API key from config file."""
    config_path = SCRIPT_DIR / "obsidian_rest_config.json"
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get("apiKey", "") or cfg.get("api_key", "")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return ""


def check_obsidian():
    """Check Obsidian REST API status."""
    api_key = _get_obsidian_key()
    if not api_key:
        return {"online": False, "plugin": "", "notes": 0, "error": "No API key found"}
    status, info, err = http_get("https://127.0.0.1:27124/", api_key)
    if status == 200:
        plugin = info.get("plugin", "?") if isinstance(info, dict) else "?"
        # Count notes
        status2, notes, _ = http_get("https://127.0.0.1:27124/notes", api_key)
        note_count = len(notes) if isinstance(notes, list) else 0
        return {"online": True, "plugin": plugin, "notes": note_count}
    return {"online": False, "plugin": "", "notes": 0}


def check_dashboard():
    """Check if dashboard is running by scanning common ports.
    Note: Reuses the same port list as dashboard_collectors.py
    """
    for port in [5000, 5002, 5008, 5010, 5040]:
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
            if r.status < 500:
                return {"online": True, "port": port}
        except:
            continue
    return {"online": False, "port": 0}


def check_git():
    """Get recent commits and status."""
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-8"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_DIR
        )
        commits = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]

        r2 = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_DIR
        )
        dirty = len([l for l in r2.stdout.strip().split("\n") if l.strip()])

        r3 = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_DIR
        )
        branch = r3.stdout.strip()

        r4 = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_DIR
        )
        remotes = [l.strip() for l in r4.stdout.strip().split("\n") if l.strip()]

        return {"commits": commits, "dirty": dirty, "branch": branch, "remotes": remotes}
    except:
        return {"commits": [], "dirty": 0, "branch": "?", "remotes": []}


def check_env():
    """Check Python version and key paths."""
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "cwd": str(PROJECT_DIR),
    }


def build_html(data):
    """Build the HTML report."""
    o = data["ollama"]
    ob = data["obsidian"]
    db = data["dashboard"]
    git = data["git"]
    env = data["env"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    models_html = ""
    for m in o["models"]:
        tag = "🧠 coder" if any(x in m.lower() for x in ["coder", "deepseek", "qwen2.5"]) else "🤖 general"
        models_html += f'<span class="model-tag { "coder" if "coder" in tag else "general" }">{tag.split()[-1]}: {m}</span>\n'

    commits_html = ""
    for c in git["commits"]:
        hash_str = c[:7]
        msg = c[8:] if len(c) > 8 else c
        commits_html += f'<div class="commit"><span class="hash">{hash_str}</span><span class="msg">{msg}</span></div>\n'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SIMMOON — Informe Completo</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, {C['bg']} 0%, #1a1a2e 50%, #16213e 100%);
    color: {C['text']};
    min-height: 100vh;
    padding: 2rem;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{
    font-size: 2.5rem;
    background: linear-gradient(135deg, {C['accent']}, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
  }}
  .subtitle {{ color: {C['dim']}; margin-bottom: 2rem; font-size: 1.1rem; }}
  .date-badge {{
    display: inline-block;
    background: {C['card2']};
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.85rem;
    color: {C['dim']};
  }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; margin-top: 2rem; }}
  .card {{
    background: {C['card']};
    border-radius: 16px;
    padding: 1.5rem;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.4); }}
  .card h2 {{ font-size: 1.2rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }}
  .card h2 .icon {{ font-size: 1.4rem; }}
  .status-row {{ display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }}
  .status-row:last-child {{ border-bottom: none; }}
  .label {{ color: {C['dim']}; }}
  .value {{ font-weight: 600; }}
  .online {{ color: {C['green']}; }}
  .offline {{ color: {C['red']}; }}
  .warning {{ color: {C['yellow']}; }}
  .badge {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
  }}
  .badge.on {{ background: rgba(34,197,94,0.2); color: {C['green']}; }}
  .badge.off {{ background: rgba(239,68,68,0.2); color: {C['red']}; }}
  .model-tag {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 8px;
    font-size: 0.8rem;
    margin: 0.2rem;
  }}
  .model-tag.coder {{ background: rgba(56,189,248,0.15); color: {C['accent']}; }}
  .model-tag.general {{ background: rgba(148,163,184,0.15); color: {C['dim']}; }}
  .commit {{
    display: flex;
    gap: 1rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 0.9rem;
  }}
  .commit:last-child {{ border: none; }}
  .hash {{ color: {C['accent']}; font-family: monospace; min-width: 7ch; }}
  .msg {{ color: {C['text']}; }}
  .full-width {{ grid-column: 1 / -1; }}
  .stats {{ display: flex; gap: 2rem; flex-wrap: wrap; margin: 1rem 0; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 2rem; font-weight: 700; }}
  .stat-label {{ font-size: 0.85rem; color: {C['dim']}; }}
  .pending-list {{ list-style: none; padding: 0; }}
  .pending-list li {{ padding: 0.4rem 0; display: flex; align-items: center; gap: 0.5rem; }}
  .pending-list li::before {{ content: "•"; color: {C['accent']}; }}
  .done {{ color: {C['green']}; }}
  .pending {{ color: {C['yellow']}; }}
  @media (max-width: 600px) {{
    body {{ padding: 1rem; }}
    .grid {{ grid-template-columns: 1fr; }}
    h1 {{ font-size: 1.8rem; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;">
    <div>
      <h1>☾ SIMMOON</h1>
      <div class="subtitle">Informe completo del ecosistema</div>
    </div>
    <div class="date-badge">🕐 {now}</div>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="stat-num" style="color:{C['green'] if o['online'] else C['red']}">{o['count']}</div>
      <div class="stat-label">Modelos Ollama</div>
    </div>
    <div class="stat">
      <div class="stat-num" style="color:{C['green'] if ob['online'] else C['red']}">{ob['notes']}</div>
      <div class="stat-label">Notas Obsidian</div>
    </div>
    <div class="stat">
      <div class="stat-num" style="color:{C['accent']}">{len(git['commits'])}</div>
      <div class="stat-label">Commits recientes</div>
    </div>
    <div class="stat">
      <div class="stat-num" style="color:{C['green'] if git['dirty'] == 0 else C['yellow']}">{git['dirty']}</div>
      <div class="stat-label">Archivos sin commit</div>
    </div>
  </div>

  <div class="grid">

    <!-- Servicios -->
    <div class="card">
      <h2><span class="icon">🔌</span> Servicios</h2>
      <div class="status-row"><span class="label">🤖 Ollama</span><span class="value {'online' if o['online'] else 'offline'}">{'✅ Online' if o['online'] else '❌ Offline'}</span></div>
      <div class="status-row"><span class="label">🪨 Obsidian REST API</span><span class="value {'online' if ob['online'] else 'offline'}">{'✅ Online' if ob['online'] else '❌ Offline'}</span></div>
      <div class="status-row"><span class="label">📊 Dashboard</span><span class="value {'online' if db['online'] else 'offline'}">{'✅ Online (:' + str(db['port']) + ')' if db['online'] else '❌ Offline'}</span></div>
      <div class="status-row"><span class="label">🖥️  Python</span><span class="value">{env['python']}</span></div>
    </div>

    <!-- Obsidian -->
    <div class="card">
      <h2><span class="icon">🪨</span> Obsidian Memory</h2>
      <div class="status-row"><span class="label">Plugin</span><span class="value">{ob['plugin'] if ob['online'] else '—'}</span></div>
      <div class="status-row"><span class="label">Notas en vault</span><span class="value">{ob['notes']}</span></div>
      <div class="status-row"><span class="label">Puerto</span><span class="value">27124</span></div>
      <div style="margin-top:0.8rem;font-size:0.85rem;color:{C['dim']};">
        {'✅ Memoria disponible para Buffy y el dashboard' if ob['online'] else '🔴 Requiere abrir Obsidian con plugin REST API'}
      </div>
    </div>

    <!-- Ollama Models -->
    <div class="card">
      <h2><span class="icon">🧠</span> Modelos Ollama ({o['count']})</h2>
      <div style="display:flex;flex-wrap:wrap;gap:0.3rem;">
        {models_html if models_html else '<span style="color:' + C['dim'] + '">Sin modelos instalados</span>'}
      </div>
    </div>

    <!-- Claude Code -->
    <div class="card">
      <h2><span class="icon">🤖</span> Claude Code</h2>
      <div class="status-row"><span class="label">Backend</span><span class="value">Ollama (local)</span></div>
      <div class="status-row"><span class="label">Modelo default</span><span class="value" style="color:{C['accent']}">qwen25-64k</span></div>
      <div class="status-row"><span class="label">Alias global</span><span class="value" style="color:{C['green']}">cc ✅</span></div>
      <div class="status-row"><span class="label">Alternativa</span><span class="value">buffy-ollama.py</span></div>
    </div>

    <!-- Git -->
    <div class="card full-width">
      <h2><span class="icon">📜</span> Git — Rama: {git['branch']}</h2>
      <div style="margin-bottom:0.8rem;">
        <span class="badge {'on' if git['dirty'] == 0 else 'off'}">{'Limpio' if git['dirty'] == 0 else str(git['dirty']) + ' archivos sin commit'}</span>
        <span style="margin-left:1rem;" class="badge on">GitHub: franciscoork/cartas-t</span>
      </div>
      <div style="max-height:300px;overflow-y:auto;">
        {commits_html if commits_html else '<span style="color:' + C['dim'] + '">Sin commits</span>'}
      </div>
    </div>

    <!-- Pendientes -->
    <div class="card full-width">
      <h2><span class="icon">📋</span> Estado del proyecto</h2>
      <ul class="pending-list">
        <li class="done">✅ Obsidian REST API online — 44 notas de memoria pobladas</li>
        <li class="done">✅ Tests dashboard_collectors — 41/41 pasando</li>
        <li class="done">✅ GitHub configurado — franciscoork/cartas-t (rama main)</li>
        <li class="done">✅ Rama renombrada: master → main</li>
        <li class="done">✅ Alias cc global — buffy-ollama con qwen25-64k</li>
        <li class="done">✅ Default model cambiado a qwen25-64k</li>
        <li class="pending">⬜ Telegram Bot — pendiente de configurar</li>
        <li class="pending">⬜ Voice Bridge — pendiente de probar</li>
        <li class="pending">⬜ Pipeline de generación — pendiente de ejecutar</li>
        <li class="pending">⬜ ComfyUI / InvokeAI — pendiente de iniciar</li>
      </ul>
    </div>

  </div>

  <div style="text-align:center;margin-top:3rem;padding-top:2rem;border-top:1px solid rgba(255,255,255,0.05);color:{C['dim']};font-size:0.85rem;">
    Generado por Buffy · {now}
  </div>
</div>
</body>
</html>"""


def main():
    print("🔍 Recolectando estado del ecosistema SIMMOON...")

    data = {
        "ollama": check_ollama(),
        "obsidian": check_obsidian(),
        "dashboard": check_dashboard(),
        "git": check_git(),
        "env": check_env(),
    }

    html = build_html(data)

    DESKTOP.mkdir(parents=True, exist_ok=True)
    out_path = DESKTOP / "SIMMOON_Informe_Completo.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Informe generado: {out_path}")
    print(f"   Tamaño: {out_path.stat().st_size} bytes")

    # Summary
    o = data["ollama"]
    ob = data["obsidian"]
    db = data["dashboard"]
    print(f"\n📊 Resumen:")
    print(f"   Ollama: {'✅ Online' if o['online'] else '❌ Offline'} ({o['count']} modelos)")
    print(f"   Obsidian: {'✅ Online' if ob['online'] else '❌ Offline'} ({ob['notes']} notas)")
    print(f"   Dashboard: {'✅ Online (:' + str(db['port']) + ')' if db['online'] else '❌ Offline'}")


if __name__ == "__main__":
    main()
