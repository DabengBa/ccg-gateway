@echo off
title CCG Gateway

echo ========================================
echo   CCG Gateway Startup Script
echo ========================================
echo.

cd /d "%~dp0"

:: Load .env file
set GATEWAY_PORT=7788
set UI_PORT=3000
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if "%%a"=="GATEWAY_PORT" set GATEWAY_PORT=%%b
        if "%%a"=="UI_PORT" set UI_PORT=%%b
    )
)

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check pnpm
where pnpm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pnpm not found. Please install: npm install -g pnpm
    pause
    exit /b 1
)

:: Init backend venv
if not exist "backend\venv" (
    echo [Backend] Creating virtual environment...
    cd backend
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt -q
    cd ..
    echo [Backend] Virtual environment created
) else (
    echo [Backend] Virtual environment exists
)

:: Init frontend dependencies
if not exist "frontend\node_modules" (
    echo [Frontend] Installing dependencies...
    cd frontend
    pnpm install
    cd ..
    echo [Frontend] Dependencies installed
) else (
    echo [Frontend] Dependencies exist
)

echo.
echo ========================================
echo   Starting Services
echo ========================================
echo.

:: Start backend (new window)
echo [Backend] Starting... (port %GATEWAY_PORT%)
start "CCG Gateway - Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port %GATEWAY_PORT% --reload"

:: Wait for backend
timeout /t 3 /nobreak >nul

:: Start frontend (new window)
echo [Frontend] Starting... (port %UI_PORT%)
start "CCG Gateway - Frontend" cmd /k "cd /d %~dp0frontend && pnpm dev"

:: Wait for frontend
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   Services Started
echo ========================================
echo.
echo   Backend API:  http://127.0.0.1:%GATEWAY_PORT%
echo   Frontend UI:  http://127.0.0.1:%UI_PORT%
echo.
echo   Press any key to open browser...
pause >nul

start http://127.0.0.1:%UI_PORT%

echo.
echo   To stop services, run stop.bat
echo.
pause
