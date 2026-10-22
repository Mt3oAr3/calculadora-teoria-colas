"""
app.py
Crea la QApplication y abre la ventana principal (ver main_qt.py).
"""
import sys

import matplotlib
matplotlib.use("QtAgg")

from PySide6.QtWidgets import QApplication  # noqa: E402

from .ventana_principal import VentanaPrincipal  # noqa: E402


def main(argv=None):
    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("Calculadora de Teoría de Colas")
    ventana = VentanaPrincipal("oscuro" if "--oscuro" in argv else "claro")
    ventana.show()
    return app.exec()
