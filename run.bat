@echo off
set PYTHON_EXE="C:\Users\IAP9978\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe"
echo ==========================================
echo   Invexa Control - Inicializando Sistema
echo ==========================================

echo.
echo [1/3] Limpando sessoes zumbi e processos antigos...
%PYTHON_EXE% cleanup.py

echo.
echo [2/3] Verificando dependencias...
%PYTHON_EXE% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Erro ao instalar dependencias. Verifique seu Python.
    pause
    exit /b
)

echo.
echo [3/3] Iniciando Servidor Web...
echo ==========================================
echo Acesse no seu navegador: http://localhost:8001
echo Para outros na rede: http://10.85.1.186:8001
echo Pressione CTRL+C para parar o sistema.
echo ==========================================
echo.

%PYTHON_EXE% -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

pause
