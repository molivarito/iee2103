# -*- coding: utf-8 -*-
"""
demo_convolucion_audio.py — La convolución audible: señal seca * respuesta al impulso
========================================================================================

Qué ilustra
-----------
La convolución no es solo un ejercicio de pizarra: y = x * h es literalmente
lo que se escucha cuando una señal "seca" (grabada sin reverberación) suena
dentro de un espacio acústico real cuya respuesta al impulso (IR) se ha
medido con un disparo/globo/sine-sweep. Este script:

    1. Genera una señal seca corta x[n]: un par de clicks (impulsos breves)
       seguidos de un fragmento de melodía sintética simple (arpegio).
    2. Carga una respuesta al impulso real h[n] desde common/ejercicios/IR
       (archivos .wav de salas, iglesias, túneles, etc. — ver Read Me.txt
       de cada carpeta), la deja mono y la resamplea si su fs no coincide
       con la de x (resampleo lineal con numpy puro, sin dependencias
       adicionales de DSP).
    3. Calcula y = x * h (scipy.signal.fftconvolve si está disponible, si
       no np.convolve) y la normaliza para evitar clipping.
    4. Muestra x, h e y en 3 filas (forma de onda + espectrograma) y permite,
       con el foco en la figura:

           t -> reproducir la señal seca
           c -> reproducir la señal convolucionada (con reverberación)
           g -> guardar los tres .wav (seco, IR adaptada, convolucionado)

       La reproducción usa sounddevice si está instalado; si no, la demo
       degrada con gracia e indica cómo guardar los .wav para reproducirlos
       con otro programa (no se cae ni exige la librería).

A qué clase sirve
------------------
C7 (convolución analítica y gráfica; demo con respuestas al impulso
acústicas reales (IR .wav), U2.3) del curso IEE2103 — la "convolución
audible" que conecta la teoría de C6 con una experiencia perceptual.

Dependencias: numpy, matplotlib, scipy.io.wavfile (lectura/escritura de
.wav) y opcionalmente scipy.signal.fftconvolve (si no está, se usa
np.convolve) y sounddevice (si no está, se degrada a solo guardar/graficar).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from scipy.io import wavfile

try:
    from scipy.signal import fftconvolve
    HAS_SCIPY_SIGNAL = True
except ImportError:  # pragma: no cover
    HAS_SCIPY_SIGNAL = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


# ---------------------------------------------------------------------------
# 1. Funciones puras de cálculo (sin dependencia de matplotlib/sounddevice)
# ---------------------------------------------------------------------------

def resample_lineal(x, fs_in, fs_out):
    """Resampleo simple por interpolación lineal (numpy puro)."""
    x = np.asarray(x, dtype=float)
    if fs_in == fs_out:
        return x.copy()
    dur = len(x) / fs_in
    n_out = max(1, int(round(dur * fs_out)))
    t_in = np.arange(len(x)) / fs_in
    t_out = np.arange(n_out) / fs_out
    return np.interp(t_out, t_in, x)


def generar_senal_seca(fs=44100):
    """
    Genera una señal seca corta: unos clicks (impulsos breves con caída
    exponencial) seguidos de un arpegio simple con envolvente para evitar
    clicks de encendido/apagado. Sirve como x[n] "sin sala" para convolucionar
    con una IR real.
    """
    # --- clicks ---
    dur_clicks = 0.6
    n_muestras_clicks = int(fs * dur_clicks)
    x_clicks = np.zeros(n_muestras_clicks)
    n_clicks = 4
    ancho_click = max(1, int(0.003 * fs))
    posiciones = np.linspace(0, n_muestras_clicks - ancho_click - 1, n_clicks).astype(int)
    n_local = np.arange(ancho_click)
    envolvente_click = np.exp(-n_local / (ancho_click / 4.0))
    for pos in posiciones:
        x_clicks[pos:pos + ancho_click] += envolvente_click

    # --- arpegio simple (C4-E4-G4-C5) con envolvente ADSR simplificada ---
    notas_hz = [261.63, 329.63, 392.00, 523.25]
    dur_nota = 0.30
    n_nota = int(fs * dur_nota)
    t_nota = np.arange(n_nota) / fs
    ataque = max(1, int(0.01 * fs))
    caida = max(1, int(0.05 * fs))
    trozos = []
    for f0 in notas_hz:
        env = np.ones(n_nota)
        env[:ataque] = np.linspace(0.0, 1.0, ataque)
        env[-caida:] = np.linspace(1.0, 0.0, caida)
        trozos.append(0.6 * np.sin(2 * np.pi * f0 * t_nota) * env)
    x_melodia = np.concatenate(trozos)

    x = np.concatenate([x_clicks, x_melodia])
    pico = np.max(np.abs(x))
    if pico > 0:
        x = x / pico * 0.9
    return x, fs


def cargar_ir(path, fs_objetivo=44100):
    """
    Carga una respuesta al impulso real desde un .wav, la deja mono
    (promedio de canales si es estéreo/multicanal), normalizada a pico
    unitario, y resampleada a fs_objetivo si su fs original es distinta.
    Devuelve (h, fs_objetivo).
    """
    fs_ir, data = wavfile.read(str(path))
    data = np.asarray(data, dtype=np.float64)
    if data.ndim > 1:
        data = data.mean(axis=1)
    pico = np.max(np.abs(data))
    if pico > 0:
        data = data / pico
    if fs_ir != fs_objetivo:
        data = resample_lineal(data, fs_ir, fs_objetivo)
    return data, fs_objetivo


def convolucionar(x, h):
    """y = x * h (convolución lineal completa). Usa FFT si scipy está
    disponible (mucho más rápido para IRs largas); si no, np.convolve."""
    if HAS_SCIPY_SIGNAL:
        return fftconvolve(x, h, mode="full")
    return np.convolve(x, h, mode="full")


def normalizar_sin_clipping(y, headroom=0.98):
    """Escala y para que su pico quede en `headroom` (<1) y así no clipee
    al guardarlo como PCM entero."""
    y = np.asarray(y, dtype=float)
    pico = np.max(np.abs(y))
    if pico < 1e-12:
        return y.copy()
    return y * (headroom / pico)


def guardar_wav(path, señal, fs):
    """Guarda una señal float en [-1,1] como .wav PCM16."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    señal_i16 = np.clip(señal, -1.0, 1.0)
    señal_i16 = (señal_i16 * 32767.0).astype(np.int16)
    wavfile.write(str(path), fs, señal_i16)


