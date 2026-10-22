"""
sombra_lateral.py
Sombra paralela del panel «Cómo se calculó», dibujada en un widget HERMANO pegado a su
borde izquierdo (degradado de transparente a sombra).

Así la sombra nunca se recorta (tiene su propio espacio en el área de resultados) y el
panel no necesita un QGraphicsEffect, que obligaría a redibujarlo fuera de pantalla en
cada cuadro de la animación (parpadeo / lentitud). No recibe clics.
"""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from . import tema

# Caída de la sombra: (posición desde el borde del panel hacia afuera, fracción de opacidad)
PERFIL = ((0.0, 1.0), (0.25, 0.55), (0.6, 0.18), (1.0, 0.0))


class SombraLateral(QWidget):

    def __init__(self, padre):
        super().__init__(padre)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.hide()

    @property
    def ancho(self):
        return tema.LAYOUT["drawer_sombra"]

    def seguir(self, panel):
        """Se coloca justo a la izquierda del panel, con su misma altura."""
        g = panel.geometry()
        self.setGeometry(g.x() - self.ancho, g.y(), self.ancho, g.height())
        self.setVisible(panel.isVisible())
        self.stackUnder(panel)

    def paintEvent(self, _e):
        base = tema.qcolor("sombra_panel")
        grad = QLinearGradient(QPointF(self.width(), 0), QPointF(0, 0))
        for pos, fraccion in PERFIL:
            c = QColor(base)
            c.setAlpha(int(base.alpha() * fraccion))
            grad.setColorAt(pos, c)
        p = QPainter(self)
        p.fillRect(self.rect(), grad)
        p.end()
