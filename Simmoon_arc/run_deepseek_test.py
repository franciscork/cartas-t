#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from claude_code_bridge import OllamaAnthropicClient

TASK = "Escribe una clase Python llamada TaskQueue. Constructor: max_retries=3, retry_delay=1.0, persist_path=None. Metodos: add_task(name, fn, args, kwargs), run_all() con reintentos y KeyboardInterrupt, run_one(task_id), get_status(task_id), summary() con total/completed/failed/pending/total_time. Persistencia JSON si persist_path. Timestamps por tarea. Type hints, docstrings, logging. Incluye ejemplo. Al final escribe RESUMEN:"

client = OllamaAnthropicClient(model='deepseek-r1:7b', verbose=False)
r = client.run_task(task=TASK, timeout=360)

with open('compare_deepseek_r1_7b.txt', 'w', encoding='utf-8') as f:
    f.write(r.output)

print(f"EXIT:{r.exit_code} DURATION:{r.duration:.1f}s CHARS:{len(r.output)} LINES:{len(r.output.splitlines())} SUCCESS:{r.success}")
print("OUTPUT_SAVED:compare_deepseek_r1_7b.txt")
