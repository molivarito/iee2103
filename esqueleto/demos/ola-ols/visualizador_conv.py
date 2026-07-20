import sys
import numpy as np
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # Necesario para projection='3d'
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QGroupBox, QRadioButton, QSlider, QLabel, QFormLayout, QComboBox,
    QTabWidget, QSpinBox
)
from PySide6.QtCore import Qt, Slot

# --- Parámetros Pedagógicos ---
# Valores iniciales. La longitud de la señal ahora es configurable.
TOTAL_SIGNAL_LEN = 256
FILTER_M = 17  # Longitud del filtro (M)


class MainVisualizerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lección Interactiva de Filtrado Rápido (OLA/OLS)")
        self.setGeometry(100, 100, 1200, 900)

        # --- Variables de Estado de la Simulación ---
        self.x_full = None       # Señal de entrada completa
        self.h_full = None       # Respuesta al impulso (filtro)
        self.y_true = None       # Convolución lineal "Verdad Fundamental"
        self.y_recon = None      # Salida reconstruida bloque a bloque
        self.M = FILTER_M        # Longitud del filtro

        # Generar señales iniciales ANTES de crear los widgets que las usan
        self._generate_signals()

        # --- Configurar la GUI principal con pestañas ---
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)

        # Crear panel de control superior (común a ambas pestañas)
        self._create_common_control_panel()

        # Crear el widget de pestañas
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab0 = QWidget()
        self.tabs.addTab(self.tab0, "1. ¿Cómo Funciona la Convolución?")
        self.tabs.addTab(self.tab1, "2. Lineal vs. Circular (vía FFT)")
        self.tabs.addTab(self.tab2, "3. Filtrado por Bloques (OLA/OLS)")
        self.main_layout.addWidget(self.tabs)

        # Crear el contenido de cada pestaña
        self.mechanics_visualizer = ConvolutionMechanicsVisualizer(self)
        self.ola_ols_visualizer = OLA_OLS_Visualizer(self)
        self.concepts_visualizer = ConceptsVisualizer(self)

        # FIX: renombrado de .layout a .main_layout para evitar colisión con QWidget.layout()
        self.tab0.setLayout(self.mechanics_visualizer.main_layout)
        self.tab1.setLayout(self.concepts_visualizer.main_layout)
        self.tab2.setLayout(self.ola_ols_visualizer.main_layout)

        # Conectar señales
        self.btn_gen_signal.clicked.connect(lambda: self._generate_signals())

    def _create_common_control_panel(self):
        """Crea el panel superior con el botón de generar señal."""
        common_panel = QGroupBox("Control General")
        layout = QHBoxLayout()
        self.btn_gen_signal = QPushButton("Generar Nueva Señal/Filtro")
        layout.addWidget(self.btn_gen_signal)
        common_panel.setLayout(layout)
        self.main_layout.addWidget(common_panel)

    @Slot()
    def _generate_signals(self, signal_len=None):
        """Genera la señal de entrada, el filtro y la 'verdad fundamental'."""
        if signal_len is not None:
            current_signal_len = signal_len
        elif hasattr(self, 'concepts_visualizer'):
            current_signal_len = self.concepts_visualizer.slider_L_signal.value()
        else:
            current_signal_len = TOTAL_SIGNAL_LEN

        # Generar filtro (Respuesta al impulso h[n] de longitud M)
        self.h_full = np.hamming(self.M)
        self.h_full = self.h_full / np.sum(self.h_full)

        # Generar señal (Entrada x[n])
        self.x_full = np.zeros(current_signal_len)
        self.x_full[int(current_signal_len * 0.15)] = 1.0
        self.x_full[int(current_signal_len * 0.35)] = -0.7
        self.x_full[int(current_signal_len * 0.62)] = 0.9
        self.x_full += 0.05 * np.random.randn(current_signal_len)  # Ruido leve

        # Calcular la "Verdad Fundamental" (Convolución Lineal)
        self.y_true = np.convolve(self.x_full, self.h_full, mode='full')

        # Notificar a las pestañas para que se actualicen, si ya existen
        if hasattr(self, 'concepts_visualizer'):
            # La pestaña 0 no depende de estas señales largas
            self.concepts_visualizer.update_with_new_signals()
            self.ola_ols_visualizer.update_with_new_signals()


