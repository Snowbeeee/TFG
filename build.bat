@echo off
REM ============================================================
REM  build.bat – Genera un único TFG.exe en bin/
REM  Uso:  build.bat          (desde la raíz del proyecto)
REM ============================================================

echo [1/3] Comprobando Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python no encontrado. Descargando instalador oficial...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    if %ERRORLEVEL% neq 0 (
        echo ERROR: No se pudo descargar Python. Comprueba tu conexion a internet.
        pause
        exit /b 1
    )
    echo Instalando Python (instalacion por usuario, sin permisos de admin)...
    REM /quiet: sin UI. InstallAllUsers=0: por-usuario, no requiere admin.
    REM PrependPath=1: anade python y Scripts al PATH (solo en cmds NUEVOS).
    REM Include_pip=1: fuerza la instalacion de pip aunque el usuario lo hubiera desactivado.
    python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
    set INSTALL_ERR=%ERRORLEVEL%
    del python_installer.exe
    if %INSTALL_ERR% neq 0 (
        echo ERROR: La instalacion de Python fallo con codigo %INSTALL_ERR%.
        echo Prueba a instalar Python 3.11 manualmente desde python.org.
        pause
        exit /b 1
    )
    echo.
    echo ================================================================
    echo   Python instalado correctamente.
    echo   IMPORTANTE: cierra esta ventana de cmd y abre una NUEVA
    echo   para que el PATH se actualice, luego vuelve a lanzar build.bat.
    echo ================================================================
    pause
    exit /b 0
)

echo Comprobando pip...
python -m pip --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo pip no encontrado en esta instalacion de Python. Instalandolo con ensurepip...
    python -m ensurepip --default-pip
    if %ERRORLEVEL% neq 0 (
        echo ERROR: No se pudo instalar pip automaticamente.
        echo Reinstala Python 3.11 desde python.org marcando "Install pip".
        pause
        exit /b 1
    )
)

echo [2/3] Instalando dependencias...
REM Se invoca pip a traves de "python -m pip" para no depender de que la
REM carpeta Scripts\ este en el PATH. Justo despues de instalar Python o
REM tras un "pip install X" el ejecutable X.exe queda en Scripts\ pero
REM el PATH de esta sesion de cmd todavia no lo ve.
python -m pip install --upgrade pip
python -m pip install PyQt6 PyQt6-Qt6 PyOpenGL Pillow pyaudio pygame requests pyinstaller
if %ERRORLEVEL% neq 0 (
    echo ERROR: pip fallo instalando dependencias.
    pause
    exit /b 1
)

REM Comprobar si TFG.exe está en uso antes de compilar
if exist TFG.exe (
    del /F TFG.exe >nul 2>&1
    if exist TFG.exe (
        echo ERROR: TFG.exe esta en uso. Cierra la aplicacion o espera a que el
        echo antivirus termine de analizarlo e intentalo de nuevo.
        pause
        exit /b 1
    )
)

echo [3/3] Compilando con PyInstaller (modo onefile)...
REM Igual que arriba: "python -m PyInstaller" evita depender de que
REM pyinstaller.exe este en el PATH, que es lo que falla justo despues
REM de instalar el paquete en esta misma sesion.
python -m PyInstaller main.spec --noconfirm --distpath .
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller fallo.
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
