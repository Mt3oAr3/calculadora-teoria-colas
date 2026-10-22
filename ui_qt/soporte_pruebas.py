"""
soporte_pruebas.py
Utilidades para probar la ventana sin pantalla (QT_QPA_PLATFORM=offscreen).

Viven en ui_qt/ porque es la única capa que puede importar Qt: así tests/ no
importa PySide6 directamente (ver tests/test_arquitectura.py).
"""
import os
import sys


def aplicacion():
    """QApplication sin pantalla (la crea una sola vez) con las fuentes del sistema."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    fuentes = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    if sys.platform == "win32" and os.path.isdir(fuentes):
        os.environ.setdefault("QT_QPA_FONTDIR", fuentes)
    import matplotlib
    matplotlib.use("QtAgg")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def procesar(veces=5):
    from PySide6.QtWidgets import QApplication
    for _ in range(veces):
        QApplication.processEvents()


def esperar(ms):
    """Deja correr animaciones y temporizadores durante `ms` milisegundos."""
    from PySide6.QtTest import QTest
    QTest.qWait(ms)


def tecla(widget, nombre):
    """Pulsa una tecla por nombre de Qt.Key (p. ej. 'Escape', 'Return', 'F5')."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    QTest.keyClick(widget, getattr(Qt, f"Key_{nombre}"))


def clic(widget, punto=None):
    """Clic izquierdo en el widget (en su centro o en `punto`, coordenadas locales)."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, punto if punto is not None else QPoint())


def visible_en_ventana(widget):
    """True si el widget se ve y su rectángulo entero cae dentro de la ventana."""
    if not widget.isVisible():
        return False
    ventana = widget.window()
    esquina = widget.mapTo(ventana, widget.rect().topLeft())
    rect = widget.rect().translated(esquina)
    return ventana.rect().contains(rect)


def captura(widget, ruta):
    widget.grab().save(ruta)
