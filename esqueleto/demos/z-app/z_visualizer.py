"""
Visualizador y Diseñador de Sistemas en el Dominio Z
=====================================================

Análogo discreto de `laplace_visualizer.py` (módulo 5). Mismo espíritu:
una app Tkinter + matplotlib donde el plano complejo (aquí, el plano z
con el círculo unitario) es un lienzo interactivo. Se arrastran polos
(X) y ceros (O) con el mouse y se observa en vivo el efecto en:

  - |H(e^{jw})| y su fase, para w en [-pi, pi]  (geometría -> respuesta
    en frecuencia: C25, U6.3/U6.5)
  - h[n], la respuesta al impulso (causal), con indicador de
    estabilidad (¿todos los polos dentro del círculo unitario?)

Incluye presets de diseño de filtros por polos/ceros (notch, peine,
primer orden, resonador) para la clase C26 (U6.6).

Dependencias: SOLO numpy, matplotlib y tkinter (biblioteca estándar).
No se usa scipy ni sympy: los coeficientes H(z) = B(z)/A(z) que arma
esta app son directamente compatibles con `scipy.signal.freqz`/`lfilter`
por si los estudiantes quieren verificar después (ver botón
"Copiar b, a para scipy").

-----------------------------------------------------------------------
Convención matemática usada (IMPORTANTE, léase antes de tocar el código)
-----------------------------------------------------------------------
Un punto z_k marcado como CERO o POLO define, respectivamente, un factor
(1 - z_k * z^-1) en el numerador o denominador de H(z), es decir:

    H(z) = K * prod_k (1 - z_k * z^-1)
               ---------------------------
               prod_k (1 - p_k * z^-1)

Esta es exactamente la convención de scipy/MATLAB para (b, a): b y a son
los coeficientes de B(z) y A(z) como polinomios en z^-1 (b[0], a[0] son
los términos sin retardo). Con ella, un solo polo en r y ningún cero da
H(z) = 1/(1 - r z^-1), cuya respuesta al impulso es h[n] = r^n para
n >= 0 (el caso de prueba clásico), SIN retardo espurio. Es distinto de
escribir H(z) = z^N(...)/z^D(...) como polinomios monicos en z positivo
(la convención de `numpy.poly` "cruda"), que introduce un retardo si
hay menos ceros que polos. Usamos la primera porque es la que importa
para la respuesta al impulso y es la que entienden los estudiantes
cuando ven H(z) escrito con potencias negativas de z.

La MAGNITUD |H(e^{jw})| es idéntica bajo ambas convenciones (el factor
que las diferencia tiene módulo 1 sobre el círculo unitario), así que
la interpretación geométrica clásica sigue siendo válida:

    |H(e^{jw})| = |K| * prod(distancias de e^{jw} a cada CERO)
                        -----------------------------------------
                        prod(distancias de e^{jw} a cada POLO)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import messagebox

IMPULSE_N = 40           # muestras de h[n] a mostrar
SELECT_RADIUS = 0.12     # radio (en el plano z) para "agarrar" un polo/cero
ZPLANE_LIM = 1.6         # límite de los ejes del plano z

_SUP = {"0": "⁰", "1": "¹", "2": "²", "3": "³",
        "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷",
        "8": "⁸", "9": "⁹", "-": "⁻"}


def _sup(n):
    return "".join(_SUP[ch] for ch in str(n))


# =====================================================================
# ===================  LÓGICA DE CÁLCULO (sin Tkinter)  =============
# =====================================================================

def conj_pair(z, tol=1e-9):
    """Dado un punto z, retorna [z] si es real, o [z, conj(z)] si no."""
    z = complex(z)
    if abs(z.imag) < tol:
        return [complex(round(z.real, 9), 0.0)]
    return [z, z.conjugate()]


def _clean(arr, tol=1e-6):
    """Convierte a real si la parte imaginaria es despreciable (esperado
    cuando polos/ceros vienen en pares conjugados)."""
    arr = np.asarray(arr)
    if np.iscomplexobj(arr):
        max_imag = float(np.max(np.abs(arr.imag))) if arr.size else 0.0
        max_real = float(np.max(np.abs(arr.real))) if arr.size else 1.0
        if max_imag < tol * max(1.0, max_real):
            return arr.real.astype(float)
    return arr.astype(float)


def tf_from_zpk(zeros, poles, gain=1.0):
    """Construye (b, a), los coeficientes de H(z) = B(z)/A(z) como
    polinomios en z^-1 (b[0], a[0] = términos sin retardo), a partir de
    listas de ceros/polos y una ganancia K. Ver docstring del módulo.
    """
    if len(zeros) == 0:
        b = np.array([gain], dtype=complex)
    else:
        b = gain * np.poly(list(zeros)).astype(complex)
    if len(poles) == 0:
        a = np.array([1.0], dtype=complex)
    else:
        a = np.poly(list(poles)).astype(complex)
    return _clean(b), _clean(a)


def freq_response(b, a, n_points=800, omega=None):
    """Evalúa H(e^{jw}) para w en [-pi, pi] (o el arreglo `omega` dado)."""
    if omega is None:
        omega = np.linspace(-np.pi, np.pi, n_points)
    zinv = np.exp(-1j * omega)
    b = np.asarray(b, dtype=complex)
    a = np.asarray(a, dtype=complex)
    B = np.polyval(b[::-1], zinv)
    A = np.polyval(a[::-1], zinv)
    with np.errstate(divide="ignore", invalid="ignore"):
        H = B / A
    mask = np.abs(A) < 1e-10
    H = np.where(mask, np.nan + 1j * np.nan, H)
    return omega, H


def impulse_response(b, a, N=IMPULSE_N):
    """Respuesta al impulso h[n], n=0..N-1, asumiendo el sistema causal
    definido por la ecuación en diferencias de (b, a):

        y[n] = sum_k b[k] x[n-k] - sum_{k>=1} a[k] y[n-k]   (todo / a[0])
    """
    b = np.asarray(b, dtype=float)
    a = np.asarray(a, dtype=float)
    x = np.zeros(N)
    x[0] = 1.0
    y = np.zeros(N)
    a0 = a[0]
    for n in range(N):
        acc = 0.0
        for k in range(min(len(b), n + 1)):
            acc += b[k] * x[n - k]
        for k in range(1, min(len(a), n + 1)):
            acc -= a[k] * y[n - k]
        y[n] = acc / a0
    return y


def is_stable(poles):
    """Estable (BIBO, sistema causal) sii todos los polos están
    estrictamente dentro del círculo unitario. Sin polos -> FIR -> siempre
    estable."""
    if len(poles) == 0:
        return True
    return bool(np.all(np.abs(np.asarray(poles)) < 1.0))


def geometric_magnitude(zeros, poles, gain, omega0):
    """|H(e^{j w0})| calculada como producto de distancias (la lectura
    geométrica de C25), para contrastar contra freq_response()."""
    zpt = np.exp(1j * omega0)
    num = abs(gain)
    for zk in zeros:
        num *= abs(zpt - zk)
    den = 1.0
    for pk in poles:
        den *= abs(zpt - pk)
    if den < 1e-12:
        return np.inf
    return num / den


def _poly_str(coeffs, tol=1e-9):
    parts = []
    for k, c in enumerate(coeffs):
        if abs(c) < tol:
            continue
        sign = "+" if c >= 0 else "-"
        mag = abs(c)
        term = f"{mag:.4g}" if k == 0 else f"{mag:.4g}·z{_sup('-' + str(k))}"
        parts.append((sign, term))
    if not parts:
        return "0"
    s = parts[0][1] if parts[0][0] == "+" else f"-{parts[0][1]}"
    for sign, term in parts[1:]:
        s += f" {sign} {term}"
    return s


def format_tf_string(b, a):
    return f"H(z) = ({_poly_str(b)}) / ({_poly_str(a)})"


# ---------------------------------------------------------------------
# Presets de diseño (C26 / U6.6)
# ---------------------------------------------------------------------

def normalize_gain_peak(zeros, poles, n_points=2000):
    """Ganancia K tal que max_w |H(e^{jw})| == 1 (útil para que los
    presets de notch/peine/resonador queden con paso ~1)."""
    b, a = tf_from_zpk(zeros, poles, 1.0)
    _, H = freq_response(b, a, n_points)
    peak = float(np.nanmax(np.abs(H)))
    return 1.0 / peak if peak > 1e-12 else 1.0


def preset_notch(f0, fs, r):
    """Notch: ceros sobre el círculo unitario en +-w0 (anulan esa
    frecuencia exactamente); polos en r*e^{+-jw0} (r<1) para angostar
    la muesca sin tocar el resto del espectro."""
    w0 = 2 * np.pi * f0 / fs
    zeros = conj_pair(np.exp(1j * w0))
    poles = conj_pair(r * np.exp(1j * w0))
    gain = normalize_gain_peak(zeros, poles)
    return zeros, poles, gain


def preset_comb(N, r):
    """Peine: ceros en las N raíces N-ésimas de la unidad -> H(z) es
    (proporcional a) 1 - z^-N, que anula w_k = 2*pi*k/N para
    k=0..N-1. Con r>0 se agregan polos en r*(mismas raíces) para
    angostar cada diente (IIR comb)."""
    N = int(round(N))
    angles = [2 * np.pi * k / N for k in range(N)]
    zeros = [np.exp(1j * a) for a in angles]
    poles = [r * np.exp(1j * a) for a in angles] if r > 1e-9 else []
    gain = normalize_gain_peak(zeros, poles) if poles else 1.0
    return zeros, poles, gain


def preset_lowpass1(r):
    """Pasa bajos de primer orden: H(z) = (1-r)/(1 - r z^-1). Ganancia
    DC exacta = 1."""
    zeros = []
    poles = [complex(r, 0.0)]
    gain = 1.0 - r
    return zeros, poles, gain


def preset_highpass1(r):
    """Pasa altos de primer orden: cero en z=1 (mata DC), polo en r.
    Ganancia elegida para que |H(e^{j pi})| = 1 (Nyquist)."""
    zeros = [complex(1.0, 0.0)]
    poles = [complex(r, 0.0)]
    gain = (1.0 + r) / 2.0
    return zeros, poles, gain


def preset_resonator(f0, fs, r):
    """Resonador: par de polos complejos cerca del círculo unitario en
    +-w0, sin ceros. Mientras más cerca de r=1, más angosto/selectivo
    el pico (y más lenta la caída de h[n])."""
    w0 = 2 * np.pi * f0 / fs
    poles = conj_pair(r * np.exp(1j * w0))
    zeros = []
    gain = normalize_gain_peak(zeros, poles)
    return zeros, poles, gain


PRESETS = {
    "Manual (sin preset)": None,
    "Notch (elimina f0)": {
        "params": {"f0": (1.0, 500.0, 50.0), "fs": (100.0, 2000.0, 1000.0), "r": (0.5, 0.99, 0.9)},
        "build": lambda p: preset_notch(p["f0"], p["fs"], p["r"]),
    },
    "Peine / Comb": {
        "params": {"N": (2.0, 12.0, 4.0), "r": (0.0, 0.99, 0.85)},
        "build": lambda p: preset_comb(p["N"], p["r"]),
    },
    "Pasa bajos (1er orden)": {
        "params": {"r": (0.0, 0.99, 0.7)},
        "build": lambda p: preset_lowpass1(p["r"]),
    },
    "Pasa altos (1er orden)": {
        "params": {"r": (0.0, 0.99, 0.7)},
        "build": lambda p: preset_highpass1(p["r"]),
    },
    "Resonador": {
        "params": {"f0": (1.0, 500.0, 100.0), "fs": (100.0, 2000.0, 1000.0), "r": (0.5, 0.999, 0.95)},
        "build": lambda p: preset_resonator(p["f0"], p["fs"], p["r"]),
    },
}


# =====================================================================
# ==========================  INTERFAZ (Tkinter)  ====================
# =====================================================================

class ZVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador y Diseñador de Sistemas en el Dominio Z")
        self.root.geometry("1400x880")

        self.design_poles = []   # list[complex]
        self.design_zeros = []   # list[complex]
        self.gain = 1.0

        self.dragging = False
        self.selected_index = None
        self.selected_type = None

        self.preset_name = "Manual (sin preset)"
        self.preset_params = {}

        self.omega0 = 0.4  # rad

        self.formula_var = tk.StringVar(value="H(z) = 1")
        self.select_info_var = tk.StringVar(value="Ningún punto seleccionado.")
        self.readout_var = tk.StringVar(value="")

        formula_frame = tk.Frame(root, pady=4)
        formula_frame.pack(side=tk.TOP, fill=tk.X)
        tk.Label(formula_frame, textvariable=self.formula_var, font=("Helvetica", 12, "bold")).pack()
        tk.Label(formula_frame, textvariable=self.select_info_var, font=("Helvetica", 9, "italic")).pack()

        controls_container = tk.Frame(root)
        controls_container.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.fig = plt.figure(figsize=(13, 8), tight_layout=True)
        self.z_plane_ax = self.fig.add_subplot(2, 2, 1)
        self.mag_ax = self.fig.add_subplot(2, 2, 2)
        self.h_ax = self.fig.add_subplot(2, 2, 3)
        self.phase_ax = self.fig.add_subplot(2, 2, 4)

        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas_widget = self.canvas.get_tk_widget()

        self.setup_controls(controls_container)
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.update_plots()

        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)

    # -----------------------------------------------------------------
    # Controles
    # -----------------------------------------------------------------
    def setup_controls(self, parent):
        left = tk.Frame(parent)
        left.pack(side=tk.LEFT, padx=10, fill="y", anchor="n")
        tk.Label(left, text="Preset de diseño (C26):", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.preset_var = tk.StringVar(value=self.preset_name)
        tk.OptionMenu(left, self.preset_var, *PRESETS.keys(), command=self.on_preset_change).pack(anchor="w", pady=(0, 6))
        instructions = ("Clic Izq: agrega Polo | Clic Der: agrega Cero.\n"
                         "Arrastra un polo/cero existente para moverlo.\n"
                         "Shift + arrastrar: ajusta al círculo unitario.")
        tk.Label(left, text=instructions, font=("Helvetica", 9, "italic"), justify="left").pack(anchor="w")
        tk.Button(left, text="Limpiar Diseño", command=self.clear_design).pack(anchor="w", pady=6)
        tk.Button(left, text="Copiar b, a para scipy", command=self.show_scipy_code).pack(anchor="w")

        self.param_sliders_frame = tk.Frame(parent)
        self.param_sliders_frame.pack(side=tk.LEFT, padx=15, fill="both", anchor="n")

        gain_frame = tk.Frame(parent)
        gain_frame.pack(side=tk.LEFT, padx=15, fill="y", anchor="n")
        tk.Label(gain_frame, text="Ganancia K:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.gain_slider = tk.Scale(gain_frame, from_=0.01, to=3.0, resolution=0.01, orient=tk.HORIZONTAL,
                                     length=150, command=self.on_gain_change)
        self.gain_slider.set(self.gain)
        self.gain_slider.pack(anchor="w")

        geo_frame = tk.Frame(parent)
        geo_frame.pack(side=tk.LEFT, padx=15, fill="y", anchor="n")
        self.show_vectors = tk.BooleanVar(value=False)
        tk.Checkbutton(geo_frame, text="Modo geométrico (vectores a e^{jw})",
                        variable=self.show_vectors, command=self.update_plots).pack(anchor="w")
        tk.Label(geo_frame, text="w (rad):").pack(anchor="w")
        self.omega_slider = tk.Scale(geo_frame, from_=-np.pi, to=np.pi, resolution=0.01, orient=tk.HORIZONTAL,
                                      length=200, command=self.on_omega_change)
        self.omega_slider.set(self.omega0)
        self.omega_slider.pack(anchor="w")
        tk.Label(geo_frame, textvariable=self.readout_var, font=("Helvetica", 9)).pack(anchor="w")

        self.on_preset_change(self.preset_name)

    def create_preset_sliders(self):
        for w in self.param_sliders_frame.winfo_children():
            w.destroy()
        info = PRESETS[self.preset_name]
        if info is None:
            tk.Label(self.param_sliders_frame, text="(Diseño manual: clic para agregar\npolos/ceros en el plano z)",
                     font=("Helvetica", 9, "italic"), justify="left").pack(anchor="w")
            return
        self.preset_params = {name: default for name, (_, _, default) in info["params"].items()}
        for name, (lo, hi, default) in info["params"].items():
            frame = tk.Frame(self.param_sliders_frame)
            tk.Label(frame, text=f"{name}:").pack(side=tk.LEFT)
            res = 1.0 if name == "N" else (hi - lo) / 200.0
            slider = tk.Scale(frame, from_=lo, to=hi, resolution=res, orient=tk.HORIZONTAL, length=160,
                               command=lambda val, n=name: self.on_preset_param_change(n, val))
            slider.set(default)
            slider.pack(side=tk.LEFT)
            frame.pack(anchor="w")

    # -----------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------
    def on_preset_change(self, name):
        self.preset_name = name
        self.create_preset_sliders()
        self.rebuild_from_preset()

    def on_preset_param_change(self, name, value):
        self.preset_params[name] = float(value)
        self.rebuild_from_preset()

    def rebuild_from_preset(self):
        info = PRESETS[self.preset_name]
        if info is None:
            return
        zeros, poles, gain = info["build"](self.preset_params)
        self.design_zeros = list(zeros)
        self.design_poles = list(poles)
        self.gain = gain
        self.gain_slider.set(gain)
        self.update_plots()

    def on_gain_change(self, value):
        self.gain = float(value)
        self.update_plots()

    def on_omega_change(self, value):
        self.omega0 = float(value)
        self.update_plots()

    def clear_design(self):
        self.design_poles = []
        self.design_zeros = []
        self.gain = 1.0
        self.gain_slider.set(1.0)
        self.preset_var.set("Manual (sin preset)")
        self.preset_name = "Manual (sin preset)"
        self.create_preset_sliders()
        self.update_plots()

    def show_scipy_code(self):
        b, a = tf_from_zpk(self.design_zeros, self.design_poles, self.gain)
        b_list = [round(float(x), 6) for x in b]
        a_list = [round(float(x), 6) for x in a]
        msg = (f"b = {b_list}\na = {a_list}\n\n"
               "# Verificación en Python:\n"
               "# from scipy.signal import freqz\n"
               "# w, H = freqz(b, a, worN=1024)\n"
               "# plt.plot(w, abs(H))")
        messagebox.showinfo("H(z) - coeficientes para scipy.signal", msg)

    # -----------------------------------------------------------------
    # Interacción con el mouse (arrastre de polos/ceros)
    # -----------------------------------------------------------------
    def on_press(self, event):
        if event.inaxes != self.z_plane_ax or event.xdata is None:
            return
        click = complex(event.xdata, event.ydata)
        self.selected_index = None
        self.selected_type = None
        min_dist = SELECT_RADIUS
        for i, p in enumerate(self.design_poles):
            d = abs(click - p)
            if d < min_dist:
                min_dist = d
                self.selected_index, self.selected_type = i, "pole"
        for i, z in enumerate(self.design_zeros):
            d = abs(click - z)
            if d < min_dist:
                min_dist = d
                self.selected_index, self.selected_type = i, "zero"

        if self.selected_index is not None:
            self.dragging = True
            self._update_select_readout()
        else:
            znew = complex(round(event.xdata, 3), round(event.ydata, 3))
            if event.button == 1:
                self.design_poles.append(znew)
                if abs(znew.imag) > 1e-9:
                    self.design_poles.append(znew.conjugate())
            elif event.button == 3:
                self.design_zeros.append(znew)
                if abs(znew.imag) > 1e-9:
                    self.design_zeros.append(znew.conjugate())
            self.update_plots()

    def on_motion(self, event):
        if not self.dragging or event.inaxes != self.z_plane_ax or event.xdata is None:
            return
        znew = complex(round(event.xdata, 3), round(event.ydata, 3))
        if event.key == "shift" and abs(znew) > 1e-9:
            znew = znew / abs(znew)
        lst = self.design_poles if self.selected_type == "pole" else self.design_zeros
        old = lst[self.selected_index]
        lst[self.selected_index] = znew
        if abs(old.imag) > 1e-9:
            try:
                idx = lst.index(old.conjugate())
                lst[idx] = znew.conjugate()
            except ValueError:
                pass
        self._update_select_readout(znew)
        self.update_plots()

    def on_release(self, event):
        self.dragging = False
        self.selected_index = None
        self.selected_type = None
        self.select_info_var.set("Ningún punto seleccionado.")

    def _update_select_readout(self, z=None):
        if z is None:
            lst = self.design_poles if self.selected_type == "pole" else self.design_zeros
            z = lst[self.selected_index]
        r, theta = abs(z), np.angle(z)
        etiqueta = "Polo" if self.selected_type == "pole" else "Cero"
        self.select_info_var.set(
            f"{etiqueta} seleccionado: z = {z.real:.2f}{z.imag:+.2f}j  |  r = {r:.3f}  |  "
            f"θ = {theta:.3f} rad ({np.degrees(theta):.1f}°)")

    # -----------------------------------------------------------------
    # Dibujo
    # -----------------------------------------------------------------
    def update_plots(self):
        b, a = tf_from_zpk(self.design_zeros, self.design_poles, self.gain)
        self.formula_var.set(f"Preset: {self.preset_name}   |   {format_tf_string(b, a)}")

        self._draw_z_plane()
        self._draw_freq_response(b, a)
        self._draw_impulse(b, a)

        omega, H = freq_response(b, a, 4)
        Hw0 = float(np.abs(np.polyval(b[::-1], np.exp(-1j * self.omega0))
                            / np.polyval(a[::-1], np.exp(-1j * self.omega0))))
        self.readout_var.set(f"|H(e^jw0)| = {Hw0:.3f}  en w0 = {self.omega0:.2f} rad")

        self.canvas.draw()

    def _draw_z_plane(self):
        ax = self.z_plane_ax
        ax.clear()
        theta = np.linspace(0, 2 * np.pi, 400)
        ax.plot(np.cos(theta), np.sin(theta), "k--", lw=1, alpha=0.6)
        ax.axhline(0, color="k", lw=0.5)
        ax.axvline(0, color="k", lw=0.5)
        ax.set_xlim(-ZPLANE_LIM, ZPLANE_LIM)
        ax.set_ylim(-ZPLANE_LIM, ZPLANE_LIM)
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3)

        stable = is_stable(self.design_poles)
        estado = "ESTABLE" if stable else "INESTABLE"
        color = "green" if stable else "red"
        ax.set_title(f"Plano z  —  {estado} (causal supuesto)", fontsize=9, color=color)
        ax.set_xlabel("Re(z)")
        ax.set_ylabel("Im(z)")

        if self.design_poles:
            pr = [p.real for p in self.design_poles]
            pi = [p.imag for p in self.design_poles]
            ax.plot(pr, pi, "rx", markersize=10, mew=2, label="Polos")
        if self.design_zeros:
            zr = [z.real for z in self.design_zeros]
            zi = [z.imag for z in self.design_zeros]
            ax.plot(zr, zi, "bo", markersize=10, mfc="none", mew=2, label="Ceros")

        if self.show_vectors.get():
            zpt = np.exp(1j * self.omega0)
            ax.plot([zpt.real], [zpt.imag], "g^", markersize=11, label="e^{jw}")
            for p in self.design_poles:
                ax.annotate("", xy=(zpt.real, zpt.imag), xytext=(p.real, p.imag),
                             arrowprops=dict(arrowstyle="->", color="red", alpha=0.65, lw=1.2))
            for z in self.design_zeros:
                ax.annotate("", xy=(zpt.real, zpt.imag), xytext=(z.real, z.imag),
                             arrowprops=dict(arrowstyle="->", color="blue", alpha=0.65, lw=1.2))
        if self.design_poles or self.design_zeros:
            ax.legend(loc="upper right", fontsize=7)

    def _draw_freq_response(self, b, a):
        omega, H = freq_response(b, a, 800)
        mag = np.abs(H)

        ax = self.mag_ax
        ax.clear()
        ax.plot(omega, mag)
        ax.set_title("|H(e^{jw})|", fontsize=9)
        ax.set_xlabel("w [rad]")
        ax.set_xlim(-np.pi, np.pi)
        ax.set_xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
        ax.set_xticklabels(["-π", "-π/2", "0", "π/2", "π"])
        ax.grid(True, alpha=0.3)
        if self.show_vectors.get():
            Hw0 = abs(np.polyval(b[::-1], np.exp(-1j * self.omega0))
                      / np.polyval(a[::-1], np.exp(-1j * self.omega0)))
            ax.axvline(self.omega0, color="green", ls="--", lw=1)
            ax.plot([self.omega0], [Hw0], "g^", markersize=9)

        ax2 = self.phase_ax
        ax2.clear()
        ax2.plot(omega, np.angle(H, deg=True))
        ax2.set_title("∠H(e^{jw}) [grados]", fontsize=9)
        ax2.set_xlabel("w [rad]")
        ax2.set_xlim(-np.pi, np.pi)
        ax2.set_xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
        ax2.set_xticklabels(["-π", "-π/2", "0", "π/2", "π"])
        ax2.grid(True, alpha=0.3)
        if self.show_vectors.get():
            ax2.axvline(self.omega0, color="green", ls="--", lw=1)

    def _draw_impulse(self, b, a):
        h = impulse_response(b, a, IMPULSE_N)
        ax = self.h_ax
        ax.clear()
        n = np.arange(len(h))
        markerline, stemlines, baseline = ax.stem(n, h, basefmt=" ")
        plt.setp(markerline, markersize=4)
        ax.set_title("h[n]  (respuesta al impulso)", fontsize=9)
        ax.set_xlabel("n")
        ax.axhline(0, color="k", lw=0.5)
        ax.grid(True, alpha=0.3)

        stable = is_stable(self.design_poles)
        txt = "ESTABLE" if stable else "INESTABLE\n(h[n] no decae)"
        color = "green" if stable else "red"
        ax.text(0.97, 0.95, txt, transform=ax.transAxes, ha="right", va="top",
                 color=color, fontweight="bold", fontsize=9)


if __name__ == "__main__":
    root = tk.Tk()
    app = ZVisualizer(root)
    root.mainloop()
