"""
exportacion_service.py
Exporta resultados a CSV y gráficas a PNG a partir de estructuras de datos
(Tabla y el contexto de gráficas), nunca leyendo widgets de la interfaz.

Formato CSV (igual que la versión original): separador ';', codificación
UTF-8 con BOM (Excel la abre bien), y por cada sección una fila con el título,
una con los encabezados, las filas de datos y una fila vacía.
"""
import csv
import os

from matplotlib.figure import Figure

from visualization import graficas_colas as gc


def escribir_csv(destino, tablas, fmt):
    """Escribe las tablas en un objeto de archivo de texto ya abierto."""
    w = csv.writer(destino, delimiter=";")
    for tabla in tablas:
        w.writerow([tabla.titulo])
        w.writerow(tabla.encabezados)
        for fila in tabla.textos(fmt):
            w.writerow(fila)
        w.writerow([])


def exportar_csv(ruta, tablas, fmt):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        escribir_csv(fh, tablas, fmt)


def graficas_disponibles(finita):
    """Gráficas que tienen sentido para el modelo (las de M solo en finita)."""
    return [g for g in gc.GRAFICAS if finita or not g.por_M]


def guardar_grafica(ruta, gid, ctx, dpi=150):
    fig = Figure(figsize=(9, 5.5), dpi=dpi, layout="constrained")
    gc.dibujar(fig, gid, ctx)
    fig.savefig(ruta)


def guardar_todas(carpeta, ctx, dpi=150):
    """Guarda cada gráfica aplicable como NN_id.png. Devuelve las rutas creadas."""
    rutas = []
    for i, g in enumerate(gc.GRAFICAS, start=1):
        if g.por_M and not ctx["finita"]:
            continue
        ruta = os.path.join(carpeta, f"{i:02d}_{g.gid}.png")
        guardar_grafica(ruta, g.gid, ctx, dpi)
        rutas.append(ruta)
    return rutas
