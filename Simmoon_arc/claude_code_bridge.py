#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║    Claude Code Bridge — Buffy ↔ Claude Code Orchestrator   ║
║                                                            ║
║  Buffy (DeepSeek) supervisa y delega tareas de código a    ║
║  Claude Code (Anthropic) mediante un protocolo estructurado║
║                                                            ║
║  Flujo:                                                     ║
║    Buffy define tarea → Bridge invoca Claude Code →         ║
║    Claude Code ejecuta → Buffy revisa + itera              ║
╚══════════════════════════════════════════════════════════════╝

Uso:
    from claude_code_bridge import ClaudeCodeBridge

    bridge = ClaudeCodeBridge(verbose=True)

    # Delegar tarea simple
    result = bridge.run("Refactoriza la función X para que sea async")

    # Delegar con archivos específicos
    result = bridge.run_with_files(
        "Añade tests para este módulo",
        files=["simmoon_pipeline.py"],
    )

    # Delegar con contexto completo
    result = bridge.run_task(
        task="Crea un nuevo backend de generación",
        context="Queremos integrar Stability AI como backend...",
        files=["generator_factory.py"],
        effort="high",
    )

    # Ver resultado
    print(result.output)
    if result.success:
        print("✅ Tarea completada")
    else:
        print(f"❌ Falló: {result.summary}")
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ══════════════════════════════════════════════════════════════════════════
# Modelos de Datos
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class ClaudeCodeTask:
    """Tarea estructurada para delegar a Claude Code."""
    task: str
    files: List[str] = field(default_factory=list)
    context: str = ""
    system_prompt: Optional[str] = None
    effort: str = "medium"  # low, medium, high, xhigh, max
    model: Optional[str] = None
    timeout: int = 300
    max_budget_usd: Optional[float] = None
    output_format: str = "text"  # text, json, stream-json
    tags: List[str] = field(default_factory=list)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"cc_{int(time.time())}_{hash(self.task) % 10000:04d}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClaudeCodeResult:
    """Resultado de una ejecución de Claude Code."""
    task: str
    task_id: str
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    success: bool
    files_modified: List[str] = field(default_factory=list)
    summary: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    effort: str = "medium"
    model_used: str = ""

    @property
    def output(self) -> str:
        """Output principal (stdout, o stderr si stdout vacío)."""
        return self.stdout or self.stderr or ""

    @property
    def error(self) -> bool:
        return not self.success

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)


# ══════════════════════════════════════════════════════════════════════════
# Bridge Principal
# ══════════════════════════════════════════════════════════════════════════

