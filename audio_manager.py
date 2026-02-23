import ctypes
import struct
import array
try:
    import pyaudio
except ImportError:
    pyaudio = None

class AudioManager:
    def __init__(self):
        self.audio_stream = None
        self.pyaudio_instance = None
        self._volume = 1.0  # 0.0 a 1.0

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = max(0.0, min(1.0, value))
    
    def init_stream(self, sample_rate):
        if pyaudio:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16, 
                channels=2, 
                rate=sample_rate, 
                output=True
            )
            print(f"Audio inicializado con PyAudio a {sample_rate} Hz")
        else:
            print("Advertencia: PyAudio no encontrado.")

    def write(self, data):
        if self.audio_stream:
            if self._volume < 1.0:
                data = self._apply_volume(data)
            self.audio_stream.write(data)

    def _apply_volume(self, data):
        """Aplica el multiplicador de volumen a muestras PCM int16 estéreo."""
        vol = self._volume
        if vol <= 0.0:
            return b'\x00' * len(data)
        # Desempaquetar muestras int16, escalar, reempaquetar
        n_samples = len(data) // 2
        samples = struct.unpack(f'<{n_samples}h', data)
        scaled = array.array('h', (max(-32768, min(32767, int(s * vol))) for s in samples))
        return scaled.tobytes()
    
    def stop(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
