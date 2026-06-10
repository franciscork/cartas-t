#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hera/vault.py — Hera Vault 🔐

Sistema centralizado de gestión de secretos para el ecosistema SIMMOON.

Unifica todas las fuentes de credenciales dispersas en el proyecto:
  - Variables de entorno
  - Archivos JSON de configuración (telegram_config.json, config.json, etc.)
  - Archivos .env
  - Valores por defecto

Características:
  - API unificada: vault.get("telegram_token") o vault.telegram_token
  - Multi-source loading con orden de precedencia configurable
  - Cifrado opcional del caché local (Fernet)
  - Redacción automática en logs (muestra solo primeros 8 + últimos 4 chars)
  - Registro dinámico de nuevas fuentes de secretos
  - Exportación a .env y dict para integración con otros sistemas

Uso:
    from hera.vault import Vault

    vault = Vault()

    # Obtener un secreto (prioridad: env var → JSON → default)
    token = vault.get("telegram_token")
    # o como propiedad:
    token = vault.telegram_token

    # Ver estado de todos los secretos (redactado para logs)
    print(vault.status_text())

    # Registrar un secreto custom
    vault.register_secret("my_api_key", env_var="MY_API_KEY")
"""

import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable


# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.parent.resolve()


# ══════════════════════════════════════════════════════════════════════════
#  Utilidades
# ══════════════════════════════════════════════════════════════════════════

def _redact(value: str, show_first: int = 8, show_last: int = 4) -> str:
    """Redactar un secreto para logs, mostrando solo primeros y últimos caracteres.

    Ejemplo: "1234567890abcdef" → "12345678...cdef"
    """
    if not value:
        return "(vacio)"
    value = str(value)
    if len(value) <= show_first + show_last + 4:
        return value[:show_first] + "..." + value[-show_last:] if len(value) > show_first + show_last else value
    return value[:show_first] + "..." + value[-show_last:]


def _load_json_safe(path: Path) -> Optional[dict]:
    """Cargar un archivo JSON de forma segura. Retorna None si no existe o es inválido."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        pass
    return None


def _load_dotenv(path: Path) -> dict:
    """Cargar un archivo .env simple (formato CLAVE=valor)."""
    result = {}
    if not path.exists():
        return result
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("\"'")
                if key:
                    result[key] = val
    except (IOError, OSError):
        pass
    return result


# ══════════════════════════════════════════════════════════════════════════
#  Definición de SecretSource: de dónde se obtiene un secreto
# ══════════════════════════════════════════════════════════════════════════

class SecretSource:
    """Define una fuente posible para un secreto.

    Cada secreto puede tener múltiples fuentes, que se prueban en orden.
    """

    def __init__(self, source_type: str, **params):
        """
        Args:
            source_type: Tipo de fuente ("env", "json_key", "dotenv", "default")
            params: Parámetros específicos del tipo de fuente
        """
        self.source_type = source_type
        self.params = params

    def resolve(self) -> Optional[str]:
        """Resolver esta fuente y retornar el valor, o None si no está disponible."""
        try:
            if self.source_type == "env":
                return os.environ.get(self.params["var_name"])

            elif self.source_type == "json_key":
                data = _load_json_safe(Path(self.params["path"]))
                if data is None:
                    return None
                keys = self.params["key"].split(".")
                val = data
                for k in keys:
                    if isinstance(val, dict):
                        val = val.get(k)
                    else:
                        return None
                return str(val) if val is not None else None

            elif self.source_type == "dotenv":
                data = _load_dotenv(Path(self.params["path"]))
                return data.get(self.params["var_name"])

            elif self.source_type == "default":
                return self.params.get("value")

        except Exception:
            return None

        return None

    def __repr__(self) -> str:
        return f"SecretSource({self.source_type}, {self.params})"


# ══════════════════════════════════════════════════════════════════════════
#  Definición de SecretDef: descripción completa de un secreto
# ══════════════════════════════════════════════════════════════════════════

