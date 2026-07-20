# Visualizador Pedagógico de Convolución Rápida

## Overlap-Add (OLA) y Overlap-Save (OLS)

Esta es una aplicación de escritorio desarrollada en Python, PySide6 y Matplotlib, diseñada con un fin **pedagógico**: enseñar visualmente los algoritmos de convolución rápida por bloques, Overlap-Add (OLA) y Overlap-Save (OLS).

[cite\_start]Esta herramienta es un complemento ideal para un curso de Procesamiento Digital de Señales (DSP), especialmente al cubrir el Análisis de Fourier en Tiempo Discreto (como el Capítulo 6 del libro de Alvarado [cite: 1469-1529]).

## El Problema Pedagógico

1.  **El Costo:** La convolución lineal $y[n] = x[n] * h[n]$ es la base del filtrado LTI, pero es computacionalmente costosa ($O(N \cdot M)$) para señales largas.
2.  **La Solución Rápida:** La convolución rápida, usando la FFT ($O(N \log N)$), es mucho más eficiente.
3.  **El Desafío:** La multiplicación en el dominio de la FFT *no* es una convolución lineal, sino una **convolución circular** ($x[n] \circledast h[n]$). Si procesamos una señal larga en bloques, esto introduce errores de "aliasing temporal" (wrap-around) en los bordes de cada bloque.

**¿Cómo usamos la FFT por bloques para obtener un resultado *idéntico* al de la convolución lineal?**

La respuesta son los algoritmos **Overlap-Add** y **Overlap-Save**. Esta aplicación desmitifica cómo funcionan.

## Captura de Pantalla

*(Inserta aquí una captura de pantalla de la aplicación)*

## Características

  * **Visualización Paso a Paso:** Procesa señales largas bloque por bloque con un botón "Siguiente Bloque".
  * **Comparación de Métodos:** Permite cambiar instantáneamente entre los modos OLA y OLS.
  * **Validación de Parámetros:** La GUI valida en tiempo real la condición $N \ge L+M-1$, crucial para ambos métodos.
  * **Tres Gráficos Sincronizados:**
    1.  **Salida Global:** Compara la "Verdad Fundamental" (convolución lineal real) con la salida reconstruida por el método de bloques.
    2.  **Proceso de Entrada:** Muestra exactamente qué datos se envían a la FFT en cada paso (incluyendo padding o solapamiento).
    3.  **Proceso de Salida:** Muestra exactamente qué datos provienen de la IFFT (incluyendo colas, solapamientos y partes corruptas).

## Requisitos e Instalación

La aplicación está escrita en Python 3.

1.  Clona este repositorio:

    ```bash
    git clone https://github.com/tu_usuario/tu_repositorio.git
    cd tu_repositorio
    ```

2.  (Recomendado) Crea un entorno virtual:

    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  Instala las dependencias. Puedes usar el archivo `requirements.txt` (si lo creas) o instalarlas manualmente:

    ```bash
    pip install numpy matplotlib pyside6
    ```

    *(Opcional, para un mejor estilo visual)*:

    ```bash
    pip install qdarktheme
    ```

    Si creas un `requirements.txt`, debería contener:

    ```
    numpy
    matplotlib
    PySide6
    qdarktheme
    ```

4.  Ejecuta la aplicación:

    ```bash
    python visualizador_conv.py
    ```

## Guía de Uso Pedagógico

Esta es la guía para usar la herramienta en una clase:

1.  **Configuración Inicial:**

      * Inicia la aplicación.
      * Presiona **"Generar Nueva Señal/Filtro"**. Esto crea un filtro $h[n]$ de longitud $M=17$ y una señal $x[n]$ con algunos impulsos.
      * El **Gráfico 1 (Global)** mostrará la "Verdad Fundamental" (línea azul punteada). Esta es la convolución lineal $y[n] = x[n] * h[n]$ calculada de la forma tradicional. *Este es el resultado que ambos métodos deben igualar*.

2.  **Presiona "Iniciar / Reiniciar":**

      * La línea de "Salida Reconstruida" (roja) se reinicia a cero.
      * El botón **"Siguiente Bloque \>\>"** se activa.

3.  **Analiza cada Bloque:**

      * Presiona **"Siguiente Bloque \>\>"** repetidamente.
      * En cada paso, guía a los estudiantes para que observen los 3 gráficos y respondan:
          * **Gráfico 2 (Entrada):** ¿Qué datos está procesando la FFT *exactamente*? ¿Veo ceros (padding) o datos del bloque anterior (solapamiento)?
          * **Gráfico 3 (Salida):** ¿Qué datos salieron de la IFFT? ¿Qué parte es "buena" y qué parte es "mala"?
          * **Gráfico 1 (Global):** ¿Cómo se "pega" este nuevo bloque de salida al resultado final? ¿Se suma o se concatena?

-----

### Conceptos Clave a Observar

Usa esta guía para explicar *por qué* los métodos funcionan.

#### 1\. Modo: Overlap-Add (OLA)

  * **Gráfico 2 (Entrada):** Verás bloques de datos de longitud $L$ (p.ej., 64) que **no se solapan**. La aplicación añade $M-1$ ceros al final (**Zero-Padding**) para completar el tamaño de FFT $N$.
  * **Gráfico 3 (Salida):** El resultado $y_i[n]$ es una convolución lineal *perfecta* de longitud $N=L+M-1$. Se divide en:
      * Datos principales (muestras $0$ a $L-1$).
      * La "cola" de la convolución (muestras $L$ a $N-1$, resaltadas en verde).
  * **Gráfico 1 (Global) - ¡El "Aha\!" del Add\!:**
      * Verás cómo la "cola" verde del bloque $y_i$ se **SUMA** al inicio del siguiente bloque $y_{i+1}$.
      * **¿Por qué?** Porque la convolución lineal $y[n] = (x_1+x_2+\dots)*h$ es, por linealidad, igual a $(x_1*h) + (x_2*h) + \dots$. La salida verdadera en los puntos de unión de bloques *es* la suma de la cola del bloque anterior y el inicio del nuevo.

#### 2\. Modo: Overlap-Save (OLS)

  * **Gráfico 2 (Entrada):** Verás bloques de datos de longitud $N$ que **sí se solapan**. Cada bloque $x_i$ se construye con:
      * Las últimas $M-1$ muestras del bloque *anterior* $x_{i-1}$ (el **solapamiento**, en naranja).
      * $L = N-M+1$ muestras *nuevas* de la señal de entrada.
  * **Gráfico 3 (Salida):** El resultado $y_i[n]$ es una convolución *circular* ($x_i \circledast h$).
      * Las primeras $M-1$ muestras (en rojo) están **corruptas** por el aliasing temporal (el "wrap-around" del final del bloque de entrada).
      * Las últimas $L$ muestras (en verde) son **válidas**, ya que el solapamiento de entrada proveyó la "memoria" del filtro.
  * **Gráfico 1 (Global) - ¡El "Aha\!" del Save\!:**
      * La aplicación **DESCARTA** las $M-1$ muestras corruptas.
      * Luego, **GUARDA** (Save) y **CONCATENA** (pega, sin sumar) las $L$ muestras válidas al final de la señal de salida.

### Licencia

Este proyecto se distribuye bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

### Autor

Desarrollado para el curso de **Procesamiento Digital de Señales**.