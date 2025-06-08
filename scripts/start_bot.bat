@echo off
chcp 65001 > nul
title 트레이딩 봇 시작 도우미

echo 🎯 트레이딩 봇 시작 도우미
echo ==============================

REM 현재 스크립트 위치
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다
    pause
    exit /b 1
)

REM 가상환경 활성화 (있는 경우)
if exist "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
    echo 📁 가상환경 활성화 중...
    call "%PROJECT_ROOT%\venv\Scripts\activate.bat"
)

echo.
echo 실행 모드를 선택하세요:
echo 1) 일반 모드 (실제 거래)
echo 2) 안전 모드 (모의 거래)
echo 3) 환경 검증만
echo 4) 재시작 없이 한 번만 실행
echo.

set /p choice="선택 (1-4): "

if "%choice%"=="1" (
    echo 🚀 일반 모드로 시작합니다...
    python "%SCRIPT_DIR%start_bot.py"
) else if "%choice%"=="2" (
    echo 🛡️ 안전 모드로 시작합니다...
    python "%SCRIPT_DIR%start_bot.py" --safe-mode
) else if "%choice%"=="3" (
    echo 🔍 환경 검증을 수행합니다...
    python "%SCRIPT_DIR%start_bot.py" --check-only
) else if "%choice%"=="4" (
    echo 🔄 재시작 없이 실행합니다...
    python "%SCRIPT_DIR%start_bot.py" --no-restart
) else (
    echo ❌ 올바른 선택지를 입력하세요
    pause
    exit /b 1
)

pause