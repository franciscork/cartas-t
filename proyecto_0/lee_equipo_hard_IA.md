
---

## 🔧 Fixes Aplicados — 2026-06-06

### 1. context_length obligatorio
Hermes Agent requiere mínimo 64K contexto. Ollama reporta el contexto nativo del modelo (ej: qwen2.5-coder = 32K). Fix en config.yaml:

```yaml
model:
  context_length: 65536
```

### 2. PATH .bashrc — 3 líneas export PATH
El .bashrc tiene 3 líneas `export PATH=` (129, 148, 210). La línea 210 sobreescribe las anteriores. Fix: añadido `/usr/local/bin` al inicio de línea 210.

**Pendiente:** Línea 210 usa rutas Git Bash (`/c/...`) en vez de WSL (`/mnt/c/...`). Necesita limpieza.

### 3. Aliases rotos
Aliases de simmoon, crewai, launch_all, a1111, simmoon-gen, simmoon-update tenían quotes escaped incorrectas. Corregidos con Python script.

### 4. Ollama models listo
4 modelos con 64K contexto: gemma3-tools-64k, qwen3-14b-64k, qwen25-coder-14b-64k, nomic-embed-text.

---

*Última actualización: 2026-06-06*

---

## 🛠️ Troubleshooting — Problemas Conocidos

### 1. Hermes no responde o va muy lento
**Causa:** Runner de Ollama atascado tras timeouts repetidos.
**Fix:**
```bash
pkill -9 ollama
sleep 3
ollama serve &
```

### 2. context_length below minimum 64,000
**Causa:** Modelos de 12-14B reportan 32K contexto nativo, Hermes requiere 64K mínimo.
**Fix:** En config.yaml, añadir:
```yaml
model:
  context_length: 65536
```

### 3. GPU utilization 0% durante inferencia
**Causa:** Modelo cargado en VRAM pero inferencia en CPU.
**Fix:** Matar procesos atascados y reiniciar Ollama limpio.

### 4. ollama command not found (/usr/local/bin not in PATH)
**Causa:** Línea 210 del .bashrc sobreescribe PATH sin /usr/local/bin.
**Fix:** Añadir /usr/local/bin al inicio de la línea 210 del .bashrc.

---

## 📊 Velocidad Real — Tokens/segundo

| Modelo | Velocidad | Notas |
|--------|-----------|-------|
| gemma3-tools:12b-ft | ~13-20 tok/s | Rápido, recomendado para uso diario |
| qwen3:14b | ~8-10 tok/s | Más lento por tamaño |
| qwen2.5-coder:14b | ~8-10 tok/s | Coding especializado |

---
*Última actualización: 2026-06-06 — Fixes de context_length y troubleshooting*

---

## Troubleshooting

### Hermes no responde
Causa: Runner de Ollama atascado.
Fix: pkill -9 ollama && ollama serve &

### context_length below minimum 64000
Causa: Modelos reportan 32K, Hermes requiere 64K.
Fix: context_length: 65536 en config.yaml

### GPU utilization 0%
Causa: Runner atascado tras timeouts.
Fix: Matar procesos y reiniciar Ollama.

### ollama command not found
Causa: /usr/local/bin no en PATH (linea 210 .bashrc).
Fix: Añadir /usr/local/bin al inicio de linea 210.

---

## Velocidad Real

- gemma3-tools:12b-ft: ~13-20 tok/s
- qwen3:14b: ~8-10 tok/s
- qwen2.5-coder:14b: ~8-10 tok/s

---
Actualizado: 2026-06-06

---

## Troubleshooting

### Hermes no responde
Causa: Runner de Ollama atascado.
Fix: pkill -9 ollama && ollama serve &

### context_length below minimum 64000
Causa: Modelos reportan 32K, Hermes requiere 64K.
Fix: context_length: 65536 en config.yaml

### GPU utilization 0%
Causa: Runner atascado tras timeouts.
Fix: Matar procesos y reiniciar Ollama.

### ollama command not found
Causa: /usr/local/bin no en PATH (linea 210 .bashrc).
Fix: Añadir /usr/local/bin al inicio de linea 210.

---

## Velocidad Real

- gemma3-tools:12b-ft: ~13-20 tok/s
- qwen3:14b: ~8-10 tok/s
- qwen2.5-coder:14b: ~8-10 tok/s

---
Actualizado: 2026-06-06

---

## Leccion Clave: num_ctx vs context_length

Problema: Hermes requiere context_length minimo 65536. Con num_ctx 65536 en Modelfile, el modelo reserva 64K KV cache que excede 8GB VRAM, causando timeout >90s.

Solucion:
- Modelfile: num_ctx 32768 (cabe en 8GB VRAM)
- config.yaml: context_length 65536 (Hermes verifica esto, no el runtime de Ollama)

Resultado: Inferencia a 14-20 tok/s sin timeout.

---
Actualizado: 2026-06-06
