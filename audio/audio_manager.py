import ctypes
import struct      # Para desempaquetar/empaquetar datos binarios (muestras de audio PCM)
import array       # Para crear arrays tipados eficientes de muestras de audio

# Intentar importar PyAudio; si no está instalado, se desactiva el audio
try:
    import pyaudio
except ImportError:
    pyaudio = None

# Clase encargada de gestionar la salida de audio del emulador.
# Recibe las muestras de audio del core Libretro y las reproduce mediante PyAudio.
class AudioManager:
    # Inicializa las variables del gestor de audio
    def __init__(self):
        self.audio_stream = None           # Stream de salida de PyAudio
        self.pyaudio_instance = None       # Instancia principal de PyAudio
        self._volume = 1.0                 # Volumen actual (rango 0.0 a 1.0)

    # Propiedad de solo lectura para obtener el volumen actual
    @property
    def volume(self):
        return self._volume

    # Setter del volumen. Limita el valor al rango [0.0, 1.0] para evitar distorsión
    @volume.setter
    def volume(self, value):
        self._volume = max(0.0, min(1.0, value))
    
    # Inicializa el stream de audio con la frecuencia de muestreo indicada por el core.
    # Configura PyAudio para reproducir audio estéreo (2 canales) en formato PCM 16 bits.
    def init_stream(self, sample_rate):
        if pyaudio:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,     # Formato: enteros de 16 bits con signo
                channels=2,                 # Estéreo (izquierdo + derecho)
                rate=sample_rate,           # Frecuencia de muestreo (ej: 32000, 44100 Hz)
                output=True                 # Solo salida (reproducción)
            )
            print(f"Audio inicializado con PyAudio a {sample_rate} Hz")
        else:
            print("Advertencia: PyAudio no encontrado.")

    # Escribe un bloque de muestras de audio en el stream de reproducción.
    # Si el volumen es menor a 1.0, aplica el escalado antes de escribir.
    def write(self, data):
        if self.audio_stream:
            if self._volume < 1.0:
                data = self._apply_volume(data)
            self.audio_stream.write(data)

    # Aplica el multiplicador de volumen a muestras PCM int16 estéreo.
    # Desempaqueta los bytes en muestras numéricas, las escala y las vuelve a empaquetar.
    def _apply_volume(self, data):
        vol = self._volume
        # Si el volumen es 0, devolver silencio directamente (bytes a cero)
        if vol <= 0.0:
            return b'\x00' * len(data)
        # Cada muestra ocupa 2 bytes (int16), así que el número de muestras es len/2
        n_samples = len(data) // 2
        # Desempaquetar los bytes como enteros de 16 bits con signo en little-endian
        samples = struct.unpack(f'<{n_samples}h', data)
        # Escalar cada muestra por el volumen, limitando al rango [-32768, 32767]
        # para evitar desbordamiento (clipping)
        scaled = array.array('h', (max(-32768, min(32767, int(s * vol))) for s in samples))
        # Convertir de vuelta a bytes para enviar al stream
        return scaled.tobytes()
    
    # Detiene y cierra el stream de audio, liberando los recursos de PyAudio
    def stop(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()    # Detener la reproducción
            self.audio_stream.close()          # Cerrar el stream
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()  # Liberar recursos de PyAudio
