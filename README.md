# Emulator Frontend

Una interfaz gráfica de escritorio para gestionar y lanzar juegos de **Nintendo DS** y **Nintendo 3DS**, construida con PyQt6 y libretro.

---

> **Aviso importante:** Este proyecto **no incluye ni distribuye ROMs de ningún tipo**. Para utilizar la aplicación necesitas tus propias copias legales de los juegos. El desarrollador no se hace responsable del uso indebido de este software.

---

## ¿De qué va el proyecto?

Emulator Frontend es un lanzador de juegos que actúa como intermediario entre tu biblioteca de ROMs y los cores de emulación (libretro). En lugar de abrir el emulador directamente, esta interfaz te ofrece:

- Una **biblioteca visual** de todos tus juegos con portadas, iconos extraídos automáticamente de los propios ROMs y metadatos descargados desde [ScreenScraper](https://www.screenscraper.fr/)
- **Listas y categorías** personalizables para organizar tu colección
- **Estadísticas de juego**: tiempo total jugado y fecha de última sesión
- **Configuración de controles** por emulador (teclado y mando)
- **Ajustes gráficos y de audio** en tiempo real sin necesidad de reiniciar
- Lanzamiento directo de juegos con los cores de melonDS y Citra

---

## Sistemas soportados

| Sistema | Core | Formatos |
|---|---|---|
| Nintendo DS | melonDS | `.nds` |
| Nintendo 3DS | Citra | `.3ds` |

---

## Instalación (Windows)

**1. Clona el repositorio**

```bash
git clone https://github.com/Snowbeeee/TFG.git
cd TFG
```

**2. Ejecuta el script de compilación**

```bash
build.bat
```

El script instala las dependencias automáticamente y genera el ejecutable en `dist/TFG/TFG.exe`.

**3. Añade tus ROMs**

```
games/           ← tus ROMs (.nds, .3ds...)
```

---

## Estructura del proyecto

```
TFG/
├── main.py              # Punto de entrada
├── lista.py             # Gestión de listas y categorías
├── config.json          # Configuración de la app
│
├── ui/                  # Componentes de la interfaz (PyQt6)
│   ├── mainWindow/      # Ventana principal
│   ├── gameWindow/      # Ventana de emulación
│   ├── configWindow/    # Ajustes gráficos y de audio
│   ├── controlsWindow/  # Configuración de controles
│   └── gameDetailPage/  # Página de detalle del juego
│
├── libretro/            # Integración con cores libretro
├── audio/               # Gestión de audio (PyAudio)
├── input/               # Teclado, mando y pantalla táctil
├── api/                 # Cliente de ScreenScraper
├── game/                # Clase de juego y escaneo de ROMs
│
├── cores/               # DLLs de los cores (no incluidas)
├── games/               # Biblioteca de juegos (no incluida)
├── saves/               # Archivos de guardado
└── system/              # Archivos de sistema del emulador
```

---

## Configuración

Al primer arranque se genera un `config.json` con los valores por defecto. Desde la propia interfaz puedes ajustar:

- **Volumen** general
- **Renderizador** de DS (Software u OpenGL)
- **Resolución** de DS y 3DS (1x a 3x)
- **Controles** por teclado o mando para cada sistema

Para la descarga automática de metadatos y portadas necesitas credenciales de la API de [ScreenScraper](https://www.screenscraper.fr/) (gratuita con registro).

---

## Licencia

Distribuido bajo la licencia **GNU GPL v3**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

> Trabajo de Fin de Grado (TFG) para el Grado en Ingeniería del Software en la Universidad de Málaga (UMA).
