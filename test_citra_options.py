from input.input_manager import QtInputManager
from audio.audio_manager import AudioManager
from libretro.retro_core import RetroCore

am = AudioManager()
im = QtInputManager()
core_citra = RetroCore("cores/citra_libretro.dll", am, im)
print("Citra options:")
for k, v in core_citra.available_options.items():
    print(k, v)

try:
    core_melon = RetroCore("cores/melonds_libretro.dll", am, im)
    print("\nMelonDS options:")
    for k, v in core_melon.available_options.items():
        print(k, v)
except Exception as e:
    print(e)