class ConvolutionMechanicsVisualizer(QWidget):
    """Pestaña para explicar la mecánica de la convolución paso a paso."""

    def __init__(self, main_window: MainVisualizerWindow):
        super().__init__()
        # FIX: renombrado a main_window para evitar colisión con QWidget.parent()
        self.main_window = main_window
        # FIX: renombrado a main_layout para evitar colisión con QWidget.layout()
        self.main_layout = QVBoxLayout(self)

        # --- Estado ---
        self.x = np.array([])
        self.h = np.array([])
        self.y_lin = np.array([])
        self.y_circ = np.array([])
        self.n_step = 0
        self.N = 8  # Tamaño para convolución circular

        # --- Controles ---
        controls_group = QGroupBox("Parámetros de las Señales")
        controls_layout = QHBoxLayout(controls_group)

        form_layout = QFormLayout()
        self.spin_len_x = QSpinBox()
        self.spin_len_x.setRange(3, 16)
        self.spin_len_x.setValue(5)
        form_layout.addRow("Longitud de x[n]:", self.spin_len_x)

        self.spin_len_h = QSpinBox()
        self.spin_len_h.setRange(3, 16)
        self.spin_len_h.setValue(4)
        form_layout.addRow("Longitud de h[n]:", self.spin_len_h)

        self.combo_N_circ = QComboBox()
        self.combo_N_circ.addItems([str(i) for i in range(4, 33)])
        self.combo_N_circ.setCurrentText("8")
        form_layout.addRow("Tamaño N (Circular):", self.combo_N_circ)
        controls_layout.addLayout(form_layout)

        sim_layout = QVBoxLayout()
        self.btn_gen = QPushButton("Generar Señales")
        self.btn_reset = QPushButton("Reiniciar Animación")
        self.btn_next = QPushButton("Siguiente Paso >>")
        sim_layout.addWidget(self.btn_gen)
        sim_layout.addWidget(self.btn_reset)
        sim_layout.addWidget(self.btn_next)
        controls_layout.addLayout(sim_layout)

        self.main_layout.addWidget(controls_group)

        # --- Gráficos ---
        plot_widget = QWidget()
        plot_layout = QHBoxLayout(plot_widget)

        # Panel Izquierdo: Convolución Circular
        circ_group = QGroupBox("Convolución Circular")
        circ_layout = QVBoxLayout(circ_group)
        # FIX: usar Figure() directamente en lugar de plt.figure() para evitar
        # registro en el estado global de matplotlib
        self.fig_circ = Figure(figsize=(6, 8))
        gs_circ = self.fig_circ.add_gridspec(2, 1, height_ratios=[3, 1])
        ax_c_main = self.fig_circ.add_subplot(gs_circ[0], projection='3d')
        ax_c_res = self.fig_circ.add_subplot(gs_circ[1])
        self.axes_circ = (ax_c_main, ax_c_res)
        self.canvas_circ = FigureCanvas(self.fig_circ)
        circ_layout.addWidget(self.canvas_circ)
        plot_layout.addWidget(circ_group)

        # Panel Derecho: Convolución Lineal
        lin_group = QGroupBox("Convolución Lineal")
        lin_layout = QVBoxLayout(lin_group)
        # FIX: usar Figure() directamente en lugar de plt.subplots()
        self.fig_lin = Figure(figsize=(6, 8))
        gs_lin = self.fig_lin.add_gridspec(2, 1, height_ratios=[3, 1])
        self.axes_lin = (
            self.fig_lin.add_subplot(gs_lin[0]),
            self.fig_lin.add_subplot(gs_lin[1])
        )
        self.canvas_lin = FigureCanvas(self.fig_lin)
        lin_layout.addWidget(self.canvas_lin)
        plot_layout.addWidget(lin_group)

        self.main_layout.addWidget(plot_widget)

        # Conexiones
        self.btn_gen.clicked.connect(self.generate_signals)
        self.btn_reset.clicked.connect(self.reset_animation)
        self.btn_next.clicked.connect(self.next_step)
        self.combo_N_circ.currentTextChanged.connect(self.reset_animation)

        # Inicializar
        self.generate_signals()

    @Slot()
    def generate_signals(self):
        len_x = self.spin_len_x.value()
        len_h = self.spin_len_h.value()
        self.x = np.round(np.random.rand(len_x) * 2 - 1, 1)
        self.h = np.round(np.random.rand(len_h) * 2 - 1, 1)
        self.reset_animation()

    @Slot()
    def reset_animation(self):
        self.n_step = 0
        self.N = int(self.combo_N_circ.currentText())
        self.y_lin = np.zeros(len(self.x) + len(self.h) - 1)
        self.y_circ = np.zeros(self.N)
        self.btn_next.setEnabled(True)
        self.update_plots()

    def _pad_or_truncate(self, arr, N):
        """Pads with zeros or truncates an array to length N."""
        if len(arr) >= N:
            return arr[:N]
        else:
            return np.pad(arr, (0, N - len(arr)), 'constant')

    @Slot()
    def next_step(self):
        # --- Cálculo Lineal ---
        y_n_lin = 0
        for k in range(len(self.x)):
            if 0 <= self.n_step - k < len(self.h):  # Check for overlap
                y_n_lin += self.x[k] * self.h[self.n_step - k]  # Sum product
        if self.n_step < len(self.y_lin):
            self.y_lin[self.n_step] = y_n_lin

        # --- Cálculo Circular ---
        # FIX: eliminada variable h_rev que se calculaba pero nunca se usaba
        y_n_circ = 0
        x_p = self._pad_or_truncate(self.x, self.N)
        h_p = self._pad_or_truncate(self.h, self.N)

        for k in range(self.N):
            # Usamos la fórmula de definición directa para el cálculo
            y_n_circ += x_p[k] * h_p[(self.n_step - k) % self.N]
        if self.n_step < len(self.y_circ):
            self.y_circ[self.n_step] = y_n_circ

        self.update_plots()
        self.n_step += 1

        if self.n_step >= max(len(self.y_lin), len(self.y_circ)) + 1:
            self.btn_next.setEnabled(False)

    def update_plots(self):
        # --- Panel Circular ---
        ax_c_main, ax_c_res = self.axes_circ
        ax_c_main.clear()
        ax_c_res.clear()

        # --- Preparación de datos para 3D ---
        x_pad = self._pad_or_truncate(self.x, self.N)
        h_rev = self.h[::-1]
        h_pad = self._pad_or_truncate(h_rev, self.N)
        # Para visualizar h[(n-k)_N], necesitamos desplazar h_rev por n
        h_shifted_display = np.roll(h_pad, self.n_step)

        theta = np.linspace(0, 2 * np.pi, self.N, endpoint=False)
        radius = 1.0

        # Coordenadas para x[k] en z=1
        x_coords = radius * np.cos(theta)
        y_coords = radius * np.sin(theta)
        z_x = np.full(self.N, 1.5)  # Elevamos la señal x

        # Coordenadas para h[n-k] en z=0
        z_h = np.full(self.N, -1.5)  # Bajamos la señal h

        # --- Dibujo en 3D ---
        ax_c_main.set_title(f"Circular: $y_c[{self.n_step}] = \\sum x[k]h[({self.n_step}-k) \\% {self.N}]$")

        # Colores y tamaños para destacar el inicio (n=0)
        s_base = 50
        c_x_colors = ['blue'] * self.N
        c_x_colors[0] = 'black'

        c_h_colors = ['red'] * self.N
        c_h_colors[self.n_step % self.N] = 'black'  # El 'cero' de h se ha movido

        ax_c_main.scatter(x_coords, y_coords, z_x + x_pad, c=c_x_colors, s=s_base, marker='o', label='$x[k]$ (inicio en negro)')
        ax_c_main.scatter(x_coords, y_coords, z_h + h_shifted_display, c=c_h_colors, s=s_base, marker='o', label=f'$h[({self.n_step}-k)\\%N]$ (inicio en negro)')

        # Dibujar ejes horizontales (círculos) para referencia
        circle_x = np.append(x_coords, x_coords[0])
        circle_y = np.append(y_coords, y_coords[0])
        ax_c_main.plot(circle_x, circle_y, z_x[0], color='gray', linestyle=':', alpha=0.8)
        ax_c_main.plot(circle_x, circle_y, z_h[0], color='gray', linestyle=':', alpha=0.8)

        # Dibujar stems y líneas de conexión
        for i in range(self.N):
            ax_c_main.plot([x_coords[i], x_coords[i]], [y_coords[i], y_coords[i]], [z_x[i], z_x[i] + x_pad[i]], color='blue', alpha=0.4)
            ax_c_main.plot([x_coords[i], x_coords[i]], [y_coords[i], y_coords[i]], [z_h[i], z_h[i] + h_shifted_display[i]], color='red', alpha=0.4)
            ax_c_main.plot([x_coords[i], x_coords[i]], [y_coords[i], y_coords[i]], [z_x[i], z_h[i]], color='gray', linestyle=':', alpha=0.3)

        ax_c_main.set_zlim(-3, 3)
        ax_c_main.view_init(elev=20, azim=45)  # Ajustar ángulo de vista

        stem_container_circ = ax_c_res.stem(self.y_circ, basefmt=" ")
        ax_c_res.set_title(f"Resultado $y_c[n]$ (Largo {self.N})")
        ax_c_res.set_xlim(-1, self.N)
        # Resaltar el último punto calculado
        if self.n_step > 0 and self.n_step <= len(self.y_circ) and len(stem_container_circ.stemlines.get_colors()) >= self.n_step:
            colors = stem_container_circ.stemlines.get_colors().copy()
            colors[self.n_step - 1] = (0, 1, 0, 1)  # Green
            stem_container_circ.stemlines.set_colors(colors)

        # FIX: tight_layout sobre la figura específica, no el estado global de plt
        self.fig_circ.tight_layout()
        self.canvas_circ.draw()

        # --- Panel Lineal ---
        ax_l_main, ax_l_res = self.axes_lin
        ax_l_main.clear()
        ax_l_res.clear()

        ax_l_main.set_title(f"Lineal: $y_l[{self.n_step}] = \\sum x[k]h[{self.n_step}-k]$")
        k_x = np.arange(len(self.x))
        k_h = np.arange(len(self.h))
        h_rev_plot = self.h[::-1]

        ax_l_main.stem(k_x, self.x, linefmt='b-', markerfmt='bo', basefmt=' ', label='x[k]')
        ax_l_main.stem(self.n_step - k_h, h_rev_plot, linefmt='r-', markerfmt='ro', basefmt=' ', label=f'h[{self.n_step}-k]')
        ax_l_main.legend()
        ax_l_main.grid(True)
        ax_l_main.set_xlim(-len(self.h), self.N + len(self.h))

        stem_container_lin = ax_l_res.stem(self.y_lin, basefmt=" ")
        ax_l_res.set_title(f"Resultado $y_l[n]$ (Largo {len(self.y_lin)})")
        ax_l_res.set_xlim(-1, len(self.y_lin))
        # Resaltar el último punto calculado
        if self.n_step > 0 and self.n_step <= len(self.y_lin) and len(stem_container_lin.stemlines.get_colors()) >= self.n_step:
            colors = stem_container_lin.stemlines.get_colors().copy()
            colors[self.n_step - 1] = (0, 1, 0, 1)  # Green
            stem_container_lin.stemlines.set_colors(colors)

        # FIX: tight_layout sobre la figura específica, no el estado global de plt
        self.fig_lin.tight_layout()
        self.canvas_lin.draw()


