<#
.SYNOPSIS
    Crea (o actualiza) un GitHub Release usando gh CLI o GitHub API.
.DESCRIPTION
    Idempotente: si el release ya existe, actualiza las notas (no falla).
    Si no existe, lo crea con el title y notas especificados.

    Path 1: gh CLI (preferido). Auto-instala via winget si no esta.
    Path 2: GitHub API con GITHUB_TOKEN/GH_TOKEN env var (fallback).
    Path 3: Instrucciones manuales para la UI web (ultimo recurso).

    Uso tipico: .\create-release.ps1                 # usa defaults (v1.0.0-ollama-integration)
           .\create-release.ps1 -DryRun             # mostrar lo que haria
           .\create-release.ps1 -Tag v1.1.0         # para otro release
           .\create-release.ps1 -Repo otro/repo     # para otro repo

.PARAMETER Repo
    Repo en formato owner/name. Default: franciscork/cartas-t
.PARAMETER Tag
    Tag del release. Default: v1.0.0-ollama-integration
.PARAMETER Title
    Titulo del release. Default: v1.0.0-ollama-integration - Claude Code + Ollama
.PARAMETER NotesFile
    Path al archivo Markdown con las notas. Default: RELEASE_NOTES.md (junto al script)
.PARAMETER DryRun
    Muestra lo que haria sin hacer cambios.
#>

