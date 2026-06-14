#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obsidian_memory.py — 🪨 Memoria Externa para Buffy usando Obsidian

Permite a Buffy usar un vault de Obsidian como sistema de memoria persistente,
con frontmatter YAML, tags, búsqueda-fulltext y sincronización opcional
con PostgreSQL.

Dos modos de operación:
1. **REST API** (por defecto): usa el plugin Obsidian Local REST API
   (https://github.com/coddingtonbear/obsidian-local-rest-api)
   → más rápido, sin archivos duplicados, usa el vault real de Obsidian

2. **Filesystem directo** (fallback): escribe archivos .md directamente al disco
   → útil para testing o si no está instalado el plugin

Uso básico:
    from obsidian_memory import ObsidianMemory

    # Con REST API (recomendado)
    memory = ObsidianMemory(rest_port=27123, rest_api_key="tu-api-key")
    memory.save("sesion_2026-06-09", "Renderizador extraído", tipo="fact",
                tags=["refactor"])

    # Sin REST API (fallback a archivos)
    memory = ObsidianMemory(vault_path="~/simmoon-memoria")

    contexto = memory.get_context(days=7)
    resultados = memory.search("votos")
    memory.boot()

CLI:
    python obsidian_memory.py --init
    python obsidian_memory.py --save key contenido --save-type fact
    python obsidian_memory.py --get key
    python obsidian_memory.py --recent 7
    python obsidian_memory.py --search texto
    # Con REST API:
    python obsidian_memory.py --rest --rest-api-key abc123 --save key contenido
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Soft deps: YAML frontmatter ───────────────────────────────────────────
try:
    import yaml as _yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

try:
    import frontmatter as _fm
    _FM_OK = True
except ImportError:
    _FM_OK = False


# ── Constants: frontmatter safety ───────────────────────────────────────
# Allowlist explícita de meta-keys que save_diaria() promueve al frontmatter
# de las diarias. Evita leak accidental de secretos (api_key, token, etc.) y
# errores de serialización YAML con tipos no soportados (datetime, Path, set,
# bytes). Cubre las necesidades de _cargar_ayer_obsidian.py
# (system_events/system_sources) y los metadatos canónicos (tags/created_by).
_ALLOWED_DIARIA_PASSTHROUGH_KEYS = frozenset({
    "system_events", "system_sources", "tags", "created_by",
})
# Tipos seguros para serialización YAML. bool es subclase de int en Python,
# pero lo listamos explícitamente por claridad. type(None) cubre None.
_SAFE_YAML_TYPES = (str, int, float, bool, list, dict, type(None))


# ── Helper: parse JSON safely ────────────────────────────────────────────
def _try_parse_json(val: Any) -> Any:
    """Try to parse a JSON string; return as-is on failure."""
    if not isinstance(val, str):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, ValueError):
        return val


def _to_str(val: Any) -> str:
    """Convert any value to string, handling datetime.date objects from YAML."""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)


# ── Minimal YAML frontmatter parser (fallback) ────────────────────────────
def _parse_frontmatter(text: str) -> Tuple[dict, str]:
    """Parse YAML frontmatter from markdown text.

    Returns (metadata_dict, body_text). Uses python-frontmatter if available,
    falls back to regex-based YAML parsing.
    """
    if _FM_OK:
        try:
            post = _fm.loads(text)
            return dict(post.metadata), post.content
        except Exception:
            pass

    text = text.lstrip("\ufeff")  # BOM
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end < 0:
        return {}, text

    yaml_block = text[3:end].strip()
    body = text[end + 3:].lstrip("\n")

    metadata = {}
    if _YAML_OK:
        try:
            metadata = _yaml.safe_load(yaml_block) or {}
            return metadata, body
        except Exception:
            pass

    for line in yaml_block.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("\"'").strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("\"'") for v in val[1:-1].split(",")]
            elif val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            else:
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
            metadata[key] = val

    return metadata, body


def _dump_frontmatter(metadata: dict, body: str = "") -> str:
    """Build markdown text with YAML frontmatter."""
    if not metadata:
        return body
    if _FM_OK:
        try:
            post = _fm.Post(body, **metadata)
            return _fm.dumps(post)
        except Exception:
            pass
    lines = ["---"]
    for key, val in metadata.items():
        if isinstance(val, list):
            items = ", ".join(f'"{v}"' for v in val)
            lines.append(f"{key}: [{items}]")
        elif isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, (int, float)):
            lines.append(f"{key}: {val}")
        else:
            lines.append(f"{key}: {str(val)}")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(lines)


