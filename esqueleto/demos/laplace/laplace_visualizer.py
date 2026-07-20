import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
import tkinter as tk
from tkinter import messagebox
from scipy.signal import lti, impulse, tf2zpk
from matplotlib.colors import Normalize
import sympy

class LaplaceVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador y Diseñador de Sistemas en el Dominio de Laplace")
        self.root.geometry("1400x850")

        self.s = -0.2 + 1.5j
        self.dragging_s = False
        self.dragging_pz = False
        self.selected_pz_index = None
        self.selected_pz_type = None
        self.design_poles = []
        self.design_zeros = []
        
        self.signals = {
            "Impulso (Delta de Dirac)": {
                "plain_formula_t": "x(t) = δ(t)", "plain_formula_s": "X(s) = 1",
                "func_t": lambda t, **p: np.where(np.abs(t) < 1e-3, 1e3, 0), # Approximation for plotting
                "func_s": lambda s, **p: np.ones_like(s),
                "poles": lambda **p: [], "zeros": lambda **p: [],
                "roc": {"type": "all", "boundary": lambda **p: None}, "params": {}
            },
            "Pulso Rectangular": {
                "plain_formula_t": "x(t) = u(t) - u(t-T)", "plain_formula_s": "X(s) = (1 - e⁻ˢᵀ)/s",
                "func_t": lambda t, **p: (t >= 0) * (t < p['T']),
                "func_s": lambda s, **p: (1 - np.exp(-s * p['T'])) / s,
                "poles": lambda **p: [], "zeros": lambda **p: [2j * np.pi * k / p['T'] for k in range(-10, 11) if k != 0],
                "roc": {"type": "all", "boundary": lambda **p: None}, "params": {"T": (1.0, 10.0, 4.0)}
            },
            "Derecha: Seno Amortiguado": {
                "plain_formula_t": "x(t) = e⁻ᵃᵗ⋅sin(ω₀t)⋅u(t)", "plain_formula_s": "X(s) = ω₀ / ((s+a)² + ω₀²)",
                "func_t": lambda t, **p: np.exp(-p['a'] * t) * np.sin(p['w0'] * t) * (t >= 0),
                "func_s": lambda s, **p: p['w0'] / ((s + p['a'])**2 + p['w0']**2),
                "poles": lambda **p: [complex(-p['a'], p['w0']), complex(-p['a'], -p['w0'])],
                "roc": {"type": "right", "boundary": lambda **p: -p['a']}, "params": {"a": (0.1, 2.0, 0.5), "w0": (1.0, 10.0, 3.0)}
            },
            "Derecha: Seno Puro": {
                "plain_formula_t": "x(t) = sin(ω₀t)⋅u(t)", "plain_formula_s": "X(s) = ω₀ / (s² + ω₀²)",
                "func_t": lambda t, **p: np.sin(p['w0'] * t) * (t >= 0), "func_s": lambda s, **p: p['w0'] / (s**2 + p['w0']**2),
                "poles": lambda **p: [complex(0, p['w0']), complex(0, -p['w0'])],
                "roc": {"type": "right", "boundary": lambda **p: 0}, "params": {"w0": (1.0, 10.0, 3.0)}
            },
            "Derecha: Escalón Unitario": {
                "plain_formula_t": "x(t) = u(t)", "plain_formula_s": "X(s) = 1 / s",
                "func_t": lambda t, **p: 1.0 * (t >= 0), "func_s": lambda s, **p: 1/s,
                "poles": lambda **p: [0], "roc": {"type": "right", "boundary": lambda **p: 0},
                "params": {}
            },
            "Derecha: Exponencial Decreciente": {
                "plain_formula_t": "x(t) = e⁻ᵃᵗ⋅u(t)", "plain_formula_s": "X(s) = 1 / (s+a)",
                "func_t": lambda t, **p: np.exp(-p['a'] * t) * (t >= 0), "func_s": lambda s, **p: 1 / (s + p['a']),
                "poles": lambda **p: [complex(-p['a'], 0)], "roc": {"type": "right", "boundary": lambda **p: -p['a']},
                "params": {"a": (0.1, 2.0, 0.5)}
            },
            "Derecha: Rampa": {
                "plain_formula_t": "x(t) = t⋅u(t)", "plain_formula_s": "X(s) = 1 / s²",
                "func_t": lambda t, **p: t * (t >= 0), "func_s": lambda s, **p: 1/s**2,
                "poles": lambda **p: [0, 0], "roc": {"type": "right", "boundary": lambda **p: 0},
                "params": {}
            },
            "Izquierda: Escalón Unitario": {
                "plain_formula_t": "x(t) = -u(-t)", "plain_formula_s": "X(s) = 1/s",
                "func_t": lambda t, **p: -1.0 * (t < 0), "func_s": lambda s, **p: 1/s,
                "poles": lambda **p: [0], "roc": {"type": "left", "boundary": lambda **p: 0},
                "params": {}
            },
            "Izquierda: Exponencial Creciente": {
                "plain_formula_t": "x(t) = -e⁻ᵃᵗ⋅u(-t)", "plain_formula_s": "X(s) = 1 / (s+a)",
                "func_t": lambda t, **p: -np.exp(-p['a'] * t) * (t < 0), "func_s": lambda s, **p: 1 / (s + p['a']),
                "poles": lambda **p: [complex(-p['a'], 0)], "roc": {"type": "left", "boundary": lambda **p: -p['a']},
                "params": {"a": (-2.0, -0.1, -0.5)}
            },
            "Izquierda: Seno Amortiguado": {
                "plain_formula_t": "x(t) = -eᵃᵗ⋅sin(ω₀t)⋅u(-t)", "plain_formula_s": "X(s) = ω₀ / ((s-a)² + ω₀²)",
                "func_t": lambda t, **p: -np.exp(p['a'] * t) * np.sin(p['w0'] * t) * (t <= 0),
                "func_s": lambda s, **p: p['w0'] / ((s - p['a'])**2 + p['w0']**2),
                "poles": lambda **p: [complex(p['a'], p['w0']), complex(p['a'], -p['w0'])],
                "roc": {"type": "left", "boundary": lambda **p: p['a']}, "params": {"a": (0.1, 2.0, 0.5), "w0": (1.0, 10.0, 3.0)}
            },
            "Bilateral: Exponencial": {
                "plain_formula_t": "x(t) = e⁻ᵃ|ᵗ|", "plain_formula_s": "X(s) = 2a / (a² - s²)",
                "func_t": lambda t, **p: np.exp(-p['a'] * np.abs(t)), "func_s": lambda s, **p: (2*p['a']) / (p['a']**2 - s**2),
                "poles": lambda **p: [complex(p['a'], 0), complex(-p['a'], 0)],
                "roc": {"type": "strip", "boundary": lambda **p: (-p['a'], p['a'])},
                "params": {"a": (0.1, 2.0, 1.0)}
            }
        }
        self.signal_name = "Derecha: Escalón Unitario"
        self.params = {name: val[2] for name, val in self.signals[self.signal_name]['params'].items()}

        formula_frame = tk.Frame(root, pady=5); formula_frame.pack(side=tk.TOP, fill=tk.X)
        self.formula_t_var = tk.StringVar(); self.formula_s_var = tk.StringVar()
        tk.Label(formula_frame, textvariable=self.formula_t_var, font=('Helvetica', 12, 'bold')).pack()
        tk.Label(formula_frame, textvariable=self.formula_s_var, font=('Helvetica', 12, 'bold')).pack()
        controls_container = tk.Frame(root); controls_container.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.fig = plt.figure(figsize=(14, 8), tight_layout=True)
        self.s_plane_ax = self.fig.add_subplot(2, 3, 1)
        self.ft_mag_ax = self.fig.add_subplot(2, 3, 2)
        self.ft_phase_ax = self.fig.add_subplot(2, 3, 3)
        self.signal_ax = self.fig.add_subplot(2, 3, 4)
        self.integrand_ax = self.fig.add_subplot(2, 3, 5)
        self.three_d_ax = self.fig.add_subplot(2, 3, 6, projection='3d')

        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.setup_controls(controls_container)
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.init_plots()
        
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)

    def _update_formula_display(self):
        if self.mode.get() == "Analisis":
            info = self.signals[self.signal_name]
            self.formula_t_var.set(f"Señal: {info.get('plain_formula_t', '')}")
            self.formula_s_var.set(f"Transformada: {info.get('plain_formula_s', '')}")
        else:
             if self.design_submode.get() == "EqDiff":
                self.formula_t_var.set("Modo Diseño: Sistema definido por Ecuación Diferencial")
                den_coeffs_str = self.den_coeffs_entry.get(); num_coeffs_str = self.num_coeffs_entry.get()
                try:
                    num_coeffs = [float(c.strip()) for c in num_coeffs_str.split(',')]; den_coeffs = [float(c.strip()) for c in den_coeffs_str.split(',')]
                    s = sympy.Symbol('s')
                    num_poly = sum(c * s**i for i, c in enumerate(reversed(num_coeffs)))
                    den_poly = sum(c * s**i for i, c in enumerate(reversed(den_coeffs)))
                    hs_expr = sympy.simplify(num_poly / den_poly)
                    self.formula_s_var.set(f"H(s) = {sympy.printing.sstr(hs_expr, full_prec=False)}")
                except:
                    self.formula_s_var.set("H(s) = (Error en los coeficientes)")
             else:
                self.formula_t_var.set("Modo Diseño: Sistema definido por Polos y Ceros")
                self.formula_s_var.set("Puedes arrastrar los polos/ceros una vez creados.")

    def setup_controls(self, parent_frame):
        mode_frame = tk.Frame(parent_frame); mode_frame.pack(side=tk.LEFT, padx=10, fill='y', anchor='n')
        tk.Label(mode_frame, text="Modo Principal:", font=('Helvetica', 10, 'bold')).pack(anchor='w')
        self.mode = tk.StringVar(value="Analisis")
        tk.Radiobutton(mode_frame, text="Análisis de Señales", variable=self.mode, value="Analisis", command=self.on_mode_change).pack(anchor='w')
        tk.Radiobutton(mode_frame, text="Diseño de Sistemas", variable=self.mode, value="Diseno", command=self.on_mode_change).pack(anchor='w')
        self.analysis_controls_frame = tk.Frame(parent_frame)
        self.design_controls_frame = tk.Frame(parent_frame)
        
        analysis_selector_frame = tk.Frame(self.analysis_controls_frame); analysis_selector_frame.pack(side=tk.LEFT, fill='y', anchor='n')
        tk.Label(analysis_selector_frame, text="Señal Predefinida:").pack(anchor='w')
        self.signal_var = tk.StringVar(self.root); self.signal_var.set(self.signal_name)
        self.signal_selector = tk.OptionMenu(analysis_selector_frame, self.signal_var, *self.signals.keys(), command=self.on_signal_change)
        self.signal_selector.config(width=25); self.signal_selector.pack(anchor='w', padx=5, pady=(0, 10))
        instruction_text = "Mueva el punto 's' (círculo verde).\nMantén SHIFT para ajustar a los ejes."
        tk.Label(analysis_selector_frame, text=instruction_text, font=('Helvetica', 9, 'italic'), justify='left').pack(anchor='w', padx=5)
        self.param_sliders_frame = tk.Frame(self.analysis_controls_frame); self.param_sliders_frame.pack(side=tk.LEFT, padx=10, fill='both')

        design_mode_selector = tk.Frame(self.design_controls_frame); design_mode_selector.pack(side=tk.TOP, fill=tk.X, pady=5)
        tk.Label(design_mode_selector, text="Método de Definición:", font=('Helvetica', 10, 'bold')).pack(anchor='w')
        self.design_submode = tk.StringVar(value="PolosCeros")
        tk.Radiobutton(design_mode_selector, text="Por Polos y Ceros (Interactivo)", variable=self.design_submode, value="PolosCeros", command=self._on_design_submode_change).pack(anchor='w')
        tk.Radiobutton(design_mode_selector, text="Por Ecuación Diferencial", variable=self.design_submode, value="EqDiff", command=self._on_design_submode_change).pack(anchor='w')
        
        self.diffeq_frame = tk.Frame(self.design_controls_frame)
        den_frame = tk.Frame(self.diffeq_frame); den_frame.pack(fill='x', expand=True)
        tk.Label(den_frame, text="Coefs. y(t) [a_n,...,a_0]:", anchor='w').pack(side=tk.LEFT)
        self.den_coeffs_entry = tk.Entry(den_frame); self.den_coeffs_entry.insert(0, "1, 2, 26"); self.den_coeffs_entry.pack(side=tk.LEFT, fill='x', expand=True)
        num_frame = tk.Frame(self.diffeq_frame); num_frame.pack(fill='x', expand=True)
        tk.Label(num_frame, text="Coefs. x(t) [b_m,...,b_0]:", anchor='w').pack(side=tk.LEFT)
        self.num_coeffs_entry = tk.Entry(num_frame); self.num_coeffs_entry.insert(0, "1, 0"); self.num_coeffs_entry.pack(side=tk.LEFT, fill='x', expand=True)
        tk.Button(self.diffeq_frame, text="Calcular y Graficar Sistema", command=self._calculate_from_diffeq).pack(pady=5)

        self.polezero_frame = tk.Frame(self.design_controls_frame)
        tk.Label(self.polezero_frame, text="Clic Izq: Polo | Clic Der: Cero\nPuedes arrastrar polos/ceros existentes.", font=('Helvetica', 9, 'italic')).pack()
        tk.Button(self.polezero_frame, text="Limpiar Diseño", command=self.clear_design).pack(pady=5)
        
        self.on_mode_change()

    def _on_design_submode_change(self):
        self._update_formula_display(); self.clear_design()
        if self.design_submode.get() == "EqDiff":
            self.diffeq_frame.pack(pady=5, fill='x', expand=True); self.polezero_frame.pack_forget()
        else:
            self.diffeq_frame.pack_forget(); self.polezero_frame.pack(pady=10)
    
    def _calculate_from_diffeq(self):
        try:
            den_coeffs_str = self.den_coeffs_entry.get(); num_coeffs_str = self.num_coeffs_entry.get()
            if not den_coeffs_str.strip(): den_coeffs_str = '1'
            if not num_coeffs_str.strip(): num_coeffs_str = '1'
            den_coeffs = [float(c.strip()) for c in den_coeffs_str.split(',')]; num_coeffs = [float(c.strip()) for c in num_coeffs_str.split(',')]
            zeros, poles, _ = tf2zpk(num_coeffs, den_coeffs)
            self.design_zeros = list(zeros); self.design_poles = list(poles)
            self._update_formula_display(); self.update_plots()
        except Exception as e:
            messagebox.showerror("Error de Entrada", f"No se pudieron procesar los coeficientes.\nError: {e}")

    def on_mode_change(self):
        if self.mode.get() == "Analisis":
            self.analysis_controls_frame.pack(side=tk.LEFT, padx=10, fill='y'); self.design_controls_frame.pack_forget()
            self.create_param_sliders()
        else: 
            self.analysis_controls_frame.pack_forget(); self.design_controls_frame.pack(side=tk.LEFT, padx=20, fill='y')
            self._on_design_submode_change()
        self._update_formula_display(); self.update_plots(update_3d=True)
    
    def clear_design(self):
        self.design_poles.clear(); self.design_zeros.clear(); self.update_plots()

    def create_param_sliders(self):
        for widget in self.param_sliders_frame.winfo_children(): widget.destroy()
        current_signal_info = self.signals[self.signal_name]
        self.params = {name: val[2] for name, val in current_signal_info.get('params', {}).items()}
        for name, (min_val, max_val, default_val) in current_signal_info.get('params', {}).items():
            frame = tk.Frame(self.param_sliders_frame)
            tk.Label(frame, text=f"{name}:").pack(side=tk.LEFT)
            slider = tk.Scale(frame, from_=min_val, to=max_val, resolution=0.1, orient=tk.HORIZONTAL, length=150, command=lambda val, n=name: self.on_param_change(n, val))
            slider.set(default_val); slider.pack(side=tk.LEFT)
            frame.pack(side=tk.LEFT)

    def on_signal_change(self, selected_signal_name):
        self.signal_name = selected_signal_name; self.create_param_sliders(); self._update_formula_display(); self.update_plots(update_3d=True)

    def on_param_change(self, name, value):
        self.params[name] = float(value); self.update_plots(update_3d=True)

    def init_plots(self):
        self._update_formula_display(); self.update_plots(update_3d=True)

    def on_press(self, event):
        if event.inaxes != self.s_plane_ax or event.xdata is None: return
        
        if self.mode.get() == "Analisis":
            self.dragging_s = True; self.s = complex(event.xdata, event.ydata); self.update_plots(update_3d=False)
        
        elif self.design_submode.get() == "PolosCeros":
            self.selected_pz_index = None; min_dist = 0.5
            for i, p in enumerate(self.design_poles):
                dist = np.sqrt((event.xdata - p.real)**2 + (event.ydata - p.imag)**2)
                if dist < min_dist:
                    min_dist = dist; self.selected_pz_index = i; self.selected_pz_type = 'pole'
            for i, z in enumerate(self.design_zeros):
                dist = np.sqrt((event.xdata - z.real)**2 + (event.ydata - z.imag)**2)
                if dist < min_dist:
                    min_dist = dist; self.selected_pz_index = i; self.selected_pz_type = 'zero'
            if self.selected_pz_index is not None: self.dragging_pz = True
            else:
                s_new = complex(np.round(event.xdata, 2), np.round(event.ydata, 2))
                if event.button == 1: self.design_poles.append(s_new)
                if s_new.imag != 0 and event.button == 1: self.design_poles.append(s_new.conjugate())
                elif event.button == 3: self.design_zeros.append(s_new)
                if s_new.imag != 0 and event.button == 3: self.design_zeros.append(s_new.conjugate())
                self.update_plots()

    def on_motion(self, event):
        if event.inaxes != self.s_plane_ax or event.xdata is None: return

        if self.mode.get() == "Analisis" and self.dragging_s:
            s_real, s_imag = event.xdata, event.ydata
            if event.key == 'shift':
                if abs(s_real) < 0.2: s_real = 0
                if abs(s_imag) < 0.2: s_imag = 0
            self.s = complex(s_real, s_imag)
            self.s_point_artist.set_data([self.s.real], [self.s.imag])
            self.s_plane_ax.set_title(f'Plano s: $s = {self.s.real:.2f} + j{self.s.imag:.2f}$ (Polo: X, s: O)', fontsize=9)
            self.canvas.draw_idle()
        
        elif self.mode.get() == "Diseno" and self.dragging_pz:
            s_new = complex(np.round(event.xdata, 2), np.round(event.ydata, 2))
            if self.selected_pz_type == 'pole':
                old_pole = self.design_poles[self.selected_pz_index]
                self.design_poles[self.selected_pz_index] = s_new
                if old_pole.imag != 0:
                    try:
                        conjugate_idx = self.design_poles.index(old_pole.conjugate())
                        self.design_poles[conjugate_idx] = s_new.conjugate()
                    except ValueError: pass
            elif self.selected_pz_type == 'zero':
                old_zero = self.design_zeros[self.selected_pz_index]
                self.design_zeros[self.selected_pz_index] = s_new
                if old_zero.imag != 0:
                    try:
                        conjugate_idx = self.design_zeros.index(old_zero.conjugate())
                        self.design_zeros[conjugate_idx] = s_new.conjugate()
                    except ValueError: pass
            self.update_plots()

    def on_release(self, event):
        if self.mode.get() == "Analisis" and self.dragging_s:
            self.dragging_s = False
            if event.inaxes == self.s_plane_ax and event.xdata is not None: self.s = complex(event.xdata, event.ydata)
            self.update_plots(update_3d=False)
        elif self.mode.get() == "Diseno" and self.dragging_pz:
            self.dragging_pz = False; self.selected_pz_index = None; self.selected_pz_type = None
            self.update_plots()

    def update_plots(self, update_3d=False):
        if self.mode.get() == "Analisis": self.plot_analysis_mode(update_3d)
        else: self.plot_design_mode()

    def plot_analysis_mode(self, update_3d=False):
        # <<< CORRECCIÓN: No borrar el eje 3D en actualizaciones parciales >>>
        axes_to_clear = [self.s_plane_ax, self.signal_ax, self.integrand_ax, self.ft_mag_ax, self.ft_phase_ax]
        for ax in axes_to_clear: ax.clear()
        
        signal_info = self.signals[self.signal_name]
        func_t = lambda t: signal_info["func_t"](t, **self.params)
        func_s = lambda s: signal_info["func_s"](s, **self.params)
        roc_info = signal_info["roc"]
        self.s_plane_ax.set_title(f'Plano s: $s = {self.s.real:.2f} + j{self.s.imag:.2f}$ (Polo: X, s: O)', fontsize=9)
        self.s_plane_ax.set_xlabel(r'$\sigma$'); self.s_plane_ax.set_ylabel(r'$j\omega$')
        xlim = (-5, 5); ylim = (-12, 12)
        self.s_plane_ax.set_xlim(xlim); self.s_plane_ax.set_ylim(ylim)
        self.s_plane_ax.grid(True); self.s_plane_ax.axhline(0, color='k', lw=0.5); self.s_plane_ax.axvline(0, color='k', lw=0.5, label=r'Eje $j\omega$')
        roc_boundary = roc_info["boundary"](**self.params)
        poles = signal_info["poles"](**self.params)
        if roc_info["type"] == "right": self.s_plane_ax.fill_betweenx(ylim, roc_boundary, xlim[1], color='lightgreen', alpha=0.3)
        elif roc_info["type"] == "left": self.s_plane_ax.fill_betweenx(ylim, xlim[0], roc_boundary, color='lightblue', alpha=0.3)
        elif roc_info["type"] == "strip": left_b, right_b = roc_boundary; self.s_plane_ax.fill_betweenx(ylim, left_b, right_b, color='gold', alpha=0.3)
        self.s_plane_ax.plot(np.real(poles), np.imag(poles), 'rx', markersize=8, mew=1.5, label='Polos')
        self.s_point_artist, = self.s_plane_ax.plot([self.s.real], [self.s.imag], 'go', markersize=8)
        t_vals = np.linspace(-5, 10, 1000)
        self.signal_ax.set_title(r'Señal en el tiempo $x(t)$', fontsize=9); self.signal_ax.plot(t_vals, func_t(t_vals)); self.signal_ax.grid(True); self.signal_ax.axhline(0, color='k', lw=0.5)
        self.integrand_ax.set_title(r'Integrando Amortiguado: $x(t)e^{-\sigma t}$', fontsize=9); self.integrand_ax.plot(t_vals, func_t(t_vals) * np.exp(-self.s.real * t_vals)); self.integrand_ax.grid(True); self.integrand_ax.axhline(0, color='k', lw=0.5)
        ft_exists = (roc_info["type"] == "right" and roc_boundary <= 0) or \
                    (roc_info["type"] == "left" and roc_boundary >= 0) or \
                    (roc_info["type"] == "strip" and roc_boundary[0] < 0 < roc_boundary[1])
        self.ft_mag_ax.set_title(r'$|X(j\omega)|$', fontsize=9); self.ft_phase_ax.set_title(r'$\angle X(j\omega)$', fontsize=9)
        if ft_exists:
            omega_vals = np.linspace(ylim[0], ylim[1], 400); s_vals = 1j * omega_vals
            X_jw = func_s(s_vals)
            self.ft_mag_ax.plot(omega_vals, np.abs(X_jw)); self.ft_phase_ax.plot(omega_vals, np.angle(X_jw, deg=True))
        else:
            self.ft_mag_ax.text(0.5, 0.5, 'T.F. no existe', ha='center', va='center'); self.ft_phase_ax.text(0.5, 0.5, 'T.F. no existe', ha='center', va='center')
        for ax in [self.ft_mag_ax, self.ft_phase_ax]: ax.grid(True); ax.set_xlabel(r'$\omega$')
        
        if update_3d:
            self.three_d_ax.clear(); self.three_d_ax.set_title('$|X(s)|$: ROC (color) vs. Divergencia (gris)', fontsize=9)
            sigma_3d = np.linspace(xlim[0], xlim[1], 70); omega_3d = np.linspace(ylim[0], ylim[1], 70)
            S_sigma, S_omega = np.meshgrid(sigma_3d, omega_3d); s_grid = S_sigma + 1j * S_omega
            magnitude = np.abs(func_s(s_grid))
            vmax = np.nanpercentile(magnitude, 98); magnitude[magnitude > vmax] = vmax
            cmap = plt.get_cmap('viridis'); norm = Normalize(vmin=np.nanmin(magnitude), vmax=vmax)
            colors = cmap(norm(magnitude))
            mask = np.ones_like(S_sigma, dtype=bool)
            if roc_info["type"] == "right": mask = S_sigma < roc_boundary
            elif roc_info["type"] == "left": mask = S_sigma > roc_boundary
            elif roc_info["type"] == "strip": mask = (S_sigma < roc_boundary[0]) | (S_sigma > roc_boundary[1])
            elif roc_info["type"] == "all": mask = np.zeros_like(S_sigma, dtype=bool)
            colors[mask] = [0.5, 0.5, 0.5, 0.2]
            self.three_d_ax.plot_surface(S_sigma, S_omega, magnitude, facecolors=colors, rstride=1, cstride=1, antialiased=False)
            self.three_d_ax.scatter([p.real for p in poles], [p.imag for p in poles], 0, color='r', marker='x', s=50)
            self.three_d_ax.set_xlabel(r'$\sigma$'); self.three_d_ax.set_ylabel(r'$\omega$')
        
        self.canvas.draw()

    def plot_design_mode(self):
        # ... (código sin cambios)
        for ax in self.fig.axes: ax.clear()
        poles = np.array(self.design_poles); zeros = np.array(self.design_zeros)
        self.s_plane_ax.set_title('Diseño: Polo (X), Cero (O), Límite Estabilidad (--) ', fontsize=9); self.s_plane_ax.set_xlabel(r'$\sigma$'); self.s_plane_ax.set_ylabel(r'$j\omega$')
        self.s_plane_ax.set_xlim(-5, 5); self.s_plane_ax.set_ylim(-12, 12)
        self.s_plane_ax.grid(True); self.s_plane_ax.axhline(0, color='k', lw=0.5); self.s_plane_ax.axvline(0, color='r', lw=0.8, ls='--', label='Límite Estabilidad')
        if poles.size > 0: self.s_plane_ax.plot(poles.real, poles.imag, 'rx', markersize=10, mew=2, label='Polos')
        if zeros.size > 0: self.s_plane_ax.plot(zeros.real, zeros.imag, 'bo', markersize=10, mew=2, mfc='none', label='Ceros')
        self.signal_ax.set_title('Respuesta al Impulso $h(t)$', fontsize=9); self.signal_ax.set_xlabel('Tiempo (t)'); self.signal_ax.set_ylabel('Amplitud')
        self.signal_ax.grid(True); self.signal_ax.axhline(0, color='k', lw=0.5)
        if poles.size > 0:
            if len(zeros) > len(poles): self.signal_ax.text(0.5, 0.5, "Sistema no realizable", ha='center', color='red')
            else:
                num = np.poly(zeros); den = np.poly(poles)
                system = lti(num, den)
                t, h = impulse(system, T=np.linspace(0, 15, 500))
                self.signal_ax.plot(t, h)
                if np.any(poles.real > 0.001): self.signal_ax.text(0.95, 0.95, "INESTABLE", ha='right', va='top', transform=self.signal_ax.transAxes, color='red', fontweight='bold')
        ft_exists = poles.size > 0 and np.all(poles.real <= 0)
        self.ft_mag_ax.set_title(r'$|H(j\omega)|$', fontsize=9); self.ft_phase_ax.set_title(r'$\angle H(j\omega)$', fontsize=9)
        if ft_exists:
            omega_vals = np.linspace(-12, 12, 400); s_vals = 1j * omega_vals
            if zeros.size > 0: num_s = np.polyval(np.poly(zeros), s_vals)
            else: num_s = 1
            den_s = np.polyval(np.poly(poles), s_vals)
            H_jw = num_s / den_s
            self.ft_mag_ax.plot(omega_vals, np.abs(H_jw)); self.ft_phase_ax.plot(omega_vals, np.angle(H_jw, deg=True))
        else:
            self.ft_mag_ax.text(0.5, 0.5, 'T.F. no existe', ha='center', va='center'); self.ft_phase_ax.text(0.5, 0.5, 'T.F. no existe', ha='center', va='center')
        for ax in [self.ft_mag_ax, self.ft_phase_ax]: ax.grid(True); ax.set_xlabel(r'$\omega$')
        self.integrand_ax.set_title("Integrando", fontsize=9, color='gray'); self.integrand_ax.text(0.5, 0.5, "No aplicable", ha='center', color='gray'); self.integrand_ax.set_xticks([]); self.integrand_ax.set_yticks([])
        self.three_d_ax.clear(); self.three_d_ax.set_title('$|H(s)|$', fontsize=9)
        if poles.size > 0:
            xlim = (-5, 5); ylim = (-12, 12)
            sigma_3d = np.linspace(xlim[0], xlim[1], 50); omega_3d = np.linspace(ylim[0], ylim[1], 50)
            S_sigma, S_omega = np.meshgrid(sigma_3d, omega_3d); s_grid = S_sigma + 1j * S_omega
            if zeros.size > 0: num_s_grid = np.polyval(np.poly(zeros), s_grid)
            else: num_s_grid = 1
            den_s_grid = np.polyval(np.poly(poles), s_grid)
            magnitude = np.abs(num_s_grid / den_s_grid)
            vmax = np.nanpercentile(magnitude, 98); magnitude[magnitude > vmax] = vmax
            self.three_d_ax.plot_surface(S_sigma, S_omega, magnitude, cmap='viridis', rstride=1, cstride=1)
            self.three_d_ax.scatter(poles.real, poles.imag, 0, color='r', marker='x', s=50)
        self.three_d_ax.set_xlabel(r'$\sigma$'); self.three_d_ax.set_ylabel(r'$\omega$')
        self.canvas.draw()

if __name__ == '__main__':
    root = tk.Tk()
    app = LaplaceVisualizer(root)
    root.mainloop()