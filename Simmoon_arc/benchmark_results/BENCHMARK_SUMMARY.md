# 📊 Benchmark de Modelos Ollama para Código

**Fecha:** 2026-06-10 01:14:56
**Modelos evaluados:** 5
**Tareas:** 5
**Ejecuciones totales:** 25
**Duración total:** 2651.7s (44.2m)

## 🏆 Ranking General (promedio por modelo)

| Rank | Modelo | ⏱ Promedio | ✅ Tareas OK | 📏 Chars | 💻 Sintaxis | 📋 Reqs | 📝 Type Hints |
|------|--------|:----------:|:----------:|:--------:|:----------:|:------:|:-------------:|
| 🥇 | qwen2.5-coder:14b            | 191.1s | 5/5 | 21032 | 4/5 |    94% | 0/5 |
| 🥈 | deepseek-r1:7b               | 109.9s | 5/5 | 33392 | 1/5 |    94% | 0/5 |
| 🥉 | gemma4:latest                | 259.1s | 3/5 | 33324 | 2/5 |    56% | 0/5 |
|   4. | qwen3.5:4b                   | 194.3s | 3/5 | 20025 | 2/5 |    45% | 0/5 |
|   5. | qwen3:14b                    | 262.1s | 2/5 | 11545 | 2/5 |    37% | 0/5 |

*Puntaje compuesto: 30% completitud + 25% sintaxis + 20% requisitos + 15% type hints + 10% output*

## 📋 Matriz Modelo × Tarea

