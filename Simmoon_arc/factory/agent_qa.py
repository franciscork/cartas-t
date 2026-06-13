#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/agent_qa.py — 🎯 QA / Testing

Supervisa la calidad del código que produce Claude Code. Revisa
sintaxis, ejecuta tests, detecta regresiones y problemas comunes.

Con MODO AUTÓNOMO (--daemon): monitorea el código modificado por
Claude, ejecuta verificaciones y reporta hallazgos.

Uso:
    # Modo interactivo
    python factory/agent_qa.py review archivo.py
    python factory/agent_qa.py syntax archivo.py
    python factory/agent_qa.py tests
    python factory/agent_qa.py health

    # Modo autónomo (NUEVO)
    python factory/agent_qa.py daemon
    python factory/agent_qa.py daemon --interval 20
    python factory/agent_qa.py once
    python factory/agent_qa.py status
"""

import ast
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from factory.agent_base import AgentDaemon, _consulta_llm, _extraer_json

DEFAULT_MODEL = "qwen2.5-coder:14b"

# ── System prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un **QA Engineer** experto, parte del equipo FactoryGames.
Tu especialidad es la **revisión de calidad de código, testing y detección de bugs**.

Tus habilidades:
- Revisión de sintaxis y estilo de código Python
- Detección de bugs comunes (off-by-one, None checks, encoding, recursos)
- Análisis de regresiones comparando cambios recientes
- Sugerencia y ejecución de tests unitarios
- Verificación de tipos y imports
- Detección de código muerto, duplicado o mal optimizado

Tono: técnico, preciso, constructivo. Usa emojis de QA (🔍 🐛 ✅ 🚨 🧪).
Sé específico: menciona línea exacta, archivo y sugerencia de fix.
"""

# ── Checkers de código ───────────────────────────────────────────────────

