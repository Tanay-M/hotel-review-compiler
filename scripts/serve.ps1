# Start the browser demo using the same Python discovery as the CLI launcher.
& (Join-Path $PSScriptRoot 'run.ps1') '--web' @args
exit $LASTEXITCODE
