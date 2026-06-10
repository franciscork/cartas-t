<#
.SYNOPSIS
    SIMMOON Overnight Image Generator
    Generates all 66 game assets with full progress logging.
.DESCRIPTION
    Runs simmoon_generator.py for all categories overnight with:
    - Detailed progress log with timestamps
    - Automatic retry for failed images
    - Console output + log file dual logging
    - Final summary report
    - Estimated time tracking
.PARAMETER Backend
    Image generation backend: comfyui or huggingface
.PARAMETER MaxRetries
    Maximum retry attempts for failed images (default: 3)
.PARAMETER DelayBetweenImages
    Seconds to wait between images (default: 2)
.EXAMPLE
    .\overnight_generate.ps1 -Backend comfyui
    .\overnight_generate.ps1 -Backend comfyui -MaxRetries 5
#>

param(
    [ValidateSet("comfyui", "huggingface")]
    [string]$Backend = "comfyui",

    [int]$MaxRetries = 3,
    [int]$DelayBetweenImages = 2
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GeneratorScript = Join-Path $ScriptDir "simmoon_generator.py"
$LogFile = Join-Path $ScriptDir "generation_log_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').txt"
$SummaryFile = Join-Path $ScriptDir "generation_summary.json"

# --- Logging Function ---
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    Write-Host $logLine -ForegroundColor $(
        switch ($Level) {
            "ERROR" { "Red" }
            "WARN"  { "Yellow" }
            "OK"    { "Green" }
            "START" { "Cyan" }
            default { "White" }
        }
    )
    Add-Content -Path $LogFile -Value $logLine
}

# --- Banner ---
function Write-Banner {
    $banner = @"

  ================================================================
  |     SIMMOON Overnight Image Generator                        |
  |     Backend: $($Backend.PadRight(46))|
  |     Log: $LogFile
  |     Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  ================================================================

"@
    Write-Host $banner -ForegroundColor Cyan
    Add-Content -Path $LogFile -Value $banner
}

# --- Check Prerequisites ---
function Test-Prerequisites {
    if (-not (Test-Path $GeneratorScript)) {
        Write-Log "simmoon_generator.py not found at $GeneratorScript" "ERROR"
        exit 1
    }

    try {
        python -c "import requests" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Installing requests package..." "WARN"
            pip install requests
        }
    } catch {
        Write-Log "Python is required. Install Python 3.8+" "ERROR"
        exit 1
    }

    Write-Log "Prerequisites check passed" "OK"
}

# --- Category Processing ---
function Invoke-CategoryGeneration {
    param(
        [string]$CategoryName,
        [int]$CategoryIndex,
        [int]$TotalCategories
    )

    Write-Log "=== Category $CategoryIndex/$TotalCategories: $CategoryName ===" "START"

    $attempt = 0
    $success = $false

    while ($attempt -lt $MaxRetries -and -not $success) {
        $attempt++
        Write-Log "Attempt $attempt/$MaxRetries for $CategoryName" "INFO"

        $startTime = Get-Date
        $output = python $GeneratorScript --backend $Backend --category $CategoryName 2>&1
        $exitCode = $LASTEXITCODE
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds

        # Parse output for stats
        $generated = ($output | Select-String "Generated:\s+(\d+)" | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -Last 1)
        $failed = ($output | Select-String "Failed:\s+(\d+)" | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -Last 1)
        $skipped = ($output | Select-String "Skipped:\s+(\d+)" | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -Last 1)

        if (-not $generated) { $generated = 0 }
        if (-not $failed) { $failed = 0 }
        if (-not $skipped) { $skipped = 0 }

        $generated = [int]$generated
        $failed = [int]$failed
        $skipped = [int]$skipped

        # Mark success if no failures OR if this is the last retry attempt
        # Also check exit code: non-zero means the script itself crashed
        if (($failed -eq 0 -and $exitCode -eq 0) -or $attempt -ge $MaxRetries) {
            $success = $true
        }

        # Log results
        $status = if ($success) { "OK" } else { "WARN" }
        Write-Log "  $CategoryName completed: generated=$generated, failed=$failed, skipped=$skipped (${duration}s)" $status

        # Log each image result from output
        foreach ($line in $output) {
            if ($line -match "\[OK\].*Saved|\[FAIL\]|\[SKIP\]") {
                Add-Content -Path $LogFile -Value "  $line"
            }
        }

        if (-not $success) {
            Write-Log "  Retrying $CategoryName in 10 seconds..." "WARN"
            Start-Sleep -Seconds 10
        }
    }

    return @{
        Category = $CategoryName
        Generated = $generated
        Failed = $failed
        Skipped = $skipped
        Duration = $duration
        Attempts = $attempt
    }
}

