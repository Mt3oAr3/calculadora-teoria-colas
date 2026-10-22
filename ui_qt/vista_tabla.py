"""
vista_tabla.py
Tabla reutilizable (QTableView sobre ModeloTabla) dentro de una tarjeta, con
mensaje cuando está vacía, cabecera fija, filas alternadas, números a la
derecha y, opcionalmente, orden por columna. Emite la clave de la fórmula de
la fila clicada.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHeaderView, QLabel, QStackedLayout, QTableView,
                               QVBoxLayout, QWidget)

from .modelo_tabla import ROL_CLAVE, ModeloTabla, ProxyOrdenable

ALTO_FILA = 30
ANCHO_MAX_COLUMNA = 420


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


class VistaTabla(QFrame):
    fila_clicada = Signal(str)

    def __init__(self, titulo="", ordenable=False, filas_min=4, padre=None):
        super().__init__(padre)
        self.setObjectName("Bloque")
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
        self.vista = QTableView()
        self.vista.setModel(self.proxy or self.modelo)
        self.vista.setAlternatingRowColors(True)
        self.vista.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vista.setSelectionMode(QAbstractItemView.SingleSelection)
        self.vista.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.vista.setShowGrid(False)
        self.vista.setWordWrap(False)
        self.vista.setSortingEnabled(ordenable)
        if ordenable:   # orden original hasta que el usuario haga clic en un encabezado
            self.vista.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.vista.verticalHeader().hide()
        self.vista.verticalHeader().setDefaultSectionSize(ALTO_FILA)
        cab = self.vista.horizontalHeader()
        cab.setHighlightSections(False)
        cab.setMinimumSectionSize(60)
        self.vista.setMinimumHeight(ALTO_FILA * (filas_min + 1) + 4)
        self.vista.clicked.connect(self._clic)

        self.vacio = QLabel("")
        self.vacio.setProperty("rol", "vacio")
        self.vacio.setAlignment(Qt.AlignCenter)
        self.vacio.setWordWrap(True)
        self.pila = QStackedLayout()
        self.pila.addWidget(self.vista)
        self.pila.addWidget(self.vacio)
        lay.addLayout(self.pila, 1)

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
        cab = self.vista.horizontalHeader()
        for c in range(self.modelo.columnCount()):
            cab.setSectionResizeMode(c, QHeaderView.Interactive)
        self.vista.resizeColumnsToContents()
        for c in range(self.modelo.columnCount()):
            cab.resizeSection(c, min(cab.sectionSize(c) + 16, ANCHO_MAX_COLUMNA))
        # La última columna de texto ocupa el espacio sobrante; las numéricas conservan su ancho
        texto = [c for c, col in enumerate(tabla.columnas) if not col.numerica]
        if texto:
            cab.setSectionResizeMode(texto[-1], QHeaderView.Stretch)

    def limpiar(self, mensaje):
        self.modelo.limpiar()
        self.vacio.setText(mensaje)
        self.pila.setCurrentWidget(self.vacio)

    def repintar(self):
        self.modelo.repintar()

    def _clic(self, ix):
        clave = ix.data(ROL_CLAVE)
        if clave:
            self.fila_clicada.emit(clave)


def ajustar_alto(vista_tabla, filas_max=14):
    """Alto justo para mostrar todas las filas (hasta filas_max), con lugar para la barra horizontal."""
    n = min(max(vista_tabla.modelo.rowCount(), 1), filas_max)
    alto = ALTO_FILA * (n + 1) + 6 + 12
    vista_tabla.vista.setMinimumHeight(alto)
    vista_tabla.vista.setMaximumHeight(alto if vista_tabla.modelo.rowCount() <= filas_max else 16777215)
