#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_verify_rest_e2e.py — Verificación end-to-end del Obsidian Local REST API.

Este script confirma que:
  1. El plugin Local REST API está activo y responde en el puerto configurado.
  2. La API key configurada en obsidian_rest_config.json es válida.
  3. Un write de prueba llega al vault REAL (factoryGames-Simmoon),
     NO al fallback filesystem ~/simmoon-memoria.

Uso:
    cd Simmoon_arc
    PYTHONIOENCODING=utf-8 python _verify_rest_e2e.py

Exit codes:
    0 → todo OK, REST API activo y write al vault real verificado
    1 → fallo de conexión (Obsidian no está corriendo o plugin no activo)
    2 → write al REST OK pero archivo NO aparece en disco
    3 → archivo aparece en fallback (~/simmoon-memoria) — routing incorrecto
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "obsidian_rest_config.json"
FALLBACK_VAULT = Path.home() / "simmoon-memoria"
TEST_FILE_PREFIX = "_rest_e2e_test_"
MAX_WRITE_RETRIES = 2  # Tolerar cold start del plugin tras activarlo


def load_config() -> dict:
    """Carga obsidian_rest_config.json desde el directorio del script."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ❌ Error leyendo {CONFIG_PATH}: {e}")
        return {}


def _ssl_ctx() -> ssl.SSLContext:
    """SSL context que ignora verificación (cert self-signed del plugin)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def test_connectivity(base_url: str, api_key: str) -> int:
    """Prueba GET al endpoint raíz del REST API. Retorna 0 si OK, 1 si falla."""
    print(f"  🔌 GET {base_url}/ ...")
    try:
        req = urllib.request.Request(f"{base_url}/", method="GET")
        req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"     ✅ Status: {resp.status}")
            preview = body[:200].replace("\n", " ")
            print(f"     Body preview: {preview!r}")
            return 0
    except urllib.error.HTTPError as e:
        # 401/403 = plugin activo pero API key inválida
        # 404 = plugin activo pero ruta inexistente
        if e.code in (401, 403):
            print(f"     ⚠️  Status {e.code}: plugin activo pero API key rechazada")
            print(f"     → Regenera la API key en Obsidian (plugin settings)")
            return 1
        if e.code == 404:
            print(f"     ✅ Plugin activo (404 en / es esperado, sólo expone /vault/)")
            return 0
        print(f"     ❌ HTTP {e.code}: {e.reason}")
        return 1
    except urllib.error.URLError as e:
        print(f"     ❌ Conexión fallida: {e.reason}")
        print()
        print("  📋 Pasos para activar el plugin:")
        print("     1. Abrir Obsidian sobre el vault 'factoryGames-Simmoon'")
        print("     2. Settings → Community Plugins → activar 'Local REST API'")
        print("     3. Re-ejecutar este script")
        return 1
    except Exception as e:
        print(f"     ❌ Error inesperado: {e}")
        return 1


def test_write(base_url: str, api_key: str, test_path: str,
               content: str) -> int:
    """PUT al REST API para escribir un archivo de prueba. Retorna 0 si OK.

    Reintenta hasta `MAX_WRITE_RETRIES` veces con un sleep entre intentos
    para tolerar el cold start del plugin tras activarlo.
    """
    # URL-encode the path (slashes in vault path)
    encoded_path = urllib.parse.quote(test_path, safe="/")
    url = f"{base_url}/vault/{encoded_path}"
    print(f"  📝 PUT {url} ...")
    last_err = None
    for attempt in range(1, MAX_WRITE_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                data=content.encode("utf-8"),
                method="PUT",
            )
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("Content-Type", "text/markdown")
            with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=10) as resp:
                if attempt > 1:
                    print(f"     (retry {attempt}/{MAX_WRITE_RETRIES} succeeded)")
                print(f"     ✅ Status: {resp.status} (write aceptado por REST)")
                return 0
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"     ❌ HTTP {e.code}: {body[:200]}")
            return 2
        except Exception as e:
            last_err = e
            if attempt < MAX_WRITE_RETRIES:
                wait = 1.5 * attempt
                print(f"     ⚠️  Intento {attempt} falló: {e} (retry en {wait:.1f}s)")
                time.sleep(wait)
            else:
                print(f"     ❌ Error tras {MAX_WRITE_RETRIES} intentos: {e}")
                return 2
    if last_err:
        print(f"     ❌ Último error: {last_err}")
    return 2


