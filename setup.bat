@echo off
title TTSアプリ 初期セットアップ
echo ===================================================
echo TTSアプリ 専用動作環境のセットアップを開始します。
echo この処理はお使いのPCの環境（システム設定等）を一切汚さず、
echo このフォルダ内（bin）に専用の最小構成Pythonを構築します。
echo ===================================================
echo.

set BIN_DIR=%~dp0bin
set PYTHON_ZIP=python-3.11.9-embed-amd64.zip
set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/%PYTHON_ZIP%

if not exist "%BIN_DIR%\python.exe" goto :DOWNLOAD
echo [情報] 既に bin フォルダが存在します。セットアップをスキップします。
goto :INSTALL_LIBS

:DOWNLOAD
echo [1/5] 軽量版Python (Embeddable Package) をダウンロード中...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'"

if exist "%PYTHON_ZIP%" goto :EXTRACT
echo [エラー] ダウンロードに失敗しました。インターネット接続を確認してください。
pause
exit /b 1

:EXTRACT
echo [2/5] ZIPファイルを展開中 (binフォルダを作成)...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%BIN_DIR%' -Force"
del "%PYTHON_ZIP%"

echo [3/5] GUI描画機能(Tkinter)を組み込んでいます...
if exist "%~dp0core\tkinter_files.zip" (
    powershell -Command "Expand-Archive -Path '%~dp0core\tkinter_files.zip' -DestinationPath '%BIN_DIR%' -Force"
) else (
    echo [警告] core\tkinter_files.zip が見つからないためGUIが起動しない可能性があります。
)

echo [4/5] パッケージ管理ツール(pip)を有効化しています...
powershell -Command "(Get-Content '%BIN_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%BIN_DIR%\python311._pth'; Add-Content -Path '%BIN_DIR%\python311._pth' -Value 'Lib'"

echo [5/5] pip本体をダウンロードしてインストール中...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%BIN_DIR%\get-pip.py'"
"%BIN_DIR%\python.exe" "%BIN_DIR%\get-pip.py"
del "%BIN_DIR%\get-pip.py"

:INSTALL_LIBS
echo.
echo ===================================================
echo 依存ライブラリのインストールを行っています...
echo ===================================================
"%BIN_DIR%\python.exe" -m pip install -r "%~dp0core\requirements.txt"

echo.
echo ===================================================
echo [完了] すべてのセットアップが正常に終了しました！
echo ===================================================
echo これ以降は「run.vbs」をダブルクリックするだけで
echo すぐにアプリを利用できます。
echo.
pause
