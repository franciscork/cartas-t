# Claude Code + Ollama — Integración local

Usa [Claude Code](https://www.anthropic.com/claude-code) (la CLI oficial de Anthropic) con [Ollama](https://ollama.com) ejecutando modelos Claude localmente. **Sin API key, sin costos, 100% privado.**

---

## ⚡ Quick Start (3 comandos)

```powershell
# 1. Instalar Ollama + descargar modelo Claude (una sola vez)
winget install Ollama.Ollama
ollama pull claude-sonnet-4-20250514

# 2. Instalar Claude Code CLI (una sola vez)
npm install -g @anthropic-ai/claude-code

# 3. Persistir env vars en tu profile + arrancar Claude Code
.\install-claude-ollama-env.ps1
.\launch_claude_ollama.ps1
```

¡Listo! `claude` arrancará apuntando a Ollama local en `http://localhost:11434`.

---

## 📋 Requisitos

| Componente | Mínimo | Verificar |
|---|---|---|
| **Ollama** | 0.14.0+ (soporte nativo de `/v1/messages` con formato Anthropic, enero 2026) | `curl http://localhost:11434/api/version` |
| **Claude Code CLI** | Última (`@anthropic-ai/claude-code`) | `claude --version` |
| **PowerShell** | 7.0+ (los scripts avisan si estás en Windows PowerShell 5) | `$PSVersionTable.PSVersion` |
| **Node.js** | 18+ (para `npm install`) | `node --version` |
| **RAM** | 8 GB mínimo, 16 GB recomendado para 14B+ | — |

---

## 🛠️ Los 3 scripts

| Script | Propósito | Parámetros |
|---|---|---|
| **`launch_ollama.ps1`** | Arrancar/detener/status del servicio Ollama en WSL2 + auto-exporta env vars | `-Action [start\|stop\|status\|restart]` (default: `start`)<br>`-Persistent` → persiste env vars en `HKCU\Environment` |
| **`launch_claude_ollama.ps1`** | Wrapper one-command: verifica Ollama → exporta env vars → invoca `claude` | `-OllamaPort` (default `11434`)<br>`-NoVerify` → skip el check de Ollama |
| **`install-claude-ollama-env.ps1`** | Persiste las 3 env vars en `$PROFILE` (idempotente) | `-Unattended`<br>`-Uninstall` → borra el bloque del profile<br>`-ListProfiles` → muestra paths |

**Bonus para WSL/Linux:** `launch_claude_ollama.sh` (misma lógica de 3 pasos con `set -euo pipefail`).

Documentación detallada en [CLAUDE-CODE-OLLAMA.md](./CLAUDE-CODE-OLLAMA.md).

---

## 🔑 Las 3 env vars (cómo funcionan)

| Variable | Valor | Propósito |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `http://localhost:11434` | Redirige la API de Anthropic a Ollama local |
| `ANTHROPIC_AUTH_TOKEN` | `ollama` | Token falso (Ollama no valida) |
| `ANTHROPIC_API_KEY` | `""` (vacío) | Indica al SDK usar endpoint custom |

Ollama 0.14.0+ expone `/v1/messages` drop-in compatible con Anthropic Messages API (mismo JSON, headers, `tool_use`, streaming).

---

## 🔄 Flujo end-to-end

```
┌──────────────────────────────────────────────────────────────────┐
│  Terminal pwsh 7                                                 │
│   $ .\launch_claude_ollama.ps1                                   │
│           │                                                      │
│           ├─ 1/3 Verificar Ollama en :11434                      │
│           │      curl GET /api/version  →  {"version":"0.30.7"}  │
│           │                                                      │
│           ├─ 2/3 Exportar env vars                               │
│           │      $env:ANTHROPIC_BASE_URL   = "http://localhost:" │
│           │      $env:ANTHROPIC_AUTH_TOKEN = "ollama"            │
│           │      $env:ANTHROPIC_API_KEY    = ""                 │
│           │                                                      │
│           └─ 3/3 Invocar claude                                  │
└──────────────────┼───────────────────────────────────────────────┘
                   │ POST /v1/messages
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  claude CLI (Node.js)                                            │
│  SDK Anthropic lee $env:ANTHROPIC_BASE_URL → apunta a localhost │
└──────────────────┼───────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  Ollama (http://localhost:11434)                                 │
│  /v1/messages con formato Anthropic                              │
│   - Recibe request, parsea Anthropic format                      │
│   - Ejecuta inferencia con el modelo descargado                  │
│   - Devuelve content[] con text y tool_use blocks                │
└──────────────────┼───────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  claude CLI procesa tool_use                                     │
│   - Si stop_reason == "tool_use":                                │
│       Ejecuta localmente el Bash / Read / Write / Edit           │
│       Envía tool_result de vuelta a Ollama                       │
│       Repite hasta stop_reason == "end_turn"                     │
│   - Si stop_reason == "end_turn":                                │
│       Imprime la respuesta al usuario                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛟 Troubleshooting

### ❌ Puerto 11434 ocupado / Ollama no responde

```powershell
# Verificar si Ollama está corriendo
curl http://localhost:11434/api/version

# Si no responde, arrancarlo
.\launch_ollama.ps1 start

# Si sigue sin responder, ver conflictos de puerto
netstat -ano | findstr :11434
taskkill /PID <pid> /F
```

**Causa típica:** múltiples WSL distros o instancias de Ollama en conflicto.

---

### ❌ "model not found"

```powershell
# Ver qué modelos tienes descargados
curl http://localhost:11434/api/tags

# Descargar el correcto (case-sensitive, el tag importa)
ollama pull claude-sonnet-4-20250514
```

**Causa típica:** pediste `qwen2.5-coder:7b` (no descargado) en vez de `qwen2.5-coder:14b` (sí descargado).

---

### ❌ Perfil en host incorrecto (PS 5 vs pwsh 7)

Cada host tiene su propio `$PROFILE`:

| Host | Path del profile |
|---|---|
| **Windows PowerShell 5** (`powershell.exe`) | `C:\Users\<user>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` |
| **PowerShell 7** (`pwsh.exe`) | `C:\Users\<user>\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` |

**Solución:**

```powershell
# 1. Ver en qué host estás
$PSVersionTable.PSVersion

# 2. Si es 5.x, abrir PowerShell 7
pwsh

# 3. Re-ejecutar el installer
.\install-claude-ollama-env.ps1

# 4. Verificar
$env:ANTHROPIC_BASE_URL  # debe decir http://localhost:11434
```

---

## 📚 Documentación adicional

- **[CLAUDE-CODE-OLLAMA.md](./CLAUDE-CODE-OLLAMA.md)** — Documentación completa (Quick Start extendido, diagrama ASCII detallado, todas las env vars explicadas, 5 problemas de troubleshooting, referencias)
- **[RELEASE_NOTES.md](./RELEASE_NOTES.md)** — Notas del release `v1.0.0-ollama-integration`

---

## 🏷️ Versión

**v1.0.0-ollama-integration** — Test E2E confirmado con Ollama 0.30.7 + claude-sonnet-4-20250514 vía API Anthropic. `tool_use` y `tool_result` feedback loop funcionan correctamente.
