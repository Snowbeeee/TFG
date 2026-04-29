@echo off
REM ============================================================
REM  build.bat – Genera el .exe y crea los junctions necesarios
REM  Uso:  build.bat          (desde la raíz del proyecto)
REM ============================================================

echo [1/3] Comprobando Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python no encontrado. Descargando instalador...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    if %ERRORLEVEL% neq 0 (
        echo ERROR: No se pudo descargar Python. Comprueba tu conexion a internet.
        pause
        exit /b 1
    )
    echo Instalando Python...
    python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del python_installer.exe
    echo Python instalado. Reinicia el script para continuar.
    pause
    exit /b 0
)

echo [2/3] Instalando dependencias...
pip install PyQt6 PyOpenGL Pillow pyaudio pygame requests pyinstaller
if %ERRORLEVEL% neq 0 (
    echo ERROR: pip falló.
    pause
    exit /b 1
)

echo [3/3] Compilando con PyInstaller...
pyinstaller main.spec --noconfirm
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller falló.
    pause
    exit /b 1
)

echo [4/4] Creando carpetas necesarias si no existen...
if not exist games mkdir games
if not exist system mkdir system

echo [5/5] Creando junctions a las carpetas externas...
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

echo Listo!
echo.
echo   Ejecutable: %DIST%\TFG.exe
echo   Las carpetas games/, saves/, cores/ y system/ son junctions
echo   (cualquier cambio en las originales se refleja automaticamente).
echo.
pause
