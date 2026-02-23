@echo off
set PYTHON_EXE=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_EXE=C:\Users\IAP9978\AppData\Local\Programs\Python\Python313\python.exe
)
echo Usando: %PYTHON_EXE%
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
echo (Acesso restrito a esta maquina)
echo Pressione CTRL+C para parar o sistema.
echo ==========================================
echo.

%PYTHON_EXE% -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

pause
