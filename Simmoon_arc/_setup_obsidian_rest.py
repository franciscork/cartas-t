#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_setup_obsidian_rest.py — Asistente para configurar la REST API de Obsidian

Detecta la instalación de Obsidian, encuentra el vault real, valida la
configuración existente, intenta conectar con el plugin Local REST API
y guía al usuario en los pasos manuales restantes.

Uso:
    python _setup_obsidian_rest.py              # Diagnóstico + auto-fix
    python _setup_obsidian_rest.py --test       # Solo probar conexión
    python _setup_obsidian_rest.py --api-key KEY   # Guardar API key
    python _setup_obsidian_rest.py --vault PATH    # Cambiar vault
"""
import sys
import os
import json
import ssl
import socket
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "obsidian_rest_config.json"
ENV_FILE = SCRIPT_DIR / ".env.obsidian"

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ── Default vault search paths (Windows-first) ─────────────────────────────
DEFAULT_VAULT_CANDIDATES = [
    Path(os.path.expanduser("~")) / "Documents" / "_obsidian_FG-S" / "factoryGames-Simmoon",
    Path(os.path.expanduser("~")) / "Documents" / "ObsidianVault",
    Path(os.path.expanduser("~")) / "Documents" / "Obsidian",
    Path(os.path.expanduser("~")) / "simmoon-memoria",  # fallback filesystem vault
]

OBSIDIAN_EXE_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Obsidian" / "Obsidian.exe",
    Path("C:/Program Files/Obsidian/Obsidian.exe"),
    Path("C:/Program Files (x86)/Obsidian/Obsidian.exe"),
]


def detect_obsidian_install() -> dict:
    """Detecta si Obsidian está instalado en Windows."""
    info = {
        "installed": False,
        "exe_path": None,
        "vaults": [],
    }
    for cand in OBSIDIAN_EXE_CANDIDATES:
        if cand.exists():
            info["installed"] = True
            info["exe_path"] = str(cand)
            break

    # Buscar vaults en la config global de Obsidian
    obsidian_config = Path(os.environ.get("APPDATA", "")) / "obsidian" / "obsidian.json"
    if obsidian_config.exists():
        try:
            with open(obsidian_config, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for v in cfg.get("vaults", {}).values():
                    if v.get("path"):
                        info["vaults"].append({
                            "name": v.get("name", "?"),
                            "path": v.get("path"),
                            "open": bool(v.get("open", False)),
                        })
        except Exception:
            pass

    return info


def detect_real_vault() -> tuple[Optional[Path], Optional[str]]:
    """Encuentra el vault real de Obsidian (no el fallback ~/simmoon-memoria).

    Returns:
        (vault_path, vault_name) — path y nombre interno registrado en Obsidian.
        Si no se encuentra, devuelve (None, None).
    """
    obsidian_info = detect_obsidian_install()
    # Preferir vaults registrados en Obsidian (no el fallback)
    for v in obsidian_info.get("vaults", []):
        p = Path(v["path"])
        if p.exists() and "simmoon-memoria" not in str(p):
            return p, v.get("name", p.name)
    # Fallback a candidatos
    for cand in DEFAULT_VAULT_CANDIDATES:
        if cand.exists() and cand.is_dir() and "simmoon-memoria" not in str(cand):
            if (cand / ".obsidian").exists():
                return cand, cand.name
    return None, None


def has_rest_api_plugin(vault_path: Path) -> bool:
    """Verifica si el plugin Local REST API está instalado en el vault."""
    plugin_dir = vault_path / ".obsidian" / "plugins" / "obsidian-local-rest-api"
    return plugin_dir.exists() and (plugin_dir / "main.js").exists()


def load_config() -> dict:
    """Carga obsidian_rest_config.json o devuelve defaults."""
    defaults = {
        "api_key": "",
        "base_url": "https://127.0.0.1:27124",
        "https": True,
        "port": 27124,
        "vault_name": "simmoon-memoria",
        "vault_path": str(Path.home() / "simmoon-memoria"),
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**defaults, **json.load(f)}
        except Exception as e:
            print(f"  ⚠️  No se pudo leer {CONFIG_PATH}: {e}")
    return defaults


def save_config(cfg: dict) -> bool:
    """Guarda obsidian_rest_config.json."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Config guardada en {CONFIG_PATH}")
        return True
    except Exception as e:
        print(f"  ❌ Error guardando config: {e}")
        return False


