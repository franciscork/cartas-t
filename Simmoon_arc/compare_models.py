#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_models.py — Compara qwen3.5:4b vs qwen2.5-coder:14b
en exactamente la misma tarea de código.
"""

import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from claude_code_bridge import OllamaAnthropicClient

TASK = """Escribe una clase Python llamada TaskQueue con:

1. Constructor: max_retries=3, retry_delay=1.0, persist_path=None
2. add_task(name, fn, args=None, kwargs=None)
3. run_all() - ejecuta en orden con reintentos (max_retries, retry_delay)
4. run_one(task_id) - ejecuta tarea especifica
5. get_status(task_id) - pending/running/success/failed
6. summary() - dict con total, completed, failed, pending, total_time
7. persistencia JSON si persist_path no es None
8. Timestamps: creation_time y last_execution_time por tarea
9. Type hints, docstrings, logging (import logging)
10. Manejar KeyboardInterrupt durante run_all()

Incluye un ejemplo de uso al final.
Al final escribe RESUMEN: (que hiciste)"""

MODELS = ["qwen3.5:4b", "qwen2.5-coder:14b"]
RESULTS = {}

for model in MODELS:
    print(f"\n{'='*60}")
    print(f"  ▶ Ejecutando {model}...")
    print(f"  {'='*60}")

    client = OllamaAnthropicClient(model=model, verbose=False)
    
    start = time.time()
    result = client.run_task(task=TASK, timeout=300)
    duration = time.time() - start
    
    output = result.output.strip()
    
    # Guardar a archivo
    fname = f"compare_{model.replace(':', '_').replace('.', '_')}.txt"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(output)
    
    # Métricas
    lines = output.split('\n')
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('"""')]
    doc_lines = [l for l in lines if '"""' in l or l.strip().startswith('#')]
    has_summary = 'RESUMEN:' in output
    has_example = 'ejemplo' in output.lower() or 'Example' in output or 'Ejemplo' in output
    has_keyboard = 'KeyboardInterrupt' in output
    has_persist = 'persist_path' in output or 'save_state' in output or 'load_state' in output
    has_logging = 'logging' in output.lower()
    has_type_hints = 'def ' in output and (':' in output.split('def ')[-1][:50] if 'def ' in output else False)
    
    RESULTS[model] = {
        'duration': f"{duration:.1f}s",
        'duration_sec': round(duration, 1),
        'total_chars': len(output),
        'total_lines': len(lines),
        'code_lines': len(code_lines),
        'has_summary': has_summary,
        'has_example': has_example,
        'has_keyboardinterrupt': has_keyboard,
        'has_persistencia': has_persist,
        'has_logging': has_logging,
        'exit_code': result.exit_code,
        'success': result.success,
        'file': fname,
        'output_preview': output[:200] + '...' if len(output) > 200 else output,
    }
    
    print(f"  ✅ Completado en {duration:.1f}s")
    print(f"  📄 {len(output)} caracteres, {len(lines)} lineas")
    print(f"  💾 Guardado en {fname}")

# Comparación
print(f"\n\n{'='*60}")
print(f"  📊 COMPARACION: qwen3.5:4b vs qwen2.5-coder:14b")
print(f"  {'='*60}")

metrics = [
    ("⏱️  Tiempo", "duration", "s", True),
    ("📏 Output (chars)", "total_chars", "", False),
    ("📏 Output (lineas)", "total_lines", "", False),
    ("💻 Lineas de codigo", "code_lines", "", False),
    ("📝 RESUMEN incluido", "has_summary", "", False),
    ("🎯 Ejemplo de uso", "has_example", "", False),
    ("⌨️  KeyboardInterrupt", "has_keyboardinterrupt", "", False),
    ("💾 Persistencia JSON", "has_persistencia", "", False),
    ("📋 Logging", "has_logging", "", False),
]

print(f"\n  {'Métrica':<30} {'qwen3.5:4b':<18} {'qwen2.5-coder:14b':<18}")
print(f"  {'-'*30} {'-'*18} {'-'*18}")

for label, key, suffix, reverse in metrics:
    v1 = RESULTS['qwen3.5:4b'].get(key, '?')
    v2 = RESULTS['qwen2.5-coder:14b'].get(key, '?')
    
    # Formatear booleanos
    if isinstance(v1, bool):
        v1_str = "✅" if v1 else "❌"
        v2_str = "✅" if v2 else "❌"
    else:
        v1_str = f"{v1}{suffix}"
        v2_str = f"{v2}{suffix}"
    
    # Marcar el ganador
    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
        if reverse:  # menor es mejor (tiempo)
            winner = "←" if v1 < v2 else ("→" if v2 < v1 else "=")
        else:  # mayor es mejor
            winner = "←" if v1 > v2 else ("→" if v2 > v1 else "=")
        if key == 'duration_sec':
            # Para duración, menor es mejor pero solo marginalmente
            winner = "←" if v1 < v2 else ("→" if v2 < v1 else "=")
    else:
        winner = ""
    
    print(f"  {label:<30} {v1_str:<18} {v2_str:<18}  {winner}")

# Análisis cualitativo
print(f"\n\n  🔍 ANALISIS CUALITATIVO")
print(f"  {'='*60}")

# Leer outputs completos para análisis
for model in MODELS:
    fname = RESULTS[model]['file']
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si el código es sintácticamente válido
    import ast
    # Extraer código Python del output (entre ```python y ```)
    code_blocks = []
    in_block = False
    current_block = []
    for line in content.split('\n'):
        if line.strip().startswith('```python') or line.strip() == '```python':
            in_block = True
            current_block = []
        elif line.strip() == '```' and in_block:
            in_block = False
            code_blocks.append('\n'.join(current_block))
        elif in_block:
            current_block.append(line)
    
    syntax_ok = False
    if code_blocks:
        try:
            ast.parse(code_blocks[0])
            syntax_ok = True
        except SyntaxError as e:
            syntax_ok = f"ERROR: {e}"
    
    print(f"\n  🧠 {model}:")
    print(f"    Sintaxis del codigo: {'✅ Valida' if syntax_ok is True else f'❌ {syntax_ok}'}")
    
    # Contar imports
    imports = [l for l in content.split('\n') if l.strip().startswith('import ') or l.strip().startswith('from ')]
    print(f"    Imports: {len(imports)} ({', '.join(i.split()[1] for i in imports[:6])})")
    
    # Contar clases y funciones
    classes = [l for l in content.split('\n') if l.strip().startswith('class ')]
    funcs = [l for l in content.split('\n') if l.strip().startswith('def ')]
    print(f"    Clases: {len(classes)}, Funciones: {len(funcs)}")
    
    # Docstrings
    docstring_count = content.count('"""') // 2
    print(f"    Docstrings: ~{docstring_count}")

print(f"\n\n  {'='*60}")
print(f"  ✅ COMPARACION COMPLETA")
print(f"  {'='*60}")
print()

# Guardar JSON con resultados
with open('model_comparison_results.json', 'w', encoding='utf-8') as f:
    json.dump(RESULTS, f, indent=2, ensure_ascii=False)
print("Resultados guardados en model_comparison_results.json")
