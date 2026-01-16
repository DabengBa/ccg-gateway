@echo off
setlocal

echo === CCG Gateway Build Script ===
echo.

cd /d "%~dp0"

echo [1/3] Building frontend...
cd frontend
call pnpm install
if errorlevel 1 (
    echo Failed to install frontend dependencies!
    pause
    exit /b 1
)
call pnpm build
if errorlevel 1 (
    echo Frontend build failed!
    pause
    exit /b 1
)
cd ..

echo.
echo [2/3] Running PyInstaller...
cd backend
uv run --extra desktop pyinstaller --noconfirm "..\desktop\ccg-gateway.spec"
if errorlevel 1 (
    echo PyInstaller build failed!
    pause
    exit /b 1
)
cd ..

echo.
echo [3/3] Copying data files...
if not exist "backend\dist\ccg-gateway\data" mkdir "backend\dist\ccg-gateway\data"
if exist ".env" copy ".env" "backend\dist\ccg-gateway\data\.env"
if exist ".env.example" copy ".env.example" "backend\dist\ccg-gateway\data\.env.example"

echo.
echo === Build completed! ===
echo Output: backend\dist\ccg-gateway\
echo.

pause
endlocal
