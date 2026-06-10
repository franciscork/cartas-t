# Diagnostico del Sistema - $(Get-Date)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       DIAGNOSTICO DEL SISTEMA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- SISTEMA OPERATIVO ---
Write-Host "`n--- SISTEMA OPERATIVO ---" -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "Windows: $($os.Caption)"
Write-Host "Version: $($os.Version) | Build: $($os.BuildNumber)"
Write-Host "Arquitectura: $($os.OSArchitecture)"
Write-Host "Instalado: $($os.InstallDate)"
Write-Host "Tiempo encendido (horas): $([math]::Round(((Get-Date)-$os.LastBootUpTime).TotalHours,1))"

# --- RAM ---
Write-Host "`n--- MEMORIA RAM ---" -ForegroundColor Yellow
$cs = Get-CimInstance Win32_ComputerSystem
$totalRAM = [math]::Round($cs.TotalPhysicalMemory/1GB, 1)
$freeRAM = [math]::Round($os.FreePhysicalMemory/1MB, 1)
$usedRAM = [math]::Round(($cs.TotalPhysicalMemory - $os.FreePhysicalMemory*1KB)/1GB, 1)
$pctRAM = [math]::Round((($cs.TotalPhysicalMemory - $os.FreePhysicalMemory*1KB)/$cs.TotalPhysicalMemory)*100, 1)
Write-Host "Total RAM: $totalRAM GB"
Write-Host "En uso: $usedRAM GB  |  Libre: $freeRAM GB  |  Uso: $pctRAM%"

# --- CPU ---
Write-Host "`n--- PROCESADOR ---" -ForegroundColor Yellow
$cpu = Get-CimInstance Win32_Processor
Write-Host "Modelo: $($cpu.Name)"
Write-Host "Nucleos: $($cpu.NumberOfCores) | Hilos: $($cpu.NumberOfLogicalProcessors) | Max: $($cpu.MaxClockSpeed) MHz"
Write-Host "Carga actual: $($cpu.LoadPercentage)%"

# --- GPU ---
Write-Host "`n--- TARJETA GRAFICA ---" -ForegroundColor Yellow
Get-CimInstance Win32_VideoController | ForEach-Object {
    $vramGB = [math]::Round($_.AdapterRAM/1GB, 1)
    Write-Host "GPU: $($_.Name)  |  VRAM: $vramGB GB"
}

# --- DISCOS ---
Write-Host "`n--- DISCOS ---" -ForegroundColor Yellow
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    $total = [math]::Round($_.Size/1GB, 1)
    $free = [math]::Round($_.FreeSpace/1GB, 1)
    $used = $total - $free
    $pct = [math]::Round(($_.FreeSpace/$_.Size)*100, 1)
    Write-Host "$($_.DeviceID)  Total: ${total}GB  |  Usado: ${used}GB  |  Libre: ${free}GB  |  Libre: ${pct}%"
}

# Tipo de disco (SSD/HDD)
Write-Host "`n--- TIPO DE DISCO ---" -ForegroundColor Yellow
try {
    Get-PhysicalDisk | Select-Object FriendlyName, MediaType, @{N='Size_GB';E={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize
} catch {
    Write-Host "No se pudo obtener tipo de disco (requiere admin)"
}

# --- PROCESOS (Top RAM) ---
Write-Host "--- TOP 20 PROCESOS POR RAM ---" -ForegroundColor Yellow
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 @{N='Proceso';E={$_.ProcessName}}, @{N='RAM_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}}, Id | Format-Table -AutoSize

# --- PROCESOS (Top CPU) ---
Write-Host "--- TOP 10 PROCESOS POR CPU ---" -ForegroundColor Yellow
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 @{N='Proceso';E={$_.ProcessName}}, @{N='CPU_s';E={[math]::Round($_.CPU,0)}}, Id | Format-Table -AutoSize

# --- SERVICIOS ---
Write-Host "--- SERVICIOS ---" -ForegroundColor Yellow
$running = (Get-Service).Where({$_.Status -eq 'Running'}).Count
$stopped = (Get-Service).Where({$_.Status -eq 'Stopped'}).Count
Write-Host "Servicios ejecutandose: $running  |  Detenidos: $stopped  |  Total: $($running+$stopped)"

# --- TAREAS PROGRAMADAS ---
Write-Host "`n--- TAREAS PROGRAMADAS ---" -ForegroundColor Yellow
try {
    $tasks = (Get-ScheduledTask).Count
    Write-Host "Total tareas programadas: $tasks"
} catch {
    Write-Host "No se pudo obtener tareas programadas"
}

# --- RED ---
Write-Host "`n--- RED ---" -ForegroundColor Yellow
Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name, Status, LinkSpeed | Format-Table -AutoSize

# --- BATERIA ---
Write-Host "--- BATERIA ---" -ForegroundColor Yellow
$batt = Get-CimInstance Win32_Battery
if ($batt) {
    Write-Host "Carga: $($batt.EstimatedChargeRemaining)%  |  Estado: $($batt.BatteryStatus)"
}

# --- PLAN DE ENERGIA ---
Write-Host "`n--- PLAN DE ENERGIA ---" -ForegroundColor Yellow
powercfg /getactivescheme

# --- PROGRAMAS DE INICIO ---
Write-Host "`n--- PROGRAMAS DE INICIO ---" -ForegroundColor Yellow
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command | Format-Table -AutoSize -Wrap

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "       FIN DEL DIAGNOSTICO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
