# create_agatha_scheduled_task.ps1
# Crea una tarea programada de Windows para lanzar el daemon de Agatha Actas
# al iniciar sesion. Ejecutar como Administrador si se necesita
# ejecutar aunque el usuario no haya iniciado sesion.

$ErrorActionPreference = "Stop"

$taskName = "AgathaActas_Daemon"
$scriptDir = $PSScriptRoot
$batchPath = Join-Path $scriptDir "launch_agatha_daemon.bat"

if (-not (Test-Path $batchPath)) {
    Write-Error "No se encontro $batchPath. Ejecuta este script desde Simmoon_arc/"
    exit 1
}

Write-Host "`n  Creando tarea programada: $taskName"
Write-Host "  Launcher: $batchPath"
Write-Host "  Trigger: Al iniciar sesion (AtLogon)`n"

# ── Accion: ejecutar el .bat ──
$action = New-ScheduledTaskAction `
    -Execute $batchPath `
    -WorkingDirectory $scriptDir

# ── Trigger: al iniciar sesion ──
$trigger = New-ScheduledTaskTrigger -AtLogon

# ── Configuracion: ejecutar con maxima prioridad, reiniciar si falla ──
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Days 7)

# ── Registrar la tarea ──
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Daemon de Agatha Actas - Reportes periodicos, carga diaria en Obsidian, supervision FactoryGames" `
        -Force

    Write-Host "  Tarea creada exitosamente.`n"

    # ── Verificar ──
    $task = Get-ScheduledTask -TaskName $taskName
    Write-Host "  Resumen de la tarea:"
    Write-Host "  ──────────────────────────────────────"
    Write-Host "  Nombre : $($task.TaskName)"
    Write-Host "  Estado : $($task.State)"
    Write-Host "  Trigger: $($task.Triggers[0].CimClass.CimSuperClassName)"
    Write-Host ""

    # ── Preguntar si quiere ejecutarla ahora ──
    Write-Host "  Quieres ejecutar la tarea ahora? (S/N): " -NoNewline
    $resp = Read-Host
    if ($resp -eq "S" -or $resp -eq "s") {
        Start-ScheduledTask -TaskName $taskName
        Write-Host "  Daemon iniciado. Verifica agatha_daemon.log para el output."
    } else {
        Write-Host "  La tarea se ejecutara al proximo inicio de sesion."
    }

} catch {
    Write-Error "Error al crear la tarea: $_"
    Write-Host "`n  Soluciones posibles:"
    Write-Host "    1. Ejecuta PowerShell como Administrador"
    Write-Host "    2. Verifica que launch_agatha_daemon.bat existe en $scriptDir"
    Write-Host "    3. Revisa permisos de Task Scheduler"
    exit 1
}

Write-Host "`n  Para administrar la tarea manualmente:"
Write-Host "    taskschd.msc                           # Abrir Task Scheduler"
Write-Host "    Get-ScheduledTask -TaskName '$taskName' # Ver estado"
Write-Host "    Start-ScheduledTask -TaskName '$taskName' # Ejecutar ahora"
Write-Host "    Stop-ScheduledTask -TaskName '$taskName'  # Detener"
Write-Host "    Unregister-ScheduledTask -TaskName '$taskName' # Eliminar"
Write-Host ""
