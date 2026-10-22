"""
render_formula.py
Dibuja una fórmula mathtext de matplotlib (sin LaTeX externo) como QPixmap,
con fondo transparente y el color de texto del tema, nítida en pantallas HiDPI.
"""
import io

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PySide6.QtGui import QPixmap

from . import tema

DPI_BASE = 96


def formula_a_pixmap(latex, color, escala=1.0, tamano=None):
    """latex: texto mathtext sin los $. escala: devicePixelRatio de la pantalla. tamano en puntos."""
    tamano = tema.LAYOUT["formula_puntos"] if tamano is None else tamano
    dpi = DPI_BASE * escala
    fig = Figure(dpi=dpi)
    fig.patch.set_alpha(0)
    FigureCanvasAgg(fig)
    fig.text(0, 0, f"${latex}$", fontsize=tamano, color=color)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0.06)
    pix = QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    pix.setDevicePixelRatio(escala)
    return pix