class ConceptsVisualizer(QWidget):
    """Pestaña para explicar los conceptos de conv. rápida con FFT."""

    def __init__(self, main_window: MainVisualizerWindow):
        super().__init__()
        # FIX: renombrado a main_window para evitar colisión con QWidget.parent()
        self.main_window = main_window
        # FIX: renombrado a main_layout para evitar colisión con QWidget.layout()
        self.main_layout = QVBoxLayout(self)

        # --- Controles ---
        controls_group = QGroupBox("Parámetros de las Señales y la FFT")
        controls_layout = QFormLayout(controls_group)

        self.slider_L_signal = QSlider(Qt.Horizontal)
        self.slider_L_signal.setRange(64, 512)
        self.slider_L_signal.setValue(TOTAL_SIGNAL_LEN)
        self.slider_L_signal.setTickPosition(QSlider.TicksBelow)
        self.label_L_signal = QLabel(f"Longitud Señal x[n] (L_x): {self.slider_L_signal.value()}")
        controls_layout.addRow(self.label_L_signal, self.slider_L_signal)

        self.combo_N_concept = QComboBox()
        self.combo_N_concept.addItems(["64", "128", "256", "300"])
        self.combo_N_concept.setCurrentText("256")
        controls_layout.addRow("Tamaño FFT (N):", self.combo_N_concept)

        self.main_layout.addWidget(controls_group)

        # --- Gráficos ---
        # FIX: usar Figure() directamente en lugar de plt.subplots()
        self.fig = Figure(figsize=(10, 8))
        self.axes = [self.fig.add_subplot(3, 1, i + 1) for i in range(3)]
        self.canvas = FigureCanvas(self.fig)
        self.main_layout.addWidget(self.canvas)

        self.combo_N_concept.currentTextChanged.connect(self.update_plots)
        self.slider_L_signal.valueChanged.connect(self._handle_signal_len_change)

    @Slot(int)
    def _handle_signal_len_change(self, value):
        """Regenera las señales cuando el slider cambia."""
        self.label_L_signal.setText(f"Longitud Señal x[n] (L_x): {value}")
        self.main_window._generate_signals(signal_len=value)

    def update_with_new_signals(self):
        """Llamado cuando se generan nuevas señales."""
        new_val = f"{len(self.main_window.x_full) + self.main_window.M - 1} (L_x+M-1)"

        self.combo_N_concept.blockSignals(True)
        # FIX: eliminar todos los ítems dinámicos (índice >= 4) antes de añadir
        # el nuevo, evitando acumulación si se llama varias veces
        while self.combo_N_concept.count() > 4:
            self.combo_N_concept.removeItem(self.combo_N_concept.count() - 1)
        self.combo_N_concept.addItem(new_val)
        self.combo_N_concept.blockSignals(False)
        self.update_plots()

    @Slot()
    def update_plots(self):
        """Dibuja los gráficos de conceptos."""
        x = self.main_window.x_full
        h = self.main_window.h_full
        y_lin = self.main_window.y_true

        try:
            N_str = self.combo_N_concept.currentText().split(" ")[0]
            N = int(N_str)
        except (ValueError, IndexError):
            N = 256  # Default

        # Calcular convolución circular
        X_k = np.fft.fft(x, N)
        H_k = np.fft.fft(h, N)
        y_circ = np.fft.ifft(X_k * H_k).real

        # Limpiar y dibujar
        for ax in self.axes:
            ax.clear()

        # Gráfico 1: Señal x[n]
        self.axes[0].set_title("Señal de Entrada $x[n]$")
        self.axes[0].stem(x, basefmt=" ")
        self.axes[0].grid(True)

        # Gráfico 2: Filtro h[n]
        self.axes[1].set_title(f"Respuesta al Impulso del Filtro $h[n]$ (Longitud M={self.main_window.M})")
        self.axes[1].stem(h, basefmt=" ")
        self.axes[1].grid(True)

        # Gráfico 3: Convoluciones
        self.axes[2].set_title(f"Convolución Lineal vs. Circular (para N={N})")
        self.axes[2].plot(y_lin, 'b-', label=f"Conv. Lineal ($x*h$, Longitud={len(y_lin)})", alpha=0.9, linewidth=2)

        if N >= len(x) + len(h) - 1:
            # Si N es suficiente, la circular es igual a la lineal en la región de interés
            self.axes[2].plot(y_circ, 'ro', markersize=4, label="Conv. Circular (puntos coinciden con la lineal)")
            self.axes[2].axvspan(-0.5, len(y_lin) - 0.5, color='green', alpha=0.2, label=f"Región Válida (L_x+M-1 = {len(y_lin)})")
            self.axes[2].text(0.5, 0.6, "¡Coinciden!", transform=self.axes[2].transAxes,
                              ha='center', va='center', fontsize=14, color='green',
                              bbox=dict(boxstyle='round,pad=0.5', fc='lightgreen', alpha=0.5))
        else:
            # Si N no es suficiente, hay aliasing
            self.axes[2].plot(y_circ, 'r--', label=f"Conv. Circular ($x \\circledast_{{{N}}} h$, Longitud={N})", alpha=0.8)
            self.axes[2].text(0.5, 0.5, "¡Aliasing!\nN < L_x+M-1", transform=self.axes[2].transAxes,
                              ha='center', va='center', fontsize=14, color='red',
                              bbox=dict(boxstyle='round,pad=0.5', fc='lightcoral', alpha=0.5))

        self.axes[2].legend()
        self.axes[2].grid(True)
        self.axes[2].set_xlim(0, max(len(y_lin), len(y_circ)))

        # FIX: tight_layout sobre la figura específica, no el estado global de plt
        self.fig.tight_layout()
        self.canvas.draw()


