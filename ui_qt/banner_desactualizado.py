"""
banner_desactualizado.py
Único aviso de «datos desactualizados» de la interfaz: banner ámbar bajo la barra
superior, con botón «Calcular». Aparece y desaparece con una animación corta de
altura para que el contenido no salte. El texto puede ocupar una o dos líneas; el
botón queda centrado verticalmente respecto a él.
"""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from . import tema

TEXTO = "Cambiaste parámetros: los resultados mostrados son del cálculo anterior."
SIN_LIMITE = 16777215          # QWIDGETSIZE_MAX


class BannerDesactualizado(QFrame):
    calcular = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Banner")
        self.setAccessibleName("Aviso de datos desactualizados")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        L = tema.LAYOUT
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*L["banner_margen"])
        lay.setSpacing(L["banner_espacio"])
        icono = QLabel(tema.ICONOS["aviso"])
        icono.setObjectName("BannerIcono")
        self.texto = QLabel(TEXTO)
        self.texto.setObjectName("BannerTexto")
        self.texto.setWordWrap(True)
        self.texto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.boton = QPushButton("Calcular")
        self.boton.setObjectName("BannerBoton")
        self.boton.setCursor(Qt.PointingHandCursor)
        self.boton.setToolTip("Recalcular con los parámetros actuales (Enter o F5)")
        self.boton.clicked.connect(self.calcular.emit)
        lay.addWidget(icono, 0, Qt.AlignVCenter)
        lay.addWidget(self.texto, 1, Qt.AlignVCenter)
        lay.addWidget(self.boton, 0, Qt.AlignVCenter)

        self._anim = QPropertyAnimation(self, b"maximumHeight", self)
        self._anim.setDuration(L["banner_ms"])
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._fin)
        self._visible = False
        self.setMaximumHeight(0)
        self.hide()

    @property
    def activo(self):
        """True si el aviso está mostrado (o apareciendo)."""
        return self._visible

    def _alto_natural(self):
        lay = self.layout()
        if lay.hasHeightForWidth() and self.width() > 0:
            return max(lay.heightForWidth(self.width()), lay.minimumSize().height())
        return lay.sizeHint().height()

    def mostrar(self, si):
        if si == self._visible:
            return
        self._visible = si
        self._anim.stop()
        if si:
            self.show()
        self._anim.setStartValue(min(self.maximumHeight(), self._alto_natural()))
        self._anim.setEndValue(self._alto_natural() if si else 0)
        self._anim.start()

    def _fin(self):
        if self._visible:
            self.setMaximumHeight(SIN_LIMITE)      # libre: se adapta si el texto pasa a dos líneas
        else:
            self.hide()
