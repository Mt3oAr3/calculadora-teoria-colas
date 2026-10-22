"""
ventana_principal.py
Ventana principal de la versión Qt. Coordina el mismo flujo que ui/app.py:

    PanelEntradas --(texto)--> calculadora_service.leer_parametros()
                  --> calculadora_service.calcular_escenario()
                  --> PanelResumen (tarjetas) y las páginas de resultados
    clic en tarjeta o fila --> PanelFormulas («Cómo se calculó»)

Distingue tres tipos de fallo:
    ErrorEntrada  -> se marcan los campos en el formulario.
    ErrorModelo   -> limitación matemática / numérica, se explica en el resumen.
    otro          -> error inesperado: mensaje breve al usuario y traza en consola.
En cualquier fallo se retiran los resultados anteriores para no confundirlos.
"""
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QVBoxLayout, QWidget)

from domain.errores import ErrorEntrada, ErrorModelo
from services import calculadora_service as cs
from services import exportacion_service as ex
from services.tablas import Formateador

from . import tema
from .barra_lateral import PAGINAS, BarraLateral
from .panel_entradas import PanelEntradas
from .panel_formulas import PanelFormulas
from .tarjetas import PanelResumen
from .vista_comparacion import PaginaComparacion
from .vista_costos import PaginaCostos
from .vista_graficas import PaginaGraficas
from .vista_probabilidades import PaginaProbabilidades
from .vista_resultados import PaginaResultados

TITULO = "Calculadora de Teoría de Colas - Técnicas de Simulación"
CENTRO_COMODO = 500      # ancho deseado del centro al abrir el panel de fórmulas


