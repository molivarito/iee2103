import numpy as np
from scipy.signal import resample_poly, get_window, firwin, lfilter
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QComboBox, QTabWidget, QCheckBox, QGroupBox
)
from PySide6.QtCore import Qt


class DSPVisualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSP Visualizer: Análisis Espectral y Remuestreo")
        self.resize(1400, 900)

        # Configuración global de PyQtGraph
        pg.setConfigOptions(antialias=True)

        # --- Layout principal tipo DAW: controles a la izquierda, gráficos a la derecha ---
        central = QWidget()
        self.setCentralWidget(central)
        h_layout = QHBoxLayout(central)

        # Panel izquierdo: controles
        self.controls_panel = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_panel)
        h_layout.addWidget(self.controls_panel, stretch=0)

        # Panel derecho: gráficos (4 plots en malla 2x2)
        self.plot_widget = pg.GraphicsLayoutWidget()
        h_layout.addWidget(self.plot_widget, stretch=1)

        self._create_plots()
        self._create_controls()

        # Primer dibujado
        self.update_plots()

    # ---------------------------------------------------------------------
    # 1. Creación de gráficos
    # ---------------------------------------------------------------------
    def _create_plots(self):
        # 2x2: arriba tiempo, abajo frecuencia
        self.p_time1 = self.plot_widget.addPlot(row=0, col=0, title="Tiempo 1")
        self.p_time2 = self.plot_widget.addPlot(row=0, col=1, title="Tiempo 2")
        self.p_freq1 = self.plot_widget.addPlot(row=1, col=0, title="Frecuencia 1")
        self.p_freq2 = self.plot_widget.addPlot(row=1, col=1, title="Frecuencia 2")

        for p in [self.p_time1, self.p_time2, self.p_freq1, self.p_freq2]:
            p.showGrid(x=True, y=True, alpha=0.3)

        # Curvas pre-creadas (se actualizan con setData para máxima velocidad)
        self.curve_time1 = self.p_time1.plot(pen=pg.mkPen(width=2))
        self.curve_time2 = self.p_time2.plot(pen=pg.mkPen(width=2))
        self.curve_freq1 = self.p_freq1.plot(pen=pg.mkPen(color=(0,200,0), width=2))
        self.curve_freq2 = self.p_freq2.plot(pen=pg.mkPen(color=(200,0,200), width=2))
        self.stems_freq1 = []
        self.stems_freq2 = []
    def _draw_stems(self, plot_item, stems_list, x, y, color):
        # Remove old stems
        for line in stems_list:
            try:
                plot_item.removeItem(line)
            except Exception:
                pass
        stems_list.clear()

        # --- Performance optimization: decimate stems ---
        # Limit to max 400 stem lines for real-time performance
        Nmax = 400
        if len(x) > Nmax:
            step = len(x) // Nmax
            x = x[::step]
            y = y[::step]

        pen = pg.mkPen(color=color, width=1)
        for xv, yv in zip(x, y):
            stem = pg.PlotDataItem([xv, xv], [0, yv], pen=pen)
            plot_item.addItem(stem)
            stems_list.append(stem)

    # ---------------------------------------------------------------------
    # 2. Controles (panel izquierdo)
    # ---------------------------------------------------------------------
    def _add_labeled_slider(self, parent_layout, text, min_val, max_val, init_val):
        box = QGroupBox()
        v = QVBoxLayout(box)
        label = QLabel(f"{text}: {init_val}")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(init_val)
        v.addWidget(label)
        v.addWidget(slider)
        parent_layout.addWidget(box)
        return slider, label

    def _create_controls(self):
        # Tabs principales: Análisis Espectral / Remuestreo
        self.tabs_main = QTabWidget()
        self.controls_layout.addWidget(self.tabs_main)

        # --- Pestaña 1: Análisis Espectral ---
        tab_sa = QWidget()
        sa_layout = QVBoxLayout(tab_sa)
        self.tabs_main.addTab(tab_sa, "Análisis Espectral")

        self.sa_fs_slider, self.sa_fs_label = self._add_labeled_slider(
            sa_layout, "F_s (Hz)", 100, 1000, 200
        )
        expl = QLabel("● Controla cuántas muestras por segundo se toman; afecta la resolución temporal y el Nyquist.")
        expl.setWordWrap(True)
        sa_layout.addWidget(expl)

        self.sa_f0_slider, self.sa_f0_label = self._add_labeled_slider(
            sa_layout, "f0 (Hz)", 1, 100, 31
        )
        expl = QLabel("● Frecuencia de la sinusoide de prueba; permite ver aliasing y leakage.")
        expl.setWordWrap(True)
        sa_layout.addWidget(expl)

        self.sa_window_combo = QComboBox()
        self.sa_window_combo.addItems(["rectangular", "hann", "blackman"])
        sa_layout.addWidget(QLabel("Tipo de ventana"))
        sa_layout.addWidget(self.sa_window_combo)

        self.sa_nfft_slider, self.sa_nfft_label = self._add_labeled_slider(
            sa_layout, "Factor N_fft (xN)", 1, 32, 16
        )
        expl = QLabel("● Expande el número de puntos usados en la DFT para ver mejor los picos.")
        expl.setWordWrap(True)
        sa_layout.addWidget(expl)

        self.sa_zoom_slider, self.sa_zoom_label = self._add_labeled_slider(
            sa_layout, "Zoom espectral (x)", 1, 20, 1
        )
        expl = QLabel("● Amplifica la región alrededor del tono principal para ver detalles finos.")
        expl.setWordWrap(True)
        sa_layout.addWidget(expl)

        self.sa_norm_combo = QComboBox()
        self.sa_norm_combo.addItems(["Hz", "Normalizada (ω)"])
        sa_layout.addWidget(QLabel("Eje de frecuencia"))
        sa_layout.addWidget(self.sa_norm_combo)

        sa_layout.addStretch()

        # --- Pestaña 2: Remuestreo ---
        tab_rs = QWidget()
        rs_layout = QVBoxLayout(tab_rs)
        self.tabs_main.addTab(tab_rs, "Remuestreo")

        # Sub-pestañas internas para el flujo L → filtro → M → L/M
        self.tabs_rs = QTabWidget()
        self.tabs_rs.addTab(QWidget(), "Inserción de ceros (L)")
        self.tabs_rs.addTab(QWidget(), "Filtro anti-imagen")
        self.tabs_rs.addTab(QWidget(), "Diezmado (M)")
        self.tabs_rs.addTab(QWidget(), "Remuestreo L/M")
        rs_layout.addWidget(self.tabs_rs)

        # Controles compartidos de remuestreo
        self.rs_fs_slider, self.rs_fs_label = self._add_labeled_slider(
            rs_layout, "F_s original (Hz)", 50, 1000, 200
        )
        expl = QLabel("● Controla cuántas muestras por segundo se toman; afecta la resolución temporal y el Nyquist.")
        expl.setWordWrap(True)
        rs_layout.addWidget(expl)

        self.rs_f0_slider, self.rs_f0_label = self._add_labeled_slider(
            rs_layout, "f0 (Hz)", 1, 100, 40
        )
        expl = QLabel("● Frecuencia de la sinusoide de prueba; permite ver aliasing y leakage.")
        expl.setWordWrap(True)
        rs_layout.addWidget(expl)

        self.rs_L_slider, self.rs_L_label = self._add_labeled_slider(
            rs_layout, "L", 1, 5, 3
        )
        expl = QLabel("● Factor de expansión: inserta ceros y replica el espectro.")
        expl.setWordWrap(True)
        rs_layout.addWidget(expl)

        self.rs_M_slider, self.rs_M_label = self._add_labeled_slider(
            rs_layout, "M", 1, 5, 2
        )
        expl = QLabel("● Factor de diezmado: reduce la densidad de muestras y puede producir aliasing.")
        expl.setWordWrap(True)
        rs_layout.addWidget(expl)

        self.rs_norm_combo = QComboBox()
        self.rs_norm_combo.addItems(["Hz", "Normalizada (ω)"])
        rs_layout.addWidget(QLabel("Eje de frecuencia"))
        rs_layout.addWidget(self.rs_norm_combo)

        self.rs_alias_checkbox = QCheckBox("Simular diezmado sin filtro (aliasing)")
        rs_layout.addWidget(self.rs_alias_checkbox)

        # Overlay pedagogical checkboxes
        self.btn_show_filter = QCheckBox("Mostrar filtro ideal")
        self.btn_show_images = QCheckBox("Resaltar imágenes espectrales")
        self.controls_layout.addWidget(self.btn_show_filter)
        self.controls_layout.addWidget(self.btn_show_images)
        self.btn_show_filter.stateChanged.connect(self.update_plots)
        self.btn_show_images.stateChanged.connect(self.update_plots)

        rs_layout.addStretch()

        # --- Conexiones: todo apunta a update_plots (redibujado único y rápido) ---
        for slider in [
            self.sa_fs_slider, self.sa_f0_slider, self.sa_nfft_slider, self.sa_zoom_slider,
            self.rs_fs_slider, self.rs_f0_slider, self.rs_L_slider, self.rs_M_slider,
        ]:
            slider.valueChanged.connect(self.update_plots)

        for combo in [self.sa_window_combo, self.sa_norm_combo, self.rs_norm_combo]:
            combo.currentIndexChanged.connect(self.update_plots)

        self.rs_alias_checkbox.stateChanged.connect(self.update_plots)
        self.tabs_main.currentChanged.connect(self.update_plots)
        self.tabs_rs.currentChanged.connect(self.update_plots)

    # ---------------------------------------------------------------------
    # 3. Utilidades de frecuencia
    # ---------------------------------------------------------------------
    def _get_freq_axis(self, Fs, N_points, norm_mode):
        # Eje en Hz
        f_hz = np.fft.fftshift(np.fft.fftfreq(N_points, 1/Fs))

        if norm_mode == "Normalizada (ω)":
            # ω = 2π f / Fs  (normalización correcta dependiente de Fs)
            w = 2 * np.pi * f_hz / Fs
            return w, "ω (rad/muestra)"
        else:
            return f_hz, "Frecuencia (Hz)"

    def _draw_nyquist_line(self, plot_item, Fs, norm_mode):
        # Remove previous Nyquist lines if present
        for attr in ["_nyquist_line", "_nyquist_line_neg"]:
            prev = getattr(plot_item, attr, None)
            if prev is not None:
                try:
                    plot_item.removeItem(prev)
                except Exception:
                    pass
                setattr(plot_item, attr, None)
        if norm_mode == "Normalizada (ω)":
            x_nyq = np.pi
            x_nyq_neg = -np.pi
        else:
            x_nyq = Fs / 2
            x_nyq_neg = -Fs / 2
        pen = pg.mkPen(color=(200, 0, 0), width=2, style=Qt.DashLine)
        line = pg.InfiniteLine(pos=x_nyq, angle=90, pen=pen)
        line_neg = pg.InfiniteLine(pos=x_nyq_neg, angle=90, pen=pen)
        plot_item.addItem(line)
        plot_item.addItem(line_neg)
        plot_item._nyquist_line = line
        plot_item._nyquist_line_neg = line_neg

    # ---------------------------------------------------------------------
    # 4. Dispatcher de actualización
    # ---------------------------------------------------------------------
    def update_plots(self):
        if self.tabs_main.currentIndex() == 0:
            self._update_spectral_analysis()
        else:
            idx = self.tabs_rs.currentIndex()
            if idx == 0:
                self._update_rs_insertion()
            elif idx == 1:
                self._update_rs_filter()
            elif idx == 2:
                self._update_rs_decimation()
            else:
                self._update_rs_LM()

    # ---------------------------------------------------------------------
    # 5. Análisis Espectral
    # ---------------------------------------------------------------------
    def _update_spectral_analysis(self):
        Fs = self.sa_fs_slider.value()
        f0 = self.sa_f0_slider.value()
        window_type = self.sa_window_combo.currentText()
        nfft_mult = self.sa_nfft_slider.value()
        zoom = self.sa_zoom_slider.value()
        norm_mode = self.sa_norm_combo.currentText()
        N = 128
        N_fft = N * nfft_mult

        # Actualizar etiquetas
        self.sa_fs_label.setText(f"F_s (Hz): {Fs}")
        self.sa_f0_label.setText(f"f0 (Hz): {f0}")
        self.sa_nfft_label.setText(f"Factor N_fft (xN): {nfft_mult}  → N_fft={N_fft}")
        self.sa_zoom_label.setText(f"Zoom espectral (x): {zoom}")

        # Señal y ventana
        t = np.arange(N) / Fs
        x_n = np.sin(2 * np.pi * f0 * t)
        window = get_window(window_type, N)
        x_w = x_n * window

        x_padded = np.pad(x_w, (0, N_fft - N), 'constant')
        t_padded = np.arange(N_fft) / Fs

        f_axis, xlabel = self._get_freq_axis(Fs, N_fft, norm_mode)
        Xw = np.fft.fft(x_w, n=N_fft)
        Xw_shift = np.fft.fftshift(Xw)
        W = np.fft.fft(window, n=N_fft)
        W_shift = np.fft.fftshift(W)

        mag_win_db = 20 * np.log10(np.abs(W_shift) / (np.max(np.abs(W_shift)) + 1e-12) + 1e-12)
        mag_sig = np.abs(Xw_shift)

        # Tiempo
        self.p_time1.setTitle("Señal original x[n]")
        self.p_time1.setLabel("bottom", "Tiempo", units="s")
        self.p_time1.setLabel("left", "Amplitud")
        self.curve_time1.setData(t, x_n)

        self.p_time2.setTitle("Señal ventaneada con zero-padding")
        self.p_time2.setLabel("bottom", "Tiempo", units="s")
        self.p_time2.setLabel("left", "Amplitud")
        self.curve_time2.setData(t_padded, x_padded)

        # Frecuencia
        self.p_freq1.setTitle("Espectro de la ventana (dB)")
        self.p_freq1.setLabel("bottom", xlabel)
        self.p_freq1.setLabel("left", "Magnitud (dB)")
        self.curve_freq1.setData(f_axis, mag_win_db)

        self.p_freq2.setTitle("DFT de la señal ventaneada")
        self.p_freq2.setLabel("bottom", xlabel)
        self.p_freq2.setLabel("left", "|X[k]|")

        # --- Overlay: Ideal LPF outline ---
        if getattr(self, "btn_show_filter", None) and self.btn_show_filter.isChecked():
            # Add ideal LPF outline
            if not hasattr(self.p_freq2, "_ideal_filter"):
                pen = pg.mkPen(color=(50,150,50), width=2, style=Qt.DashLine)
                self.p_freq2._ideal_filter = pg.PlotDataItem()
                self.p_freq2.addItem(self.p_freq2._ideal_filter)
            if norm_mode == "Hz":
                H = (np.abs(f_axis) < (Fs/2)*0.9).astype(float)
            else:
                H = (np.abs(f_axis) < np.pi * 0.9).astype(float)
            self.p_freq2._ideal_filter.setData(f_axis, H*np.max(mag_sig))
        else:
            if hasattr(self.p_freq2, "_ideal_filter"):
                self.p_freq2.removeItem(self.p_freq2._ideal_filter)
                del self.p_freq2._ideal_filter

        # Plot main curve
        self.curve_freq2.setData(f_axis, mag_sig)

        # --- Overlay: Highlight spectral images ---
        if getattr(self, "btn_show_images", None) and self.btn_show_images.isChecked():
            if not hasattr(self.p_freq2, "_image_lines"):
                self.p_freq2._image_lines = []
            # remove old
            for ln in self.p_freq2._image_lines:
                try: self.p_freq2.removeItem(ln)
                except: pass
            self.p_freq2._image_lines.clear()

            if norm_mode == "Hz":
                bw = Fs  # spacing between images in Hz
                f0_plot = f0
            else:
                bw = 2 * np.pi  # spacing between images in rad (2π)
                f0_plot = 2 * np.pi * f0 / Fs  # convert f0 to radians
            for k in range(-3,4):
                f_center = k*bw + f0_plot
                pen = pg.mkPen(color=(180,120,0), style=Qt.DotLine)
                ln = pg.InfiniteLine(pos=f_center, angle=90, pen=pen)
                self.p_freq2.addItem(ln)
                self.p_freq2._image_lines.append(ln)
        else:
            if hasattr(self.p_freq2, "_image_lines"):
                for ln in self.p_freq2._image_lines:
                    try: self.p_freq2.removeItem(ln)
                    except: pass
                self.p_freq2._image_lines.clear()

        # Draw Nyquist lines
        self._draw_nyquist_line(self.p_freq1, Fs, norm_mode)
        self._draw_nyquist_line(self.p_freq2, Fs, norm_mode)

        # Zoom simple (centrado en f0)
        if norm_mode == "Hz":
            if zoom > 1:
                width = Fs / (4 * zoom)
                self.p_freq2.setXRange(f0 - width, f0 + width, padding=0)
                self.p_freq1.setXRange(-Fs / 2, Fs / 2, padding=0)
            else:
                self.p_freq1.setXRange(-Fs / 2, Fs / 2, padding=0)
                self.p_freq2.setXRange(-Fs / 2, Fs / 2, padding=0)
        else:
            # ω ∈ [-π, π]
            if zoom > 1:
                width = np.pi / (2 * zoom)
                f0_norm = 2 * np.pi * f0 / Fs
                self.p_freq2.setXRange(f0_norm - width, f0_norm + width, padding=0)
            else:
                self.p_freq2.setXRange(-np.pi, np.pi, padding=0)
            self.p_freq1.setXRange(-np.pi, np.pi, padding=0)

    # ---------------------------------------------------------------------
    # 6. Base común para Remuestreo
    # ---------------------------------------------------------------------
    def _prepare_resampling_base(self):
        Fs = self.rs_fs_slider.value()
        f0 = self.rs_f0_slider.value()
        L = self.rs_L_slider.value()
        M = self.rs_M_slider.value()
        norm_mode = self.rs_norm_combo.currentText()
        sim_alias = self.rs_alias_checkbox.isChecked()
        N = 128
        N_fft = None  # Defer FFT size to be set dynamically in the relevant function

        self.rs_fs_label.setText(f"F_s original (Hz): {Fs}")
        self.rs_f0_label.setText(f"f0 (Hz): {f0}")
        self.rs_L_label.setText(f"L: {L}")
        self.rs_M_label.setText(f"M: {M}")

        t_orig = np.arange(N) / Fs
        x_n = np.sin(2 * np.pi * f0 * t_orig)
        return Fs, f0, L, M, norm_mode, sim_alias, N, N_fft, t_orig, x_n

    # ---------------------------------------------------------------------
    # 7. Remuestreo: Paso 1 - Inserción de ceros (L)
    # ---------------------------------------------------------------------
    def _update_rs_insertion(self):
        Fs, f0, L, M, norm_mode, sim_alias, N, N_fft_unused, t_orig, x_n = self._prepare_resampling_base()
        self.rs_alias_checkbox.setEnabled(False)
        self.rs_alias_checkbox.setChecked(False)

        # Asegurar L entero válido
        L = max(int(L), 1)

        # FFT size for original signal spectrum
        N_fft_orig = 4096
        X = np.fft.fftshift(np.fft.fft(x_n, n=N_fft_orig))
        f_axis_orig, xlabel_orig = self._get_freq_axis(Fs, N_fft_orig, norm_mode)

        # Dynamic FFT size: at least 4096, but larger for higher L and N
        # Usar un tamaño de FFT más grande para capturar bien las réplicas
        N_fft_e = max(8192, int(N * L * 64))

        # Inserción de ceros
        x_e = np.zeros(N * L)
        x_e[::L] = x_n
        Fs_new = Fs * L
        t_e = np.arange(len(x_e)) / Fs_new

        # FFT con zero‑padding coherente (siempre a N_fft_e)
        X_e = np.fft.fftshift(np.fft.fft(x_e, n=N_fft_e))
        f_axis_new, xlabel_new = self._get_freq_axis(Fs_new, N_fft_e, norm_mode)

        # --- Tiempo ---
        self.p_time1.setTitle("Señal original x[n]")
        self.p_time1.setLabel("bottom", "Tiempo", units="s")
        self.curve_time1.setData(t_orig, x_n)

        self.p_time2.setTitle(f"Señal expandida por L={L} (inserción de ceros)")
        self.p_time2.setLabel("bottom", "Tiempo", units="s")
        self.curve_time2.setData(t_e, x_e)

        # --- Frecuencia: espectro original (eje basado en Fs) ---
        self.p_freq1.setTitle("Espectro original |X(e^{jω})|")
        self.p_freq1.setLabel("bottom", xlabel_orig)
        # Stems + curva continua
        self._draw_stems(self.p_freq1, self.stems_freq1, f_axis_orig, np.abs(X), (0,120,255))
        self.curve_freq1.setData(f_axis_orig, np.abs(X))

        # --- Frecuencia: espectro expandido (eje basado en Fs_new) ---
        self.p_freq2.setTitle("Espectro expandido (imágenes por inserción de ceros)")
        self.p_freq2.setLabel("bottom", xlabel_new)
        self._draw_stems(self.p_freq2, self.stems_freq2, f_axis_new, np.abs(X_e), (255,120,0))
        self.curve_freq2.setData(f_axis_new, np.abs(X_e))

        # --- Líneas que marcan las imágenes espectrales reales ---
        if hasattr(self.p_freq2, "_image_lines"):
            for ln in self.p_freq2._image_lines:
                try: self.p_freq2.removeItem(ln)
                except: pass
            self.p_freq2._image_lines.clear()
        else:
            self.p_freq2._image_lines = []

        # Imágenes repetidas cada Fs (teoría del upsampling)
        # Cuando insertas ceros con factor L, el espectro se comprime y se repite cada Fs Hz
        Fs_img = Fs  # Las réplicas aparecen cada Fs Hz (frecuencia de muestreo original)
        max_k = int((Fs_new/2) // Fs_img) + 3
        for k in range(-max_k, max_k+1):
            f_center = k * Fs_img
            pen = pg.mkPen(color=(255,180,0), style=Qt.DotLine, width=2)
            ln = pg.InfiniteLine(pos=f_center, angle=90, pen=pen)
            self.p_freq2.addItem(ln)
            self.p_freq2._image_lines.append(ln)

        # Líneas de Nyquist: cada figura con su propio Fs
        self._draw_nyquist_line(self.p_freq1, Fs, norm_mode)
        self._draw_nyquist_line(self.p_freq2, Fs_new, norm_mode)
        
        # Ajustar el rango del eje X para mostrar mejor la compresión y las réplicas
        if norm_mode == "Hz":
            # Mostrar un rango que incluya varias réplicas del espectro
            x_range = max(Fs_new, 3 * Fs)
            self.p_freq2.setXRange(-x_range, x_range, padding=0.05)
            self.p_freq1.setXRange(-Fs, Fs, padding=0.05)
        else:
            # En modo normalizado, mostrar el rango completo [-π, π] para el expandido
            # pero el espectro se comprime a [-π/L, π/L] y se repite
            self.p_freq2.setXRange(-np.pi * 1.5, np.pi * 1.5, padding=0.05)
            self.p_freq1.setXRange(-np.pi, np.pi, padding=0.05)

    # ---------------------------------------------------------------------
    # 8. Remuestreo: Paso 2 - Filtro anti-imagen
    # ---------------------------------------------------------------------
    def _update_rs_filter(self):
        Fs, f0, L, M, norm_mode, sim_alias, N, N_fft_unused, t_orig, x_n = self._prepare_resampling_base()
        self.rs_alias_checkbox.setEnabled(False)
        self.rs_alias_checkbox.setChecked(False)

        L = max(int(L), 1)
        x_e = np.zeros(N * L)
        x_e[::L] = x_n
        Fs_new = Fs * L
        t_e = np.arange(len(x_e)) / Fs_new

        # Apply ideal LPF after zero-stuffing: first expand, then filter
        # Frecuencia de corte normalizada: π/L en el dominio normalizado
        # En Hz: Fs/2 (la mitad de la frecuencia de muestreo original)
        num_taps = 129
        fc = 1 / (2 * L)  # normalized cutoff for anti-imaging LPF (π/L → fc = 0.5/L)
        h = firwin(num_taps, fc)
        y = lfilter(h, 1.0, x_e)
        t_y = np.arange(len(y)) / Fs_new

        # FFT size para visualización espectral
        N_fft = max(8192, int(N * L * 64))
        X_e = np.fft.fftshift(np.fft.fft(x_e, n=N_fft))
        Y = np.fft.fftshift(np.fft.fft(y, n=N_fft))
        f_axis_new, xlabel = self._get_freq_axis(Fs_new, N_fft, norm_mode)

        self.p_time1.setTitle(f"Señal expandida por L={L} (F_s={Fs_new:.0f} Hz)")
        self.p_time1.setLabel("bottom", "Tiempo", units="s")
        self.p_time1.setLabel("left", "Amplitud")
        self.curve_time1.setData(t_e, x_e)
        
        self.p_time2.setTitle(f"Salida tras filtro anti-imagen (f_c≈{Fs/2:.0f} Hz)")
        self.p_time2.setLabel("bottom", "Tiempo", units="s")
        self.p_time2.setLabel("left", "Amplitud")
        self.curve_time2.setData(t_y, y)

        self.p_freq1.setTitle(f"Espectro con imágenes (antes del filtro, F_s={Fs_new:.0f} Hz)")
        self.p_freq1.setLabel("bottom", xlabel)
        self.p_freq1.setLabel("left", "|X(e^{jω})|")
        self._draw_stems(self.p_freq1, self.stems_freq1, f_axis_new, np.abs(X_e), (0, 120, 255))
        self.curve_freq1.setData(f_axis_new, np.abs(X_e))

        # Highlight image bands in red shading - las réplicas aparecen cada Fs Hz (original)
        for ln in getattr(self.p_freq1, "_image_bands", []):
            try: self.p_freq1.removeItem(ln)
            except: pass
        self.p_freq1._image_bands = []
        if norm_mode == "Hz":
            bw = Fs  # Las imágenes aparecen cada Fs Hz (frecuencia de muestreo original)
        else:
            bw = 2 * np.pi  # spacing in radians
        for k in range(-3,4):
            if k != 0:  # No resaltar la banda principal
                band = pg.LinearRegionItem([k*bw - 0.4*bw, k*bw + 0.4*bw], brush=(255,0,0,40))
                self.p_freq1.addItem(band)
                self.p_freq1._image_bands.append(band)

        self.p_freq2.setTitle(f"Espectro filtrado (sin imágenes, F_s={Fs_new:.0f} Hz)")
        self.p_freq2.setLabel("bottom", xlabel)
        self.p_freq2.setLabel("left", "|Y(e^{jω})|")
        # Use a solid curve for the filtered result (clearer for students)
        self.curve_freq2.setData(f_axis_new, np.abs(Y))

        # --- Overlay: Ideal LPF outline ---
        if getattr(self, "btn_show_filter", None) and self.btn_show_filter.isChecked():
            if not hasattr(self.p_freq2, "_ideal_filter"):
                pen = pg.mkPen(color=(50,150,50), width=2, style=Qt.DashLine)
                self.p_freq2._ideal_filter = pg.PlotDataItem()
                self.p_freq2.addItem(self.p_freq2._ideal_filter)
            if norm_mode == "Hz":
                H = (np.abs(f_axis_new) < (Fs_new/2)*0.9).astype(float)
            else:
                H = (np.abs(f_axis_new) < np.pi * 0.9).astype(float)
            self.p_freq2._ideal_filter.setData(f_axis_new, H*np.max(np.abs(Y)))
        else:
            if hasattr(self.p_freq2, "_ideal_filter"):
                self.p_freq2.removeItem(self.p_freq2._ideal_filter)
                del self.p_freq2._ideal_filter

        # --- Overlay: Highlight spectral images ---
        if getattr(self, "btn_show_images", None) and self.btn_show_images.isChecked():
            if not hasattr(self.p_freq2, "_image_lines"):
                self.p_freq2._image_lines = []
            # remove old
            for ln in self.p_freq2._image_lines:
                try: self.p_freq2.removeItem(ln)
                except: pass
            self.p_freq2._image_lines.clear()

            # Las imágenes aparecen cada Fs Hz (original), no Fs_new
            if norm_mode == "Hz":
                bw = Fs
                f0_plot = f0
            else:
                bw = 2 * np.pi  # spacing in radians
                f0_plot = 2 * np.pi * f0 / Fs  # convert f0 to radians using original Fs
            for k in range(-3,4):
                f_center = k*bw + f0_plot
                pen = pg.mkPen(color=(180,120,0), style=Qt.DotLine)
                ln = pg.InfiniteLine(pos=f_center, angle=90, pen=pen)
                self.p_freq2.addItem(ln)
                self.p_freq2._image_lines.append(ln)
        else:
            if hasattr(self.p_freq2, "_image_lines"):
                for ln in self.p_freq2._image_lines:
                    try: self.p_freq2.removeItem(ln)
                    except: pass
                self.p_freq2._image_lines.clear()

        # Draw Nyquist lines
        self._draw_nyquist_line(self.p_freq1, Fs_new, norm_mode)
        self._draw_nyquist_line(self.p_freq2, Fs_new, norm_mode)
        
        # Ajustar rangos de visualización
        if norm_mode == "Hz":
            x_range = max(Fs_new, 3 * Fs)
            self.p_freq1.setXRange(-x_range, x_range, padding=0.05)
            self.p_freq2.setXRange(-Fs_new/2, Fs_new/2, padding=0.05)
        else:
            self.p_freq1.setXRange(-np.pi * 1.5, np.pi * 1.5, padding=0.05)
            self.p_freq2.setXRange(-np.pi, np.pi, padding=0.05)

    # ---------------------------------------------------------------------
    # 9. Remuestreo: Paso 3 - Diezmado (M)
    # ---------------------------------------------------------------------
    def _update_rs_decimation(self):
        Fs, f0, L, M, norm_mode, sim_alias, N, N_fft_unused, t_orig, x_n = self._prepare_resampling_base()
        self.rs_alias_checkbox.setEnabled(True)

        M = max(int(M), 1)
        Fs_new = Fs / M

        y_filt = resample_poly(x_n, 1, M)
        t_y = np.arange(len(y_filt)) / Fs_new

        y_raw = x_n[::M]
        t_raw = np.arange(len(y_raw)) / Fs_new

        # FFT size para visualización espectral
        N_fft = 4096
        
        # Espectro original con su propio eje de frecuencias (Fs)
        X = np.fft.fftshift(np.fft.fft(x_n, n=N_fft))
        f_axis_orig, xlabel_orig = self._get_freq_axis(Fs, N_fft, norm_mode)
        
        # Espectro diezmado con su nuevo eje de frecuencias (Fs_new)
        f_axis_new, xlabel_new = self._get_freq_axis(Fs_new, N_fft, norm_mode)

        self.p_time1.setTitle(f"Señal original x[n] (F_s={Fs:.0f} Hz)")
        self.p_time1.setLabel("bottom", "Tiempo", units="s")
        self.p_time1.setLabel("left", "Amplitud")
        self.curve_time1.setData(t_orig, x_n)

        if sim_alias:
            Y_raw = np.fft.fftshift(np.fft.fft(y_raw, n=N_fft))
            self.p_time2.setTitle(f"Diezmado sin filtro, M={M} (F_s={Fs_new:.0f} Hz)")
            self.p_time2.setLabel("bottom", "Tiempo", units="s")
            self.p_time2.setLabel("left", "Amplitud")
            self.curve_time2.setData(t_raw, y_raw)
            self.p_freq2.setTitle(f"Espectro de salida sin filtro (con aliasing, F_s={Fs_new:.0f} Hz)")
            self.p_freq2.setLabel("bottom", xlabel_new)
            self.p_freq2.setLabel("left", "|Y(e^{jω})|")
            # --- Overlay: Ideal LPF outline ---
            if getattr(self, "btn_show_filter", None) and self.btn_show_filter.isChecked():
                if not hasattr(self.p_freq2, "_ideal_filter"):
                    pen = pg.mkPen(color=(50,150,50), width=2, style=Qt.DashLine)
                    self.p_freq2._ideal_filter = pg.PlotDataItem()
                    self.p_freq2.addItem(self.p_freq2._ideal_filter)
                if norm_mode == "Hz":
                    H = (np.abs(f_axis_new) < (Fs_new/2)*0.9).astype(float)
                else:
                    H = (np.abs(f_axis_new) < np.pi * 0.9).astype(float)
                self.p_freq2._ideal_filter.setData(f_axis_new, H*np.max(np.abs(Y_raw)))
            else:
                if hasattr(self.p_freq2, "_ideal_filter"):
                    self.p_freq2.removeItem(self.p_freq2._ideal_filter)
                    del self.p_freq2._ideal_filter
            # Plot main curve
            self.curve_freq2.setData(f_axis_new, np.abs(Y_raw))
            # --- Overlay: Highlight spectral images ---
            if getattr(self, "btn_show_images", None) and self.btn_show_images.isChecked():
                if not hasattr(self.p_freq2, "_image_lines"):
                    self.p_freq2._image_lines = []
                for ln in self.p_freq2._image_lines:
                    try: self.p_freq2.removeItem(ln)
                    except: pass
                self.p_freq2._image_lines.clear()
                if norm_mode == "Hz":
                    bw = Fs_new
                    f0_plot = f0
                else:
                    bw = 2 * np.pi  # spacing in radians
                    f0_plot = 2 * np.pi * f0 / Fs_new  # convert f0 to radians
                for k in range(-3,4):
                    f_center = k*bw + f0_plot
                    pen = pg.mkPen(color=(180,120,0), style=Qt.DotLine)
                    ln = pg.InfiniteLine(pos=f_center, angle=90, pen=pen)
                    self.p_freq2.addItem(ln)
                    self.p_freq2._image_lines.append(ln)
            else:
                if hasattr(self.p_freq2, "_image_lines"):
                    for ln in self.p_freq2._image_lines:
                        try: self.p_freq2.removeItem(ln)
                        except: pass
                    self.p_freq2._image_lines.clear()
        else:
            Y_filt = np.fft.fftshift(np.fft.fft(y_filt, n=N_fft))
            self.p_time2.setTitle(f"Diezmado con filtro, M={M} (F_s={Fs_new:.0f} Hz)")
            self.p_time2.setLabel("bottom", "Tiempo", units="s")
            self.p_time2.setLabel("left", "Amplitud")
            self.curve_time2.setData(t_y, y_filt)
            self.p_freq2.setTitle(f"Espectro de salida con filtro (F_s={Fs_new:.0f} Hz)")
            self.p_freq2.setLabel("bottom", xlabel_new)
            self.p_freq2.setLabel("left", "|Y(e^{jω})|")
            # --- Overlay: Ideal LPF outline ---
            if getattr(self, "btn_show_filter", None) and self.btn_show_filter.isChecked():
                if not hasattr(self.p_freq2, "_ideal_filter"):
                    pen = pg.mkPen(color=(50,150,50), width=2, style=Qt.DashLine)
                    self.p_freq2._ideal_filter = pg.PlotDataItem()
                    self.p_freq2.addItem(self.p_freq2._ideal_filter)
                if norm_mode == "Hz":
                    H = (np.abs(f_axis_new) < (Fs_new/2)*0.9).astype(float)
                else:
                    H = (np.abs(f_axis_new) < np.pi * 0.9).astype(float)
                self.p_freq2._ideal_filter.setData(f_axis_new, H*np.max(np.abs(Y_filt)))
            else:
                if hasattr(self.p_freq2, "_ideal_filter"):
                    self.p_freq2.removeItem(self.p_freq2._ideal_filter)
                    del self.p_freq2._ideal_filter
            # Plot main curve
            self.curve_freq2.setData(f_axis_new, np.abs(Y_filt))
            # --- Overlay: Highlight spectral images ---
            if getattr(self, "btn_show_images", None) and self.btn_show_images.isChecked():
                if not hasattr(self.p_freq2, "_image_lines"):
                    self.p_freq2._image_lines = []
                for ln in self.p_freq2._image_lines:
                    try: self.p_freq2.removeItem(ln)
                    except: pass
                self.p_freq2._image_lines.clear()
                if norm_mode == "Hz":
                    bw = Fs_new
                    f0_plot = f0
                else:
                    bw = 2 * np.pi  # spacing in radians
                    f0_plot = 2 * np.pi * f0 / Fs_new  # convert f0 to radians
                for k in range(-3,4):
                    f_center = k*bw + f0_plot
                    pen = pg.mkPen(color=(180,120,0), style=Qt.DotLine)
                    ln = pg.InfiniteLine(pos=f_center, angle=90, pen=pen)
                    self.p_freq2.addItem(ln)
                    self.p_freq2._image_lines.append(ln)
            else:
                if hasattr(self.p_freq2, "_image_lines"):
                    for ln in self.p_freq2._image_lines:
                        try: self.p_freq2.removeItem(ln)
                        except: pass
                    self.p_freq2._image_lines.clear()

        # Mostrar el espectro original con su propio eje de frecuencias (Fs)
        # Esto permite ver claramente cómo el rango de Nyquist se reduce al diezmar
        self.p_freq1.setTitle(f"Espectro original |X(e^{{jω}})| (F_s={Fs:.0f} Hz)")
        self.p_freq1.setLabel("bottom", xlabel_orig)
        self.p_freq1.setLabel("left", "|X(e^{jω})|")
        self.curve_freq1.setData(f_axis_orig, np.abs(X))

        # Draw Nyquist lines - cada gráfico con su propio Fs
        self._draw_nyquist_line(self.p_freq1, Fs, norm_mode)
        self._draw_nyquist_line(self.p_freq2, Fs_new, norm_mode)
        
        # Ajustar rangos de visualización
        if norm_mode == "Hz":
            # Espectro original: rango completo [-Fs/2, Fs/2]
            self.p_freq1.setXRange(-Fs/2, Fs/2, padding=0.05)
            # Espectro diezmado: rango completo [-Fs_new/2, Fs_new/2]
            self.p_freq2.setXRange(-Fs_new/2, Fs_new/2, padding=0.05)
        else:
            # Ambos en rango normalizado [-π, π]
            self.p_freq1.setXRange(-np.pi, np.pi, padding=0.05)
            self.p_freq2.setXRange(-np.pi, np.pi, padding=0.05)

    # ---------------------------------------------------------------------
    # 10. Remuestreo: Paso 4 - Remuestreo racional L/M
    # ---------------------------------------------------------------------
    def _update_rs_LM(self):
        Fs, f0, L, M, norm_mode, sim_alias, N, N_fft_unused, t_orig, x_n = self._prepare_resampling_base()
        self.rs_alias_checkbox.setEnabled(False)
        self.rs_alias_checkbox.setChecked(False)

        L = max(int(L), 1)
        M = max(int(M), 1)
        Fs_new = Fs * L / M

        y = resample_poly(x_n, L, M)
        t_y = np.arange(len(y)) / Fs_new

        # FFT size para visualización espectral
        N_fft = max(8192, int(N * max(L, M) * 64))
        X = np.fft.fftshift(np.fft.fft(x_n, n=N_fft))
        Y = np.fft.fftshift(np.fft.fft(y, n=N_fft))
        f_axis_new, xlabel = self._get_freq_axis(Fs_new, N_fft, norm_mode)

        self.p_time1.setTitle(f"Señal original x[n] (F_s={Fs:.0f} Hz)")
        self.p_time1.setLabel("bottom", "Tiempo", units="s")
        self.p_time1.setLabel("left", "Amplitud")
        self.curve_time1.setData(t_orig, x_n)
        
        self.p_time2.setTitle(f"Señal remuestreada L/M={L}/{M} (F_s={Fs_new:.1f} Hz)")
        self.p_time2.setLabel("bottom", "Tiempo", units="s")
        self.p_time2.setLabel("left", "Amplitud")
        self.curve_time2.setData(t_y, y)

        self.p_freq1.setTitle(f"Espectro original referido a F_s={Fs_new:.1f} Hz")
        self.p_freq1.setLabel("bottom", xlabel)
        self.p_freq1.setLabel("left", "|X(e^{jω})|")
        self.curve_freq1.setData(f_axis_new, np.abs(X))

        self.p_freq2.setTitle(f"Espectro de la señal remuestreada (F_s={Fs_new:.1f} Hz)")
        self.p_freq2.setLabel("bottom", xlabel)
        self.p_freq2.setLabel("left", "|Y(e^{jω})|")

        # --- Overlay: Ideal LPF outline ---
        if getattr(self, "btn_show_filter", None) and self.btn_show_filter.isChecked():
            if not hasattr(self.p_freq2, "_ideal_filter"):
                pen = pg.mkPen(color=(50,150,50), width=2, style=Qt.DashLine)
                self.p_freq2._ideal_filter = pg.PlotDataItem()
                self.p_freq2.addItem(self.p_freq2._ideal_filter)
            if norm_mode == "Hz":
                H = (np.abs(f_axis_new) < (Fs_new/2)*0.9).astype(float)
            else:
                H = (np.abs(f_axis_new) < np.pi * 0.9).astype(float)
            self.p_freq2._ideal_filter.setData(f_axis_new, H*np.max(np.abs(Y)))
        else:
            if hasattr(self.p_freq2, "_ideal_filter"):
                self.p_freq2.removeItem(self.p_freq2._ideal_filter)
                del self.p_freq2._ideal_filter

        # Plot main curve
        self.curve_freq2.setData(f_axis_new, np.abs(Y))

        # --- Overlay: Highlight spectral images ---
        if getattr(self, "btn_show_images", None) and self.btn_show_images.isChecked():
            if not hasattr(self.p_freq2, "_image_lines"):
                self.p_freq2._image_lines = []
            for ln in self.p_freq2._image_lines:
                try: self.p_freq2.removeItem(ln)
                except: pass
            self.p_freq2._image_lines.clear()
            if norm_mode == "Hz":
                bw = Fs_new
                f0_plot = f0
            else:
                bw = 2 * np.pi  # spacing in radians
                f0_plot = 2 * np.pi * f0 / Fs_new  # convert f0 to radians
            for k in range(-3,4):
                f_center = k*bw + f0_plot
                pen = pg.mkPen(color=(180,120,0), style=Qt.DotLine)
                ln = pg.InfiniteLine(pos=f_center, angle=90, pen=pen)
                self.p_freq2.addItem(ln)
                self.p_freq2._image_lines.append(ln)
        else:
            if hasattr(self.p_freq2, "_image_lines"):
                for ln in self.p_freq2._image_lines:
                    try: self.p_freq2.removeItem(ln)
                    except: pass
                self.p_freq2._image_lines.clear()

        # Draw Nyquist lines
        self._draw_nyquist_line(self.p_freq1, Fs_new, norm_mode)
        self._draw_nyquist_line(self.p_freq2, Fs_new, norm_mode)
        
        # Ajustar rangos de visualización
        if norm_mode == "Hz":
            self.p_freq1.setXRange(-Fs_new, Fs_new, padding=0.05)
            self.p_freq2.setXRange(-Fs_new/2, Fs_new/2, padding=0.05)
        else:
            self.p_freq1.setXRange(-np.pi, np.pi, padding=0.05)
            self.p_freq2.setXRange(-np.pi, np.pi, padding=0.05)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = DSPVisualizerApp()
    win.show()
    sys.exit(app.exec())