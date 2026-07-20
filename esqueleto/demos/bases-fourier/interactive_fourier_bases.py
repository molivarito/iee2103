# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d import Axes3D # Necesario para proyección 3D
import math 

# --- Variables Globales para los Elementos del Gráfico ---
fig_base = None
ax_base_real_stem = None
ax_base_phasor_2d = None
ax_base_spiral_3d = None
ax_base_imag_stem = None

text_base_formula = None 
text_base_periodicity_info = None
slider_N_dft = None 
slider_k_index = None 
slider_phi_base = None 

# --- Función de Actualización ---
def update_base_plots(val_or_event):
    """
    Esta función se llama cada vez que un valor del slider cambia.
    Actualiza los datos de los cuatro gráficos para la función base de la DFT.
    """
    global fig_base, ax_base_real_stem, ax_base_phasor_2d, ax_base_spiral_3d, ax_base_imag_stem
    global text_base_formula, text_base_periodicity_info 
    global slider_N_dft, slider_k_index, slider_phi_base

    N_val = int(slider_N_dft.val)
    k_val = int(slider_k_index.val)
    phi_val = slider_phi_base.val * np.pi 
    amplitud = 1 
    A_str = "A"

    # Asegurar que k_val sea siempre válido
    if k_val >= N_val:
        k_val = N_val - 1
        slider_k_index.set_val(k_val)
    elif N_val <= 0: 
        N_val = 2 
        k_val = 0

    n_indices = np.arange(0, N_val) 

    omega_k_val = 0
    if N_val > 0: 
        omega_k_val = (2 * np.pi * k_val) / N_val

    base_complex_data = amplitud * np.exp(1j * (omega_k_val * n_indices + phi_val))
    base_real_part_data = np.real(base_complex_data)
    base_imag_part_data = np.imag(base_complex_data)

    # 1. Parte Real de la Función Base (Stem Plot) - Color Azul
    ax_base_real_stem.cla() 
    ax_base_real_stem.stem(n_indices, base_real_part_data, 
                           label=r'Re{$\phi_k[n]$}', 
                           basefmt=" ", linefmt='b-', markerfmt='bo') 
    ax_base_real_stem.set_xlabel('n (muestra)')
    ax_base_real_stem.set_ylabel('Amplitud')
    ax_base_real_stem.set_title(rf'Parte Real de la Base $\phi_k[n]$ (k={k_val})') # Uso de rf""
    ax_base_real_stem.grid(True)
    ax_base_real_stem.legend(loc='upper right')
    ax_base_real_stem.set_xlim(-0.5, N_val - 0.5 if N_val > 1 else 0.5)
    ax_base_real_stem.set_ylim(-amplitud*1.1, amplitud*1.1)

    # 2. Fasores en el Plano Complejo (2D Plot)
    ax_base_phasor_2d.cla()
    theta_circ = np.linspace(0, 2*np.pi, 100) 
    ax_base_phasor_2d.plot(amplitud * np.cos(theta_circ), amplitud * np.sin(theta_circ), 'k--', alpha=0.5, linewidth=0.8, label=f'Círculo de Amplitud {A_str}')
    
    step_phasor = max(1, N_val // 15) 
    has_legend_entry_phasor = False 
    if N_val > 0: 
        for i in range(0, N_val, step_phasor):
            label_for_legend = None
            if not has_legend_entry_phasor : 
                label_for_legend = r'Fasores $\phi_k[n]$' # Uso de r""
                has_legend_entry_phasor = True
                
            ax_base_phasor_2d.plot([0, base_real_part_data[i]], [0, base_imag_part_data[i]], 
                              marker='o', markersize=4, linestyle='-', 
                              label=label_for_legend) 
            ax_base_phasor_2d.text(base_real_part_data[i]*1.2, base_imag_part_data[i]*1.2, f'$n={i}$', 
                               fontsize=8, ha='center', va='center', color='blue')
    
    ax_base_phasor_2d.set_xlabel('Parte Real')
    ax_base_phasor_2d.set_ylabel('Parte Imaginaria')
    ax_base_phasor_2d.set_title(rf'Fasores de $\phi_k[n]$ (k={k_val})') # Uso de rf""
    ax_base_phasor_2d.grid(True)
    ax_base_phasor_2d.axis('equal')
    ax_base_phasor_2d.set_xlim(-amplitud*1.3, amplitud*1.3) 
    ax_base_phasor_2d.set_ylim(-amplitud*1.3, amplitud*1.3)
    if has_legend_entry_phasor : 
        ax_base_phasor_2d.legend(loc='upper right', fontsize='small')

    # 3. Espiral 3D de la Función Base con Proyecciones Stem Mejoradas
    ax_base_spiral_3d.cla()
    z_min_proj = -amplitud * 1.15 
    y_max_proj = amplitud * 1.15  

    if N_val > 0: 
        ax_base_spiral_3d.plot3D(n_indices, base_real_part_data, base_imag_part_data, color='deepskyblue', label=r'Espiral $\phi_k[n]$') # Uso de r""
        for i in range(0, N_val, step_phasor): 
            ax_base_spiral_3d.plot3D([n_indices[i], n_indices[i]], [0, base_real_part_data[i]], [z_min_proj, z_min_proj], color='blue', linestyle='-', alpha=0.75, linewidth=1.5)
            ax_base_spiral_3d.scatter(n_indices[i], base_real_part_data[i], z_min_proj, color='blue', marker='o', s=20, alpha=0.9)
        for i in range(0, N_val, step_phasor): 
            ax_base_spiral_3d.plot3D([n_indices[i], n_indices[i]], [y_max_proj, y_max_proj], [0, base_imag_part_data[i]], color='green', linestyle='-', alpha=0.75, linewidth=1.5)
            ax_base_spiral_3d.scatter(n_indices[i], y_max_proj, base_imag_part_data[i], color='green', marker='o', s=20, alpha=0.9)
    
    ax_base_spiral_3d.set_xlabel('n (muestra)')
    ax_base_spiral_3d.set_ylabel('Parte Real')
    ax_base_spiral_3d.set_zlabel('Parte Imaginaria')
    ax_base_spiral_3d.set_title(rf'Espiral 3D de $\phi_k[n]$ (k={k_val}) y Proyecciones Stem') # Uso de rf""
    ax_base_spiral_3d.set_xlim(0, N_val -1 if N_val > 0 else 1)
    ax_base_spiral_3d.set_ylim(-amplitud*1.2, amplitud*1.2) 
    ax_base_spiral_3d.set_zlim(-amplitud*1.2, amplitud*1.2) 
    ax_base_spiral_3d.view_init(elev=20, azim=-60) 

    # 4. Parte Imaginaria de la Función Base (Stem Plot) - Color Verde
    ax_base_imag_stem.cla()
    ax_base_imag_stem.stem(n_indices, base_imag_part_data, 
                           label=r'Im{$\phi_k[n]$}', 
                           basefmt=" ", linefmt='g-', markerfmt='go') 
    ax_base_imag_stem.set_xlabel('n (muestra)')
    ax_base_imag_stem.set_ylabel('Amplitud')
    ax_base_imag_stem.set_title(rf'Parte Imaginaria de la Base $\phi_k[n]$ (k={k_val})') # Uso de rf""
    ax_base_imag_stem.grid(True)
    ax_base_imag_stem.legend(loc='upper right')
    ax_base_imag_stem.set_xlim(-0.5, N_val - 0.5 if N_val > 1 else 0.5)
    ax_base_imag_stem.set_ylim(-amplitud*1.1, amplitud*1.1)

    if fig_base._suptitle is not None:
        fig_base._suptitle.remove()
        fig_base._suptitle = None

    fig_base.suptitle(f'Función Base de Fourier Discreta para N={N_val}', 
                 fontsize=16, y=0.985) 

    phi_formula_part = ""
    if abs(phi_val) > 1e-9:
        sign = "+" if phi_val >=0 else "-"
        phi_formula_part = rf" {sign} {abs(phi_val/np.pi):.2f}\pi" # Uso de rf""


    if N_val == 0:
        formula_str_display = "N debe ser > 0 para definir la base"
    else:
        if text_base_formula.get_usetex(): 
             formula_str_display = rf'$\phi_{{{k_val}}}[n] = e^{{j(\frac{{2\pi \cdot {k_val}}}{{{N_val}}}n{phi_formula_part})}}$' # Uso de rf""
        else: 
            phi_text_part_plain = ""
            if abs(phi_val) > 1e-9:
                 sign_plain = "+" if phi_val >=0 else "-"
                 phi_text_part_plain = f" {sign_plain} {abs(phi_val/np.pi):.2f}π" 

            term_k_N = f"(2π*{k_val}/{N_val})" if N_val > 0 else " indefinido "
            formula_str_display = f"φ_{k_val}[n] = exp(j * ({term_k_N}*n{phi_text_part_plain}))"

    text_base_formula.set_text(formula_str_display)

    period_info_str = rf"Periodicidad de $\phi_{{{k_val}}}[n]$: " # Uso de rf""
    if N_val == 0: 
        period_info_str += "N debe ser > 0"
    elif k_val == 0 and N_val > 0 : 
        period_info_str += "Constante (Período Fundamental Np = 1)"
    elif N_val > 0:
        common_divisor = math.gcd(k_val, N_val) 
        Np_base = N_val // common_divisor
        period_info_str += f"Periódica, Np = {Np_base}"
            
    text_base_periodicity_info.set_text(period_info_str)
    
    fig_base.canvas.draw_idle()

# --- Configuración Inicial de la Figura y Sliders ---
def setup_interactive_dft_bases_plot():
    global fig_base, ax_base_real_stem, ax_base_phasor_2d, ax_base_spiral_3d, ax_base_imag_stem
    global text_base_formula, text_base_periodicity_info 
    global slider_N_dft, slider_k_index, slider_phi_base

    fig_base = plt.figure(figsize=(14, 11)) 
    
    ax_base_real_stem = fig_base.add_subplot(2, 2, 1)
    ax_base_phasor_2d = fig_base.add_subplot(2, 2, 2)
    ax_base_spiral_3d = fig_base.add_subplot(2, 2, 3, projection='3d') 
    ax_base_imag_stem = fig_base.add_subplot(2, 2, 4)
    
    plt.subplots_adjust(left=0.08, bottom=0.25, right=0.95, top=0.85, hspace=0.5, wspace=0.35) 

    init_N = 16 
    init_k = 1
    init_phi_norm = 0.0   

    use_latex_for_formula = False # MANTENER EN FALSE PARA EVITAR CONGELAMIENTO SI LATEX NO ESTÁ BIEN
    text_base_formula = fig_base.text(0.5, 0.94, "", ha='center', va='center', fontsize=14, color='purple', usetex=use_latex_for_formula) 
    text_base_periodicity_info = fig_base.text(0.5, 0.90, "", ha='center', va='center', fontsize=12, color='darkgreen') 

    ax_slider_N_pos = [0.20, 0.12, 0.60, 0.025] 
    ax_slider_k_pos = [0.20, 0.08, 0.60, 0.025]
    ax_slider_phi_pos = [0.20, 0.04, 0.60, 0.025]
    
    slider_ax_N = plt.axes(ax_slider_N_pos)
    slider_N_dft = Slider(
        ax=slider_ax_N,
        label='N (Puntos DFT)', 
        valmin=2, 
        valmax=64, 
        valinit=init_N,
        valstep=1 
    )

    slider_ax_k = plt.axes(ax_slider_k_pos)
    slider_k_index = Slider(
        ax=slider_ax_k,
        label='k (Índice Base)', 
        valmin=0,
        valmax=max(1, init_N - 1), 
        valinit=init_k if init_k < init_N else max(0, init_N -1),
        valstep=1
    )
    
    def on_N_change(val_N_float):
        N_new = int(val_N_float)
        slider_N_dft.valtext.set_text(f'{N_new}') 
        
        current_k = int(slider_k_index.val)
        new_k_max = max(0, N_new - 1) 
        slider_k_index.valmax = new_k_max
        slider_k_index.ax.set_xlim(slider_k_index.valmin, new_k_max if new_k_max > 0 else 1) 
        
        if current_k >= N_new:
            slider_k_index.set_val(new_k_max) 
        else:
            update_base_plots(None)
        
        if not (current_k >= N_new) : 
             slider_k_index.valtext.set_text(f'{int(slider_k_index.val)}')

    slider_N_dft.on_changed(on_N_change)
    
    def on_k_change(val_k_float):
        slider_k_index.valtext.set_text(f'{int(val_k_float)}')
        update_base_plots(None)
    slider_k_index.on_changed(on_k_change)


    slider_ax_phi = plt.axes(ax_slider_phi_pos)
    slider_phi_base = Slider(
        ax=slider_ax_phi,
        label=r'$\phi/\pi$ (Fase)', # Uso de r""
        valmin=-1, 
        valmax=1,
        valinit=init_phi_norm,
        valstep=1/16 
    )
    slider_phi_base.valtext.set_text(rf'{slider_phi_base.val:.3f}$\pi$') # Uso de rf""
    def on_phi_change(val_norm):
        slider_phi_base.valtext.set_text(rf'{val_norm:.3f}$\pi$') # Uso de rf""
        update_base_plots(None)
    slider_phi_base.on_changed(on_phi_change)

    slider_N_dft.valtext.set_text(f'{init_N}')
    slider_k_index.valtext.set_text(f'{init_k if init_k < init_N else max(0, init_N-1)}')

    update_base_plots(None) 
    plt.show()

# --- Ejecución Principal ---
if __name__ == "__main__":
    setup_interactive_dft_bases_plot()