class VentanaPrincipal(QMainWindow):

    def __init__(self, tema_inicial="claro"):
        super().__init__()
        self.setWindowTitle(TITULO)
        self.resize(1480, 900)
        self.setMinimumSize(1300, 700)
        self.esc = None                  # escenario vigente (None si no hay resultados válidos)
        self.desactualizado = False      # True si se editaron datos después de calcular
        tema.aplicar(QApplication.instance(), tema_inicial)
        self._construir()
        self._atajos()
        self.calcular()

    # ------------------------------------------------------------------
    def _construir(self):
        self.barra = BarraLateral()
        self.panel = PanelEntradas()
        self.panel.calcular.connect(self.calcular)
        self.panel.exportar.connect(self.exportar_csv)
        self.panel.datos_cambiaron.connect(self._datos_cambiaron)
        self.panel.presentacion_cambio.connect(self._presentacion_cambio)

        # Centro: tarjetas arriba y páginas debajo, todo desplazable si la ventana es baja
        centro = QWidget()
        centro.setObjectName("Contenido")
        lc = QVBoxLayout(centro)
        lc.setContentsMargins(16, 16, 16, 12)
        lc.setSpacing(14)
        self.resumen = PanelResumen()
        self.resumen.indicador_clicado.connect(self.mostrar_formula)
        lc.addWidget(self.resumen)
        self.paginas = QStackedWidget()
        self.p_resultados = PaginaResultados()
        self.p_probabilidades = PaginaProbabilidades()
        self.p_costos = PaginaCostos()
        self.p_comparacion = PaginaComparacion(unidad_tiempo=lambda: self.panel.get("ut"))
        self.p_graficas = PaginaGraficas()
        self.p_graficas.aviso.connect(self.avisar)
        for pag in (self.p_resultados, self.p_probabilidades, self.p_costos, self.p_comparacion, self.p_graficas):
            self.paginas.addWidget(pag)
        for pag in (self.p_resultados, self.p_probabilidades, self.p_costos):
            pag.fila_clicada.connect(self.mostrar_formula)
        self.paginas.setMinimumHeight(380)
        lc.addWidget(self.paginas, 1)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QScrollArea.NoFrame)
        desplazable.setWidget(centro)
        desplazable.setMinimumWidth(380)

        self.formulas = PanelFormulas()
        self.formulas.cerrado.connect(lambda: self.resumen.marcar_activa(None))
        self.formulas.hide()

        self.divisor = QSplitter(Qt.Horizontal)
        self.divisor.setChildrenCollapsible(False)
        self.divisor.setHandleWidth(4)
        for w in (self.panel, desplazable, self.formulas):
            self.divisor.addWidget(w)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.setSizes([360, 1000, 380])

        raiz = QWidget()
        lay = QHBoxLayout(raiz)             # la barra lateral tiene ancho fijo
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.barra)
        lay.addWidget(self.divisor, 1)
        self.setCentralWidget(raiz)

        self.estado = QLabel("Listo.")
        self.statusBar().addWidget(self.estado, 1)
        self.barra.pagina_elegida.connect(self._ir_a_pagina)
        self.barra.cambiar_tema.connect(self.alternar_tema)
        self.barra.elegir(0)

    def _ir_a_pagina(self, indice):
        """Solo la página visible cuenta para el tamaño mínimo (QStackedWidget usa el de todas)."""
        for i in range(self.paginas.count()):
            politica = QSizePolicy.Preferred if i == indice else QSizePolicy.Ignored
            self.paginas.widget(i).setSizePolicy(politica, politica)
        self.paginas.setCurrentIndex(indice)
        self.paginas.adjustSize()

    def _atajos(self):
        QShortcut(QKeySequence(Qt.Key_F5), self, self.calcular)
        QShortcut(QKeySequence("Ctrl+T"), self, self.alternar_tema)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.formulas.cerrar)
        for i in range(len(PAGINAS)):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, lambda i=i: self.barra.elegir(i))

    def avisar(self, texto):
        self.estado.setText(texto)

    def _formateador(self):
        H = self.esc.p.H if self.esc else 8.0
        return Formateador(int(self.panel.get("dec")), self.panel.get("ut"), H)

    # ------------------------------------------------------------------
    # Cálculo
    # ------------------------------------------------------------------
    def calcular(self):
        self.panel.limpiar_errores()
        try:
            p = cs.leer_parametros(self.panel.valores())
        except ErrorEntrada as e:
            self.panel.marcar_errores(e.errores)
            n = len(e.errores)
            detalle = e.errores[0][1] + (f"  (y {n - 1} error(es) más)" if n > 1 else "")
            self._sin_resultados(f"Revisa los datos marcados en rojo en el panel de parámetros. {detalle}")
            return
        try:
            esc = cs.calcular_escenario(p)
        except ErrorModelo as e:
            self._sin_resultados(f"Limitación del modelo: {e}")
            return
        except Exception as e:  # error del programa: no mostrar resultados dudosos
            traceback.print_exc()
            self._sin_resultados("Ocurrió un error inesperado al calcular. No se muestran resultados.")
            QMessageBox.critical(self, "Error inesperado", "Ocurrió un error inesperado al calcular.\n\n"
                                                           f"Detalle técnico: {type(e).__name__}: {e}")
            return
        self.esc = esc
        self.desactualizado = False
        self._mostrar()
        self.avisar(f"Calculado {esc.kendall}." + ("" if esc.estable else " Sistema inestable."))

    def _mostrar(self):
        """Dibuja el escenario vigente en todas las vistas con la presentación elegida."""
        fmt = self._formateador()
        try:
            self.resumen.mostrar(self.esc, fmt)
            self.p_resultados.mostrar(self.esc, fmt)
            self.p_probabilidades.mostrar(self.esc, fmt)
            self.p_costos.mostrar(self.esc, fmt)
            self.p_comparacion.mostrar(self.esc, fmt)
            self.p_graficas.mostrar(cs.contexto_graficas(self.esc, self.panel.get("ut")))
            self.formulas.actualizar(self.esc, fmt, self.desactualizado)
        except Exception as e:
            traceback.print_exc()
            self._sin_resultados("Ocurrió un error inesperado al mostrar los resultados.")
            QMessageBox.critical(self, "Error inesperado", f"Detalle técnico: {type(e).__name__}: {e}")
            return
        if self.desactualizado:
            self.resumen.marcar_desactualizado(True)
        self.panel.habilitar_exportar(not self.desactualizado)

    def _sin_resultados(self, mensaje):
        """Retira todos los resultados anteriores para que no se confundan con los actuales."""
        self.esc = None
        self.desactualizado = False
        self.resumen.limpiar(mensaje)
        for pag in (self.p_resultados, self.p_probabilidades, self.p_costos):
            pag.limpiar("Sin resultados. Corrige los datos y pulsa «Calcular».")
        self.p_comparacion.limpiar("Sin resultados.")
        self.p_graficas.limpiar("Sin resultados para graficar.")
        self.formulas.cerrar()
        self.panel.habilitar_exportar(False)
        self.avisar("Sin resultados vigentes.")

    def _datos_cambiaron(self):
        if self.esc is not None and not self.desactualizado:
            self.desactualizado = True
            self.resumen.marcar_desactualizado(True)
            self.formulas.actualizar(self.esc, self._formateador(), True)
            self.panel.habilitar_exportar(False)
            self.avisar("Parámetros modificados: pulsa «Calcular» (Enter o F5) para actualizar.")

    def _presentacion_cambio(self):
        if self.esc is not None:
            self._mostrar()

    # ------------------------------------------------------------------
    # Fórmulas y tema
    # ------------------------------------------------------------------
    def mostrar_formula(self, clave):
        if self.esc is None:
            return
        if not self.formulas.isVisible():
            self.formulas.show()
            total = sum(self.divisor.sizes())
            izq = self.divisor.sizes()[0]
            ancho = max(self.formulas.minimumWidth(), 380)
            # Si el centro queda angosto ceden espacio, hasta su mínimo, el panel de entradas
            # y luego el de fórmulas
            falta = CENTRO_COMODO - (total - izq - ancho)
            if falta > 0:
                cede = min(falta, izq - self.panel.minimumWidth())
                izq, falta = izq - cede, falta - cede
            if falta > 0:
                ancho = max(self.formulas.minimumWidth(), ancho - falta)
            self.divisor.setSizes([izq, total - izq - ancho, ancho])
        self.formulas.mostrar(self.esc, clave, self._formateador(), self.desactualizado)
        self.resumen.marcar_activa(clave)

    def alternar_tema(self):
        tema.aplicar(QApplication.instance(), "oscuro" if tema.actual() == "claro" else "claro")
        self.barra.actualizar_tema()
        self.resumen.actualizar_tema()
        for pag in (self.p_resultados, self.p_probabilidades, self.p_costos, self.p_comparacion, self.p_graficas):
            pag.repintar()
        self.formulas.repintar()

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------
    def exportar_csv(self):
        if self.esc is None or self.desactualizado:
            return
        esc = self.esc
        try:
            # Orden de la exportación original: Resultados, Probabilidades, Por día, Costos, Variando k y M
            tablas = (self.p_resultados.tablas_para_exportar(esc) + self.p_probabilidades.tablas_para_exportar(esc)
                      + self.p_costos.tablas_para_exportar(esc) + self.p_comparacion.tablas_para_exportar())
        except ErrorEntrada as e:
            QMessageBox.warning(self, "No se puede exportar", e.errores[0][1])
            return
        ruta, _f = QFileDialog.getSaveFileName(self, "Exportar tablas", "resultados_colas.csv", "CSV (*.csv)")
        if not ruta:
            return
        try:
            ex.exportar_csv(ruta, tablas, self._formateador())
        except OSError as e:
            QMessageBox.critical(self, "No se pudo guardar",
                                 f"No se pudo escribir el archivo (¿está abierto en Excel?).\n\n{e.strerror or e}")
            return
        self.avisar(f"Tablas exportadas a {ruta}")
        QMessageBox.information(self, "Exportado", f"Tablas guardadas en:\n{ruta}")