class ClaudeCodeBridge:
    """
    Puente para delegar tareas de código a Claude Code (Anthropic).

    Buffy (o cualquier agente) usa este puente para:
    1. Definir tareas estructuradas con contexto y archivos
    2. Invocar Claude Code vía CLI (modo no interactivo con -p)
    3. Recibir resultados estructurados
    4. Persistir el historial en agent_memory

    Modos de operación:
    - run() → tarea simple
    - run_with_files() → tarea con archivos específicos como contexto
    - run_task() → tarea completa con todos los parámetros
    """

    # Nombre del modelo que Claude Code usa por defecto.
    # En ollama_mode, se pasa explicitamente con --model para evitar
    # que Claude Code valide el nombre contra Anthropic.
    # Ollama debe tener un alias que mapee este nombre al modelo local
    # (creado automaticamente por _ensure_model_alias).
    # Se crean ambos alias (claude-opus-4-8 y claude-sonnet-4-20250514)
    # para cubrir diferentes versiones de Claude Code.
    CLAUDE_DEFAULT_MODEL = "claude-opus-4-8"
    CLAUDE_ALT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, model: Optional[str] = None, effort: str = "medium",
                 verbose: bool = False, max_budget_usd: Optional[float] = None,
                 dangerously_skip_permissions: bool = True,
                 permission_mode: str = "acceptEdits",
                 bare_mode: bool = False,
                 ollama_mode: bool = False,
                 ollama_url: str = "http://localhost:11434",
                 ollama_model: str = "gemma3:latest",
                 native_ollama: bool = True,
                 native_ollama_model: str = "minimax-m3:cloud"):
        """
        Args:
            model: Modelo especifico de Claude (ej: "claude-sonnet-4-20250514")
            effort: Nivel de esfuerzo (low, medium, high, xhigh, max)
            verbose: Mostrar debug info
            max_budget_usd: Limite de gasto en USD
            dangerously_skip_permissions: Saltar confirmaciones de seguridad
            permission_mode: Politica de permisos (auto, acceptEdits, plan, etc.)
            bare_mode: Modo minimo (sin hooks/LSP)
            ollama_mode: Si True, redirige Claude Code a Ollama (gratis, local)
            ollama_url: URL de Ollama para ollama_mode
            ollama_model: Modelo Ollama local a usar en ollama_mode (ej: gemma3:latest)
            native_ollama: Usar ollama launch claude (Ollama v0.24+) — recomendado, sin API key
            native_ollama_model: Modelo para native_ollama.
                Recomendados: minimax-m3:cloud, qwen3.5:cloud, kimi-k2.5:cloud, glm-5:cloud
        """
        self.model = model
        self.effort = effort
        self.verbose = verbose
        self.max_budget_usd = max_budget_usd
        self.dangerously_skip_permissions = dangerously_skip_permissions
        self.permission_mode = permission_mode
        self.bare_mode = bare_mode
        self.ollama_mode = ollama_mode
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.native_ollama = native_ollama
        self.native_ollama_model = native_ollama_model

        # Buffer de resultados para la sesión actual
        self.history: List[ClaudeCodeResult] = []

        # Cache de memoria (inicialización lazy)
        self._memory = None

        # Verificar disponibilidad al iniciar
        self._availability = None
        self._native_available = None
        self._alias_ensured = False  # Flag lazy para _ensure_model_alias()

    # ── Propiedades ──────────────────────────────────────────────────────

    @property
    def memory(self):
        """Conexión lazy a agent_memory."""
        if self._memory is None:
            try:
                from agent_memory import AgentMemory
                self._memory = AgentMemory('claude_code', project='SIMMOON')
            except (ImportError, Exception) as e:
                if self.verbose:
                    print(f"[CLAUDE BRIDGE] agent_memory no disponible: {e}")
                self._memory = None  # No memory = no problem
        return self._memory

    @property
    def available(self) -> bool:
        """Verificar si Claude Code CLI está disponible (con caché)."""
        if self._availability is None:
            self._availability = self.check_available()
        return self._availability

    # ── Verificación de disponibilidad ──────────────────────────────────

    def _find_claude_binary(self) -> Optional[str]:
        """Encontrar el binario de Claude Code en el sistema."""
        from shutil import which
        
        # 1. Rutas comunes de npm global en Windows
        common_npm_bins = [
            os.path.expanduser("~/AppData/Roaming/npm"),
            os.path.expanduser("~/.npm-global/bin"),
            os.path.expanduser("~/.npm/bin"),
        ]
        
        for npm_bin in common_npm_bins:
            for name in ["claude.cmd", "claude", "claude.exe"]:
                path = os.path.join(npm_bin, name)
                if os.path.isfile(path):
                    return path
        
        # 2. Buscar en el directorio del ejecutable de Python
        python_dir = os.path.dirname(sys.executable)
        for name in ["claude.cmd", "claude", "claude.exe"]:
            path = os.path.join(python_dir, name)
            if os.path.isfile(path):
                return path
        
        # 3. shutil.which (busca en PATH)
        for name in ["claude.cmd", "claude", "claude.exe"]:
            path = which(name)
            if path:
                return path
        
        return None

    def _is_cmd_file(self, path: str) -> bool:
        """Verificar si el binario es un script .cmd (necesita shell=True en Windows)."""
        return path.lower().endswith('.cmd')

    # ── Alias de modelo para Ollama ────────────────────────────────────

    def _ensure_model_alias(self):
        """Crear alias en Ollama para que Claude Code funcione localmente.

        Claude Code CLI siempre envia un nombre de modelo de Anthropic en sus
        requests (ej: claude-opus-4-8, claude-sonnet-4-20250514).
        Ollama no conoce ese modelo.
        Esta funcion crea alias en Ollama que mapean los nombres de modelo
        de Claude al modelo local configurado (self.ollama_model).

        Los alias persisten hasta que se reinicie Ollama, asi que se recrean
        cada vez que el bridge se inicializa.
        """
        if not self.ollama_mode:
            return

        local_model = self.ollama_model
        alias_names = [self.CLAUDE_DEFAULT_MODEL, self.CLAUDE_ALT_MODEL]

        for alias_name in alias_names:
            # 1. Verificar si el alias ya existe
            try:
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/show",
                    data=json.dumps({"model": alias_name}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if self.verbose:
                        print(f"  ✅ Alias existe: {alias_name} → {local_model}")
                    continue
            except Exception:
                pass

            # 2. Crear alias si no existe
            if self.verbose:
                print(f"  🔧 Creando alias: {alias_name} → {local_model}...")

            try:
                payload = json.dumps({
                    "model": alias_name,
                    "from": local_model,
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/create",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp.read()
                    if self.verbose:
                        print(f"  ✅ Alias creado: {alias_name} → {local_model}")
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️  No se pudo crear alias '{alias_name}': {e}")

    # ── Ejecucion de comandos ──────────────────────────────────────────

    def _run_claude(self, args: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
        """Ejecutar Claude Code manejando correctamente archivos .cmd en Windows."""
        # Asegurar alias de modelo en Ollama (lazy, solo en el primer uso)
        if self.ollama_mode and not self._alias_ensured:
            self._ensure_model_alias()
            self._alias_ensured = True

        claude_path = self._find_claude_binary()
        if not claude_path:
            raise FileNotFoundError("Claude Code binary not found")
        
        # Preparar entorno: si ollama_mode, redirigir a Ollama
        env = os.environ.copy()
        if self.ollama_mode:
            env["ANTHROPIC_BASE_URL"] = self.ollama_url
            env["ANTHROPIC_AUTH_TOKEN"] = "ollama"
            env["ANTHROPIC_API_KEY"] = "sk-ollama-local"
            if self.verbose:
                print(f"  🦙 Modo Ollama: {self.ollama_url} (modelo: {self.ollama_model})")
        
        # Asegurar que el modelo se pasa correctamente
        has_model = any(a.startswith("--model") for a in args)
        if self.ollama_mode and not has_model:
            args = args + ["--model", self.ollama_model]
        
        if claude_path == "npx":
            cmd = ["npx", "--yes", "@anthropic-ai/claude-code"] + args
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                               encoding='utf-8', errors='replace', env=env)
        elif self._is_cmd_file(claude_path):
            full_cmd = f'"{claude_path}" {" ".join(args)}'
            return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout,
                               encoding='utf-8', errors='replace', shell=True, env=env)
        else:
            cmd = [claude_path] + args
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                               encoding='utf-8', errors='replace', env=env)

    def check_available(self) -> bool:
        """Verificar si Claude Code CLI está instalado y accesible."""
        claude_path = self._find_claude_binary()
        if not claude_path:
            if self.verbose:
                print("[CLAUDE BRIDGE] ❌ Claude Code binario no encontrado")
            return False
        
        try:
            r = self._run_claude(["--version"], timeout=60)
            ok = r.returncode == 0 and bool(r.stdout.strip())
            if ok and self.verbose:
                print(f"[CLAUDE BRIDGE] ✅ Claude Code v{r.stdout.strip()} ({claude_path})")
            return ok
        except Exception as e:
            if self.verbose:
                print(f"[CLAUDE BRIDGE] ❌ Claude Code error: {e}")
            return False
    
    def check_native_ollama_available(self) -> bool:
        """Verificar si ollama launch claude está disponible (Ollama v0.24+).
        
        Este es el método recomendado: lanza Claude Code con modelos locales
        de Ollama SIN necesidad de ANTHROPIC_API_KEY.
        """
        if self._native_available is not None:
            return self._native_available
        
        try:
            # Verificar que ollama launch claude funciona
            r = subprocess.run(
                ["ollama", "launch", "claude", "--help"],
                capture_output=True, text=True, timeout=10,
            )
            self._native_available = r.returncode == 0
            if self._native_available and self.verbose:
                print(f"[CLAUDE BRIDGE] ✅ ollama launch claude disponible")
        except Exception:
            self._native_available = False
        
        return self._native_available
    
    def _run_native_ollama(self, prompt: str, timeout: int = 300) -> ClaudeCodeResult:
        """Ejecutar tarea usando ollama launch claude (método nativo, sin API key).
        
        Ollama v0.24+ incluye integración nativa con Claude Code vía
        ollama launch claude, que automáticamente configura las variables
        de entorno para rutear a Ollama local.
        """
        started_at = datetime.now().isoformat()
        task_id = f"native_{int(time.time())}_{hash(prompt) % 10000:04d}"
        
        # Construir comando
        cmd = [
            "ollama", "launch", "claude",
            "--model", self.native_ollama_model,
            "--yes",
            "--", "-p", prompt,
            "--effort", self.effort,
            "--dangerously-skip-permissions",
            "--output-format", "text",
            "--no-session-persistence",
        ]
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  🦙 CLAUDE CODE NATIVO (ollama launch claude)")
            print(f"  🆔 ID: {task_id}")
            print(f"  🧠 Modelo: {self.native_ollama_model}")
            print(f"  📋 Task: {prompt[:120]}...")
            print(f"  ⏱️  Timeout: {timeout}s")
            print(f"{'='*60}\n")
        
        start_time = time.time()
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, encoding='utf-8', errors='replace',
            )
            duration = time.time() - start_time
            success = r.returncode == 0
            
            result = ClaudeCodeResult(
                task=prompt, task_id=task_id,
                stdout=r.stdout, stderr=r.stderr,
                exit_code=r.returncode, duration=duration,
                success=success,
                files_modified=self._extract_files(r.stdout),
                summary=self._extract_summary(r.stdout),
                started_at=started_at,
                finished_at=datetime.now().isoformat(),
                effort=self.effort,
                model_used=f"ollama/{self.native_ollama_model}",
            )
            
            if self.verbose:
                status = "✅" if success else "❌"
                print(f"  {status} Completado en {duration:.1f}s")
                print(f"  📄 Output: {len(r.stdout)} chars")
            
            self.history.append(result)
            self._save_to_memory(result)
            return result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            result = ClaudeCodeResult(
                task=prompt, task_id=task_id,
                stdout="", stderr=f"[TIMEOUT] excedió {timeout}s",
                exit_code=-1, duration=duration, success=False,
                started_at=started_at, finished_at=datetime.now().isoformat(),
                effort=self.effort, model_used=f"ollama/{self.native_ollama_model}",
            )
            self.history.append(result)
            return result
        except Exception as e:
            duration = time.time() - start_time
            result = ClaudeCodeResult(
                task=prompt, task_id=task_id,
                stdout="", stderr=f"[ERROR] {e}",
                exit_code=-1, duration=duration, success=False,
                started_at=started_at, finished_at=datetime.now().isoformat(),
                effort=self.effort, model_used=f"ollama/{self.native_ollama_model}",
            )
            self.history.append(result)
            return result

    # ── Construcción del comando CLI ────────────────────────────────────

    def _build_cmd(self, prompt: str, system_prompt: Optional[str] = None,
                   output_format: str = "text") -> tuple:
        """Construir comando y args para invocar Claude Code.
        Returns:
            (claude_path, args_list) para usar con _run_claude
        """
        claude_path = self._find_claude_binary() or "claude"
        
        args = ["-p", prompt]
        
        # En ollama_mode, pasar el modelo CLAUDE_DEFAULT_MODEL (que tiene alias
        # en Ollama apuntando al modelo local). Asi Claude Code no valida
        # el modelo contra Anthropic porque se lo pasamos explicitamente.
        if self.ollama_mode:
            args.extend(["--model", self.CLAUDE_DEFAULT_MODEL])
        elif self.model:
            args.extend(["--model", self.model])
        
        if self.effort:
            args.extend(["--effort", self.effort])
        if self.max_budget_usd is not None:
            args.extend(["--max-budget-usd", str(self.max_budget_usd)])
        if system_prompt:
            args.extend(["--append-system-prompt", system_prompt])
        if output_format and output_format != "text":
            args.extend(["--output-format", output_format])

        # Seguridad
        if self.dangerously_skip_permissions:
            args.append("--dangerously-skip-permissions")
        else:
            args.extend(["--permission-mode", self.permission_mode])

        # Bare mode opcional (sin hooks/LSP)
        if self.bare_mode:
            args.append("--bare")

        # No guardar sesiones en disco para automatización limpia
        if "--no-session-persistence" not in args:
            args.append("--no-session-persistence")

        return (claude_path, args)

    # ── Armado del prompt con contexto ──────────────────────────────────

    def _build_prompt(self, task: str, context: str = "",
                      files: Optional[List[str]] = None) -> str:
        """Construir el prompt completo con contexto y archivos."""
        parts = []

        # Contexto del proyecto
        parts.append(
            "Eres Claude Code trabajando como sub-agente de Buffy "
            "(el orquestador principal) en el proyecto SIMMOON.\n"
        )

        # Instrucciones de comportamiento
        parts.append(
            "INSTRUCCIONES:\n"
            "- Completa la tarea de forma autonoma: lee archivos, escribe codigo,\n"
            "  ejecuta comandos segun sea necesario.\n"
            "- Si encuentras errores, intenta resolverlos.\n"
            "- Si necesitas mas contexto, usa las herramientas disponibles para obtenerlo.\n"
            "- No preguntes, solo haz. Tienes permiso para tomar decisiones.\n"
            "- Al final, proporciona un resumen de lo que hiciste.\n"
        )

        # Archivos de contexto (solo rutas — Claude Code los lee solo)
        if files:
            resolved_files = []
            for fp in files:
                path = Path(fp)
                if not path.is_absolute():
                    path = SCRIPT_DIR / fp
                if path.exists():
                    resolved_files.append(str(path.resolve()))

            if resolved_files:
                parts.append(
                    "ARCHIVOS RELEVANTES (lee los que necesites):\n"
                    + "\n".join(f"  - {f}" for f in resolved_files) + "\n"
                )

        # Contexto adicional
        if context:
            parts.append(f"📌 CONTEXTO ADICIONAL:\n{context}\n")

        # La tarea en sí
        parts.append(f"🎯 TAREA:\n{task}\n")

        # Formato de respuesta esperado
        parts.append(
            "\n✅ Al finalizar, incluye un breve resumen de:\n"
            "1. Qué hiciste\n"
            "2. Qué archivos modificaste\n"
            "3. Si encontraste problemas\n"
        )

        return "\n".join(parts)

    # ── Métodos de ejecución ────────────────────────────────────────────

    def run(self, task: str, system_prompt: Optional[str] = None,
            timeout: int = 300, effort: Optional[str] = None,
            output_format: str = "text") -> ClaudeCodeResult:
        """
        Ejecutar una tarea simple en Claude Code.

        Args:
            task: Descripción de la tarea a realizar
            system_prompt: Instrucciones adicionales de sistema
            timeout: Tiempo máximo de ejecución en segundos
            effort: Nivel de esfuerzo para esta tarea específica
            output_format: Formato de salida (text, json, stream-json)

        Returns:
            ClaudeCodeResult con el resultado de la ejecución
        """
        return self.run_task(
            task=task,
            system_prompt=system_prompt,
            timeout=timeout,
            effort=effort or self.effort,
            output_format=output_format,
        )

    def run_with_files(self, task: str, files: Optional[List[str]] = None,
                       context: str = "", **kwargs) -> ClaudeCodeResult:
        """
        Ejecutar tarea con archivos específicos como contexto.

        Args:
            task: Descripción de la tarea
            files: Lista de rutas a archivos relevantes
            context: Contexto adicional sobre la tarea
            **kwargs: Argumentos adicionales para run_task

        Returns:
            ClaudeCodeResult
        """
        return self.run_task(
            task=task,
            files=files or [],
            context=context,
            **kwargs
        )

    def run_task(self, task: str, files: Optional[List[str]] = None,
                 context: str = "", system_prompt: Optional[str] = None,
                 timeout: int = 300, effort: Optional[str] = None,
                 model: Optional[str] = None,
                 output_format: str = "text",
                 tags: Optional[List[str]] = None) -> ClaudeCodeResult:
        """
        Método completo para delegar una tarea a Claude Code.

        Args:
            task: Descripción de la tarea
            files: Archivos relevantes para la tarea
            context: Contexto adicional
            system_prompt: System prompt override
            timeout: Timeout en segundos
            effort: Nivel de esfuerzo
            model: Modelo específico
            output_format: Formato de salida
            tags: Tags para la memoria

        Returns:
            ClaudeCodeResult
        """
        started_at = datetime.now().isoformat()

        # Construir el objeto de tarea
        cc_task = ClaudeCodeTask(
            task=task,
            files=files or [],
            context=context,
            system_prompt=system_prompt,
            effort=effort or self.effort,
            model=model or self.model,
            timeout=timeout,
            output_format=output_format,
            tags=tags or [],
        )

        # Verificar disponibilidad
        if not self.available:
            return ClaudeCodeResult(
                task=task, task_id=cc_task.id,
                stdout="", stderr="[ERROR] Claude Code CLI no está disponible. "
                       "Instala con: npm install -g @anthropic-ai/claude-code",
                exit_code=-2, duration=0, success=False,
                started_at=started_at, finished_at=datetime.now().isoformat(),
                model_used="", effort=effort or self.effort,
            )

        # Construir prompt y args (pasar model si se especificó)
        prompt = self._build_prompt(task, context, files)
        saved_model = self.model
        if model:
            self.model = model
        _, args = self._build_cmd(prompt, system_prompt, output_format)
        if model:
            self.model = saved_model

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  🤖 CLAUDE CODE BRIDGE — Ejecutando tarea")
            print(f"  🆔 ID: {cc_task.id}")
            print(f"  📋 Task: {task[:120]}...")
            if files:
                print(f"  📁 Files: {len(files)} archivos")
            print(f"  🎯 Effort: {cc_task.effort}")
            print(f"  ⏱️  Timeout: {timeout}s")
            print(f"{'='*60}\n")

        # Ejecutar Claude Code
        start_time = time.time()
        try:
            result = self._run_claude(args, timeout=timeout)
            duration = time.time() - start_time

            # Parsear archivos modificados del output
            files_modified = self._extract_files(result.stdout)

            cc_result = ClaudeCodeResult(
                task=task,
                task_id=cc_task.id,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration=duration,
                success=result.returncode == 0,
                files_modified=files_modified,
                summary=self._extract_summary(result.stdout),
                started_at=started_at,
                finished_at=datetime.now().isoformat(),
                effort=effort or self.effort,
                model_used=self.model or "default",
            )

            if self.verbose:
                status = "✅" if cc_result.success else "❌"
                print(f"  {status} Completado en {duration:.1f}s (exit: {result.returncode})")
                print(f"  📄 Output: {len(result.stdout)} chars")
                if files_modified:
                    print(f"  📝 Archivos modificados: {len(files_modified)}")
                    for f in files_modified[:5]:
                        print(f"     - {f}")
                if not cc_result.success and result.stderr:
                    print(f"  ⚠️  Stderr: {result.stderr[:300]}")

            # Guardar en memoria
            self._save_to_memory(cc_result)
            self.history.append(cc_result)

            return cc_result

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            cc_result = ClaudeCodeResult(
                task=task, task_id=cc_task.id,
                stdout="", stderr=f"[TIMEOUT] Claude Code excedió {timeout}s",
                exit_code=-1, duration=duration, success=False,
                started_at=started_at, finished_at=datetime.now().isoformat(),
                effort=effort or self.effort,
            )
            print(f"  ⚠️  TIMEOUT después de {duration:.1f}s")
            self.history.append(cc_result)
            return cc_result

        except Exception as e:
            duration = time.time() - start_time
            cc_result = ClaudeCodeResult(
                task=task, task_id=cc_task.id,
                stdout="", stderr=f"[ERROR] {e}",
                exit_code=-1, duration=duration, success=False,
                started_at=started_at, finished_at=datetime.now().isoformat(),
                effort=effort or self.effort,
            )
            if self.verbose:
                print(f"  ❌ Error: {e}")
            self.history.append(cc_result)
            return cc_result

    # ── Parseo de resultados ────────────────────────────────────────────

    def _extract_files(self, output: str) -> List[str]:
        """Extraer lista de archivos modificados del output de Claude."""
        files = []
        # Buscar patrones comunes de modificación de archivos
        for line in output.split('\n'):
            line = line.strip()
            # Patrones: "Wrote file X", "Modified X", "Created X", "--- a/path"
            for marker in ["Wrote", "Modified", "Created", "Updated", "--- a/", "+++ b/"]:
                if marker in line:
                    # Intentar extraer ruta
                    words = line.replace("--- a/", "").replace("+++ b/", "").split()
                    for w in words:
                        if w.endswith(('.py', '.js', '.ts', '.html', '.css', '.json',
                                       '.md', '.txt', '.sh', '.bat', '.ps1', '.yaml',
                                       '.yml', '.toml', '.cfg', '.ini', '.env')):
                            if w not in files:
                                files.append(w)
        return files

    def _extract_summary(self, output: str) -> str:
        """Extraer resumen del final del output."""
        # Buscar sección de resumen al final
        lines = output.split('\n')
        summary_lines = []
        in_summary = False
        for line in reversed(lines):
            stripped = line.strip()
            if in_summary:
                if stripped.startswith(('1.', '2.', '3.', '-', '•', '*', '#')):
                    summary_lines.insert(0, stripped)
                elif not stripped and summary_lines:
                    break
                elif summary_lines:
                    break
            elif any(marker in stripped.lower() for marker in
                     ['resumen', 'summary', 'hiciste', 'modificaste']):
                in_summary = True
                summary_lines.insert(0, stripped)

        if summary_lines:
            return '\n'.join(summary_lines[:10])
        # Fallback: últimas líneas no vacías
        non_empty = [l.strip() for l in lines if l.strip()]
        return '\n'.join(non_empty[-5:]) if non_empty else ""

    # ── Persistencia en memoria compartida ──────────────────────────────

    def _save_to_memory(self, result: ClaudeCodeResult):
        """Guardar resultado en agent_memory para persistencia entre sesiones."""
        if not self.memory:
            return

        try:
            key = f"claude_task_{result.task_id}"

            # Resumen de la ejecución
            self.memory.save(
                key_name=key,
                content=(
                    f"🤖 Claude Code Task\n"
                    f"Task: {result.task[:150]}\n"
                    f"Status: {'✅ Success' if result.success else '❌ Failed'}\n"
                    f"Duration: {result.duration:.1f}s\n"
                    f"Files modified: {', '.join(result.files_modified[:5]) or 'none'}\n"
                    f"Summary: {result.summary[:200]}"
                ),
                memory_type='result',
                tags=['claude_code', 'automated'] + (['success'] if result.success else ['failed']),
                importance=3,
            )

            # Si tuvo éxito, guardar también como contexto
            if result.success and result.files_modified:
                self.memory.save_context(
                    key_name=f"claude_output_{result.task_id}",
                    content=f"Claude Code modificó: {', '.join(result.files_modified[:10])}. "
                            f"Resumen: {result.summary[:200]}",
                )

        except Exception as e:
            if self.verbose:
                print(f"[CLAUDE BRIDGE] No se pudo guardar en memoria: {e}")

    # ── Utilidades ──────────────────────────────────────────────────────

    def get_history(self, limit: int = 10) -> List[ClaudeCodeResult]:
        """Obtener historial de ejecuciones de esta sesión."""
        return self.history[-limit:]

    def get_last_result(self) -> Optional[ClaudeCodeResult]:
        """Obtener el último resultado."""
        return self.history[-1] if self.history else None

    def status(self) -> dict:
        """Estado actual del bridge."""
        # Verificar disponibilidad usando el mismo método de detección
        available = False
        version = ""
        try:
            r = self._run_claude(["--version"], timeout=60)
            available = r.returncode == 0
            version = r.stdout.strip() if available else ""
        except Exception:
            available = False
            version = ""
        
        native_ok = self.check_native_ollama_available()

        return {
            "available": available,
            "version": version,
            "model": self.model or "default",
            "effort": self.effort,
            "tasks_run": len(self.history),
            "tasks_success": sum(1 for h in self.history if h.success),
            "tasks_failed": sum(1 for h in self.history if not h.success),
            "memory_enabled": self._memory is not None,
            "dangerously_skip_permissions": self.dangerously_skip_permissions,
            "api_key_configured": "ANTHROPIC_API_KEY" in os.environ,
            "ollama_available": self._check_ollama(),
            "native_ollama": native_ok,
            "native_ollama_model": self.native_ollama_model if native_ok else "",
        }

    def _check_ollama(self) -> bool:
        """Verificar si Ollama esta disponible (delega a OllamaAnthropicClient)."""
        return OllamaAnthropicClient.check_available()

    def reset_history(self):
        """Limpiar historial de la sesión actual."""
        self.history = []

    def print_summary(self):
        """Mostrar resumen de todas las ejecuciones de esta sesión."""
        if not self.history:
            print("  📭 No hay ejecuciones en esta sesión.")
            return

        print(f"\n{'='*60}")
        print(f"  📊 RESUMEN DE CLAUDE CODE BRIDGE")
        print(f"  {'='*60}")
        print(f"  Total: {len(self.history)} tareas")
        success = sum(1 for h in self.history if h.success)
        failed = sum(1 for h in self.history if not h.success)
        total_time = sum(h.duration for h in self.history)
        print(f"  ✅ {success} exitosas | ❌ {failed} fallidas | ⏱️  {total_time:.1f}s total")
        print()

        for i, h in enumerate(self.history):
            status = "✅" if h.success else "❌"
            print(f"  {i+1}. {status} [{h.task_id}] {h.task[:80]}...")
            print(f"      ⏱️  {h.duration:.1f}s | Archivos: {len(h.files_modified)}")
            if h.files_modified:
                for f in h.files_modified[:3]:
                    print(f"      📄 {f}")
            print()


