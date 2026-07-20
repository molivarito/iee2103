# -*- coding: utf-8 -*-
"""
demo_dtft.py — Transformada de Fourier de tiempo discreto (DTFT)
==================================================================

Qué ilustra
-----------
La DTFT de una señal discreta x[n]:

        X(e^{jω}) = Σ_n x[n] e^{-jωn}

calculada numéricamente (suma directa) para tres familias de señales
seleccionables con RadioButtons:

    - Pulso rectangular de largo L (slider L)
    - Exponencial causal a^n u[n]  (slider a, con |a|<1 para que converja)
    - Sinusoide enventanada: cos(ω0 n)·rect_L[n]  (sliders ω0 y L)

La figura tiene cuatro paneles:

    1. x[n]                    — stems de la señal en el dominio del tiempo
    2. círculo unitario         — el punto e^{jω} (slider ω) y su relación
                                  con la transformada Z evaluada en |z|=1
    3. |X(e^{jω})|              — magnitud en ω∈[-3π,3π], marcando
                                  explícitamente la periodicidad 2π (líneas
                                  verticales en los múltiplos de π y
                                  anotaciones de las réplicas)
    4. fase de X(e^{jω})        — con anotaciones de la simetría conjugada
                                  para x[n] real: |X| es par, la fase es impar

El slider ω (marcador) mueve un punto sobre el círculo unitario y una línea
vertical sobre los paneles de magnitud/fase; como e^{jω} es 2π-periódico,
el punto en el círculo se calcula módulo 2π aunque ω se mueva fuera de
[-π,π), reforzando visualmente la relación DTFT ↔ transformada Z (evaluar
H(z) sobre |z|=1).

A qué clase sirve
------------------
C27 (DTFT: definición, propiedades, relación con Z, U7.1) del curso
IEE2103.

Dependencias: solo numpy y matplotlib.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons


# ---------------------------------------------------------------------------
# 1. Funciones puras de cálculo
# ---------------------------------------------------------------------------

def senal_pulso_rect(L, N=60):
    """x[n] = 1 para 0<=n<L, 0 en el resto. Devuelve (n, x) con n=0..N-1."""
    n = np.arange(0, N)
    x = np.where(n < L, 1.0, 0.0)
    return n, x


def senal_exponencial_causal(a, N=500):
    """x[n] = a^n u[n]. Se usa N grande para que la suma trunca truncada
    aproxime bien la DTFT siempre que |a|<1 (decae geométricamente)."""
    n = np.arange(0, N)
    x = np.asarray(a, dtype=float) ** n.astype(float)
    return n, x


def senal_sinusoide_enventanada(omega0, L, N=60):
    """x[n] = cos(ω0 n) para 0<=n<L, 0 en el resto."""
    n = np.arange(0, N)
    x = np.where(n < L, np.cos(omega0 * n), 0.0)
    return n, x


def dtft(x, n_indices, omega):
    """
    DTFT evaluada por suma directa:  X(ω) = Σ_n x[n] e^{-jωn}
    x, n_indices: arreglos de igual largo (muestras y sus índices n).
    omega: arreglo de frecuencias donde evaluar.
    Devuelve un arreglo complejo del mismo largo que omega.
    """
    n_indices = np.asarray(n_indices, dtype=float)
    x = np.asarray(x, dtype=float)
    omega = np.asarray(omega, dtype=float)
    # Matriz (len(omega) x len(n)) de exponenciales; vectorizado con outer.
    fase = np.outer(omega, n_indices)
    W = np.exp(-1j * fase)
    return W @ x


def kernel_dirichlet(omega, L):
    """
    Forma cerrada de la DTFT de un pulso rectangular causal de largo L:
        X(ω) = e^{-jω(L-1)/2} · sin(ωL/2) / sin(ω/2)
    Se usa solo para verificación numérica (no la usa la GUI).
    """
    omega = np.asarray(omega, dtype=float)
    num = np.sin(omega * L / 2.0)
    den = np.sin(omega / 2.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        mag = np.where(np.abs(den) > 1e-12, np.abs(num / den), L)
    return mag


# ---------------------------------------------------------------------------
# 2. Configuración de señales disponibles
# ---------------------------------------------------------------------------

SENAL_RECT = "Pulso rectangular"
SENAL_EXP = "Exponencial causal aⁿu[n]"
SENAL_SIN = "Sinusoide enventanada"
NOMBRES_SENALES = [SENAL_RECT, SENAL_EXP, SENAL_SIN]

N_DISPLAY = 40      # muestras mostradas en el stem de x[n]
N_OMEGA = 2000       # resolución de la grilla de frecuencia
OMEGA_RANGE = (-3 * np.pi, 3 * np.pi)


# ---------------------------------------------------------------------------
# 3. Estado y widgets de la GUI
# ---------------------------------------------------------------------------

fig = None
ax_stem = None
ax_circulo = None
ax_mag = None
ax_fase = None

slider_L = None
slider_a = None
slider_omega0 = None
slider_omega_pt = None
radio_senal = None


def _senal_actual():
    """Devuelve (n_calc, x_calc, n_disp, x_disp, titulo) según la señal y
    sliders vigentes. n_calc/x_calc son los usados para la DTFT (pueden ser
    más largos que lo desplegado, p.ej. para la exponencial causal)."""
    nombre = radio_senal.value_selected
    L = int(round(slider_L.val))
    a = slider_a.val
    omega0 = slider_omega0.val * np.pi  # el slider guarda ω0/π

    if nombre == SENAL_RECT:
        n_calc, x_calc = senal_pulso_rect(L, N=max(N_DISPLAY, L + 5))
        titulo = f"x[n] = rect, L={L}"
    elif nombre == SENAL_EXP:
        n_calc, x_calc = senal_exponencial_causal(a, N=500)
        titulo = f"x[n] = ({a:.2f})ⁿ u[n]"
    else:
        n_calc, x_calc = senal_sinusoide_enventanada(omega0, L, N=max(N_DISPLAY, L + 5))
        titulo = f"x[n] = cos({omega0/np.pi:.2f}π n)·rect_{L}[n]"

    n_disp = n_calc[:N_DISPLAY]
    x_disp = x_calc[:N_DISPLAY]
    return n_calc, x_calc, n_disp, x_disp, titulo


def actualizar(_=None):
    n_calc, x_calc, n_disp, x_disp, titulo = _senal_actual()

    omega = np.linspace(OMEGA_RANGE[0], OMEGA_RANGE[1], N_OMEGA)
    X = dtft(x_calc, n_calc, omega)
    mag = np.abs(X)
    fase = np.angle(X)

    omega_pt = slider_omega_pt.val
    X_pt = dtft(x_calc, n_calc, np.array([omega_pt]))[0]
    # Ángulo equivalente en (-π, π] para el punto en el círculo unitario
    # (e^{jω} es 2π-periódico aunque ω se mueva fuera de un periodo).
    angulo_circ = np.mod(omega_pt + np.pi, 2 * np.pi) - np.pi

    # --- Panel 1: x[n] ---
    ax_stem.cla()
    ax_stem.stem(n_disp, x_disp, linefmt="tab:blue", markerfmt="bo", basefmt="k-")
    ax_stem.set_title(titulo, fontsize=10)
    ax_stem.set_xlabel("n")
    ax_stem.set_ylabel("x[n]")
    ax_stem.grid(True, alpha=0.3)

    # --- Panel 2: círculo unitario y el punto e^{jω} ---
    ax_circulo.cla()
    theta = np.linspace(0, 2 * np.pi, 200)
    ax_circulo.plot(np.cos(theta), np.sin(theta), "k--", lw=1, alpha=0.6)
    ax_circulo.plot([0, np.cos(angulo_circ)], [0, np.sin(angulo_circ)], "tab:red", lw=1.5)
    ax_circulo.plot([np.cos(angulo_circ)], [np.sin(angulo_circ)], "o", color="tab:red", ms=9)
    ax_circulo.annotate(r"$e^{j\omega}$", (np.cos(angulo_circ), np.sin(angulo_circ)),
                        textcoords="offset points", xytext=(8, 8), color="tab:red")
    ax_circulo.set_title(f"z-plano: |z|=1, ω={omega_pt/np.pi:.2f}π\n|X|={np.abs(X_pt):.2f}, ∠X={np.angle(X_pt):.2f} rad",
                         fontsize=9)
    ax_circulo.set_xlim(-1.4, 1.4)
    ax_circulo.set_ylim(-1.4, 1.4)
    ax_circulo.set_aspect("equal")
    ax_circulo.axhline(0, color="gray", lw=0.5)
    ax_circulo.axvline(0, color="gray", lw=0.5)
    ax_circulo.grid(True, alpha=0.3)

    # --- Panel 3: magnitud, con periodicidad 2π marcada ---
    ax_mag.cla()
    ax_mag.plot(omega, mag, color="tab:blue", lw=1.5)
    ax_mag.axvline(omega_pt, color="tab:red", ls=":", lw=1.5)
    ax_mag.plot([omega_pt], [np.abs(X_pt)], "o", color="tab:red", ms=7, zorder=5)
    for k in (-2, -1, 0, 1, 2):
        ax_mag.axvline(k * np.pi, color="gray", ls="--", lw=0.6, alpha=0.6)
    for k in (-1, 0, 1):
        centro = 2 * k * np.pi
        if OMEGA_RANGE[0] <= centro <= OMEGA_RANGE[1]:
            etiqueta = "réplica" if k != 0 else "periodo fund."
            ax_mag.annotate(etiqueta, (centro, 0),
                            xytext=(centro, -0.12 * max(mag.max(), 1e-9)),
                            textcoords="data", ha="center", fontsize=8, color="dimgray")
    ax_mag.set_title(r"$|X(e^{j\omega})|$  —  periódica en ω con período $2\pi$ (simetría par si x[n] real)")
    ax_mag.set_xlabel("ω [rad]")
    ax_mag.set_xticks([k * np.pi for k in range(-3, 4)])
    ax_mag.set_xticklabels([f"{k}π" if k != 0 else "0" for k in range(-3, 4)])
    ax_mag.grid(True, alpha=0.3)
    ax_mag.set_xlim(OMEGA_RANGE)
    ax_mag.set_ylim(bottom=-0.20 * max(mag.max(), 1e-9))

    # --- Panel 4: fase, con anotación de simetría impar ---
    ax_fase.cla()
    ax_fase.plot(omega, fase, color="tab:green", lw=1.5)
    ax_fase.axvline(omega_pt, color="tab:red", ls=":", lw=1.5)
    ax_fase.plot([omega_pt], [np.angle(X_pt)], "o", color="tab:red", ms=7, zorder=5)
    for k in (-2, -1, 0, 1, 2):
        ax_fase.axvline(k * np.pi, color="gray", ls="--", lw=0.6, alpha=0.6)
    ax_fase.axhline(0, color="gray", lw=0.6)
    ax_fase.set_title(r"$\angle X(e^{j\omega})$  —  antisimétrica: $\angle X(-\omega) = -\angle X(\omega)$ (x[n] real)")
    ax_fase.set_xlabel("ω [rad]")
    ax_fase.set_ylabel("fase [rad]")
    ax_fase.set_xticks([k * np.pi for k in range(-3, 4)])
    ax_fase.set_xticklabels([f"{k}π" if k != 0 else "0" for k in range(-3, 4)])
    ax_fase.grid(True, alpha=0.3)
    ax_fase.set_xlim(OMEGA_RANGE)

    fig.canvas.draw_idle()


def _on_cambio_senal(_label):
    actualizar()


# ---------------------------------------------------------------------------
# 4. Construcción de la figura
# ---------------------------------------------------------------------------

def setup_interactive_plot():
    global fig, ax_stem, ax_circulo, ax_mag, ax_fase
    global slider_L, slider_a, slider_omega0, slider_omega_pt, radio_senal

    fig = plt.figure(figsize=(12, 10))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 1.0])
    ax_stem = fig.add_subplot(gs[0, 0])
    ax_circulo = fig.add_subplot(gs[0, 1])
    ax_mag = fig.add_subplot(gs[1, :])
    ax_fase = fig.add_subplot(gs[2, :])

    plt.subplots_adjust(left=0.08, right=0.97, top=0.93, bottom=0.30, hspace=0.55, wspace=0.30)
    fig.suptitle("DTFT: X(e^{jω}) = Σ x[n] e^{-jωn}  —  periodicidad 2π y relación con el plano z",
                 fontsize=12)

    ax_slider_L = plt.axes([0.10, 0.20, 0.55, 0.025])
    slider_L = Slider(ax=ax_slider_L, label="L", valmin=1, valmax=25, valinit=8, valstep=1)
    slider_L.on_changed(actualizar)

    ax_slider_a = plt.axes([0.10, 0.16, 0.55, 0.025])
    slider_a = Slider(ax=ax_slider_a, label="a", valmin=-0.95, valmax=0.95, valinit=0.7, valstep=0.01)
    slider_a.on_changed(actualizar)

    ax_slider_omega0 = plt.axes([0.10, 0.12, 0.55, 0.025])
    slider_omega0 = Slider(ax=ax_slider_omega0, label=r"$\omega_0/\pi$", valmin=0.0, valmax=1.0,
                           valinit=0.25, valstep=1 / 64)
    # Guardamos omega0 en radianes reales; usamos una envoltura para la conversión.
    def _on_omega0(val_norm):
        actualizar()
    slider_omega0.on_changed(_on_omega0)

    ax_slider_wpt = plt.axes([0.10, 0.06, 0.55, 0.025])
    slider_omega_pt = Slider(ax=ax_slider_wpt, label=r"$\omega$ (marcador)", valmin=OMEGA_RANGE[0],
                             valmax=OMEGA_RANGE[1], valinit=0.0)
    slider_omega_pt.on_changed(actualizar)

    ax_radio = plt.axes([0.72, 0.04, 0.24, 0.20])
    radio_senal = RadioButtons(ax_radio, NOMBRES_SENALES, active=0)
    radio_senal.on_clicked(_on_cambio_senal)

    actualizar()
    return fig


if __name__ == "__main__":
    figura = setup_interactive_plot()
    plt.show()