[CmdletBinding()]
param(
    [string]$Repo      = "franciscork/cartas-t",
    [string]$Tag       = "v1.0.0-ollama-integration",
    [string]$Title     = "v1.0.0-ollama-integration - Claude Code + Ollama (local, privado, sin API key)",
    [string]$NotesFile = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Default NotesFile = RELEASE_NOTES.md junto al script
if (-not $NotesFile) {
    $NotesFile = Join-Path $PSScriptRoot "RELEASE_NOTES.md"
}

$GhPath = "C:\Program Files\GitHub CLI\gh.exe"

function Write-Step { param([string]$T) Write-Host "" ; Write-Host $T -ForegroundColor Cyan }
function Write-Ok    { param([string]$T) Write-Host "  $T" -ForegroundColor Green }
function Write-Warn  { param([string]$T) Write-Host "  $T" -ForegroundColor Yellow }
function Write-Err   { param([string]$T) Write-Host "  $T" -ForegroundColor Red }

# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------
function Get-GhPath {
    if (Test-Path $GhPath) { return $GhPath }
    $cmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Install-Gh {
    Write-Warn "gh no encontrado. Intentando instalar via winget..."
    try {
        $proc = Start-Process -FilePath "winget" -ArgumentList @(
            "install", "--id", "GitHub.cli",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "-s",           # silent: suprime UI del installer
            "-i"            # disable-interactivity: suprime prompts
        ) -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -eq 0) {
            Write-Ok "gh instalado"
            return $true
        }
        Write-Err "winget fallo con exit code $($proc.ExitCode)"
        return $false
    } catch {
        Write-Err "No se pudo ejecutar winget: $($_.Exception.Message)"
        return $false
    }
}

function Test-GhAuth {
    param([string]$Gh)
    # gh auth token devuelve un string no-vacio si esta authed, exit 1 si no.
    # Mas confiable que gh auth status (cuyo exit code puede ser 0 sin auth util).
    $token = & $Gh auth token 2>&1
    return ($LASTEXITCODE -eq 0) -and (-not [string]::IsNullOrWhiteSpace($token))
}

# -----------------------------------------------------------------
# Validaciones iniciales
# -----------------------------------------------------------------
if (-not (Test-Path $NotesFile)) {
    Write-Err "No se encuentra el archivo de notas: $NotesFile"
    exit 1
}

Write-Step "create-release.ps1"
Write-Host "  Repo:      $Repo"
Write-Host "  Tag:       $Tag"
Write-Host "  Title:     $Title"
Write-Host "  NotesFile: $NotesFile"
Write-Host "  DryRun:    $DryRun"
Write-Host ""

# -----------------------------------------------------------------
# Path 1: gh CLI
# -----------------------------------------------------------------
$gh = Get-GhPath
if (-not $gh) {
    if ($DryRun) {
        Write-Warn "[DRY-RUN] gh no encontrado; saltando install"
    } else {
        $installed = Install-Gh
        if ($installed) { $gh = Get-GhPath }
    }
}

if ($gh) {
    Write-Step "gh CLI: $gh"
    & $gh --version | Select-Object -First 1

    if (-not (Test-GhAuth $gh)) {
        Write-Warn "gh no autenticado. Opciones:"
        Write-Host "  1. gh auth login                  (interactivo)" -ForegroundColor Yellow
        Write-Host "  2. `$env:GH_TOKEN = 'ghp_...'      (o GITHUB_TOKEN)" -ForegroundColor Yellow
        Write-Host "  3. .\create-release.ps1" -ForegroundColor Yellow
        if ($env:GH_TOKEN -or $env:GITHUB_TOKEN) {
            Write-Warn "GH_TOKEN detectado en env. Cayendo a Path 2 (API)."
        } else {
            Write-Err "Aborta: gh no autenticado y no hay GH_TOKEN/GITHUB_TOKEN"
            exit 1
        }
    } else {
        Write-Ok "gh auth OK"

        # Check if release exists
        $viewOut = & $gh release view $Tag --repo $Repo 2>&1
        $exists = ($LASTEXITCODE -eq 0)
        Write-Host "  release existe: $exists"

        if ($exists) {
            Write-Step "Actualizando notas del release existente..."
            if ($DryRun) {
                Write-Warn "[DRY-RUN] gh release edit $Tag --repo $Repo --notes-file $NotesFile"
            } else {
                $editOut = & $gh release edit $Tag --repo $Repo --notes-file $NotesFile 2>&1
                if ($LASTEXITCODE -ne 0) {
                    Write-Err "gh release edit fallo: $editOut"
                    exit 1
                }
                Write-Ok "Notas actualizadas"
            }
        } else {
            Write-Step "Creando release $Tag..."
            if ($DryRun) {
                Write-Warn "[DRY-RUN] gh release create $Tag --repo $Repo --title <title> --notes-file $NotesFile"
            } else {
                $createOut = & $gh release create $Tag --repo $Repo --title $Title --notes-file $NotesFile 2>&1
                if ($LASTEXITCODE -ne 0) {
                    Write-Err "gh release create fallo: $createOut"
                    exit 1
                }
                Write-Ok "Release creado"
            }
        }

        Write-Step "Verificando resultado..."
        & $gh release view $Tag --repo $Repo 2>&1 | Select-Object -First 20

        $url = & $gh release view $Tag --repo $Repo --json url -q .url 2>&1
        Write-Ok "URL: $url"
        exit 0
    }
}

# -----------------------------------------------------------------
# Path 2: GitHub API via Invoke-RestMethod + GITHUB_TOKEN
# -----------------------------------------------------------------
$token = $env:GITHUB_TOKEN
if (-not $token) { $token = $env:GH_TOKEN }

if ($token) {
    Write-Step "Usando GitHub API con token..."

    $headers = @{
        "Authorization" = "token $token"
        "Accept"        = "application/vnd.github.v3+json"
        "User-Agent"    = "create-release.ps1"
    }

    try {
        $existing = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/tags/$Tag" -Headers $headers
    } catch {
        $existing = $null
    }

    $notes = Get-Content $NotesFile -Raw

    if ($existing) {
        Write-Step "Release existe (id=$($existing.id)). Actualizando notas..."
        $body = @{ body = $notes } | ConvertTo-Json
        if ($DryRun) {
            Write-Warn "[DRY-RUN] PATCH /releases/$($existing.id)"
        } else {
            $null = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/$($existing.id)" `
                -Method PATCH -Headers $headers -Body $body -ContentType "application/json"
        }
        Write-Ok "Notas actualizadas"
    } else {
        Write-Step "Creando release via API..."
        $body = @{
            tag_name   = $Tag
            name       = $Title
            body       = $notes
            draft      = $false
            prerelease = $false
        } | ConvertTo-Json
        if ($DryRun) {
            Write-Warn "[DRY-RUN] POST /releases"
        } else {
            $null = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases" `
                -Method POST -Headers $headers -Body $body -ContentType "application/json"
        }
        Write-Ok "Release creado"
    }

    $url = "https://github.com/$Repo/releases/tag/$Tag"
    Write-Ok "URL: $url"
    exit 0
}

# -----------------------------------------------------------------
# Path 3: Manual instructions
# -----------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host " No se pudo crear el release automaticamente" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Opcion A: Autenticar gh y correr este script" -ForegroundColor Cyan
Write-Host "  gh auth login"
Write-Host "  .\create-release.ps1"
Write-Host ""
Write-Host "Opcion B: Crear via UI web" -ForegroundColor Cyan
Write-Host "  https://github.com/$Repo/releases/new?tag=$Tag"
Write-Host "  Title: $Title"
Write-Host "  Description: pegar contenido de $NotesFile"
Write-Host ""
Write-Host "Opcion C: API con GITHUB_TOKEN" -ForegroundColor Cyan
Write-Host "  `$env:GITHUB_TOKEN = 'ghp_...'"
Write-Host "  .\create-release.ps1"
Write-Host ""
exit 1
