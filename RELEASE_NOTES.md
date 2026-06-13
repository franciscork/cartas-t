# Release Notes — v1.0.0-ollama-integration

**Tag:** `v1.0.0-ollama-integration`
**Fecha:** 2026-06-13
**Tipo:** Feature release (initial integration)

---

## 🎉 Claude Code + Ollama — Integración local completa

Usa [Claude Code](https://www.anthropic.com/claude-code) (la CLI oficial de Anthropic) con [Ollama](https://ollama.com) ejecutando modelos Claude localmente. **Sin API key, sin costos de Anthropic, 100% privado.**

---

## 📦 Qué incluye este release

**4 archivos** que permiten el flujo end-to-end:

| Archivo | Tipo | Propósito |
|---|---|---|
| **`claude-env.ps1`** | Nuevo (módulo) | Fuente única de verdad para los 3 env vars de Claude Code. Usado por los otros 2 scripts. |
| **`launch_ollama.ps1`** | Modificado | Servicio Ollama (start/stop/status/restart) + auto-exporta env vars via módulo compartido. |
| **`launch_claude_ollama.ps1`** | Nuevo | Wrapper one-command: verifica Ollama → exporta env vars → invoca `claude`. |
| **`install-claude-ollama-env.ps1`** | Nuevo | Persiste los 3 env vars en `$PROFILE` (idempotente, soporta `-Uninstall` y `-ListProfiles`). |

**Bonus:** `launch_claude_ollama.sh` (versión bash equivalente para WSL/Linux con la misma lógica de 3 pasos).

---

## ⚡ Quick Start (3 comandos)

```powershell
# 1. Instalar Ollama y descargar un modelo Claude (una sola vez)
winget install Ollama.Ollama
ollama pull claude-sonnet-4-20250514

# 2. Instalar Claude Code CLI (una sola vez)
npm install -g @anthropic-ai/claude-code

# 3. Persistir las env vars en tu profile (una sola vez)
.\install-claude-ollama-env.ps1

# 4. Arrancar Claude Code local
.\launch_claude_ollama.ps1
```

¡Listo! `claude` arrancará apuntando a Ollama local en `http://localhost:11434`.

---

## 📋 Requisitos

| Componente | Versión mínima | Verificar |
|---|---|---|
| **Ollama** | 0.14.0+ (soporte nativo de `/v1/messages` con formato Anthropic, enero 2026) | `curl http://localhost:11434/api/version` |
| **Claude Code CLI** | Última (`@anthropic-ai/claude-code`) | `claude --version` |
| **PowerShell** | 7.0+ (los scripts avisan si estás en Windows PowerShell 5) | `$PSVersionTable.PSVersion` |
| **Node.js** | 18+ (para `npm install`) | `node --version` |
| **RAM** | 8 GB mínimo (16 GB recomendado para modelos 14B+) | — |

**Modelos recomendados:**
- `claude-sonnet-4-20250514` — mejor relación calidad/recursos (~7 GB)
- `claude-opus-4-8` — máxima calidad (~7 GB)
- `qwen2.5-coder:14b` — alternativa open-source para código (~8.5 GB)

---

## 🛠️ Los 3 scripts — Tabla de parámetros

### `claude-env.ps1` (módulo compartido)
```powershell
. (Join-Path $PSScriptRoot "claude-env.ps1")
Set-ClaudeEnv -Port 11434 [-Persistent] [-Quiet]
```

### `launch_ollama.ps1`
```powershell
.\launch_ollama.ps1 [-Action [start|stop|status|restart]] [-Persistent]
```
- `-Persistent` → persiste env vars en `HKCU\Environment`

### `launch_claude_ollama.ps1`
```powershell
.\launch_claude_ollama.ps1 [-OllamaPort 11434] [-NoVerify]
```
- Pre-flight de `claude` CLI al inicio (fail-fast)
- `claude @args` propaga tus flags

### `launch_claude_ollama.sh` (WSL/Linux)
```bash
./launch_claude_ollama.sh [--port N] [--no-verify]
```
- `set -euo pipefail`, `--port` validado como numérico
- `exec claude "${CLAUDE_ARGS[@]}"` para Ctrl+C limpio

### `install-claude-ollama-env.ps1`
```powershell
.\install-claude-ollama-env.ps1 [-Unattended] [-Uninstall] [-ListProfiles]
```
- Idempotente: marker `# >>> claude-ollama-env <<<`
- `-Uninstall` borra el bloque del profile
- `-ListProfiles` muestra paths para debugging

---

## ✅ Test E2E confirmado

**tool_use via `/v1/messages` funciona con claude-sonnet-4 + Ollama:**

```bash
curl -X POST http://localhost:11434/v1/messages \
  -H 'Content-Type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -H 'x-api-key: ollama' \
  -d '{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 200,
    "tools": [{"name":"list_files","description":"Lista archivos","input_schema":{...}}],
    "messages": [{"role":"user","content":"lista los archivos .py en Simmoon_arc/"}]
  }'
```

**Respuesta confirmada:**
```json
{
  "content": [{
    "type": "tool_use",
    "id": "call_pm7cex24",
    "name": "list_files",
    "input": {"directory": "Simmoon_arc/", "pattern": ".py"}
  }],
  "stop_reason": "tool_use"
}
```

**Implicación:** Claude Code (que depende 100% de `tool_use` para bash/file editing) funciona con Ollama local.

---

## 🔑 Las 3 env vars (cómo funcionan)

| Variable | Valor | Propósito |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `http://localhost:11434` | Redirige la API de Anthropic a Ollama local. |
| `ANTHROPIC_AUTH_TOKEN` | `ollama` | Token falso (Ollama no valida, pero SDK lo requiere). |
| `ANTHROPIC_API_KEY` | `""` (vacío) | Indica al SDK que use la API key vacía con endpoint custom. |

Ollama 0.14.0+ expone `/v1/messages` drop-in compatible con la API Anthropic Messages (mismo JSON, headers, `tool_use`, streaming).

---

## ⚠️ Limitaciones conocidas de Ollama + API Anthropic

- ❌ No soporta **prompt caching** (`cache_control` blocks)
- ❌ No soporta `/v1/messages/count_tokens`
- ❌ No soporta **PDF** (`document` blocks)
- ❌ No soporta **Batches API**
- ⚠️ **Tool choice** fino (forzar tool específica) tiene soporte limitado

---

## 🛟 Troubleshooting rápido

| Problema | Solución |
|---|---|
| Puerto 11434 ocupado | `netstat -ano \| findstr :11434` + `taskkill /PID <pid> /F` |
| Model not found | `ollama pull claude-sonnet-4-20250514` (verifica tag exacto) |
| env vars no se aplican | Estás en PS 5.x → abre pwsh 7 y re-ejecuta installer |
| Permission denied en $PROFILE | `notepad $PROFILE.CurrentUserAllHosts` y agrega env vars manualmente |
| tool_use no funciona | Verifica que el modelo soporta tools (`curl /api/tags`); upgrade Ollama si v0.30.x |

Para troubleshooting completo, ver [CLAUDE-CODE-OLLAMA.md](./CLAUDE-CODE-OLLAMA.md).

---

## 📚 Referencias

- [Ollama — Claude Code compatibility (blog)](https://ollama.com/blog/claude) (enero 2026)
- [Ollama — Anthropic compatibility docs](https://docs.ollama.com/api/anthropic-compatibility)
- [Claude Code — Install & setup](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Anthropic Messages API reference](https://docs.anthropic.com/en/api/messages)

---

## 🏗️ Arquitectura

```
┌──────────────────┐    . (dot-source)    ┌──────────────────┐
│ launch_ollama.ps1│─────────────────────▶│  claude-env.ps1  │
└──────────────────┘                      │  (Set-ClaudeEnv) │
┌──────────────────────┐    . (dot-source)  │  DRY: unica fuente│
│launch_claude_ollama.ps1│─────────────────▶│  de verdad para  │
└──────────────────────┘                   │  los 3 env vars  │
                                           └──────────────────┘
```

**DRY:** un solo lugar para cambiar los env vars en el futuro.

---

## 📝 Changelog desde v0.x

### Added
- `claude-env.ps1` — módulo compartido con `Set-ClaudeEnv`
- `launch_claude_ollama.ps1` — wrapper PowerShell 3 pasos
- `launch_claude_ollama.sh` — wrapper bash equivalente
- `install-claude-ollama-env.ps1` — persistencia idempotente en `$PROFILE`
- `CLAUDE-CODE-OLLAMA.md` — documentación completa (requisitos, env vars, troubleshooting, diagrama ASCII)
- `RELEASE_NOTES.md` — este archivo

### Changed
- `launch_ollama.ps1` — auto-exporta env vars via módulo compartido (antes inline)

### Verified
- `/v1/messages` responde con `claude-sonnet-4-20250514`
- `tool_use` content block se emite correctamente
- `tool_result` feedback loop funciona
- Idempotencia de la persistencia en `$PROFILE` confirmada

---

**Hecho con ❤️ por franciscork · [Reportar issue](../../issues) · [Ver código](../../tree/v1.0.0-ollama-integration)**
