# Windows launcher: prefer an installed Python, then Codex's bundled runtime.
# All command-line arguments are forwarded to the compiler unchanged.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = $null
$taskPythonPrefix = @()
$taskModule = 'hotel_compiler'
$taskArguments = @($args)
if ($taskArguments.Count -gt 0 -and $taskArguments[0] -eq '--web') {
    $taskModule = 'hotel_compiler.web'
    $taskArguments = @($taskArguments | Select-Object -Skip 1)
}
elseif ($taskArguments.Count -gt 0 -and $taskArguments[0] -eq '--batch') {
    $taskModule = 'hotel_compiler.batch_cli'
    $taskArguments = @($taskArguments | Select-Object -Skip 1)
}
elseif ($taskArguments.Count -gt 0 -and $taskArguments[0] -eq '--evaluate') {
    $taskModule = 'hotel_compiler.evaluation'
    $taskArguments = @($taskArguments | Select-Object -Skip 1)
}
elseif ($taskArguments.Count -gt 0 -and $taskArguments[0] -eq '--research') {
    $taskModule = 'hotel_compiler.research_cli'
    $taskArguments = @($taskArguments | Select-Object -Skip 1)
}
$taskProjectPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $taskProjectPython) {
    $taskPython = $taskProjectPython
}
$taskInstalledPython = Get-Command python -ErrorAction SilentlyContinue
if (-not $taskPython -and $taskInstalledPython -and $taskInstalledPython.Source -notlike '*\WindowsApps\*') {
    $taskPython = $taskInstalledPython.Source
}
if (-not $taskPython) {
    $taskPythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($taskPythonLauncher -and $taskPythonLauncher.Source -notlike '*\WindowsApps\*') {
        $taskPython = $taskPythonLauncher.Source
        $taskPythonPrefix = @('-3')
    }
}
if (-not $taskPython) {
    $taskBundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $taskBundledPython) {
        $taskPython = $taskBundledPython
    }
}
if (-not $taskPython) {
    throw 'Python 3.10 or newer is required. Install Python, then run this launcher again.'
}
$taskExitCode = 0
Push-Location -LiteralPath $taskRoot
try {
    & $taskPython @taskPythonPrefix -X utf8 -m $taskModule @taskArguments
    $taskExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $taskExitCode