def write_env_file(cfg: dict) -> bool:
    """Crea .env.obsidian con permisos 600 (solo owner lee/escribe)."""
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Obsidian Local REST API config\n")
            f.write(f"# Generado por _setup_obsidian_rest.py\n")
            f.write(f"OBSIDIAN_REST_API_KEY={cfg.get('api_key', '')}\n")
            f.write(f"OBSIDIAN_REST_PORT={cfg.get('port', 27124)}\n")
            f.write(f"OBSIDIAN_REST_HTTPS={'true' if cfg.get('https') else 'false'}\n")
        # Permisos 600: solo el owner puede leer/escribir (protege la API key)
        try:
            os.chmod(ENV_FILE, 0o600)
        except Exception:
            pass  # En Windows el chmod es no-op, no es bloqueante
        print(f"  ✅ .env.obsidian creado en {ENV_FILE} (permisos 600)")
        return True
    except Exception as e:
        print(f"  ⚠️  No se pudo crear .env.obsidian: {e}")
        return False


def test_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Prueba si un puerto está abierto."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def test_rest_api(cfg: dict, timeout: float = 5.0) -> dict:
    """Intenta conectar con la REST API de Obsidian."""
    base_url = cfg.get("base_url", "https://127.0.0.1:27124")
    api_key = cfg.get("api_key", "")
    https = cfg.get("https", True)

    result = {
        "connected": False,
        "vault_info": None,
        "error": None,
    }

    if not api_key:
        result["error"] = "API key vacía"
        return result

    # Intentar petición al endpoint raíz
    url = f"{base_url}/"
    try:
        ctx = None
        if https:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status == 200:
                result["connected"] = True
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    result["vault_info"] = json.loads(body)
                except Exception:
                    result["vault_info"] = body[:200]
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.reason}"
        if e.code == 401:
            result["error"] += " — API key inválida"
    except urllib.error.URLError as e:
        result["error"] = f"Connection error: {e.reason}"
    except Exception as e:
        result["error"] = str(e)

    return result


def print_instructions():
    """Imprime instrucciones para el setup manual."""
    print("""
  ┌─────────────────────────────────────────────────────────────┐
  │  📋 PASOS MANUALES REQUERIDOS                               │
  ├─────────────────────────────────────────────────────────────┤
  │  1. Abre Obsidian con el vault correcto                     │
  │  2. Settings → Community plugins → habilita "Local REST API"│
  │  3. Click en el plugin → copia la API Key                  │
  │  4. Pega la key aquí:                                       │
  │     python _setup_obsidian_rest.py --api-key <TU_KEY>       │
  │  5. Verifica conexión:                                      │
  │     python _setup_obsidian_rest.py --test                   │
  │                                                              │
  │  Si Obsidian no está corriendo, el plugin no responderá.   │
  │  Asegúrate de tener Obsidian ABIERTO con el vault activo.   │
  └─────────────────────────────────────────────────────────────┘
""")


