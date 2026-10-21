#!/usr/bin/env python3
"""Barrido de frecuencia que cruza Nyquist (C19, lámina «Demo en vivo»).

    python3 barrido.py                 # 200 → 3800 Hz, generado a fs = 4000: sube y luego BAJA
    python3 barrido.py --fs 44100      # mismo barrido, sin pliegue: sube limpio hasta 3800
    python3 barrido.py --fmax 8000     # con fs = 4000: sube, baja y vuelve a subir
    python3 barrido.py --wav salida.wav   # guarda el audio en vez de reproducirlo

Es el mismo código de la lámina y de la ficha (queda en Canvas para que lo corran y lo
modifiquen), con `sd.wait()` para que la terminal no cierre el sonido antes de tiempo.
Necesita numpy y sounddevice (`pip install sounddevice`).
"""
import argparse

import numpy as np

ap = argparse.ArgumentParser(description="Barrido de frecuencia que cruza Nyquist (C19)")
ap.add_argument("--fs", type=int, default=4000, help="frecuencia de muestreo en Hz (4000)")
ap.add_argument("--fmin", type=float, default=200, help="frecuencia inicial en Hz (200)")
ap.add_argument("--fmax", type=float, default=3800, help="frecuencia final en Hz (3800)")
ap.add_argument("--dur", type=float, default=6, help="duración en segundos (6)")
ap.add_argument("--wav", help="guardar en este archivo WAV en vez de reproducir")
args = ap.parse_args()

fs = args.fs                                     # frecuencia de muestreo (Hz)
t = np.arange(0, args.dur, 1/fs)
f_inst = args.fmin + (args.fmax - args.fmin) / args.dur * t   # barrido lineal
x = np.cos(2*np.pi*np.cumsum(f_inst)/fs)         # fase acumulada = integral de la frecuencia

print(f"fs = {fs} Hz (Nyquist en {fs/2:g} Hz) · barrido {args.fmin:g} → {args.fmax:g} Hz en {args.dur:g} s")
if args.wav:
    from scipy.io import wavfile
    wavfile.write(args.wav, fs, (0.8 * x).astype(np.float32))
    print(f"→ {args.wav}")
else:
    import sounddevice as sd
    sd.play(0.8 * x, fs)                         # ¿qué se escucha al cruzar fs/2?
    sd.wait()
