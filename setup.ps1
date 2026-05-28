# Cria o ambiente virtual (.venv) e instala as dependencias.
# Uso:  .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Localiza um Python 3.11+ utilizavel.
$pythonExe = $null
foreach ($cand in @("$env:LOCALAPPDATA\Python\bin\python.exe", "py", "python")) {
    try {
        $v = & $cand --version 2>$null
        if ($LASTEXITCODE -eq 0) { $pythonExe = $cand; break }
    } catch { }
}
if (-not $pythonExe) {
    Write-Host "Python 3.11+ nao encontrado. Instale de https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "Usando Python: $pythonExe"

& $pythonExe -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "`nPronto! Para iniciar a interface:  .\run_ui.ps1" -ForegroundColor Green
