"""Genera ../x_data.js con las entradas anecoicas embebidas (base64) a partir de x/*.mp3.
Recortes de ~8 s, mono 22.05 kHz, mp3 64 kbps (ffmpeg), hechos desde las fuentes indicadas."""
import base64, pathlib
AQUI = pathlib.Path(__file__).parent
FUENTES = {
    "flamenco": ("guitarra flamenca", 'Guitarra flamenca: "Cologne University of Applied Sciences - Anechoic Recordings", Michio Woirgard, Philipp Stade, Jeffrey Amankwor, Benjamin Bernschütz y Johannes Arend, 2012 (CC BY-SA 3.0), recorte 95.5–103.5 s de Flamenco_2'),
    "soprano":  ("soprano (Mozart)", 'Soprano: aria de Donna Elvira (Don Giovanni, Mozart), grabación anecoica de Aalto University — Pätynen, Pulkki y Lokki, Acta Acustica 94(6), 2008 (uso académico), recorte 10–18.6 s de mozart_sopr_6'),
}
out = ["// Entradas anecoicas embebidas (ver x/gen_x_data.py y x/ATRIBUCION.md)", "window.X_DATA = {"]
for k, (nombre, credito) in FUENTES.items():
    f = AQUI / f"{k}.mp3"
    if not f.exists():
        print("falta", f.name); continue
    b = base64.b64encode(f.read_bytes()).decode()
    out.append(f'  {k}: {{nombre: {nombre!r}, credito: {credito!r}, mime: "audio/mpeg", b64: "{b}"}},')
out.append("};")
(AQUI.parent / "x_data.js").write_text("\n".join(out) + "\n", encoding="utf-8")
print("x_data.js:", (AQUI.parent / "x_data.js").stat().st_size, "bytes")