# ══════════════════════════════════════════════════════════════════════════
# Cliente Ollama Anthropic Messages API — Modo Local Gratuito
# ══════════════════════════════════════════════════════════════════════════

OLLAMA_URL = "http://localhost:11434"

class OllamaAnthropicClient:
    """
    Cliente directo para Ollama usando el formato Anthropic Messages API.

    Desde Ollama v0.14.0+, el endpoint /v1/messages soporta el formato
    Anthropic Messages API de forma nativa, lo que permite usar modelos
    locales SIN necesidad del binario claude ni API key.

    Uso:
        client = OllamaAnthropicClient(model="qwen2.5-coder:14b")
        result = client.chat("Refactoriza esta funcion")
    """

    def __init__(self, model: str = "qwen3.5:9b",
                 ollama_url: str = OLLAMA_URL,
                 verbose: bool = False,
                 system_prompt: Optional[str] = None):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.verbose = verbose
        self.default_system = system_prompt or (
            "Eres un asistente de codigo experto. Trabajas como sub-agente de "
            "Buffy en el proyecto SIMMOON. Completa las tareas de forma autonoma "
            "y proporciona codigo funcional. Responde en espanol."
        )

    def _messages_request(self, messages: List[dict],
                          max_tokens: int = 4096,
                          temperature: float = 0.3,
                          timeout: int = 300,
                          system: Optional[str] = None) -> dict:
        """Enviar request al endpoint /v1/messages de Ollama.
        
        El system prompt va como campo raiz (formato Anthropic Messages API).
        """
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url}/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": "ollama",
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"error": f"HTTP {e.code}: {body[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    def chat(self, prompt: str, system: Optional[str] = None,
             max_tokens: int = 4096, temperature: float = 0.3,
             timeout: int = 300) -> str:
        """Enviar un prompt y obtener respuesta."""
        sys_msg = system or self.default_system
        messages = [
            {"role": "user", "content": prompt},
        ]

        if self.verbose:
            print(f"[OLLAMA] Enviando prompt a {self.model}...")

        result = self._messages_request(messages, max_tokens, temperature, timeout, system=sys_msg)

        if "error" in result:
            return f"[ERROR] {result['error']}"

        # Parsear respuesta Anthropic Messages API
        content_blocks = result.get("content", [])
        if isinstance(content_blocks, list):
            texts = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif isinstance(block, str):
                    texts.append(block)
            return "\n".join(texts)
        elif isinstance(content_blocks, str):
            return content_blocks
        else:
            return str(result.get("content", result.get("message", {}).get("content", "")))

    def run_task(self, task: str, files: Optional[List[str]] = None,
                 context: str = "", timeout: int = 300) -> ClaudeCodeResult:
        """Ejecutar una tarea estructurada (compatible con ClaudeCodeBridge)."""
        started_at = datetime.now().isoformat()
        task_id = f"ollama_{int(time.time())}_{hash(task) % 10000:04d}"

        # Construir prompt con contexto
        parts = [
            "Eres un asistente de codigo experto trabajando en el proyecto SIMMOON.\n",
            "INSTRUCCIONES:\n"
            "- Completa la tarea de forma autonoma.\n"
            "- Analiza el codigo y proporciona soluciones completas.\n"
            "- Incluye el codigo necesario en tu respuesta.\n"
            "- Al final, resume que hiciste en 1-2 lineas.\n",
        ]

        if files:
            resolved = []
            for fp in files:
                path = Path(fp)
                if not path.is_absolute():
                    path = SCRIPT_DIR / fp
                if path.exists():
                    resolved.append(str(path.resolve()))
            if resolved:
                parts.append("ARCHIVOS RELEVANTES:\n" + "\n".join(f"  - {f}" for f in resolved) + "\n")
                # Incluir contenido de archivos
                for fp in resolved[:3]:
                    path = Path(fp)
                    if path.exists() and path.stat().st_size < 30000:
                        try:
                            content = path.read_text(encoding="utf-8", errors="replace")
                            parts.append(f"\nContenido de {path.name}:\n```\n{content[:5000]}\n```\n")
                        except Exception:
                            pass

        if context:
            parts.append(f"CONTEXTO: {context}\n")

        parts.append(f"TAREA:\n{task}\n")
        parts.append("Al finalizar incluye: RESUMEN: (que hiciste)")

        prompt = "\n".join(parts)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  🦙 OLLAMA ANTHROPIC API — Ejecutando tarea")
            print(f"  🆔 ID: {task_id}")
            print(f"  🧠 Modelo: {self.model}")
            print(f"  📋 Task: {task[:120]}...")
            if files:
                print(f"  📁 Files: {len(files)} archivos")
            print(f"  ⏱️  Timeout: {timeout}s")
            print(f"{'='*60}\n")

        start_time = time.time()
        try:
            response = self.chat(prompt, timeout=timeout)
            duration = time.time() - start_time

            if response.startswith("[ERROR]"):
                cc_result = ClaudeCodeResult(
                    task=task, task_id=task_id,
                    stdout="", stderr=response,
                    exit_code=1, duration=duration, success=False,
                    started_at=started_at, finished_at=datetime.now().isoformat(),
                    effort="medium", model_used=self.model,
                )
            else:
                # Extraer resumen del final
                summary = ""
                if "RESUMEN:" in response:
                    summary = response.split("RESUMEN:")[-1].strip()[:200]

                cc_result = ClaudeCodeResult(
                    task=task, task_id=task_id,
                    stdout=response, stderr="",
                    exit_code=0, duration=duration, success=True,
                    files_modified=[],
                    summary=summary or response[-200:],
                    started_at=started_at, finished_at=datetime.now().isoformat(),
                    effort="medium", model_used=self.model,
                )

            if self.verbose:
                status = "✅" if cc_result.success else "❌"
                print(f"  {status} Completado en {duration:.1f}s")
                print(f"  📄 Output: {len(response)} chars\n")

            return cc_result

        except Exception as e:
            duration = time.time() - start_time
            return ClaudeCodeResult(
                task=task, task_id=task_id,
                stdout="", stderr=f"[ERROR] {e}",
                exit_code=-1, duration=duration, success=False,
                started_at=started_at, finished_at=datetime.now().isoformat(),
                effort="medium", model_used=self.model,
            )

    @staticmethod
    def check_available(ollama_url: str = OLLAMA_URL) -> bool:
        """Verificar si Ollama esta disponible."""
        try:
            req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return len(data.get("models", [])) > 0
        except Exception:
            return False

    @staticmethod
    def list_models(ollama_url: str = OLLAMA_URL) -> List[str]:
        """Listar modelos disponibles en Ollama."""
        try:
            req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# ══════════════════════════════════════════════════════════════════════════
