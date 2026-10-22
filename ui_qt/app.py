"""
app.py
Crea la QApplication y abre la ventana principal (ver main_qt.py).
"""
import sys

import matplotlib
# Sin pyplot: las figuras se crean con matplotlib.figure.Figure y se muestran con FigureCanvasQTAgg
# explícito. El backend «Agg» (sin ventanas) garantiza que nada abra ventanas propias de matplotlib.
matplotlib.use("Agg")

from PySide6.QtWidgets import QApplication  # noqa: E402

from .ventana_principal import VentanaPrincipal  # noqa: E402


def main(argv=None):
    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("Calculadora de Teoría de Colas")
    ventana = VentanaPrincipal("oscuro" if "--oscuro" in argv else "claro")
    ventana.show()
    return app.exec()
