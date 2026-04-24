@echo off
REM ============================================================
REM  build.bat — Compilador de Printer Counter
REM  Uso: build.bat  (doble clic o desde terminal)
REM  Genera: dist\Printer_Counter_V1.x.exe
REM ============================================================
setlocal

set EXE_NAME=Printer_Counter_V1.0
set ENTRY=main.py
set ICON=Icon.ico
set VENV_PY=.venv\Scripts\python.exe

echo.
echo ========================================
echo   Compilando %EXE_NAME%
echo ========================================
echo.

echo Limpiando build anterior...
if exist build  rd /s /q build
if exist dist   rd /s /q dist
if exist %EXE_NAME%.spec del /q %EXE_NAME%.spec

echo Iniciando PyInstaller...
%VENV_PY% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "%EXE_NAME%" ^
    --icon "%ICON%" ^
    --add-data "%ICON%;." ^
    %ENTRY%

if %ERRORLEVEL% == 0 (
    echo.
    echo ========================================
    echo   Build exitoso^^!
    echo   Archivo: dist\%EXE_NAME%.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo   ERROR en la compilacion
    echo   Revisa los mensajes de error arriba
    echo ========================================
)

echo.
pause
endlocal
