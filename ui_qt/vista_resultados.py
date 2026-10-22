"""
vista_resultados.py
Pestaña «Resultados»: tarjetas de los indicadores principales y todas las medidas
del modelo (calculadora_service.tabla_resultados). Las tarjetas solo viven aquí.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from services import calculadora_service as cs

from .tarjetas import FilaTarjetas
from .vista_tabla import VistaTabla, encabezado_pagina


class PaginaResultados(QWidget):
    fila_clicada = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Pagina")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.tarjetas = FilaTarjetas()
        self.tarjetas.indicador_clicado.connect(self.fila_clicada.emit)
        lay.addWidget(self.tarjetas)
        lay.addWidget(encabezado_pagina(
            "Todas las medidas", "Filas en negrita: indicadores principales. «—» indica que la medida no está "
                                 "definida para el modelo. Haz clic en una tarjeta o fila para ver cómo se calculó."))
        self.tabla = VistaTabla(filas_min=8)
        self.tabla.fila_clicada.connect(self.fila_clicada.emit)
        lay.addWidget(self.tabla)
        lay.addStretch(1)

    def mostrar(self, esc, fmt):
        self.tarjetas.mostrar(esc, fmt)
        self.tabla.mostrar(cs.tabla_resultados(esc), fmt)

    def tablas_para_exportar(self, esc):
        return [cs.tabla_resultados(esc)]

    def limpiar(self, mensaje):
        self.tarjetas.limpiar()
        self.tabla.limpiar(mensaje)

    def repintar(self):
        self.tarjetas.actualizar_tema()
        self.tabla.repintar()
