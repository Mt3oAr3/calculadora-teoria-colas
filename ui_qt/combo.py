"""
combo.py
Lista desplegable de la aplicación: crear_combo() arma TODOS los QComboBox de ui_qt.

  * La lista emergente se ve como parte de la app y no con el estilo nativo: fondo
    superficie_elevada, borde borde_fuerte y esquinas redondeadas. La ventana emergente es
    translúcida y sin marco ni sombra del sistema; el fondo y el borde los pinta la hoja de
    estilos en #PopupCombo, un widget detrás de la lista que ocupa toda la ventana (el
    contenedor de Qt no pinta fondos de hoja de estilos cuando es translúcido).
  * Un QStyledItemDelegate hace que la hoja de estilos se aplique a cada opción
    (::item, ::item:hover, ::item:selected): alto cómodo, hover y elegida con los tokens.
  * La flecha es un chevron propio dibujado con el color del tema vigente (apunta hacia
    arriba mientras la lista está abierta).
  * La lista mide al menos lo que su opción más larga, aunque el campo sea más angosto.
"""
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QWidget

from . import tema

L = tema.LAYOUT


class Combo(QComboBox):
    """QComboBox con chevron propio; `abierto` indica si la lista está desplegada."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.abierto = False
        self._fondo = None

    def vestir_lista(self):
        """Lista emergente translúcida, sin marco ni sombra nativos, con el fondo redondeado #PopupCombo."""
        ventana = self.view().window()
        ventana.setWindowFlags(ventana.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        ventana.setAttribute(Qt.WA_TranslucentBackground)
        m = L["combo_lista_margen"]
        ventana.setContentsMargins(m, m, m, m)      # Qt los suma al alto de la lista: no aparece barra de más
        self._fondo = QWidget(ventana)
        self._fondo.setObjectName("PopupCombo")
        self._fondo.lower()
        ventana.installEventFilter(self)

    def eventFilter(self, obj, evento):
        if self._fondo is not None and obj is self._fondo.parentWidget() and evento.type() == QEvent.Resize:
            self._fondo.setGeometry(obj.rect())
        return False

    def showPopup(self):
        self.abierto = True
        self.update()
        super().showPopup()

    def hidePopup(self):
        super().hidePopup()
        self.abierto = False
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lapiz = QPen(tema.qcolor("texto_2" if self.isEnabled() else "texto_3"), L["combo_flecha_grosor"])
        lapiz.setCapStyle(Qt.RoundCap)
        lapiz.setJoinStyle(Qt.RoundJoin)
        p.setPen(lapiz)
        medio = L["combo_flecha_ancho"] / 2
        alto = medio / 2 * (-1 if self.abierto else 1)
        cx = self.width() - L["combo_flecha_margen"] - medio
        cy = self.height() / 2
        trazo = QPainterPath(QPointF(cx - medio, cy - alto))
        trazo.lineTo(QPointF(cx, cy + alto))
        trazo.lineTo(QPointF(cx + medio, cy - alto))
        p.drawPath(trazo)
        p.end()


def crear_combo(opciones, actual=None, minimo_contenido=None, padre=None):
    """
    Lista desplegable con las `opciones` (textos). `actual`: opción elegida al inicio.
    `minimo_contenido`: si se da, el campo no exige el ancho de su opción más larga (mide
    esa cantidad de caracteres); la lista emergente sí se abre con el ancho de su contenido.
    """
    c = Combo(padre)
    c.addItems(list(opciones))
    if actual is not None:
        c.setCurrentText(actual)
    if minimo_contenido is not None:
        c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        c.setMinimumContentsLength(minimo_contenido)
    c.setItemDelegate(QStyledItemDelegate(c))      # sin él, la hoja de estilos no llega a ::item
    vista = c.view()
    vista.setMinimumWidth(vista.sizeHintForColumn(0) + L["combo_lista_extra"])
    c.vestir_lista()
    return c

