import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
from scipy import signal
from itertools import cycle, islice
import sounddevice as sd
import threading
import sys

class FourierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Laboratorio Virtual de la Serie de Fourier")

        # Configuración de los datos
        self.armonics = list(range(1, 21))
        self.sliders = {}
        self.entry_real = {}
        self.entry_imag = {}
        self.values_labels = {}
        self.c0 = 0.0  # término DC para reconstrucción

        # Controles trigonométricos (a_n, b_n) y modos
        self.a_entries = {}
        self.b_entries = {}
        self.a0_entry = None
        self.mode = 'complex'  # 'complex' | 'trig' | 'cos'
        self.trig_sliders = {}

        # Controles coseno (A_n, phi_n)
        self.cos_entries = {}
        self.cos_sliders = {}
        self.cos_a0_entry = None

        # Paleta de colores consistente por armónico
        base_colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        self.colors = list(islice(cycle(base_colors), len(self.armonics)))

        # --- Configuración de Audio Continuo ---
        self.samplerate = 44100
        self.base_freq = 220.0  # A3
        self.start_idx = 0
        self.sound_active = tk.BooleanVar()
        self.lock = threading.Lock() # Para acceso seguro a coeficientes desde el hilo de audio
        
        # Almacén de coeficientes para el hilo de audio, para desacoplarlo de la UI
        self.audio_coeffs = {n: {'mag': 0.0, 'phase_rad': 0.0} for n in self.armonics}

        try:
            self.stream = sd.OutputStream(
                samplerate=self.samplerate, channels=1,
                callback=self._audio_callback, finished_callback=self.on_stream_finished)
        except Exception as e:
            print(f"No se pudo inicializar el dispositivo de audio: {e}")
            self.stream = None
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 1. Panel de Controles dentro de un Notebook (viñetas)
        controls_container = ttk.Frame(root)
        controls_container.pack(side=tk.LEFT, fill="y")
        self.notebook = ttk.Notebook(controls_container)
        self.notebook.pack(fill="y")

        # Tab 1: representación compleja (c_n)
        controls_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(controls_frame, text="Compleja (c_n)")

        # Tab 2: representación trigonométrica (a_n, b_n)
        trig_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(trig_frame, text="Trigonométrica (a_n, b_n)")

        # Tab 3: representación coseno (A_n, φ_n)
        cos_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(cos_frame, text="Coseno (A_n, φ_n)")

        # Cambio de pestañas: actualizar modo y sincronizar
        def _on_tab_changed(event):
            tab_text = self.notebook.tab(self.notebook.select(), 'text')
            if 'Trigonométrica' in tab_text:
                self.mode = 'trig'
                self.sync_complex_to_trig_all()
            elif 'Coseno' in tab_text:
                self.mode = 'cos'
                self.sync_complex_to_cos_all()
            else:
                self.mode = 'complex'
            self.update_plot()
        self.notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)

        # ======= CONTROLES DE LA PESTAÑA COMPLEJA =======

        # Selector de señal (10 funciones)
        ttk.Label(controls_frame, text="Señal de Referencia:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, columnspan=5, pady=(0, 10))
        self.signal_selector = ttk.Combobox(
            controls_frame,
            values=[
                "Onda Cuadrada",
                "Onda Triangular",
                "Onda Diente de Sierra (Desc)",
                "Onda Diente de Sierra (Asc)",
                "Pulso Rectangular 50%",
                "Pulso Rectangular 25%",
                "Onda Senoidal",
                "Onda Cosenoidal",
                "Seno Rectificado Completo |sin|",
                "Seno Rectificado Media Onda"
            ],
            state="readonly"
        )
        self.signal_selector.set("Onda Cuadrada")
        self.signal_selector.grid(row=1, column=0, columnspan=5, pady=(0, 20))
        self.signal_selector.bind("<<ComboboxSelected>>", lambda event: (self.update_expression_label(), self.update_plot()))

        # Expresión analítica de la señal (T = 2π)
        ttk.Label(controls_frame, text="Expresión analítica (T = 2π):", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, columnspan=5, sticky='w')
        self.expr_label = ttk.Label(controls_frame, text="", justify='left', wraplength=320)
        self.expr_label.grid(row=2, column=1, columnspan=4, sticky='w')

        # Botones de control
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.grid(row=3, column=0, columnspan=5, pady=10)
        ttk.Button(btn_frame, text="Reset", command=self.reset_sliders).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Mostrar Solución", command=self.show_solution).pack(side=tk.LEFT, padx=5)
        
        # Checkbox para activar/desactivar sonido
        ttk.Checkbutton(btn_frame, text="Activar Sonido", variable=self.sound_active, command=self.toggle_sound).pack(side=tk.LEFT, padx=10)

        # Cabeceras
        ttk.Label(controls_frame, text="Armónico (n)", font=('Helvetica', 10, 'bold')).grid(row=4, column=0, pady=5)
        ttk.Label(controls_frame, text="Magnitud |c_n|", font=('Helvetica', 10, 'bold')).grid(row=4, column=1, columnspan=2, pady=5)
        ttk.Label(controls_frame, text="Fase (grados)", font=('Helvetica', 10, 'bold')).grid(row=4, column=3, columnspan=2, pady=5)
        ttk.Label(controls_frame, text="Real", font=('Helvetica', 10, 'bold')).grid(row=4, column=5, pady=5)
        ttk.Label(controls_frame, text="Imag", font=('Helvetica', 10, 'bold')).grid(row=4, column=6, pady=5)

        # Sliders/entries complejos por armónico
        for row, n in enumerate(self.armonics, 5):
            self._create_harmonic_controls_complex(controls_frame, n, row)

        # ==== TAB TRIGONOMÉTRICA (a_n, b_n) ====
        ttk.Label(trig_frame, text="a_0 (DC)", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.a0_entry = ttk.Entry(trig_frame, width=8)
        self.a0_entry.grid(row=0, column=1, padx=5)
        self.a0_entry.insert(0, f"{2*self.c0:.2f}")
        self.a0_entry.bind("<Return>", lambda event: self.sync_a0_from_trig())

        ttk.Label(trig_frame, text="Armónico (n)", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, pady=5)
        ttk.Label(trig_frame, text="a_n (cos) slider", font=('Helvetica', 10, 'bold')).grid(row=1, column=1, pady=5)
        ttk.Label(trig_frame, text="a_n (cos)", font=('Helvetica', 10, 'bold')).grid(row=1, column=2, pady=5)
        ttk.Label(trig_frame, text="b_n (sin) slider", font=('Helvetica', 10, 'bold')).grid(row=1, column=3, pady=5)
        ttk.Label(trig_frame, text="b_n (sin)", font=('Helvetica', 10, 'bold')).grid(row=1, column=4, pady=5)

        for row_idx, n in enumerate(self.armonics, start=2):
            ttk.Label(trig_frame, text=f"n={n}:").grid(row=row_idx, column=0, sticky='w', padx=5)
            a_slider = ttk.Scale(trig_frame, from_=-1.5, to=1.5, orient=tk.HORIZONTAL, length=100)
            a_slider.grid(row=row_idx, column=1, padx=5, pady=2)
            a_e = ttk.Entry(trig_frame, width=8)
            a_e.grid(row=row_idx, column=2, padx=5, pady=2)
            a_e.insert(0, "0.00")

            b_slider = ttk.Scale(trig_frame, from_=-1.5, to=1.5, orient=tk.HORIZONTAL, length=100)
            b_slider.grid(row=row_idx, column=3, padx=5, pady=2)
            b_e = ttk.Entry(trig_frame, width=8)
            b_e.grid(row=row_idx, column=4, padx=5, pady=2)
            b_e.insert(0, "0.00")

            self.trig_sliders[n] = {"a": a_slider, "b": b_slider}
            self.a_entries[n] = a_e
            self.b_entries[n] = b_e

            a_slider.bind("<B1-Motion>", lambda event, nn=n, type='a': self._sync_trig_for_audio(event, nn, type))
            b_slider.bind("<B1-Motion>", lambda event, nn=n, type='b': self._sync_trig_for_audio(event, nn, type))
            a_slider.bind("<ButtonRelease-1>", self._sync_from_trig_and_plot)
            b_slider.bind("<ButtonRelease-1>", self._sync_from_trig_and_plot)

            a_e.bind("<Return>", lambda event, nn=n: self.sync_trig_entry_to_sliders(nn))
            b_e.bind("<Return>", lambda event, nn=n: self.sync_trig_entry_to_sliders(nn))

        # ==== TAB COSENO (A_n, φ_n) ====
        ttk.Label(cos_frame, text="a_0 (DC)", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.cos_a0_entry = ttk.Entry(cos_frame, width=8)
        self.cos_a0_entry.grid(row=0, column=1, padx=5)
        self.cos_a0_entry.insert(0, f"{2*self.c0:.2f}")
        self.cos_a0_entry.bind("<Return>", lambda event: self.sync_a0_from_cos())

        ttk.Label(cos_frame, text="Armónico (n)", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, pady=5)
        ttk.Label(cos_frame, text="A_n slider", font=('Helvetica', 10, 'bold')).grid(row=1, column=1, pady=5)
        ttk.Label(cos_frame, text="A_n", font=('Helvetica', 10, 'bold')).grid(row=1, column=2, pady=5)
        ttk.Label(cos_frame, text="φ_n slider (°)", font=('Helvetica', 10, 'bold')).grid(row=1, column=3, pady=5)
        ttk.Label(cos_frame, text="φ_n (°)", font=('Helvetica', 10, 'bold')).grid(row=1, column=4, pady=5)

        for row_idx, n in enumerate(self.armonics, start=2):
            ttk.Label(cos_frame, text=f"n={n}:").grid(row=row_idx, column=0, sticky='w', padx=5)
            A_slider = ttk.Scale(cos_frame, from_=0.0, to=3.0, orient=tk.HORIZONTAL, length=100)
            A_slider.grid(row=row_idx, column=1, padx=5, pady=2)
            A_e = ttk.Entry(cos_frame, width=8)
            A_e.grid(row=row_idx, column=2, padx=5, pady=2)
            A_e.insert(0, "0.00")

            phi_slider = ttk.Scale(cos_frame, from_=-180, to=180, orient=tk.HORIZONTAL, length=100)
            phi_slider.grid(row=row_idx, column=3, padx=5, pady=2)
            phi_e = ttk.Entry(cos_frame, width=8)
            phi_e.grid(row=row_idx, column=4, padx=5, pady=2)
            phi_e.insert(0, "0.00")

            self.cos_sliders[n] = {"A": A_slider, "phi": phi_slider}
            self.cos_entries[n] = {"A": A_e, "phi": phi_e}

            A_slider.bind("<B1-Motion>", lambda event, nn=n, type='A': self._sync_cos_for_audio(event, nn, type))
            phi_slider.bind("<B1-Motion>", lambda event, nn=n, type='phi': self._sync_cos_for_audio(event, nn, type))
            A_slider.bind("<ButtonRelease-1>", self._sync_from_cos_and_plot)
            phi_slider.bind("<ButtonRelease-1>", self._sync_from_cos_and_plot)

            A_e.bind("<Return>", lambda event, nn=n: self.sync_cos_entry_to_sliders(nn))
            phi_e.bind("<Return>", lambda event, nn=n: self.sync_cos_entry_to_sliders(nn))

        # 2. Panel de Gráficos (4 subplots) con GridSpec
        self.fig = plt.figure(figsize=(11, 10))
        gs = self.fig.add_gridspec(4, 1, height_ratios=[3, 2, 1, 1], hspace=0.35)
        self.axs = [self.fig.add_subplot(gs[i]) for i in range(4)]

        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.RIGHT, fill="both", expand=True)

        self.update_plot()
        self.update_expression_label()

    def toggle_sound(self):
        """Inicia o detiene el flujo de audio según el estado del checkbox."""
        if self.stream is None: return
        if self.sound_active.get():
            if not self.stream.active:
                self.start_idx = 0 # Reinicia el tiempo de audio
                self.stream.start()
        else:
            if self.stream.active:
                self.stream.stop()

    def _audio_callback(self, outdata, frames, time, status):
        """Función llamada por el hilo de audio para generar la señal."""
        if status:
            print(status, file=sys.stderr)

        t = (self.start_idx + np.arange(frames)) / self.samplerate
        self.start_idx += frames
        
        audio_signal = np.zeros(frames, dtype=np.float32)

        # Leemos los coeficientes de nuestro almacén seguro, no de la UI
        with self.lock:
            coeffs_to_use = self.audio_coeffs.copy()

        for n in self.armonics:
            coeffs = coeffs_to_use.get(n)
            if coeffs and coeffs['mag'] > 1e-6:
                amplitude = 2.0 * coeffs['mag']
                frequency = n * self.base_freq
                audio_signal += amplitude * np.cos(2 * np.pi * frequency * t + coeffs['phase_rad'])

        # Normalización simple para evitar clipping
        max_abs = np.max(np.abs(audio_signal))
        if max_abs > 1.0:
             audio_signal /= max_abs

        outdata[:] = audio_signal.reshape(-1, 1) * 0.5 # Asigna a la salida y ajusta volumen

    def _update_audio_coeffs(self):
        """Copia de forma segura los coeficientes de la UI al almacén de audio."""
        with self.lock:
            for n in self.armonics:
                try:
                    magnitude_val = float(self.values_labels[n]["mag"].get())
                    phase_val_deg = float(self.values_labels[n]["phase"].get())
                    self.audio_coeffs[n]['mag'] = magnitude_val
                    self.audio_coeffs[n]['phase_rad'] = np.deg2rad(phase_val_deg)
                except (ValueError, tk.TclError): # Si la ventana se está cerrando
                    self.audio_coeffs[n]['mag'] = 0.0

    def on_stream_finished(self):
        """Callback que se llama cuando el stream termina por alguna razón."""
        # Podríamos querer reiniciar el stream aquí si fue un error inesperado
        pass

    def on_closing(self):
        """Maneja el cierre de la ventana para detener el audio limpiamente."""
        if self.stream and self.stream.active:
            self.stream.stop()
            self.stream.close()
        self.root.destroy()

    def _create_harmonic_controls_complex(self, parent, n, row):
        """Crea los widgets de control para un armónico en la pestaña compleja."""
        ttk.Label(parent, text=f"n={n}:").grid(row=row, column=0, sticky="w", padx=5)
        
        # Magnitud
        mag_slider = ttk.Scale(parent, from_=0, to=1.5, orient=tk.HORIZONTAL, length=100)
        mag_slider.grid(row=row, column=1, padx=5, pady=5)
        mag_label = ttk.Entry(parent, width=8)
        mag_label.grid(row=row, column=2, padx=2)
        mag_label.insert(0, "0.00")
        
        # Fase
        phase_slider = ttk.Scale(parent, from_=-180, to=180, orient=tk.HORIZONTAL, length=100)
        phase_slider.grid(row=row, column=3, padx=5, pady=5)
        phase_label = ttk.Entry(parent, width=8)
        phase_label.grid(row=row, column=4, padx=2)
        phase_label.insert(0, "0.00")
        
        # Real e Imaginario
        entry_real = ttk.Entry(parent, width=8)
        entry_real.grid(row=row, column=5, padx=5, pady=2)
        entry_imag = ttk.Entry(parent, width=8)
        entry_imag.grid(row=row, column=6, padx=5, pady=2)

        # Almacenamiento y bindeo de eventos
        self.sliders[n] = {"mag": mag_slider, "phase": phase_slider}
        self.values_labels[n] = {"mag": mag_label, "phase": phase_label}
        self.entry_real[n] = entry_real
        self.entry_imag[n] = entry_imag

        for widget in [mag_slider, phase_slider]:
            widget.bind("<B1-Motion>", self.sync_sliders_with_labels)
            widget.bind("<ButtonRelease-1>", lambda event: self.update_plot())

        mag_label.bind("<Return>", lambda event, nn=n: self.sync_labels_with_sliders(nn, "mag"))
        phase_label.bind("<Return>", lambda event, nn=n: self.sync_labels_with_sliders(nn, "phase"))
        entry_real.bind("<Return>", lambda event, nn=n: self.sync_entries_with_sliders(nn))
        entry_imag.bind("<Return>", lambda event, nn=n: self.sync_entries_with_sliders(nn))

    def update_expression_label(self):
        signal_type = self.signal_selector.get()
        if signal_type == "Onda Senoidal":
            txt = ("f(t) = sin(t)\nPeriodo T = 2π.")
        elif signal_type == "Onda Cosenoidal":
            txt = ("f(t) = cos(t)\nPeriodo T = 2π.")
        elif signal_type == "Onda Cuadrada":
            txt = ("f(t) = sgn(sin t) = {+1 si sin t ≥ 0; −1 si sin t < 0}\n"
                   "En (−π, π]: +1 para t∈(0, π], −1 para t∈(−π, 0].\nPeriodo T = 2π.")
        elif signal_type == "Onda Triangular":
            txt = ("Triangular simétrica con mínimo en t=0. En (0, 2π):\n"
                   "  f(t) = −1 + (2/π) t   (0<t<π)\n"
                   "  f(t) =  3 − (2/π) t   (π<t<2π)\nPeríodo 2π. (También f(t) = (2/π)·arcsin(sin t)).")
        elif signal_type == "Onda Diente de Sierra (Desc)":
            txt = ("Diente de sierra descendente: f(t) = 1 − t/π en (0,2π), 2π-periódica.")
        elif signal_type == "Onda Diente de Sierra (Asc)":
            txt = ("Diente de sierra ascendente: f(t) = t/π − 1 en (0,2π), 2π-periódica.")
        elif signal_type == "Pulso Rectangular 50%":
            txt = ("Pulso 0/1 con duty 50%: f=1 en (0,π), 0 en (π,2π), 2π-periódica.")
        elif signal_type == "Pulso Rectangular 25%":
            txt = ("Pulso 0/1 con duty 25%: f=1 en (0,π/2), 0 en (π/2,2π), 2π-periódica.")
        elif signal_type == "Seno Rectificado Completo |sin|":
            txt = ("|sin t|, 2π-periódica. Media 2/π. Sólo cosenos pares: a_{2n} = -4/(π(4n²-1)).")
        elif signal_type == "Seno Rectificado Media Onda":
            txt = ("max(0, sin t), 2π-periódica. Media 1/π. Contiene DC y armónicos senoidales.")
        else:
            txt = ""
        self.expr_label.config(text=txt)

    # ==== Sincronizaciones (compleja) ====
    def sync_sliders_with_labels(self, event=None):
        for n in self.armonics:
            mag = self.sliders[n]["mag"].get()
            phase_deg = self.sliders[n]["phase"].get()
            self.values_labels[n]["mag"].delete(0, tk.END)
            self.values_labels[n]["mag"].insert(0, f"{mag:.2f}")
            self.values_labels[n]["phase"].delete(0, tk.END)
            self.values_labels[n]["phase"].insert(0, f"{phase_deg:.2f}")
            real = mag * np.cos(np.deg2rad(phase_deg))
            imag = mag * np.sin(np.deg2rad(phase_deg))
            self.entry_real[n].delete(0, tk.END)
            self.entry_real[n].insert(0, f"{real:.2f}")
            self.entry_imag[n].delete(0, tk.END)
            self.entry_imag[n].insert(0, f"{imag:.2f}")

        self._update_audio_coeffs()

    def sync_labels_with_sliders(self, n, type_):
        try:
            val = float(self.values_labels[n][type_].get())
            self.sliders[n][type_].set(val)
            self.sync_sliders_with_labels()
            self.update_plot()
        except ValueError:
            pass

    def sync_entries_with_sliders(self, n):
        try:
            real = float(self.entry_real[n].get()); imag = float(self.entry_imag[n].get())
            mag = np.hypot(real, imag)
            phase_deg = np.rad2deg(np.arctan2(imag, real))
            self.sliders[n]["mag"].set(mag)
            self.sliders[n]["phase"].set(phase_deg)
            self.sync_sliders_with_labels()
            self.update_plot()
        except ValueError:
            pass

    # ==== Sincronizaciones (trig) ====
    def sync_trig_entries_only(self, event=None):
        """Actualiza solo los campos de texto de la pestaña trigonométrica. Es rápido para B1-Motion."""
        with self.lock:
            for n in self.armonics:
                a_val = self.trig_sliders[n]["a"].get()
                b_val = self.trig_sliders[n]["b"].get()
                self.a_entries[n].delete(0, tk.END); self.a_entries[n].insert(0, f"{a_val:.2f}")
                self.b_entries[n].delete(0, tk.END); self.b_entries[n].insert(0, f"{b_val:.2f}")

    def _sync_trig_for_audio(self, event, n, type):
        """Actualización ligera para audio mientras se arrastra el slider trigonométrico."""
        # 1. Actualizar solo el campo de texto correspondiente
        slider_val = self.trig_sliders[n][type].get()
        entry_widget = self.a_entries[n] if type == 'a' else self.b_entries[n]
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, f"{slider_val:.2f}")

        # 2. Actualizar los coeficientes de audio para este armónico
        with self.lock:
            a_val = self.trig_sliders[n]['a'].get()
            b_val = self.trig_sliders[n]['b'].get()
            mag = 0.5 * np.hypot(a_val, b_val)
            phase_rad = np.arctan2(-b_val, a_val)
            self.audio_coeffs[n] = {'mag': mag, 'phase_rad': phase_rad}

    def _sync_from_trig_and_plot(self, event=None):
        """Sincroniza desde la pestaña trigonométrica a la compleja y actualiza todo."""
        with self.lock:
            for n in self.armonics:
                a_val = self.trig_sliders[n]['a'].get()
                b_val = self.trig_sliders[n]['b'].get()
                mag = 0.5 * np.hypot(a_val, b_val)
                phase_deg = np.rad2deg(np.arctan2(-b_val, a_val))
                self.sliders[n]['mag'].set(mag)
                self.sliders[n]['phase'].set(phase_deg)
        self.sync_sliders_with_labels() # Actualiza entries complejas y audio
        self.update_plot()

    def sync_trig_entry_to_sliders(self, n):
        try: a_n = float(self.a_entries[n].get())
        except ValueError: a_n = 0.0
        try: b_n = float(self.b_entries[n].get())
        except ValueError: b_n = 0.0
        self.trig_sliders[n]["a"].set(a_n)
        self.trig_sliders[n]["b"].set(b_n)
        mag = 0.5 * np.hypot(a_n, b_n)
        phase = np.rad2deg(np.arctan2(-b_n, a_n))
        self.sliders[n]["mag"].set(mag)
        self.sliders[n]["phase"].set(phase)
        self.sync_sliders_with_labels()
        self.update_plot()

    def sync_trig_to_complex(self, n):
        self.sync_trig_entry_to_sliders(n)

    def sync_complex_to_trig_all(self):
        with self.lock:
            if self.a0_entry is not None:
                self.a0_entry.delete(0, tk.END); self.a0_entry.insert(0, f"{2*self.c0:.2f}")
            for n in self.armonics:
                try:
                    magnitude_val = float(self.values_labels[n]["mag"].get())
                    phase_val_deg = float(self.values_labels[n]["phase"].get())
                except ValueError:
                    magnitude_val = 0.0; phase_val_deg = 0.0
                a_n = 2.0 * magnitude_val * np.cos(np.deg2rad(phase_val_deg))
                b_n = -2.0 * magnitude_val * np.sin(np.deg2rad(phase_val_deg))
                self.a_entries[n].delete(0, tk.END); self.a_entries[n].insert(0, f"{a_n:.2f}")
                self.b_entries[n].delete(0, tk.END); self.b_entries[n].insert(0, f"{b_n:.2f}")
                if n in self.trig_sliders:
                    self.trig_sliders[n]["a"].set(a_n); self.trig_sliders[n]["b"].set(b_n)

    def sync_a0_from_trig(self):
        try: a0 = float(self.a0_entry.get())
        except (TypeError, ValueError): return
        self.c0 = 0.5 * a0
        self.update_plot()

    # ==== Sincronizaciones (cos) ====
    def sync_cos_entries_only(self, event=None):
        """Actualiza solo los campos de texto de la pestaña coseno. Es rápido para B1-Motion."""
        with self.lock:
            for n in self.armonics:
                A = self.cos_sliders[n]["A"].get()
                phi = self.cos_sliders[n]["phi"].get()
                self.cos_entries[n]["A"].delete(0, tk.END); self.cos_entries[n]["A"].insert(0, f"{A:.2f}")
                self.cos_entries[n]["phi"].delete(0, tk.END); self.cos_entries[n]["phi"].insert(0, f"{phi:.2f}")

    def _sync_cos_for_audio(self, event, n, type):
        """Actualización ligera para audio mientras se arrastra el slider de coseno."""
        # 1. Actualizar solo el campo de texto correspondiente
        slider_val = self.cos_sliders[n][type].get()
        entry_widget = self.cos_entries[n][type]
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, f"{slider_val:.2f}")

        # 2. Actualizar los coeficientes de audio para este armónico
        with self.lock:
            A = self.cos_sliders[n]['A'].get()
            phi_deg = self.cos_sliders[n]['phi'].get()
            self.audio_coeffs[n] = {'mag': 0.5 * A, 'phase_rad': np.deg2rad(phi_deg)}

    def _sync_from_cos_and_plot(self, event=None):
        """Sincroniza desde la pestaña coseno a la compleja y actualiza todo."""
        with self.lock:
            for n in self.armonics:
                A = self.cos_sliders[n]['A'].get()
                phi_deg = self.cos_sliders[n]['phi'].get()
                mag = 0.5 * A
                self.sliders[n]['mag'].set(mag)
                self.sliders[n]['phase'].set(phi_deg)
        self.sync_sliders_with_labels() # Actualiza entries complejas y audio
        self.update_plot()

    def sync_cos_entry_to_sliders(self, n):
        try: A = float(self.cos_entries[n]["A"].get())
        except ValueError: A = 0.0
        try: phi = float(self.cos_entries[n]["phi"].get())
        except ValueError: phi = 0.0
        self.cos_sliders[n]["A"].set(A); self.cos_sliders[n]["phi"].set(phi)
        self.sliders[n]["mag"].set(0.5 * A)
        self.sliders[n]["phase"].set(phi)
        self.sync_sliders_with_labels()
        self.update_plot()

    def sync_cos_to_complex(self, n):
        self.sync_cos_entry_to_sliders(n)

    def sync_complex_to_cos_all(self):
        with self.lock:
            if self.cos_a0_entry is not None:
                self.cos_a0_entry.delete(0, tk.END); self.cos_a0_entry.insert(0, f"{2*self.c0:.2f}")
            for n in self.armonics:
                try:
                    magnitude_val = float(self.values_labels[n]["mag"].get())
                    phase_val_deg = float(self.values_labels[n]["phase"].get())
                except ValueError:
                    magnitude_val = 0.0; phase_val_deg = 0.0
                A = 2.0 * magnitude_val; phi = phase_val_deg
                self.cos_entries[n]["A"].delete(0, tk.END); self.cos_entries[n]["A"].insert(0, f"{A:.2f}")
                self.cos_entries[n]["phi"].delete(0, tk.END); self.cos_entries[n]["phi"].insert(0, f"{phi:.2f}")
                if n in self.cos_sliders:
                    self.cos_sliders[n]["A"].set(A); self.cos_sliders[n]["phi"].set(phi)

    def sync_a0_from_cos(self):
        try: a0 = float(self.cos_a0_entry.get())
        except (TypeError, ValueError): return
        self.c0 = 0.5 * a0
        self.update_plot()

    def reset_sliders(self):
        for n in self.armonics:
            self.sliders[n]["mag"].set(0); self.sliders[n]["phase"].set(0)
        self.c0 = 0.0
        self.sync_sliders_with_labels()
        self.sync_complex_to_trig_all()
        self.sync_complex_to_cos_all()
        self._update_audio_coeffs()
        self.update_plot()

    def show_solution(self):
        signal_type = self.signal_selector.get()
        self.update_expression_label()
        self.c0 = 0.0

        if signal_type == "Onda Cuadrada":
            for n in self.armonics:
                if n % 2 != 0:
                    mag = 2 / (np.pi * n); phase = -90
                else:
                    mag = 0; phase = 0
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Onda Triangular":
            for n in self.armonics:
                if n % 2 != 0:
                    mag = 4 / (np.pi**2 * n**2); phase = 180
                else:
                    mag = 0; phase = 0
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Onda Diente de Sierra (Desc)":
            for n in self.armonics:
                mag = 1 / (np.pi * n); phase = -90
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Onda Diente de Sierra (Asc)":
            for n in self.armonics:
                mag = 1 / (np.pi * n); phase = 90
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Pulso Rectangular 50%":
            self.c0 = 0.5
            for n in self.armonics:
                if n % 2 != 0:
                    mag = 1 / (np.pi * n); phase = -90
                else:
                    mag = 0; phase = 0
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Pulso Rectangular 25%":
            self.c0 = 0.25
            d = 0.25
            for n in self.armonics:
                s = np.sin(np.pi * n * d)
                mag = np.abs(s) / (np.pi * n)
                phase_rad = -np.pi * n * d
                if s < 0: phase_rad += np.pi
                self.sliders[n]["mag"].set(mag)
                self.sliders[n]["phase"].set(np.rad2deg(phase_rad))

        elif signal_type == "Onda Senoidal":
            for n in self.armonics:
                mag = 0.5 if n == 1 else 0
                phase = -90 if n == 1 else 0
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Onda Cosenoidal":
            for n in self.armonics:
                mag = 0.5 if n == 1 else 0
                phase = 0.0 if n == 1 else 0.0
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Seno Rectificado Completo |sin|":
            self.c0 = 2/np.pi
            for n in self.armonics:
                if n % 2 == 0:
                    k = n // 2
                    a_n = -(4/np.pi) * (1/(4*k*k - 1))
                    mag = abs(a_n)/2; phase = 0.0 if a_n >= 0 else 180.0
                else:
                    mag = 0.0; phase = 0.0
                self.sliders[n]["mag"].set(mag); self.sliders[n]["phase"].set(phase)

        elif signal_type == "Seno Rectificado Media Onda":
            # f(t) = max(0, sin t)
            # a0 = 2/pi  => c0 = a0/2 = 1/pi
            self.c0 = 1/np.pi
            for n in self.armonics:
                if n == 1:
                    # b1 = 1/2  => c1 = -i/4
                    mag = 0.25
                    phase = -90.0
                elif n % 2 == 0:
                    # a_{2k} = -2/(pi*(4k^2 - 1))  => c_{2k} = a_{2k}/2 (real negativo)
                    k = n // 2
                    mag = 1.0 / (np.pi * (4*k*k - 1))
                    phase = 180.0
                else:
                    mag = 0.0
                    phase = 0.0
                self.sliders[n]["mag"].set(mag)
                self.sliders[n]["phase"].set(phase)

        # Sincronizar otras pestañas
        self.sync_sliders_with_labels()
        self.sync_complex_to_trig_all()
        self.sync_complex_to_cos_all()
        self._update_audio_coeffs()
        self.update_plot()

    def get_reference_signal(self, signal_type, t, T):
        if signal_type == "Onda Cuadrada":
            return signal.square(2 * np.pi * t / T)
        elif signal_type == "Onda Triangular":
            return signal.sawtooth(2 * np.pi * t / T, 0.5)
        elif signal_type == "Onda Diente de Sierra (Desc)":
            return signal.sawtooth(2 * np.pi * t / T, 0)
        elif signal_type == "Onda Diente de Sierra (Asc)":
            return signal.sawtooth(2 * np.pi * t / T, 1)
        elif signal_type == "Pulso Rectangular 50%":
            duty_cycle = 0.5
            return np.where(np.mod(t, T) < duty_cycle * T, 1, 0)
        elif signal_type == "Pulso Rectangular 25%":
            duty_cycle = 0.25
            return np.where(np.mod(t, T) < duty_cycle * T, 1, 0)
        elif signal_type == "Onda Senoidal":
            return np.sin(2 * np.pi * t / T)
        elif signal_type == "Onda Cosenoidal":
            return np.cos(2 * np.pi * t / T)
        elif signal_type == "Seno Rectificado Completo |sin|":
            return np.abs(np.sin(2 * np.pi * t / T))
        elif signal_type == "Seno Rectificado Media Onda":
            s = np.sin(2 * np.pi * t / T)
            return np.where(s > 0, s, 0)
        else:
            return np.zeros_like(t)

    def update_plot(self):
        for ax in self.axs:
            ax.clear()

        T = 2 * np.pi
        t = np.linspace(-3 * T, 3 * T, 1000)

        signal_type = self.signal_selector.get()
        reference_signal = self.get_reference_signal(signal_type, t, T)

        fourier_approx = np.zeros_like(t, dtype=complex)
        magnitudes, phases_deg = [], []
        a_vals, b_vals = [], []
        A_vals, phi_vals = [], []
        components = []

        for n in self.armonics:
            if self.mode == 'cos':
                try: A = float(self.cos_entries[n]["A"].get())
                except ValueError: A = 0.0
                try: phi_deg = float(self.cos_entries[n]["phi"].get())
                except ValueError: phi_deg = 0.0
                phase_val_rad = np.deg2rad(phi_deg)
                cn = 0.5 * A * np.exp(1j * phase_val_rad)
                magnitude_val = np.abs(cn); phase_val_deg = phi_deg
            elif self.mode == 'trig':
                try: a_n = float(self.a_entries[n].get())
                except ValueError: a_n = 0.0
                try: b_n = float(self.b_entries[n].get())
                except ValueError: b_n = 0.0
                cn = 0.5 * (a_n - 1j * b_n)
                magnitude_val = np.abs(cn)
                phase_val_deg = np.rad2deg(np.angle(cn))
            else:
                try:
                    magnitude_val = float(self.values_labels[n]["mag"].get())
                    phase_val_deg = float(self.values_labels[n]["phase"].get())
                except ValueError:
                    magnitude_val = 0.0; phase_val_deg = 0.0
                cn = magnitude_val * np.exp(1j * np.deg2rad(phase_val_deg))

            if n > 0:
                term_pos = cn * np.exp(1j * n * (2 * np.pi / T) * t)
                fourier_approx += term_pos + np.conj(term_pos)
                components.append(2 * np.real(term_pos))
            else:
                components.append(np.zeros_like(t))

            magnitudes.append(magnitude_val); phases_deg.append(phase_val_deg)
            a_vals.append(2.0 * np.real(cn)); b_vals.append(-2.0 * np.imag(cn))
            A_vals.append(2.0 * np.abs(cn)); phi_vals.append(phase_val_deg)

        fourier_approx += self.c0

        # Reconstrucción
        self.axs[0].axhline(0, color='black', linewidth=0.5, linestyle='--')
        self.axs[0].axvline(0, color='black', linewidth=0.5, linestyle='--')
        self.axs[0].plot(t, reference_signal, label=f'{signal_type} (Original)', linewidth=2, color='k')
        self.axs[0].plot(t, np.real(fourier_approx), label='Señal Reconstruida', linewidth=2, color='b', linestyle='--')
        self.axs[0].set_title('Reconstrucción de la Señal', fontsize=11)
        self.axs[0].set_ylabel('Amplitud')
        self.axs[0].legend(loc='upper right')
        self.axs[0].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

        # Componentes en el tiempo
        self.axs[1].axhline(0, color='black', linewidth=0.5, linestyle='--')
        for idx, comp in enumerate(components, start=1):
            if np.any(np.abs(comp) > 1e-12):
                self.axs[1].plot(t, comp, linewidth=1, color=self.colors[idx-1])
        self.axs[1].set_title('Componentes armónicas (tiempo)', fontsize=11)
        self.axs[1].set_ylabel('Amplitud')
        self.axs[1].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

        # Paneles inferiores según modo
        if self.mode == 'trig':
            self.axs[2].bar(self.armonics, a_vals, width=0.6, color=self.colors)
            self.axs[2].set_title('Coeficientes a_n (cos)', fontsize=11)
            self.axs[2].set_ylabel('a_n'); self.axs[2].set_xticks(self.armonics); self.axs[2].set_xlim(0, max(self.armonics) + 1)
            a_max = max([abs(v) for v in a_vals]) if a_vals else 1
            self.axs[2].set_ylim(-1.1*a_max if a_max>0 else -1, 1.1*a_max if a_max>0 else 1)
            self.axs[2].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

            self.axs[3].bar(self.armonics, b_vals, width=0.6, color=self.colors)
            self.axs[3].set_title('Coeficientes b_n (sin)', fontsize=11)
            self.axs[3].set_xlabel('Armónico (n)'); self.axs[3].set_ylabel('b_n'); self.axs[3].set_xticks(self.armonics); self.axs[3].set_xlim(0, max(self.armonics)+1)
            b_max = max([abs(v) for v in b_vals]) if b_vals else 1
            self.axs[3].set_ylim(-1.1*b_max if b_max>0 else -1, 1.1*b_max if b_max>0 else 1)
            self.axs[3].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

        elif self.mode == 'cos':
            self.axs[2].bar(self.armonics, A_vals, width=0.6, color=self.colors)
            self.axs[2].set_title('Amplitudes A_n (cos)', fontsize=11)
            self.axs[2].set_ylabel('A_n'); self.axs[2].set_xticks(self.armonics); self.axs[2].set_xlim(0, max(self.armonics) + 1)
            A_max = max(A_vals) if A_vals else 1
            self.axs[2].set_ylim(0, max(1e-3, 1.1 * A_max))
            self.axs[2].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

            self.axs[3].bar(self.armonics, phi_vals, width=0.6, color=self.colors)
            self.axs[3].set_title('Fases φ_n (°)', fontsize=11)
            self.axs[3].set_xlabel('Armónico (n)'); self.axs[3].set_ylabel('φ_n (°)'); self.axs[3].set_xticks(self.armonics); self.axs[3].set_xlim(0, max(self.armonics)+1)
            self.axs[3].set_ylim(-180, 180)
            self.axs[3].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

        else:
            self.axs[2].bar(self.armonics, magnitudes, width=0.6, color=self.colors)
            self.axs[2].set_title('Espectro de Magnitudes', fontsize=11)
            self.axs[2].set_ylabel('|c_n|'); self.axs[2].set_xticks(self.armonics); self.axs[2].set_xlim(0, max(self.armonics) + 1)
            max_mag = max(magnitudes) if len(magnitudes) > 0 else 1
            self.axs[2].set_ylim(0, max(1e-3, 1.1 * max_mag))
            self.axs[2].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

            self.axs[3].bar(self.armonics, phases_deg, width=0.6, color=self.colors)
            self.axs[3].set_title('Espectro de Fases', fontsize=11)
            self.axs[3].set_xlabel('Armónico (n)'); self.axs[3].set_ylabel('Fase (grados)'); self.axs[3].set_xticks(self.armonics); self.axs[3].set_xlim(0, max(self.armonics) + 1)
            self.axs[3].set_ylim(-180, 180)
            self.axs[3].grid(True, linestyle='--', linewidth=0.5, alpha=0.3)

        for ax in self.axs:
            ax.tick_params(labelsize=9)
        fig_w, fig_h = self.fig.get_size_inches()
        if fig_w < 8 or fig_h < 6:
            for ax in self.axs:
                ax.title.set_fontsize(9); ax.xaxis.label.set_size(8); ax.yaxis.label.set_size(8); ax.tick_params(labelsize=7)

        self.fig.suptitle('Laboratorio Virtual de la Serie de Fourier', fontsize=15, y=0.98)
        self.fig.tight_layout(rect=[0.03, 0.03, 0.98, 0.95])
        self.canvas.draw()

if __name__ == '__main__':
    root = tk.Tk()
    app = FourierApp(root)
    root.mainloop()