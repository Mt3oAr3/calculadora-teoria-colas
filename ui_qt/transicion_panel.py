"""
transicion_panel.py
Cuadros de la animación del panel de parámetros (Ctrl+B) sin reacomodar nada.

Reacomodar el área de resultados en cada cuadro es caro (tablas que miden sus filas, el
lienzo de matplotlib que se redibuja, el panel «Cómo se calculó» que se reubica): en las
pestañas pesadas un cuadro costaba 50-130 ms. En su lugar, mientras dura la animación esta
capa tapa el divisor y desplaza dos capturas tomadas al empezar: la del panel (entra o sale
por la izquierda) y la del área de resultados (se corre con él). Si el panel «Cómo se
calculó» está abierto, su franja de la captura queda fija contra el borde derecho, como
quedará al final. El layout real se aplica una sola vez, al terminar (ver
VentanaPrincipal.mostrar_parametros).
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from . import tema


class TransicionPanel(QWidget):

    def __init__(self, padre=None):
        super().__init__(padre)
        self._panel = self._area = None      # capturas (QPixmap)
        self._ancho_panel = 1                # ancho del panel completamente visible
        self._separador = 0                  # ancho del separador del divisor
        self._anclada = 0                    # franja derecha del área que no se desplaza (drawer abierto)
        self.ancho = 0                       # ancho visible del panel en este cuadro
        # Opaca: Qt no repinta lo que queda debajo (las tablas y la gráfica) en cada cuadro
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.hide()

    def preparar(self, geometria, captura_panel, ancho_panel, captura_area, separador, anclada=0):
        """
        Tapa `geometria` (la del divisor) con las capturas; el panel visible mide `ancho_panel` y
        los `anclada` px de la derecha del área (drawer y su sombra) quedan fijos contra el borde.
        """
        self._panel, self._area = captura_panel, captura_area
        self._ancho_panel, self._separador, self._anclada = max(1, ancho_panel), separador, anclada
        self.setGeometry(geometria)
        self.show()
        self.raise_()

    def poner_ancho(self, ancho):
        ancho = int(round(ancho))
        if ancho != self.ancho:              # sin cambio de píxel entero no se repinta
            self.ancho = ancho
            self.update()

    def terminar(self):
        self.hide()
        self._panel = self._area = None      # libera las capturas

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), tema.qcolor("fondo"))
        if self._area is not None:
            x = self.ancho + round(self._separador * self.ancho / self._ancho_panel)
            escala = self._area.devicePixelRatio()
            ancho, alto = self._area.width() / escala, self._area.height() / escala
            corte = ancho - self._anclada
            p.drawPixmap(QRectF(x, 0, corte, alto), self._area, QRectF(0, 0, corte * escala, alto * escala))
            if self._anclada:
                p.drawPixmap(QRectF(self.width() - self._anclada, 0, self._anclada, alto), self._area,
                             QRectF(corte * escala, 0, self._anclada * escala, alto * escala))

        if self._panel is not None and self.ancho > 0:
            p.drawPixmap(self.ancho - self._ancho_panel, 0, self._panel)
        p.end()