# ── ObsidianRestClient: HTTP wrapper para el plugin Local REST API ────────
class ObsidianRestClient:
    """Cliente HTTP para el plugin Obsidian Local REST API.

    Wrapper ligero sobre urllib que expone todas las operaciones del vault
    via REST: leer, escribir, eliminar, listar y buscar notas.

    El plugin escucha en:
      - http://127.0.0.1:27123 (HTTP plano)
      - https://127.0.0.1:27124 (HTTPS con certificado autofirmado)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 27123,
                 api_key: Optional[str] = None, use_https: bool = False):
        """Inicializar cliente REST.

        Args:
            host: Host del plugin (default: 127.0.0.1)
            port: Puerto (27123 HTTP, 27124 HTTPS)
            api_key: API key del plugin (requerida)
            use_https: Usar HTTPS en vez de HTTP
        """
        self.host = host
        self.port = port
        self.api_key = api_key or ""
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}:{port}"

        # HTTPS con certificado autofirmado → no verificar
        self.ssl_ctx = None
        if use_https:
            self.ssl_ctx = ssl.create_default_context()
            self.ssl_ctx.check_hostname = False
            self.ssl_ctx.verify_mode = ssl.CERT_NONE

        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "text/markdown; charset=utf-8",
        }

    def _request(self, method: str, path: str,
                 data: Optional[str] = None,
                 extra_headers: Optional[dict] = None) -> Tuple[int, Union[str, dict, None]]:
        """Ejecutar una request HTTP y devolver (status_code, body_parsed).

        Args:
            method: GET, PUT, DELETE, POST
            path: Ruta del endpoint (ej: /vault/Buffy/fact/test.md)
            data: Body para PUT/POST en texto plano
            extra_headers: Headers adicionales

        Returns:
            Tuple de (status_code, parsed_response). Para GET devuelve str,
            para JSON devuelve dict, para errores devuelve None.
        """
        url = f"{self.base_url}{path}"
        headers = dict(self._headers)
        if extra_headers:
            headers.update(extra_headers)

        body_bytes = data.encode("utf-8") if data else None
        req = urllib.request.Request(url, data=body_bytes, headers=headers,
                                     method=method)

        try:
            ctx = self.ssl_ctx
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                status = resp.status

                if "application/json" in content_type:
                    return status, json.loads(raw.decode("utf-8"))
                else:
                    return status, raw.decode("utf-8")
        except urllib.error.HTTPError as e:
            body_raw = e.read()
            try:
                body = json.loads(body_raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = body_raw.decode("utf-8", errors="replace") if body_raw else None
            return e.code, body
        except urllib.error.URLError as e:
            return 0, f"Connection error: {e.reason}"
        except Exception as e:
            return 0, str(e)

    def is_available(self) -> bool:
        """Verificar si el plugin REST API está corriendo y accesible."""
        status, body = self._request("GET", "/")
        return status == 200

    # ── CRUD operations ────────────────────────────────────────────────

    def read_note(self, vault_path: str) -> Tuple[bool, Optional[str]]:
        """Leer el contenido de una nota markdown.

        Args:
            vault_path: Ruta relativa al vault (ej: Buffy/fact/test.md)

        Returns:
            (success, content_string_or_None)
        """
        status, body = self._request("GET", f"/vault/{vault_path.lstrip('/')}")
        if status == 200 and isinstance(body, str):
            return True, body
        return False, None

    def write_note(self, vault_path: str, content: str) -> bool:
        """Crear o sobrescribir una nota markdown.

        Args:
            vault_path: Ruta relativa al vault
            content: Contenido markdown completo (frontmatter + body)

        Returns:
            True si se escribió correctamente
        """
        status, _ = self._request("PUT", f"/vault/{vault_path.lstrip('/')}",
                                  data=content)
        return 200 <= status < 300

    def delete_note(self, vault_path: str) -> bool:
        """Eliminar una nota markdown del vault.

        Args:
            vault_path: Ruta relativa al vault

        Returns:
            True si se eliminó correctamente
        """
        status, _ = self._request("DELETE", f"/vault/{vault_path.lstrip('/')}")
        return status == 200

    def note_exists(self, vault_path: str) -> bool:
        """Verificar si una nota existe."""
        status, _ = self._request("GET", f"/vault/{vault_path.lstrip('/')}")
        return status == 200

    # ── List / Search ──────────────────────────────────────────────────

    def list_notes(self, prefix: str = "") -> List[str]:
        """Listar notas en el vault, opcionalmente filtradas por prefijo.

        El plugin REST API devuelve solo items del nivel consultado
        (no es recursivo). Por eso, si hay prefijo, consultamos
        /vault/{prefijo} directamente en vez de /vault/.

        Args:
            prefix: Prefijo de ruta (ej: Buffy/fact/)

        Returns:
            Lista de rutas relativas completas de archivos .md
        """
        endpoint = "/vault/"
        if prefix:
            prefix = prefix.replace("\\", "/").strip("/")
            endpoint = f"/vault/{prefix}/"

        status, body = self._request("GET", endpoint)
        if status != 200 or not isinstance(body, (list, dict)):
            return []

        # La API puede devolver {"files": [...]} o una lista plana
        if isinstance(body, dict):
            files = body.get("files", [])
        elif isinstance(body, list):
            files = body
        else:
            return []
        # Reconstruir rutas completas relativas al vault
        if prefix:
            files = [f"{prefix}/{f}" for f in files if isinstance(f, str)]
        return [f for f in files if isinstance(f, str) and f.endswith(".md")]

    def search(self, query: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Buscar notas por texto (búsqueda simple).

        Args:
            query: Texto a buscar
            limit: Máximo de resultados

        Returns:
            Lista de notas que coinciden, con metadatos básicos
        """
        import urllib.parse
        encoded = urllib.parse.quote(query)
        status, body = self._request("POST",
                                     f"/search/simple/?query={encoded}&maxresults={limit}")
        if status != 200:
            return []
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            return body.get("results", body.get("data", []))
        return []

    # ── Patch operations (frontmatter / headings) ──────────────────────

    def patch_note(self, vault_path: str, operation: str,
                   target_type: str, target: str,
                   content: str) -> bool:
        """Modificar una sección específica de una nota sin sobrescribirla.

        Args:
            vault_path: Ruta relativa al vault
            operation: append, prepend, replace
            target_type: frontmatter, heading
            target: Nombre del heading o clave del frontmatter
            content: Nuevo contenido

        Returns:
            True si se parcheó correctamente
        """
        headers = {
            "Operation": operation,
            "Target-Type": target_type,
            "Target": target,
        }
        status, _ = self._request("PATCH",
                                  f"/vault/{vault_path.lstrip('/')}",
                                  data=content,
                                  extra_headers=headers)
        return 200 <= status < 300


