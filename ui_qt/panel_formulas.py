"""
panel_formulas.py
Panel «Cómo se calculó»: panel acoplado a la derecha del área de resultados (no la tapa:
al abrirse el área se achica para dejarle lugar y al cerrarse vuelve a crecer). Borde
izquierdo de 1 px. Se cierra con su botón, con Esc o con un clic fuera.

El ancho del panel lo anima la ventana (ui_qt/animacion.AnimadorPaneles) entre 0 y
`ancho_abierto`; el contenido mide siempre `ancho_abierto` y el panel solo lo recorta, así
durante la animación no se vuelve a acomodar ni a renderizar nada.

Muestra título, explicación, la fórmula dibujada con matplotlib, la misma fórmula
con los valores actuales y el resultado. No guarda fórmulas: cada vez la pide a
services.formulas con el escenario vigente o, para una fila de «Comparar k y M», con
el escenario de esa fila (`contexto`, p. ej. "k = 3", va en el título). Al cambiar el
tema se regenera con el mismo escenario con que se abrió.
"""
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from services import formulas as fm

from . import animacion, tema
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
        self._color = None          # color de texto con que se dibujó (cambia con el tema)
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
        self._color = color
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
    abriendo = Signal()         # se abrió: la ventana decide su ancho y lo despliega
    cerrado = Signal()          # se cerró: la ventana lo repliega

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("PanelFormulas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.clave = None
        self.contexto = None        # "k = 3" si muestra una fila de «Comparar k y M»; None: escenario vigente
        self._nombre = None         # nombre de la métrica de esa fila (para el mensaje si no aplica)
        self.abierto = False
        self._esc = self._fmt = None
        self._imagenes = []
        self._imagenes_pendientes = False
        self.ancho_abierto = L["drawer_min"]

        # Contenido de ancho fijo (ancho_abierto); el panel lo recorta mientras se despliega
        self.contenido = QWidget(self)
        self.contenido.setObjectName("ContenidoFormulas")
        lay = QVBoxLayout(self.contenido)
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
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(0)
        self.hide()
        animacion.indicador.cambio.connect(self._animacion_cambio)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._soltar_filtro)

    # ------------------------------------------------------------------
    # Ancho, apertura y cierre
    # ------------------------------------------------------------------
    def poner_ancho_abierto(self, ancho):
        """Ancho del panel desplegado (lo calcula la ventana); solo aquí se reacomoda el contenido."""
        if ancho != self.ancho_abierto:
            self.ancho_abierto = ancho
            self._colocar_contenido()
            self._ajustar_imagenes()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._colocar_contenido()

    def _colocar_contenido(self):
        # 1 px a la izquierda para el borde del panel (#PanelFormulas, ver tema.py)
        self.contenido.setGeometry(1, 0, max(1, self.ancho_abierto - 1), self.height())

    def _soltar_filtro(self):
        QApplication.instance().removeEventFilter(self)

    def abrir(self, esc, clave, fmt, contexto=None, nombre=None):
        if self.abierto:
            self.mostrar(esc, clave, fmt, contexto, nombre)
            return
        self.abierto = True
        # Primero se dibujan las ecuaciones (matplotlib) y recién después se despliega el panel:
        # así la animación no pierde cuadros mientras se renderiza el contenido.
        self.mostrar(esc, clave, fmt, contexto, nombre)
        self.show()
        QApplication.instance().installEventFilter(self)
        self.abriendo.emit()

    def cerrar(self):
        if not self.abierto:
            return
        self.abierto = False
        self.clave = self.contexto = None
        self._soltar_filtro()
        self.cerrado.emit()

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
    def mostrar(self, esc, clave, fmt, contexto=None, nombre=None):
        """Pide la fórmula al servicio con el escenario dado y la dibuja (reemplaza el contenido)."""
        self.clave, self._esc, self._fmt = clave, esc, fmt
        self.contexto, self._nombre = contexto, nombre
        self._imagenes = []
        cuerpo = QWidget()
        cuerpo.setObjectName("CuerpoFormulas")
        lc = QVBoxLayout(cuerpo)
        lc.setContentsMargins(L["drawer_margen"], 4, L["drawer_margen"], L["drawer_margen"])
        lc.setSpacing(L["drawer_espacio"])
        try:
            f = fm.formula(esc, clave, fmt)
        except fm.FormulaNoDisponible as e:
            if contexto:
                lc.addWidget(_texto(f"{nombre} para {contexto}", nombre="FormulaTitulo"))
                aviso = _texto(f"{tema.ICONOS['aviso']}  {e} Elige otra métrica en «Condición de búsqueda».",
                               "mensaje")
                aviso.setProperty("nivel", "aviso")
                lc.addWidget(aviso)
            else:
                lc.addWidget(_texto(str(e), "nota"))
        else:
            fila = f"Fila {contexto} de «Comparar k y M» · " if contexto else ""
            lc.addWidget(_texto(f"{fila}{esc.kendall} · {esc.sigla}", "nota"))
            self._agregar(lc, f, principal=True)
            for extra in f.extras:
                self._agregar(lc, extra, principal=False)
        lc.addStretch(1)
        self.scroll.setWidget(cuerpo)        # QScrollArea elimina el contenido anterior
        self._ajustar_imagenes()

    def actualizar(self, esc, fmt):
        """Vuelve a generar la fórmula abierta (nuevo cálculo, presentación o tema) con su mismo contexto."""
        if self.clave and self.abierto and esc is not None:
            self.mostrar(esc, self.clave, fmt, self.contexto, self._nombre)

    def repintar(self):
        if self._esc is not None:
            self.actualizar(self._esc, self._fmt)

    def _agregar(self, lc, f, principal):
        if principal:
            lc.addWidget(_texto(f"{f.titulo} para {self.contexto}" if self.contexto else f.titulo,
                                nombre="FormulaTitulo"))
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
        """Ecuaciones al ancho del contenido; mientras se anima un panel, se hace al terminar."""
        if animacion.animando():
            self._imagenes_pendientes = True
            return
        self._imagenes_pendientes = False
        m = L["caja_formula_margen"]
        barra = self.scroll.verticalScrollBar().sizeHint().width()
        ancho = self.ancho_abierto - 2 * L["drawer_margen"] - m[0] - m[2] - barra - 2
        for img in self._imagenes:
            img.ajustar(ancho)

    def _animacion_cambio(self, activa):
        if not activa and self._imagenes_pendientes:
            self._ajustar_imagenes()
