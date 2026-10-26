"""
barra_superior.py
Barra fina superior: botón para ocultar / mostrar el panel de parámetros, nombre de la
aplicación y botón para alternar el tema claro / oscuro.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from . import tema


class BarraSuperior(QFrame):
    cambiar_tema = Signal()
    alternar_parametros = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("BarraSuperior")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*tema.LAYOUT["barra_superior_margen"])
        self.btn_parametros = QPushButton("☰")
        self.btn_parametros.setObjectName("BotonParametros")
        self.btn_parametros.setCheckable(True)
        self.btn_parametros.setChecked(True)
        self.btn_parametros.setCursor(Qt.PointingHandCursor)
        self.btn_parametros.setToolTip("Ocultar/Mostrar parámetros (Ctrl+B)")
        self.btn_parametros.setAccessibleName("Ocultar o mostrar el panel de parámetros")
        # El estado lo fija la ventana (marcar_parametros): el clic solo pide el cambio
        self.btn_parametros.clicked.connect(self._pedir_parametros)
        lay.addWidget(self.btn_parametros)
        lay.addSpacing(tema.LAYOUT["barra_superior_espacio"])
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

    def _pedir_parametros(self):
        self.btn_parametros.setChecked(not self.btn_parametros.isChecked())   # deshace el cambio automático
        self.alternar_parametros.emit()

    def marcar_parametros(self, visible):
        """Refleja si el panel de parámetros está visible (botón «presionado»)."""
        self.btn_parametros.setChecked(visible)

    def actualizar_tema(self):
        otro = "oscuro" if tema.actual() == "claro" else "claro"
        self.btn_tema.setText(tema.NOMBRES[otro])
        self.btn_tema.setToolTip(f"Cambiar a {tema.NOMBRES[otro].lower()} (Ctrl+T)")
