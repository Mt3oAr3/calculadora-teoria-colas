"""
render_formula.py
Dibuja una fórmula mathtext de matplotlib (sin LaTeX externo) como QPixmap,
con fondo transparente y el color de texto del tema, nítida en pantallas HiDPI.
"""
import io

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PySide6.QtGui import QPixmap

PUNTOS = 12          # tamaño de la fórmula en puntos tipográficos
DPI_BASE = 96


def formula_a_pixmap(latex, color, escala=1.0, tamano=PUNTOS):
    """latex: texto mathtext sin los $. escala: devicePixelRatio de la pantalla."""
    dpi = DPI_BASE * escala
    fig = Figure(dpi=dpi)
    fig.patch.set_alpha(0)
    FigureCanvasAgg(fig)
    fig.text(0, 0, f"${latex}$", fontsize=tamano, color=color)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0.04)
    pix = QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    pix.setDevicePixelRatio(escala)
    return pix
