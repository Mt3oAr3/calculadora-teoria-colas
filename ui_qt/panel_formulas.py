"""
panel_formulas.py
Panel lateral «Cómo se calculó»: título, explicación, fórmula dibujada con
matplotlib, la misma fórmula con los valores actuales y el resultado.

No guarda fórmulas: cada vez que se muestra la pide a services.formulas con el
escenario vigente (al hacer clic, al recalcular o al cambiar presentación/tema).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
                               QWidget)

from services import formulas as fm

from . import tema
from .render_formula import PUNTOS, formula_a_pixmap

ANCHO_MIN = 320
PUNTOS_MIN = 9           # por debajo de esto la fórmula se desplaza en horizontal en vez de achicarse
MARGEN = 16
MARGEN_CAJA = 12


def _texto(txt, rol=None, nombre=None):
    lbl = QLabel(txt)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    if rol:
        lbl.setProperty("rol", rol)
    if nombre:
        lbl.setObjectName(nombre)
    return lbl


class ImagenFormula(QScrollArea):
    """Fórmula dibujada; se achica hasta PUNTOS_MIN para caber y, si aún no cabe, se desplaza."""

    def __init__(self, latex):
        super().__init__()
        self.setObjectName("FilaFormula")
        self.latex = latex
        self._ancho = None
        self.img = QLabel()
        self.setWidget(self.img)
        self.setWidgetResizable(False)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def ajustar(self, ancho):
        if ancho == self._ancho or ancho <= 0:
            return
        self._ancho = ancho
        escala = self.devicePixelRatioF() or 1.0
        color = tema.color("texto")
        pix = formula_a_pixmap(self.latex, color, escala, PUNTOS)
        w = pix.deviceIndependentSize().width()
        if w > ancho:
            pix = formula_a_pixmap(self.latex, color, escala, max(PUNTOS_MIN, PUNTOS * ancho / w * 0.97))
        self.img.setPixmap(pix)
        self.img.adjustSize()
        rebalsa = pix.deviceIndependentSize().width() > ancho
        self.setFixedHeight(self.img.height() + (12 if rebalsa else 2))


class PanelFormulas(QFrame):
    cerrado = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("PanelFormulas")
        self.setMinimumWidth(ANCHO_MIN)
        self.clave = None
        self._esc = self._fmt = None
        self._imagenes = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        cab = QHBoxLayout()
        cab.setContentsMargins(MARGEN, 12, 8, 6)
        titulo = QLabel("Cómo se calculó")
        titulo.setProperty("rol", "titulo")
        cab.addWidget(titulo, 1)
        cerrar = QPushButton("✕")
        cerrar.setObjectName("Plano")
        cerrar.setToolTip("Cerrar el panel (Esc)")
        cerrar.setCursor(Qt.PointingHandCursor)
        cerrar.clicked.connect(self.cerrar)
        cab.addWidget(cerrar, 0, Qt.AlignTop)
        lay.addLayout(cab)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ScrollFormulas")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lay.addWidget(self.scroll, 1)

    # ------------------------------------------------------------------
    def mostrar(self, esc, clave, fmt):
        """Pide la fórmula al servicio con el escenario dado y la dibuja (reemplaza el contenido)."""
        self.clave, self._esc, self._fmt = clave, esc, fmt
        self._imagenes = []
        cuerpo = QWidget()
        cuerpo.setObjectName("CuerpoFormulas")
        lc = QVBoxLayout(cuerpo)
        lc.setContentsMargins(MARGEN, 4, MARGEN, MARGEN)
        lc.setSpacing(10)
        try:
            f = fm.formula(esc, clave, fmt)
        except fm.FormulaNoDisponible as e:
            lc.addWidget(_texto(str(e), "nota"))
        else:
            lc.addWidget(_texto(f"{esc.kendall} · {esc.sigla}", "nota"))
            self._agregar(lc, f, principal=True)
            for extra in f.extras:
                self._agregar(lc, extra, principal=False)
        lc.addStretch(1)
        self.scroll.setWidget(cuerpo)        # QScrollArea elimina el contenido anterior
        self._ajustar_imagenes()

    def actualizar(self, esc, fmt):
        """Vuelve a generar la fórmula abierta (nuevo cálculo, presentación o tema)."""
        if self.clave and self.isVisible() and esc is not None:
            self.mostrar(esc, self.clave, fmt)

    def repintar(self):
        if self._esc is not None:
            self.actualizar(self._esc, self._fmt)

    def cerrar(self):
        self.clave = None
        self.hide()
        self.cerrado.emit()

    # ------------------------------------------------------------------
    def _agregar(self, lc, f, principal):
        if principal:
            lc.addWidget(_texto(f.titulo, nombre="FormulaTitulo"))
            lc.addWidget(_texto(f.explicacion, "subtitulo"))
        else:
            sep = QFrame()
            sep.setProperty("rol", "separador")
            lc.addWidget(sep)
            lc.addWidget(_texto(f.titulo, "seccion"))
        lc.addWidget(self._caja("Fórmula", [f.latex]))
        lc.addWidget(self._caja("Con los datos actuales", list(f.pasos)))
        fila = QHBoxLayout()
        lbl = QLabel("Resultado")
        lbl.setProperty("rol", "campo")
        fila.addWidget(lbl)
        res = _texto(self._fmt.texto(f.resultado), nombre="FormulaResultado" if principal else None)
        res.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fila.addWidget(res, 1)
        lc.addLayout(fila)

    def _caja(self, titulo, formulas):
        caja = QFrame()
        caja.setObjectName("CajaFormula")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(MARGEN_CAJA, 8, MARGEN_CAJA, 10)
        lay.setSpacing(6)
        lay.addWidget(_texto(titulo, "nota"))
        for latex in formulas:
            img = ImagenFormula(latex)
            self._imagenes.append(img)
            lay.addWidget(img)
        return caja

    def _ajustar_imagenes(self):
        ancho = self.width() - 2 * MARGEN - 2 * MARGEN_CAJA - 14     # bordes y barra vertical
        for img in self._imagenes:
            img.ajustar(ancho)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ajustar_imagenes()