# --- Main Execution ---
Write-Banner
Test-Prerequisites

# Get category list
Write-Log "Fetching category list..." "INFO"
$categoryOutput = python $GeneratorScript --list-categories 2>&1
$categoryNames = @()
foreach ($line in $categoryOutput) {
    if ($line -match "^\s+([\w_]+)\s+-\s+(\d+)\s+images") {
        $categoryNames += $Matches[1]
    }
}

Write-Log "Found $($categoryNames.Count) categories: $($categoryNames -join ', ')" "OK"

# Process each category
$results = @()
$overallStartTime = Get-Date
$totalGenerated = 0
$totalFailed = 0
$totalSkipped = 0

for ($i = 0; $i -lt $categoryNames.Count; $i++) {
    $cat = $categoryNames[$i]        $result = Invoke-CategoryGeneration -CategoryName $cat -CategoryIndex ($i + 1) -TotalCategories $categoryNames.Count
    $results += $result

    $totalGenerated += $result.Generated
    $totalFailed += $result.Failed
    $totalSkipped += $result.Skipped

    # Brief pause between categories
    if ($i -lt ($categoryNames.Count - 1)) {
        Write-Log "Pausing 5 seconds before next category..." "INFO"
        Start-Sleep -Seconds 5
    }
}

$overallEndTime = Get-Date
$totalDuration = ($overallEndTime - $overallStartTime).TotalSeconds

# --- Final Summary ---
$summary = @{
    backend = $Backend
    started = $overallStartTime.ToString("yyyy-MM-dd HH:mm:ss")
    completed = $overallEndTime.ToString("yyyy-MM-dd HH:mm:ss")
    total_seconds = [math]::Round($totalDuration, 1)
    total_generated = $totalGenerated
    total_failed = $totalFailed
    total_skipped = $totalSkipped
    categories = $results | ForEach-Object {
        @{
            name = $_.Category
            generated = $_.Generated
            failed = $_.Failed
            skipped = $_.Skipped
            duration_seconds = [math]::Round($_.Duration, 1)
            attempts = $_.Attempts
        }
    }
}

$summary | ConvertTo-Json -Depth 5 | Set-Content -Path $SummaryFile

Write-Host ""
Write-Log "================================================================" "START"
Write-Log "  OVERNIGHT GENERATION COMPLETE" "OK"
Write-Log "================================================================" "START"
Write-Log "  Total Generated: $totalGenerated" "OK"
Write-Log "  Total Failed:    $totalFailed" $(if ($totalFailed -gt 0) { "WARN" } else { "OK" })
Write-Log "  Total Skipped:   $totalSkipped" "INFO"
Write-Log "  Total Duration:  $([math]::Round($totalDuration / 60, 1)) minutes" "INFO"
Write-Log "  Log File:        $LogFile" "INFO"
Write-Log "  Summary File:    $SummaryFile" "INFO"
Write-Log "================================================================" "START"

if ($totalFailed -gt 0) {
    Write-Log "Some images failed. Re-run to retry failed images (they will be skipped if they exist)." "WARN"
}
