"""
vista_costos.py
Página «Costos y por día»: costos e ingresos diarios y semanales, y la
operación diaria (horas en cada estado, clientes por día, totales de S sistemas).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QSplitter, QVBoxLayout, QWidget

from services import calculadora_service as cs

from .vista_tabla import VistaTabla, ajustar_alto, encabezado_pagina

NOTA_SIN_COSTOS = ("No has ingresado costos. Completa «Costos e ingresos» en el panel de parámetros "
                   "y pulsa Calcular.")
CAMPOS_COSTO = ("c_servidor", "c_espera", "c_ocio", "ingreso")


def sin_costos(esc):
    """True si todos los costos e ingresos del escenario son 0 (cS, cW, cI e ingreso)."""
    return all(esc.p.cfg[c] == 0 for c in CAMPOS_COSTO)


class PaginaCostos(QWidget):
    fila_clicada = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Pagina")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(encabezado_pagina(
            "Costos y por día",
            "Montos por día de operación (H horas). Tiempo en un estado = probabilidad × horas. "
            "Clientes que esperan = λ efectiva × horas × probabilidad de esperar."))
        self.nota = QLabel(NOTA_SIN_COSTOS)
        self.nota.setProperty("rol", "nota_vacia")
        self.nota.setWordWrap(True)
        self.nota.hide()
        lay.addWidget(self.nota)
        div = QSplitter(Qt.Vertical)
        div.setChildrenCollapsible(False)
        self.tabla_cost = VistaTabla("Costos e ingresos", filas_min=4)
        self.tabla_dia = VistaTabla("Operación diaria", filas_min=4)
        for t in (self.tabla_cost, self.tabla_dia):
            t.fila_clicada.connect(self.fila_clicada.emit)
            div.addWidget(t)
        div.setStretchFactor(1, 1)
        lay.addWidget(div, 1)

    def mostrar(self, esc, fmt):
        self.nota.setVisible(sin_costos(esc))
        self.tabla_cost.mostrar(cs.tabla_costos(esc), fmt)
        ajustar_alto(self.tabla_cost)
        self.tabla_dia.mostrar(cs.tabla_por_dia(esc), fmt)

    def tablas_para_exportar(self, esc):
        """Mismo orden que la exportación original: Por día, Costos."""
        return [cs.tabla_por_dia(esc), cs.tabla_costos(esc)]

    def limpiar(self, mensaje):
        self.nota.hide()
        self.tabla_cost.limpiar(mensaje)
        self.tabla_dia.limpiar(mensaje)

    def repintar(self):
        self.tabla_cost.repintar()
        self.tabla_dia.repintar()