def reproducir(audio, fs, nombre=""):
    """Reproduce `audio` con sounddevice si está disponible; si no, informa
    cómo proceder en su lugar (degradación con gracia, no falla la demo)."""
    if HAS_SOUNDDEVICE:
        try:
            sd.play(np.asarray(audio, dtype=float), fs)
            sd.wait()
            return True
        except Exception as e:  # pragma: no cover (depende del hardware)
            print(f"[audio] No se pudo reproducir '{nombre}': {e}. "
                  f"Usa 'g' para guardar los .wav y reprodúcelos con otro programa.")
            return False
    else:
        print(f"[audio] sounddevice no está instalado: no se puede reproducir "
              f"'{nombre}' en vivo. Presiona 'g' para guardar los .wav.")
        return False


# ---------------------------------------------------------------------------
# 2. Rutas por defecto
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
# Script vive en material/demos/convolucion/; el repo del curso está 3 niveles
# arriba y de ahí cuelga common/ejercicios/IR con las respuestas al impulso.
IR_DEFAULT = (_SCRIPT_DIR.parent.parent.parent / "common" / "ejercicios" / "IR"
              / "lady-chapel-st-albans-cathedral" / "mono" / "stalbans_a_mono.wav")


# ---------------------------------------------------------------------------
# 3. GUI (matplotlib puro; se construye aparte del cómputo para poder
#    probar/guardar figuras sin abrir ventana interactiva)
# ---------------------------------------------------------------------------

