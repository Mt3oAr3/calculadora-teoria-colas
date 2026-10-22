"""
panel_formulas.py
Panel «Cómo se calculó»: drawer flotante anclado al borde derecho del área de
resultados. Se superpone al contenido (no cambia su ancho), tiene sombra, se abre
y se cierra deslizándose, y se cierra con su botón, con Esc o con un clic fuera.

Muestra título, explicación, la fórmula dibujada con matplotlib, la misma fórmula
con los valores actuales y el resultado. No guarda fórmulas: cada vez la pide a
services.formulas con el escenario vigente.
"""
from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from services import formulas as fm

from . import tema
from .render_formula import formula_a_pixmap

L = tema.LAYOUT


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
    """Ecuación centrada; se achica hasta formula_puntos_min para caber y, si aún no cabe, se desplaza."""

    def __init__(self, latex):
        super().__init__()
        self.setObjectName("FilaFormula")
        self.latex = latex
        self._ancho = None
        self.img = QLabel()
        self.setWidget(self.img)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignCenter)
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
        normal = L["formula_puntos"]
        pix = formula_a_pixmap(self.latex, color, escala, normal)
        w = pix.deviceIndependentSize().width()
        if w > ancho:
            pix = formula_a_pixmap(self.latex, color, escala, max(L["formula_puntos_min"], normal * ancho / w * 0.97))
        self.img.setPixmap(pix)
        self.img.adjustSize()
        rebalsa = pix.deviceIndependentSize().width() > ancho
        barra = self.horizontalScrollBar().sizeHint().height() if rebalsa else 0
        self.setFixedHeight(self.img.height() + barra + 2)


class PanelFormulas(QFrame):
    cerrado = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("PanelFormulas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.clave = None
        self.abierto = False
        self._esc = self._fmt = None
        self._imagenes = []
        self._area = None

        self.sombra = QGraphicsDropShadowEffect(self)
        self.sombra.setBlurRadius(L["drawer_sombra"])
        self.sombra.setOffset(-4, 0)
        self.setGraphicsEffect(self.sombra)
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(L["drawer_ms"])
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._fin_animacion)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        cab = QHBoxLayout()
        cab.setContentsMargins(L["drawer_margen"], 12, 10, 6)
        titulo = QLabel("Cómo se calculó")
        titulo.setProperty("rol", "titulo")
        cab.addWidget(titulo, 1)
        self.btn_cerrar = QPushButton("✕  Cerrar")
        self.btn_cerrar.setToolTip("Cerrar el panel (Esc o clic fuera)")
        self.btn_cerrar.setCursor(Qt.PointingHandCursor)
        self.btn_cerrar.clicked.connect(self.cerrar)
        cab.addWidget(self.btn_cerrar, 0, Qt.AlignTop)
        lay.addLayout(cab)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ScrollFormulas")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lay.addWidget(self.scroll, 1)
        self.hide()

    # ------------------------------------------------------------------
    # Anclaje, apertura y cierre
    # ------------------------------------------------------------------
    def anclar(self, area):
        """Superpone el panel al borde derecho de `area` (sin entrar en su layout)."""
        self._area = area
        self.setParent(area)
        area.redimensionada.connect(self._reacomodar)
        QApplication.instance().aboutToQuit.connect(self._soltar_filtro)
        self.hide()

    def _reacomodar(self):
        if self.isVisible():
            self._anim.stop()
            self.setGeometry(self._geometria(self.abierto))
            self._ajustar_imagenes()

    def _soltar_filtro(self):
        QApplication.instance().removeEventFilter(self)

    def _geometria(self, abierto):
        a = self._area.rect()
        ancho = int(min(L["drawer_max"], max(L["drawer_min"], a.width() * L["drawer_fraccion"])))
        ancho = min(ancho, a.width())
        x = a.width() - ancho if abierto else a.width()
        return QRect(x, 0, ancho, a.height())

    def abrir(self, esc, clave, fmt):
        if not self.abierto:
            self.abierto = True
            self.sombra.setColor(tema.qcolor("sombra"))
            self.setGeometry(self._geometria(False))
            self.show()
            self.raise_()
            self._animar(self._geometria(True).topLeft())
            QApplication.instance().installEventFilter(self)
        self.mostrar(esc, clave, fmt)

    def cerrar(self):
        if not self.abierto:
            return
        self.abierto = False
        self.clave = None
        self._soltar_filtro()
        self._animar(self._geometria(False).topLeft())
        self.cerrado.emit()

    def _animar(self, destino):
        self._anim.stop()
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(QPoint(destino))
        self._anim.start()

    def _fin_animacion(self):
        if not self.abierto:
            self.hide()

    def eventFilter(self, obj, evento):
        """Filtro de la aplicación, activo solo con el panel abierto: un clic fuera lo cierra."""
        if evento.type() == QEvent.MouseButtonPress and self.abierto and isinstance(obj, QWidget):
            if not self._dentro(evento.globalPosition().toPoint()) and not self._abre_formula(obj):
                self.cerrar()
        return False

    def _dentro(self, punto_global):
        return self.rect().contains(self.mapFromGlobal(punto_global))

    @staticmethod
    def _abre_formula(widget):
        """Clic en una tarjeta o tabla con fórmulas: cambia la fórmula en vez de cerrar."""
        while widget is not None:
            if widget.property("abre_formula"):
                return True
            widget = widget.parentWidget()
        return False

    # ------------------------------------------------------------------
    # Contenido
    # ------------------------------------------------------------------
    def mostrar(self, esc, clave, fmt):
        """Pide la fórmula al servicio con el escenario dado y la dibuja (reemplaza el contenido)."""
        self.clave, self._esc, self._fmt = clave, esc, fmt
        self._imagenes = []
        cuerpo = QWidget()
        cuerpo.setObjectName("CuerpoFormulas")
        lc = QVBoxLayout(cuerpo)
        lc.setContentsMargins(L["drawer_margen"], 4, L["drawer_margen"], L["drawer_margen"])
        lc.setSpacing(L["drawer_espacio"])
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
        if self.clave and self.abierto and esc is not None:
            self.mostrar(esc, self.clave, fmt)

    def repintar(self):
        self.sombra.setColor(tema.qcolor("sombra"))
        if self._esc is not None:
            self.actualizar(self._esc, self._fmt)

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
        caja = QFrame()
        if principal:
            caja.setObjectName("CajaResultado")
        fila = QHBoxLayout(caja)
        fila.setContentsMargins(*(L["caja_formula_margen"] if principal else (0, 0, 0, 0)))
        lbl = QLabel("Resultado")
        lbl.setProperty("rol", "campo")
        fila.addWidget(lbl)
        res = _texto(self._fmt.texto(f.resultado), nombre="FormulaResultado" if principal else "FormulaResultadoExtra")
        res.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fila.addWidget(res, 1)
        lc.addWidget(caja)

    def _caja(self, titulo, formulas):
        caja = QFrame()
        caja.setObjectName("CajaFormula")
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(*L["caja_formula_margen"])
        lay.setSpacing(L["caja_formula_espacio"])
        lay.addWidget(_texto(titulo, "nota"))
        for latex in formulas:
            img = ImagenFormula(latex)
            self._imagenes.append(img)
            lay.addWidget(img)
        return caja

    def _ajustar_imagenes(self):
        m = L["caja_formula_margen"]
        barra = self.scroll.verticalScrollBar().sizeHint().width()
        ancho = self.width() - 2 * L["drawer_margen"] - m[0] - m[2] - barra - 2
        for img in self._imagenes:
            img.ajustar(ancho)
