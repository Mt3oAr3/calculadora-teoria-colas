"""
chips.py
Fila de «chips» (datos clave sobre una tabla, p. ej. «Menor k que cumple: 2»). Los chips
saltan de línea si no caben, así la fila nunca obliga a desplazar en horizontal. Un clic en
un chip con valor emite elegido(tipo, valor); los que no tienen fila («Ningún k cumple»)
se muestran deshabilitados.
"""
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import QLayout, QPushButton, QSizePolicy, QWidget

from . import tema

L = tema.LAYOUT


class _Flujo(QLayout):
    """Coloca los widgets de izquierda a derecha y pasa a la línea siguiente cuando no caben."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, ancho):
        return self._colocar(QRect(0, 0, ancho, 0), aplicar=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._colocar(rect, aplicar=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        tam = QSize()
        for item in self._items:
            tam = tam.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return tam + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _colocar(self, rect, aplicar):
        m = self.contentsMargins()
        zona = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, alto_linea = zona.x(), zona.y(), 0
        esp = self.spacing()
        for item in self._items:
            tam = item.sizeHint()
            if x + tam.width() > zona.right() + 1 and alto_linea > 0:
                x, y = zona.x(), y + alto_linea + esp
                alto_linea = 0
            if aplicar:
                item.setGeometry(QRect(QPoint(x, y), tam))
            x += tam.width() + esp
            alto_linea = max(alto_linea, tam.height())
        return y + alto_linea - rect.y() + m.bottom()


class FilaChips(QWidget):
    elegido = Signal(str, int)          # tipo ("k" o "M") y valor de la fila

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("FilaChips")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._flujo = _Flujo(self)
        self._flujo.setContentsMargins(*L["chips_margen"])
        self._flujo.setSpacing(L["chips_espacio"])
        self.chips = []
        # Clic en un chip con «Cómo se calculó» abierto: cambia la fórmula en vez de cerrar el panel
        self.setProperty("abre_formula", True)

    def poner(self, destacados, estilos=None):
        """destacados: lista de services.comparacion_service.Destacado; estilos: tipo de chip por posición."""
        for chip in self.chips:
            self._flujo.removeWidget(chip)
            chip.deleteLater()
        self.chips = []
        for i, d in enumerate(destacados):
            chip = QPushButton(d.texto, self)
            chip.setObjectName("Chip")
            chip.setProperty("tipo", (estilos or {}).get(i, "info"))
            chip.setToolTip(d.detalle + ("  Clic: ver la fila y «Cómo se calculó»." if d.valor is not None else ""))
            chip.setEnabled(d.valor is not None)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setFocusPolicy(Qt.StrongFocus)
            if d.valor is not None:
                chip.clicked.connect(lambda _c=False, t=d.tipo, v=d.valor: self.elegido.emit(t, v))
            self._flujo.addWidget(chip)
            chip.show()
            self.chips.append(chip)
        self.updateGeometry()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, ancho):
        return self._flujo.heightForWidth(ancho)

    def sizeHint(self):
        ancho = max(1, self.width())
        return QSize(ancho, self.heightForWidth(ancho))