def construir_figura(x, h, y, fs):
    """Construye la figura de 3x2 (forma de onda + espectrograma) para
    x (seco), h (IR) e y (convolucionado). No llama a plt.show()."""
    fig, axs = plt.subplots(3, 2, figsize=(12, 9))
    fig.suptitle("Convolución audible: x (seco)  *  h (IR real)  =  y (con reverberación)",
                 fontsize=12)

    señales = [("x[n] — seco", x), ("h[n] — respuesta al impulso (IR)", h), ("y[n] = x * h", y)]
    for fila, (titulo, s) in enumerate(señales):
        t = np.arange(len(s)) / fs
        ax_wave = axs[fila, 0]
        ax_wave.plot(t, s, lw=0.6, color="tab:blue")
        ax_wave.set_title(titulo, fontsize=10)
        ax_wave.set_xlabel("t [s]")
        ax_wave.set_ylabel("amplitud")
        ax_wave.grid(True, alpha=0.3)

        ax_spec = axs[fila, 1]
        nfft = min(1024, max(64, int(2 ** np.floor(np.log2(max(8, len(s) // 8))))))
        if len(s) > nfft:
            ax_spec.specgram(s, NFFT=nfft, Fs=fs, noverlap=nfft // 2, cmap="magma")
        else:
            ax_spec.text(0.5, 0.5, "(señal muy corta\npara espectrograma)",
                         ha="center", va="center", transform=ax_spec.transAxes)
        ax_spec.set_title("espectrograma", fontsize=10)
        ax_spec.set_xlabel("t [s]")
        ax_spec.set_ylabel("f [Hz]")

    fig.tight_layout(rect=[0, 0.06, 1, 0.95])
    fig.text(0.5, 0.02,
             "Teclas:  [t] tocar seco   [c] tocar convolucionado   [g] guardar .wav"
             + ("" if HAS_SOUNDDEVICE else "   (sounddevice no disponible: usa 'g')"),
             ha="center", fontsize=10, color="dimgray")
    return fig


def conectar_teclas(fig, x, h, y, fs, outdir):
    """Conecta el manejador de teclado t/c/g a la figura ya construida."""
    def on_key(event):
        if event.key == "t":
            reproducir(x, fs, nombre="seco")
        elif event.key == "c":
            reproducir(y, fs, nombre="convolucionado")
        elif event.key == "g":
            guardar_wav(Path(outdir) / "seco.wav", x, fs)
            guardar_wav(Path(outdir) / "ir_adaptada.wav", h, fs)
            guardar_wav(Path(outdir) / "convolucionado.wav", y, fs)
            print(f"[audio] .wav guardados en: {outdir}")

    fig.canvas.mpl_connect("key_press_event", on_key)


# ---------------------------------------------------------------------------
# 4. Orquestación de punta a punta (usable con o sin GUI, para pruebas)
# ---------------------------------------------------------------------------

def ejecutar_pipeline(ir_path, fs=44100):
    """Genera x, carga y adapta h, calcula y normalizado. Sin matplotlib ni
    sounddevice: útil para pruebas automáticas de punta a punta."""
    x, fs = generar_senal_seca(fs=fs)
    h, fs = cargar_ir(ir_path, fs_objetivo=fs)
    y_bruta = convolucionar(x, h)
    y = normalizar_sin_clipping(y_bruta)
    return x, h, y, fs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", default=str(IR_DEFAULT),
                        help="Ruta a la respuesta al impulso .wav (default: %(default)s)")
    parser.add_argument("--fs", type=int, default=44100, help="Frecuencia de muestreo de trabajo")
    parser.add_argument("--outdir", default=None,
                        help="Carpeta donde guardar los .wav con 'g' (default: ./salida_convolucion_audio)")
    parser.add_argument("--no-gui", action="store_true",
                        help="Solo calcula y opcionalmente guarda, sin abrir la figura interactiva")
    parser.add_argument("--guardar", action="store_true",
                        help="Guarda los .wav de salida inmediatamente (útil junto con --no-gui)")
    args = parser.parse_args()

    outdir = args.outdir or str(Path.cwd() / "salida_convolucion_audio")

    ir_path = Path(args.ir)
    if not ir_path.exists():
        print(f"[error] No se encontró la IR: {ir_path}", file=sys.stderr)
        sys.exit(1)

    x, h, y, fs = ejecutar_pipeline(ir_path, fs=args.fs)
    print(f"[info] IR: {ir_path.name}  |  len(x)={len(x)}  len(h)={len(h)}  len(y)={len(y)}  fs={fs}")
    print(f"[info] pico |y| tras normalizar = {np.max(np.abs(y)):.4f} (debe ser <= 0.98)")

    if args.guardar or args.no_gui:
        guardar_wav(Path(outdir) / "seco.wav", x, fs)
        guardar_wav(Path(outdir) / "ir_adaptada.wav", h, fs)
        guardar_wav(Path(outdir) / "convolucionado.wav", y, fs)
        print(f"[info] .wav guardados en: {outdir}")

    if not args.no_gui:
        fig = construir_figura(x, h, y, fs)
        conectar_teclas(fig, x, h, y, fs, outdir)
        plt.show()


if __name__ == "__main__":
    main()
