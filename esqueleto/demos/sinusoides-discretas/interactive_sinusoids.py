# -*- coding: utf-8 -*-
# Asegúrate de que esta línea de arriba sea la PRIMERA o SEGUNDA línea de tu archivo.
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d import Axes3D # Necesario para proyección 3D
import math 

# --- Variables Globales para los Elementos del Gráfico ---
fig = None
ax_real_stem = None
ax_phasor_2d = None
ax_spiral_3d = None
ax_imag_stem = None

text_formula_display = None 
text_periodicity_info = None
slider_omega = None
slider_n_muestras = None
slider_phi = None

# --- Función de Actualización ---
def update_plots(val_or_event):
    """
    Esta función se llama cada vez que un valor del slider cambia.
    Actualiza los datos de los cuatro gráficos.
    """
    global fig, ax_real_stem, ax_phasor_2d, ax_spiral_3d, ax_imag_stem
    global text_formula_display, text_periodicity_info
    global slider_omega, slider_n_muestras, slider_phi

    omega_val = slider_omega.val * np.pi 
    n_muestras_val = int(slider_n_muestras.val)
    phi_val = slider_phi.val * np.pi 
    amplitud = 1 
    A_formula_str = "A" 

    n_indices = np.arange(0, n_muestras_val)

    y_complex_data = amplitud * np.exp(1j * (omega_val * n_indices + phi_val))
    y_real_part_data = np.real(y_complex_data)
    y_imag_part_data = np.imag(y_complex_data)

    # 1. Sinusoide Discreta Real (Stem Plot) - Color Azul
    ax_real_stem.cla() 
    label_real_stem = r"$\mathrm{Re}\{" + A_formula_str + r" e^{j(\Omega n + \phi)}\}$" 
    ax_real_stem.stem(n_indices, y_real_part_data, 
                      label=label_real_stem,
                      basefmt=" ", linefmt='b-', markerfmt='bo') 
    ax_real_stem.set_xlabel('n (muestra)')
    ax_real_stem.set_ylabel('Amplitud')
    ax_real_stem.set_title('Sinusoide Discreta Real / Parte Real')
    ax_real_stem.grid(True)
    ax_real_stem.legend(loc='upper right')
    ax_real_stem.set_xlim(-0.5, n_muestras_val - 0.5 if n_muestras_val > 1 else 0.5)
    ax_real_stem.set_ylim(-amplitud*1.1, amplitud*1.1)

    # 2. Fasores en el Plano Complejo (2D Plot)
    ax_phasor_2d.cla()
    theta_circ = np.linspace(0, 2*np.pi, 100) 
    # CORREGIDO: etiqueta del círculo con concatenación
    label_circulo = 'Círculo de Amplitud ' + A_formula_str
    ax_phasor_2d.plot(amplitud * np.cos(theta_circ), amplitud * np.sin(theta_circ), 'k--', alpha=0.5, linewidth=0.8, label=label_circulo)
    
    step_phasor = max(1, n_muestras_val // 15) 
    has_legend_entry_phasor = False 
    
    # Almacenar posiciones de labels para evitar solapamientos
    label_positions = []
    min_label_distance = amplitud * 0.15  # Distancia mínima entre labels
    
    def adjust_label_position(x, y, existing_positions, min_dist):
        """Ajusta la posición del label para evitar solapamientos"""
        # Posición inicial
        label_x = x * 1.2
        label_y = y * 1.2
        
        # Calcular el ángulo del fasor
        angle = np.arctan2(y, x) if (x != 0 or y != 0) else 0
        
        # Intentar diferentes distancias radiales
        for radial_factor in [1.2, 1.35, 1.5, 1.7, 1.9, 2.1]:
            test_x = x * radial_factor
            test_y = y * radial_factor
            
            # Verificar si esta posición está suficientemente lejos de otros labels
            too_close = False
            for ex_x, ex_y in existing_positions:
                dist = np.sqrt((test_x - ex_x)**2 + (test_y - ex_y)**2)
                if dist < min_dist:
                    too_close = True
                    break
            
            if not too_close:
                return test_x, test_y
        
        # Si no se encontró una buena posición, usar la original pero más lejos
        return x * 1.5, y * 1.5
    
    if n_muestras_val > 0:
        for i in range(0, n_muestras_val, step_phasor):
            label_for_legend = None
            if not has_legend_entry_phasor : 
                label_for_legend = r"Fasores $" + A_formula_str + r" e^{j(\Omega n+\phi)}$" 
                has_legend_entry_phasor = True
                
            ax_phasor_2d.plot([0, y_real_part_data[i]], [0, y_imag_part_data[i]], 
                              marker='o', markersize=4, linestyle='-', 
                              label=label_for_legend) 
            
            # Ajustar posición del label para evitar solapamientos
            label_x, label_y = adjust_label_position(
                y_real_part_data[i], y_imag_part_data[i], 
                label_positions, min_label_distance
            )
            label_positions.append((label_x, label_y))
            
            ax_phasor_2d.text(label_x, label_y, f'$n={i}$', 
                               fontsize=8, ha='center', va='center', color='blue')
    
    ax_phasor_2d.set_xlabel('Parte Real')
    ax_phasor_2d.set_ylabel('Parte Imaginaria')
    ax_phasor_2d.set_title(r'Fasores en Plano Complejo') 
    ax_phasor_2d.grid(True)
    ax_phasor_2d.axis('equal')
    ax_phasor_2d.set_xlim(-amplitud*1.3, amplitud*1.3) 
    ax_phasor_2d.set_ylim(-amplitud*1.3, amplitud*1.3)
    if has_legend_entry_phasor : 
        ax_phasor_2d.legend(loc='upper right', fontsize='small')


    # 3. Espiral 3D de la Sinusoide Compleja con Proyecciones Stem
    ax_spiral_3d.cla()
    z_min_proj = -amplitud * 1.15 
    y_max_proj = amplitud * 1.15  

    if n_muestras_val > 0: 
        label_spiral = r"Espiral $" + A_formula_str + r" e^{j(\Omega n + \phi)}$" 
        ax_spiral_3d.plot3D(n_indices, y_real_part_data, y_imag_part_data, color='deepskyblue', label=label_spiral)
        for i in range(0, n_muestras_val, step_phasor): 
            ax_spiral_3d.plot3D([n_indices[i], n_indices[i]], [0, y_real_part_data[i]], [z_min_proj, z_min_proj], color='blue', linestyle='-', alpha=0.75, linewidth=1.5)
            ax_spiral_3d.scatter(n_indices[i], y_real_part_data[i], z_min_proj, color='blue', marker='o', s=20, alpha=0.9)
        for i in range(0, n_muestras_val, step_phasor): 
            ax_spiral_3d.plot3D([n_indices[i], n_indices[i]], [y_max_proj, y_max_proj], [0, y_imag_part_data[i]], color='green', linestyle='-', alpha=0.75, linewidth=1.5)
            ax_spiral_3d.scatter(n_indices[i], y_max_proj, y_imag_part_data[i], color='green', marker='o', s=20, alpha=0.9)
    
    ax_spiral_3d.set_xlabel('n (muestra)')
    ax_spiral_3d.set_ylabel('Parte Real')
    ax_spiral_3d.set_zlabel('Parte Imaginaria')
    ax_spiral_3d.set_title('Espiral 3D y Proyecciones Stem')
    ax_spiral_3d.set_xlim(0, n_muestras_val -1 if n_muestras_val > 0 else 1)
    ax_spiral_3d.set_ylim(-amplitud*1.2, amplitud*1.2) 
    ax_spiral_3d.set_zlim(-amplitud*1.2, amplitud*1.2) 
    ax_spiral_3d.view_init(elev=20, azim=-60) 

    # 4. Parte Imaginaria de la Sinusoide Compleja (Stem Plot) - Color Verde
    ax_imag_stem.cla()
    label_imag_stem = r"$\mathrm{Im}\{" + A_formula_str + r" e^{j(\Omega n + \phi)}\}$" 
    ax_imag_stem.stem(n_indices, y_imag_part_data, 
                      label=label_imag_stem,
                      basefmt=" ", linefmt='g-', markerfmt='go') 
    ax_imag_stem.set_xlabel('n (muestra)')
    ax_imag_stem.set_ylabel('Amplitud')
    ax_imag_stem.set_title('Parte Imaginaria de Sinusoide Compleja')
    ax_imag_stem.grid(True)
    ax_imag_stem.legend(loc='upper right')
    ax_imag_stem.set_xlim(-0.5, n_muestras_val - 0.5 if n_muestras_val > 1 else 0.5)
    ax_imag_stem.set_ylim(-amplitud*1.1, amplitud*1.1)

    if fig._suptitle is not None:
        fig._suptitle.remove()
        fig._suptitle = None

    fig.suptitle(f'Visualizador de Sinusoides Discretas', fontsize=16, y=0.99)

    omega_str_val = omega_val/np.pi
    phi_str_val = phi_val/np.pi
    
    omega_latex_str = rf"{omega_str_val:.3f}\pi"
    phi_latex_str = rf"{phi_str_val:.3f}\pi"

    omega_plain_str = f"{omega_str_val:.3f}π" 
    phi_plain_str = f"{phi_str_val:.3f}π"

    if text_formula_display.get_usetex():
        formula_str_display = rf"${A_formula_str} e^{{j(\Omega n + \phi)}}$  con $\Omega = {omega_latex_str}$, $\phi = {phi_latex_str}$"
    else:
        formula_str_display = f"{A_formula_str} exp(j * (Ωn + φ))  con Ω = {omega_plain_str}, φ = {phi_plain_str}"

    text_formula_display.set_text(formula_str_display)

    period_info_str = "Periodicidad: "
    if abs(omega_val) < 1e-9:
        period_info_str += "Constante (Período Fundamental Np = 1)"
    else:
        found_period = False
        # Aumentar el límite de búsqueda puede ser útil, pero con cuidado para no ralentizar.
        max_Np_search = 500 
        
        # Simplificar la lógica de casos especiales. El método general de ratio los cubre.
        if not found_period:
            ratio = omega_val / (2 * np.pi)
            # Evitar división por cero si ratio es muy pequeño
            if abs(ratio) < 1e-9:
                 period_info_str += "Constante (Período Fundamental Np = 1)"
                 found_period = True

        if not found_period:
            for den_test in range(1, max_Np_search + 1):
                num_test_float = ratio * den_test
                if abs(num_test_float - round(num_test_float)) < 1e-5: 
                    num = int(round(num_test_float))
                    den = den_test
                    if den == 0: continue
                    common_divisor = math.gcd(num, den) 
                    simplified_m = num // common_divisor
                    simplified_Np = den // common_divisor
                    
                    if simplified_Np > 0: 
                        period_info_str += f"Periódica, Np = {simplified_Np} (m={simplified_m})"
                        found_period = True
                        break
        
        if not found_period:
            period_info_str += "No periódica (o Np > límite de búsqueda)"
            
    text_periodicity_info.set_text(period_info_str)
    
    fig.canvas.draw_idle()

# --- Configuración Inicial de la Figura y Sliders ---
def setup_interactive_plot():
    global fig, ax_real_stem, ax_phasor_2d, ax_spiral_3d, ax_imag_stem
    global text_formula_display, text_periodicity_info
    global slider_omega, slider_n_muestras, slider_phi

    fig = plt.figure(figsize=(14, 11)) 
    
    ax_real_stem = fig.add_subplot(2, 2, 1)
    ax_phasor_2d = fig.add_subplot(2, 2, 2)
    ax_spiral_3d = fig.add_subplot(2, 2, 3, projection='3d') 
    ax_imag_stem = fig.add_subplot(2, 2, 4)
    
    plt.subplots_adjust(left=0.08, bottom=0.25, right=0.95, top=0.85, hspace=0.5, wspace=0.35) 

    init_omega_norm = 0.25 
    init_n_muestras = 30
    init_phi_norm = 0.0   

    use_latex_for_formula = False 
    text_formula_display = fig.text(0.5, 0.94, "", ha='center', va='center', fontsize=14, color='teal', usetex=use_latex_for_formula)
    text_periodicity_info = fig.text(0.5, 0.90, "", ha='center', va='center', fontsize=12, color='darkblue') 

    ax_slider_omega_pos = [0.20, 0.12, 0.60, 0.025] 
    ax_slider_n_muestras_pos = [0.20, 0.08, 0.60, 0.025]
    ax_slider_phi_pos = [0.20, 0.04, 0.60, 0.025]
    
    slider_ax_omega = plt.axes(ax_slider_omega_pos)
    slider_omega = Slider(
        ax=slider_ax_omega,
        label=r'$\Omega/\pi$', 
        valmin=0,
        valmax=2, 
        valinit=init_omega_norm,
        valstep=1/32 
    )
    slider_omega.valtext.set_text(rf'{slider_omega.val:.3f}$\pi$') 
    def on_omega_change(val_norm):
        slider_omega.valtext.set_text(rf'{val_norm:.3f}$\pi$') 
        update_plots(None)
    slider_omega.on_changed(on_omega_change)

    slider_ax_n_muestras = plt.axes(ax_slider_n_muestras_pos)
    slider_n_muestras = Slider(
        ax=slider_ax_n_muestras,
        label='N Muestras',
        valmin=2, 
        valmax=100,
        valinit=init_n_muestras,
        valstep=1
    )
    slider_n_muestras.on_changed(update_plots)

    slider_ax_phi = plt.axes(ax_slider_phi_pos)
    slider_phi_local = Slider( 
        ax=slider_ax_phi,
        label=r'$\phi/\pi$', 
        valmin=-1, 
        valmax=1,
        valinit=init_phi_norm,
        valstep=1/16 
    )
    slider_phi_local.valtext.set_text(rf'{slider_phi_local.val:.3f}$\pi$') 
    slider_phi = slider_phi_local 

    def on_phi_change(val_norm):
        slider_phi_local.valtext.set_text(rf'{val_norm:.3f}$\pi$') 
        update_plots(None)
    slider_phi_local.on_changed(on_phi_change)

    update_plots(None) 
    plt.show()

# --- Ejecución Principal ---
if __name__ == "__main__":
    setup_interactive_plot()
