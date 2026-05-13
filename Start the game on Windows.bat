@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title 游戏启动器
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════╗
echo ║        游 戏 启 动 器           ║
echo ╚══════════════════════════════════╝
echo.

:: ============================================
:: 第一步：检测 Python 环境
:: ============================================
set PYTHON_CMD=

python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    goto :check_pygame
)

py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py"
    goto :check_pygame
)

:: ============================================
:: 第二步：Python 未找到，尝试自动安装
:: ============================================
echo [检测] 未找到 Python，开始自动安装...

:: 方式一：尝试用 winget 安装（Windows 10/11 自带）
where winget >nul 2>&1
if !errorlevel! equ 0 (
    echo [安装] 正在通过 winget 安装 Python 3.10...
    winget install Python.Python.3.10 --accept-source-agreements --accept-package-agreements
    if !errorlevel! equ 0 (
        call :refresh_env
        call :try_python
        if "!PYTHON_CMD!" neq "" goto :check_pygame
    )
)

:: 方式二：直接下载安装包静默安装
echo [安装] 正在下载 Python 3.10 安装包...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe' -OutFile '%TEMP%\python-3.10.11-amd64.exe'}" 2>nul

if exist "%TEMP%\python-3.10.11-amd64.exe" (
    echo [安装] 正在静默安装 Python（请稍候，可能需要几分钟）...
    "%TEMP%\python-3.10.11-amd64.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    del "%TEMP%\python-3.10.11-amd64.exe" 2>nul
    call :refresh_env
    call :try_python
    if "!PYTHON_CMD!" neq "" goto :check_pygame
)

:: 安装失败
echo.
echo [错误] 自动安装 Python 失败。
echo 请手动安装 Python 3.10+ 并勾选"添加到 PATH"：
echo https://www.python.org/downloads/
echo.
pause
exit /b 1

:: ============================================
:: 第三步：检测并安装 pygame
:: ============================================
:check_pygame
echo [检测] Python 命令: !PYTHON_CMD!

:: --- 检查 pygame ---
!PYTHON_CMD! -c "import pygame" >nul 2>&1
if !errorlevel! equ 0 (
    echo [检测] pygame 已安装。
    goto :check_cv2
)

echo [安装] 正在安装 pygame（使用清华镜像源）...
!PYTHON_CMD! -m pip install pygame -i https://pypi.tuna.tsinghua.edu.cn/simple
if !errorlevel! equ 0 (
    echo [完成] pygame 安装成功！
    goto :check_cv2
)

echo [重试] 使用默认源重新安装...
!PYTHON_CMD! -m pip install pygame
if !errorlevel! equ 0 (
    echo [完成] pygame 安装成功！
    goto :check_cv2
)

echo.
echo [错误] pygame 安装失败，请检查网络连接。
echo 可手动执行: !PYTHON_CMD! -m pip install pygame
echo.
pause
exit /b 1

:: --- 检查 opencv-python ---
:check_cv2
!PYTHON_CMD! -c "import cv2" >nul 2>&1
if !errorlevel! equ 0 (
    echo [检测] opencv-python 已安装。
    goto :run_game
)

echo [安装] 正在安装 opencv-python（使用清华镜像源）...
!PYTHON_CMD! -m pip install opencv-python -i https://pypi.tuna.tsinghua.edu.cn/simple
if !errorlevel! equ 0 (
    echo [完成] opencv-python 安装成功！
    goto :run_game
)

echo [重试] 使用默认源重新安装...
!PYTHON_CMD! -m pip install opencv-python
if !errorlevel! equ 0 (
    echo [完成] opencv-python 安装成功！
    goto :run_game
)

echo.
echo [错误] opencv-python 安装失败，请检查网络连接。
echo 可手动执行: !PYTHON_CMD! -m pip install opencv-python
echo.
pause
exit /b 1

:: ============================================
:: 第四步：启动游戏
:: ============================================
:run_game
echo.
echo [启动] 正在启动游戏...
echo ══════════════════════════════════
echo.
!PYTHON_CMD! main.py
if !errorlevel! neq 0 (
    echo.
    echo [提示] 游戏已退出。
    pause
)
exit /b 0

:: ============================================
:: 辅助：检测 Python 是否可用
:: ============================================
:try_python
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    echo [完成] Python 安装成功！
    exit /b
)
py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py"
    echo [完成] Python 安装成功！
    exit /b
)
exit /b

:: ============================================
:: 辅助：刷新 PATH（覆盖常见安装位置）
:: ============================================
:refresh_env
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%LOCALAPPDATA%\Microsoft\WindowsApps;C:\Program Files\Python310;C:\Program Files\Python310\Scripts"
exit /b
