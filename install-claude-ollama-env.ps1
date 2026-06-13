<#
.SYNOPSIS
    Persiste (o remueve) las 3 env vars de Claude Code + Ollama en $PROFILE de PowerShell
.DESCRIPTION
    Agrega (o actualiza idempotentemente) un bloque en $PROFILE.CurrentUserAllHosts
    con las env vars necesarias para que `claude` (Claude Code CLI) use Ollama local:

        $env:ANTHROPIC_BASE_URL    = "http://localhost:11434"
        $env:ANTHROPIC_AUTH_TOKEN  = "ollama"
        $env:ANTHROPIC_API_KEY     = ""

    Requisito: Ollama >= 0.14.0 (soporte nativo de /v1/messages formato Anthropic).

    Idempotente: detecta un marker (# >>> claude-ollama-env <<<) y actualiza el
    bloque existente en vez de duplicarlo. Soporta -Uninstall para borrar el bloque.

    NO hace dot-source del profile completo al final (para no re-ejecutar
    side-effects del usuario como chcp, Set-Location, prompts). Solo setea
    las 3 env vars en la sesion actual.

.PARAMETER Unattended
    Si se especifica, no pausa ni pide confirmaciones. Util para CI/scripts.
.PARAMETER OllamaPort
    Puerto de Ollama. Default: 11434.
.PARAMETER Uninstall
    Si se especifica, BORRA el bloque del profile en vez de crearlo/actualizarlo.
.PARAMETER ListProfiles
    Si se especifica, muestra TODOS los profile paths relevantes y sale (no modifica nada).
.EXAMPLE
    .\install-claude-ollama-env.ps1
    .\install-claude-ollama-env.ps1 -Unattended
    .\install-claude-ollama-env.ps1 -ListProfiles
    .\install-claude-ollama-env.ps1 -Uninstall
#>

[CmdletBinding()]
param(
    [switch]$Unattended,
    [int]$OllamaPort = 11434,
    [switch]$Uninstall,
    [switch]$ListProfiles
)

$ErrorActionPreference = "Stop"
$ProfilePath = $PROFILE.CurrentUserAllHosts
$Utf8NoBom   = [System.Text.UTF8Encoding]::new($false)

# Cargar modulo compartido (unica fuente de verdad para los 3 env vars + el bloque
# de profile). Sin esto, los env vars se duplican aqui y en launch_ollama.ps1.
$claudeEnvModule = Join-Path $PSScriptRoot "claude-env.ps1"
if (-not (Test-Path $claudeEnvModule)) {
    Write-Host "ERROR: no se encontro el modulo compartido:" -ForegroundColor Red
    Write-Host "  $claudeEnvModule" -ForegroundColor Red
    Write-Host "Este script debe estar junto a claude-env.ps1." -ForegroundColor Red
    exit 1
}
. $claudeEnvModule

# Usar los marcadores del modulo (NO redefinir localmente: DRY)
$MarkerStart = $script:ClaudeEnvMarkerStart
$MarkerEnd   = $script:ClaudeEnvMarkerEnd

function Write-Step { param([string]$T) Write-Host "" ; Write-Host $T -ForegroundColor Cyan }
function Write-Ok    { param([string]$T) Write-Host "  $T" -ForegroundColor Green }
function Write-Warn  { param([string]$T) Write-Host "  $T" -ForegroundColor Yellow }
function Write-Err   { param([string]$T) Write-Host "  $T" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# -ListProfiles: solo muestra info y sale
# ---------------------------------------------------------------------------
if ($ListProfiles) {
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host " Profile paths en este sistema" -ForegroundColor Magenta
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host "  PS Version:        $($PSVersionTable.PSVersion)"
    Write-Host "  CurrentUserAllHosts (este script usara):  $ProfilePath"
    Write-Host "  CurrentUserCurrentHost:                   $($PROFILE.CurrentUserCurrentHost)"
    Write-Host ""
    Write-Host "  Path PowerShell 7 (pwsh):    C:\Users\<user>\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"
    Write-Host "  Path Windows PowerShell 5:   C:\Users\<user>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
    exit 0
}

# ---------------------------------------------------------------------------
# Construir el bloque a insertar — delegado al modulo compartido (DRY).
# Get-ClaudeEnvBlock encapsula el here-string + el placeholder del puerto.
# ---------------------------------------------------------------------------

Write-Host "============================================" -ForegroundColor Magenta
Write-Host " install-claude-ollama-env.ps1" -ForegroundColor Magenta
Write-Host " Persistir/remover env vars de Claude Code en profile" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  PS Version:   $($PSVersionTable.PSVersion)"
Write-Host "  Profile:      $ProfilePath"
Write-Host "  Ollama URL:   http://localhost:$OllamaPort"
Write-Host "  Modo:         $(if ($Uninstall) { 'UNINSTALL' } else { 'INSTALL' })"
Write-Host "  Unattended:   $Unattended"
Write-Host ""

# ---------------------------------------------------------------------------
# Detectar si estamos en Windows PowerShell 5 (legacy) y avisar al usuario
# ---------------------------------------------------------------------------
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Warn "Estas en PS 5.x; las env vars NO estaran en pwsh 7. Path PS5: $ProfilePath. Ejecuta desde pwsh 7 (escribe 'pwsh' o C:\Program Files\PowerShell\7\pwsh.exe) para persistir en su profile correcto."
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------
if ($Uninstall) {
    if (-not (Test-Path $ProfilePath)) {
        Write-Warn "Profile no existe: $ProfilePath (nada que desinstalar)"
        exit 0
    }
    $existing = [System.IO.File]::ReadAllText($ProfilePath, $Utf8NoBom)
    $startPos = $existing.IndexOf($MarkerStart)
    if ($startPos -lt 0) {
        Write-Warn "No se encontro el bloque claude-ollama-env en el profile (nada que desinstalar)"
        exit 0
    }
    $endPos = $existing.IndexOf($MarkerEnd, $startPos)
    if ($endPos -lt 0) {
        Write-Err "Marker de inicio encontrado pero no el de fin. Profile corrupto?"
        exit 1
    }
    $endOfBlock = $endPos + $MarkerEnd.Length
    # Quitar el bloque completo (incluyendo el newline previo si existe)
    $cutStart = $startPos
    if ($cutStart -gt 1) {
        $prevChar = $existing.Substring($cutStart - 1, 1)
        if ($prevChar -eq "`n") { $cutStart = $cutStart - 1 }
    }
    $newContent = $existing.Substring(0, $cutStart) + $existing.Substring($endOfBlock)
    [System.IO.File]::WriteAllText($ProfilePath, $newContent, $Utf8NoBom)
    Write-Ok "Bloque eliminado del profile"
    # Tambien limpiar env vars de la sesion actual
    Remove-Item Env:ANTHROPIC_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
    Write-Ok "Env vars limpiadas de la sesion actual"
    exit 0
}

# ---------------------------------------------------------------------------
# Confirmar (a menos que sea unattended)
# ---------------------------------------------------------------------------
if (-not $Unattended) {
    $answer = Read-Host "  ¿Persistir las env vars en tu profile de PowerShell? [y/N]"
    if ($answer -notmatch '^[Yy]') {
        Write-Warn "Cancelado por el usuario."
        exit 0
    }
}

# ---------------------------------------------------------------------------
# 1) Asegurar que el directorio del profile existe
# ---------------------------------------------------------------------------
$profileDir = Split-Path -Parent $ProfilePath
if (-not (Test-Path $profileDir)) {
    Write-Step "Creando directorio del profile: $profileDir"
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    Write-Ok "Directorio creado"
}

# ---------------------------------------------------------------------------
# 2) Construir el bloque nuevo (delegado a Get-ClaudeEnvBlock en claude-env.ps1)
# ---------------------------------------------------------------------------
$newBlock = Get-ClaudeEnvBlock -Port $OllamaPort
$lineCount = ($newBlock -split "`n").Count
Write-Step "Bloque a insertar ($lineCount lineas, $($newBlock.Length) chars)"

# ---------------------------------------------------------------------------
# 3) Leer profile existente y mergear idempotentemente
# ---------------------------------------------------------------------------
$existing = ""
if (Test-Path $ProfilePath) {
    $existing = [System.IO.File]::ReadAllText($ProfilePath, $Utf8NoBom)
    Write-Ok "Profile actual: $($existing.Length) chars"
} else {
    Write-Warn "Profile no existe. Se creara nuevo en: $ProfilePath"
}

$startPos = $existing.IndexOf($MarkerStart)
if ($startPos -ge 0) {
    $endPos = $existing.IndexOf($MarkerEnd, $startPos)
    if ($endPos -lt 0) {
        Write-Err "Marker de inicio encontrado pero no el de fin. Profile corrupto?"
        exit 1
    }
    $endOfBlock = $endPos + $MarkerEnd.Length
    $newContent = $existing.Substring(0, $startPos) + $newBlock + $existing.Substring($endOfBlock)
    Write-Step "Bloque existente detectado en pos $startPos..$endOfBlock — actualizando in-place"
    Write-Ok "Bloque actualizado (sin duplicar)"
} else {
    $newContent = $existing
    if ($newContent.Length -gt 0 -and -not $newContent.EndsWith("`n")) { $newContent += "`n" }
    $newContent += $newBlock
    Write-Step "Insertando nuevo bloque al final del profile"
    Write-Ok "Bloque agregado"
}

# ---------------------------------------------------------------------------
# 4) Escribir al profile (UTF-8 sin BOM)
# ---------------------------------------------------------------------------
[System.IO.File]::WriteAllText($ProfilePath, $newContent, $Utf8NoBom)
Write-Ok "Profile escrito: $ProfilePath ($($newContent.Length) chars)"

# ---------------------------------------------------------------------------
# 5) Validar sintaxis del profile
# ---------------------------------------------------------------------------
if ($newContent.Trim().Length -gt 0) {
    Write-Step "Validando sintaxis del profile..."
    try {
        $null = [System.Management.Automation.PSParser]::Tokenize($newContent, [ref]$null)
        Write-Ok "Sintaxis OK"
    } catch {
        Write-Err "Error de sintaxis: $($_.Exception.Message)"
        Write-Err "Revisa manualmente: $ProfilePath"
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 6) Aplicar env vars en la sesion actual (delegado a Set-ClaudeEnv en el
#    modulo compartido). NO dot-source del profile: re-ejecutaria
#    side-effects del usuario como chcp, Set-Location, prompts, etc.
# ---------------------------------------------------------------------------
Write-Step "Aplicando env vars en esta sesion..."
Set-ClaudeEnv -Port $OllamaPort

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Listo." -ForegroundColor Green
Write-Host " Las env vars estaran disponibles en TODA nueva sesion PowerShell." -ForegroundColor Green
Write-Host "   Para aplicar YA en esta ventana: reinicia PowerShell (o abre una nueva pestana)" -ForegroundColor Cyan
Write-Host "   Para desinstalar: .\install-claude-ollama-env.ps1 -Uninstall" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Green
