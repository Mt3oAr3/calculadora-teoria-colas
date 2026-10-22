"""
vista_costos.py
Página «Costos y por día»: costos e ingresos diarios y semanales, y la
operación diaria (horas en cada estado, clientes por día, totales de S sistemas).

Presentación de los costos:
  * todos los costos e ingresos en 0 -> estado vacío dentro de la tarjeta, con un botón
    que lleva a la sección «Costos e ingresos» del formulario;
  * algunos en 0 -> la tabla, con los montos en 0 atenuados y «—» en Rentabilidad si no aplica.
Solo cambia lo que se ve: la exportación CSV usa la tabla original del servicio.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from services import calculadora_service as cs
from services.tablas import Valor

from .estado_vacio import EstadoVacio
from .vista_tabla import VistaTabla, encabezado_pagina

CAMPOS_COSTO = ("c_servidor", "c_espera", "c_ocio", "ingreso")
VACIO = ("$", "Aún no hay costos ingresados",
         "Completa «Costos e ingresos» en el panel de parámetros y pulsa Calcular.", "Ir a Costos e ingresos")
FILA_RENTABILIDAD = "rentabilidad"


def sin_costos(esc):
    """True si todos los costos e ingresos del escenario son 0 (cS, cW, cI e ingreso)."""
    return all(esc.p.cfg[c] == 0 for c in CAMPOS_COSTO)


def _tabla_costos_vista(esc):
    """Tabla de costos para mostrar: Rentabilidad «—» si no hay ingresos o costos (no aplica)."""
    tabla = cs.tabla_costos(esc)
    if esc.p.cfg["ingreso"] == 0 or esc.costos["ct"] == 0:
        for fila in tabla.filas:
            if fila.clave == FILA_RENTABILIDAD:
                fila.celdas[1] = Valor(float("nan"))       # el Formateador lo muestra como «—»
    return tabla


class PaginaCostos(QWidget):
    fila_clicada = Signal(str)
    ir_a_costos = Signal()            # abrir la sección «Costos e ingresos» del formulario

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
        # Las dos tablas apiladas en el único scroll de la pestaña
        self.tabla_cost = VistaTabla("Costos e ingresos", filas_min=4)
        self.tabla_cost.modelo.atenuar_ceros = True
        self.vacio = EstadoVacio(*VACIO)
        self.vacio.accion.connect(self.ir_a_costos.emit)
        self.tabla_cost.usar_estado_vacio(self.vacio)
        self.tabla_dia = VistaTabla("Operación diaria", filas_min=4)
        for t in (self.tabla_cost, self.tabla_dia):
            t.fila_clicada.connect(self.fila_clicada.emit)
            lay.addWidget(t)
        lay.addStretch(1)

    @property
    def mostrando_vacio(self):
        return self.tabla_cost.pila.currentWidget() is self.vacio

    def mostrar(self, esc, fmt):
        if esc.costos is not None and sin_costos(esc):
            self.tabla_cost.mostrar_estado_vacio()
        else:
            self.tabla_cost.mostrar(_tabla_costos_vista(esc) if esc.costos else cs.tabla_costos(esc), fmt)
        self.tabla_dia.mostrar(cs.tabla_por_dia(esc), fmt)

    def tablas_para_exportar(self, esc):
        """Mismo orden que la exportación original: Por día, Costos (tablas del servicio, sin cambios)."""
        return [cs.tabla_por_dia(esc), cs.tabla_costos(esc)]

    def limpiar(self, mensaje):
        self.tabla_cost.limpiar(mensaje)
        self.tabla_dia.limpiar(mensaje)

    def repintar(self):
        self.tabla_cost.repintar()
        self.tabla_dia.repintar()
