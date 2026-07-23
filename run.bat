@echo off
title TTSアプリを起動中...

set BIN_DIR=%~dp0bin

if not exist "%BIN_DIR%\pythonw.exe" (
    echo [エラー] ランタイム環境が見つかりません。
    echo 先に「setup.bat」をダブルクリックして初期セットアップを完了させてください。
    pause
    exit /b 1
)

start "" "%BIN_DIR%\pythonw.exe" "%~dp0core\main.pyw"
