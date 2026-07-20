# -*- coding: utf-8 -*-
"""
demo_convolucion.py — Convolución paso a paso: flip / slide / multiply / integrate
====================================================================================

Qué ilustra
-----------
El procedimiento gráfico clásico para calcular y(t) = (x * h)(t):

    1. Se refleja h(τ) respecto del eje vertical  ->  h(-τ)
    2. Se desplaza en t                            ->  h(t - τ)
    3. Se multiplica punto a punto por x(τ)        ->  x(τ)·h(t-τ)
    4. Se integra (o suma, en el caso discreto) el producto sobre τ (o n)
       para obtener el valor y(t) (o y[n]).

La figura muestra tres paneles sincronizados por un slider de t (o de n en el
modo discreto):

    - Panel superior : x(τ) y h(t-τ) (la copia espejada y desplazada de h)
    - Panel medio    : el producto x(τ)·h(t-τ) con el área bajo la curva
                       sombreada (o los stems del producto en el caso discreto)
    - Panel inferior : y(t) construyéndose hasta el instante actual, con un
                       punto marcando el valor y(t) recién calculado.

Un selector de pares (RadioButtons) permite cambiar entre:
    - rect * rect                 (da un triángulo — el ejemplo canónico)
    - rect * exponencial causal
    - exponencial * exponencial
    - modo discreto x[n] * h[n]   (stems, suma en vez de integral)

Un botón "Animar" barre t automáticamente para ver la convolución "correr".

A qué clase sirve
------------------
C6 (LTI ⇒ convolución, derivación conceptual, U2.2) y, sobre todo, C7
(convolución analítica y gráfica, U2.3) del curso IEE2103. El caso rect*rect
es el ejemplo de pizarra estándar (Oppenheim) que da un triángulo; sirve para
que el estudiante verifique "a mano" el resultado que la demo calcula
numéricamente.

Dependencias: solo numpy y matplotlib.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons, Button


# ---------------------------------------------------------------------------
# 1. Funciones puras de cálculo (sin dependencia de matplotlib)
# ---------------------------------------------------------------------------

def rect(t, width=1.0, start=0.0):
    """Pulso rectangular unitario en [start, start+width)."""
    t = np.asarray(t, dtype=float)
    return np.where((t >= start) & (t < start + width), 1.0, 0.0)


def exp_causal(t, a=1.0, start=0.0):
    """Exponencial causal exp(-a (t-start)) u(t-start)."""
    t = np.asarray(t, dtype=float)
    out = np.zeros_like(t)
    mask = t >= start
    out[mask] = np.exp(-a * (t[mask] - start))
    return out


def convolucion_continua_en_t(x_func, h_func, t, tau_grid):
    """
    Evalúa y(t) = ∫ x(τ) h(t-τ) dτ para un único instante t, integrando
    numéricamente (regla del trapecio) sobre una grilla fina tau_grid.
    """
    integrando = x_func(tau_grid) * h_func(t - tau_grid)
    return float(np.trapz(integrando, tau_grid))


def curva_convolucion_continua(x_func, h_func, t_values, tau_grid):
    """y(t) evaluado en varios instantes t_values (para la curva 'construida')."""
    return np.array([convolucion_continua_en_t(x_func, h_func, t, tau_grid) for t in t_values])


def convolucion_discreta(x, h):
    """
    Convolución discreta lineal completa, calculada explícitamente como una
    suma (equivalente en resultado a np.convolve(x, h, mode='full')).
    y[n] = sum_k x[k] h[n-k],  n = 0 .. len(x)+len(h)-2
    """
    x = np.asarray(x, dtype=float)
    h = np.asarray(h, dtype=float)
    Nx, Nh = len(x), len(h)
    y = np.zeros(Nx + Nh - 1)
    for n in range(len(y)):
        s = 0.0
        for k in range(Nx):
            m = n - k
            if 0 <= m < Nh:
                s += x[k] * h[m]
        y[n] = s
    return y


# ---------------------------------------------------------------------------
# 2. Definición de los pares (x, h) disponibles en el selector
# ---------------------------------------------------------------------------

PARES_CONTINUOS = {
    "rect * rect (→ triángulo)": dict(
        x=lambda t: rect(t, width=1.0, start=0.0),
        h=lambda t: rect(t, width=1.0, start=0.0),
        t_range=(-0.5, 2.5),
        tau_range=(-1.0, 3.0),
        x_label=r"$x(\tau)=\mathrm{rect}(\tau),\ \tau\in[0,1)$",
        h_label=r"$h(\tau)=\mathrm{rect}(\tau),\ \tau\in[0,1)$",
    ),
    "rect * exponencial": dict(
        x=lambda t: rect(t, width=1.0, start=0.0),
        h=lambda t: exp_causal(t, a=1.5, start=0.0),
        t_range=(-0.5, 4.0),
        tau_range=(-1.0, 5.0),
        x_label=r"$x(\tau)=\mathrm{rect}(\tau)$",
        h_label=r"$h(\tau)=e^{-1.5\tau}u(\tau)$",
    ),
    "exponencial * exponencial": dict(
        x=lambda t: exp_causal(t, a=1.0, start=0.0),
        h=lambda t: exp_causal(t, a=2.0, start=0.0),
        t_range=(-0.5, 5.0),
        tau_range=(-1.0, 6.0),
        x_label=r"$x(\tau)=e^{-\tau}u(\tau)$",
        h_label=r"$h(\tau)=e^{-2\tau}u(\tau)$",
    ),
}

MODO_DISCRETO_LABEL = "discreto: x[n] * h[n] (suma)"

# Secuencias discretas de ejemplo (fijas, ilustrativas)
DISCRETO_X = np.array([1.0, 1.0, 1.0, 1.0, 1.0])       # rect de largo 5
DISCRETO_H = np.array([1.0, 0.7, 0.4, 0.2])              # decaimiento simple

NOMBRES_PARES = list(PARES_CONTINUOS.keys()) + [MODO_DISCRETO_LABEL]

N_TAU = 2000     # resolución de la grilla de integración
N_T_CURVA = 300  # resolución de la curva y(t) "construida"


# ---------------------------------------------------------------------------
# 3. Estado y widgets de la GUI (matplotlib puro, estilo interactive_sinusoids)
# ---------------------------------------------------------------------------

fig = None
ax_top = None
ax_mid = None
ax_bot = None
slider_t = None
radio_par = None
boton_animar = None
text_valor = None

_timer = None
_animando = False

# Caché del par actualmente seleccionado
_cache = {}


def _recalcular_cache(nombre_par):
    """Precalcula lo que depende solo del par (x,h) elegido, no de t."""
    global _cache
    if nombre_par == MODO_DISCRETO_LABEL:
        y_full = convolucion_discreta(DISCRETO_X, DISCRETO_H)
        _cache = dict(
            discreto=True,
            x=DISCRETO_X, h=DISCRETO_H, y_full=y_full,
            n_min=0, n_max=len(y_full) - 1,
        )
    else:
        info = PARES_CONTINUOS[nombre_par]
        tau_grid = np.linspace(info["tau_range"][0], info["tau_range"][1], N_TAU)
        t_values = np.linspace(info["t_range"][0], info["t_range"][1], N_T_CURVA)
        y_curva = curva_convolucion_continua(info["x"], info["h"], t_values, tau_grid)
        _cache = dict(
            discreto=False,
            x_func=info["x"], h_func=info["h"],
            tau_grid=tau_grid, t_values=t_values, y_curva=y_curva,
            t_range=info["t_range"], tau_range=info["tau_range"],
            x_label=info["x_label"], h_label=info["h_label"],
        )


def _actualizar_continuo(t_val):
    info = _cache
    tau = info["tau_grid"]
    x_tau = info["x_func"](tau)
    h_t_menos_tau = info["h_func"](t_val - tau)
    producto = x_tau * h_t_menos_tau
    y_ahora = convolucion_continua_en_t(info["x_func"], info["h_func"], t_val, tau)

    # Panel superior: x(τ) y h(t-τ)
    ax_top.cla()
    ax_top.plot(tau, x_tau, color="tab:blue", lw=2, label=info["x_label"])
    ax_top.plot(tau, h_t_menos_tau, color="tab:orange", lw=2, label=r"$h(t-\tau)$")
    ax_top.axvline(t_val, color="gray", ls=":", lw=1)
    ax_top.set_title(f"Reflejar y desplazar  (t = {t_val:.2f})")
    ax_top.set_xlabel(r"$\tau$")
    ax_top.legend(loc="upper right", fontsize=9)
    ax_top.grid(True, alpha=0.3)
    ax_top.set_xlim(info["tau_range"])

    # Panel medio: producto, área sombreada
    ax_mid.cla()
    ax_mid.plot(tau, producto, color="tab:green", lw=1.5)
    ax_mid.fill_between(tau, 0, producto, color="tab:green", alpha=0.35)
    ax_mid.set_title(rf"Multiplicar e integrar:  $y(t)=\int x(\tau)h(t-\tau)\,d\tau = {y_ahora:.3f}$")
    ax_mid.set_xlabel(r"$\tau$")
    ax_mid.grid(True, alpha=0.3)
    ax_mid.set_xlim(info["tau_range"])

    # Panel inferior: y(t) construyéndose
    ax_bot.cla()
    t_values, y_curva = info["t_values"], info["y_curva"]
    mask = t_values <= t_val
    ax_bot.plot(t_values, y_curva, color="lightgray", lw=1, ls="--", label="y(t) completa")
    ax_bot.plot(t_values[mask], y_curva[mask], color="tab:purple", lw=2, label="y(t) construida")
    ax_bot.plot([t_val], [y_ahora], "o", color="tab:red", ms=8, zorder=5)
    ax_bot.set_title("Resultado de la convolución  y(t)")
    ax_bot.set_xlabel("t")
    ax_bot.legend(loc="upper right", fontsize=9)
    ax_bot.grid(True, alpha=0.3)
    ax_bot.set_xlim(info["t_range"])


def _actualizar_discreto(n_val):
    info = _cache
    x, h = info["x"], info["h"]
    n = int(round(n_val))
    Nx, Nh = len(x), len(h)
    k_min, k_max = -Nh, Nx + Nh
    k = np.arange(k_min, k_max)

    x_k = np.zeros_like(k, dtype=float)
    x_k[(k >= 0) & (k < Nx)] = x[k[(k >= 0) & (k < Nx)]]

    m = n - k  # índice de h que corresponde a h[n-k]
    h_nk = np.zeros_like(k, dtype=float)
    valid = (m >= 0) & (m < Nh)
    h_nk[valid] = h[m[valid]]

    producto = x_k * h_nk
    y_ahora = float(np.sum(producto))

    ax_top.cla()
    ax_top.stem(k, x_k, linefmt="tab:blue", markerfmt="bo", basefmt=" ", label="x[k]")
    markerline, stemlines, baseline = ax_top.stem(
        k, h_nk, linefmt="tab:orange", markerfmt="o", basefmt=" ", label="h[n-k]"
    )
    plt.setp(markerline, color="tab:orange")
    ax_top.set_title(f"Reflejar y desplazar h  (n = {n})")
    ax_top.set_xlabel("k")
    ax_top.legend(loc="upper right", fontsize=9)
    ax_top.grid(True, alpha=0.3)

    ax_mid.cla()
    ax_mid.stem(k, producto, linefmt="tab:green", markerfmt="go", basefmt=" ")
    ax_mid.set_title(rf"Multiplicar y sumar:  $y[n]=\sum_k x[k]h[n-k] = {y_ahora:.3f}$")
    ax_mid.set_xlabel("k")
    ax_mid.grid(True, alpha=0.3)

    ax_bot.cla()
    y_full = info["y_full"]
    n_full = np.arange(len(y_full))
    mask = n_full <= n
    ax_bot.stem(n_full, y_full, linefmt="lightgray", markerfmt=" ", basefmt=" ")
    ax_bot.stem(n_full[mask], y_full[mask], linefmt="tab:purple", markerfmt="o", basefmt=" ")
    ax_bot.plot([n], [y_ahora], "o", color="tab:red", ms=9, zorder=5)
    ax_bot.set_title("Resultado y[n] (= np.convolve(x,h))")
    ax_bot.set_xlabel("n")
    ax_bot.grid(True, alpha=0.3)


def actualizar(_=None):
    """Callback único que redibuja los 3 paneles según el slider y el par elegido."""
    if _cache.get("discreto"):
        _actualizar_discreto(slider_t.val)
    else:
        _actualizar_continuo(slider_t.val)
    fig.canvas.draw_idle()


def _on_cambio_par(nombre_par):
    _detener_animacion()
    _recalcular_cache(nombre_par)
    if _cache["discreto"]:
        slider_t.valmin = _cache["n_min"]
        slider_t.valmax = _cache["n_max"]
        slider_t.valstep = 1
        slider_t.ax.set_xlim(_cache["n_min"], _cache["n_max"])
        slider_t.label.set_text("n")
        nuevo_val = _cache["n_min"]
    else:
        slider_t.valmin = _cache["t_range"][0]
        slider_t.valmax = _cache["t_range"][1]
        slider_t.valstep = None
        slider_t.ax.set_xlim(_cache["t_range"])
        slider_t.label.set_text("t")
        nuevo_val = _cache["t_range"][0]
    slider_t.set_val(nuevo_val)
    actualizar()


def _paso_animacion():
    if not _animando:
        return
    paso = 1 if _cache.get("discreto") else (slider_t.valmax - slider_t.valmin) / 150.0
    nuevo = slider_t.val + paso
    if nuevo > slider_t.valmax:
        nuevo = slider_t.valmin
    slider_t.set_val(nuevo)


def _detener_animacion():
    global _animando
    _animando = False
    if boton_animar is not None:
        boton_animar.label.set_text("Animar")


def _on_click_animar(_event):
    global _animando
    _animando = not _animando
    boton_animar.label.set_text("Detener" if _animando else "Animar")
    if _animando and _timer is not None:
        _timer.start()


# ---------------------------------------------------------------------------
# 4. Construcción de la figura (no llama a plt.show(); eso lo hace __main__)
# ---------------------------------------------------------------------------

def setup_interactive_plot():
    global fig, ax_top, ax_mid, ax_bot, slider_t, radio_par, boton_animar, _timer

    fig = plt.figure(figsize=(10, 10))
    ax_top = fig.add_subplot(3, 1, 1)
    ax_mid = fig.add_subplot(3, 1, 2)
    ax_bot = fig.add_subplot(3, 1, 3)
    plt.subplots_adjust(left=0.10, right=0.97, top=0.93, bottom=0.28, hspace=0.55)

    fig.suptitle("Convolución paso a paso: reflejar, desplazar, multiplicar, integrar/sumar",
                 fontsize=13)

    ax_slider_t = plt.axes([0.12, 0.14, 0.60, 0.03])
    slider_t = Slider(ax=ax_slider_t, label="t", valmin=-0.5, valmax=2.5, valinit=-0.5)
    slider_t.on_changed(actualizar)

    ax_radio = plt.axes([0.76, 0.03, 0.23, 0.24])
    radio_par = RadioButtons(ax_radio, NOMBRES_PARES, active=0)
    for lbl in radio_par.labels:
        lbl.set_fontsize(8)
    radio_par.on_clicked(_on_cambio_par)

    ax_boton = plt.axes([0.12, 0.05, 0.15, 0.05])
    boton_animar = Button(ax_boton, "Animar")
    boton_animar.on_clicked(_on_click_animar)

    _timer = fig.canvas.new_timer(interval=60)
    _timer.add_callback(_paso_animacion)
    _timer.start()

    _recalcular_cache(NOMBRES_PARES[0])
    slider_t.valmin = _cache["t_range"][0]
    slider_t.valmax = _cache["t_range"][1]
    slider_t.ax.set_xlim(_cache["t_range"])
    slider_t.set_val(_cache["t_range"][0])
    actualizar()

    return fig


if __name__ == "__main__":
    figura = setup_interactive_plot()
    plt.show()
