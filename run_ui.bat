@echo off
REM Inicia a interface web (Streamlit) usando o ambiente virtual do projeto.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado. Rode primeiro:  powershell -ExecutionPolicy Bypass -File setup.ps1
    exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app\ui\app.py
