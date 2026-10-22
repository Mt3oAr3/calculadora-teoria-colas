"""
area_resultados.py
Parte derecha de la ventana: encabezado del modelo y las pestañas de resultados
(Resultados, Probabilidades, Costos y por día, Comparar k y M, Gráficas).
Cada pestaña tiene una sola barra de desplazamiento vertical: la de su página.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from . import tema
from .encabezado_modelo import EncabezadoModelo
from .vista_comparacion import PaginaComparacion
from .vista_costos import PaginaCostos
from .vista_graficas import PaginaGraficas
from .vista_probabilidades import PaginaProbabilidades
from .vista_resultados import PaginaResultados

PESTANAS = ["Resultados", "Probabilidades", "Costos y por día", "Comparar k y M", "Gráficas"]


def _desplazable(pagina):
    """Envuelve una página en el único scroll vertical de su pestaña."""
    scroll = QScrollArea()
    scroll.setObjectName("PaginaScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    contenedor = QWidget()
    lay = QVBoxLayout(contenedor)
    lay.setContentsMargins(*tema.LAYOUT["pagina_margen"])
    lay.addWidget(pagina)
    scroll.setWidget(contenedor)
    return scroll


class AreaResultados(QWidget):
    fila_clicada = Signal(str)        # tarjeta o fila con fórmula
    aviso = Signal(str)               # mensajes para la barra de estado
    ir_a_costos = Signal()            # botón del estado vacío de costos
    redimensionada = Signal()         # el panel superpuesto se reacomoda

    def __init__(self, unidad_tiempo, padre=None):
        super().__init__(padre)
        self.setObjectName("AreaResultados")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*tema.LAYOUT["area_margen"])
        lay.setSpacing(10)
        self.encabezado = EncabezadoModelo()
        lay.addWidget(self.encabezado)

        self.resultados = PaginaResultados()
        self.probabilidades = PaginaProbabilidades()
        self.costos = PaginaCostos()
        self.costos.ir_a_costos.connect(self.ir_a_costos.emit)
        self.comparacion = PaginaComparacion(unidad_tiempo=unidad_tiempo)
        self.graficas = PaginaGraficas()
        self.graficas.aviso.connect(self.aviso.emit)
        self.paginas = [self.resultados, self.probabilidades, self.costos, self.comparacion, self.graficas]
        for pag in (self.resultados, self.probabilidades, self.costos):
            pag.fila_clicada.connect(self.fila_clicada.emit)

        self.pestanas = QTabWidget()
        self.pestanas.setDocumentMode(True)
        self.pestanas.tabBar().setExpanding(False)
        self.pestanas.tabBar().setDrawBase(False)
        for nombre, pag in zip(PESTANAS, self.paginas):
            self.pestanas.addTab(_desplazable(pag), nombre)
        for i, nombre in enumerate(PESTANAS):
            self.pestanas.setTabToolTip(i, f"{nombre}  (Ctrl+{i + 1})")
        lay.addWidget(self.pestanas, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.redimensionada.emit()

    def ir_a(self, indice):
        self.pestanas.setCurrentIndex(indice)

    def mostrar(self, esc, fmt, ctx_graficas):
        self.encabezado.mostrar(esc, fmt)
        for pag in (self.resultados, self.probabilidades, self.costos, self.comparacion):
            pag.mostrar(esc, fmt)
        self.graficas.mostrar(ctx_graficas)

    def limpiar(self, mensaje):
        self.encabezado.limpiar(mensaje)
        for pag in (self.resultados, self.probabilidades, self.costos):
            pag.limpiar("Sin resultados. Corrige los datos y pulsa «Calcular».")
        self.comparacion.limpiar("Sin resultados.")
        self.graficas.limpiar("Sin resultados para graficar.")

    def tablas_para_exportar(self, esc):
        """Orden de la exportación original: Resultados, Probabilidades, Por día, Costos, Variando k y M."""
        return (self.resultados.tablas_para_exportar(esc) + self.probabilidades.tablas_para_exportar(esc)
                + self.costos.tablas_para_exportar(esc) + self.comparacion.tablas_para_exportar())

    def repintar(self):
        for pag in self.paginas:
            pag.repintar()