def _check_syntax(filepath: Path) -> Tuple[bool, str]:
    """Verificar sintaxis de un archivo Python.

    Returns:
        (ok, mensaje)
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        ast.parse(source)
        return True, "✅ Sintaxis correcta"
    except SyntaxError as e:
        return False, f"❌ Error de sintaxis: {e}"
    except UnicodeDecodeError as e:
        return False, f"❌ Error de encoding: {e}"
    except Exception as e:
        return False, f"❌ Error inesperado: {e}"


def _run_tests(test_files: Optional[List[str]] = None,
               cwd: Optional[Path] = None) -> Tuple[bool, str, int, int]:
    """Ejecutar pytest sobre archivos de test específicos o todo el proyecto.

    Returns:
        (ok, output, passed, failed)
    """
    if cwd is None:
        cwd = SCRIPT_DIR

    cmd = [sys.executable, "-m", "pytest"]
    if test_files:
        cmd.extend(test_files)
    cmd.extend(["-v", "--tb=short", "--no-header"])

    try:
        r = subprocess.run(
            cmd, cwd=str(cwd),
            capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace"
        )
        output = r.stdout + r.stderr

        # Parsear resultados
        passed = output.count("PASSED")
        failed = output.count("FAILED")
        errored = output.count("ERROR")
        total_failures = failed + errored

        if r.returncode == 0:
            return True, output, passed, total_failures
        else:
            return False, output, passed, total_failures
    except subprocess.TimeoutExpired:
        return False, "❌ Timeout: los tests tomaron más de 120s", 0, 0
    except Exception as e:
        return False, f"❌ Error ejecutando tests: {e}", 0, 0


def _check_imports(filepath: Path) -> List[str]:
    """Verificar que los imports de un archivo Python funcionan.

    Returns:
        Lista de problemas encontrados
    """
    issues = []
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("."):  # relative import
                        continue
                    # Solo verificar imports del proyecto
                    if any(alias.name.startswith(p) for p in ["factory", "simmoon_"]):
                        try:
                            __import__(alias.name)
                        except ImportError as e:
                            issues.append(f"Import '{alias.name}' falló: {e}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and not node.module.startswith("."):
                    if any(node.module.startswith(p) for p in ["factory", "simmoon_"]):
                        try:
                            __import__(node.module)
                        except ImportError as e:
                            issues.append(f"Import '{node.module}' falló: {e}")
    except Exception:
        pass  # Si no se puede parsear, el syntax check ya lo atrapó
    return issues


def _check_todos(filepath: Path) -> List[str]:
    """Buscar TODO, FIXME, HACK en el archivo.

    Returns:
        Lista de líneas con TODOs
    """
    issues = []
    try:
        for i, line in enumerate(filepath.read_text(encoding="utf-8").split("\n"), 1):
            upper = line.upper()
            if any(marker in upper for marker in ["TODO", "FIXME", "HACK", "XXX"]):
                issues.append(f"  L{i}: {line.strip()[:80]}")
    except Exception:
        pass
    return issues


def _check_for_common_bugs(filepath: Path) -> List[str]:
    """Buscar patrones de bugs comunes en código Python.

    Returns:
        Lista de problemas encontrados
    """
    issues = []
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            # except: sin especificar excepción (muy amplio)
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(f"  L{node.lineno}: 'except:' sin especificar — atrapa demasiado")

            # comparación con None con == en vez de is
            if isinstance(node, ast.Compare):
                for op, comp in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        if isinstance(comp, ast.Constant) and comp.value is None:
                            issues.append(f"  L{node.lineno}: usar 'is None' en vez de '== None'")

            # print() en producción (excepto si está en test)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    if "test_" not in filepath.stem:
                        issues.append(f"  L{node.lineno}: print() en código de producción")

            # os.system o subprocess.run con shell=True
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "system" and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        issues.append(f"  L{node.lineno}: os.system() — preferir subprocess")
                    if node.func.attr == "run" or node.func.attr == "Popen":
                        for kw in node.keywords:
                            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                issues.append(f"  L{node.lineno}: shell=True es riesgoso")

    except SyntaxError:
        pass  # Ya verificado por _check_syntax
    except Exception:
        pass
    return issues


def review_file(filepath: str) -> Dict[str, Any]:
    """Ejecutar todas las verificaciones QA sobre un archivo.

    Args:
        filepath: Ruta al archivo a revisar (relativa a SCRIPT_DIR)

    Returns:
        Dict con resultados de todas las verificaciones
    """
    path = SCRIPT_DIR / filepath
    if not path.exists():
        return {"error": f"Archivo no encontrado: {filepath}", "ok": False}

    if path.suffix not in (".py",):
        return {"error": f"Formato no soportado: {path.suffix} (solo .py)", "ok": False}

    result = {
        "file": filepath,
        "ok": True,
        "syntax": None,
        "imports": [],
        "bugs": [],
        "todos": [],
    }

    # 1. Syntax check
    syntax_ok, syntax_msg = _check_syntax(path)
    result["syntax"] = {"ok": syntax_ok, "msg": syntax_msg}
    if not syntax_ok:
        result["ok"] = False

    # 2. Imports
    result["imports"] = _check_imports(path)
    if result["imports"]:
        result["ok"] = False

    # 3. Bugs comunes
    result["bugs"] = _check_for_common_bugs(path)

    # 4. TODOs
    result["todos"] = _check_todos(path)

    return result


# ══════════════════════════════════════════════════════════════════════════
#  QA Agent
# ══════════════════════════════════════════════════════════════════════════

class QAAgent(AgentDaemon):
    """Agente de QA/Testing — supervisa la calidad del código.

    Extiende AgentDaemon para operar en modo autónomo: monitorea
    los archivos modificados por Claude y ejecuta verificaciones.
    """

    def __init__(self, model: str = DEFAULT_MODEL, verbose: bool = True,
                 interval_minutos: int = 20):
        super().__init__(
            name="QA Agent",
            emoji="🎯",
            role="Control de Calidad y Testing",
            model=model,
            system_prompt=SYSTEM_PROMPT,
            verbose=verbose,
            interval_minutos=interval_minutos,
        )
        self.capabilities = [
            "code_review", "syntax_check", "test_runner",
            "bug_detection", "regression_check", "import_verifier"
        ]

    # ── QA operations ────────────────────────────────────────────────

    def review(self, filepath: str) -> Dict[str, Any]:
        """Revisar un archivo completo."""
        return review_file(filepath)

    def review_text(self, filepath: str) -> str:
        """Revisar archivo y devolver texto formateado."""
        result = self.review(filepath)

        if "error" in result:
            return f"❌ {result['error']}"

        lines = [f"\n  🎯 QA Review: {result['file']}"]
        lines.append(f"  {'─'*50}")

        # Syntax
        s = result.get("syntax", {})
        if s:
            lines.append(f"\n  📝 Sintaxis: {s.get('msg', '?')}")

        # Imports
        imports = result.get("imports", [])
        if imports:
            lines.append(f"\n  🔗 Problemas de imports ({len(imports)}):")
            for i in imports:
                lines.append(f"     {i}")

        # Bugs
        bugs = result.get("bugs", [])
        if bugs:
            lines.append(f"\n  🐛 Posibles bugs ({len(bugs)}):")
            for b in bugs:
                lines.append(f"     {b}")
        else:
            lines.append(f"\n  🐛 Sin bugs detectados")

        # TODOs
        todos = result.get("todos", [])
        if todos:
            lines.append(f"\n  📌 TODOs pendientes ({len(todos)}):")
            for t in todos:
                lines.append(f"     {t}")

        verdict = "✅ APROBADO" if result.get("ok", False) else "❌ REQUIERE REVISIÓN"
        lines.append(f"\n  {'─'*50}")
        lines.append(f"  Veredicto: {verdict}\n")

        return "\n".join(lines)

    def run_tests(self, test_files: Optional[List[str]] = None) -> str:
        """Ejecutar tests y devolver resumen formateado."""
        ok, output, passed, failed = _run_tests(test_files)

        if test_files:
            header = f"  {'/'.join(test_files)}"
        else:
            header = "Todos los tests"

        lines = [
            f"\n  🧪 Tests: {header}",
            f"  {'─'*50}",
        ]

        if not output:
            lines.append("  ⚠️  No se pudo ejecutar pytest")
        else:
            # Mostrar solo resumen (últimas líneas)
            summary_lines = [l for l in output.split("\n")
                           if any(k in l for k in ["PASSED", "FAILED", "ERROR", "passed",
                                                    "failed", "error", "==", "short test"])]
            for l in summary_lines[-15:]:
                lines.append(f"  {l.strip()}")

        verdict = "✅ Todos los tests pasan" if ok else f"❌ {failed} test(s) fallaron"
        lines.append(f"\n  Veredicto: {verdict}\n")

        return "\n".join(lines)

    def full_scan(self, paths: Optional[List[str]] = None) -> str:
        """Escanear archivos Python en busca de problemas.

        Args:
            paths: Lista de paths a escanear (relativos a SCRIPT_DIR).
                   Si es None, escanea factory/ y archivos .py raíz.
        """
        if paths is None:
            paths = ["factory/"]
            # Agregar archivos .py raíz
            for f in sorted(SCRIPT_DIR.glob("*.py")):
                if f.stem.startswith("test_") or f.stem.startswith("_"):
                    continue
                if f.name in ("factory.py", "agatha_actas.py",
                              "juego_simmoon.py", "dashboard.py",
                              "dashboard_collectors.py", "telegram_bot.py"):
                    paths.append(f.name)

        lines = [f"\n  🎯 QA Full Scan — {len(paths)} archivo(s)"]
        lines.append(f"  {'='*55}")

        total_issues = 0
        for filepath in paths:
            result = self.review(filepath)
            if "error" in result:
                lines.append(f"\n  ⚠️  {filepath}: {result['error']}")
                continue

            issues = (len(result.get("imports", [])) +
                     len(result.get("bugs", [])) +
                     len(result.get("todos", [])))
            if not result.get("syntax", {}).get("ok", True):
                issues += 1

            icon = "✅" if issues == 0 else f"⚠️  ({issues})"
            lines.append(f"  {icon} {filepath}")
            total_issues += issues

        lines.append(f"\n  {'─'*50}")
        lines.append(f"  Total: {total_issues} issue(s) en {len(paths)} archivo(s)")
        lines.append("")

        return "\n".join(lines)

    # ── Lógica autónoma ─────────────────────────────────────────────

    def _get_recent_changes(self) -> List[str]:
        """Obtener archivos modificados en el último commit."""
        try:
            r = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True, text=True, timeout=5,
                cwd=str(SCRIPT_DIR)
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().split("\n")
        except Exception:
            pass
        return []

    def decidir_siguiente_tarea(self) -> Optional[Dict[str, Any]]:
        """Decidir qué verificación de calidad ejecutar LOCALMENTE.

        A diferencia de Creativo/Guionista que delegan a Claude,
        el QA Agent ejecuta los checks directamente (ast.parse,
        pytest) y solo informa resultados. Si encuentra bugs,
        puede delegar la corrección a Claude.

        Returns:
            Dict con 'action', 'target' o None si no hay nada.
        """
        recientes = self._get_recent_changes()
        diff_info = "\n".join(f"  - {f}" for f in recientes[:10])

        prompt = (
            f"Eres el QA Agent de FactoryGames. "
            f"Debes decidir QUÉ verificación ejecutar LOCALMENTE.\n\n"
            f"Contexto del proyecto:\n"
            f"- Sistema FactoryGames en Python\n"
            f"- Tests con pytest en la carpeta Simmoon_arc/\n"
            f"- Claude Code produce código que necesita revisión\n"
            f"- Tú puedes ejecutar checks SIN Claude\n\n"
            f"Cambios recientes ({len(recientes)} archivos):\n"
            f"{diff_info or '  (sin cambios detectados)'}\n\n"
            f"Elige UNA acción concreta de QA:\n"
            f"  1. 'syntax': verificar sintaxis de archivos .py\n"
            f"  2. 'tests': ejecutar pytest\n"
            f"  3. 'scan': escanear bugs y patrones problemáticos\n"
            f"  4. 'review': revisar un archivo específico\n\n"
            f"Responde SOLO con JSON:\n"
            f"{{\n"
            f'  "action": "syntax|tests|scan|review",\n'
            f'  "target": "archivo_o_ruta o vacío",\n'
            f'  "razon": "por qué esta acción es prioritaria"\n'
            f"}}\n\n"
            f"Si no hay nada que hacer, responde: {{\"action\": \"\"}}"
        )

        respuesta = self._preguntar(prompt, temperature=0.4, max_tokens=1024)
        if not respuesta:
            return None

        decision = _extraer_json(respuesta)
        if not decision or not decision.get("action"):
            if self.verbose:
                print(f"     ℹ️  Sin acción de QA decidida")
            return None

        return decision

    # ── Override: run_once ejecuta QA local, no delega a Claude ────

    def run_once(self) -> bool:
        """Ejecutar un ciclo de QA localmente (sin delegar a Claude).

        El QA Agent ejecuta verificaciones directamente:
        - Syntax check: usa ast.parse (instantáneo)
        - Tests: ejecuta pytest (rápido)
        - Scan: analiza AST buscando bugs
        - Review: análisis completo de un archivo

        Solo si encuentra bugs, delega la corrección a Claude.
        """
        ahora = datetime.now().strftime("%H:%M")
        if self.verbose:
            print(f"\n  {self.emoji} [{ahora}] {self.name} — ciclo QA local")

        # Decidir qué check ejecutar
        decision = self.decidir_siguiente_tarea()
        if not decision:
            if self.verbose:
                print(f"     ℹ️  Sin verificaciones pendientes")
            return False

        action = decision.get("action", "")
        target = decision.get("target", "")
        razon = decision.get("razon", "")

        if self.verbose:
            print(f"     🎯 Acción: {action} {target or ''}")
            print(f"     💡 Razón: {razon[:100]}")

        ejecutado = False
        necesita_fix = False
        detalle_resultado = ""

        # ── Syntax check ──
        if action == "syntax":
            if target:
                files_to_check = [target] if (SCRIPT_DIR / target).exists() else []
            else:
                files_to_check = [str(f.relative_to(SCRIPT_DIR))
                                 for f in (SCRIPT_DIR / "factory").glob("*.py")]
                files_to_check.append("factory.py")

            ejecutado = True
            errores = []
            for fp in files_to_check:
                ok, msg = _check_syntax(SCRIPT_DIR / fp)
                if not ok:
                    errores.append(f"{fp}: {msg}")
                    if self.verbose:
                        print(f"     ❌ {msg}")
                elif self.verbose:
                    print(f"     ✅ {fp}: sintaxis correcta")

            if errores:
                necesita_fix = True
                detalle_resultado = "\n".join(errores)

        # ── Tests ──
        elif action == "tests":
            ejecutado = True
            ok, output, passed, failed = _run_tests(cwd=SCRIPT_DIR)
            if self.verbose:
                print(f"     📊 {passed} passed, {failed} failed")

            if not ok:
                necesita_fix = True
                detalle_resultado = output
                # Delegar a Claude si hay tests fallando
                if self.verbose:
                    print(f"     🚨 {failed} test(s) fallando — delegando corrección a Claude...")
                self.delegate_to_claude(
                    task=f"Corregir {failed} test(s) fallando",
                    context=f"Resultados:\n{output[-1000:]}",
                )

        # ── Scan ──
        elif action == "scan":
            ejecutado = True
            issues = []
            scan_targets = ["factory/"]
            if target and (SCRIPT_DIR / target).exists():
                scan_targets = [target]
            elif target:
                if self.verbose:
                    print(f"     ⚠️  Target '{target}' no encontrado, escaneando factory/")

            # Recolectar archivos .py a escanear
            scan_files = []
            for st in scan_targets:
                p = SCRIPT_DIR / st
                if p.is_dir():
                    scan_files.extend(p.glob("**/*.py"))
                elif p.is_file() and p.suffix == ".py":
                    scan_files.append(p)

            for fp in scan_files:
                rel = fp.relative_to(SCRIPT_DIR)
                r = review_file(str(rel))
                file_issues = []
                if r.get("bugs"):
                    file_issues.extend(r["bugs"])
                if r.get("todos"):
                    file_issues.extend(r["todos"])
                if r.get("imports"):
                    file_issues.extend(r["imports"])
                if not r.get("syntax", {}).get("ok", True):
                    file_issues.append(r["syntax"]["msg"])

                if file_issues:
                    issues.append(f"\n  📄 {rel} ({len(file_issues)} issue(s)):")
                    for iss in file_issues[:5]:
                        issues.append(f"     {iss}")
                    if len(file_issues) > 5:
                        issues.append(f"     ... y {len(file_issues)-5} más")

            if self.verbose:
                print(f"     Escaneados {len(scan_files)} archivo(s)")
                if issues:
                    print("     " + "\n     ".join(issues))
                else:
                    print("     ✅ Sin issues encontrados")

            if issues:
                necesita_fix = True
                detalle_resultado = "\n".join(issues)

        # ── Review ──
        elif action == "review":
            if not target:
                target = "factory/orchestrator.py"
            fp = SCRIPT_DIR / target
            if fp.exists() and fp.suffix == ".py":
                ejecutado = True
                result = review_file(str(fp.relative_to(SCRIPT_DIR)))
                issues = (result.get("bugs", []) +
                         result.get("todos", []) +
                         result.get("imports", []))

                if self.verbose:
                    print(f"     {'✅ Sin issues' if not issues else f'⚠️  {len(issues)} issue(s)'}")
                    for iss in issues[:10]:
                        print(f"     {iss}")

                if issues:
                    necesita_fix = True
                    detalle_resultado = "\n".join(issues)

        # ── Registrar resultado ──
        if ejecutado:
            self.memoria.add_task(
                task_type="qa_check",
                description=f"QA {action}: {target or 'default'} ({razon[:60]})",
                delegated_to="local",
                status="completed" if not necesita_fix else "pending",
            )
            self.memoria.add_decision(
                decision=f"QA {action} on {target or 'project'}: "
                        f"{'✅ OK' if not necesita_fix else '⚠️  Issues found'}",
                context=detalle_resultado[:500],
            )

        # ── Si hay bugs, delegar fix a Claude ──
        if necesita_fix and detalle_resultado:
            if self.bridge:
                if self.verbose:
                    print(f"     🔧 Delegando corrección a Claude...")
                self.delegate_to_claude(
                    task=f"Corregir issues encontrados por QA: {action} - {razon[:80]}",
                    context=detalle_resultado[:2000],
                    files=[target] if target else [],
                )

        return ejecutado

    # ── Utilidad ─────────────────────────────────────────────────────

    def resumen(self) -> dict:
        """Resumen del agente para registro."""
        return {
            "name": self.name,
            "emoji": self.emoji,
            "role": self.role,
            "model": self.model,
            "capabilities": self.capabilities,
            "available": True,
            "modo_autonomo": True,
            "bridge_disponible": self.bridge is not None,
        }

    def __str__(self):
        return f"{self.emoji} {self.name} — {self.role}"


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    """Interfaz CLI para el QA Agent."""
    import argparse
    parser = argparse.ArgumentParser(
        description="🎯 QA Agent — Control de Calidad y Testing Autónomo"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Ollama")
    parser.add_argument("--quiet", "-q", action="store_true", help="Modo silencioso")

    sub = parser.add_subparsers(dest="command")

    # Comandos interactivos
    p_review = sub.add_parser("review", help="Revisar un archivo")
    p_review.add_argument("filepath", help="Archivo a revisar")

    p_syntax = sub.add_parser("syntax", help="Verificar sintaxis")
    p_syntax.add_argument("filepath", help="Archivo a verificar")

    p_tests = sub.add_parser("tests", help="Ejecutar tests")
    p_tests.add_argument("--files", "-f", nargs="*", help="Archivos de test específicos")

    p_scan = sub.add_parser("scan", help="Escanear proyecto completo")
    p_scan.add_argument("--paths", "-p", nargs="*", help="Paths específicos")

    p_health = sub.add_parser("health", help="Verificar disponibilidad")

    # Comandos autónomos
    p_daemon = sub.add_parser("daemon", help="🧠 Modo autónomo")
    p_daemon.add_argument("--interval", "-i", type=int, default=20,
                          help="Intervalo en minutos (default: 20)")

    p_status = sub.add_parser("status", help="Estado del agente")
    p_once = sub.add_parser("once", help="Un ciclo de decisión")

    args = parser.parse_args()

    qa = QAAgent(model=args.model, verbose=not args.quiet)

    if args.command == "review":
        print(qa.review_text(args.filepath))
    elif args.command == "syntax":
        path = SCRIPT_DIR / args.filepath
        if not path.exists():
            print(f"  ❌ Archivo no encontrado: {args.filepath}")
            return
        ok, msg = _check_syntax(path)
        print(f"  {msg}")
    elif args.command == "tests":
        print(qa.run_tests(args.files))
    elif args.command == "scan":
        print(qa.full_scan(args.paths))
    elif args.command == "health":
        info = qa.resumen()
        print(f"✅ {info['name']}")
        print(f"   Role: {info['role']}")
        print(f"   Modelo: {info['model']}")
        print(f"   Capacidades: {', '.join(info['capabilities'])}")
        print(f"   🧠 Modo autónomo: {'✅' if info['modo_autonomo'] else '❌'}")
        print(f"   🔗 Bridge Claude: {'✅' if info['bridge_disponible'] else '❌'}")
    elif args.command == "daemon":
        print(qa.status_text())
        qa.run_daemon(interval_minutos=args.interval)
    elif args.command == "status":
        print(qa.status_text())
    elif args.command == "once":
        ok = qa.run_once()
        print(f"\n  {'✅' if ok else 'ℹ️'} Ciclo completado")
        print(qa.memoria.summary())
    else:
        parser.print_help()
        print("\n  Ejemplos:")
        print("    python factory/agent_qa.py review factory/agent_registry.py")
        print("    python factory/agent_qa.py syntax factory/orchestrator.py")
        print("    python factory/agent_qa.py tests")
        print("    python factory/agent_qa.py scan")
        print("    python factory/agent_qa.py daemon          # 🆕 Autónomo")
        print("    python factory/agent_qa.py daemon -i 15    # Cada 15 min")
        print("    python factory/agent_qa.py once            # Un ciclo")
        print("    python factory/agent_qa.py status          # Estado")
        print("    python factory/agent_qa.py health")


if __name__ == "__main__":
    main()
