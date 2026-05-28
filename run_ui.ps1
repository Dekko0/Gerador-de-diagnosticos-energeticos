# Inicia a interface web (Streamlit) usando o ambiente virtual do projeto.
# Uso:  .\run_ui.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Ambiente virtual nao encontrado. Rode primeiro:  .\setup.ps1" -ForegroundColor Yellow
    exit 1
}
& $py -m streamlit run app/ui/app.py