def cleanup_previous_tests(real_vault: str) -> int:
    """Borra archivos de prueba previos en el vault real. Retorna cuántos."""
    real_path = Path(real_vault)
    if not real_path.exists():
        return 0
    factorygames_dir = real_path / "FactoryGames"
    if not factorygames_dir.exists():
        return 0
    removed = 0
    for old_test in factorygames_dir.glob(f"{TEST_FILE_PREFIX}*.md"):
        try:
            old_test.unlink()
            removed += 1
        except Exception as e:
            print(f"     ⚠️  No pude borrar {old_test}: {e}")
    if removed:
        print(f"  🧹 Limpiados {removed} archivos de prueba previos")
    return removed


def verify_on_disk(test_path: str, real_vault: str) -> int:
    """Confirma que el archivo escrito aparece en el vault real."""
    expected = Path(real_vault) / test_path.replace("/", os.sep)
    print(f"  🔍 Buscando en vault real: {expected}")
    if expected.exists():
        size = expected.stat().st_size
        print(f"     ✅ Existe, {size} bytes")
        return 0
    print(f"     ❌ NO existe en el vault real")
    return 2


def verify_not_in_fallback(test_path: str) -> int:
    """Confirma que el archivo NO aparece en el fallback ~/simmoon-memoria."""
    fallback = FALLBACK_VAULT / test_path.replace("/", os.sep)
    print(f"  🛡️  Verificando que NO esté en fallback: {fallback}")
    if fallback.exists():
        print(f"     ❌ Aparece en fallback (routing incorrecto)")
        return 3
    print(f"     ✅ No aparece en fallback (correcto)")
    return 0


def main() -> int:
    print(f"  🪨 Verificación end-to-end del Obsidian Local REST API")
    print(f"  {'='*60}")
    print()
    print(f"  ⚠️  IMPORTANTE: este script SOLO VERIFICA el plugin, no lo activa.")
    print(f"  Si el plugin no está activo, los pasos son:")
    print(f"     1. Abrir Obsidian sobre el vault 'factoryGames-Simmoon'")
    print(f"        (si Obsidian abre otro vault, este test probará ese, no el correcto)")
    print(f"     2. Settings → Community Plugins → activar 'Local REST API'")
    print(f"     3. Re-ejecutar este script")
    print()

    cfg = load_config()
    if not cfg:
        print(f"  ❌ No se encontró {CONFIG_PATH}")
        return 1

    base_url = cfg.get("base_url", "")
    api_key = cfg.get("api_key", "")
    real_vault = cfg.get("vault_path", "")

    if not (base_url and api_key and real_vault):
        print(f"  ❌ Config incompleta en {CONFIG_PATH}")
        print(f"     base_url={base_url!r}, api_key={'...' if api_key else ''!r}, vault_path={real_vault!r}")
        return 1

    key_preview = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    print(f"  🔧 Config:")
    print(f"     base_url:    {base_url}")
    print(f"     api_key:     {key_preview}")
    print(f"     vault_path:  {real_vault}")
    print(f"     fallback:    {FALLBACK_VAULT}")
    print()

    # 1. Conectividad
    print(f"  ▶ Paso 1/5: Conectividad REST")
    rc = test_connectivity(base_url, api_key)
    if rc != 0:
        return rc
    print()

    # 2. Write de prueba
    # 0. Limpiar archivos de prueba previos
    print(f"  ▶ Paso 0/5: Limpieza de archivos de prueba previos")
    cleanup_previous_tests(real_vault)
    print()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_path = f"FactoryGames/{TEST_FILE_PREFIX}{timestamp}.md"
    test_content = (
        f"---\n"
        f"date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"tags: [test, rest-api, e2e]\n"
        f"cargado_por: _verify_rest_e2e.py\n"
        f"---\n\n"
        f"# REST API E2E Test\n\n"
        f"Este archivo fue escrito vía REST API para verificar que el\n"
        f"script puede escribir al vault **real** de factoryGames-Simmoon.\n\n"
        f"Si puedes ver este archivo en Obsidian, la integración funciona.\n"
        f"Puedes eliminarlo de forma segura.\n"
    )
    print(f"  ▶ Paso 2/5: Write de prueba")
    rc = test_write(base_url, api_key, test_path, test_content)
    if rc != 0:
        return rc
    print()

    # 3. Verificar en disco
    print(f"  ▶ Paso 3/5: Verificar archivo en vault real")
    rc = verify_on_disk(test_path, real_vault)
    if rc != 0:
        return rc
    print()

    # 4. Verificar que NO esté en fallback
    print(f"  ▶ Paso 4/5: Verificar que NO esté en fallback")
    rc = verify_not_in_fallback(test_path)
    if rc != 0:
        return rc
    print()

    print(f"  🎉 Verificación end-to-end exitosa")
    print(f"     → REST API activo: ✅")
    print(f"     → Write al vault real: ✅")
    print(f"     → Sin fallback a filesystem: ✅")
    print(f"     → Archivo de prueba: {test_path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  🛑 Interrumpido")
        sys.exit(130)