# ── ObsidianMemory Class ───────────────────────────────────────────────────
class ObsidianMemory:
    """Sistema de memoria externa usando Obsidian.

    Opera en dos modos:
    1. REST API (modo primario): se conecta al plugin Local REST API de Obsidian
       para leer/escribir directamente en el vault de Obsidian.
    2. Filesystem (fallback): escribe archivos .md en una carpeta local.

    Estructura del vault (en ambos modos):
        {vault}/
        ├── Buffy/
        │   ├── facts/
        │   ├── context/
        │   ├── preferences/
        │   ├── tasks/
        │   ├── results/
        │   ├── errors/
        │   └── conversations/
        ├── Agentes/
        ├── Diarias/
        └── Proyecto/
    """

    MEMORY_TYPES = ["context", "fact", "preference", "task", "result", "error", "conversation"]
    REST_DEFAULT_PORT = 27123
    REST_DEFAULT_HTTPS_PORT = 27124

    def __init__(self, vault_path: Optional[str] = None, agent_name: str = "Buffy",
                 project: str = "SIMMOON",
                 rest_port: Optional[int] = None,
                 rest_api_key: Optional[str] = None,
                 rest_https: bool = False,
                 rest_host: str = "127.0.0.1"):
        """Inicializar memoria Obsidian.

        Args:
            vault_path: Ruta al vault (default: ~/simmoon-memoria).
                        Solo usado en modo filesystem.
            agent_name: Nombre del agente (Buffy, Claude-Code, etc.)
            project: Proyecto asociado
            rest_port: Puerto del plugin REST API. Si se pasa, activa modo REST.
            rest_api_key: API key del plugin REST API.
            rest_https: Usar HTTPS en vez de HTTP.
            rest_host: Host del plugin (default: 127.0.0.1)
        """
        self.agent_name = agent_name
        self.project = project

        # ── Modo REST API ──
        use_rest = rest_port is not None
        self.rest_client: Optional[ObsidianRestClient] = None
        self.rest_available = False

        if use_rest:
            self.rest_client = ObsidianRestClient(
                host=rest_host,
                port=rest_port,
                api_key=rest_api_key or "",
                use_https=rest_https,
            )
            self.rest_available = self.rest_client.is_available()
            if not self.rest_available:
                print(f"[WARN] REST API en {rest_host}:{rest_port} no responde. "
                      f"Usando fallback a filesystem.")
                self.rest_client = None

        # ── Ruta del vault ──
        if vault_path:
            self.vault_path = Path(vault_path).expanduser().resolve()
        else:
            self.vault_path = Path.home() / "simmoon-memoria"

        # Crear estructura de directorios (solo si no estamos en modo REST)
        if not self.rest_available:
            self._ensure_vault()

    def _ensure_vault(self):
        """Crear la estructura del vault si no existe (solo filesystem)."""
        dirs = [
            self.vault_path / "Buffy" / t for t in self.MEMORY_TYPES
        ] + [
            self.vault_path / "Agentes",
            self.vault_path / "Diarias",
            self.vault_path / "Proyecto",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _rel_path(self, key_name: str, memory_type: str = "context") -> str:
        """Generar ruta relativa para REST API (estilo Unix).

        Formato: Buffy/{type}/{YYYY-MM-DD}_{key}.md
        """
        today = datetime.now().strftime("%Y-%m-%d")
        safe_key = re.sub(r'[^\w\-_ ]', '_', key_name)[:60]
        return f"Buffy/{memory_type}/{today}_{safe_key}.md"

    def _local_path(self, key_name: str, memory_type: str = "context") -> Path:
        """Generar ruta absoluta local para filesystem.

        Formato: {vault}/Buffy/{type}/{YYYY-MM-DD}_{key}.md
        """
        return self.vault_path / self._rel_path(key_name, memory_type)

    def _build_metadata(self, key_name: str, memory_type: str = "context",
                        tags: Optional[List[str]] = None,
                        importance: int = 3,
                        related_agent: Optional[str] = None,
                        content_json: Optional[dict] = None) -> dict:
        """Construir frontmatter estándar para una entrada de memoria."""
        now = datetime.now().isoformat()
        metadata = {
            "key": key_name,
            "type": memory_type,
            "agent": self.agent_name,
            "project": self.project,
            "importance": importance,
            "created": now,
            "updated": now,
        }
        if tags:
            metadata["tags"] = tags
        if related_agent:
            metadata["related_agent"] = related_agent
        if content_json:
            metadata["content_json"] = json.dumps(content_json, ensure_ascii=False)
        return metadata

    # ── Backend: read / write / delete ──────────────────────────────────

    def _read_markdown(self, key_name: str, memory_type: str) -> Optional[str]:
        """Leer contenido markdown desde el backend activo."""
        if self.rest_available and self.rest_client:
            rel = self._rel_path(key_name, memory_type)
            ok, text = self.rest_client.read_note(rel)
            return text if ok else None
        else:
            fp = self._local_path(key_name, memory_type)
            if not fp.exists():
                return None
            try:
                return fp.read_text(encoding="utf-8")
            except Exception:
                return None

    def _write_markdown(self, key_name: str, memory_type: str, text: str) -> bool:
        """Escribir contenido markdown al backend activo."""
        if self.rest_available and self.rest_client:
            rel = self._rel_path(key_name, memory_type)
            return self.rest_client.write_note(rel, text)
        else:
            fp = self._local_path(key_name, memory_type)
            try:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(text, encoding="utf-8")
                return True
            except Exception as e:
                print(f"[ERROR] No se pudo guardar en {fp}: {e}")
                return False

    def _delete_markdown(self, key_name: str, memory_type: str) -> bool:
        """Eliminar archivo markdown del backend activo."""
        if self.rest_available and self.rest_client:
            rel = self._rel_path(key_name, memory_type)
            return self.rest_client.delete_note(rel)
        else:
            fp = self._local_path(key_name, memory_type)
            if not fp.exists():
                return False
            try:
                fp.unlink()
                return True
            except Exception:
                return False

    def _markdown_exists(self, key_name: str, memory_type: str) -> bool:
        """Verificar si existe una entrada markdown."""
        if self.rest_available and self.rest_client:
            rel = self._rel_path(key_name, memory_type)
            return self.rest_client.note_exists(rel)
        else:
            return self._local_path(key_name, memory_type).exists()

    # ── Backend: list / scan ────────────────────────────────────────────

    def _list_markdown(self, memory_type: Optional[str] = None) -> List[Tuple[str, str]]:
        """Listar archivos en el vault, devolviendo (ruta_relativa, tipo_memoria)."""
        results: List[Tuple[str, str]] = []

        if self.rest_available and self.rest_client:
            # REST API: listar con prefijo
            types_to_scan = [memory_type] if memory_type else self.MEMORY_TYPES
            for mt in types_to_scan:
                prefix = f"Buffy/{mt}/"
                files = self.rest_client.list_notes(prefix=prefix)
                for f in files:
                    results.append((f, mt))
        else:
            # Filesystem: glob
            types_to_scan = [memory_type] if memory_type else self.MEMORY_TYPES
            for mt in types_to_scan:
                d = self.vault_path / "Buffy" / mt
                if not d.exists():
                    continue
                for fp in sorted(d.glob("*.md"), reverse=True):
                    rel = str(fp.relative_to(self.vault_path)).replace("\\", "/")
                    results.append((rel, mt))

        return results

    def _parse_memory_from_text(self, text: str, filepath: str,
                                 memory_type: str) -> Dict[str, Any]:
        """Parsear texto markdown a dict de memoria."""
        metadata, body = _parse_frontmatter(text)
        filename = Path(filepath).stem
        return {
            "key_name": metadata.get("key", filename),
            "content": body.strip(),
            "memory_type": metadata.get("type", memory_type),
            "tags": metadata.get("tags", []),
            "importance": metadata.get("importance", 3),
            "agent": metadata.get("agent", self.agent_name),
            "project": metadata.get("project", self.project),
            "related_agent": metadata.get("related_agent"),
            "created_at": metadata.get("created", ""),
            "updated_at": metadata.get("updated", ""),
            "filepath": filepath,
            "content_json": _try_parse_json(metadata.get("content_json")),
        }

    def _parse_memory_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Parsear un archivo markdown local a dict de memoria."""
        if not filepath.exists():
            return None
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception:
            return None
        mt = filepath.parent.name  # contexto, fact, etc.
        rel = str(filepath.relative_to(self.vault_path)).replace("\\", "/")
        return self._parse_memory_from_text(text, rel, mt)

    def _scan_memories(self, memory_type: Optional[str] = None,
                       days: Optional[int] = None,
                       limit: int = 50) -> List[Dict[str, Any]]:
        """Escanear memorias en el vault (ambos backends)."""
        memories: List[Dict[str, Any]] = []

        if self.rest_available and self.rest_client:
            # REST API: listar + leer cada nota
            entries = self._list_markdown(memory_type)
            for rel, mt in entries:
                ok, text = self.rest_client.read_note(rel)
                if not ok or text is None:
                    continue
                mem = self._parse_memory_from_text(text, rel, mt)

                # Filtrar por días (parsear del frontmatter)
                if days is not None and mem["created_at"]:
                    try:
                        created = datetime.fromisoformat(mem["created_at"])
                        if created < datetime.now() - timedelta(days=days):
                            continue
                    except (ValueError, TypeError):
                        pass

                memories.append(mem)
                if len(memories) >= limit:
                    break
        else:
            # Filesystem
            if memory_type:
                search_dirs = [self.vault_path / "Buffy" / memory_type]
            else:
                search_dirs = [self.vault_path / "Buffy" / t for t in self.MEMORY_TYPES]

            cutoff = None
            if days is not None:
                cutoff = datetime.now() - timedelta(days=days)

            for d in search_dirs:
                if not d.exists():
                    continue
                for f in sorted(d.glob("*.md"), reverse=True):
                    mem = self._parse_memory_file(f)
                    if mem is None:
                        continue
                    if cutoff and mem["created_at"]:
                        try:
                            created = datetime.fromisoformat(mem["created_at"])
                            if created < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    memories.append(mem)
                    if len(memories) >= limit:
                        break
                if len(memories) >= limit:
                    break

        return memories

    # ── Public API ──────────────────────────────────────────────────────

    def save(self, key_name: str, content: str, memory_type: str = "context",
             tags: Optional[List[str]] = None, importance: int = 3,
             related_agent: Optional[str] = None,
             content_json: Optional[dict] = None) -> bool:
        """Guardar una entrada de memoria en el vault Obsidian.

        Args:
            key_name: Identificador único de la memoria
            content: Contenido en texto (markdown)
            memory_type: Tipo: context, fact, preference, task, result, error
            tags: Tags para búsqueda
            importance: 1-5 (5 = máxima importancia)
            related_agent: Agente relacionado
            content_json: Datos estructurados opcionales

        Returns:
            True si se guardó correctamente
        """
        if memory_type not in self.MEMORY_TYPES:
            raise ValueError(f"Tipo inválido: {memory_type}. Usar: {self.MEMORY_TYPES}")

        metadata = self._build_metadata(
            key_name=key_name,
            memory_type=memory_type,
            tags=tags,
            importance=min(max(importance, 1), 5),
            related_agent=related_agent,
            content_json=content_json,
        )

        # Si ya existe, preservar created_at original
        existing_text = self._read_markdown(key_name, memory_type)
        if existing_text:
            existing_meta, _ = _parse_frontmatter(existing_text)
            if existing_meta.get("created"):
                metadata["created"] = existing_meta["created"]

        text = _dump_frontmatter(metadata, content)
        return self._write_markdown(key_name, memory_type, text)

    def save_context(self, key_name: str, content: str, **kwargs) -> bool:
        """Guardar contexto (tipo default)."""
        return self.save(key_name, content, memory_type="context", **kwargs)

    def save_fact(self, key_name: str, content: str, importance: int = 4, **kwargs) -> bool:
        """Guardar un hecho importante."""
        return self.save(key_name, content, memory_type="fact", importance=importance, **kwargs)

    def save_preference(self, key_name: str, content: str, **kwargs) -> bool:
        """Guardar preferencia del usuario."""
        return self.save(key_name, content, memory_type="preference", **kwargs)

    def save_task(self, key_name: str, content: str, **kwargs) -> bool:
        """Guardar estado de tarea."""
        return self.save(key_name, content, memory_type="task", **kwargs)

    def get(self, key_name: str, memory_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Obtener una entrada de memoria por key_name."""
        types_to_search = [memory_type] if memory_type else self.MEMORY_TYPES
        for mt in types_to_search:
            text = self._read_markdown(key_name, mt)
            if text:
                rel = self._rel_path(key_name, mt)
                return self._parse_memory_from_text(text, rel, mt)
        return None

    def get_recent(self, days: int = 7, memory_type: Optional[str] = None,
                   limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener memorias recientes.

        Args:
            days: Días hacia atrás
            memory_type: Filtrar por tipo
            limit: Máximo de resultados

        Returns:
            Lista de memorias ordenadas por importancia descendente
        """
        memories = self._scan_memories(memory_type=memory_type, days=days, limit=limit)
        memories.sort(key=lambda m: (
            m.get("importance", 3) or 3,
            m.get("updated_at", "") or "",
        ), reverse=True)
        return memories[:limit]

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Buscar memorias por texto en contenido y tags.

        En modo REST API, delega al endpoint /search/simple/ del plugin.
        En modo filesystem, hace fulltext scan local.
        """
        # REST API: usar endpoint de búsqueda nativo
        if self.rest_available and self.rest_client:
            raw_results = self.rest_client.search(query, limit=limit)
            parsed = []
            for item in raw_results:
                if isinstance(item, dict):
                    # El endpoint search devuelve {filename, content, score}
                    filename = item.get("filename", "")
                    content = item.get("content", "")
                    # Extraer tipo de la ruta (Buffy/{type}/...)
                    mt = "context"
                    parts = filename.replace("\\", "/").split("/")
                    if "Buffy" in parts:
                        idx = parts.index("Buffy")
                        if idx + 1 < len(parts):
                            mt = parts[idx + 1]
                    parsed.append(self._parse_memory_from_text(
                        content, filename, mt))
            return parsed[:limit]

        # Filesystem: fulltext scan
        query_lower = query.lower()
        results = []
        for t in self.MEMORY_TYPES:
            d = self.vault_path / "Buffy" / t
            if not d.exists():
                continue
            for f in d.glob("*.md"):
                mem = self._parse_memory_file(f)
                if mem is None:
                    continue
                content = (mem.get("content") or "").lower()
                tags = [str(t).lower() for t in (mem.get("tags") or [])]
                key = (mem.get("key_name") or "").lower()
                if (query_lower in content or
                    query_lower in key or
                    any(query_lower in t for t in tags)):
                    results.append(mem)
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
        return results[:limit]

    def search_by_tag(self, tag: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Buscar memorias por tag específico.

        Args:
            tag: Tag a buscar (case-insensitive)
            limit: Máximo de resultados
        """
        tag_lower = tag.lower()
        results = []

        if self.rest_available and self.rest_client:
            # REST API: buscar en contenido + filtrar tags manualmente
            # El endpoint search/simple busca en texto plano, no tags directamente
            raw = self.rest_client.search(tag, limit=limit * 3)
            for item in raw:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename", "")
                content = item.get("content", "")
                meta, _ = _parse_frontmatter(content)
                mem_tags = [str(t).lower() for t in (meta.get("tags") or [])]
                if tag_lower in mem_tags:
                    parts = filename.replace("\\", "/").split("/")
                    mt = "context"
                    if "Buffy" in parts:
                        idx = parts.index("Buffy")
                        if idx + 1 < len(parts):
                            mt = parts[idx + 1]
                    results.append(self._parse_memory_from_text(content, filename, mt))
                if len(results) >= limit:
                    break
        else:
            # Filesystem
            for t in self.MEMORY_TYPES:
                d = self.vault_path / "Buffy" / t
                if not d.exists():
                    continue
                for f in d.glob("*.md"):
                    mem = self._parse_memory_file(f)
                    if mem is None:
                        continue
                    mem_tags = [str(t).lower() for t in (mem.get("tags") or [])]
                    if tag_lower in mem_tags:
                        results.append(mem)
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break

        return results[:limit]

    def delete(self, key_name: str, memory_type: Optional[str] = None) -> bool:
        """Eliminar una entrada de memoria.

        Args:
            key_name: Identificador de la memoria
            memory_type: Tipo (si se conoce, búsqueda más rápida)
        """
        if memory_type:
            return self._delete_markdown(key_name, memory_type)

        for t in self.MEMORY_TYPES:
            if self._markdown_exists(key_name, t):
                return self._delete_markdown(key_name, t)
        return False

    def clear_old(self, days: int = 30) -> int:
        """Eliminar memorias antiguas.

        Args:
            days: Edad máxima en días para conservar

        Returns:
            Cantidad de archivos eliminados
        """
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        if self.rest_available and self.rest_client:
            # REST API: listar + parsear fecha del filename + borrar
            entries = self._list_markdown()
            for rel, mt in entries:
                try:
                    fname = Path(rel).stem
                    date_part = fname[:10]
                    file_date = datetime.strptime(date_part, "%Y-%m-%d")
                    if file_date < cutoff:
                        if self.rest_client.delete_note(rel):
                            deleted += 1
                except (ValueError, IndexError):
                    pass
        else:
            # Filesystem
            for memory_type in self.MEMORY_TYPES:
                d = self.vault_path / "Buffy" / memory_type
                if not d.exists():
                    continue
                for f in d.glob("*.md"):
                    try:
                        fname = f.stem
                        date_part = fname[:10]
                        file_date = datetime.strptime(date_part, "%Y-%m-%d")
                        if file_date < cutoff:
                            f.unlink()
                            deleted += 1
                    except (ValueError, IndexError, OSError):
                        pass

        return deleted

    def get_context(self, days: int = 7, limit: int = 30) -> str:
        """Obtener contexto formateado para Buffy (para context window).

        Returns string formateado con las memorias más importantes.
        """
        memories = self.get_recent(days=days, limit=limit)

        if not memories:
            return f"[{self.agent_name}] 📭 Sin memoria reciente en Obsidian"

        mode = "REST" if self.rest_available else "FS"
        parts = [f"=== 🪨 MEMORIA OBSIDIAN ({self.agent_name}) [{mode}] ==="]
        parts.append(f"📅 Últimos {days} días | {len(memories)} entradas")
        parts.append("")

        by_type: Dict[str, List[Dict]] = {}
        for m in memories:
            t = m.get("memory_type", "context")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m)

        for mem_type, items in by_type.items():
            parts.append(f"[{mem_type.upper()}]")
            for item in items[:8]:
                key = item.get("key_name", "?")
                content = (item.get("content") or "")[:120]
                imp = "⭐" * item.get("importance", 3)
                tags = item.get("tags", [])
                tag_str = f" [#{','.join(tags)}]" if tags else ""
                parts.append(f"  {imp} {key}: {content}{tag_str}")
            parts.append("")

        parts.append("=" * 60)
        return "\n".join(parts)

    def boot(self, days: int = 7) -> str:
        """Cargar contexto completo al iniciar sesión.

        Equivalente a buffy_boot.py pero desde Obsidian.

        Returns:
            Contexto formateado para Buffy
        """
        return self.get_context(days=days)

    def summary(self) -> str:
        """Generar resumen del vault: cantidad de entradas por tipo."""
        stats: Dict[str, int] = {}
        total = 0

        if self.rest_available and self.rest_client:
            # REST API: contar por prefijo
            for memory_type in self.MEMORY_TYPES:
                prefix = f"Buffy/{memory_type}/"
                files = self.rest_client.list_notes(prefix=prefix)
                count = len(files)
                if count > 0:
                    stats[memory_type] = count
                    total += count
            # Contar Diarias
            diarias = self.rest_client.list_notes(prefix="Diarias/")
            d_count = len(diarias)
        else:
            for memory_type in self.MEMORY_TYPES:
                d = self.vault_path / "Buffy" / memory_type
                count = len(list(d.glob("*.md"))) if d.exists() else 0
                if count > 0:
                    stats[memory_type] = count
                    total += count
            diarias = self.vault_path / "Diarias"
            d_count = len(list(diarias.glob("*.md"))) if diarias.exists() else 0

        mode = "REST" if self.rest_available else "FS"
        parts = [f"🪨 RESUMEN DEL VAULT OBSIDIAN [{mode}]", ""]
        parts.append(f"📍 Vault: {self.vault_path}")
        parts.append(f"🤖 Agente: {self.agent_name}")
        parts.append(f"📊 Total entradas: {total}")
        parts.append("")
        for mem_type, count in sorted(stats.items(), key=lambda x: -x[1]):
            parts.append(f"  📁 {mem_type}: {count}")
        parts.append(f"  📅 Diarias: {d_count}")

        return "\n".join(parts)

    # ── Diarias: resúmenes diarios del proyecto ────────────────────────────

    def _diaria_rel_path(self, date_str: str) -> str:
        """Ruta relativa para un archivo de diaria (estilo Unix)."""
        safe_date = re.sub(r'[^\d\-]', '_', date_str)[:10]
        return f"Diarias/{safe_date}.md"

    def _diaria_local_path(self, date_str: str) -> Path:
        """Ruta absoluta local para un archivo de diaria."""
        return self.vault_path / self._diaria_rel_path(date_str)

    def save_diaria(self, date_str: str, title: str, content: str,
                    metadata: Optional[dict] = None) -> bool:
        """Guardar un resumen diario en la carpeta Diarias/ del vault.

        Args:
            date_str: Fecha en formato YYYY-MM-DD
            title: Título del resumen
            content: Contenido markdown del resumen
            metadata: Dict opcional con assets_created, assets_total,
                      services_active, agents_active, alerts_count, tags, etc.

        Returns:
            True si se guardó correctamente
        """
        meta = metadata or {}
        now = datetime.now().isoformat()

        frontmatter = {
            "date": date_str,
            "title": title,
            "type": "diaria",
            "agent": self.agent_name,
            "project": self.project,
            "assets_created": meta.get("assets_created", 0),
            "assets_total": meta.get("assets_total", 0),
            "services_active": meta.get("services_active", 0),
            "services_total": meta.get("services_total", 0),
            "agents_active": meta.get("agents_active", 0),
            "agents_total": meta.get("agents_total", 0),
            "alerts_count": meta.get("alerts_count", 0),
            "created": now,
            "updated": now,
        }
        # Allowlist explícita (ver constantes a nivel de módulo):
        # evita leak de secretos y errores de YAML con tipos no soportados.
        if meta:
            for k, v in meta.items():
                if k in _ALLOWED_DIARIA_PASSTHROUGH_KEYS and k not in frontmatter:
                    if isinstance(v, _SAFE_YAML_TYPES):
                        frontmatter[k] = v

        # Si ya existe, preservar created original
        existing = self._read_diaria(date_str)
        if existing:
            existing_meta, _ = _parse_frontmatter(existing)
            if existing_meta.get("created"):
                frontmatter["created"] = existing_meta["created"]

        text = _dump_frontmatter(frontmatter, content)
        return self._write_diaria(date_str, text)

    def _read_diaria(self, date_str: str) -> Optional[str]:
        """Leer contenido markdown de una diaria."""
        if self.rest_available and self.rest_client:
            rel = self._diaria_rel_path(date_str)
            ok, text = self.rest_client.read_note(rel)
            return text if ok else None
        else:
            fp = self._diaria_local_path(date_str)
            if not fp.exists():
                return None
            try:
                return fp.read_text(encoding="utf-8")
            except Exception:
                return None

    def _write_diaria(self, date_str: str, text: str) -> bool:
        """Escribir archivo de diaria al backend activo."""
        if self.rest_available and self.rest_client:
            rel = self._diaria_rel_path(date_str)
            return self.rest_client.write_note(rel, text)
        else:
            fp = self._diaria_local_path(date_str)
            try:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(text, encoding="utf-8")
                return True
            except Exception as e:
                print(f"[ERROR] No se pudo guardar diaria en {fp}: {e}")
                return False

    def get_diarias(self, days: int = 7, limit: int = 30) -> List[Dict[str, Any]]:
        """Obtener resúmenes diarios desde la carpeta Diarias/ del vault.

        Args:
            days: Días hacia atrás
            limit: Máximo de resultados

        Returns:
            Lista de dicts con date, title, content, metadata
        """
        cutoff = datetime.now() - timedelta(days=days)
        results: List[Dict[str, Any]] = []

        if self.rest_available and self.rest_client:
            files = self.rest_client.list_notes(prefix="Diarias/")
            for rel in files:
                if not rel.endswith(".md"):
                    continue
                ok, text = self.rest_client.read_note(rel)
                if not ok or text is None:
                    continue
                meta, body = _parse_frontmatter(text)
                # YAML puede parsear la fecha como datetime.date → convertir a str
                date_raw = _to_str(meta.get("date", ""))
                try:
                    file_date = datetime.strptime(date_raw[:10], "%Y-%m-%d")
                    if file_date < cutoff:
                        continue
                except (ValueError, IndexError):
                    pass
                results.append(self._parse_diaria(meta, body, rel))
                if len(results) >= limit:
                    break
        else:
            diarias_dir = self.vault_path / "Diarias"
            if diarias_dir.exists():
                for fp in sorted(diarias_dir.glob("*.md"), reverse=True):
                    try:
                        text = fp.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    meta, body = _parse_frontmatter(text)
                    date_raw = _to_str(meta.get("date", ""))
                    try:
                        file_date = datetime.strptime(date_raw[:10], "%Y-%m-%d")
                        if file_date < cutoff:
                            continue
                    except (ValueError, IndexError):
                        pass
                    rel = str(fp.relative_to(self.vault_path)).replace("\\", "/")
                    results.append(self._parse_diaria(meta, body, rel))
                    if len(results) >= limit:
                        break

        return results

    def _parse_diaria(self, metadata: dict, body: str, filepath: str) -> Dict[str, Any]:
        """Parsear frontmatter + body de una diaria a dict estructurado."""
        return {
            "date": _to_str(metadata.get("date", "")),
            "title": _to_str(metadata.get("title", "")),
            "content": body.strip(),
            "assets_created": metadata.get("assets_created", 0),
            "assets_total": metadata.get("assets_total", 0),
            "services_active": metadata.get("services_active", 0),
            "services_total": metadata.get("services_total", 0),
            "agents_active": metadata.get("agents_active", 0),
            "agents_total": metadata.get("agents_total", 0),
            "alerts_count": metadata.get("alerts_count", 0),
            "tags": metadata.get("tags", []),
            "created_by": metadata.get("created_by", ""),
            "created_at": metadata.get("created", ""),
            "filepath": filepath,
        }

    # ── Sincronización con PostgreSQL ──────────────────────────────────────

    def sync_from_postgres(self, agent_filter: Optional[str] = None,
                           days: int = 7) -> int:
        """Sincronizar memorias desde PostgreSQL → Obsidian.

        Incluye tanto agent_memory como daily_summaries.

        Args:
            agent_filter: Sincronizar solo un agente específico
            days: Días hacia atrás

        Returns:
            Cantidad de entradas sincronizadas
        """
        synced = 0

        # ── Parte 1: Agent Memory ──
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from agent_memory import AgentMemory, get_shared_context
        except ImportError:
            print("[ERROR] agent_memory.py no disponible para sync")
        else:
            if agent_filter:
                memories = AgentMemory(agent_filter).get_recent(days=days, limit=100)
            else:
                memories = get_shared_context("SIMMOON", days=days, limit=100)

            tag_suffix = "synced_from_pg"

            for m in memories:
                key = f"pg_{m.get('key_name', 'unknown')}"
                content = m.get("content", "")
                mem_type = m.get("memory_type", "context")
                tags = (m.get("tags") or []) + [tag_suffix]
                importance = m.get("importance", 3)
                related = m.get("agent_name") or m.get("related_agent")

                if self.save(key, content, memory_type=mem_type,
                             tags=tags, importance=importance,
                             related_agent=related):
                    synced += 1

        # ── Parte 2: Daily Summaries → Diarias/ ──
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from agatha_actas import get_recent_summaries
            summaries = get_recent_summaries(days=days)
            for s in summaries:
                date_str = str(s.get("date", ""))[:10]
                if not date_str:
                    continue
                meta = {
                    "assets_created": s.get("assets_created", 0),
                    "assets_total": s.get("assets_total", 0),
                    "services_active": s.get("services_active", 0),
                    "services_total": s.get("services_total", 0),
                    "agents_active": s.get("agents_active", 0),
                    "agents_total": s.get("agents_total", 0),
                    "alerts_count": s.get("alerts_count", 0),
                    "tags": (s.get("tags") or []) + ["synced_from_pg"],
                    "created_by": "Agatha Actas",
                }
                if self.save_diaria(date_str, s.get("title", ""),
                                    s.get("content", ""), meta):
                    synced += 1
        except ImportError:
            pass  # agatha_actas no disponible, sin problema

        return synced

    def sync_to_postgres(self, days: int = 7) -> int:
        """Sincronizar memorias desde Obsidian → PostgreSQL.

        Incluye tanto agent_memory como Diarias/ → daily_summaries.

        Args:
            days: Días hacia atrás

        Returns:
            Cantidad de entradas sincronizadas
        """
        synced = 0

        # ── Parte 1: Agent Memory ──
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from agent_memory import AgentMemory
        except ImportError:
            print("[ERROR] agent_memory.py no disponible para sync")
        else:
            memories = self.get_recent(days=days, limit=100)
            tag_suffix = "synced_from_obsidian"

            for m in memories:
                agent = m.get("agent", "Buffy")
                pg_memory = AgentMemory(agent)
                key = f"obs_{m.get('key_name', 'unknown')}"
                if pg_memory.save(
                    key_name=key,
                    content=m.get("content", ""),
                    memory_type=m.get("memory_type", "context"),
                    tags=(m.get("tags") or []) + [tag_suffix],
                    importance=m.get("importance", 3),
                    related_agent=m.get("related_agent"),
                ):
                    synced += 1

        # ── Parte 2: Diarias/ → daily_summaries ──
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from agatha_actas import save_daily_summary
            diarias = self.get_diarias(days=days, limit=30)
            for d in diarias:
                date_str = d.get("date", "")[:10]
                if not date_str:
                    continue
                meta = {
                    "assets_created": d.get("assets_created", 0),
                    "assets_total": d.get("assets_total", 0),
                    "services_active": d.get("services_active", 0),
                    "services_total": d.get("services_total", 0),
                    "agents_active": d.get("agents_active", 0),
                    "agents_total": d.get("agents_total", 0),
                    "alerts_count": d.get("alerts_count", 0),
                    "tags": (d.get("tags") or []) + ["synced_from_obsidian"],
                }
                if save_daily_summary(date_str, d.get("title", ""),
                                      d.get("content", ""), meta):
                    synced += 1
        except ImportError:
            pass  # agatha_actas no disponible

        return synced

    def sync_bidirectional(self, days: int = 7) -> Dict[str, int]:
        """Sincronización bidireccional completa."""
        return {
            "from_pg": self.sync_from_postgres(days=days),
            "to_pg": self.sync_to_postgres(days=days),
        }


# ── CLI Interface ──────────────────────────────────────────────────────────
def main():
    """Interfaz CLI para obsidian_memory."""
    import argparse

    parser = argparse.ArgumentParser(
        description="obsidian_memory.py — 🪨 Memoria Obsidian para Buffy"
    )
    parser.add_argument("--vault", default=None,
                        help="Ruta al vault Obsidian (default: ~/simmoon-memoria)")
    parser.add_argument("--agent", "-a", default="Buffy",
                        help="Nombre del agente (default: Buffy)")

    # ── REST API flags ──
    rest_group = parser.add_argument_group("REST API (plugin Local REST API)")
    rest_group.add_argument("--rest", action="store_true",
                            help="Usar plugin Local REST API (por defecto usa filesystem)")
    rest_group.add_argument("--rest-port", type=int, default=27123,
                            help="Puerto del plugin (27123 HTTP / 27124 HTTPS)")
    rest_group.add_argument("--rest-api-key", default="",
                            help="API key del plugin Local REST API")
    rest_group.add_argument("--rest-https", action="store_true",
                            help="Usar HTTPS en vez de HTTP")
    rest_group.add_argument("--rest-host", default="127.0.0.1",
                            help="Host del plugin (default: 127.0.0.1)")
    rest_group.add_argument("--rest-check", action="store_true",
                            help="Verificar si el REST API está disponible")

    parser.add_argument("--init", action="store_true",
                        help="Inicializar estructura del vault")

    # Save/get/recent
    parser.add_argument("--save", nargs=2, metavar=("KEY", "CONTENT"),
                        help="Guardar memoria: key content")
    parser.add_argument("--save-type", default="context",
                        choices=ObsidianMemory.MEMORY_TYPES,
                        help="Tipo de memoria para --save")
    parser.add_argument("--save-tags", default="",
                        help="Tags para --save (separados por coma)")
    parser.add_argument("--save-importance", type=int, default=3, choices=range(1, 6),
                        help="Importancia 1-5 (default: 3)")
    parser.add_argument("--get", "-g", help="Obtener memoria por key_name")
    parser.add_argument("--recent", "-r", type=int, nargs="?", const=7, default=0,
                        help="Ver memorias recientes (días)")
    parser.add_argument("--search", "-s", help="Buscar en memorias")
    parser.add_argument("--tag", help="Buscar por tag")
    parser.add_argument("--delete", help="Eliminar memoria por key")
    parser.add_argument("--clear-old", type=int, default=0,
                        help="Eliminar memorias mayores a N días")

    # Context/boot
    parser.add_argument("--context", "-c", action="store_true",
                        help="Contexto formateado para Buffy")
    parser.add_argument("--boot", action="store_true",
                        help="Cargar contexto de inicio (boot)")
    parser.add_argument("--summary", action="store_true",
                        help="Resumen del vault")

    # Sync
    parser.add_argument("--sync-from-pg", action="store_true",
                        help="Sincronizar PostgreSQL → Obsidian")
    parser.add_argument("--sync-to-pg", action="store_true",
                        help="Sincronizar Obsidian → PostgreSQL")
    parser.add_argument("--sync-bidi", action="store_true",
                        help="Sincronización bidireccional")
    parser.add_argument("--sync-days", type=int, default=7,
                        help="Días a sincronizar (default: 7)")

    # Diarias
    parser.add_argument("--save-diaria", nargs=3,
                        metavar=("DATE", "TITLE", "CONTENT"),
                        help="Guardar resumen diario: fecha(YYYY-MM-DD) título contenido")
    parser.add_argument("--diarias", type=int, nargs="?", const=7, default=0,
                        help="Ver resúmenes diarios (días, default: 7)")
    parser.add_argument("--get-diaria", metavar="DATE",
                        help="Obtener diaria por fecha (YYYY-MM-DD)")

    # Filtros
    parser.add_argument("--days", type=int, default=7,
                        help="Días hacia atrás (default: 7)")
    parser.add_argument("--limit", type=int, default=30,
                        help="Límite de resultados (default: 30)")
    parser.add_argument("--type", choices=ObsidianMemory.MEMORY_TYPES,
                        help="Filtrar por tipo de memoria")

    if len(sys.argv) == 1:
        parser.print_help()
        print("\n  Ejemplos:")
        print("    python obsidian_memory.py --init")
        print("    python obsidian_memory.py --save 'refactor' 'ok' --save-type fact")
        print("    python obsidian_memory.py --context")
        print("    python obsidian_memory.py --search 'votos'")
        print("    python obsidian_memory.py --diarias 7")
        print("    python obsidian_memory.py --save-diaria 2026-06-12 'Resumen' 'contenido'")
        print("    # Con REST API:")
        print("    python obsidian_memory.py --rest --rest-api-key abc123 --rest-check")
        print("    python obsidian_memory.py --rest --rest-api-key abc123 --context")
        return

    # ── Parse args ──
    args = parser.parse_args()
    rest_port = args.rest_port if args.rest else None
    memory = ObsidianMemory(
        vault_path=args.vault,
        agent_name=args.agent,
        rest_port=rest_port,
        rest_api_key=args.rest_api_key,
        rest_https=args.rest_https,
        rest_host=args.rest_host,
    )

    mode = "REST" if memory.rest_available else "FS"

    # ── Rest check ──
    if args.rest_check:
        if memory.rest_available:
            print(f"✅ REST API disponible [{memory.rest_client.base_url}]")
        else:
            print(f"❌ REST API NO disponible en {args.rest_host}:{args.rest_port}")
            print("   Asegúrate de que el plugin Local REST API esté instalado")
            print("   y habilitado en Obsidian (Settings → Community plugins).")
        return

    # ── Init vault (solo filesystem) ──
    if args.init:
        if memory.rest_available:
            print("ℹ️  En modo REST API, el vault ya existe en Obsidian. No se necesita init.")
        else:
            memory._ensure_vault()
            print(f"✅ Vault inicializado en: {memory.vault_path}")
            print("📁 Directorios creados:")
            for t in memory.MEMORY_TYPES:
                d = memory.vault_path / "Buffy" / t
                print(f"   📂 {d.relative_to(memory.vault_path)}")
            print("   📂 Diarias/")
            print("   📂 Proyecto/")
        return

    # ── Save ──
    if args.save:
        key, content = args.save
        tags = [t.strip() for t in args.save_tags.split(",") if t.strip()]
        ok = memory.save(key, content, memory_type=args.save_type,
                         tags=tags if tags else None,
                         importance=args.save_importance)
        if ok:
            print(f"✅ Guardado [{mode}]: '{key}' [{args.save_type}]")
            if tags:
                print(f"   Tags: {tags}")
        else:
            print(f"❌ Error al guardar '{key}'")
        return

    # ── Get ──
    if args.get:
        result = memory.get(args.get, memory_type=args.type)
        if result:
            print(f"📄 {result['key_name']} [{result['memory_type']}]")
            print(f"   Importancia: {'⭐' * result['importance']}")
            if result.get("tags"):
                print(f"   Tags: #{', #'.join(result['tags'])}")
            print(f"   Creado: {result['created_at']}")
            print(f"   ---")
            print(result.get("content", ""))
        else:
            print(f"❌ No encontrado: '{args.get}'")
        return

    # ── Search ──
    if args.search:
        results = memory.search(args.search, limit=args.limit)
        print(f"🔍 [{mode}] {len(results)} resultado(s) para '{args.search}':")
        for r in results:
            imp = "⭐" * r["importance"]
            tags = f" [#{', #'.join(r['tags'])}]" if r.get("tags") else ""
            print(f"  {imp} [{r['memory_type']}] {r['key_name']}{tags}")
            print(f"     {(r.get('content') or '')[:100]}")
        return

    # ── Tag search ──
    if args.tag:
        results = memory.search_by_tag(args.tag, limit=args.limit)
        print(f"🏷️  [{mode}] {len(results)} resultado(s) con tag '{args.tag}':")
        for r in results:
            imp = "⭐" * r["importance"]
            print(f"  {imp} [{r['memory_type']}] {r['key_name']}")
            print(f"     {(r.get('content') or '')[:100]}")
        return

    # ── Recent ──
    if args.recent > 0:
        memories = memory.get_recent(days=args.recent, memory_type=args.type,
                                     limit=args.limit)
        print(f"\n📋 [{mode}] Memorias recientes (últimos {args.recent} días):")
        print(f"   {'='*60}")
        for m in memories:
            imp = "⭐" * m["importance"]
            content = (m.get("content") or "")[:80]
            print(f"   {imp} [{m['memory_type']}] {m['key_name']}")
            print(f"      {content}")
        if not memories:
            print("   (vacío)")
        return

    # ── Delete ──
    if args.delete:
        ok = memory.delete(args.delete, memory_type=args.type)
        print(f"{'✅' if ok else '❌'} Eliminado [{mode}]: '{args.delete}'")
        return

    # ── Clear old ──
    if args.clear_old > 0:
        deleted = memory.clear_old(args.clear_old)
        print(f"🗑️  [{mode}] {deleted} memoria(s) eliminada(s) (> {args.clear_old} días)")
        return

    # ── Sync ──
    if args.sync_from_pg:
        count = memory.sync_from_postgres(days=args.sync_days)
        print(f"🔄 [{mode}] PostgreSQL → Obsidian: {count} entrada(s)")
        return
    if args.sync_to_pg:
        count = memory.sync_to_postgres(days=args.sync_days)
        print(f"🔄 [{mode}] Obsidian → PostgreSQL: {count} entrada(s)")
        return
    if args.sync_bidi:
        result = memory.sync_bidirectional(days=args.sync_days)
        print(f"🔄 [{mode}] Sincronización bidireccional:")
        print(f"   PostgreSQL → Obsidian: {result['from_pg']}")
        print(f"   Obsidian → PostgreSQL: {result['to_pg']}")
        return

    # ── Diarias ──
    if args.save_diaria:
        date_str, title, content = args.save_diaria
        ok = memory.save_diaria(date_str, title, content)
        print(f"{'✅' if ok else '❌'} Diaria guardada [{mode}]: {date_str} — {title}")
        return

    if args.get_diaria:
        # Buscar diaria por fecha exacta — cargar todas y filtrar
        target = args.get_diaria.strip()[:10]
        diarias = memory.get_diarias(days=365, limit=366)
        found = None
        for d in diarias:
            if d.get("date", "")[:10] == target:
                found = d
                break
        if found:
            print(f"📅 {found['date']}: {found['title']}")
            print(f"   Assets: {found['assets_total']} | "
                  f"Servicios: {found['services_active']}/{found['services_total']} | "
                  f"Agentes: {found['agents_active']}/{found['agents_total']}")
            if found.get("alerts_count"):
                print(f"   🚨 Alertas: {found['alerts_count']}")
            print(f"   ---")
            print(found.get("content", ""))
        else:
            print(f"❌ No se encontró diaria para: {target}")
        return

    if args.diarias > 0:
        diarias = memory.get_diarias(days=args.diarias, limit=args.limit)
        print(f"\n📅 [{mode}] Resúmenes diarios (últimos {args.diarias} días):")
        print(f"   {'='*60}")
        if diarias:
            for d in diarias:
                print(f"   📅 {d['date']}: {d['title']}")
                print(f"      Assets: {d['assets_total']} | "
                      f"Servicios: {d['services_active']}/{d['services_total']} | "
                      f"Agentes: {d['agents_active']}/{d['agents_total']}")
                if d.get("alerts_count"):
                    print(f"      🚨 Alertas: {d['alerts_count']}")
        else:
            print("   (sin diarias guardadas — ejecuta --save-diaria o --sync-from-pg)")
        return

    # ── Context / Boot / Summary ──
    if args.context:
        print(memory.get_context(days=args.days, limit=args.limit))
        return
    if args.boot:
        print(memory.boot(days=args.days))
        return
    if args.summary:
        print(memory.summary())
        return


if __name__ == "__main__":
    main()
