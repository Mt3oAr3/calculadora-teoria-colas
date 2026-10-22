"""
vista_tabla.py
Tabla reutilizable (QTableView sobre ModeloTabla) dentro de una tarjeta.

  * Sin barra vertical propia: la tabla toma el alto de todas sus filas y la única
    barra vertical es la de la pestaña.
  * Sin «…»: las columnas numéricas conservan su ancho natural; las de texto se
    ajustan al contenido, la última absorbe el espacio sobrante y, si no cabe, el
    texto salta de línea y la fila crece. Si ni así cabe (tablas muy anchas de
    números), aparece la barra horizontal de la tabla.
  * Filas alternadas, números a la derecha, orden opcional por columna y clic en
    una fila con fórmula -> fila_clicada(clave).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHeaderView, QLabel, QSizePolicy, QStackedLayout,
                               QTableView, QVBoxLayout, QWidget)

from . import tema
from .modelo_tabla import ROL_CLAVE, ModeloTabla, ProxyOrdenable

L = tema.LAYOUT


def encabezado_pagina(titulo, nota=""):
    """Título y nota breve de una página de resultados."""
    caja = QWidget()
    lay = QVBoxLayout(caja)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    t = QLabel(titulo)
    t.setProperty("rol", "titulo")
    lay.addWidget(t)
    if nota:
        n = QLabel(nota)
        n.setProperty("rol", "nota")
        n.setWordWrap(True)
        lay.addWidget(n)
    return caja


class _Tabla(QTableView):
    """QTableView que avisa cuando cambia el ancho útil (para reajustar columnas y alturas)."""
    redimensionada = Signal()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.redimensionada.emit()


class VistaTabla(QFrame):
    fila_clicada = Signal(str)

    def __init__(self, titulo="", ordenable=False, filas_min=4, padre=None):
        super().__init__(padre)
        self.setObjectName("Bloque")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)
        if titulo:
            self.titulo = QLabel(titulo)
            self.titulo.setProperty("rol", "seccion")
            self.titulo.setContentsMargins(12, 10, 12, 6)
            self.titulo.setWordWrap(True)
            lay.addWidget(self.titulo)
        else:
            self.titulo = None

        self.modelo = ModeloTabla(self)
        self.proxy = ProxyOrdenable(self.modelo, self) if ordenable else None
        self.vista = _Tabla()
        self.vista.setModel(self.proxy or self.modelo)
        self.vista.setAlternatingRowColors(True)
        self.vista.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vista.setSelectionMode(QAbstractItemView.SingleSelection)
        self.vista.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.vista.setShowGrid(False)
        self.vista.setWordWrap(True)
        self.vista.setTextElideMode(Qt.ElideNone)
        self.vista.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.vista.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.vista.setSortingEnabled(ordenable)
        if ordenable:   # orden original hasta que el usuario haga clic en un encabezado
            self.vista.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        vh = self.vista.verticalHeader()
        vh.hide()
        vh.setMinimumSectionSize(L["tabla_alto_fila"])
        vh.setDefaultSectionSize(L["tabla_alto_fila"])
        cab = self.vista.horizontalHeader()
        cab.setHighlightSections(False)
        cab.setMinimumSectionSize(60)
        cab.setSectionResizeMode(QHeaderView.Interactive)
        cab.sectionResized.connect(self._columna_redimensionada)
        self.vista.clicked.connect(self._clic)
        self.vista.redimensionada.connect(self._ajustar)
        (self.proxy or self.modelo).layoutChanged.connect(self._ajustar_alto)

        self.vacio = QLabel("")
        self.vacio.setProperty("rol", "vacio")
        self.vacio.setAlignment(Qt.AlignCenter)
        self.vacio.setWordWrap(True)
        self.vacio.setMinimumHeight(L["tabla_alto_fila"] * filas_min)
        self.pila = QStackedLayout()
        self.pila.addWidget(self.vista)
        self.pila.addWidget(self.vacio)
        lay.addLayout(self.pila)
        self._naturales = []
        self._ancho_previo = None
        self._ajustando = False

    def poner_titulo(self, texto):
        if self.titulo is not None:
            self.titulo.setText(texto)

    def mostrar(self, tabla, fmt):
        self.modelo.mostrar(tabla, fmt)
        if not tabla.filas:
            self.limpiar(tabla.mensaje_vacio or "Sin datos.")
            return
        self.pila.setCurrentWidget(self.vista)
        con_formula = any(f.clave for f in tabla.filas)
        self.vista.viewport().setCursor(Qt.PointingHandCursor if con_formula else Qt.ArrowCursor)
        # Un clic en una tabla con fórmulas cambia la fórmula del panel en vez de cerrarlo
        self.vista.viewport().setProperty("abre_formula", con_formula)
        self._medir_naturales()
        self._ancho_previo = None
        self._ajustar()

    def limpiar(self, mensaje):
        self.modelo.limpiar()
        self._naturales = []
        self.vacio.setText(mensaje)
        self.pila.setCurrentWidget(self.vacio)
        self.vista.setFixedHeight(L["tabla_alto_fila"])     # la tabla oculta no fija el alto del bloque
        self._fijar_alto_bloque(self.vacio.minimumHeight())

    def repintar(self):
        self.modelo.repintar()

    # ------------------------------------------------------------------
    # Dimensionado
    # ------------------------------------------------------------------
    def _medir_naturales(self):
        """Ancho natural de cada columna: contenido y encabezado en una sola línea."""
        cab = self.vista.horizontalHeader()
        self._naturales = []
        for c in range(self.modelo.columnCount()):
            contenido = max(self.vista.sizeHintForColumn(c), cab.sectionSizeHint(c))
            ancho = min(contenido + L["tabla_relleno_celda"], L["tabla_ancho_max"])
            self._naturales.append(max(ancho, cab.minimumSectionSize()))

    def _anchos(self, disponible):
        nat = list(self._naturales)
        texto = [c for c, col in enumerate(self.modelo.tabla.columnas) if not col.numerica]
        sobra = disponible - sum(nat)
        if sobra >= 0:
            if texto:
                nat[texto[-1]] += sobra             # la última columna de texto absorbe lo sobrante
            return nat
        # Falta espacio: solo se achican las columnas de texto (hasta un mínimo legible) y saltan de línea
        cab = self.vista.horizontalHeader()
        minimos = {c: min(nat[c], max(L["tabla_ancho_min_texto"],
                                      cab.sectionSizeHint(c) + L["tabla_relleno_celda"])) for c in texto}
        holgura = sum(nat[c] - minimos[c] for c in texto)
        if holgura > 0:
            recorte = min(-sobra, holgura)
            for c in texto:
                nat[c] -= int(recorte * (nat[c] - minimos[c]) / holgura + 0.999)
        return nat

    def _ajustar(self):
        if self.modelo.tabla is None or not self._naturales:
            return
        disponible = self.vista.viewport().width()
        if disponible == self._ancho_previo:
            return
        self._ancho_previo = disponible
        self._ajustando = True
        try:
            cab = self.vista.horizontalHeader()
            for c, w in enumerate(self._anchos(disponible)):
                cab.resizeSection(c, w)
        finally:
            self._ajustando = False
        self._ajustar_alto()

    def _alto_fila(self, fila):
        """Alto de una fila según su texto envuelto en el ancho de cada columna (no depende de que se vea)."""
        m = self.vista.model()
        alto = L["tabla_alto_fila"]
        for c in range(m.columnCount()):
            ix = m.index(fila, c)
            texto = ix.data() or ""
            if not texto:
                continue
            fm = QFontMetrics(ix.data(Qt.FontRole) or self.vista.font())
            ancho = max(1, self.vista.columnWidth(c) - L["tabla_relleno_celda"])
            caja = fm.boundingRect(0, 0, ancho, 100000, Qt.TextWordWrap, texto)
            alto = max(alto, caja.height() + L["tabla_relleno_vertical"])
        return alto

    def _ajustar_alto(self):
        """Filas al alto de su texto y la tabla al alto de todas sus filas (sin barra vertical)."""
        if self.modelo.tabla is None:
            return
        vh = self.vista.verticalHeader()
        filas = 0
        for r in range(self.vista.model().rowCount()):
            h = self._alto_fila(r)
            vh.resizeSection(r, h)
            filas += h
        cab = self.vista.horizontalHeader()
        rebalsa = cab.length() > self.vista.viewport().width() + 1
        barra = self.vista.horizontalScrollBar().sizeHint().height() if rebalsa else 0
        self.vista.setFixedHeight(filas + cab.sizeHint().height() + 2 * self.vista.frameWidth() + barra)
        self._fijar_alto_bloque(self.vista.height())

    def _fijar_alto_bloque(self, alto_contenido):
        """Alto mínimo explícito del bloque (título + tabla o mensaje): los layouts siempre lo respetan."""
        m = self.layout().contentsMargins()
        alto = m.top() + m.bottom() + alto_contenido
        if self.titulo is not None:
            ancho = max(1, self.width() - m.left() - m.right())
            alto += max(self.titulo.sizeHint().height(), self.titulo.heightForWidth(ancho))
        self.layout().invalidate()
        self.setMinimumHeight(max(alto, self.minimumSizeHint().height()))

    def _columna_redimensionada(self, *_):
        if not self._ajustando:          # el usuario cambió un ancho a mano: recalcula las alturas
            self._ajustar_alto()

    def _clic(self, ix):
        clave = ix.data(ROL_CLAVE)
        if clave:
            self.fila_clicada.emit(clave)
