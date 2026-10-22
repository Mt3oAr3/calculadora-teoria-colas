"""
vista_resultados.py
Página «Resultados»: todas las medidas del modelo (calculadora_service.tabla_resultados).
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from services import calculadora_service as cs

from .vista_tabla import VistaTabla, encabezado_pagina


class PaginaResultados(QWidget):
    fila_clicada = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Pagina")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(encabezado_pagina(
            "Resultados", "Filas en negrita: indicadores principales. «—» indica que la medida no está definida "
                          "para el modelo. Haz clic en una fila para ver cómo se calculó."))
        self.tabla = VistaTabla(filas_min=8)
        self.tabla.fila_clicada.connect(self.fila_clicada.emit)
        lay.addWidget(self.tabla, 1)

    def mostrar(self, esc, fmt):
        self.tabla.mostrar(cs.tabla_resultados(esc), fmt)

    def tablas_para_exportar(self, esc):
        return [cs.tabla_resultados(esc)]

    def limpiar(self, mensaje):
        self.tabla.limpiar(mensaje)

    def repintar(self):
        self.tabla.repintar()
