import ctypes
try:
    import pyaudio
except ImportError:
    pyaudio = None

class AudioManager:
    def __init__(self):
        self.audio_stream = None
        self.pyaudio_instance = None
    
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
            self.audio_stream.write(data)
    
    def stop(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
