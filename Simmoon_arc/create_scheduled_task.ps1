# create_scheduled_task.ps1
$taskName = "SIMMOON_DailySummary"
$scriptPath = Join-Path $PSScriptRoot "run_daily_summary.bat"

$action = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Daily -At "23:00"

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Force
Get-ScheduledTask -TaskName $taskName | Select TaskName, State, Trigger