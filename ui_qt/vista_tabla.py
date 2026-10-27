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

from . import animacion, tema
from .info_box import InfoBox
from .modelo_tabla import ROL_CLAVE, ModeloTabla, ProxyOrdenable

L = tema.LAYOUT


def encabezado_pagina(titulo, nota=""):
    """Título de una página de resultados y, debajo, su explicación en una caja informativa."""
    caja = QWidget()
    lay = QVBoxLayout(caja)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(tema.LAYOUT["info_espacio"])
    t = QLabel(titulo)
    t.setProperty("rol", "titulo")
    lay.addWidget(t)
    if nota:
        lay.addWidget(InfoBox(nota))
    return caja


class _Tabla(QTableView):
    """QTableView que avisa cuando cambia el ancho útil (para reajustar columnas y alturas)."""
    redimensionada = Signal()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.redimensionada.emit()


class VistaTabla(QFrame):
    fila_clicada = Signal(str)

    def __init__(self, titulo="", ordenable=False, filas_min=4, filas_max=None, padre=None):
        super().__init__(padre)
        self.estado_vacio = None          # widget opcional que reemplaza a la tabla (ver usar_estado_vacio)
        self.extra = None                 # widget opcional bajo el título (p. ej. chips)
        # Con más de filas_max filas la tabla no crece más: tiene su propia barra vertical
        self.filas_max = filas_max
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
        self.vista = _Tabla(self)          # con padre desde el inicio: nunca es ventana propia
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
        cab.sortIndicatorChanged.connect(self._reordenado)
        self.vista.clicked.connect(self._clic)
        self.vista.redimensionada.connect(self._ajustar)
        (self.proxy or self.modelo).layoutChanged.connect(self._ajustar_alto)

        self.vacio = QLabel("", self)
        self.vacio.setProperty("rol", "vacio")
        self.vacio.setAlignment(Qt.AlignCenter)
        self.vacio.setWordWrap(True)
        self.vacio.setMinimumHeight(L["tabla_alto_fila"] * filas_min)
        # El QStackedLayout muestra/oculta sus widgets al agregarlos: se instala en el bloque ANTES de
        # recibirlos; si no, el widget sin padre aparece un instante como ventana de nivel superior.
        self.pila = QStackedLayout()
        lay.addLayout(self.pila)
        self.pila.addWidget(self.vista)
        self.pila.addWidget(self.vacio)
        self._naturales = []
        self._ancho_previo = None
        self._ajustando = False
        self._diferido = False            # hubo cambios de ancho durante una animación de paneles
        animacion.indicador.cambio.connect(self._animacion_cambio)

    def poner_titulo(self, texto):
        if self.titulo is not None:
            self.titulo.setText(texto)

    def agregar_bajo_titulo(self, widget):
        """Widget entre el título y la tabla (cuenta en el alto del bloque)."""
        self.extra = widget
        self.layout().insertWidget(0 if self.titulo is None else 1, widget)

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

    def usar_estado_vacio(self, widget):
        """Registra un estado vacío propio (p. ej. EstadoVacio) para mostrar en lugar de la tabla."""
        self.estado_vacio = widget
        self.pila.addWidget(widget)

    def mostrar_estado_vacio(self):
        self.modelo.limpiar()
        self._naturales = []
        self.pila.setCurrentWidget(self.estado_vacio)
        self.vista.setFixedHeight(L["tabla_alto_fila"])
        m = self.layout().contentsMargins()
        self._fijar_alto_bloque(self.estado_vacio.alto_para(max(1, self.width() - m.left() - m.right())))

    def repintar(self):
        self.modelo.repintar()

    def _reordenado(self, *_):
        """La flecha ↑/↓ alarga el título de la columna ordenada: se vuelven a medir los anchos."""
        if self.modelo.tabla is not None and self._naturales:
            self._medir_naturales()
            self._ancho_previo = None
            self._ajustar()

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
                # La última columna de texto absorbe el sobrante, pero si tiene cifras a su derecha crece a lo
                # sumo una holgura: los números quedan cerca de su etiqueta y el resto es espacio libre.
                c = texto[-1]
                nat[c] += sobra if c == len(nat) - 1 else min(sobra, L["tabla_holgura_texto"])
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

    @property
    def pendiente(self):
        """True si quedó un reajuste completo para cuando termine la animación de los paneles."""
        return self._diferido

    def _animacion_cambio(self, activa):
        if not activa and self._diferido:
            self._diferido = False
            self._ancho_previo = None
            self._ajustar()

    def _ajuste_rapido(self):
        """
        Durante la animación de los paneles: solo la columna de texto absorbente toma el cambio de
        ancho (sin medir columnas ni filas). El reajuste completo se hace una vez, al terminar.
        """
        self._diferido = True
        if self.modelo.tabla is None or not self._naturales:
            return
        texto = [c for c, col in enumerate(self.modelo.tabla.columnas) if not col.numerica]
        if not texto:
            return                         # sin columna de texto: sobra espacio libre o aparece la barra
        c = texto[-1]
        cab = self.vista.horizontalHeader()
        nuevo = cab.sectionSize(c) + self.vista.viewport().width() - cab.length()
        tope = None if c == len(self._naturales) - 1 else self._naturales[c] + L["tabla_holgura_texto"]
        nuevo = max(min(self._naturales[c], L["tabla_ancho_min_texto"]), nuevo if tope is None else min(nuevo, tope))
        if nuevo != cab.sectionSize(c):
            self._ajustando = True
            try:
                cab.resizeSection(c, nuevo)
            finally:
                self._ajustando = False

    def _ajustar(self):
        if animacion.animando():
            self._ajuste_rapido()
            return
        if self.estado_vacio is not None and self.pila.currentWidget() is self.estado_vacio:
            m = self.layout().contentsMargins()
            self._fijar_alto_bloque(self.estado_vacio.alto_para(max(1, self.width() - m.left() - m.right())))
            return
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

    def _alto_fila(self, fila, angostas):
        """
        Alto de una fila según su texto envuelto en el ancho de cada columna (no depende de que se vea).
        Solo las columnas `angostas` (más angostas que su contenido en una línea) pueden partir el
        texto: las demás ocupan una línea y no hace falta medirlas celda por celda.
        """
        m = self.vista.model()
        fm = QFontMetrics(m.index(fila, 0).data(Qt.FontRole) or self.vista.font())    # la fuente es por fila
        alto = max(L["tabla_alto_fila"], fm.height() + L["tabla_relleno_vertical"])
        for c in angostas:
            texto = m.index(fila, c).data() or ""
            if not texto:
                continue
            ancho = max(1, self.vista.columnWidth(c) - L["tabla_relleno_celda"])
            caja = fm.boundingRect(0, 0, ancho, 100000, Qt.TextWordWrap, texto)
            alto = max(alto, caja.height() + L["tabla_relleno_vertical"])
        return alto

    def _columnas_angostas(self):
        """Columnas más angostas que su ancho natural (contenido en una línea): las únicas que parten texto."""
        n = self.vista.model().columnCount()
        if len(self._naturales) != n:
            return list(range(n))
        return [c for c in range(n) if self.vista.columnWidth(c) < self._naturales[c]]

    def _ajustar_alto(self):
        """Filas al alto de su texto y la tabla al alto de todas sus filas (sin barra vertical)."""
        if self.modelo.tabla is None:
            return
        vh = self.vista.verticalHeader()
        angostas = self._columnas_angostas()
        altos = []
        for r in range(self.vista.model().rowCount()):
            h = self._alto_fila(r, angostas)
            vh.resizeSection(r, h)
            altos.append(h)
        limitada = self.filas_max is not None and len(altos) > self.filas_max
        self.vista.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if limitada else Qt.ScrollBarAlwaysOff)
        filas = sum(altos[:self.filas_max] if limitada else altos)
        cab = self.vista.horizontalHeader()
        rebalsa = cab.length() > self.vista.viewport().width() + 1
        barra = self.vista.horizontalScrollBar().sizeHint().height() if rebalsa else 0
        self.vista.setFixedHeight(filas + cab.sizeHint().height() + 2 * self.vista.frameWidth() + barra)
        self._fijar_alto_bloque(self.vista.height())

    def _fijar_alto_bloque(self, alto_contenido):
        """Alto mínimo explícito del bloque (título + tabla o mensaje): los layouts siempre lo respetan."""
        m = self.layout().contentsMargins()
        alto = m.top() + m.bottom() + alto_contenido
        ancho = max(1, self.width() - m.left() - m.right())
        if self.titulo is not None:
            alto += max(self.titulo.sizeHint().height(), self.titulo.heightForWidth(ancho))
        if self.extra is not None and not self.extra.isHidden():
            alto += self.extra.heightForWidth(ancho)
        self.layout().invalidate()
        self.setMinimumHeight(max(alto, self.minimumSizeHint().height()))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.estado_vacio is not None and self.pila.currentWidget() is self.estado_vacio:
            self._ajustar()

    def _columna_redimensionada(self, *_):
        if not self._ajustando:          # el usuario cambió un ancho a mano: recalcula las alturas
            self._ajustar_alto()

    def _clic(self, ix):
        clave = ix.data(ROL_CLAVE)
        if clave:
            self.fila_clicada.emit(clave)

    def _indice_de(self, clave):
        m = self.vista.model()
        for r in range(m.rowCount()):
            if m.index(r, 0).data(ROL_CLAVE) == clave:
                return m.index(r, 0)
        return None

    def seleccionar_clave(self, clave):
        """Resalta la fila con esa clave (también tras reordenar o volver a mostrar) y la deja a la vista."""
        ix = self._indice_de(clave)
        if ix is None:
            return False
        self.vista.selectRow(ix.row())
        self.vista.scrollTo(ix, QAbstractItemView.EnsureVisible)
        return True

    def desplazar_a_clave(self, clave):
        """Deja a la vista la fila con esa clave (tablas con barra propia); False si no está."""
        ix = self._indice_de(clave)
        if ix is not None:
            self.vista.scrollTo(ix, QAbstractItemView.PositionAtTop)
        return ix is not None

    def quitar_seleccion(self):
        self.vista.clearSelection()

