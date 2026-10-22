"""
vista_comparacion.py
Página «Comparar k y M»: condición de búsqueda, leyenda de colores y las
tablas en función de k y de M (calculadas en comparacion_service).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter, QVBoxLayout,
                               QWidget)

from domain.errores import ErrorEntrada
from services import comparacion_service as cmp

from . import tema
from .vista_tabla import VistaTabla, encabezado_pagina


def _muestra(tipo, texto):
    caja = QWidget()
    lay = QHBoxLayout(caja)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    m = QLabel()
    m.setProperty("rol", "muestra")
    m.setProperty("tipo", tipo)
    m.setFixedSize(16, 12)
    lay.addWidget(m)
    t = QLabel(texto)
    t.setProperty("rol", "leyenda")
    lay.addWidget(t)
    return caja


class PaginaComparacion(QWidget):

    def __init__(self, unidad_tiempo, padre=None):
        super().__init__(padre)
        self.setObjectName("Pagina")
        self.esc = self.fmt = None
        self._unidad_tiempo = unidad_tiempo      # función que devuelve la unidad elegida
        self.res_k = self.res_M = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(encabezado_pagina("Comparar k y M",
                                        "Busca el menor k (o el mayor M) que cumple una condición y el k de menor "
                                        "costo total. Clic en el encabezado de una columna para ordenar."))

        lbl = QLabel("Condición de búsqueda")
        lbl.setProperty("rol", "subgrupo")
        lay.addWidget(lbl)
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.cb_metrica = QComboBox()
        self.cb_metrica.addItems([m.nombre for m in cmp.METRICAS])
        self.cb_metrica.setCurrentText(cmp.METRICA_INICIAL)
        self.cb_metrica.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cb_metrica.setMinimumContentsLength(14)
        self.cb_metrica.view().setMinimumWidth(self.cb_metrica.view().sizeHintForColumn(0) + 24)
        self.cb_op = QComboBox()
        self.cb_op.addItems(cmp.OPERADORES)
        self.cb_op.setCurrentText("≤")
        self.ent_lim = QLineEdit("0,5")
        self.ent_lim.setFixedWidth(70)
        self.ent_lim.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_unidad = QLabel("")
        self.lbl_unidad.setProperty("rol", "unidad")
        self.lbl_unidad.setMinimumWidth(30)
        btn = QPushButton("Buscar")
        for w in (self.cb_metrica, self.cb_op, self.ent_lim, self.lbl_unidad, btn):
            fila.addWidget(w)
        fila.setStretch(0, 1)
        lay.addLayout(fila)
        self.lbl_err = QLabel("")
        self.lbl_err.setProperty("rol", "error")
        self.lbl_err.setWordWrap(True)
        self.lbl_err.hide()
        lay.addWidget(self.lbl_err)
        btn.clicked.connect(self.actualizar)
        self.ent_lim.returnPressed.connect(self.actualizar)
        self.cb_metrica.currentTextChanged.connect(lambda _t: self.actualizar())
        self.cb_op.currentTextChanged.connect(lambda _t: self.actualizar())

        leyenda = QHBoxLayout()
        leyenda.setSpacing(16)
        leyenda.addWidget(_muestra("cumple", "Cumple la condición"))
        leyenda.addWidget(_muestra("mejor", "Menor costo total"))
        nota = QLabel("Negrita: valor actual. Los tiempos usan la unidad de «Mostrar tiempos en».")
        nota.setProperty("rol", "leyenda")
        nota.setWordWrap(True)
        leyenda.addWidget(nota, 1)
        lay.addLayout(leyenda)

        div = QSplitter(Qt.Vertical)
        div.setChildrenCollapsible(False)
        self.tabla_k = VistaTabla("En función de k", ordenable=True, filas_min=3)
        self.tabla_M = VistaTabla("En función de M", ordenable=True, filas_min=3)
        div.addWidget(self.tabla_k)
        div.addWidget(self.tabla_M)
        lay.addWidget(div, 1)

    def mostrar(self, esc, fmt):
        self.esc, self.fmt = esc, fmt
        self.actualizar()

    def _marcar(self, error):
        self.ent_lim.setProperty("error", error)
        tema.refrescar(self.ent_lim)

    def actualizar(self):
        if self.esc is None:
            return
        try:
            cond = cmp.leer_condicion(self.cb_metrica.currentText(), self.cb_op.currentText(),
                                      self.ent_lim.text(), self._unidad_tiempo())
        except ErrorEntrada as e:
            self._marcar(True)
            self.lbl_err.setText(e.errores[0][1])
            self.lbl_err.show()
            self.res_k = self.res_M = None
            self.tabla_k.poner_titulo("En función de k")
            self.tabla_M.poner_titulo("En función de M")
            self.tabla_k.limpiar("Corrige la condición para ver la comparación.")
            self.tabla_M.limpiar("")
            return
        self._marcar(False)
        self.lbl_err.hide()
        self.lbl_unidad.setText(self.fmt.abrev_tiempo if cond.metrica.es_tiempo else "")
        self.res_k = cmp.comparar_k(self.esc, cond, self.fmt)
        self.res_M = cmp.comparar_M(self.esc, cond, self.fmt)
        self.tabla_k.poner_titulo("En función de k:  " + self.res_k.resumen)
        self.tabla_k.mostrar(self.res_k.tabla, self.fmt)
        self.tabla_M.poner_titulo("En función de M:  " + self.res_M.resumen)
        self.tabla_M.mostrar(self.res_M.tabla, self.fmt)

    def tablas_para_exportar(self):
        """Tablas «Variando k» y «Variando M». Lanza ErrorEntrada si la condición no es válida."""
        if self.res_k is None:
            raise ErrorEntrada([("cond_v", "La condición de comparación no es válida; corrígela antes de exportar.")])
        return [self.res_k.tabla, self.res_M.tabla]

    def limpiar(self, mensaje):
        self.esc = None
        self.res_k = self.res_M = None
        self.tabla_k.limpiar(mensaje)
        self.tabla_M.limpiar("")

    def repintar(self):
        self.tabla_k.repintar()
        self.tabla_M.repintar()
