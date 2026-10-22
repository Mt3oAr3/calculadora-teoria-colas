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

# Prioridad de los fondos: el de «menor costo» gana al de «cumple». Las filas «principales» solo van
# en negrita: así se sigue viendo el sombreado alterno.
FONDOS = (("mejor", "fila_mejor"), ("ok", "fila_cumple"))


class ModeloTabla(QAbstractTableModel):

    def __init__(self, padre=None):
        super().__init__(padre)
        self.tabla = None
        self._textos = []
        self._negrita = QFont()
        self._negrita.setBold(True)
        self.atenuar_ceros = False     # montos en 0 en gris atenuado (tabla de costos)

    def mostrar(self, tabla, fmt):
        self.beginResetModel()
        self.tabla = tabla
        self._textos = tabla.textos(fmt)
        self.endResetModel()

    def limpiar(self):
        self.beginResetModel()
        self.tabla = None
        self._textos = []
        self.endResetModel()

    def repintar(self):
        """Tras cambiar de tema: los colores se piden de nuevo a tema.qcolor()."""
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

    def data(self, ix, rol=Qt.DisplayRole):
        if not ix.isValid():
            return None
        fila = self.tabla.filas[ix.row()]
        if rol == Qt.DisplayRole:
            return self._textos[ix.row()][ix.column()]
        if rol == Qt.TextAlignmentRole:
            return int(self._alineacion(ix.column()))
        if rol == Qt.FontRole and ("principal" in fila.etiquetas or "actual" in fila.etiquetas):
            return self._negrita
        if rol == Qt.ForegroundRole:
            if "mejor" in fila.etiquetas:
                return tema.qcolor("secundario_texto")           # óptimo / menor costo en verde
            if self.atenuar_ceros and self._es_cero(fila.celdas[ix.column()]):
                return tema.qcolor("texto_3")
            return None
        if rol == Qt.BackgroundRole:
            for etiqueta, color in FONDOS:
                if etiqueta in fila.etiquetas:
                    return tema.qcolor(color)
            return None
        if rol == Qt.ToolTipRole:
            txt = self._textos[ix.row()][ix.column()]
            # Texto completo como respaldo, más la pista si la fila tiene fórmula
            pista = "\nClic para ver cómo se calculó." if fila.clave else ""
            return (txt + pista) if (txt or pista) else None
        if rol == ROL_ORDEN:
            return self._orden(fila.celdas[ix.column()], ix.column())
        if rol == ROL_CLAVE:
            return fila.clave
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

    def headerData(self, seccion, orientacion, rol=Qt.DisplayRole):
        if orientacion != Qt.Horizontal or self.tabla is None:
            return None
        if rol == Qt.DisplayRole:
            return self.tabla.columnas[seccion].titulo
        if rol == Qt.TextAlignmentRole:
            return int(self._alineacion(seccion))
        return None


class ProxyOrdenable(QSortFilterProxyModel):
    """Ordena por el valor crudo (ROL_ORDEN), no por el texto formateado."""

    def __init__(self, fuente, padre=None):
        super().__init__(padre)
        self.setSourceModel(fuente)
        self.setSortRole(ROL_ORDEN)

    def headerData(self, seccion, orientacion, rol=Qt.DisplayRole):
        """El orden se indica con ↑/↓ DELANTE del título: el borde derecho de las cifras no se mueve."""
        texto = super().headerData(seccion, orientacion, rol)
        if rol == Qt.DisplayRole and orientacion == Qt.Horizontal and seccion == self.sortColumn() and texto:
            return ("↑ " if self.sortOrder() == Qt.AscendingOrder else "↓ ") + texto
        return texto
