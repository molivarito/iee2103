# Desmos — scripts listos para pegar

**Los cuatro gráficos ya están guardados** en la cuenta de Desmos del profesor y **embebidos en
`c02-slides.qmd`** — en clase no hay que pegar nada, basta avanzar las diapositivas:

| | Gráfico | Link |
|---|---|---|
| D1 | Periodicidad de una suma | <https://www.desmos.com/calculator/0pa5xq5fvv> |
| D2 | Energía vs. potencia | <https://www.desmos.com/calculator/03eionpor9> |
| D3 | Descomposición par + impar | <https://www.desmos.com/calculator/tgftr50dp5> |
| D4 | Continua vs. discreta (muestreo) | <https://www.desmos.com/calculator/iyfcef6onv> |
| D5 | Transformaciones $x(at-b)$ (C3) | <https://www.desmos.com/calculator/7axluaxsae> |

El código fuente de cada uno queda abajo, por si hay que rehacerlos, modificarlos o dárselos a
los estudiantes. **Ojo**: las versiones publicadas no son idénticas a esos scripts — llevan dos
adaptaciones obligatorias para que funcionen incrustadas (ver *Trampas*): los sliders se
reemplazaron por **puntos arrastrables** y los resultados numéricos se sacaron a **etiquetas
sobre la pizarra**. Cada bloque se pega **completo, de una vez** en
[desmos.com/calculator](https://www.desmos.com/calculator): abre una calculadora en blanco, haz
clic en la primera casilla vacía y pega. Desmos parte el texto por saltos de línea y crea una
expresión por fila, con sus sliders.

Todos los scripts de este archivo fueron **probados en Desmos** (jul-2026); los valores que
se indican como esperados son los que devuelve la calculadora.

---

## D1 · ¿Es periódica una suma de periódicas? (C2, Bloque 2)

El bloque con la votación. La pregunta de la clase es si $\cos(6t)+\sin(15t)$ es periódica.

```
w_1=6
w_2=15
s(t)=\cos(w_1t)+\sin(w_2t)
u=1
y=s(x-u)
D(v)=\frac{1}{400}\sum_{k=0}^{400}\left(s\left(0.05k\right)-s\left(0.05k-v\right)\right)^{2}
y=D(x)\left\{0\le x\le8\right\}
\left(u,D\left(u\right)\right)
T_0=\frac{2\pi}{\gcd\left(w_1,w_2\right)}
```

**Cómo se usa en clase** (después de la votación, no antes):

1. Se ve la señal (negra) y una **copia desfasada** $s(t-u)$ (roja). Arrastrar $u$: cuando la
   roja cae *exactamente* encima de la negra, ese $u$ es un período.
2. La curva azul $D(v)$ mide "cuánto difiere la señal de su copia desfasada $v$". **Sus ceros
   son los períodos.** Es, sin nombrarlo, la autocorrelación — vuelve en la unidad 3.
3. $T_0 = 2\pi/\gcd(w_1,w_2) = 2{,}0944 = 2\pi/3$ ✓ (la respuesta de la votación).
   Arrastrar $u$ hasta $2{,}09$: $D(u)\to 0$ y las curvas coinciden.

**El contraejemplo** (cambiar solo la línea de `s` y las dos frecuencias):

```
w_1=1
w_2=\pi
s(t)=\cos(w_1t)+\cos(w_2t)
```

Ampliar el rango de $D$ a `y=D(x)\left\{0\le x\le40\right\}`: **la curva nunca vuelve a tocar
cero**. Y $T_0$ queda *indefinido*, porque $\gcd$ no existe para $\pi$ — el propio Desmos se
niega a dar la respuesta, que es justamente el punto.

---

## D2 · Señal de energía vs. señal de potencia (C2, Bloque 3)

```
A=1
w=2
g(t)=A\cos\left(wt\right)
h(t)=e^{-\left|t\right|}
L=5
E_g=\int_{-L}^{L}g\left(t\right)^{2}dt
P_g=\frac{E_g}{2L}
\frac{A^{2}}{2}
E_h=\int_{-L}^{L}h\left(t\right)^{2}dt
P_h=\frac{E_h}{2L}
```

Ajustar el slider $L$ al rango **0,5 a 60** (Desmos lo crea en −10 a 10).

**Cómo se usa**: arrastrar $L$ hacia arriba y leer las cuatro cifras.

| | $L=5$ | $L=40$ | Conclusión |
|---|---|---|---|
| $E_g$ (coseno) | 5,2 | **40,05** | crece sin parar → $E=\infty$ |
| $P_g$ | 0,52 | **0,5007** | se estabiliza en $A^2/2$ ✓ |
| $E_h$ (pulso) | 0,99995 | **1** | converge → energía finita |
| $P_h$ | 0,1 | 0,0125 | → 0 |

La tabla de la clase (energía / potencia / ninguna) queda *medida*, no afirmada. Para el
tercer caso, cambiar `h(t)=t`: ni $E$ ni $P$ convergen.

---

## D3 · Descomposición par + impar (C2, Bloque 4)

```
f(t)=\left\{t\ge0:e^{-t},0\right\}
p(t)=\frac{f\left(t\right)+f\left(-t\right)}{2}
i(t)=\frac{f\left(t\right)-f\left(-t\right)}{2}
y=p(x)+i(x)
E_f=\int_{-8}^{8}f\left(t\right)^{2}dt
E_p=\int_{-8}^{8}p\left(t\right)^{2}dt
E_i=\int_{-8}^{8}i\left(t\right)^{2}dt
E_p+E_i
```

Conviene poner la línea 4 (`y=p(x)+i(x)`) **punteada y gruesa**: cae exactamente sobre la
negra, y esa coincidencia *es* la demostración de que la descomposición reconstruye la señal.

Resultados: $E_f = 0{,}5$; $E_p = E_i = 0{,}25$; $E_p+E_i = 0{,}5 = E_f$ — que es
**exactamente el ejercicio [DB E0022] de la Lista 1**, verificado en vivo.

**Variante para el ejemplo de la clase** ($e^t \to \cosh + \sinh$): cambiar la primera línea a
`f(t)=e^{t}` y agregar `y=\cosh(x)` y `y=\sinh(x)` — se superponen a $p$ e $i$.

---

## D4 · Continua vs. discreta: el puente hacia la U5 (C2, Bloque 1)

```
f(t)=\cos\left(2\pi t\right)+0.5\cos\left(6\pi t\right)
T_s=0.1
N=\left[-40...40\right]
\left(NT_s,tf\left(NT_s\right)\right)
\left(NT_s,f\left(NT_s\right)\right)
```

Ajustar el slider $T_s$ al rango **0,02 a 0,6**.

La cuarta línea dibuja los **tallos** (es una paramétrica con $0\le t\le1$, que Desmos asume
sola) y la quinta los puntos. Se obtiene el gráfico clásico $x(t)$ continua + $x[n]$ discreta
encima.

**El gancho**: arrastrar $T_s$ de 0,02 hacia 0,5. Con pocas muestras los puntos ya no
"cuentan" la misma historia que la curva — sin decir la palabra *aliasing*, queda plantada la
pregunta que la unidad 5 responde. Es el mismo gancho que ya está escrito en el Bloque 1.

---

## D5 · Transformaciones $x(at-b)$ (C3, Bloque 3)

Resuelve la votación de C3 en vivo. La señal base es la escalonada de [DB E0286].

```
f(t)=\left\{0\le t<1:2,1\le t<3:-1,0\right\}
P=\left(2,-2.15\right)
Q=\left(3,-2.6\right)
a=\left\{P.x>0:\max\left(0.3,P.x\right),\min\left(-0.3,P.x\right)\right\}
b=Q.x
y=f\left(ax-b\right)
T=\left[0,1,3\right]
\left(\frac{T+b}{a},0\right)
\left(\frac{b}{a},0\right)
\left(b,0\right)
```

`P` y `Q` son los puntos arrastrables ($a$ y $b$); la definición de `a` lo mantiene lejos de
cero para que $b/a$ no explote. Los tres últimos puntos son el corazón del bloque: los
**quiebres anclados** en $(t^*+b)/a$, el **desplazamiento verdadero** en $b/a$ (verde) y el
**error clásico** en $b$ (rojo hueco).

Con $a=2$, $b=3$ reproduce exactamente la respuesta B de la votación (quiebres en 1,5 · 2 · 3).
Arrastrar $a$ a negativo hace aparecer el espejo.

---

## Trampas de Desmos (probadas, para no perder tiempo en clase)

- **`\left\{t\ge0\right\}` restringe el dominio**, no es un "por partes": deja la función
  *indefinida* fuera, y entonces $f(-t)$, las integrales y todo lo demás se caen. Para una
  señal causal hay que escribir la forma con rama final: `\left\{t\ge0:e^{-t},0\right\}`.
- **Nunca graficar una función que contenga una integral.** `y=D(x)` con $D$ definida por
  $\int$ cuelga el motor de Desmos (una integral por píxel). Por eso D1 usa una **suma**
  discreta: corre fluido. Integrales sueltas que devuelven *un número* (D2, D3) van perfecto.
- **Cuidado con reusar el nombre del slider como argumento**: si existe el slider `T` y además
  se escribe `D(T)=...`, Desmos lo lee como *ecuación en T* y dibuja algo absurdo. Por eso
  D1 usa `D(v)` con el slider aparte.
- **`f(t)=...` ya se grafica solo**: no hace falta agregar `y=f(x)`. Una línea menos.
- Los sliders nacen en −10 a 10. Los que no admiten valores negativos ($T_s$, $L$) hay que
  reajustarlos a mano, o el gráfico se ve raro al arrastrarlos.
- `\gcd` solo funciona con enteros — que es *útil*: el contraejemplo irracional de D1 falla
  a propósito.

### Las dos trampas del modo incrustado (`?embed`)

Son las que obligaron a rediseñar los cuatro gráficos, y valen para cualquier Desmos que se
quiera meter en una diapositiva:

1. **`?embed` es obligatorio**: sin ese parámetro el iframe queda en blanco. Desmos no se deja
   incrustar con la URL pelada.
2. **`?embed` esconde la lista de expresiones** — y con ella **los sliders y todos los
   resultados numéricos**. No hay parámetro de URL que la traiga de vuelta (`expressions=true`
   y similares no hacen nada; probado). Un gráfico que dependa de arrastrar un slider queda
   inservible dentro de la diapositiva.

Las dos soluciones, ya aplicadas a D1, D2 y D4:

- **Slider → punto arrastrable.** Los puntos *sí* se arrastran dentro del embed. Se define un
  punto libre y el parámetro se lee de su coordenada:

  ```
  P=\left(1,-2\right)          ← punto grande y visible, con dragMode en X
  u=P.x
  ```

  Si el rango útil no cabe en la pantalla, se mapea: en D4, `S.x` de −2 a 2 se convierte en
  $T_s$ de 0,02 a 0,62 con
  `T_s=\max\left(0.02,\min\left(0.6,0.02+0.15\left(S.x+2\right)\right)\right)`.

- **Número → etiqueta sobre la pizarra.** Un punto con `showLabel` e interpolación `${...}`:

  ```
  \left(-40,1.55\right)   con etiqueta:  COSENO  E = ${E_{gr}}   P = ${P_{gr}}
  ```

  Dos detalles: `pointOpacity:0` **también borra la etiqueta** (hay que dejar el punto visible
  aunque diminuto), y dentro de `${...}` **no se interpola LaTeX** — `${\frac{A^{2}}{2}}` sale
  impreso tal cual. Hay que definir antes una variable (`R=\frac{A^{2}}{2}`) y escribir `${R}`.
  Conviene además redondear: `E_{gr}=\operatorname{round}\left(E_{g},2\right)`, o se
  proyectan diez decimales.

## Cómo están incrustados

Cada gráfico va en su propia diapositiva de `c02-slides.qmd`, justo después de la que plantea
la pregunta:

```html
<iframe src="https://www.desmos.com/calculator/<hash>?embed" width="1050" height="580"
        style="border:1px solid #ccc" frameborder="0"></iframe>
```

Para rehacer o modificar uno: abrir el link, editar y apretar **Save** — el hash no cambia, así
que las diapositivas quedan actualizadas solas, sin tocar el `.qmd`.

Lo que **no** se puede hacer desde la diapositiva es editar expresiones (por ejemplo, cambiar
$s(t)$ al contraejemplo $\cos(t)+\cos(\pi t)$ de D1): eso pide la lista de expresiones, o sea
abrir el gráfico en su propia pestaña. Por eso el contraejemplo tiene su propia lámina de
transición en las diapositivas.

**Requiere internet en la sala** — a diferencia del resto de las demos de esta carpeta, que son
locales. Si la conexión es dudosa, tener capturas de respaldo: los iframes quedan en blanco sin
red, y son cuatro diapositivas seguidas del guion.

---

# Recorrido: cómo se dibuja una función compleja

Origen: el material del profesor *"Visualización de señales"* (Señales II, subtema 1.4). Esta es su
versión interactiva, con los ejes correctos para cada unidad del curso.

**La idea que instala**: una función tiene argumento y salida, y cada uno puede ser real o complejo.
De ahí salen cuatro combinaciones, y **cada una obliga a elegir qué se dibuja**. Elegir la parte
real, o el módulo, o la fase, es una *decisión* — no una propiedad de la función. El curso toma esa
decisión distinta en cada unidad, y casi siempre sin decirlo.

| | salida real | salida compleja |
|---|---|---|
| **argumento real** | la curva de siempre | 4 proyecciones (Re, Im, módulo, fase), o la espiral |
| **argumento complejo** | una superficie sobre el plano | 4 superficies… o **polos y ceros** |

| | Gráfico | Dónde se usa | Link |
|---|---|---|---|
| 1 | $e^{st}$: las 4 proyecciones a la vez | **C3** (incrustado) · **Ay1** | <https://www.desmos.com/calculator/akpveuu0ba> |
| 3 | Plano $s$: la superficie $\|X(s)\|$ y el corte $j\omega$ | **C17** (incrustado) | <https://www.desmos.com/3d/ftb7axttio> |
| 4 | Plano $z$: la superficie y el corte del círculo unitario | **C25** (incrustado) | <https://www.desmos.com/3d/cfs2pt7nfz> |
| 5 | Polos y ceros: el resumen sintético | **C17** (incrustado) | <https://www.desmos.com/calculator/d4oknsgkxc> |

(El caso "argumento real → salida real" no tiene gráfico propio a propósito: aparece como caso
degenerado del 1, llevando $\omega$ a cero.)

## Qué muestra cada uno

**1 · Las cuatro proyecciones.** $f(t)=e^{st}$ con $\sigma$ y $\omega$ arrastrables. Re e Im en
cuadratura, el módulo como envolvente (solo depende de $\sigma$), y la fase en **banda propia**
abajo, con guías punteadas en $\pm\pi$ — separada a propósito, porque en escala natural tapa a las
otras tres. El gancho: llevar $\omega$ a 0 y ver que la salida se vuelve real.

**3 · El plano $s$.** $X(s)=1/((s-p)(s-\bar p))$ con el polo movible por sliders. La superficie
$|X(s)|$, el plano rojo $\sigma=0$, y la curva de intersección que **es** $|X(j\omega)|$. Ojo al
usarlo: **partir con el polo cerca del eje** ($\sigma_p \approx -0.15$) y *alejarlo*. Con el polo
lejos el corte sale casi plano y no se entiende nada.

**4 · El plano $z$.** Lo mismo, pero el corte es el **círculo unitario**. Como es cerrado, la
respuesta se repite al dar la vuelta: ahí está la periodicidad $2\pi$ de la DTFT, que deja de ser
una convención y pasa a ser la forma del corte.

**5 · Polos y ceros.** El cierre. Polo y cero arrastrables (sus conjugados se mueven solos), y a la
derecha $|H(j\omega)|$ dibujada **de lado**, alineada con el eje $j\omega$, con guías punteadas que
conectan cada polo con su pico. Muestra que de toda la superficie basta guardar dos conjuntos de
puntos.

## El ejercicio Gauss (para la Ay1)

Del material original. Graficar a mano, en forma aproximada, las cuatro proyecciones de
$$f(x) = e^{-\pi x^{2}}\,(1 - i2\pi x)$$
y recién después comprobar. Está bien elegida: Re e Im se parecen a una gaussiana y su derivada,
pero **el módulo tiene doble joroba y la fase es una transición suave** — o sea las cuatro
proyecciones salen distintas, que es justo el punto. Gráficos originales del profesor:
[2D](https://www.desmos.com/calculator/x07wykk1rc) ·
[3D](https://www.desmos.com/3d/6bepz8hen6) ·
[paramétrica](https://www.desmos.com/3d/cls77rdw6c) ·
[argumento complejo](https://www.desmos.com/3d/uouxmwmayv).

## Trampas propias de este recorrido

- **El modo complejo se activa con `allowComplex: true`**, no con `complex: true` (ese existe pero
  no basta). Sin él, Desmos lee la `i` como variable indefinida y ofrece "add slider: i". Vale para
  **2D y 3D por igual**: el 3D sí soporta complejos, solo que un gráfico nuevo nace con el modo
  apagado.
- **En 3D, `z` es el eje vertical**: no se puede llamar `z` al argumento de la función. Usar
  `H(w)` y evaluar `H(x+yi)`.
- **El conjugado es `\operatorname{conj}(z)`**. `\overline{z}` parsea pero no calcula.
- **`extendTo3D: true`** es lo que convierte `x=0` de recta en plano. No se puede pasar al crear la
  expresión (se descarta); hay que crearla y después actualizarla, o marcar el checkbox en la UI.
- **Recortar siempre la superficie** con `\min(k, |X|)`: sin eso el polo se va al infinito y aplasta
  la escala hasta dejar todo plano.
- Las paramétricas van con `t`, no con `y`: `(f(t), t)` sí, `(f(y), y)` no dibuja nada.
- Los subíndices deben ser alfanuméricos: `P_{1}` sí, `P_{\sigma}` no es nombre válido.

### Incrustar: 2D y 3D se comportan al revés (probado)

| | `?embed` | sin parámetro |
|---|---|---|
| **calculator (2D)** | funciona | iframe en blanco |
| **3d** | iframe en blanco | funciona, y **muestra la lista de expresiones** (los sliders sirven) |

O sea: el `?embed` que es obligatorio en 2D **rompe** el 3D. Y hay una limitación mayor:

- **Desmos 3D no funciona dentro de reveal.js**, ni con `?embed` ni sin él, ni con `data-preload`.
  Usa WebGL y no inicializa dentro de un contenedor oculto (reveal mantiene las láminas no
  visibles en `display:none`), y no se recupera al mostrarse. Probado con esperas de 30 s.
- **Solución adoptada**: en las diapositivas, los 3D van como **figura estática + link** para abrir
  el gráfico vivo. Las figuras están en `assets/img/complejas/`. Es además más robusto para clase:
  no arriesga una lámina en blanco, y funciona sin internet.
- Los 2D sí se incrustan bien en reveal, con `?embed`.
