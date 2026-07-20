# Z-app — Visualizador y Diseñador de Sistemas en el Dominio Z

Análogo discreto del `laplace_visualizer.py` (módulo 5): una app Tkinter + matplotlib donde el plano z (con el círculo unitario) es un lienzo interactivo. Se arrastran polos (X) y ceros (O) con el mouse y se observa en vivo el efecto sobre |H(e^jω)|, la fase y la respuesta al impulso h[n].

## Qué es

- **Plano z interactivo**: círculo unitario, polos/ceros arrastrables, pares conjugados automáticos, lectura de radio/ángulo del punto seleccionado, "Shift + arrastrar" ajusta al círculo unitario.
- **Modo geométrico**: slider de ω que dibuja vectores desde cada polo/cero hasta e^jω sobre el círculo — la conexión visual entre geometría y |H(e^jω)| que es el corazón de C25.
- **Panel |H(e^jω)|** (ω ∈ [-π, π]) y panel de fase, actualizados en vivo mientras se arrastra.
- **Panel h[n]** (primeras 40 muestras) con indicador de estabilidad (¿todos los polos dentro del círculo unitario?) y causalidad asumida.
- **Presets de diseño (C26)**: notch (elimina una frecuencia), peine/comb (elimina varias equiespaciadas), pasa bajos / pasa altos de primer orden, resonador — cada uno con sus propios sliders (f0, fs, r, N).
- **Botón "Copiar b, a para scipy"**: muestra los coeficientes numéricos de H(z) = B(z)/A(z) listos para pegar en `scipy.signal.freqz`/`lfilter`, para que los estudiantes verifiquen el diseño hecho con el mouse.

## Cómo correrla

```bash
python3 z_visualizer.py
```

## Dependencias

Solo biblioteca estándar + numpy + matplotlib (con el backend `TkAgg`, vía `tkinter`, incluido en la instalación estándar de Python). **No** requiere scipy ni sympy — los coeficientes (b, a) que arma la app usan exactamente la misma convención que `scipy.signal` (`b[0]`, `a[0]` = términos sin retardo de z⁻¹), así que son compatibles directamente si el estudiante quiere seguir explorando con scipy.

```bash
pip install numpy matplotlib
```

## A qué clases sirve

- **C25** — Respuesta en frecuencia geométrica: del plano z a |H(e^jω)| (U6.3 / U6.5). Usar el modo geométrico (vectores + slider de ω) en modo manual, sin presets.
- **C26** — Diseño de filtros por polos/ceros: notch, peine, primer orden, con verificación en Python (U6.6). Usar los presets y el botón de exportar b, a a scipy.

Ver `actividades.txt` para una guía de tres actividades listas para usar en clase.

## Convención matemática (para quien modifique el código)

Un punto z_k marcado como cero o polo aporta un factor `(1 - z_k·z⁻¹)` al numerador o denominador de H(z):

```
H(z) = K · Π(1 - z_k·z⁻¹) / Π(1 - p_k·z⁻¹)
```

Es la misma convención de `scipy.signal.zpk2tf`/`freqz`. Con ella, un solo polo en r sin ceros da H(z) = 1/(1 - r·z⁻¹), cuya respuesta al impulso es h[n] = rⁿ (sin retardo espurio) — el caso de prueba usado para validar el módulo. La magnitud |H(e^jω)| es idéntica bajo esta convención o la de polinomios monicos en z positivo (`numpy.poly` "crudo"), así que la lectura geométrica clásica (producto de distancias) sigue siendo válida en cualquiera de las dos.
