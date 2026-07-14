import ctypes
import struct      # Para desempaquetar/empaquetar datos binarios (muestras de audio PCM)
import array       # Para crear arrays tipados eficientes de muestras de audio

# Intentar importar PyAudio; si no está instalado, se desactiva el audio
try:
    import pyaudio
except ImportError:
    pyaudio = None

# Qt sí refleja los cambios de dispositivo por defecto del sistema
# (en Windows escucha las notificaciones de IMMNotificationClient de
# Core Audio). PortAudio, en cambio, congela el default en Pa_Initialize
# aunque reinicies la instancia. Usamos Qt como fuente de verdad para el
# nombre del default actual y luego abrimos PyAudio con output_device_index
# apuntando al índice que corresponde a ese nombre.
try:
    from PyQt6.QtMultimedia import QMediaDevices
    _qt_media_available = True
except ImportError:
    _qt_media_available = False

# Clase encargada de gestionar la salida de audio del emulador.
# Recibe las muestras de audio del core Libretro y las reproduce mediante PyAudio.
class AudioManager:
    # Inicializa las variables del gestor de audio
    def __init__(self):
        self.audio_stream = None           # Stream de salida de PyAudio
        self.pyaudio_instance = None       # Instancia principal de PyAudio
        self._volume = 1.0                 # Volumen actual (rango 0.0 a 1.0)
        self._muted = False                # True → write() descarta muestras (fast-forward)
        self._sample_rate = 0              # Sample rate del stream actual (para reabrir tras cambio de dispositivo)
        self._device_name = ""             # Nombre del dispositivo con el que abrimos el stream

    # Propiedad de solo lectura para obtener el volumen actual
    @property
    def volume(self):
        return self._volume

    # Setter del volumen. Limita el valor al rango [0.0, 1.0] para evitar distorsión
    @volume.setter
    def volume(self, value):
        self._volume = max(0.0, min(1.0, value))
    
    # Devuelve el nombre del dispositivo de salida default del sistema
    # según Qt (que sí refresca este valor al vuelo en Windows).
    @staticmethod
    def _qt_default_output_name():
        if not _qt_media_available:
            return ""
        try:
            device = QMediaDevices.defaultAudioOutput()
            if device is None:
                return ""
            return device.description() or ""
        except Exception:
            return ""

    # Busca el índice de PyAudio cuyo nombre coincide (o encaja como
    # substring) con target_name. Windows y PortAudio suelen usar el
    # mismo texto pero en algún backend puede venir truncado, así que
    # se prueba primero coincidencia exacta y luego substring.
    def _find_pyaudio_index_by_name(self, target_name):
        if not self.pyaudio_instance or not target_name:
            return None
        target_lower = target_name.lower()
        count = self.pyaudio_instance.get_device_count()
        # Coincidencia exacta
        for i in range(count):
            try:
                info = self.pyaudio_instance.get_device_info_by_index(i)
            except Exception:
                continue
            if info.get("maxOutputChannels", 0) <= 0:
                continue
            if info.get("name", "").lower() == target_lower:
                return i
        # Coincidencia por substring
        for i in range(count):
            try:
                info = self.pyaudio_instance.get_device_info_by_index(i)
            except Exception:
                continue
            if info.get("maxOutputChannels", 0) <= 0:
                continue
            name = info.get("name", "").lower()
            if target_lower in name or name in target_lower:
                return i
        return None

    # Inicializa el stream de audio con la frecuencia de muestreo indicada por el core.
    # Configura PyAudio para reproducir audio estéreo (2 canales) en formato PCM 16 bits.
    # Elige el dispositivo apuntando al que Qt considera default (Qt sí ve
    # los cambios en caliente); si no lo encuentra en la lista de PyAudio,
    # se cae al default de PortAudio.
    def init_stream(self, sample_rate):
        if not pyaudio:
            print("Advertencia: PyAudio no encontrado.")
            return
        self.pyaudio_instance = pyaudio.PyAudio()
        self._sample_rate = sample_rate

        qt_name = self._qt_default_output_name()
        device_index = self._find_pyaudio_index_by_name(qt_name) if qt_name else None
        if qt_name:
            self._device_name = qt_name
        else:
            try:
                info = self.pyaudio_instance.get_default_output_device_info()
                self._device_name = info.get("name", "")
            except Exception:
                self._device_name = ""

        kwargs = {
            "format": pyaudio.paInt16,
            "channels": 2,
            "rate": sample_rate,
            "output": True,
        }
        if device_index is not None:
            kwargs["output_device_index"] = device_index

        self.audio_stream = self.pyaudio_instance.open(**kwargs)
        print(f"[Audio] Stream abierto a {sample_rate} Hz en '{self._device_name}' (índice PyAudio: {device_index})")

    # Activa/desactiva el modo mudo. En modo mudo, write() descarta las
    # muestras sin enviarlas al stream de PyAudio, liberando el throttle
    # bloqueante y permitiendo que el emulador corra a más de velocidad
    # nativa (fast-forward). El stream sigue abierto reproduciendo silencio.
    def set_muted(self, muted):
        self._muted = bool(muted)

    # Escribe un bloque de muestras de audio en el stream de reproducción.
    # Si el volumen es menor a 1.0, aplica el escalado antes de escribir.
    # En modo mudo se descartan las muestras (no se llama a write bloqueante).
    def write(self, data):
        if self._muted or not self.audio_stream:
            return
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
    
    # Detiene y cierra el stream de audio, liberando los recursos de PyAudio.
    # Deja los atributos a None para que write() no intente usar un stream
    # cerrado tras un reopen o al terminar la sesión.
    def stop(self):
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except Exception:
                pass
            self.pyaudio_instance = None

    # Comprueba si el dispositivo de salida por defecto del sistema ha
    # cambiado desde que abrimos el stream. Se llama periódicamente desde
    # un QTimer en OpenGLWidget (~2 s). Usa Qt como fuente de verdad
    # (QMediaDevices sí refresca cuando Windows cambia el default en
    # caliente; PortAudio no lo hace ni recreando la instancia).
    def check_default_device_changed(self):
        if not self.audio_stream:
            return
        new_name = self._qt_default_output_name()
        if not new_name or new_name == self._device_name:
            return
        print(f"[Audio] Default cambiado: '{self._device_name}' → '{new_name}', reabriendo stream")
        sample_rate = self._sample_rate
        self.stop()
        if sample_rate:
            self.init_stream(sample_rate)
