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
    matplotlib.use("Agg")
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


# ----------------------------------------------------------------------
# Acceso a modelos de tabla sin importar Qt desde tests/
# ----------------------------------------------------------------------
def _rol(nombre):
    from PySide6.QtCore import Qt
    return {"texto": Qt.DisplayRole, "alineacion": Qt.TextAlignmentRole, "color": Qt.ForegroundRole}[nombre]


def encabezado(modelo, columna, rol="texto"):
    from PySide6.QtCore import Qt
    return modelo.headerData(columna, Qt.Horizontal, _rol(rol))


def celda(modelo, fila, columna, rol="texto"):
    return modelo.index(fila, columna).data(_rol(rol))


def a_la_derecha(alineacion):
    from PySide6.QtCore import Qt
    return bool(Qt.AlignmentFlag(alineacion) & Qt.AlignRight)


def a_la_izquierda(alineacion):
    from PySide6.QtCore import Qt
    return bool(Qt.AlignmentFlag(alineacion) & Qt.AlignLeft)


def ordenar(vista, columna, descendente=True):
    from PySide6.QtCore import Qt
    vista.sortByColumn(columna, Qt.DescendingOrder if descendente else Qt.AscendingOrder)


def sin_orden(vista):
    from PySide6.QtCore import Qt
    vista.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)


# ----------------------------------------------------------------------
# Ventanas de nivel superior
# ----------------------------------------------------------------------
def espiar_ventanas():
    """Registra cada widget de nivel superior que se MUESTRA (aunque sea un instante).

    Devuelve un objeto con .mostradas (lista de widgets) y .detener().
    """
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QApplication, QWidget

    class _Espia(QObject):
        def __init__(self):
            super().__init__()
            self.mostradas = []

        def eventFilter(self, obj, ev):
            if ev.type() == QEvent.Show and isinstance(obj, QWidget) and obj.isWindow():
                self.mostradas.append(obj)
            return False

        def detener(self):
            QApplication.instance().removeEventFilter(self)

    espia = _Espia()
    QApplication.instance().installEventFilter(espia)
    return espia


def ventanas_visibles():
    from PySide6.QtWidgets import QApplication
    return [w for w in QApplication.topLevelWidgets() if w.isVisible()]
