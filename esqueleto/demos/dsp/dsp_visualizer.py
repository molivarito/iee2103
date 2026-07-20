import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.signal import resample_poly, get_window

# --- 1. Configuración de la Ventana Principal ---
class DSPVisualizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración inicial de CTk
        ctk.set_appearance_mode("System")
        self.title("DSP Visualizer: Análisis Espectral y Remuestreo")
        self.geometry("1400x950")
        
        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- Contenedor Principal de Controles con Pestañas ---
        self.tab_view = ctk.CTkTabview(self, width=400, command=self.update_plots)
        self.tab_view.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.tab_view.add("Análisis Espectral")
        self.tab_view.add("Remuestreo")
        self.tab_view.set("Análisis Espectral")
        self.tab_view.tab("Análisis Espectral").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Remuestreo").grid_columnconfigure(0, weight=1)

        # --- Frame de Gráficos ---
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.plot_frame.grid_rowconfigure((0, 1), weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)
        
        self.create_plots()
        self.create_controls()
        
        self.update_plots()

    # --- 2. Creación de Controles (Modularizado por Pestañas) ---
    def create_controls(self):
        self._create_spectral_analysis_controls(self.tab_view.tab("Análisis Espectral"))
        self._create_resampling_controls(self.tab_view.tab("Remuestreo"))

    def _create_spectral_analysis_controls(self, tab):
        ctk.CTkLabel(tab, text="Controles de Señal y Ventana", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 20))
        row_idx = 1

        # Fs
        ctk.CTkLabel(tab, text="Frec. Muestreo ($F_s$)").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.sa_fs_slider = ctk.CTkSlider(tab, from_=100, to=1000, number_of_steps=90, command=self.update_plots)
        self.sa_fs_slider.set(200)
        self.sa_fs_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.sa_fs_label = ctk.CTkLabel(tab, text="200 Hz")
        self.sa_fs_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2

        # f0
        ctk.CTkLabel(tab, text="Frec. Sinusoide ($f_0$)").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.sa_f0_slider = ctk.CTkSlider(tab, from_=1, to=100, number_of_steps=99, command=self.update_plots)
        self.sa_f0_slider.set(31)
        self.sa_f0_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.sa_f0_label = ctk.CTkLabel(tab, text="31 Hz")
        self.sa_f0_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2
        
        # Tipo de Ventana
        ctk.CTkLabel(tab, text="Tipo de Ventana").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.sa_window_var = ctk.StringVar(value="rectangular")
        ctk.CTkOptionMenu(tab, values=["rectangular", "hann", "blackman"], variable=self.sa_window_var, command=self.update_plots).grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        row_idx += 2

        # Longitud de la DFT (Zero-Padding)
        ctk.CTkLabel(tab, text="Longitud DFT ($N_{fft}$)", font=("Arial", 14, "bold")).grid(row=row_idx, column=0, columnspan=2, pady=(20, 10))
        row_idx += 1
        ctk.CTkLabel(tab, text="Factor (x N)").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.sa_n_fft_slider = ctk.CTkSlider(tab, from_=1, to=32, number_of_steps=31, command=self.update_plots)
        self.sa_n_fft_slider.set(16)
        self.sa_n_fft_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.sa_n_fft_label = ctk.CTkLabel(tab, text="N_fft = 2048")
        self.sa_n_fft_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2

        # Zoom Espectral
        ctk.CTkLabel(tab, text="Zoom Espectral").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.sa_zoom_slider = ctk.CTkSlider(tab, from_=1, to=20, number_of_steps=19, command=self.update_plots)
        self.sa_zoom_slider.set(1)
        self.sa_zoom_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.sa_zoom_label = ctk.CTkLabel(tab, text="Zoom: 1x")
        self.sa_zoom_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2
        
        # Normalización
        self.sa_norm_var = ctk.StringVar(value="Hz")
        ctk.CTkOptionMenu(tab, values=["Hz", "Normalizada ($\omega$)"], variable=self.sa_norm_var, command=self.update_plots).grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    def _create_resampling_controls(self, tab):
        ctk.CTkLabel(tab, text="Controles de Señal y Operación", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 20))
        row_idx = 1

        # Fs
        ctk.CTkLabel(tab, text="Frec. Muestreo ($F_s$)").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.rs_fs_slider = ctk.CTkSlider(tab, from_=50, to=1000, number_of_steps=95, command=self.update_plots)
        self.rs_fs_slider.set(200)
        self.rs_fs_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.rs_fs_label = ctk.CTkLabel(tab, text="200 Hz")
        self.rs_fs_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2

        # f0
        ctk.CTkLabel(tab, text="Frec. Sinusoide ($f_0$)").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.rs_f0_slider = ctk.CTkSlider(tab, from_=1, to=100, number_of_steps=99, command=self.update_plots)
        self.rs_f0_slider.set(40)
        self.rs_f0_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.rs_f0_label = ctk.CTkLabel(tab, text="40 Hz")
        self.rs_f0_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2

        # Operación
        ctk.CTkLabel(tab, text="Operación de Remuestreo", font=("Arial", 14, "bold")).grid(row=row_idx, column=0, columnspan=2, pady=(20, 10))
        row_idx += 1
        self.rs_op_var = ctk.StringVar(value="L")
        ctk.CTkRadioButton(tab, text="Expansión (L)", variable=self.rs_op_var, value="L", command=self.update_plots).grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        row_idx += 1
        ctk.CTkRadioButton(tab, text="Diezmado (M)", variable=self.rs_op_var, value="M", command=self.update_plots).grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        row_idx += 1
        ctk.CTkRadioButton(tab, text="Remuestreo (L/M)", variable=self.rs_op_var, value="L/M", command=self.update_plots).grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        row_idx += 1

        # Factor L
        ctk.CTkLabel(tab, text="Factor L").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.rs_L_slider = ctk.CTkSlider(tab, from_=1, to=5, number_of_steps=4, command=self.update_plots)
        self.rs_L_slider.set(3)
        self.rs_L_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.rs_L_label = ctk.CTkLabel(tab, text="L=3")
        self.rs_L_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2

        # Factor M
        ctk.CTkLabel(tab, text="Factor M").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        self.rs_M_slider = ctk.CTkSlider(tab, from_=1, to=5, number_of_steps=4, command=self.update_plots)
        self.rs_M_slider.set(2)
        self.rs_M_slider.grid(row=row_idx + 1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.rs_M_label = ctk.CTkLabel(tab, text="M=2")
        self.rs_M_label.grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        row_idx += 2
        
        # Opciones
        self.rs_norm_var = ctk.StringVar(value="Hz")
        ctk.CTkOptionMenu(tab, values=["Hz", "Normalizada ($\omega$)"], variable=self.rs_norm_var, command=self.update_plots).grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        row_idx += 1
        self.rs_sim_aliasing_var = ctk.BooleanVar(value=False)
        self.rs_sim_aliasing_checkbox = ctk.CTkCheckBox(tab, text="Simular Diezmado SIN FILTRO", variable=self.rs_sim_aliasing_var, command=self.update_plots)
        self.rs_sim_aliasing_checkbox.grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    # --- 3. Inicialización de Gráficos ---
    def create_plots(self):
        self.fig1, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 4.5), layout='constrained')
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.plot_frame)
        self.canvas1_widget = self.canvas1.get_tk_widget()
        self.canvas1_widget.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.fig2, (self.ax3, self.ax4) = plt.subplots(2, 1, figsize=(6, 4.5), layout='constrained')
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.plot_frame)
        self.canvas2_widget = self.canvas2.get_tk_widget()
        self.canvas2_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
 
    # --- 4. Lógica de Actualización Principal ---
    def update_plots(self, value=None):
        current_tab = self.tab_view.get()
        
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            self._clear_and_style_ax(ax)

        if current_tab == "Análisis Espectral":
            self._update_spectral_analysis_plots()
        elif current_tab == "Remuestreo":
            self._update_resampling_plots()

        self.canvas1.draw()
        self.canvas2.draw()

    # --- Funciones Auxiliares de Estilo y Ejes ---
    def _get_freq_axis(self, Fs, N_points, norm_mode):
        f_axis_hz = np.fft.fftfreq(N_points, 1/Fs)
        if norm_mode == "Normalizada ($\omega$)":
            return np.fft.fftshift(f_axis_hz * 2 * np.pi / Fs), rf'$\omega$ (rad/muestra)', np.pi
        else:
            return np.fft.fftshift(f_axis_hz), 'Frecuencia (Hz)', Fs / 2

    def _clear_and_style_ax(self, ax):
        ax.clear()
        ax.grid(True, which='both', linestyle=':', linewidth=0.6, alpha=0.7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='both', which='major', labelsize=8)

    # --- Lógica de Actualización por Pestaña ---
    def _update_spectral_analysis_plots(self):
        # Obtener parámetros
        F_s = self.sa_fs_slider.get()
        f0 = self.sa_f0_slider.get()
        window_type = self.sa_window_var.get()
        n_fft_multiplier = int(self.sa_n_fft_slider.get())
        zoom_factor = self.sa_zoom_slider.get()
        norm_mode = self.sa_norm_var.get()
        N = 128
        N_fft = N * n_fft_multiplier

        # Validar y actualizar GUI
        f0_max = F_s / 2
        self.sa_f0_slider.configure(to=f0_max, number_of_steps=int(f0_max - 1))
        if f0 > f0_max: f0 = f0_max; self.sa_f0_slider.set(f0)
        self.sa_fs_label.configure(text=f"{F_s:.0f} Hz")
        self.sa_f0_label.configure(text=f"{f0:.0f} Hz")
        self.sa_n_fft_label.configure(text=f"N_fft = {N_fft}")
        self.sa_zoom_label.configure(text=f"Zoom: {int(zoom_factor)}x")
        if zoom_factor == 1: zoom_factor = 0

        # Generar señal y ventana
        t = np.arange(N) * (1.0 / F_s)
        x_n = np.sin(2 * np.pi * f0 * t)
        window = get_window(window_type, N)
        x_w = x_n * window

        # --- Gráficos de Tiempo ---
        self.ax1.plot(t, x_n, '.-', label='Señal Original', alpha=0.5)
        (markers, _, _) = self.ax1.stem(t, x_w, linefmt='C0-', markerfmt='o', basefmt=' ', label=f'Señal Ventaneada ({window_type})')
        plt.setp(markers, 'markersize', 3)
        self.ax1.set_title(f'Señal Original y Ventaneada (N={N})', fontsize=11)
        
        x_padded = np.pad(x_w, (0, N_fft - N), 'constant')
        t_padded = np.arange(N_fft) * (1.0 / F_s)
        (markers, _, _) = self.ax2.stem(t_padded, x_padded, linefmt='C1-', markerfmt='.', basefmt=' ', label=f'Señal con Zero-Padding ($N_{{fft}}={N_fft}$)')
        plt.setp(markers, 'markersize', 3)
        self.ax2.set_title(f'Señal Rellenada con Ceros', fontsize=11)
        self.ax2.set_xlim(left=0, right=t_padded[-1] * 1.1 if N_fft > N else t[-1] * 1.1)

        # --- Gráficos de Frecuencia ---
        f_axis, label_x, _ = self._get_freq_axis(F_s, N_fft, norm_mode)
        X_w_fft = np.fft.fft(x_w, n=N_fft)
        X_w_fft_shifted = np.fft.fftshift(X_w_fft)
        
        W_fft = np.fft.fft(window, n=N_fft)
        W_fft_shifted = np.fft.fftshift(W_fft)

        # Añadir epsilon para evitar log10(0)
        self.ax3.plot(f_axis, 20 * np.log10(np.abs(W_fft_shifted) / np.max(np.abs(W_fft_shifted)) + 1e-9), color='C0', label=f'Espectro de la Ventana ({window_type})')
        self.ax3.set_title('Espectro de la Ventana (dB)', fontsize=11)
        self.ax3.set_ylim(-100, 5)

        self.ax4.plot(f_axis, np.abs(X_w_fft_shifted), color='C1', linewidth=1.5, label=f'DFT con Padding ($N_{{fft}}={N_fft}$)')
        self.ax4.set_title(f'DFT de la Señal Ventaneada', fontsize=11)

        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]: ax.legend(fontsize=8, loc='best')
        for ax in [self.ax3, self.ax4]:
            if zoom_factor > 0:
                zoom_width = (F_s / 4) / zoom_factor
                ax.set_xlim([f0 - zoom_width, f0 + zoom_width] if norm_mode == "Hz" else [(f0 - zoom_width)*2*np.pi/F_s, (f0 + zoom_width)*2*np.pi/F_s])
            else:
                ax.set_xlim([-F_s, F_s] if norm_mode == "Hz" else [-np.pi, np.pi])
            ax.set_xlabel(label_x)
        self.ax1.set_xlabel('Tiempo (s)')
        self.ax2.set_xlabel('Tiempo (s)')

    def _update_resampling_plots(self):
        # Obtener parámetros
        F_s_orig = self.rs_fs_slider.get()
        f0 = self.rs_f0_slider.get()
        L = int(self.rs_L_slider.get())
        M = int(self.rs_M_slider.get())
        operation = self.rs_op_var.get()
        norm_mode = self.rs_norm_var.get()
        sim_aliasing = self.rs_sim_aliasing_var.get()
        N = 128
        N_fft = 4096 # N_fft fijo para remuestreo

        # Validar y actualizar GUI
        f0_max = F_s_orig / 2
        self.rs_f0_slider.configure(to=f0_max, number_of_steps=int(f0_max - 1))
        if f0 > f0_max: f0 = f0_max; self.rs_f0_slider.set(f0)
        self.rs_fs_label.configure(text=f"{F_s_orig:.0f} Hz")
        self.rs_f0_label.configure(text=f"{f0:.0f} Hz")
        self.rs_L_label.configure(text=f"L={L}")
        self.rs_M_label.configure(text=f"M={M}")
        self.rs_sim_aliasing_checkbox.configure(state=ctk.NORMAL if operation == "M" else ctk.DISABLED)
        if operation != "M": self.rs_sim_aliasing_var.set(False)

        # Generar señal
        t_orig = np.arange(N) * (1.0 / F_s_orig)
        x_n = np.sin(2 * np.pi * f0 * t_orig)
        
        L_op, M_op = L, M
        if operation == "L": M_op = 1
        elif operation == "M": L_op = 1

        # Procesamiento
        y_n = resample_poly(x_n, L_op, M_op)
        F_s_new = F_s_orig * L_op / M_op
        t_new = np.arange(len(y_n)) * (1.0 / F_s_new)
        
        # Ejes y Espectros
        f_axis_orig, label_x, _ = self._get_freq_axis(F_s_orig, N_fft, norm_mode)
        f_axis_new, _, F_nyquist_new = self._get_freq_axis(F_s_new, N_fft, norm_mode)
        X_dtft_shifted = np.fft.fftshift(np.fft.fft(x_n, n=N_fft))
        Y_fft_shifted = np.fft.fftshift(np.fft.fft(y_n, n=N_fft))

        # --- Gráficos de Tiempo ---
        if operation == "L" or (operation == "L/M" and L_op > 1):
            x_e = np.zeros(N * L_op); x_e[::L_op] = x_n
            t_e = np.arange(len(x_e)) * (1.0 / F_s_orig / L_op)
            self.ax1.stem(t_e, x_e, linefmt='C1--', markerfmt='.', basefmt=" ", label=f'Señal Expandida $x_e[n]$')
            (m,_,_) = self.ax1.stem(t_orig, x_n, linefmt='C0-', markerfmt='o', basefmt=' ', label='Muestras Originales')
            plt.setp(m, 'markersize', 4)
            self.ax1.set_title(f'Expansión: Inserción de $L-1={L_op-1}$ Ceros', fontsize=11)
        else:
            (m,_,_) = self.ax1.stem(t_orig, x_n, linefmt='C0-', markerfmt='o', basefmt=' ', label=rf'$F_s = {F_s_orig:.0f} \text{{ Hz}}$')
            plt.setp(m, 'markersize', 4)
            self.ax1.set_title(f'Señal Original $x[n]$ ($f_0={f0}$ Hz)', fontsize=11)
        
        if operation == "M":
            if sim_aliasing:
                y_aliased = x_n[::M_op]
                (m,_,_) = self.ax2.stem(t_new, y_aliased, linefmt='C3-', markerfmt='x', basefmt=' ', label=f'Diezmado SIN filtro')
                plt.setp(m, 'markersize', 5)
                self.ax2.set_title(f'Diezmado ($M={M_op}$) SIN Filtro Anti-Aliasing', fontsize=11)
            else:
                self.ax2.plot(t_orig, x_n, ':', color='gray', alpha=0.7, label='Original (ref.)')
                (m,_,_) = self.ax2.stem(t_new, y_n, linefmt='C2-', markerfmt='o', basefmt=' ', label=f'Diezmado CON filtro')
                plt.setp(m, 'markersize', 4)
                self.ax2.set_title(f'Diezmado ($M={M_op}$) con Filtro Anti-Aliasing', fontsize=11)
        elif operation == "L":
            self.ax2.plot(t_new, y_n, '-', color='C2', linewidth=2, label='Interpolada (Filtrada)')
            (m,_,_) = self.ax2.stem(t_orig, x_n, linefmt='C0-', markerfmt='o', basefmt=' ', label='Muestras originales')
            plt.setp(m, 'markersize', 4)
            self.ax2.set_title(f'Interpolación ($L={L_op}$) - Señal Filtrada', fontsize=11)
        else: # L/M
            self.ax2.plot(t_new, y_n, '.-', markersize=4, color='C1', label=f'L/M={L_op}/{M_op}')
            self.ax2.set_title(f'Remuestreo Racional (L/M)', fontsize=11)

        # --- Gráficos de Frecuencia ---
        self.ax3.plot(f_axis_orig, np.abs(X_dtft_shifted), color='C0', linewidth=1.5, label=r'DTFT Original')
        self.ax3.set_title('Espectro Original y Efecto de la Operación', fontsize=11)
        if L_op > 1:
            x_e = np.zeros(N * L_op); x_e[::L_op] = x_n
            f_axis_e, _, _ = self._get_freq_axis(F_s_orig * L_op, N_fft, norm_mode)
            X_e_dtft_shifted = np.fft.fftshift(np.fft.fft(x_e, n=N_fft))
            self.ax3.plot(f_axis_e, np.abs(X_e_dtft_shifted), color='C3', linestyle='--', label=r'Espectro Expandido (Imágenes)')

        if operation == "L":
            # La frecuencia de corte es pi/L, que en el nuevo eje de Fs*L corresponde a Fs_orig/2
            self.ax3.axvspan(-F_s_orig / 2, F_s_orig / 2, alpha=0.2, color='C2', label=r'Filtro Anti-Imagen')
        elif operation == "L/M":
            fc_filter = min(F_s_orig / 2, F_s_new / 2)
            self.ax3.axvspan(-fc_filter, fc_filter, alpha=0.2, color='C4', label=r'Filtro Pasa-Bajos')
        elif operation == "M":
            self.ax3.axvspan(-F_nyquist_new, F_nyquist_new, alpha=0.2, color='C2', label=r'Filtro Anti-Aliasing')

        self.ax4.plot(f_axis_new, np.abs(Y_fft_shifted), color='C2', linewidth=1.5, label='Salida (con filtro)')
        self.ax4.set_title('Espectro de Salida', fontsize=11)
        if operation == "M" and sim_aliasing:
            y_aliased = x_n[::M_op]
            Y_aliased_fft_shifted = np.fft.fftshift(np.fft.fft(y_aliased, n=N_fft))
            self.ax4.plot(f_axis_new, np.abs(Y_aliased_fft_shifted), color='C1', linestyle='--', label='Salida (SIN FILTRO)')
            if f0 > F_s_new / 2:
                 self.ax4.text(0, np.max(np.abs(Y_aliased_fft_shifted)) * 0.8, '⚠️ ALIASING', color='C1', fontsize=10, ha='center', weight='bold')

        self.ax4.axvline(F_nyquist_new, color='C3', linestyle=':', linewidth=1, label=f'Nyquist ({F_nyquist_new:.0f} Hz)')
        self.ax4.axvline(-F_nyquist_new, color='C3', linestyle=':', linewidth=1)
        
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.legend(fontsize=8, loc='best')
        
        self.ax1.set_xlabel('Tiempo (s)')
        self.ax2.set_xlabel('Tiempo (s)')
        self.ax3.set_xlabel(label_x)
        self.ax4.set_xlabel(label_x)

        self.ax3.set_xlim([-1.5 * F_s_orig, 1.5 * F_s_orig] if norm_mode == "Hz" else [-1.5 * np.pi, 1.5 * np.pi])
        self.ax4.set_xlim([-1.5 * F_s_new, 1.5 * F_s_new] if norm_mode == "Hz" else [-1.5 * np.pi, 1.5 * np.pi])

if __name__ == "__main__":
    app = DSPVisualizerApp()
    app.mainloop()
