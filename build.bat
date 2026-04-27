@echo off
REM ============================================================
REM  build.bat – Genera el .exe y crea los junctions necesarios
REM  Uso:  build.bat          (desde la raíz del proyecto)
REM ============================================================

echo [1/3] Compilando con PyInstaller...
pyinstaller main.spec --noconfirm
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller falló.
    pause
    exit /b 1
)

echo [2/3] Creando junctions a las carpetas externas...
set DIST=dist\TFG

REM Eliminar junctions/carpetas anteriores si existen
for %%D in (games saves cores system) do (
    if exist "%DIST%\%%D" rmdir "%DIST%\%%D" 2>nul
)

REM Crear junctions (no requieren permisos de admin)
mklink /J "%DIST%\games"  "%~dp0games"
mklink /J "%DIST%\saves"  "%~dp0saves"
mklink /J "%DIST%\cores"  "%~dp0cores"
mklink /J "%DIST%\system" "%~dp0system"

REM Copiar config.json (archivo normal, no junction)
if exist config.json copy /Y config.json "%DIST%\config.json" >nul

echo [3/3] Listo!
echo.
echo   Ejecutable: %DIST%\TFG.exe
echo   Las carpetas games/, saves/, cores/ y system/ son junctions
echo   (cualquier cambio en las originales se refleja automaticamente).
echo.
pause