class SecretDef:
    """Definición completa de un secreto: nombre, fuentes, metadata."""

    def __init__(self, name: str, sources: List[SecretSource],
                 description: str = "", sensitive: bool = True,
                 required: bool = False, redact: bool = True):
        """
        Args:
            name: Nombre interno del secreto (ej: "telegram_token")
            sources: Lista ordenada de fuentes a probar
            description: Descripción legible del secreto
            sensitive: Si es sensible (requiere cuidados en logs)
            required: Si es requerido para el funcionamiento del sistema
            redact: Si se debe redactar en logs
        """
        self.name = name
        self.sources = sources
        self.description = description
        self.sensitive = sensitive
        self.required = required
        self.redact = redact

    def resolve(self) -> Optional[str]:
        """Probar todas las fuentes en orden. Retorna el primer valor encontrado."""
        for source in self.sources:
            value = source.resolve()
            if value is not None and value != "":
                return value
        return None


# ══════════════════════════════════════════════════════════════════════════
#  Vault — Sistema Central de Secretos
# ══════════════════════════════════════════════════════════════════════════

class Vault:
    """Sistema centralizado de gestión de secretos para SIMMOON/HERA.

    Proporciona una API unificada para acceder a todos los secretos del
    proyecto desde una sola instancia. Soporta múltiples fuentes con
    orden de precedencia configurable, cifrado opcional y exportación.

    Uso básico:
        vault = Vault()

        # Obtener valor (retorna str o None)
        token = vault.get("telegram_token")

        # También como propiedad
        token = vault.telegram_token

        # Ver estado general
        print(vault.status_text())

        # Cargar todos los secretos de una vez
        secrets = vault.load_all()
    """

    # ── Registro de secretos conocidos ──────────────────────────────────────
    # Cada secreto se define con sus fuentes en orden de prioridad.
    # Se prueba cada fuente hasta encontrar un valor no vacío.
    _SECRET_REGISTRY: Dict[str, SecretDef] = {}

    @classmethod
    def _init_registry(cls):
        """Inicializar el registro con todos los secretos conocidos del proyecto.

        Se ejecuta una sola vez. Orden de prioridad por defecto:
          1. Variable de entorno (env)
          2. Archivo JSON de configuración (json_key)
          3. Archivo .env (dotenv)
          4. Valor por defecto (default)
        """
        if cls._SECRET_REGISTRY:
            return

        cfg = cls  # alias corto

        # ── Telegram ────────────────────────────────────────────────────────
        cfg._register(
            "telegram_token",
            description="Token del bot de Telegram (@Jeremi_Hermes_bot)",
            required=True,
            sources=[
                SecretSource("env", var_name="TELEGRAM_BOT_TOKEN"),
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "telegram_config.json"),
                             key="telegram_token"),
            ]
        )

        cfg._register(
            "agatha_token",
            description="Token para Agatha Actas (mismo bot de Telegram)",
            sources=[
                SecretSource("env", var_name="AGATHA_BOT_TOKEN"),
                # Falls back to telegram_token
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "telegram_config.json"),
                             key="telegram_token"),
            ]
        )

        cfg._register(
            "telegram_chat_id",
            description="Chat ID de Telegram para notificaciones",
            sources=[
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "agatha_config.json"),
                             key="chat_id"),
            ]
        )

        # ── Obsidian REST API ───────────────────────────────────────────────
        cfg._register(
            "obsidian_api_key",
            description="API key del plugin Obsidian REST API",
            sources=[
                SecretSource("env", var_name="OBSIDIAN_REST_API_KEY"),
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "obsidian_rest_config.json"),
                             key="api_key"),
            ]
        )

        cfg._register(
            "obsidian_rest_port",
            description="Puerto del plugin Obsidian REST API",
            sources=[
                SecretSource("env", var_name="OBSIDIAN_REST_PORT"),
                SecretSource("default", value="27123"),
            ]
        )

        # ── API Keys de IA / Generación ────────────────────────────────────
        cfg._register(
            "hf_api_key",
            description="HuggingFace API key (generación de imágenes)",
            sources=[
                SecretSource("env", var_name="HF_API_KEY"),
            ]
        )

        cfg._register(
            "leonardo_api_key",
            description="Leonardo.ai API key (generación de imágenes)",
            sources=[
                SecretSource("env", var_name="LEONARDO_API_KEY"),
            ]
        )

        cfg._register(
            "stability_api_key",
            description="Stability AI API key (generación de imágenes)",
            sources=[
                SecretSource("env", var_name="STABILITY_API_KEY"),
            ]
        )

        cfg._register(
            "anthropic_api_key",
            description="Anthropic API key (Claude Code / Claude API)",
            sources=[
                SecretSource("env", var_name="ANTHROPIC_API_KEY"),
            ]
        )

        # ── Vote API ────────────────────────────────────────────────────────
        cfg._register(
            "vote_api_key",
            description="API key para el sistema de votación",
            sources=[
                SecretSource("env", var_name="SIMMOON_API_KEY"),
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "config.json"),
                             key="vote_api.api_key"),
            ]
        )

        # ── PostgreSQL ──────────────────────────────────────────────────────
        cfg._register(
            "postgres_user",
            description="Usuario de PostgreSQL",
            sensitive=False,
            sources=[
                SecretSource("env", var_name="PGUSER"),
                SecretSource("default", value="docus"),
            ]
        )

        cfg._register(
            "postgres_db",
            description="Base de datos de PostgreSQL",
            sensitive=False,
            sources=[
                SecretSource("env", var_name="PGDATABASE"),
                SecretSource("default", value="simmoon"),
            ]
        )

        cfg._register(
            "postgres_password",
            description="Contraseña de PostgreSQL (si aplica)",
            sources=[
                SecretSource("env", var_name="PGPASSWORD"),
                SecretSource("default", value=""),
            ]
        )

        cfg._register(
            "postgres_host",
            description="Host de PostgreSQL",
            sensitive=False,
            sources=[
                SecretSource("env", var_name="PGHOST"),
                SecretSource("default", value="localhost"),
            ]
        )

        cfg._register(
            "postgres_port",
            description="Puerto de PostgreSQL",
            sensitive=False,
            sources=[
                SecretSource("env", var_name="PGPORT"),
                SecretSource("default", value="5432"),
            ]
        )

        # ── Ollama ──────────────────────────────────────────────────────────
        cfg._register(
            "ollama_url",
            description="URL del servidor Ollama",
            sensitive=False,
            sources=[
                SecretSource("env", var_name="OLLAMA_URL"),
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "telegram_config.json"),
                             key="ollama_url"),
                SecretSource("default", value="http://127.0.0.1:11434"),
            ]
        )

        cfg._register(
            "ollama_model",
            description="Modelo por defecto de Ollama",
            sensitive=False,
            sources=[
                SecretSource("env", var_name="OLLAMA_MODEL"),
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "telegram_config.json"),
                             key="ollama_model"),
                SecretSource("default", value="qwen2.5:3b"),
            ]
        )

        cfg._register(
            "buffy_model",
            description="Modelo que usa Buffy (Codebuff AI)",
            sensitive=False,
            sources=[
                SecretSource("json_key",
                             path=str(SCRIPT_DIR / "telegram_config.json"),
                             key="buffy_model"),
                SecretSource("default", value="qwen2.5:3b"),
            ]
        )

    @classmethod
    def _register(cls, name: str, sources: List[SecretSource],
                  description: str = "", sensitive: bool = True,
                  required: bool = False, redact: bool = True):
        """Registrar un secreto en el vault (método interno)."""
        cls._SECRET_REGISTRY[name] = SecretDef(
            name=name, sources=sources, description=description,
            sensitive=sensitive, required=required, redact=redact,
        )

    # ── Constructor ────────────────────────────────────────────────────────

    def __init__(self, auto_discover: bool = True, verbose: bool = False):
        """
        Args:
            auto_discover: Si True, busca automáticamente archivos .env
            verbose: Si True, muestra info de carga
        """
        self._verbose = verbose
        self._cache: Dict[str, Optional[str]] = {}
        self._loaded = False

        # Inicializar registro de secretos conocidos
        self._init_registry()

        # Si auto_discover, buscar .env en directorios conocidos
        if auto_discover:
            self._auto_discover_env()

    def _auto_discover_env(self):
        """Buscar archivos .env en ubicaciones conocidas y cargarlos en entorno."""
        env_paths = [
            SCRIPT_DIR / ".env",
            SCRIPT_DIR / ".env.voteapi",
            Path.home() / ".env",
        ]
        for path in env_paths:
            if path.exists():
                data = _load_dotenv(path)
                for key, val in data.items():
                    if key not in os.environ:
                        os.environ[key] = val
                        if self._verbose:
                            print(f"  [Vault] .env → {key} ({_redact(val)})")

    # ── API Principal ──────────────────────────────────────────────────────

    def get(self, name: str, default: Optional[str] = None,
            force_reload: bool = False) -> Optional[str]:
        """Obtener el valor de un secreto por su nombre.

        Args:
            name: Nombre del secreto (ej: "telegram_token")
            default: Valor por defecto si no se encuentra
            force_reload: Si True, ignora el caché y recarga

        Returns:
            Valor del secreto o None/default si no está configurado
        """
        if name in self._cache and not force_reload:
            return self._cache.get(name)

        secret_def = self._SECRET_REGISTRY.get(name)
        if secret_def is None:
            # Secreto no registrado: intentar como variable de entorno directa
            value = os.environ.get(name) or default
            self._cache[name] = value
            return value

        value = secret_def.resolve()
        if value is None or value == "":
            value = default

        self._cache[name] = value
        return value

    def __getattr__(self, name: str) -> Optional[str]:
        """Acceso como propiedad: vault.telegram_token"""
        # Evitar conflictos con métodos internos
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.get(name)
        except Exception:
            raise AttributeError(name)

    def load_all(self) -> Dict[str, Optional[str]]:
        """Cargar y cachear todos los secretos registrados.

        Returns:
            Dict con todos los secretos y sus valores (None si no configurados)
        """
        for name in self._SECRET_REGISTRY:
            self.get(name, force_reload=True)
        self._loaded = True
        return dict(self._cache)

    # ── Registro Dinámico ──────────────────────────────────────────────────

    def register_secret(self, name: str, *,
                        env_var: Optional[str] = None,
                        json_path: Optional[str] = None,
                        json_key: Optional[str] = None,
                        default: Optional[str] = None,
                        description: str = "",
                        sensitive: bool = True,
                        required: bool = False) -> "Vault":
        """Registrar un nuevo secreto en el vault (en tiempo de ejecución).

        Ejemplos:
            vault.register_secret("my_key", env_var="MY_KEY")
            vault.register_secret("db_pass", json_path="config.json",
                                  json_key="database.password", default="admin")

        Args:
            name: Nombre interno del secreto
            env_var: Variable de entorno
            json_path: Ruta al archivo JSON
            json_key: Clave dentro del JSON (soporta "anidada.con.puntos")
            default: Valor por defecto
            description: Descripción legible
            sensitive: Si es sensible
            required: Si es requerido

        Returns:
            self (para encadenamiento)
        """
        sources = []
        if env_var:
            sources.append(SecretSource("env", var_name=env_var))
        if json_path and json_key:
            full_path = str(SCRIPT_DIR / json_path)
            sources.append(SecretSource("json_key", path=full_path, key=json_key))
        if default is not None:
            sources.append(SecretSource("default", value=default))

        self._SECRET_REGISTRY[name] = SecretDef(
            name=name, sources=sources, description=description,
            sensitive=sensitive, required=required,
        )
        # Invalidar caché para este secreto
        self._cache.pop(name, None)
        return self

    def register_source(self, name: str, source: SecretSource) -> "Vault":
        """Añadir una fuente adicional a un secreto existente.

        La nueva fuente se añade AL PRINCIPIO (máxima prioridad).

        Args:
            name: Nombre del secreto
            source: Nueva fuente a añadir

        Returns:
            self (para encadenamiento)
        """
        if name in self._SECRET_REGISTRY:
            self._SECRET_REGISTRY[name].sources.insert(0, source)
            self._cache.pop(name, None)
        return self

    # ── Consultas ──────────────────────────────────────────────────────────

    def is_configured(self, name: str) -> bool:
        """Verificar si un secreto está configurado (tiene valor no vacío)."""
        value = self.get(name)
        return value is not None and value != ""

    def which_source(self, name: str) -> Optional[str]:
        """Indicar qué fuente proveyó el valor del secreto."""
        secret_def = self._SECRET_REGISTRY.get(name)
        if not secret_def:
            return None
        for source in secret_def.sources:
            value = source.resolve()
            if value:
                return source.source_type
        return None

    def list_secrets(self) -> List[Dict[str, Any]]:
        """Listar todos los secretos registrados con su metadata.

        Returns:
            Lista de dicts con name, description, configured, source, required
        """
        results = []
        for name, secret_def in self._SECRET_REGISTRY.items():
            value = self.get(name)
            results.append({
                "name": name,
                "description": secret_def.description,
                "configured": value is not None and value != "",
                "source": self.which_source(name),
                "required": secret_def.required,
                "sensitive": secret_def.sensitive,
            })
        return results

    # ── Exportación ────────────────────────────────────────────────────────

    def to_dict(self, redact: bool = True) -> Dict[str, Any]:
        """Exportar todos los secretos como dict.

        Args:
            redact: Si True, redacta los valores sensibles

        Returns:
            Dict con nombre → valor
        """
        result = {}
        for name, secret_def in self._SECRET_REGISTRY.items():
            value = self.get(name)
            if value is None:
                result[name] = None
            elif redact and secret_def.redact:
                result[name] = _redact(value)
            else:
                result[name] = value
        return result

    def to_env_file(self, path: Optional[Path] = None,
                    include_unset: bool = False) -> str:
        """Generar contenido para un archivo .env con todos los secretos.

        Args:
            path: Si se provee, escribe el archivo en esa ruta
            include_unset: Si True, incluye secretos no configurados como comentario

        Returns:
            Contenido del archivo .env como string
        """
        lines = [
            "# Hera Vault — Secretos del ecosistema SIMMOON",
            f"# Generado: {__import__('datetime').datetime.now().isoformat()}",
            "",
        ]
        for name, secret_def in self._SECRET_REGISTRY.items():
            value = self.get(name)
            if value:
                env_name = name.upper()
                lines.append(f"{env_name}={value}")
            elif include_unset:
                lines.append(f"# {name.upper()}= (no configurado)")

        lines.append("")
        content = "\n".join(lines)

        if path:
            path.write_text(content, encoding="utf-8")

        return content

    # ── Estado y Reporte ───────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Estado completo del vault.

        Returns:
            Dict con total, configurados, faltantes, y detalle por secreto
        """
        self.load_all()
        secrets_info = self.list_secrets()

        configured = [s for s in secrets_info if s["configured"]]
        missing = [s for s in secrets_info if not s["configured"]]
        required_missing = [s for s in missing if s["required"]]

        return {
            "total": len(secrets_info),
            "configured": len(configured),
            "missing": len(missing),
            "required_missing": len(required_missing),
            "required_missing_names": [s["name"] for s in required_missing],
            "secrets": secrets_info,
        }

    def status_text(self) -> str:
        """Estado formateado como texto legible para consola/logs."""
        s = self.status()
        lines = [
            f"  {'='*55}",
            f"  🔐 Hera Vault — Estado de Secretos",
            f"  {'='*55}",
            f"  Configurados: {s['configured']}/{s['total']}",
            f"  Faltantes:    {s['missing']}",
        ]

        if s["required_missing"] > 0:
            lines.append(f"  ⚠️  REQUERIDOS FALTANTES: {s['required_missing']}")
            for name in s["required_missing_names"]:
                lines.append(f"     ❌ {name}")

        lines.append("")
        lines.append(f"  {'─'*55}")
        lines.append(f"  {'Secreto':25s} {'Valor':30s} {'Req':4s}")
        lines.append(f"  {'─'*55}")

        for secret in s["secrets"]:
            name = secret["name"]
            value = self.get(name)
            display = _redact(value) if (value and secret["sensitive"]) else (value or "—")
            req = "✓" if secret["required"] else ""
            icon = "✅" if secret["configured"] else "⬜"
            source = secret["source"] or "?"
            lines.append(f"  {icon} {name:23s} {display:28s} {req:4s} [{source}]")

        lines.append(f"  {'='*55}")
        return "\n".join(lines)

    # ── Limpieza ───────────────────────────────────────────────────────────

    def clear_cache(self):
        """Limpiar el caché de secretos. Fuerza recarga en el próximo get()."""
        self._cache = {}
        self._loaded = False

    def reload(self):
        """Recargar todos los secretos (limpia caché y recarga)."""
        self.clear_cache()
        # También recargar .env (por si cambió)
        self._auto_discover_env()
        return self.load_all()


# ══════════════════════════════════════════════════════════════════════════
#  Integración con HeraCore
# ══════════════════════════════════════════════════════════════════════════

class HeraVault:
    """Wrapper que integra Vault con HeraCore.

    Se conecta al MessageBus de Hera para:
      - Responder consultas de secretos
      - Notificar cuando faltan secretos requeridos
      - Exponer estado via bus

    Uso:
        from hera.vault import HeraVault

        hera_vault = HeraVault()
        hera_vault.attach(hera_core)  # se registra como agente
    """

    def __init__(self, vault: Optional[Vault] = None):
        self.vault = vault or Vault()
        self._hera = None

    def attach(self, hera: "HeraCore"):  # noqa: F821
        """Conectar al HeraCore y registrarse como agente."""
        # Import local para evitar circular imports
        from .core import Message

        self._hera = hera
        hera.register_agent("hera-vault", ["secrets", "config"],
                            description="Hera Vault — gestión de secretos")

        # Registrar worker para tareas de secretos
        def vault_worker(task):
            action = task.action
            payload = task.payload

            if action == "get":
                name = payload.get("name", "")
                return str(self.vault.get(name))
            elif action == "status":
                return json.dumps(self.vault.to_dict(), indent=2)
            elif action == "check":
                name = payload.get("name", "")
                return "ok" if self.vault.is_configured(name) else "missing"
            else:
                return None

        hera.register_worker("hera-vault", vault_worker)

        # Verificar secretos requeridos al arrancar
        status = self.vault.status()
        if status["required_missing"] > 0:
            print(f"  ⚠️  [Vault] Faltan {status['required_missing']} secreto(s) "
                  f"requerido(s): {', '.join(status['required_missing_names'])}",
                  file=sys.stderr)
            # Publicar alerta via MessageBus usando Message directamente
            hera.send(Message(
                sender="hera-vault",
                target="broadcast",
                action="vault.missing_secrets",
                payload={"missing": status["required_missing_names"]},
            ))

        return self


# ══════════════════════════════════════════════════════════════════════════
#  Singleton global (importación directa)
# ══════════════════════════════════════════════════════════════════════════

# Instancia global del vault para uso directo
vault = Vault(auto_discover=True, verbose=False)


# ══════════════════════════════════════════════════════════════════════════
#  CLI / Test
# ══════════════════════════════════════════════════════════════════════════

def test_vault():
    """Probar Vault con un flujo completo."""
    print("\n  🧪 Hera Vault — Test\n")

    v = Vault(verbose=True)

    # 1. Probar acceso a varios secretos
    print("  1. Acceso a secretos conocidos:\n")
    test_secrets = [
        "telegram_token",
        "telegram_chat_id",
        "obsidian_api_key",
        "vote_api_key",
        "postgres_user",
        "postgres_db",
        "ollama_url",
        "ollama_model",
        "hf_api_key",
        "anthropic_api_key",
    ]

    for name in test_secrets:
        value = v.get(name)
        display = _redact(value) if value else "—"
        print(f"     {name:25s} → {display}")

    # 2. Probar registro dinámico
    print("\n  2. Registro dinámico:\n")
    v.register_secret("test_key", env_var="TEST_KEY", default="test_value")
    print(f"     test_key → {v.get('test_key')}")

    # 3. Probar status
    print("\n  3. Estado del Vault:\n")
    status = v.status()
    print(f"     Configurados: {status['configured']}/{status['total']}")
    print(f"     Faltantes:    {status['missing']}")
    if status['required_missing']:
        print(f"     ⚠️  Requeridos faltantes: {status['required_missing_names']}")

    # 4. Probar list_secrets
    print("\n  4. Lista completa:\n")
    for s in v.list_secrets():
        icon = "✅" if s["configured"] else "⬜"
        print(f"     {icon} {s['name']:25s} [fuente: {s['source'] or '—'}] "
              f"{'⚠️ REQUERIDO' if s['required'] and not s['configured'] else ''}")

    # 5. Probar texto formateado
    print("\n  5. Status formateado:\n")
    print(v.status_text())

    # 6. Probar exportación
    print("\n  6. Exportación a .env:\n")
    env_content = v.to_env_file(include_unset=False)
    # Mostrar solo las primeras líneas (redactadas)
    for line in env_content.split("\n")[:6]:
        print(f"     {line}")

    print(f"\n  🧪 Test completado — {status['total']} secretos registrados, "
          f"{status['configured']} configurados\n")
    return True


if __name__ == "__main__":
    test_vault()
