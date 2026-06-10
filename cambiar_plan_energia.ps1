# Restaurar y activar Alto Rendimiento
Write-Host "=== RESTAURANDO PLANES OCULTOS ===" -ForegroundColor Cyan

# 1. Restaurar esquemas predeterminados
powercfg -restoredefaultschemes 2>&1 | Out-Null

# 2. El GUID estandar de Alto Rendimiento
$highPerfGuid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
powercfg -duplicatescheme $highPerfGuid 2>&1 | Out-Null

Write-Host "=== PLANES DISPONIBLES AHORA ===" -ForegroundColor Cyan
powercfg /list

Write-Host "`n=== ACTIVANDO ALTO RENDIMIENTO ===" -ForegroundColor Green
powercfg /setactive $highPerfGuid

Write-Host "`n=== PLAN ACTIVO CONFIRMADO ===" -ForegroundColor Green
powercfg /getactivescheme

Write-Host "`n=== CONFIGURACION DEL PLAN ===" -ForegroundColor Yellow
powercfg /query $highPerfGuid | Select-String -Pattern "Nombre|Modo de suspensi|Apagar disco|Brillo|Procesador" -SimpleMatch