# Supervisor — Buffy usa esto para orquestar a Claude Code
# ══════════════════════════════════════════════════════════════════════════

class BuffySupervisor:
    """
    Supervisor que orquesta tareas entre Buffy, Claude Code y Ollama.

    Buffy (DeepSeek) actúa como supervisor/arquitecto que:
    1. Define el plan y los objetivos
    2. Selecciona automaticamente el backend:
       - Claude Code (si esta autenticado) → tareas complejas
       - Ollama directo (siempre disponible) → modo local gratis
    3. Revisa los resultados
    4. Itera según sea necesario
    """

    def __init__(self, bridge: Optional[ClaudeCodeBridge] = None,
                 ollama_client: Optional[OllamaAnthropicClient] = None,
                 prefer_ollama: bool = True,
                 ollama_model: str = "gemma3:latest",
                 verbose: bool = True):
        # Bridge con ollama_mode=True: Claude Code CLI se conecta a Ollama local
        # en lugar de Anthropic API. No requiere ANTHROPIC_API_KEY.
        # El modelo default es gemma3:latest porque esta confirmado que funciona
        # con el endpoint /v1/messages de Ollama.
        self.bridge = bridge or ClaudeCodeBridge(
            verbose=verbose,
            ollama_mode=True,
            ollama_model=ollama_model,
        )
        self.ollama = ollama_client or OllamaAnthropicClient(
            model=ollama_model, verbose=verbose
        )
        self.prefer_ollama = prefer_ollama
        self.verbose = verbose
        self.session_log: List[dict] = []
        self._buff_memory = None

    def _select_backend(self) -> str:
        """Seleccionar el mejor backend disponible.
        
        Prioridad:
        1. ollama launch claude (nativo, gratis, sin API key)
        2. Claude Code + ollama_mode (Claude Code CLI redirigido a Ollama local)
        3. Ollama Anthropic Client (fallback, solo texto)
        4. Claude Code API (requiere ANTHROPIC_API_KEY)
        """
        native_available = self.bridge.check_native_ollama_available()
        ollama_available = OllamaAnthropicClient.check_available()
        
        # Prioridad 1: ollama launch claude (nativo, sin API key)
        if self.prefer_ollama and native_available:
            return "native_ollama"
        if native_available:
            return "native_ollama"
        
        # Prioridad 2: Claude Code con ollama_mode (edita archivos, usa Ollama local)
        if self.bridge.ollama_mode and self.bridge.available and ollama_available:
            return "claude"
        
        # Prioridad 3: Claude Code con API key (requiere ANTHROPIC_API_KEY)
        claude_available = self.bridge.available and ("ANTHROPIC_API_KEY" in os.environ)
        if claude_available:
            return "claude"
        
        # Prioridad 4: Ollama directo (solo texto, no edita archivos)
        if self.prefer_ollama and ollama_available:
            return "ollama"
        if ollama_available:
            return "ollama"
        
        return "none"

    @property
    def buffy_memory(self):
        """Memoria de Buffy para guardar el contexto de supervisión."""
        if self._buff_memory is None:
            try:
                from agent_memory import AgentMemory
                self._buff_memory = AgentMemory('buffy', project='SIMMOON')
            except Exception:
                self._buff_memory = None
        return self._buff_memory

    def delegate(self, task: str, files: Optional[List[str]] = None,
                 context: str = "", effort: str = "high",
                 timeout: int = 300) -> ClaudeCodeResult:
        """
        Delegar una tarea al mejor backend disponible.

        Selecciona automaticamente:
        - ollama launch claude (nativo, gratis) si esta disponible
        - Ollama Anthropic Client (fallback)
        - Claude Code si hay API key configurada

        Este es el método principal que Buffy usa para poner a trabajar
        a los workers.

        Args:
            task: La tarea a delegar
            files: Archivos relevantes
            context: Contexto adicional
            effort: Nivel de esfuerzo
            timeout: Timeout

        Returns:
            ClaudeCodeResult
        """
        backend = self._select_backend()
        backend_name = {
            "native_ollama": f"🦙 Ollama Nativo ({self.bridge.native_ollama_model})",
            "ollama": "Ollama (" + self.ollama.model + ")",
            "claude": "Claude Code",
            "none": "NINGUNO",
        }.get(backend, backend)

        if self.verbose:
            print(f"\n  🧠 BUFFY: Delegando tarea a {backend_name}")
            print(f"  {'='*55}")

        # Ejecutar segun backend
        if backend == "native_ollama":
            # Construir prompt con contexto
            full_prompt = self.bridge._build_prompt(task, context, files)
            result = self.bridge._run_native_ollama(full_prompt, timeout=timeout)
        elif backend == "ollama":
            result = self.ollama.run_task(
                task=task,
                files=files,
                context=context,
                timeout=timeout,
            )
        elif backend == "claude":
            result = self.bridge.run_task(
                task=task,
                files=files,
                context=context,
                effort=effort,
                timeout=timeout,
                tags=['supervised', 'buffy_orchestrated'],
            )
        else:
            return ClaudeCodeResult(
                task=task, task_id=f"err_{int(time.time())}",
                stdout="", stderr="[ERROR] No hay backend disponible. "
                       "Instala Ollama v0.24+ para ollama launch claude",
                exit_code=-2, duration=0, success=False,
                effort=effort,
            )

        # Registrar en el log de supervisión
        self.session_log.append({
            'task_id': result.task_id,
            'task': task[:100],
            'success': result.success,
            'duration': result.duration,
            'files_modified': result.files_modified,
            'timestamp': datetime.now().isoformat(),
        })

        # Guardar en memoria de Buffy
        if self.buffy_memory and result.success:
            self.buffy_memory.save_context(
                key_name=f"claude_delegation_{result.task_id}",
                content=(
                    f"Delegué a Claude Code: {task[:100]}... "
                    f"Resultado: {'✅' if result.success else '❌'} "
                    f"Duración: {result.duration:.1f}s"
                ),
            )

        # Resumen para Buffy
        if self.verbose:
            if result.success:
                print(f"  ✅ CLAUDE CODE COMPLETÓ LA TAREA en {result.duration:.1f}s")
                if result.files_modified:
                    print(f"  📝 Archivos afectados:")
                    for f in result.files_modified:
                        print(f"     • {f}")
                if result.summary:
                    print(f"  📋 Resumen: {result.summary[:200]}")
            else:
                print(f"  ❌ Claude Code falló (exit: {result.exit_code})")
                if result.stderr:
                    print(f"  ⚠️  {result.stderr[:300]}")

        return result

    def review(self, result: ClaudeCodeResult) -> dict:
        """Revisar el resultado de Claude Code como supervisor."""
        issues = []

        # Verificar si hubo errores
        if not result.success:
            issues.append(f"Exit code no cero: {result.exit_code}")

        # Verificar si hay stderr relevante
        if result.stderr and len(result.stderr) > 50:
            issues.append(f"Stderr presente: {result.stderr[:200]}")

        # Verificar duración
        if result.duration < 1:
            issues.append("Ejecución extremadamente rápida (<1s) — posible error silencioso")
        if result.duration > 240:
            issues.append("Ejecución larga (>4 minutos)")

        # Verificar si produjo output
        if not result.stdout.strip():
            issues.append("Sin output — posible tarea no completada")

        verdict = "approved" if not issues else "needs_review"

        review_result = {
            "task_id": result.task_id,
            "verdict": verdict,
            "issues": issues,
            "files_modified": result.files_modified,
            "duration": result.duration,
        }

        if self.verbose:
            if verdict == "approved":
                print(f"  ✅ BUFFY: Tarea aprobada sin issues")
            else:
                print(f"  🔍 BUFFY: Tarea necesita revisión — {len(issues)} issue(s)")
                for issue in issues:
                    print(f"     ⚠️  {issue}")

        return review_result

    def delegate_and_review(self, task: str, files: Optional[List[str]] = None,
                            context: str = "", effort: str = "high",
                            timeout: int = 300) -> tuple:
        """
        Delegar tarea a Claude Code y automáticamente revisar el resultado.

        Returns:
            (ClaudeCodeResult, review_dict)
        """
        result = self.delegate(task, files, context, effort, timeout)
        review = self.review(result)
        return result, review

    def session_summary(self) -> str:
        """Generar resumen de la sesión de supervisión."""
        if not self.session_log:
            return "No hay tareas delegadas en esta sesión."

        lines = [
            "📋 RESUMEN DE SUPERVISIÓN — Buffy ↔ Claude Code",
            f"{'='*55}",
            f"Total tareas delegadas: {len(self.session_log)}",
        ]

        success = sum(1 for s in self.session_log if s['success'])
        failed = len(self.session_log) - success
        total_time = sum(s['duration'] for s in self.session_log)

        lines.append(f"✅ Exitosas: {success}")
        lines.append(f"❌ Fallidas: {failed}")
        lines.append(f"⏱️  Tiempo total: {total_time:.1f}s")
        lines.append("")

        for i, s in enumerate(self.session_log, 1):
            status = "✅" if s['success'] else "❌"
            lines.append(f"  {i}. {status} {s['task']} ({s['duration']:.1f}s)")
            if s['files_modified']:
                for f in s['files_modified'][:3]:
                    lines.append(f"       📄 {f}")

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# CLI para pruebas
# ══════════════════════════════════════════════════════════════════════════

