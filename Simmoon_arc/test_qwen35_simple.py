#!/usr/bin/env python3
"""Test qwen3.5:4b with 4 simple tasks vs qwen2.5-coder:14b as reference."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from claude_code_bridge import OllamaAnthropicClient

SIMPLE_TASKS = [
    {
        "id": "factorial",
        "name": "Funcion factorial",
        "prompt": "Escribe una funcion Python que calcule el factorial de un numero entero. Incluye type hints, docstring, y manejo de errores para numeros negativos. Al final: RESUMEN:"
    },
    {
        "id": "json_keys",
        "name": "Leer JSON",
        "prompt": "Escribe una funcion que reciba una ruta de archivo JSON y devuelva una lista con sus claves principales (primer nivel). Incluye manejo de errores (FileNotFoundError, JSONDecodeError). Al final: RESUMEN:"
    },
    {
        "id": "timer_decorator",
        "name": "Decorador @timer",
        "prompt": "Escribe un decorador llamado @timer que mida y printee el tiempo de ejecucion de una funcion en segundos. Usa functools.wraps. Al final: RESUMEN:"
    },
    {
        "id": "config_class",
        "name": "Clase Config",
        "prompt": "Escribe una clase Config con metodos get(key) y set(key, value) que almacene en un diccionario interno. Incluye type hints y docstring. Al final: RESUMEN:"
    },
]

MODELS = ["qwen3.5:4b", "qwen2.5-coder:14b"]
all_results = {}

for model in MODELS:
    print(f"\n{'='*60}")
    print(f"  Modelo: {model}")
    print(f"{'='*60}")
    client = OllamaAnthropicClient(model=model, verbose=False)
    all_results[model] = []
    
    for task in SIMPLE_TASKS:
        print(f"\n  ▶ {task['name']}...", end=" ", flush=True)
        start = time.time()
        r = client.run_task(task=task["prompt"], timeout=120)
        duration = time.time() - start
        output = r.output.strip()
        chars = len(output)
        has_summary = "RESUMEN:" in output
        has_code = "```python" in output or "def " in output or "class " in output
        
        result = {
            "task": task["name"],
            "duration": round(duration, 1),
            "chars": chars,
            "has_summary": has_summary,
            "has_code": has_code,
            "success": r.success and chars > 0,
            "preview": output[:200],
        }
        all_results[model].append(result)
        
        status = "✅" if result["success"] else "❌"
        print(f"{status} {duration:.1f}s, {chars} chars")

# ── Comparison ──
print(f"\n\n{'='*60}")
print(f"  COMPARACION: qwen3.5:4b vs qwen2.5-coder:14b (Tareas Simples)")
print(f"{'='*60}")
print(f"\n  {'Tarea':<30} {'qwen3.5:4b':<25} {'qwen2.5-coder:14b':<25}")
print(f"  {'-'*30} {'-'*25} {'-'*25}")

for i, task in enumerate(SIMPLE_TASKS):
    r35 = all_results["qwen3.5:4b"][i]
    r14 = all_results["qwen2.5-coder:14b"][i]
    
    s35 = "✅" if r35["success"] else "❌"
    s14 = "✅" if r14["success"] else "❌"
    
    print(f"  {task['name']:<30} {s35} {r35['duration']:5.1f}s {r35['chars']:5d}c  {s14} {r14['duration']:5.1f}s {r14['chars']:5d}c")

# Summary stats
print(f"\n  {'─'*80}")
print(f"  {'ESTADISTICAS':^80}")
print(f"  {'─'*80}")

for model in MODELS:
    results = all_results[model]
    total_ok = sum(1 for r in results if r["success"])
    avg_time = sum(r["duration"] for r in results) / len(results)
    total_chars = sum(r["chars"] for r in results)
    print(f"  {model:25s}: {total_ok}/{len(results)} tareas OK | {avg_time:5.1f}s avg | {total_chars:5d} chars total")

# Show previews of failures
print(f"\n  {'─'*80}")
print(f"  {'PREVIEWS DE OUTPUT':^80}")
print(f"  {'─'*80}")

for model in MODELS:
    print(f"\n  🧠 {model}:")
    for r in all_results[model]:
        status = "✅" if r["success"] else "❌"
        print(f"    {status} {r['task']}: {r['preview'][:150]}")
        print()