def main():
    parser = argparse.ArgumentParser(
        description="Asistente para configurar Obsidian Local REST API"
    )
    parser.add_argument("--api-key", default=None, help="Guardar API key")
    parser.add_argument("--vault", default=None, help="Ruta al vault real de Obsidian")
    parser.add_argument("--vault-name", default=None, help="Nombre del vault (interno Obsidian)")
    parser.add_argument("--port", type=int, default=None, help="Puerto REST (27123 HTTP, 27124 HTTPS)")
    parser.add_argument("--no-https", action="store_true", help="Usar HTTP en vez de HTTPS")
    parser.add_argument("--test", action="store_true", help="Solo probar conexión")
    parser.add_argument("--write-env", action="store_true", help="Crear .env.obsidian")
    args = parser.parse_args()

    print("\n  🪨 Obsidian Local REST API — Setup\n")

    # ── Modo test ──
    if args.test:
        cfg = load_config()
        print(f"  Config cargada: {CONFIG_PATH}")
        print(f"  base_url: {cfg.get('base_url')}")
        print(f"  vault: {cfg.get('vault_name')}")
        print(f"  api_key: {cfg.get('api_key', '')[:10]}...")
        print()
        port = cfg.get("port", 27124)
        print(f"  🔌 Probando puerto {port}...")
        if test_port("127.0.0.1", port):
            print(f"     ✅ Puerto abierto")
        else:
            print(f"     ❌ Puerto cerrado (¿Obsidian está corriendo?)")
            return 1
        print(f"  🌐 Probando REST API...")
        result = test_rest_api(cfg)
        if result["connected"]:
            print(f"     ✅ Conectado!")
            if result["vault_info"]:
                print(f"     📁 Vault: {result['vault_info']}")
        else:
            print(f"     ❌ {result['error']}")
        return 0 if result["connected"] else 1

    # ── Diagnóstico completo ──
    cfg = load_config()
    obs_info = detect_obsidian_install()
    real_vault, real_vault_name = detect_real_vault()
    has_plugin = has_rest_api_plugin(real_vault) if real_vault else False

    print("  ┌─ Diagnóstico ──────────────────────────────────┐")
    print(f"  │ Obsidian instalado:    {'✅ Sí' if obs_info['installed'] else '❌ No'}")
    if obs_info["exe_path"]:
        print(f"  │ Ejecutable:            {obs_info['exe_path']}")
    if obs_info["vaults"]:
        print(f"  │ Vaults registrados:    {len(obs_info['vaults'])}")
        for v in obs_info["vaults"][:3]:
            mark = "📂" if v["open"] else "📁"
            print(f"  │   {mark} {v['name']} → {v['path']}")
    print(f"  │")
    print(f"  │ Vault real detectado:  {real_vault or '❌ No encontrado'}")
    print(f"  │ Plugin REST API:       {'✅ Instalado' if has_plugin else '❌ NO instalado'}")
    print(f"  │")
    print(f"  │ Config actual:")
    print(f"  │   api_key:     {cfg.get('api_key', '(vacía)')[:12]}...")
    print(f"  │   base_url:    {cfg.get('base_url')}")
    print(f"  │   vault_name:  {cfg.get('vault_name')}")
    print(f"  └────────────────────────────────────────────────┘")
    print()

    # ── Auto-fix config ──
    changed = False
    current_vault_name = cfg.get("vault_name", "")
    if real_vault and (real_vault_name != current_vault_name or
                       "simmoon-memoria" in current_vault_name):
        new_name = real_vault_name or real_vault.name
        if args.vault_name:
            new_name = args.vault_name
        print(f"  🔧 Actualizando vault_name: {current_vault_name} → {new_name}")
        cfg["vault_name"] = new_name
        cfg["vault_path"] = str(real_vault)
        changed = True

    if args.vault:
        cfg["vault_path"] = args.vault
        cfg["vault_name"] = Path(args.vault).name
        changed = True
        print(f"  🔧 vault_path actualizado: {args.vault}")

    if args.api_key:
        cfg["api_key"] = args.api_key
        changed = True
        print(f"  🔧 api_key actualizada: {args.api_key[:10]}...")

    if args.port:
        cfg["port"] = args.port
        cfg["https"] = (args.port == 27124) and not args.no_https
        cfg["base_url"] = f"{'https' if cfg['https'] else 'http'}://127.0.0.1:{args.port}"
        changed = True
        print(f"  🔧 Puerto: {args.port} ({'HTTPS' if cfg['https'] else 'HTTP'})")

    if args.no_https and not args.port:
        cfg["https"] = False
        cfg["port"] = 27123
        cfg["base_url"] = "http://127.0.0.1:27123"
        changed = True
        print(f"  🔧 Cambiado a HTTP :27123")

    if changed:
        save_config(cfg)
        if args.write_env:
            write_env_file(cfg)
    else:
        print(f"  ℹ️  Sin cambios en config")

    # ── Test conexión ──
    print()
    port = cfg.get("port", 27124)
    print(f"  🔌 Probando conexión al puerto {port}...")
    if not test_port("127.0.0.1", port):
        print(f"     ❌ Puerto {port} cerrado")
        print()
        print("  💡 Posibles causas:")
        print("     • Obsidian no está abierto")
        print(f"     • El plugin 'obsidian-local-rest-api' no está habilitado")
        print(f"     • El plugin está escuchando en otro puerto")
        print()
        if not has_plugin:
            print("  ⚠️  El plugin NO está instalado en el vault.")
            print("     Descárgalo desde: https://github.com/coddingtonbear/obsidian-local-rest-api")
            print("     Y cópialo a: <vault>/.obsidian/plugins/obsidian-local-rest-api/")
        else:
            print_instructions()
        return 1

    print(f"     ✅ Puerto abierto, probando REST API...")
    result = test_rest_api(cfg)
    if result["connected"]:
        print(f"     ✅ Conexión exitosa")
        if result["vault_info"]:
            print(f"     📁 Vault info: {json.dumps(result['vault_info'], indent=2)[:300]}")
        print()
        print("  🎉 ¡Configuración lista! Los scripts usarán la REST API")
        print("     en vez del fallback filesystem.")
        return 0
    else:
        print(f"     ❌ {result['error']}")
        print()
        print("  💡 La API key puede ser incorrecta o estar caducada.")
        print("     Re-genera la key en Obsidian → Settings → Local REST API")
        print_instructions()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
