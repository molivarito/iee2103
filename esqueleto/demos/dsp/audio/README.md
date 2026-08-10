# Audio examples: quantization and aliasing

Origen: página de Notion "Audio examples: Quantization and Aliasing" del profesor
(material 2024), rescatada el 2026-08-07 desde
`https://jade-anorak-611.notion.site/Audio-examples-Quantization-and-Aliasing-2448b0dd013c8045b998f4768b9e89bd`.

## Archivos

**Aliasing — tono barrido (sweep)**

- `tone48Khz.wav` — tono original, muestreado a 48 kHz (referencia sin aliasing).
- `tone-8Khz-alias.wav` — mismo tono remuestreado a 8 kHz **sin** filtro anti-alias:
  aliasing audible.
- `tone-8Khz-antialias.wav` — remuestreado a 8 kHz **con** filtro anti-alias aplicado
  antes del submuestreo: sin aliasing.

**Aliasing — pieza musical "Equinox"**

- `equinox-48KHz.wav` — "Equinox" original a 48 kHz.
- `al-equinox-8KHz-alias.wav` — a 8 kHz **sin** filtro anti-alias: aliasing audible.
- `equinox-8KHz.wav` — a 8 kHz **con** filtro anti-alias: sin aliasing.

**Cuantización — tono**

- `quant4.wav` — tono cuantizado a 4 bits (16 niveles).
- `quant16.wav` — tono cuantizado a 16 bits (referencia, prácticamente sin ruido de
  cuantización audible).
- `quant256.wav` — tono cuantizado a 256 bits (etiqueta original de Notion; en la
  práctica equivale a resolución muy alta, ruido de cuantización inaudible).

**Cuantización — nota de piano (profundidad de bits variable)**

- `piano-original.wav` — nota de piano sin cuantizar (referencia, archivo original
  `220afinal.wav`).
- `piano-1bit.wav` … `piano-8bits.wav` — la misma nota re-cuantizada a 1, 2, 3, 4, 5,
  6, 7 y 8 bits respectivamente (`220afinal1.wav` … `220afinal8.wav` en Notion).
  El ruido de cuantización decrece audiblemente a medida que aumentan los bits;
  con 1–2 bits la nota es casi irreconocible, con 6–8 bits se acerca a la calidad
  del original.

## Uso en el curso

Pensados para los bloques de **aliasing** y **cuantización** de la clase de
conversión análoga-digital (C19): reproducir en vivo los pares "con/sin filtro
anti-alias" (tono y Equinox) para ilustrar el efecto del aliasing al submuestrear,
y la secuencia de bits crecientes del piano para ilustrar el ruido de cuantización
y su relación con el número de bits (SQNR).