def test_bridge():
    """Probar el bridge con una tarea simple."""
    print(f"\n{'='*60}")
    print("  🧪 TEST: Claude Code Bridge")
    print(f"{'='*60}\n")

    bridge = ClaudeCodeBridge(verbose=True, effort="low", ollama_mode=True, ollama_model="gemma3:latest")

    # Verificar disponibilidad
    status = bridge.status()
    if not status['available']:
        print("❌ Claude Code no está disponible.")
        print("   Instálalo con: npm install -g @anthropic-ai/claude-code")
        return

    print(f"  ✅ Claude Code {status['version']} disponible")
    print(f"  📊 Estado: {json.dumps(status, indent=2, ensure_ascii=False)}")
    print()

    # Prueba simple
    result = bridge.run(
        "Responde solo: 'Hola desde Claude Code, soy tu sub-agente!'",
        timeout=60,
    )

    print(f"\n  Resultado:")
    print(f"  {'='*40}")
    print(f"  ✅ Success: {result.success}")
    print(f"  ⏱️  Duration: {result.duration:.1f}s")
    print(f"  📄 Output: {result.output[:200]}")
    print(f"  Exit code: {result.exit_code}")

    return result.success


def cli():
    """CLI para interactuar con el bridge."""
    import argparse

    parser = argparse.ArgumentParser(
        description="🤖 Claude Code Bridge — Buffy ↔ Claude Code Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Ver estado
  python claude_code_bridge.py status

  # Ejecutar tarea simple
  python claude_code_bridge.py run --task "Crea un README para el proyecto"

  # Ejecutar con archivos
  python claude_code_bridge.py run -t "Refactoriza este código" -f simmoon_pipeline.py

  # Prueba rápida
  python claude_code_bridge.py test

  # Ver historial
  python claude_code_bridge.py history
        """,
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos')

    # status
    subparsers.add_parser('status', help='Ver estado del bridge')

    # test
    subparsers.add_parser('test', help='Probar conexión con Claude Code')

    # run
    run_parser = subparsers.add_parser('run', help='Ejecutar tarea en Claude Code')
    run_parser.add_argument('-t', '--task', required=True, help='Descripción de la tarea')
    run_parser.add_argument('-f', '--files', nargs='*', help='Archivos relevantes')
    run_parser.add_argument('-c', '--context', help='Contexto adicional')
    run_parser.add_argument('--effort', default='medium',
                            choices=['low', 'medium', 'high', 'xhigh', 'max'])
    run_parser.add_argument('--timeout', type=int, default=300)
    run_parser.add_argument('--model', help='Modelo específico')

    # review
    review_parser = subparsers.add_parser('review', help='Revisar último resultado')
    review_parser.add_argument('--task-id', help='ID de la tarea a revisar')

    # history
    subparsers.add_parser('history', help='Ver historial de esta sesión')

    args = parser.parse_args()

    bridge = ClaudeCodeBridge(verbose=True)

    if args.command == 'status':
        status = bridge.status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif args.command == 'test':
        success = test_bridge()
        sys.exit(0 if success else 1)

    elif args.command == 'run':
        if not bridge.available:
            print("❌ Claude Code no disponible. Usa 'status' para verificar.")
            sys.exit(1)

        result = bridge.run_task(
            task=args.task,
            files=args.files,
            context=args.context or "",
            effort=args.effort,
            timeout=args.timeout,
            model=args.model,
        )

        print(f"\n{'='*60}")
        print(f"  {'✅' if result.success else '❌'} Tarea: {args.task[:80]}")
        print(f"  {'='*60}")
        print(f"  Exit: {result.exit_code} | Duración: {result.duration:.1f}s")
        if result.files_modified:
            print(f"  Archivos: {', '.join(result.files_modified[:10])}")
        print(f"\n  📄 Output:")
        print(f"  {result.output[:1000]}")
        if len(result.output) > 1000:
            print(f"  ... ({len(result.output) - 1000} chars más)")

    elif args.command == 'review':
        if args.task_id:
            results = [r for r in bridge.history if r.task_id == args.task_id]
        else:
            results = [bridge.history[-1]] if bridge.history else []

        if not results:
            print("📭 No hay resultados para revisar.")
            return

        for r in results:
            print(f"\n{'='*60}")
            print(f"  🔍 REVISIÓN: {r.task_id}")
            print(f"  {'='*60}")
            print(f"  Tarea: {r.task[:100]}")
            print(f"  Estado: {'✅' if r.success else '❌'}")
            print(f"  Duración: {r.duration:.1f}s")
            print(f"  Archivos: {', '.join(r.files_modified[:10]) or 'ninguno'}")
            print(f"\n  Resumen:")
            print(f"  {r.summary[:500] if r.summary else '(no disponible)'}")

    elif args.command == 'history':
        if not bridge.history:
            print("📭 No hay ejecuciones en esta sesión.")
            return
        for i, h in enumerate(bridge.history, 1):
            status = "✅" if h.success else "❌"
            print(f"  {i}. {status} [{h.task_id}] {h.task[:80]}...")
            print(f"     ⏱️  {h.duration:.1f}s | Exit: {h.exit_code}")

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
