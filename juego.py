import audio_manager
import input_manager_pygame
import retro_core 

class Juego:
    def __init__(self, ruta_core, ruta_juego, titulo):
        self.ruta_core = ruta_core
        self.ruta_juego = ruta_juego
        self.core = None
        self.titulo = titulo
        self.consola = ""
        
        if ".3ds" in ruta_juego.lower():
            self.consola = "Nintendo 3DS"
        elif ".nds" in ruta_juego.lower():
            self.consola = "Nintendo DS"
        else:
            self.consola = "Desconocida"


    def iniciar_juego(self, audio_manager, input_manager):
        self.core = retro_core.RetroCore(self.ruta_core, audio_manager, input_manager)
        self.core.load_game(self.ruta_juego)
        self.core.run()
        
            
    def finalizar_juego(self):
        if self.core:
            self.core.unload()
            self.core = None

