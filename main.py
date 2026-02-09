import sys
import os
import pygame
from pygame.locals import * 
from retro_core import RetroCore
from audio_manager import AudioManager
from input_manager import InputManager

def main():
    # Inicializar PyGame
    pygame.init()
    # Crear ventana con contexto OpenGL
    pygame.display.set_mode((400, 480), OPENGL | DOUBLEBUF | RESIZABLE)

    # Rutas
    # core_path = 'cores/citra_libretro.dll'
    core_path = 'cores/desmume_libretro.dll'
    # Ajusta esta ruta si es necesario o pásala como argumento
    # rom_path = r"C:\Users\griva\Desktop\TFG\TFG\games\PokemonSol.3ds"
    rom_path = r"C:\Users\griva\Desktop\TFG\TFG\games\PokemonNegro2.nds"

    if not os.path.exists(core_path):
        print(f"Error: No se encuentra el core en {core_path}")
        sys.exit(1)
        
    if not os.path.exists(rom_path):
        print(f"Error: No se encuentra la ROM en {rom_path}")
        # sys.exit(1) # Opcional: Permitir fallar en load_game si se quiere manejar

    # Instanciar Managers
    audio_mgr = AudioManager()
    input_mgr = InputManager()

    # Instanciar Core
    core = RetroCore(core_path, audio_mgr, input_mgr)

    # Cargar juego
    if core.load_game(rom_path):
        try:
            running = True
            while running:
                # Manejo de eventos de PyGame
                for event in pygame.event.get():
                    if event.type == QUIT:
                        running = False
                    elif event.type == VIDEORESIZE:
                        print(f"[MAIN] Evento Resize detectado: {event.w}x{event.h}")
                        # No llamamos a set_mode para no perder el contexto OpenGL
                        # Actualizamos el viewport en el core directamente
                        core.update_video(event.w, event.h)

                    # Pasar eventos al InputManager para el estado del mouse/touch
                    input_mgr.handle_event(event)
                
                # Obtener tamaño actual de la ventana
                # get_window_size() devuelve el tamaño real de la ventana, get_surface().get_size() devuelve el tamaño del buffer inicial
                win_w, win_h = pygame.display.get_window_size()
                
                # Asegurar que el core tenga las dimensiones correctas (por si no saltó el evento o al inicio)
                core.update_video(win_w, win_h) 
                
                # Ejecutar frame del core
                core.run()
                
                # Intercambiar buffers
                pygame.display.flip()
        except KeyboardInterrupt:
            pass
        finally:
            core.unload()
            audio_mgr.stop()
            pygame.quit()
    else:
        print("No se pudo iniciar el juego.")
        pygame.quit()
        sys.exit(1)

if __name__ == "__main__":
    main()
