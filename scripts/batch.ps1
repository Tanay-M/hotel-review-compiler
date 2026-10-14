# Analyze a CSV using the same Python discovery as the other launchers.
& (Join-Path $PSScriptRoot 'run.ps1') '--batch' @args
exit $LASTEXITCODE
