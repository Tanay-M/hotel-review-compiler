param(
  [string]$Source = 'output/paper/Team_17_IEEE_Conference_Paper.docx',
  [string]$Destination = 'output/paper/Team_17_IEEE_Conference_Paper.pdf'
)
$ErrorActionPreference = 'Stop'
$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$destinationPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $Destination))
$paperWord = $null
$paperDocument = $null
try {
  $paperWord = New-Object -ComObject Word.Application
  $paperWord.Visible = $false
  $paperWord.DisplayAlerts = 0
  $paperWord.AutomationSecurity = 3
  $paperWord.Options.UpdateLinksAtOpen = $false
  $paperDocument = $paperWord.Documents.Open($sourcePath, $false, $true, $false)
  $paperDocument.Repaginate()
  $paperDocument.ExportAsFixedFormat($destinationPath, 17)
  $pageCount = $paperDocument.ComputeStatistics(2)
  Write-Output "Native Word export: $pageCount pages; $destinationPath"
}
finally {
  if ($null -ne $paperDocument) {
    $paperDocument.Close(0)
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($paperDocument) | Out-Null
  }
  if ($null -ne $paperWord) {
    $paperWord.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($paperWord) | Out-Null
  }
}
