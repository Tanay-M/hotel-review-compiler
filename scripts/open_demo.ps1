param([int]$Port = 8000, [switch]$NoBrowser, [switch]$Stop)
$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path -Parent $PSScriptRoot
if ($Stop) {
    $demoPidPath = Join-Path $demoRoot "tmp\web-demo\server-$Port.pid"
    if (-not (Test-Path -LiteralPath $demoPidPath)) { Write-Host 'No launcher-managed demo was found.'; exit 0 }
    $demoSaved = [int](Get-Content -LiteralPath $demoPidPath)
    $demoListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $demoListener) { Write-Host 'The demo is already stopped.'; exit 0 }
    $demoOwner = Get-CimInstance Win32_Process -Filter "ProcessId = $($demoListener.OwningProcess)"
    if ($demoOwner.CommandLine -notmatch '-m hotel_compiler.web' -or ($demoOwner.ProcessId -ne $demoSaved -and $demoOwner.ParentProcessId -ne $demoSaved)) { throw 'The listener is not this launcher-managed demo. No process was stopped.' }
    Stop-Process -Id $demoOwner.ProcessId
    if (Get-Process -Id $demoSaved -ErrorAction SilentlyContinue) { Stop-Process -Id $demoSaved }
    Write-Host 'Hotel Review Compiler stopped.'
    exit 0
}
$demoPython = Join-Path $demoRoot '.venv\Scripts\python.exe'
$demoNeuralPython = Join-Path $demoRoot '.venv-neural\Scripts\python.exe'
$demoNeuralModel = Join-Path $demoRoot 'output\neural\2026-10-23-webis-v1\models\finetuned\recovery_manifest.json'
$demoDLModel = Join-Path $demoRoot 'output\neural\2026-10-23-dl-pair-human-v1\models\best\routed_manifest.json'
if ((Test-Path -LiteralPath $demoNeuralPython) -and ((Test-Path -LiteralPath $demoNeuralModel) -or (Test-Path -LiteralPath $demoDLModel))) {
    $demoPython = $demoNeuralPython
}
if (-not (Test-Path -LiteralPath $demoPython)) {
    throw 'Create .venv and install the project first: python -m venv .venv, then .venv\Scripts\python -m pip install -e ".[research]"'
}
$demoUrl = "http://127.0.0.1:$Port"
$demoHealth = $null
try { $demoHealth = Invoke-RestMethod "$demoUrl/api/health" -TimeoutSec 2 } catch {}
if ($demoHealth -and $demoHealth.application -ne 'team17-hotel-review-compiler') {
    throw "Port $Port is already used by another service. Try Start_Demo.bat -Port 8010."
}
if (-not $demoHealth) {
    $demoLogs = Join-Path $demoRoot 'tmp\web-demo'
    New-Item -ItemType Directory -Force -Path $demoLogs | Out-Null
    $demoProcess = Start-Process -FilePath $demoPython -ArgumentList @('-X','utf8','-m','hotel_compiler.web','--port',"$Port") -WorkingDirectory $demoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $demoLogs "server-$Port.out.log") -RedirectStandardError (Join-Path $demoLogs "server-$Port.err.log")
    for ($demoAttempt = 0; $demoAttempt -lt 40; $demoAttempt++) {
        Start-Sleep -Milliseconds 250
        try { $demoHealth = Invoke-RestMethod "$demoUrl/api/health" -TimeoutSec 1 } catch {}
        if ($demoHealth.application -eq 'team17-hotel-review-compiler') { break }
        if ($demoProcess.HasExited) { throw "The server stopped. Check tmp\web-demo\server-$Port.err.log." }
    }
    if ($demoHealth.application -ne 'team17-hotel-review-compiler') { throw 'The demo did not become ready. Check tmp\web-demo logs.' }
    Set-Content -LiteralPath (Join-Path $demoLogs "server-$Port.pid") -Value $demoProcess.Id
}
Write-Host "Hotel Review Compiler is running: $demoUrl"
Write-Host 'Choose Hybrid -> fine-tuned DL reanalysis. Upload the cleaned Booking CSV from dataset.'
if (-not $NoBrowser) { Start-Process $demoUrl }
