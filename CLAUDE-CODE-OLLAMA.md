# Claude Code + Ollama — Integración local

Usa [Claude Code](https://www.anthropic.com/claude-code) (la CLI de Anthropic) como frontend, con [Ollama](https://ollama.com) ejecutando modelos Claude localmente. **Sin API key, sin costos de Anthropic, 100% privado.**

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
| **Ollama** | 0.14.0+ (soporte nativo de `/v1/messages` con formato Anthropic, enero 2026) | `ollama --version` o `curl http://localhost:11434/api/version` |
| **Claude Code CLI** | Última (`@anthropic-ai/claude-code`) | `claude --version` o `where claude` |
| **PowerShell** | 7.0+ (los scripts avisan si estás en Windows PowerShell 5) | `$PSVersionTable.PSVersion` |
| **Node.js** | 18+ (para `npm install`) | `node --version` |
| **RAM** | 8 GB mínimo (16 GB recomendado para modelos 14B+) | — |

**Modelos recomendados para Claude Code:**
- `claude-sonnet-4-20250514` — **mejor relación calidad/recursos** (~7 GB)
- `claude-opus-4-8` — máxima calidad (~7 GB, más lento)
- `qwen2.5-coder:14b` — alternativa open-source para código (~8.5 GB)

---

## 🔑 Las 3 env vars (explicadas)

Claude Code busca la API de Anthropic en un endpoint configurable. Para redirigirlo a Ollama local, necesitas:

| Variable | Valor | Propósito |
|---|---|---|
| **`ANTHROPIC_BASE_URL`** | `http://localhost:11434` | Le dice a Claude Code dónde está la API. En vez de `https://api.anthropic.com`, apunta a tu Ollama local. |
| **`ANTHROPIC_AUTH_TOKEN`** | `ollama` | Token falso. Ollama no valida el token, pero Claude Code/SDK lo requiere para arrancar. |
| **`ANTHROPIC_API_KEY`** | `""` (vacío) | Lo mismo, vacio. Indica a Claude Code que use la API key vacía con el endpoint custom. |

**¿Por qué funciona?** Ollama 0.14.0+ expone un endpoint `/v1/messages` que es **drop-in compatible** con la API de Anthropic Messages (mismo formato JSON, mismos headers, mismo `tool_use`, mismo streaming). El SDK de Anthropic (que usa Claude Code internamente) se conecta felizmente cuando `ANTHROPIC_BASE_URL` apunta a localhost.

---

## 🛠️ Los 3 scripts (tabla de parámetros)

| Script | Propósito | Parámetros | Notas |
|---|---|---|---|
| **`launch_ollama.ps1`** | Arrancar/detener/status del servicio Ollama en WSL2 + auto-exporta env vars | `-Action [start\|stop\|status\|restart]` (default: `start`)<br>`-Persistent` → persiste env vars en `HKCU\Environment`<br>`-OllamaPort` → default `11434` | Reusa `wsl -d Ubuntu` internamente. Si Ollama ya corre, lo detecta y no re-arranca. |
| **`launch_claude_ollama.ps1`** | Wrapper one-command: verifica Ollama → exporta env vars → invoca `claude` desde el directorio actual | `-OllamaPort` → default `11434`<br>`-NoVerify` → skip el check de Ollama (asume que corre) | Pre-flight de `claude` CLI al inicio (fail-fast). `claude @args` propaga tus flags. |
| **`install-claude-ollama-env.ps1`** | Persiste las 3 env vars en `$PROFILE.CurrentUserAllHosts` | `-Unattended` → no pide confirmación<br>`-OllamaPort` → default `11434`<br>`-Uninstall` → borra el bloque del profile<br>`-ListProfiles` → muestra paths (debugging) | Idempotente (marker `# >>> claude-ollama-env <<<`). Sintaxis validada con `PSParser::Tokenize`. UTF-8 sin BOM. |

---

## 🏗️ Arquitectura (DRY: single source of truth)

Los 3 scripts `.ps1` comparten **un único módulo** (`claude-env.ps1`) que contiene toda la lógica de las env vars + el bloque de profile. Esto evita duplicación y garantiza consistencia entre los 3 puntos de entrada.

### Grafo de dependencias

```
                     ┌──────────────────────────────┐
                     │  install-claude-ollama-env.ps1│
                     │   (persiste en $PROFILE)      │
                     └──────────────┬───────────────┘
                                    │ dot-source
                                    │
 ┌────────────────────┐  dot-source │    ┌────────────────────┐
 │  launch_ollama.ps1 │◄─────────────┴───►│ launch_claude_     │
 │  (start/stop WSL2) │                  │   ollama.ps1       │
 └─────────┬──────────┘                  └──────────┬──────────┘
           │ dot-source                            │ dot-source
           │                                       │
           └─────────────────┬─────────────────────┘
                             ▼
                ┌─────────────────────────┐
                │     claude-env.ps1      │
                │  ────────────────────   │
                │  • Set-ClaudeEnv        │  ← única fuente
                │    -Port -Persistent    │    de verdad para
                │    -Quiet               │    los 3 env vars
                │  • Get-ClaudeEnvBlock   │  ← bloque para
                │    -Port                │    $PROFILE
                │  • $ClaudeEnvMarker*    │  ← deteccion
                │    (Start/End)          │    idempotente
                └─────────────────────────┘
                             ▲
                             │ (referenciado por)
                ┌────────────┴────────────┐
                │   launch_claude_ollama  │
                │       .sh  (WSL/Linux)  │   ← bash nativo,
                │   sin dot-source        │     `source` en su lugar
                └─────────────────────────┘
```

**Lectura del grafo:**

- Las **flechas hacia abajo** (`dot-source`) significan “carga este módulo para usar sus funciones”.
- Los 3 scripts `.ps1` consumen las mismas funciones (`Set-ClaudeEnv`, `Get-ClaudeEnvBlock`) — **ninguno redefine la lógica localmente**.
- La versión bash (`.sh`) sigue la misma filosofía pero con primitivas nativas: `export` + `exec` en vez de dot-source.

### ¿Por qué existe `claude-env.ps1`?

| Razón | Antes del refactor | Después del refactor |
|---|---|---|
| **Single source of truth** | Los 3 env vars estaban hard-coded en `launch_ollama.ps1`, inline en `launch_claude_ollama.ps1`, y repetidos en el here-string de `install-claude-ollama-env.ps1`. Cualquier cambio requería editar 3 archivos. | Las 3 env vars viven **solo en `Set-ClaudeEnv`**. Los 3 scripts delegan via dot-source. |
| **Cambios futuros en un solo lugar** | Si Anthropic agrega `ANTHROPIC_DEFAULT_SONNET_MODEL`, había que editar 3 scripts + reescribir el here-string del profile. | Edits `claude-env.ps1` UNA vez; los 3 scripts + el bloque de `$PROFILE` heredan el cambio automáticamente. |
| **Deteccion idempotente consistente** | Los markers `# >>> claude-ollama-env <<<` estaban hard-coded en install. Si cambiaban, install no detectaba bloques viejos. | Los markers son `$script:ClaudeEnvMarkerStart/End` exportados por el módulo. Install los consume; cambiar el formato en un solo lugar los actualiza en todos lados. |
| **Testing** | Imposible testear la lógica de env vars aislada (estaba mezclada con la lógica de arrancar ollama / escribir profile). | `Set-ClaudeEnv` + `Get-ClaudeEnvBlock` se pueden testear con Pester sin tocar el resto. |

### ¿Qué vive dentro de `claude-env.ps1`?

| Símbolo | Tipo | Propósito |
|---|---|---|
| `Set-ClaudeEnv` | `function` | Setea las 3 env vars en la sesión actual. Params: `-Port` (default 11434), `-Persistent` (switch → escribe a `HKCU\Environment`), `-Quiet` (switch → suprime output). |
| `Get-ClaudeEnvBlock` | `function` | Devuelve el bloque de texto (string multi-línea) a persistir en `$PROFILE`. Param: `-Port`. Usa literal here-string + 3 `.Replace()` para inyectar el puerto. |
| `$script:ClaudeEnvMarkerStart` | constant | `# >>> claude-ollama-env (do not edit this line) <<<` — usado por `install-claude-ollama-env.ps1` para detectar el bloque existente. |
| `$script:ClaudeEnvMarkerEnd` | constant | `# <<< claude-ollama-env` — cierre del bloque. |

### ¿Qué NO vive en `claude-env.ps1`?

- **Lógica de arrancar Ollama** (`wsl -d Ubuntu -- ollama serve`, deteccion de ya-corriendo, listado de modelos) → vive en `launch_ollama.ps1`.
- **Lógica de invocar `claude`** (pre-flight check, `& claude @args`) → vive en `launch_claude_ollama.ps1`.
- **Lógica de escribir a `$PROFILE`** (crear directorio si no existe, merge idempotente in-place, UTF-8 sin BOM, validación de sintaxis con `PSParser::Tokenize`, `-Uninstall`) → vive en `install-claude-ollama-env.ps1`.
- **Lógica de WSL2** (`wsl -d Ubuntu ...`) → específica de `launch_ollama.ps1`.

El módulo **no se carga solo**; siempre es dot-sourceado por alguno de los 3 scripts. Esto evita side-effects al importarlo interactivamente.

---

## 🔄 Flujo end-to-end (diagrama ASCII)

```
┌──────────────────────────────────────────────────────────────────┐
│  Terminal pwsh 7                                                 │
│                                                                  │
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
│                  │                                               │
└──────────────────┼───────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  claude CLI (Node.js)                                            │
│  SDK Anthropic lee $env:ANTHROPIC_BASE_URL → apunta a localhost │
│                                                                  │
│   POST http://localhost:11434/v1/messages                        │
│   Headers:                                                       │
│     Content-Type: application/json                               │
│     anthropic-version: 2023-06-01                                │
│     x-api-key: ollama                                            │
│   Body: {                                                        │
│     "model": "claude-sonnet-4-20250514",                         │
│     "messages": [...],                                           │
│     "tools": [{"name": "Bash", ...}, ...]                        │
│   }                                                              │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  Ollama (http://localhost:11434)                                 │
│  v0.14.0+ expone /v1/messages con formato Anthropic              │
│                                                                  │
│   1. Recibe request, parsea Anthropic format                     │
│   2. Traduce a formato nativo del modelo (llama.cpp)             │
│   3. Ejecuta inferencia con el modelo descargado                 │
│   4. Traduce respuesta a Anthropic format:                      │
│      {                                                           │
│        "content": [                                              │
│          {"type": "text", "text": "..."},                        │
│          {"type": "tool_use", "name": "Bash", "input": {...}}    │
│        ],                                                        │
│        "stop_reason": "tool_use"                                 │
│      }                                                           │
│   5. Devuelve al claude CLI                                      │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  claude CLI procesa tool_use                                     │
│                                                                  │
│   - Si stop_reason == "tool_use":                                │
│       Ejecuta localmente el Bash / Read / Write / Edit           │
│       Envía tool_result de vuelta a Ollama                       │
│       Repite hasta stop_reason == "end_turn"                     │
│   - Si stop_reason == "end_turn":                                │
│       Imprime la respuesta al usuario                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛟 Troubleshooting común

### ❌ "puerto 11434 ocupado" / Ollama no responde

```powershell
# 1. Verificar si Ollama está corriendo
curl http://localhost:11434/api/version

# Si no responde, arrancarlo:
.\launch_ollama.ps1 start

# Si sigue sin responder, ver si hay otro proceso usando el puerto:
netstat -ano | findstr :11434
# Matar el PID conflictivo:
taskkill /PID <pid> /F
```

**Causa típica:** Ollama corre dentro de WSL (`wsl -d Ubuntu -- ollama serve`) y Windows lo expone en `localhost:11434` automáticamente. Si tienes múltiples WSL distros o instancias de Ollama, pueden colisionar.

---

### ❌ "model not found" al hacer una petición

```powershell
# Ver qué modelos tienes descargados
curl http://localhost:11434/api/tags

# Descargar el que necesitas
ollama pull claude-sonnet-4-20250514

# Si el error persiste, especificar el modelo completo (con tag)
# Algunos modelos requieren: claude-sonnet-4-20250514:latest
```

**Causa típica:** Pediste `qwen2.5-coder:7b` (no descargado) en vez de `qwen2.5-coder:14b` (sí descargado). Los nombres son case-sensitive y el tag (`:latest`, `:7b`, `:14b`) importa.

---

### ❌ "Las env vars están, pero claude no arranca / se conecta a api.anthropic.com"

Probable causa: **estás en Windows PowerShell 5.x**, no PowerShell 7. Cada host tiene su propio `$PROFILE`:

| Host | Path del profile |
|---|---|
| **Windows PowerShell 5** (`powershell.exe`) | `C:\Users\<user>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` |
| **PowerShell 7** (`pwsh.exe`) | `C:\Users\<user>\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` |

**Solución:**

```powershell
# 1. Ver en qué host estás
$PSVersionTable.PSVersion

# 2. Si es 5.x, abrir PowerShell 7 explicitamente
pwsh

# 3. Re-ejecutar el installer (estará en el path correcto)
.\install-claude-ollama-env.ps1

# 4. Verificar
$env:ANTHROPIC_BASE_URL  # debe decir http://localhost:11434
```

---

### ❌ "Permission denied" al escribir en `$PROFILE`

```powershell
# Verificar permisos
Test-Path $PROFILE.CurrentUserAllHosts
Get-Acl $PROFILE.CurrentUserAllHosts | Select-Object Owner, AccessToString

# Si el profile está bloqueado, usar la ruta alternativa
notepad $PROFILE.CurrentUserAllHosts
# Agregar manualmente:
#   $env:ANTHROPIC_BASE_URL    = "http://localhost:11434"
#   $env:ANTHROPIC_AUTH_TOKEN  = "ollama"
#   $env:ANTHROPIC_API_KEY     = ""
```

---

### ❌ "tool_use no funciona / claude no ejecuta comandos"

```powershell
# 1. Verificar que el modelo soporta tools
# (claude-sonnet-4-20250514, claude-opus-4-8 sí; qwen2.5-coder también)
curl -s http://localhost:11434/api/tags

# 2. Test directo de tool_use
curl -X POST http://localhost:11434/v1/messages \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: ollama" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":200,"tools":[{"name":"Bash","description":"Run shell","input_schema":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}],"messages":[{"role":"user","content":"ejecuta ls"}]}'

# 3. Si la respuesta tiene "content":null, "stop_reason":"end_turn" con tokens > 0,
#    puede ser un quirk de Ollama 0.30.x. Upgrade a la última versión:
ollama --version
# Actualizar desde https://ollama.com/download
```

---

### ❌ "Quiero desinstalar todo"

```powershell
# 1. Quitar env vars del profile
.\install-claude-ollama-env.ps1 -Uninstall

# 2. (Opcional) Detener Ollama
.\launch_ollama.ps1 stop

# 3. (Opcional) Desinstalar Ollama completamente
winget uninstall Ollama.Ollama

# 4. (Opcional) Desinstalar Claude Code
npm uninstall -g @anthropic-ai/claude-code
```

---

## 📚 Referencias

- [Ollama — Claude Code compatibility (blog)](https://ollama.com/blog/claude) (enero 2026)
- [Ollama — Anthropic compatibility docs](https://docs.ollama.com/api/anthropic-compatibility)
- [Claude Code — Install & setup](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Anthropic Messages API reference](https://docs.anthropic.com/en/api/messages)

---

## 📝 Versión

**v1.0.0-ollama-integration** (tag git) — Integración inicial verificada con Ollama 0.30.7 + claude-sonnet-4-20250514. Test E2E confirmado: `/v1/messages` responde, `tool_use` content block se emite correctamente, `tool_result` feedback loop funciona.
