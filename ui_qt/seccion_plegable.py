"""
seccion_plegable.py
Grupo del formulario con cabecera clicable que muestra u oculta su contenido.
El contenido es una rejilla de 3 columnas: etiqueta | entrada | unidad.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QPushButton, QVBoxLayout, QWidget

FLECHA = {True: "▾", False: "▸"}


class SeccionPlegable(QWidget):

    def __init__(self, titulo, abierta=True, padre=None):
        super().__init__(padre)
        self._titulo = titulo
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 6)
        lay.setSpacing(2)

        self.cabecera = QPushButton()
        self.cabecera.setObjectName("CabeceraSeccion")
        self.cabecera.setCursor(Qt.PointingHandCursor)
        self.cabecera.clicked.connect(lambda: self.abrir(not self.cuerpo.isVisible()))
        lay.addWidget(self.cabecera)

        self.cuerpo = QFrame()
        self.cuerpo.setObjectName("CuerpoSeccion")
        self.rejilla = QGridLayout(self.cuerpo)
        self.rejilla.setContentsMargins(12, 10, 12, 10)
        self.rejilla.setHorizontalSpacing(8)
        self.rejilla.setVerticalSpacing(4)
        self.rejilla.setColumnStretch(1, 1)
        lay.addWidget(self.cuerpo)
        self.fila = 0                 # próxima fila libre de la rejilla
        self.abrir(abierta)

    def abrir(self, si):
        self.cuerpo.setVisible(si)
        self.cabecera.setText(f"{FLECHA[si]}  {self._titulo}")

    def agregar(self, widget, columna=0, ancho=3, alinear=None):
        """Agrega un widget en la fila actual (no avanza la fila)."""
        if alinear is None:
            self.rejilla.addWidget(widget, self.fila, columna, 1, ancho)
        else:
            self.rejilla.addWidget(widget, self.fila, columna, 1, ancho, alinear)

    def siguiente(self):
        self.fila += 1
