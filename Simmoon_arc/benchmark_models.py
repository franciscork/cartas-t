#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_models.py — Benchmark automatico de modelos Ollama para codigo
----------------------------------------------------------------------
Prueba N modelos contra 5 tareas distintas y genera un reporte completo.

Uso:
    python benchmark_models.py                          # Todos los modelos
    python benchmark_models.py --models qwen2.5-coder:14b deepseek-r1:7b
    python benchmark_models.py --tasks 1,2,3            # Solo tareas 1-3
    python benchmark_models.py --parallel 2              # Max 2 tareas simultaneas
    python benchmark_models.py --report-only             # Solo regenerar reporte
    python benchmark_models.py --quick                   # Solo 1 tarea × modelo (rapido)

Las tareas:
    1. TaskQueue  — Clase OOP con persistencia, reintentos, type hints
    2. RateLimiter — Algoritmo token bucket thread-safe
    3. CSVProcessor — Procesamiento de datos con pandas (sin librerias externas)
    4. LogDecorator — Decorator factory con configuracion y logging
    5. Refactor — Limpiar codigo spaghetti dado
"""

import argparse
import ast
import json
import os
import sys
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

try:
    from claude_code_bridge import OllamaAnthropicClient
except ImportError as e:
    print(f"❌ Error: {e}")
    print("   Necesitas claude_code_bridge.py en el mismo directorio.")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════════════════════

RESULTS_DIR = SCRIPT_DIR / "benchmark_results"
RESULTS_DIR.mkdir(exist_ok=True)

REPORT_FILE = RESULTS_DIR / "benchmark_report.json"
HISTORY_FILE = RESULTS_DIR / "benchmark_history.jsonl"
SUMMARY_FILE = RESULTS_DIR / "BENCHMARK_SUMMARY.md"

# Modelos por defecto: los mas relevantes para codigo
DEFAULT_MODELS = [
    "qwen2.5-coder:14b",
    "deepseek-r1:7b",
    "qwen3:14b",
    "qwen3.5:4b",
    "gemma4:latest",
]

# ═══════════════════════════════════════════════════════════════════════════
# TAREAS (5 tareas de codigo diferentes)
# ═══════════════════════════════════════════════════════════════════════════

TASKS = [
    {
        "id": 1,
        "name": "TaskQueue (OOP)",
        "skill": "POO, manejo de errores, persistencia",
        "prompt": (
            "Escribe una clase Python llamada TaskQueue con:\n"
            "1) Constructor: max_retries=3, retry_delay=1.0, persist_path=None\n"
            "2) add_task(name, fn, args=None, kwargs=None)\n"
            "3) run_all() - ejecuta en orden con reintentos (max_retries, retry_delay)\n"
            "4) run_one(task_id) - ejecuta una tarea especifica por indice\n"
            "5) get_status(task_id) - retorna: pending/running/success/failed\n"
            "6) summary() - dict con: total, completed, failed, pending, total_time\n"
            "7) Si persist_path no es None, guarda/recupera estado en JSON\n"
            "8) Cada tarea tiene creation_time y last_execution_time\n"
            "9) Usa type hints, docstrings, y logging (import logging)\n"
            "10) KeyboardInterrupt en run_all() guarda estado antes de salir\n"
            "Incluye un ejemplo de uso. Al final: RESUMEN:"
        ),
        "checks": [
            "class TaskQueue",
            "max_retries",
            "retry_delay",
            "persist_path",
            "add_task",
            "run_all",
            "run_one",
            "get_status",
            "summary",
            "KeyboardInterrupt",
            "logging",
        ],
    },
    {
        "id": 2,
        "name": "RateLimiter (Algoritmo)",
        "skill": "Algoritmos, thread-safety, time",
        "prompt": (
            "Escribe una clase Python llamada RateLimiter que implemente el algoritmo Token Bucket:\n"
            "1) Constructor: rate (tokens/segundo), capacity (max tokens), initial_tokens=None\n"
            "2) acquire(amount=1) -> bool - intenta consumir N tokens, retorna True si hay suficientes\n"
            "3) acquire_blocking(amount=1, timeout=None) -> bool - bloquea hasta conseguir tokens\n"
            "4) get_available_tokens() -> float - tokens disponibles actualmente\n"
            "5) reset() - reinicia el contador\n"
            "6) Thread-safe usando threading.Lock\n"
            "7) Los tokens se regeneran con el tiempo (time.time() para precision)\n"
            "8) Propiedad wait_time -> float: tiempo estimado hasta conseguir 1 token\n"
            "9) Type hints, docstrings, logging\n"
            "Incluye ejemplo de uso. Al final: RESUMEN:"
        ),
        "checks": [
            "class RateLimiter",
            "Token",
            "Bucket",
            "acquire",
            "Lock",
            "threading",
            "time.time",
            "capacity",
            "rate",
        ],
    },
    {
        "id": 3,
        "name": "CSVProcessor (Datos)",
        "skill": "Procesamiento datos, archivos, estadistica",
        "prompt": (
            "Escribe una clase Python llamada CSVProcessor para procesar archivos CSV:\n"
            "1) Constructor: filepath, delimiter=',', has_header=True, encoding='utf-8'\n"
            "2) load() - carga el CSV en memoria (lista de diccionarios o listas segun has_header)\n"
            "3) get_column(name_or_index) -> list - extrae una columna completa\n"
            "4) stats(column) -> dict - media, mediana, min, max, std, count, nulls\n"
            "5) filter_rows(column, operator, value) -> CSVProcessor - retorna nuevo filtrado\n"
            "6) sort_by(column, ascending=True) -> CSVProcessor\n"
            "7) group_by(column) -> dict - agrupa filas por valor de columna\n"
            "8) to_json(path) - exporta a JSON\n"
            "9) SIN usar pandas ni numpy - solo biblioteca estandar (csv, statistics, json)\n"
            "10) Type hints, docstrings, logging, manejo de errores (FileNotFoundError, etc)\n"
            "Incluye ejemplo de uso. Al final: RESUMEN:"
        ),
        "checks": [
            "class CSVProcessor",
            "load",
            "get_column",
            "stats",
            "filter",
            "sort",
            "group_by",
            "to_json",
            "csv",
            "statistics",
        ],
    },
    {
        "id": 4,
        "name": "LogDecorator (Funcional)",
        "skill": "Decoradores, metaprogramacion, logging",
        "prompt": (
            "Escribe un modulo Python con los siguientes decoradores:\n"
            "1) @log_call(level='INFO', logger_name=None) - registra llamada, args, kwargs, resultado\n"
            "2) @log_time(unit='ms', precision=2) - mide y registra tiempo de ejecucion\n"
            "3) @log_errors(raise_original=True, log_traceback=True) - captura excepciones y las loggea\n"
            "4) @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,)) - reintenta con backoff exponencial\n"
            "5) @memoize(ttl=None, max_size=128) - cachea resultados con Time-To-Live opcional\n"
            "6) @rate_limit(calls=10, period=1.0) - limita llamadas por periodo de tiempo\n\n"
            "Cada decorador debe:\n"
            "- Preservar el nombre y docstring de la funcion original (functools.wraps)\n"
            "- Tener type hints completos\n"
            "- Usar logging.getLogger(__name__) para logging\n"
            "- Poder aplicarse individualmente o combinados (@log_time @retry)\n\n"
            "Incluye ejemplo de uso. Al final: RESUMEN:"
        ),
        "checks": [
            "def log_call",
            "def log_time",
            "def log_errors",
            "def retry",
            "def memoize",
            "functools",
            "wraps",
            "logging",
        ],
    },
    {
        "id": 5,
        "name": "Refactor (Calidad)",
        "skill": "Refactorizacion, codigo legacy, clean code",
        "prompt": (
            "REFACTORIZA el siguiente codigo. Hazlo mas legible, mantenible y Pythonico.\n"
            "NO cambies el comportamiento, solo mejora la calidad.\n\n"
            "```python\n"
            "def process_data(d, t):\n"
            "    # t puede ser 'sum', 'avg', 'max', 'min'\n"
            "    if not isinstance(d, list):\n"
            "        return None\n"
            "    if len(d) == 0:\n"
            "        return None\n"
            "    r = None\n"
            "    if t == 'sum':\n"
            "        r = 0\n"
            "        for x in d:\n"
            "            if isinstance(x, (int, float)):\n"
            "                r = r + x\n"
            "    elif t == 'avg':\n"
            "        s = 0\n"
            "        c = 0\n"
            "        for x in d:\n"
            "            if isinstance(x, (int, float)):\n"
            "                s = s + x\n"
            "                c = c + 1\n"
            "        if c > 0:\n"
            "            r = s / c\n"
            "    elif t == 'max':\n"
            "        r = float('-inf')\n"
            "        for x in d:\n"
            "            if isinstance(x, (int, float)):\n"
            "                if x > r:\n"
            "                    r = x\n"
            "        if r == float('-inf'):\n"
            "            r = None\n"
            "    elif t == 'min':\n"
            "        r = float('inf')\n"
            "        for x in d:\n"
            "            if isinstance(x, (int, float)):\n"
            "                if x < r:\n"
            "                    r = x\n"
            "        if r == float('inf'):\n"
            "            r = None\n"
            "    else:\n"
            "        return None\n"
            "    return r\n"
            "```\n\n"
            "MEJORAS ESPERADAS:\n"
            "- Nombre de funcion y variables claros\n"
            "- Type hints y docstring\n"
            "- Separar validacion de logica\n"
            "- Usar funciones built-in de Python (sum, max, min, statistics)\n"
            "- Manejar edge cases (lista vacia, datos no numericos, tipo invalido)\n"
            "- Hacer el codigo extensible para nuevos tipos de operacion\n\n"
            "Incluye la version refactorizada COMPLETA. Al final: RESUMEN:"
        ),
        "checks": [
            "def ",
            "TypeError",
            "ValueError",
            "statistics",
            "sum",
            "docstring",
            "type hint",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIONES DEL BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    SUPPORTS = (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        and os.environ.get('TERM') not in ('', 'dumb')
    )
    @classmethod
    def c(cls, text, color):
        return f"{color}{text}{cls.RESET}" if cls.SUPPORTS else text


def validate_syntax(code: str) -> Tuple[bool, str]:
    """Validar sintaxis Python del codigo generado."""
    # Extraer bloques de codigo entre triple backticks
    blocks = re.findall(r'```python\n?(.*?)```', code, re.DOTALL)
    if not blocks:
        return False, "No se encontraron bloques de codigo Python"
    
    for block in blocks:
        try:
            ast.parse(block.strip())
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"
    return True, "OK"


def count_requirements(output: str, checks: List[str]) -> Tuple[int, int]:
    """Contar cuantos requerimientos se cumplen."""
    found = sum(1 for c in checks if c.lower() in output.lower())
    return found, len(checks)


def count_imports(output: str) -> int:
    return len(re.findall(r'^(?:import |from )', output, re.MULTILINE))


def count_functions(output: str) -> int:
    return len(re.findall(r'^def |^    def ', output, re.MULTILINE))


def count_classes(output: str) -> int:
    return len(re.findall(r'^class ', output, re.MULTILINE))


def has_type_hints(output: str) -> bool:
    # Busca: def nombre(params: tipo, ...)  o  def nombre(params: tipo, ...) -> tipo:
    # [^)]*?: captura el primer : dentro de los parentesis (el tipo hint)
    return bool(re.search(r'def \w+\([^)]*?:[^)]*\)\s*(?:->[^:]*)?\s*:', output, re.DOTALL))


def has_docstrings(output: str) -> bool:
    return bool(re.search(r'""".*?"""', output, re.DOTALL))


def has_logging(output: str) -> bool:
    return 'logging' in output.lower() and ('logging.getLogger' in output or 'import logging' in output)


def has_summary(output: str) -> bool:
    return 'RESUMEN:' in output


def has_example(output: str) -> bool:
    return bool(re.search(r'(?:ejemplo|example|uso|usage|if __name__)', output, re.I))


def run_single_benchmark(model: str, task: dict, timeout: int = 300) -> dict:
    """Ejecutar una combinacion modelo × tarea y devolver metricas."""
    task_id = task["id"]
    task_name = task["name"]
    prompt = task["prompt"]
    
    client = OllamaAnthropicClient(model=model, verbose=False)
    
    start = time.time()
    try:
        result = client.run_task(task=prompt, timeout=timeout)
    except Exception as e:
        duration = time.time() - start
        return {
            "model": model, "task_id": task_id, "task_name": task_name,
            "duration": round(duration, 1), "success": False,
            "error": str(e), "chars": 0, "lines": 0, "syntax_valid": False,
            "syntax_error": str(e), "requirements_found": 0, "requirements_total": len(task["checks"]),
            "imports": 0, "functions": 0, "classes": 0, "type_hints": False,
            "docstrings": False, "logging": False, "has_summary": False, "has_example": False,
            "output": "",
        }
    
    duration = time.time() - start
    output = result.output.strip()
    
    # Metricas
    lines = len(output.splitlines())
    chars = len(output)
    syntax_valid, syntax_error = validate_syntax(output)
    req_found, req_total = count_requirements(output, task["checks"])
    
    return {
        "model": model,
        "task_id": task_id,
        "task_name": task_name,
        "duration": round(duration, 1),
        "success": result.success and bool(output),
        "error": "",
        "chars": chars,
        "lines": lines,
        "syntax_valid": syntax_valid,
        "syntax_error": syntax_error if not syntax_valid else "",
        "requirements_found": req_found,
        "requirements_total": req_total,
        "imports": count_imports(output),
        "functions": count_functions(output),
        "classes": count_classes(output),
        "type_hints": has_type_hints(output),
        "docstrings": has_docstrings(output),
        "logging": has_logging(output),
        "has_summary": has_summary(output),
        "has_example": has_example(output),
        "output_preview": output[:150] + "..." if len(output) > 150 else output,
    }


def print_progress(current: int, total: int, model: str, task_name: str, result: dict):
    """Mostrar progreso en terminal."""
    duration = result.get("duration", 0)
    ok = result.get("success", False) and result.get("syntax_valid", False)
    status = Colors.c("✅", Colors.GREEN) if ok else Colors.c("❌", Colors.RED)
    req = result.get("requirements_found", 0)
    req_t = result.get("requirements_total", 0)
    model_padded = model.ljust(28)[:28]
    dur_str = f"{duration:5.1f}s"
    chars_val = result.get('chars', 0)
    print(
        f"  [{current:2d}/{total:2d}] {status} "
        f"{Colors.c(model_padded, Colors.CYAN)} "
        f"{task_name:22s} "
        f"{Colors.c(dur_str, Colors.DIM)} "
        f"{req}/{req_t} req  "
        f"{chars_val:5d} chars"
    )


def print_header(text: str):
    print(f"\n  {Colors.c('='*60, Colors.DIM)}")
    print(f"  {Colors.c(text, Colors.BOLD)}")
    print(f"  {Colors.c('='*60, Colors.DIM)}")


# ═══════════════════════════════════════════════════════════════════════════
# REPORTES
# ═══════════════════════════════════════════════════════════════════════════

def generate_summary(results: List[dict], models: List[str], total_duration: float):
    """Generar reporte markdown con tabla comparativa."""
    lines = []
    lines.append("# 📊 Benchmark de Modelos Ollama para Código")
    lines.append("")
    lines.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Modelos evaluados:** {len(models)}")
    lines.append(f"**Tareas:** {5}")
    lines.append(f"**Ejecuciones totales:** {len(results)}")
    lines.append(f"**Duración total:** {total_duration:.1f}s ({total_duration/60:.1f}m)")
    lines.append("")
    
    # ── Tabla resumen por modelo (promedio de todas las tareas) ──
    lines.append("## 🏆 Ranking General (promedio por modelo)")
    lines.append("")
    lines.append("| Rank | Modelo | ⏱ Promedio | ✅ Tareas OK | 📏 Chars | 💻 Sintaxis | 📋 Reqs | 📝 Type Hints |")
    lines.append("|------|--------|:----------:|:----------:|:--------:|:----------:|:------:|:-------------:|")
    
    model_stats = {}
    for model in models:
        model_results = [r for r in results if r["model"] == model]
        if not model_results:
            continue
        
        avg_duration = sum(r["duration"] for r in model_results) / len(model_results)
        tasks_ok = sum(1 for r in model_results if r["success"])
        syntax_ok = sum(1 for r in model_results if r["syntax_valid"])
        total_chars = sum(r["chars"] for r in model_results)
        avg_req = sum(r["requirements_found"] / max(r["requirements_total"], 1) for r in model_results) / len(model_results)
        type_hints = sum(1 for r in model_results if r["type_hints"])
        
        # Puntaje compuesto (0-100)
        score = (
            (tasks_ok / len(model_results) * 30) +           # 30% tareas completadas
            (syntax_ok / len(model_results) * 25) +           # 25% sintaxis valida
            (avg_req * 20) +                                   # 20% requisitos cumplidos
            (type_hints / len(model_results) * 15) +           # 15% type hints
            (min(total_chars / 3000, 1.0) * 10)               # 10% cantidad de output
        )
        
        model_stats[model] = {
            "score": round(score, 1),
            "avg_duration": round(avg_duration, 1),
            "tasks_ok": tasks_ok,
            "tasks_total": len(model_results),
            "syntax_ok": syntax_ok,
            "total_chars": total_chars,
            "avg_req": f"{avg_req:.0%}",
            "type_hints": type_hints,
        }
    
    # Ordenar por score descendente
    ranked = sorted(model_stats.items(), key=lambda x: x[1]["score"], reverse=True)
    for rank, (model, stats) in enumerate(ranked, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"  {rank}.")
        lines.append(
            f"| {medal} | {model:28s} | "
            f"{stats['avg_duration']:5.1f}s | "
            f"{stats['tasks_ok']}/{stats['tasks_total']} | "
            f"{stats['total_chars']:5d} | "
            f"{stats['syntax_ok']}/{stats['tasks_total']} | "
            f"{stats['avg_req']:>6s} | "
            f"{stats['type_hints']}/{stats['tasks_total']} |"
        )
    
    lines.append("")
    lines.append(f"*Puntaje compuesto: 30% completitud + 25% sintaxis + 20% requisitos + 15% type hints + 10% output*")
    lines.append("")
    
    # ── Matriz detallada modelo × tarea ──
    lines.append("## 📋 Matriz Modelo × Tarea")
    lines.append("")
    
    # Header
    header = "| Modelo |"
    for task in TASKS:
        header += f" ⏱️  {task['name'][:18]} |"
    lines.append(header)
    
    sep = "|--------|"
    for _ in TASKS:
        sep += f"-----------:|"
    lines.append(sep)
    
    for model, _ in ranked:
        row = f"| {model:26s} |"
        for task in TASKS:
            r = next((x for x in results if x["model"] == model and x["task_id"] == task["id"]), None)
            if r:
                ok = r["success"] and r["syntax_valid"]
                status = "✅" if ok else "❌"
                row += f" {status} {r['duration']:4.1f}s |"
            else:
                row += "  -    |"
        lines.append(row)
    
    lines.append("")
    
    # ── Detalle por tarea ──
    lines.append("## 🔍 Detalle por Tarea")
    lines.append("")
    
    for task in TASKS:
        lines.append(f"### Tarea {task['id']}: {task['name']}")
        lines.append(f"*Habilidad: {task['skill']}*")
        lines.append("")
        lines.append("| Modelo | ⏱️  Tiempo | ✅ Completada | 💻 Sintaxis | 📋 Reqs | 📏 Chars | 📝 Hints | 📋 Docs |")
        lines.append("|--------|:--------:|:------------:|:----------:|:------:|:-------:|:-------:|:-------:|")
        
        for model, _ in ranked:
            r = next((x for x in results if x["model"] == model and x["task_id"] == task["id"]), None)
            if r:
                ok = "✅" if r["success"] else "❌"
                syntax = "✅" if r["syntax_valid"] else "❌"
                hints = "✅" if r["type_hints"] else "❌"
                docs = "✅" if r["docstrings"] else "❌"
                req = f"{r['requirements_found']}/{r['requirements_total']}"
                lines.append(
                    f"| {model:28s} | {r['duration']:5.1f}s | {ok} | {syntax} | "
                    f"{req:>5s} | {r['chars']:5d} | {hints} | {docs} |"
                )
        lines.append("")
    
    # ── Conclusiones ──
    lines.append("## 💡 Conclusiones")
    lines.append("")
    if ranked:
        best = ranked[0]
        lines.append(f"- **Mejor modelo general:** `{best[0]}` (puntaje: {best[1]['score']})")
        
        fastest = min(ranked, key=lambda x: x[1]["avg_duration"])
        lines.append(f"- **Mas rapido:** `{fastest[0]}` (promedio {fastest[1]['avg_duration']}s)")
        
        most_accurate = max(ranked, key=lambda x: x[1]["syntax_ok"])
        lines.append(f"- **Menos errores de sintaxis:** `{most_accurate[0]}` ({most_accurate[1]['syntax_ok']}/{most_accurate[1]['tasks_total']} tareas limpias)")
        
        best_code = max(ranked, key=lambda x: x[1]["type_hints"])
        lines.append(f"- **Mejor tipado:** `{best_code[0]}` ({best_code[1]['type_hints']}/{best_code[1]['tasks_total']} con type hints)")
    
    lines.append("")
    lines.append("---")
    lines.append(f"*Generado por benchmark_models.py el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return "\n".join(lines)


def save_results(results: List[dict], models: List[str], total_duration: float):
    """Guardar resultados en JSON y generar reporte markdown."""
    # JSON detallado
    report = {
        "timestamp": datetime.now().isoformat(),
        "models_tested": models,
        "total_tasks": len(TASKS),
        "total_runs": len(results),
        "total_duration_seconds": round(total_duration, 1),
        "results": results,
    }
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Historial (append)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    
    # Markdown legible
    summary = generate_summary(results, models, total_duration)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"\n  {Colors.c('📄 Reporte JSON:', Colors.DIM)} {REPORT_FILE}")
    print(f"  {Colors.c('📄 Resumen MD:', Colors.DIM)} {SUMMARY_FILE}")
    print(f"  {Colors.c('📄 Historial:', Colors.DIM)} {HISTORY_FILE}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="📊 Benchmark automatico de modelos Ollama para codigo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--models", "-m", nargs="+", default=None,
                        help=f"Modelos a testear (default: {DEFAULT_MODELS[0]}, ...)")
    parser.add_argument("--tasks", "-t", type=str, default=None,
                        help="Tareas a ejecutar, separadas por coma (default: 1-5)")
    parser.add_argument("--parallel", "-p", type=int, default=1,
                        help="Max tareas en paralelo (default: 1, secuencial)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout por tarea en segundos (default: 300)")
    parser.add_argument("--report-only", action="store_true",
                        help="Solo regenerar reporte desde resultados existentes")
    parser.add_argument("--quick", "-q", action="store_true",
                        help="Modo rapido: solo 1 tarea × modelo")
    parser.add_argument("--output", "-o", default=str(SUMMARY_FILE),
                        help="Ruta del reporte de salida")
    
    args = parser.parse_args()
    
    # ── Solo regenerar reporte ──
    if args.report_only:
        if not REPORT_FILE.exists():
            print(f"❌ No hay resultados previos en {REPORT_FILE}")
            sys.exit(1)
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report = json.load(f)
        summary = generate_summary(
            report["results"], report["models_tested"], report["total_duration_seconds"]
        )
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"✅ Reporte regenerado en {args.output}")
        return
    
    # ── Modelos a testear ──
    models = args.models or DEFAULT_MODELS
    
    # ── Tareas a ejecutar ──
    if args.tasks:
        task_ids = [int(x.strip()) for x in args.tasks.split(",")]
        tasks = [t for t in TASKS if t["id"] in task_ids]
        if not tasks:
            print(f"❌ No se encontraron tareas con IDs: {task_ids}")
            sys.exit(1)
    elif args.quick:
        tasks = [TASKS[0]]  # Solo la primera tarea
    else:
        tasks = TASKS
    
    # ── Verificar modelos disponibles ──
    available_models = OllamaAnthropicClient.list_models()
    for model in models:
        if model not in available_models:
            print(f"  ⚠️  Modelo '{model}' no encontrado en Ollama. Se saltara.")
    models = [m for m in models if m in available_models]
    
    if not models:
        print("❌ Ningun modelo disponible en Ollama.")
        sys.exit(1)
    
    total_runs = len(models) * len(tasks)
    print_header(f"📊 BENCHMARK: {len(models)} modelos × {len(tasks)} tareas = {total_runs} ejecuciones")
    print(f"  Modelos: {', '.join(Colors.c(m, Colors.CYAN) for m in models)}")
    task_list = [f"{t['id']}. {t['name']}" for t in tasks]
    print(f"  Tareas:  {', '.join(task_list)}")
    print(f"  Paralelo: {args.parallel}")
    print()
    
    # ── Ejecutar benchmark ──
    all_results = []
    completed = 0
    total_start = time.time()
    
    # Crear todas las combinaciones modelo × tarea
    combinations = [(model, task) for model in models for task in tasks]
    
    # Barajar las combinaciones para que modelos diferentes se ejecuten intercalados
    import random
    random.shuffle(combinations)
    
    if args.parallel > 1:
        # Ejecucion paralela
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {
                executor.submit(run_single_benchmark, model, task, args.timeout): (model, task)
                for model, task in combinations
            }
            
            for future in as_completed(futures):
                model, task = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = {
                        "model": model, "task_id": task["id"], "task_name": task["name"],
                        "duration": 0, "success": False, "error": str(e),
                        "chars": 0, "lines": 0, "syntax_valid": False,
                        "requirements_found": 0, "requirements_total": len(task["checks"]),
                        "imports": 0, "functions": 0, "classes": 0,
                        "type_hints": False, "docstrings": False, "logging": False,
                        "has_summary": False, "has_example": False, "output": "",
                    }
                
                completed += 1
                all_results.append(result)
                print_progress(completed, total_runs, model, task["name"], result)
    else:
        # Ejecucion secuencial
        for model, task in combinations:
            result = run_single_benchmark(model, task, args.timeout)
            completed += 1
            all_results.append(result)
            print_progress(completed, total_runs, model, task["name"], result)
    
    total_duration = time.time() - total_start
    
    # ── Resultados finales ──
    print_header("✅ BENCHMARK COMPLETADO")
    print(f"  Total: {total_runs} ejecuciones en {total_duration:.1f}s ({total_duration/60:.1f}m)")
    
    # Guardar resultados
    save_results(all_results, models, total_duration)
    
    # Mostrar ranking
    print_header("🏆 RANKING FINAL")
    
    model_stats = {}
    for model in models:
        mr = [r for r in all_results if r["model"] == model]
        score = (
            (sum(1 for r in mr if r["success"]) / len(mr) * 30) +
            (sum(1 for r in mr if r["syntax_valid"]) / len(mr) * 25) +
            (sum(r["requirements_found"] / max(r["requirements_total"], 1) for r in mr) / len(mr) * 20) +
            (sum(1 for r in mr if r["type_hints"]) / len(mr) * 15) +
            (min(sum(r["chars"] for r in mr) / 3000, 1.0) * 10)
        )
        model_stats[model] = round(score, 1)
    
    ranked = sorted(model_stats.items(), key=lambda x: x[1], reverse=True)
    for rank, (model, score) in enumerate(ranked, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "   ")
        mr = [r for r in all_results if r["model"] == model]
        avg_dur = sum(r["duration"] for r in mr) / len(mr)
        ok = sum(1 for r in mr if r["success"] and r["syntax_valid"])
        print(f"  {medal} {Colors.c(f'{model:30s}', Colors.BOLD)}  "
              f"{Colors.c(f'{score:4.1f}', Colors.GREEN)} pts  "
              f"{Colors.c(f'{ok}/{len(mr)}', Colors.CYAN)} tareas  "
              f"{Colors.c(f'{avg_dur:5.1f}s', Colors.DIM)} avg")
    
    print(f"\n  {Colors.c('📖 Reporte completo:', Colors.DIM)} {SUMMARY_FILE}")
    print()


if __name__ == "__main__":
    main()
