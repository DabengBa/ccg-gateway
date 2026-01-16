@echo off
title CCG Gateway - Frontend
cd /d "%~dp0frontend"

:: Sync dependencies
echo [Frontend] Syncing dependencies...
call pnpm install
if errorlevel 1 (
    echo [Error] Failed to install dependencies!
    pause
    exit /b 1
)

pnpm dev
