@echo off
REM ============================================================
REM  build.bat – Genera un único TFG.exe en bin/
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

echo [3/3] Compilando con PyInstaller (modo onefile)...
pyinstaller main.spec --noconfirm --distpath .
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller falló.
    pause
    exit /b 1
)

REM Crear carpetas externas si no existen
if not exist games mkdir games
if not exist saves mkdir saves
if not exist cores mkdir cores
if not exist system mkdir system

echo Listo!
echo.
echo   Ejecutable:  TFG.exe
echo   ROMs:        games\
echo   Cores:       cores\
echo   Saves:       saves\
echo.
pause
