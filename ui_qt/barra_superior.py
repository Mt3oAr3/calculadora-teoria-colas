"""
barra_superior.py
Barra fina superior: nombre de la aplicación y botón para alternar el tema claro / oscuro.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from . import tema


class BarraSuperior(QFrame):
    cambiar_tema = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("BarraSuperior")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*tema.LAYOUT["barra_superior_margen"])
        marca = QLabel("Teoría de colas")
        marca.setObjectName("Marca")
        sub = QLabel("Técnicas de Simulación")
        sub.setObjectName("MarcaSub")
        lay.addWidget(marca)
        lay.addWidget(sub, 0, Qt.AlignBaseline)
        lay.addStretch(1)
        self.btn_tema = QPushButton()
        self.btn_tema.setCursor(Qt.PointingHandCursor)
        self.btn_tema.clicked.connect(self.cambiar_tema.emit)
        lay.addWidget(self.btn_tema)
        self.actualizar_tema()

    def actualizar_tema(self):
        otro = "oscuro" if tema.actual() == "claro" else "claro"
        self.btn_tema.setText(tema.NOMBRES[otro])
        self.btn_tema.setToolTip(f"Cambiar a {tema.NOMBRES[otro].lower()} (Ctrl+T)")