| Modelo | ⏱️  TaskQueue (OOP) | ⏱️  RateLimiter (Algor | ⏱️  CSVProcessor (Dato | ⏱️  LogDecorator (Func | ⏱️  Refactor (Calidad) |
|--------|-----------:|-----------:|-----------:|-----------:|-----------:|
| qwen2.5-coder:14b          | ✅ 204.3s | ✅ 181.0s | ❌ 276.5s | ✅ 176.4s | ✅ 117.2s |
| deepseek-r1:7b             | ❌ 127.7s | ❌ 65.7s | ✅ 67.9s | ❌ 217.5s | ❌ 70.9s |
| gemma4:latest              | ❌ 302.0s | ✅ 233.1s | ❌ 246.5s | ✅ 211.8s | ❌ 302.0s |
| qwen3.5:4b                 | ❌ 242.8s | ❌ 217.1s | ❌ 212.6s | ✅ 218.3s | ✅ 80.8s |
| qwen3:14b                  | ❌ 302.1s | ❌ 302.0s | ✅ 294.3s | ❌ 302.1s | ✅ 110.2s |

## 🔍 Detalle por Tarea

### Tarea 1: TaskQueue (OOP)
*Habilidad: POO, manejo de errores, persistencia*

| Modelo | ⏱️  Tiempo | ✅ Completada | 💻 Sintaxis | 📋 Reqs | 📏 Chars | 📝 Hints | 📋 Docs |
|--------|:--------:|:------------:|:----------:|:------:|:-------:|:-------:|:-------:|
| qwen2.5-coder:14b            | 204.3s | ✅ | ✅ | 11/11 |  4769 | ❌ | ❌ |
| deepseek-r1:7b               | 127.7s | ✅ | ❌ | 11/11 |  7943 | ❌ | ❌ |
| gemma4:latest                | 302.0s | ❌ | ❌ |  0/11 |    17 | ❌ | ❌ |
| qwen3.5:4b                   | 242.8s | ❌ | ❌ |  0/11 |     0 | ❌ | ❌ |
| qwen3:14b                    | 302.1s | ❌ | ❌ |  0/11 |    17 | ❌ | ❌ |

### Tarea 2: RateLimiter (Algoritmo)
*Habilidad: Algoritmos, thread-safety, time*

| Modelo | ⏱️  Tiempo | ✅ Completada | 💻 Sintaxis | 📋 Reqs | 📏 Chars | 📝 Hints | 📋 Docs |
|--------|:--------:|:------------:|:----------:|:------:|:-------:|:-------:|:-------:|
| qwen2.5-coder:14b            | 181.0s | ✅ | ✅ |   9/9 |  3770 | ❌ | ✅ |
| deepseek-r1:7b               |  65.7s | ✅ | ❌ |   9/9 |  8205 | ❌ | ✅ |
| gemma4:latest                | 233.1s | ✅ | ✅ |   9/9 |  9344 | ❌ | ✅ |
| qwen3.5:4b                   | 217.1s | ❌ | ❌ |   0/9 |     0 | ❌ | ❌ |
| qwen3:14b                    | 302.0s | ❌ | ❌ |   0/9 |    17 | ❌ | ❌ |

### Tarea 3: CSVProcessor (Datos)
*Habilidad: Procesamiento datos, archivos, estadistica*

| Modelo | ⏱️  Tiempo | ✅ Completada | 💻 Sintaxis | 📋 Reqs | 📏 Chars | 📝 Hints | 📋 Docs |
|--------|:--------:|:------------:|:----------:|:------:|:-------:|:-------:|:-------:|
| qwen2.5-coder:14b            | 276.5s | ✅ | ❌ | 10/10 |  5557 | ❌ | ❌ |
| deepseek-r1:7b               |  67.9s | ✅ | ✅ | 10/10 |  8134 | ❌ | ✅ |
| gemma4:latest                | 246.5s | ✅ | ❌ |  8/10 | 12693 | ❌ | ✅ |
| qwen3.5:4b                   | 212.6s | ✅ | ❌ |  9/10 |  6770 | ❌ | ✅ |
| qwen3:14b                    | 294.3s | ✅ | ✅ | 10/10 | 10045 | ❌ | ✅ |

### Tarea 4: LogDecorator (Funcional)
*Habilidad: Decoradores, metaprogramacion, logging*

| Modelo | ⏱️  Tiempo | ✅ Completada | 💻 Sintaxis | 📋 Reqs | 📏 Chars | 📝 Hints | 📋 Docs |
|--------|:--------:|:------------:|:----------:|:------:|:-------:|:-------:|:-------:|
| qwen2.5-coder:14b            | 176.4s | ✅ | ✅ |   8/8 |  5255 | ❌ | ❌ |
| deepseek-r1:7b               | 217.5s | ✅ | ❌ |   8/8 |  6558 | ❌ | ✅ |
| gemma4:latest                | 211.8s | ✅ | ✅ |   8/8 | 11253 | ❌ | ✅ |
| qwen3.5:4b                   | 218.3s | ✅ | ✅ |   3/8 | 10829 | ❌ | ✅ |
| qwen3:14b                    | 302.1s | ❌ | ❌ |   0/8 |    17 | ❌ | ❌ |

### Tarea 5: Refactor (Calidad)
*Habilidad: Refactorizacion, codigo legacy, clean code*

| Modelo | ⏱️  Tiempo | ✅ Completada | 💻 Sintaxis | 📋 Reqs | 📏 Chars | 📝 Hints | 📋 Docs |
|--------|:--------:|:------------:|:----------:|:------:|:-------:|:-------:|:-------:|
| qwen2.5-coder:14b            | 117.2s | ✅ | ✅ |   5/7 |  1681 | ❌ | ✅ |
| deepseek-r1:7b               |  70.9s | ✅ | ❌ |   5/7 |  2552 | ❌ | ✅ |
| gemma4:latest                | 302.0s | ❌ | ❌ |   0/7 |    17 | ❌ | ❌ |
| qwen3.5:4b                   |  80.8s | ✅ | ✅ |   7/7 |  2426 | ❌ | ✅ |
| qwen3:14b                    | 110.2s | ✅ | ✅ |   6/7 |  1449 | ❌ | ✅ |

## 💡 Conclusiones

- **Mejor modelo general:** `qwen2.5-coder:14b` (puntaje: 78.9)
- **Mas rapido:** `deepseek-r1:7b` (promedio 109.9s)
- **Menos errores de sintaxis:** `qwen2.5-coder:14b` (4/5 tareas limpias)
- **Mejor tipado:** `qwen2.5-coder:14b` (0/5 con type hints)

---
*Generado por benchmark_models.py el 2026-06-10 01:14:56*