class OLA_OLS_Visualizer(QWidget):
    """Pestaña que contiene el visualizador interactivo de los algoritmos OLA/OLS."""

    def __init__(self, main_window: MainVisualizerWindow):
        super().__init__()
        # FIX: renombrado a main_window para evitar colisión con QWidget.parent()
        self.main_window = main_window
        # FIX: renombrado a main_layout para evitar colisión con QWidget.layout()
        self.main_layout = QVBoxLayout(self)

        # --- Variables de Estado ---
        self.H_k = None
        self.L = 0
        self.N = 0
        self.current_step = 0
        self.total_steps = 0
        self.ola_output_buffer = None
        self.ols_input_buffer = None
        self.y_recon = None

        self._create_control_panel()
        self._create_plot_panel()
        self._connect_signals()

        # Dibujar el filtro inicial (h_full ya está generado por el main window)
        self.update_with_new_signals()

    def _create_control_panel(self):
        """Crea el panel superior con todos los controles."""
        control_group = QGroupBox("Parámetros de los Algoritmos")
        control_layout = QHBoxLayout()

        # --- Columna 1: Configuración ---
        config_layout = QFormLayout()

        self.slider_L = QSlider(Qt.Horizontal)
        self.slider_L.setRange(16, 128)
        self.slider_L.setValue(64)
        self.slider_L.setTickPosition(QSlider.TicksBelow)
        self.label_L = QLabel(f"Tamaño Bloque Datos (L): {self.slider_L.value()}")
        config_layout.addRow(self.label_L, self.slider_L)

        self.combo_N = QComboBox()
        self.combo_N.addItems(["64", "128", "256", "512"])
        self.combo_N.setCurrentText("128")
        config_layout.addRow("Tamaño FFT (N):", self.combo_N)

        self.label_M = QLabel(f"Longitud Filtro (M): {self.main_window.M}")
        config_layout.addRow(self.label_M)

        self.label_status = QLabel("Valide la configuración")
        self.label_status.setStyleSheet("font-weight: bold;")
        config_layout.addRow("Estado:", self.label_status)

        control_layout.addLayout(config_layout)
        control_layout.addSpacing(20)

        # --- Columna 2: Método ---
        method_group = QGroupBox("Método")
        method_layout = QVBoxLayout()
        self.radio_ola = QRadioButton("Overlap-Add (OLA)")
        self.radio_ols = QRadioButton("Overlap-Save (OLS)")
        self.radio_ola.setChecked(True)
        method_layout.addWidget(self.radio_ola)
        method_layout.addWidget(self.radio_ols)
        method_group.setLayout(method_layout)
        control_layout.addWidget(method_group)

        # Botón de explicación
        self.btn_explain = QPushButton("? Explicación del Método")
        self.btn_explain.setToolTip("Muestra una explicación del método seleccionado")
        control_layout.addWidget(self.btn_explain, 0, Qt.AlignBottom)

        # --- Columna extra: Visualización del filtro ---
        filter_plot_group = QGroupBox("Filtro h[n]")
        filter_plot_layout = QVBoxLayout()
        # FIX: usar Figure() directamente en lugar de plt.subplots()
        self.fig_h = Figure(figsize=(2, 2))
        self.ax_h = self.fig_h.add_subplot(1, 1, 1)
        self.canvas_h = FigureCanvas(self.fig_h)
        filter_plot_layout.addWidget(self.canvas_h)
        filter_plot_group.setLayout(filter_plot_layout)
        control_layout.addWidget(filter_plot_group)

        # --- Columna 3: Control de Simulación ---
        sim_layout = QVBoxLayout()
        self.btn_start = QPushButton("Iniciar / Reiniciar")
        self.btn_next = QPushButton("Siguiente Bloque >>")
        self.btn_next.setEnabled(False)
        sim_layout.addWidget(self.btn_start)
        sim_layout.addWidget(self.btn_next)
        control_layout.addLayout(sim_layout)

        control_group.setLayout(control_layout)
        self.main_layout.addWidget(control_group)

    def _create_plot_panel(self):
        """Crea el panel inferior con los 3 gráficos de Matplotlib."""
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)

        # FIX: usar Figure() directamente en lugar de plt.subplots()
        # --- Gráfico 1: Salida Global ---
        self.fig1 = Figure()
        self.ax1 = self.fig1.add_subplot(1, 1, 1)
        self.canvas1 = FigureCanvas(self.fig1)
        plot_layout.addWidget(self.canvas1)

        # --- Gráfico 2: Proceso de Entrada (Bloque) ---
        self.fig2 = Figure()
        self.ax2 = self.fig2.add_subplot(1, 1, 1)
        self.canvas2 = FigureCanvas(self.fig2)
        plot_layout.addWidget(self.canvas2)

        # --- Gráfico 3: Proceso de Salida (Bloque) ---
        self.fig3 = Figure()
        self.ax3 = self.fig3.add_subplot(1, 1, 1)
        self.canvas3 = FigureCanvas(self.fig3)
        plot_layout.addWidget(self.canvas3)

        self.main_layout.addWidget(plot_widget)

        # Ajustar layout para dar más espacio a los gráficos
        self.main_layout.setStretchFactor(plot_widget, 1)

    def _connect_signals(self):
        """Conecta los botones y sliders a sus funciones (slots)."""
        self.btn_start.clicked.connect(self._start_simulation)
        self.btn_next.clicked.connect(self._next_step)
        self.btn_explain.clicked.connect(self._show_explanation_popup)
        self.slider_L.valueChanged.connect(self._validate_params)
        self.combo_N.currentTextChanged.connect(self._validate_params)
        # FIX: usar lambda para ignorar el disparo al DESMARCAR (checked=False),
        # evitando la doble validación cuando se alterna entre radio buttons
        self.radio_ola.toggled.connect(lambda checked: self._validate_params() if checked else None)
        self.radio_ols.toggled.connect(lambda checked: self._validate_params() if checked else None)

    @Slot()
    def update_with_new_signals(self):
        """Se llama cuando el padre genera nuevas señales."""
        self.label_M.setText(f"Longitud Filtro (M): {self.main_window.M}")
        self.ax_h.clear()
        self.ax_h.stem(self.main_window.h_full, basefmt=" ")
        self.ax_h.set_title(f"h[n] (M={self.main_window.M})", fontsize=8)
        self.ax_h.grid(True)
        self.fig_h.tight_layout()
        self.canvas_h.draw()
        self._start_simulation()

    @Slot()
    def _show_explanation_popup(self):
        """Muestra un pop-up con la explicación del método actual."""
        from PySide6.QtWidgets import QMessageBox

        if self.radio_ola.isChecked():
            title = "Explicación de Overlap-Add (OLA)"
            text = (
                "<h3>Idea Central:</h3>"
                "<p>Procesar bloques de entrada <b>sin solapamiento</b> y gestionar la 'cola' de la convolución que se desborda de cada bloque, <b>sumándola</b> al inicio del siguiente.</p>"
                "<ul>"
                "<li><b>Entrada:</b> Se toman bloques de datos de longitud L (sin solapamiento).</li>"
                "<li><b>Padding:</b> Cada bloque se rellena con M-1 ceros para prevenir el aliasing.</li>"
                "<li><b>Salida:</b> La 'cola' de M-1 muestras de cada bloque de salida se <b>SOLAPA y SUMA</b> con el inicio del siguiente.</li>"
                "</ul>"
            )
        else:  # OLS
            title = "Explicación de Overlap-Save (OLS)"
            text = (
                "<h3>Idea Central:</h3>"
                "<p>Permitir que ocurra el error de la convolución circular, procesando bloques de entrada <b>solapados</b>, y luego <b>descartar</b> la parte corrupta de la salida.</p>"
                "<ul>"
                "<li><b>Entrada:</b> Se construyen bloques de longitud N, usando M-1 muestras del bloque anterior y L datos nuevos.</li>"
                "<li><b>Padding:</b> No se necesita relleno de ceros en la entrada.</li>"
                "<li><b>Salida:</b> Las primeras M-1 muestras (corruptas por aliasing) se <b>DESCARTAN</b>. El resto se <b>GUARDA</b> y concatena.</li>"
                "</ul>"
            )
        QMessageBox.information(self, title, text)

    @Slot()
    def _validate_params(self):
        """Valida N vs L+M-1 y actualiza el slider de L."""
        try:
            self.N = int(self.combo_N.currentText())
        except ValueError:
            self.N = 128  # Default

        M = self.main_window.M

        if self.radio_ola.isChecked():
            # En OLA, el usuario define L, y N debe ser >= L+M-1
            self.L = self.slider_L.value()
            self.label_L.setText(f"Tamaño Bloque Datos (L): {self.L}")
            min_N = self.L + M - 1
            if self.N < min_N:
                self.label_status.setText(f"INVÁLIDO (N debe ser >= {min_N})")
                self.label_status.setStyleSheet("color: red; font-weight: bold;")
                self.btn_start.setEnabled(False)
            else:
                self.label_status.setText(f"VÁLIDO (N={self.N} >= {min_N})")
                self.label_status.setStyleSheet("color: green; font-weight: bold;")
                self.btn_start.setEnabled(True)

        elif self.radio_ols.isChecked():
            # En OLS, el usuario define N, y L se calcula
            self.L = self.N - M + 1
            if self.L <= 0:
                self.label_status.setText(f"INVÁLIDO (N debe ser > M-1 = {M - 1})")
                self.label_status.setStyleSheet("color: red; font-weight: bold;")
                self.btn_start.setEnabled(False)
            else:
                # Ajustar el slider L para que no sea editable, solo muestre el valor
                self.slider_L.setValue(self.L)
                self.label_L.setText(f"Tamaño Datos Nuevos (L): {self.L}")
                self.label_status.setText(f"VÁLIDO (L = N-M+1 = {self.L})")
                self.label_status.setStyleSheet("color: green; font-weight: bold;")
                self.btn_start.setEnabled(True)

        # Deshabilitar "Siguiente" hasta que se inicie
        self.btn_next.setEnabled(False)

    @Slot()
    def _start_simulation(self):
        """Reinicia el estado de la simulación y prepara los gráficos."""
        if self.main_window.x_full is None:
            return  # Aún no se han generado señales

        self._validate_params()  # Carga L y N correctos
        if "INVÁLIDO" in self.label_status.text():
            return

        # FIX: eliminados los print() de depuración
        self.current_step = 0
        self.y_recon = np.zeros_like(self.main_window.y_true)

        # Pre-calcular FFT del filtro (con padding N)
        self.H_k = np.fft.fft(self.main_window.h_full, self.N)

        if self.radio_ola.isChecked():
            # Buffer para la "cola" de salida
            self.ola_output_buffer = np.zeros(self.main_window.M - 1)
            self.total_steps = int(np.ceil(len(self.main_window.x_full) / self.L))
        else:
            # Buffer para el "solapamiento" de entrada
            self.ols_input_buffer = np.zeros(self.main_window.M - 1)
            self.total_steps = int(np.ceil(len(self.main_window.x_full) / self.L))

        self.btn_next.setEnabled(True)
        self.btn_next.setText("Siguiente Bloque (0/?)")

        # Limpiar datos de gráficos
        self.plot_data_in = np.zeros(self.N)
        self.plot_data_out = np.zeros(self.N)
        self.plot_data_linear_conv = np.zeros(self.N + self.main_window.M - 1)

        self._update_plots(initial=True)

    @Slot()
    def _next_step(self):
        """Avanza la simulación un bloque."""
        # FIX: lógica de rango unificada (el bloque era idéntico para OLA y OLS)
        n_start = self.current_step * self.L
        n_end = n_start + self.L

        if n_start >= len(self.main_window.x_full):
            self.btn_next.setText("Simulación Finalizada")
            self.btn_next.setEnabled(False)
            return

        if self.radio_ola.isChecked():
            self._step_ola(n_start, n_end)
        else:
            self._step_ols(n_start, n_end)

        self._update_plots()
        self.current_step += 1
        self.btn_next.setText(f"Siguiente Bloque ({self.current_step}/{self.total_steps})")

    def _step_ola(self, n_start, n_end):
        """Ejecuta un paso del algoritmo Overlap-Add."""

        # 1. Obtener Bloque (L muestras)
        x_i = self.main_window.x_full[n_start:n_end]

        # 2. Rellenar (Pad) a longitud N
        x_pad = np.zeros(self.N)
        x_pad[0:len(x_i)] = x_i

        # 3. Procesar (FFT -> Mult -> IFFT)
        X_k = np.fft.fft(x_pad)
        Y_k = X_k * self.H_k
        y_i = np.fft.ifft(Y_k).real

        # 4. Reconstruir (Add)
        # Sumar la cola del bloque anterior
        y_i[0:self.main_window.M - 1] += self.ola_output_buffer

        # Guardar la nueva cola para el próximo bloque
        self.ola_output_buffer = y_i[self.L: self.L + self.main_window.M - 1]  # = y_i[L:N]

        # Añadir bloque a la salida reconstruida
        out_start = n_start
        out_end = min(out_start + self.L, len(self.y_recon))  # Clip al último bloque
        actual_len = out_end - out_start
        self.y_recon[out_start:out_end] = y_i[0:actual_len]

        # Sumar la cola del último bloque (si la señal no es múltiplo exacto de L)
        if n_end >= len(self.main_window.x_full):
            remaining_len = len(self.y_recon) - out_end
            if remaining_len > 0:
                self.y_recon[out_end: out_end + remaining_len] = self.ola_output_buffer[:remaining_len]

        # Guardar datos para graficar
        self.plot_data_in = x_pad
        self.plot_data_out = y_i
        # La convolución lineal del bloque con padding es lo que queremos comparar
        self.plot_data_linear_conv = np.convolve(x_pad, self.main_window.h_full, mode='full')

    def _step_ols(self, n_start, n_end):
        """Ejecuta un paso del algoritmo Overlap-Save."""
        # 1. Obtener Bloque (N muestras, solapado)
        x_new = self.main_window.x_full[n_start:n_end]

        x_i = np.zeros(self.N)
        x_i[0:self.main_window.M - 1] = self.ols_input_buffer
        x_i[self.main_window.M - 1: self.main_window.M - 1 + len(x_new)] = x_new

        # 2. Procesar (FFT -> Mult -> IFFT)
        X_k = np.fft.fft(x_i)
        Y_k = X_k * self.H_k
        y_i = np.fft.ifft(Y_k).real

        # 3. Descartar y Guardar (Save)
        # La convolución circular corrompe las primeras M-1 muestras.
        y_save = y_i[self.main_window.M - 1: self.main_window.M - 1 + len(x_new)]

        # 4. Reconstruir (Concatenar)
        out_start = n_start
        out_end = out_start + len(y_save)
        self.y_recon[out_start:out_end] = y_save

        # Actualizar buffer de entrada para el próximo ciclo
        self.ols_input_buffer = x_i[self.L: self.L + self.main_window.M - 1]  # = x_i[L:N]

        # Guardar datos para graficar
        self.plot_data_in = x_i
        self.plot_data_out = y_i
        # Para una comparación justa, calculamos la conv. lineal solo de los datos nuevos
        self.plot_data_linear_conv = np.convolve(x_new, self.main_window.h_full, mode='full')

    def _update_plots(self, initial=False):
        """Redibuja todos los gráficos con el estado actual."""

        # --- Limpiar ejes ---
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()

        # --- 1. Gráfico Global (Salida) ---
        self.ax1.set_title("Salida Global $y[n]$", fontsize=10)
        self.ax1.plot(self.main_window.y_true, 'b--', label="Verdad Fundamental (Conv. Lineal)", alpha=0.7)
        self.ax1.plot(self.y_recon, 'r-', label="Salida Reconstruida (OLA/OLS)")
        self.ax1.set_xlim(0, len(self.main_window.y_true))

        # Resaltar el bloque actual
        if not initial:
            if self.radio_ola.isChecked():
                n_start = self.current_step * self.L
                self.ax1.axvspan(n_start, n_start + self.N, color='red', alpha=0.1, label="Bloque Salida Actual (OLA)")
            else:  # OLS
                n_start = self.current_step * self.L
                self.ax1.axvspan(n_start, n_start + self.L, color='red', alpha=0.1, label="Bloque Salida Actual (OLS)")
        self.ax1.legend(loc='upper right', fontsize='small')
        self.ax1.grid(True)

        # --- 2. Gráfico de la Señal de Entrada Completa y Bloque Actual ---
        self.ax2.set_title("Señal de Entrada Completa y Bloque Actual", fontsize=10)
        self.ax2.stem(self.main_window.x_full, basefmt=" ", label="Señal x[n]")
        self.ax2.set_xlim(0, len(self.main_window.x_full))

        if not initial:
            n_start = self.current_step * self.L
            n_end = n_start + self.L
            if self.radio_ola.isChecked():
                self.ax2.axvspan(n_start, n_end, color='cyan', alpha=0.4, label=f"Bloque de datos (L={self.L})")
            else:  # OLS
                self.ax2.axvspan(n_start - (self.main_window.M - 1), n_start, color='orange', alpha=0.3, label="Solapamiento (M-1)")
                self.ax2.axvspan(n_start, n_end, color='cyan', alpha=0.4, label=f"Datos nuevos (L={self.L})")

        self.ax2.legend(loc='upper right', fontsize='small')
        self.ax2.grid(True)

        # --- 3. Gráfico de Salida del Bloque ---
        title_ax3 = f"Bloque de Salida $y_{{{self.current_step}}}[n]$"

        self.ax3.stem(self.plot_data_out, basefmt=" ")

        # Añadir la convolución lineal teórica para comparación
        if self.radio_ola.isChecked():
            self.ax3.plot(self.plot_data_linear_conv, 'k--', alpha=0.8, label='Conv. Lineal (ideal)')
            title_ax3 = "Conv. Circular == Conv. Lineal gracias al padding (N >= L+M-1)"
        else:  # OLS
            self.ax3.plot(self.plot_data_linear_conv, 'k--', alpha=0.6, label='Conv. Lineal (de datos nuevos)')
            title_ax3 = "¡Aliasing! Conv. Circular != Conv. Lineal"

        self.ax3.set_title(title_ax3, fontsize=10)

        if self.radio_ola.isChecked():
            self.ax3.axvspan(self.L, self.N - 1, color='green', alpha=0.3, label=f"Cola a SUMAR (M-1 = {self.main_window.M - 1})")
        else:  # OLS
            self.ax3.axvspan(-0.5, self.main_window.M - 2, color='red', alpha=0.3, label="DESCARTAR (Aliasing Circular)")
            self.ax3.axvspan(self.main_window.M - 2, self.N - 1, color='green', alpha=0.3, label=f"GUARDAR (L = {self.L})")
        self.ax3.legend(loc='upper right', fontsize='small')

        self.ax3.set_xlim(-1, max(self.N, len(self.plot_data_linear_conv)))
        self.ax3.grid(True)

        # FIX: tight_layout sobre cada figura individual en lugar del estado global de plt
        self.fig1.tight_layout()
        self.fig2.tight_layout()
        self.fig3.tight_layout()
        self.canvas1.draw()
        self.canvas2.draw()
        self.canvas3.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Aplicar un estilo (opcional, pero se ve bien)
    try:
        import qdarktheme
        app.setStyleSheet(qdarktheme.load_stylesheet())
    except ImportError:
        pass  # Usar estilo por defecto si qdarktheme no está instalado

    window = MainVisualizerWindow()
    window.show()
    sys.exit(app.exec())
