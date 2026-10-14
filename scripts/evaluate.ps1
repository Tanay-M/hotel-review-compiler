# Evaluate the authored review corpus using the shared Python discovery.
& (Join-Path $PSScriptRoot 'run.ps1') '--evaluate' @args
exit $LASTEXITCODE
