"""
barra_lateral.py
Navegación entre páginas y botón para alternar el tema claro / oscuro.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from . import tema

PAGINAS = ["Resultados", "Probabilidades", "Costos y por día", "Comparar k y M", "Gráficas"]
ANCHO = 196


class BarraLateral(QFrame):
    pagina_elegida = Signal(int)
    cambiar_tema = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("BarraLateral")
        self.setFixedWidth(ANCHO)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 16, 12, 12)
        lay.setSpacing(4)

        marca = QLabel("Teoría de colas")
        marca.setObjectName("Marca")
        sub = QLabel("Técnicas de Simulación")
        sub.setObjectName("MarcaSub")
        lay.addWidget(marca)
        lay.addWidget(sub)
        lay.addSpacing(16)

        self.lista = QListWidget()
        self.lista.setObjectName("Navegacion")
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for i, nombre in enumerate(PAGINAS, start=1):
            it = QListWidgetItem(nombre)
            it.setToolTip(f"{nombre}  (Ctrl+{i})")
            self.lista.addItem(it)
        self.lista.currentRowChanged.connect(self.pagina_elegida.emit)
        lay.addWidget(self.lista, 1)

        self.btn_tema = QPushButton()
        self.btn_tema.setCursor(Qt.PointingHandCursor)
        self.btn_tema.clicked.connect(self.cambiar_tema.emit)
        lay.addWidget(self.btn_tema)
        self.actualizar_tema()

    def elegir(self, indice):
        self.lista.setCurrentRow(indice)

    def actualizar_tema(self):
        otro = "oscuro" if tema.actual() == "claro" else "claro"
        self.btn_tema.setText(tema.NOMBRES[otro])
        self.btn_tema.setToolTip(f"Cambiar a {tema.NOMBRES[otro].lower()} (Ctrl+T)")
