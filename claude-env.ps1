<#
.SYNOPSIS
    Modulo compartido: Set-ClaudeEnv (unica fuente de verdad para los 3 env vars de Claude Code)
.DESCRIPTION
    Centraliza la logica de configurar las 3 env vars necesarias para que Claude Code
    use Ollama como backend:
      $env:ANTHROPIC_BASE_URL    = "http://localhost:<port>"
      $env:ANTHROPIC_AUTH_TOKEN  = "ollama"
      $env:ANTHROPIC_API_KEY     = ""

    Usado por:
      - launch_ollama.ps1 (auto-exporta al arrancar el servicio)
      - launch_claude_ollama.ps1 (wrapper one-command)
      - install-claude-ollama-env.ps1 (persiste en $PROFILE)

    DRY: una sola fuente de verdad. Cambios futuros a los env vars (e.g., agregar uno nuevo)
    se hacen solo aqui.

.PARAMETER Port
    Puerto de Ollama. Default: 11434.
.PARAMETER Persistent
    Si se especifica, persiste las env vars en HKCU\Environment para que sobrevivan
    al cerrar PowerShell (disponibles en todas las sesiones futuras).
.PARAMETER Quiet
    Si se especifica, no imprime los Write-Host de confirmacion (util para wrappers
    que ya tienen su propio output).
.PARAMETER MakePersistent
    DEPRECATED: usar -Persistent (switch) en su lugar. Mantenido por backward
    compat con callers que usaban la firma antigua `-MakePersistent [bool]`.
    Emitira un Write-Warning si se usa.
.EXAMPLE
    . (Join-Path $PSScriptRoot "claude-env.ps1")
    Set-ClaudeEnv -Port 11434
.EXAMPLE
    Set-ClaudeEnv -Port 11434 -Persistent
.EXAMPLE
    Set-ClaudeEnv -Port 11434 -Quiet
#>

$script:ClaudeEnvPort = 11434

function Set-ClaudeEnv {
    [CmdletBinding()]
    param(
        [int]$Port = $script:ClaudeEnvPort,
        [switch]$Persistent,
        [switch]$Quiet,
        [System.Obsolete("Usar -Persistent (switch) en vez de -MakePersistent (bool)")]
        [bool]$MakePersistent = $false
    )

    if ($MakePersistent) {
        Write-Warning "-MakePersistent esta deprecado, usar -Persistent (switch) en su lugar."
        $Persistent = $true
    }

    $script:ClaudeEnvPort = $Port

    $env:ANTHROPIC_BASE_URL    = "http://localhost:$Port"
    $env:ANTHROPIC_AUTH_TOKEN  = "ollama"
    $env:ANTHROPIC_API_KEY     = ""

    if (-not $Quiet) {
        Write-Host "  ANTHROPIC_BASE_URL    = $env:ANTHROPIC_BASE_URL"
        Write-Host "  ANTHROPIC_AUTH_TOKEN  = $env:ANTHROPIC_AUTH_TOKEN"
        Write-Host "  ANTHROPIC_API_KEY     = (empty)"
    }

    if ($Persistent) {
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL",   $env:ANTHROPIC_BASE_URL,   "User")
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", $env:ANTHROPIC_AUTH_TOKEN, "User")
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY",    "",                       "User")
        if (-not $Quiet) {
            Write-Host "  Env vars persistidas en HKCU\Environment" -ForegroundColor Magenta
        }
    }
}

if ($MyInvocation.InvocationName -ne '.' -and $Host.Name -eq 'ConsoleHost') {
    Write-Host "claude-env.ps1 cargado. Usar: Set-ClaudeEnv -Port <p> [-Persistent] [-Quiet]" -ForegroundColor Cyan
}
