"""
modelo_tabla.py
Adaptador Qt de services.tablas.Tabla: el texto sale del mismo Formateador que
usa la exportación CSV, y los colores de las filas (cumple, menor costo) salen del tema.

Regla única de alineación (bandera numérica de Columna): columnas numéricas con encabezado
y celdas a la derecha; columnas de texto con encabezado y celdas a la izquierda.
"""
import math

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QFont

from services.tablas import Valor

from . import tema

ROL_ORDEN = Qt.UserRole          # valor crudo para ordenar
ROL_CLAVE = Qt.UserRole + 1      # clave de la fórmula de la fila (o None)

# Qt pide los roles como enteros: compararlos con los enum de Qt cuesta caro en cada celda pintada
_TEXTO, _ALINEACION, _FUENTE = int(Qt.DisplayRole), int(Qt.TextAlignmentRole), int(Qt.FontRole)
_COLOR, _FONDO, _AYUDA = int(Qt.ForegroundRole), int(Qt.BackgroundRole), int(Qt.ToolTipRole)
_ORDEN, _CLAVE = int(ROL_ORDEN), int(ROL_CLAVE)

# Prioridad de los fondos: el de «menor costo» gana al de «cumple». Las filas «principales» solo van
# en negrita: así se sigue viendo el sombreado alterno.
FONDOS = (("mejor", "fila_mejor"), ("ok", "fila_cumple"))


class ModeloTabla(QAbstractTableModel):
    """
    data() se llama por cada celda en cada repintado (también en cada cuadro de una animación):
    alineación, negrita y colores se precalculan por fila y columna al mostrar y al cambiar de tema.
    """

    def __init__(self, padre=None):
        super().__init__(padre)
        self.tabla = None
        self._textos = []
        self._negrita = QFont()
        self._negrita.setBold(True)
        self.atenuar_ceros = False     # montos en 0 en gris atenuado (tabla de costos)
        self._precalcular()

    def _precalcular(self):
        t = self.tabla
        filas = t.filas if t is not None else []
        columnas = t.columnas if t is not None else []
        self._alineaciones = [int(self._alineacion(c)) for c in range(len(columnas))]
        self._negrita_col = [col.destacada for col in columnas]
        self._negrita_fila = [("principal" in f.etiquetas or "actual" in f.etiquetas) for f in filas]
        verde, gris = tema.qcolor("secundario_texto"), tema.qcolor("texto_3")
        self._color_fila = [verde if "mejor" in f.etiquetas else None for f in filas]   # óptimo en verde
        self._ceros = {(r, c) for r, f in enumerate(filas) for c, celda in enumerate(f.celdas)
                       if self.atenuar_ceros and self._es_cero(celda)}
        self._gris = gris
        fondos = {etiqueta: tema.qcolor(color) for etiqueta, color in FONDOS}
        self._fondo_fila = [next((fondos[e] for e, _c in FONDOS if e in f.etiquetas), None) for f in filas]

    def mostrar(self, tabla, fmt):
        self.beginResetModel()
        self.tabla = tabla
        self._textos = tabla.textos(fmt)
        self._precalcular()
        self.endResetModel()

    def limpiar(self):
        self.beginResetModel()
        self.tabla = None
        self._textos = []
        self._precalcular()
        self.endResetModel()

    def repintar(self):
        """Tras cambiar de tema: los colores se piden de nuevo a tema.qcolor()."""
        self._precalcular()
        if self._textos:
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    # ------------------------------------------------------------------
    def rowCount(self, padre=QModelIndex()):
        return 0 if padre.isValid() else len(self._textos)

    def columnCount(self, padre=QModelIndex()):
        return 0 if (padre.isValid() or self.tabla is None) else len(self.tabla.columnas)

    def _alineacion(self, col):
        num = self.tabla.columnas[col].numerica
        return (Qt.AlignRight if num else Qt.AlignLeft) | Qt.AlignVCenter

    def data(self, ix, rol=_TEXTO):
        r = ix.row()
        if r < 0:
            return None
        rol = int(rol)
        if rol == _TEXTO:
            return self._textos[r][ix.column()]
        if rol == _ALINEACION:
            return self._alineaciones[ix.column()]
        if rol == _FUENTE:
            return self._negrita if (self._negrita_fila[r] or self._negrita_col[ix.column()]) else None
        if rol == _COLOR:
            return self._color_fila[r] or (self._gris if (r, ix.column()) in self._ceros else None)
        if rol == _FONDO:
            return self._fondo_fila[r]
        if rol == _AYUDA:
            txt = self._textos[r][ix.column()]
            # Texto completo como respaldo, más la pista si la fila tiene fórmula
            pista = "\nClic para ver cómo se calculó." if self.tabla.filas[r].clave else ""
            return (txt + pista) if (txt or pista) else None
        if rol == _ORDEN:
            return self._orden(self.tabla.filas[r].celdas[ix.column()], ix.column())
        if rol == _CLAVE:
            return self.tabla.filas[r].clave
        return None

    @staticmethod
    def _es_cero(celda):
        return isinstance(celda, Valor) and celda.tipo == "dinero" and celda.dato == 0

    def _orden(self, celda, col):
        dato = celda.dato if isinstance(celda, Valor) else celda
        if self.tabla.columnas[col].numerica:
            ok = isinstance(dato, (int, float)) and not isinstance(dato, bool) and math.isfinite(dato)
            return float(dato) if ok else float("-inf")
        return str(dato or "").lower()

    def headerData(self, seccion, orientacion, rol=_TEXTO):
        if self.tabla is None or orientacion != Qt.Horizontal:
            return None
        rol = int(rol)
        if rol == _TEXTO:
            return self.tabla.columnas[seccion].titulo
        if rol == _ALINEACION:
            return self._alineaciones[seccion]
        return None


class ProxyOrdenable(QSortFilterProxyModel):
    """Ordena por el valor crudo (ROL_ORDEN), no por el texto formateado."""

    def __init__(self, fuente, padre=None):
        super().__init__(padre)
        self.setSourceModel(fuente)
        self.setSortRole(ROL_ORDEN)

    def headerData(self, seccion, orientacion, rol=_TEXTO):
        """El orden se indica con ↑/↓ DELANTE del título: el borde derecho de las cifras no se mueve."""
        texto = super().headerData(seccion, orientacion, rol)
        if int(rol) == _TEXTO and seccion == self.sortColumn() and texto and orientacion == Qt.Horizontal:
            return ("↑ " if self.sortOrder() == Qt.AscendingOrder else "↓ ") + texto
        return texto
