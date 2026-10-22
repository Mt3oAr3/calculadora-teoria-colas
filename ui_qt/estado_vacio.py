"""
estado_vacio.py
Estado vacío centrado (icono, título, una línea de ayuda y un botón secundario),
para mostrar dentro de una tarjeta en lugar de una tabla sin datos reales.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from . import tema


class EstadoVacio(QFrame):
    accion = Signal()

    def __init__(self, icono, titulo, texto, boton, padre=None):
        super().__init__(padre)
        self.setObjectName("EstadoVacio")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        L = tema.LAYOUT
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*L["vacio_margen"])
        lay.setSpacing(L["vacio_espacio"])
        self.icono = QLabel(icono)
        self.icono.setObjectName("VacioIcono")
        self.titulo = QLabel(titulo)
        self.titulo.setObjectName("VacioTitulo")
        self.texto = QLabel(texto)
        self.texto.setObjectName("VacioTexto")
        self.texto.setWordWrap(True)
        for w in (self.icono, self.titulo, self.texto):
            w.setAlignment(Qt.AlignCenter)
            lay.addWidget(w)
        self.boton = QPushButton(boton)
        self.boton.setObjectName("Secundario")
        self.boton.setCursor(Qt.PointingHandCursor)
        self.boton.clicked.connect(self.accion.emit)
        lay.addSpacing(L["vacio_espacio"])
        lay.addWidget(self.boton, 0, Qt.AlignHCenter)

    def alto_para(self, ancho):
        """Alto que necesita con ese ancho (el texto puede saltar de línea)."""
        lay = self.layout()
        return max(lay.heightForWidth(ancho) if lay.hasHeightForWidth() else 0, lay.minimumSize().height())
