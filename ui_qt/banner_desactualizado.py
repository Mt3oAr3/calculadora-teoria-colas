"""
banner_desactualizado.py
Único aviso de «datos desactualizados» de la interfaz: banner ámbar bajo la barra
superior, con botón «Calcular». Aparece y desaparece con una animación corta de
altura para que el contenido no salte.
"""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from . import tema

TEXTO = "Cambiaste parámetros: los resultados mostrados son del cálculo anterior."


class BannerDesactualizado(QFrame):
    calcular = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Banner")
        self.setAccessibleName("Aviso de datos desactualizados")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*tema.LAYOUT["banner_margen"])
        icono = QLabel("⚠")
        icono.setObjectName("BannerIcono")
        texto = QLabel(TEXTO)
        texto.setObjectName("BannerTexto")
        boton = QPushButton("Calcular")
        boton.setObjectName("BannerBoton")
        boton.setCursor(Qt.PointingHandCursor)
        boton.setToolTip("Recalcular con los parámetros actuales (Enter o F5)")
        boton.clicked.connect(self.calcular.emit)
        lay.addWidget(icono)
        lay.addWidget(texto, 1)
        lay.addWidget(boton)

        self._alto = tema.LAYOUT["banner_alto"]
        self._anim = QPropertyAnimation(self, b"maximumHeight", self)
        self._anim.setDuration(tema.LAYOUT["banner_ms"])
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._fin)
        self._visible = False
        self.setMaximumHeight(0)
        self.hide()

    @property
    def activo(self):
        """True si el aviso está mostrado (o apareciendo)."""
        return self._visible

    def mostrar(self, si):
        if si == self._visible:
            return
        self._visible = si
        self._anim.stop()
        if si:
            self.show()
        self._anim.setStartValue(self.maximumHeight())
        self._anim.setEndValue(self._alto if si else 0)
        self._anim.start()

    def _fin(self):
        if not self._visible:
            self.hide()
