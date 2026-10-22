"""
vista_probabilidades.py
Página «Probabilidades»: P(n = a), rangos [a, b], probabilidades de la cola y
la distribución completa (ordenable).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from domain.errores import ErrorEntrada
from services import calculadora_service as cs

from . import tema
from .vista_tabla import VistaTabla, encabezado_pagina


class PaginaProbabilidades(QWidget):
    fila_clicada = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Pagina")
        self.esc = self.fmt = None
        self.rango = (int(cs.VALORES_INICIALES["pa"]), int(cs.VALORES_INICIALES["pb"]))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(encabezado_pagina("Probabilidades",
                                        "n = clientes en el sistema; cola = n − k. Clic en una fila para ver "
                                        "la fórmula con los valores actuales."))

        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.ent_a = QLineEdit(cs.VALORES_INICIALES["pa"])
        self.ent_b = QLineEdit(cs.VALORES_INICIALES["pb"])
        for texto, ent, ayuda in (("Clientes  a =", self.ent_a, "Número de clientes a (entero ≥ 0)."),
                                  ("hasta  b =", self.ent_b, "Fin del rango [a, b] (entero ≥ a).")):
            lbl = QLabel(texto)
            lbl.setProperty("rol", "campo")
            fila.addWidget(lbl)
            ent.setFixedWidth(64)
            ent.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            ent.setToolTip(ayuda)
            ent.returnPressed.connect(self.actualizar_probabilidades)
            fila.addWidget(ent)
        btn = QPushButton("Calcular")
        btn.setToolTip("Calcular las probabilidades para a y b (Enter)")
        btn.clicked.connect(self.actualizar_probabilidades)
        fila.addWidget(btn)
        fila.addStretch(1)
        lay.addLayout(fila)
        self.lbl_err = QLabel("")
        self.lbl_err.setProperty("rol", "error")
        self.lbl_err.setWordWrap(True)
        self.lbl_err.hide()
        lay.addWidget(self.lbl_err)

        self.tabla_prob = VistaTabla("Para a y b", filas_min=4)
        self.tabla_dist = VistaTabla("Distribución completa  (fila en negrita: n = k; clic en el encabezado "
                                     "para ordenar)", ordenable=True, filas_min=4)
        for t in (self.tabla_prob, self.tabla_dist):
            t.fila_clicada.connect(self.fila_clicada.emit)
            lay.addWidget(t)
        lay.addStretch(1)

    def mostrar(self, esc, fmt):
        self.esc, self.fmt = esc, fmt
        self.tabla_dist.mostrar(cs.tabla_distribucion(esc), fmt)
        self.actualizar_probabilidades()

    def _marcar(self, ent, error):
        ent.setProperty("error", error)
        tema.refrescar(ent)

    def actualizar_probabilidades(self):
        if self.esc is None:
            return
        self._marcar(self.ent_a, False)
        self._marcar(self.ent_b, False)
        try:
            self.rango = cs.leer_rango(self.ent_a.text(), self.ent_b.text())
        except ErrorEntrada as e:
            for campo, _ in e.errores:
                self._marcar(self.ent_a if campo == "pa" else self.ent_b, True)
            self.lbl_err.setText(e.errores[0][1])
            self.lbl_err.show()
            self.tabla_prob.limpiar("Corrige el rango a – b para ver estas probabilidades.")
            return
        self.lbl_err.hide()
        self.tabla_prob.mostrar(cs.tabla_probabilidades(self.esc, *self.rango), self.fmt)

    def tablas_para_exportar(self, esc):
        return [cs.tabla_probabilidades(esc, *self.rango)]

    def limpiar(self, mensaje):
        self.esc = None
        self.tabla_prob.limpiar(mensaje)
        self.tabla_dist.limpiar(mensaje)

    def repintar(self):
        self.tabla_prob.repintar()
        self.tabla_dist.repintar()
