"""
info_box.py
Caja informativa reutilizable: fondo gris muy claro, borde sutil, esquinas redondeadas,
icono «i» verde a la izquierda y texto con ajuste de línea que ocupa todo el ancho.

Un QLabel con salto de línea dentro de un layout a veces no recibe la altura que
necesita; por eso la caja fija su alto mínimo según su ancho real (heightForWidth).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy

from . import tema


class InfoBox(QFrame):

    def __init__(self, texto="", padre=None):
        super().__init__(padre)
        self.setObjectName("InfoBox")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        L = tema.LAYOUT
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*L["info_margen"])
        lay.setSpacing(L["info_espacio"])
        icono = QLabel(tema.ICONOS["info"])
        icono.setObjectName("InfoIcono")
        icono.setAlignment(Qt.AlignCenter)
        icono.setFixedSize(L["info_icono"], L["info_icono"])
        icono.setAccessibleName("Información")
        self.texto = QLabel(texto)
        self.texto.setObjectName("InfoTexto")
        self.texto.setWordWrap(True)
        self.texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.texto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay.addWidget(icono, 0, Qt.AlignTop)
        lay.addWidget(self.texto, 1)

    def setText(self, texto):
        self.texto.setText(texto)
        self._ajustar_alto()

    def text(self):
        return self.texto.text()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, ancho):
        return self.layout().heightForWidth(ancho)

    def _ajustar_alto(self):
        if self.width() > 0:
            self.setMinimumHeight(self.layout().heightForWidth(self.width()))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ajustar_alto()
