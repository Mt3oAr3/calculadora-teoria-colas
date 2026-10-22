"""
ventana_principal.py
Ventana principal de la versión Qt. Coordina el mismo flujo que ui/app.py:

    PanelEntradas --(texto)--> calculadora_service.leer_parametros()
                  --> calculadora_service.calcular_escenario()
                  --> AreaResultados (encabezado, pestañas con tarjetas y tablas)
    clic en tarjeta o fila --> PanelFormulas («Cómo se calculó»)

Distribución: barra superior fina, banner global de datos desactualizados y, debajo,
el panel de parámetros a la izquierda y el área de resultados con pestañas a la derecha.

Distingue tres tipos de fallo:
    ErrorEntrada  -> se marcan los campos en el formulario.
    ErrorModelo   -> limitación matemática / numérica, se explica en el encabezado.
    otro          -> error inesperado: mensaje breve al usuario y traza en consola.
En cualquier fallo se retiran los resultados anteriores para no confundirlos.
"""
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox, QSplitter, QVBoxLayout,
                               QWidget)

from domain.errores import ErrorEntrada, ErrorModelo
from services import calculadora_service as cs
from services import exportacion_service as ex
from services.tablas import Formateador

from . import tema
from .area_resultados import PESTANAS, AreaResultados
from .banner_desactualizado import BannerDesactualizado
from .barra_superior import BarraSuperior
from .panel_entradas import PanelEntradas
from .panel_formulas import PanelFormulas

TITULO = "Calculadora de Teoría de Colas - Técnicas de Simulación"
TAMANO_INICIAL = (1480, 900)
TAMANO_MINIMO = (1100, 680)


class VentanaPrincipal(QMainWindow):

    def __init__(self, tema_inicial="claro"):
        super().__init__()
        self.setWindowTitle(TITULO)
        self.resize(*TAMANO_INICIAL)
        self.setMinimumSize(*TAMANO_MINIMO)
        self.esc = None                  # escenario vigente (None si no hay resultados válidos)
        self.desactualizado = False      # True si se editaron datos después de calcular
        tema.aplicar(QApplication.instance(), tema_inicial)
        self._construir()
        self._atajos()
        self.calcular()

    # ------------------------------------------------------------------
    def _construir(self):
        self.barra = BarraSuperior()
        self.barra.cambiar_tema.connect(self.alternar_tema)
        self.banner = BannerDesactualizado()
        self.banner.calcular.connect(self.calcular)

        self.panel = PanelEntradas()
        self.panel.calcular.connect(self.calcular)
        self.panel.exportar.connect(self.exportar_csv)
        self.panel.datos_cambiaron.connect(self._datos_cambiaron)
        self.panel.presentacion_cambio.connect(self._presentacion_cambio)

        self.area = AreaResultados(unidad_tiempo=lambda: self.panel.get("ut"))
        self.area.fila_clicada.connect(self.mostrar_formula)
        self.area.aviso.connect(self.avisar)
        self.area.ir_a_costos.connect(lambda: self.panel.ir_a_seccion("costos", "cS"))
        # Atajos a las páginas
        self.p_resultados, self.p_probabilidades = self.area.resultados, self.area.probabilidades
        self.p_costos, self.p_comparacion, self.p_graficas = self.area.costos, self.area.comparacion, self.area.graficas

        # Panel «Cómo se calculó»: superpuesto al área de resultados, no ocupa lugar en el layout
        self.formulas = PanelFormulas()
        self.formulas.anclar(self.area)
        self.formulas.cerrado.connect(lambda: self.p_resultados.tarjetas.marcar_activa(None))

        self.divisor = QSplitter(Qt.Horizontal)
        self.divisor.setChildrenCollapsible(False)
        self.divisor.setHandleWidth(4)
        for w in (self.panel, self.area):
            self.divisor.addWidget(w)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.setSizes([self.panel.minimumWidth(), TAMANO_INICIAL[0]])

        raiz = QWidget()
        lay = QVBoxLayout(raiz)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.barra)
        lay.addWidget(self.banner)
        lay.addWidget(self.divisor, 1)
        self.setCentralWidget(raiz)

        self.estado = QLabel("Listo.")
        self.statusBar().addWidget(self.estado, 1)

    def _atajos(self):
        QShortcut(QKeySequence(Qt.Key_F5), self, self.calcular)
        QShortcut(QKeySequence("Ctrl+T"), self, self.alternar_tema)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.formulas.cerrar)
        for i in range(len(PESTANAS)):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, lambda i=i: self.area.ir_a(i))

    def avisar(self, texto, nivel=""):
        """Mensaje en la barra de estado; nivel="ok" lo muestra como éxito (verde, con icono)."""
        self.estado.setText(f"{tema.ICONOS['ok']}  {texto}" if nivel == "ok" else texto)
        self.estado.setProperty("nivel", nivel)
        tema.refrescar(self.estado)

    def _formateador(self):
        H = self.esc.p.H if self.esc else 8.0
        return Formateador(int(self.panel.get("dec")), self.panel.get("ut"), H)

    def _marcar_desactualizado(self, si):
        """Único lugar donde cambia el estado «desactualizado» y su aviso (el banner global)."""
        self.desactualizado = si
        self.banner.mostrar(si)
        self.p_resultados.tarjetas.marcar_desactualizado(si)
        self.panel.habilitar_exportar(self.esc is not None and not si)

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
        self._marcar_desactualizado(False)
        self._mostrar()
        if esc.estable:
            self.avisar(f"Cálculo listo: {esc.kendall}.", "ok")
        else:
            self.avisar(f"Cálculo listo: {esc.kendall}. Sistema inestable.")

    def _mostrar(self):
        """Dibuja el escenario vigente en todas las vistas con la presentación elegida."""
        fmt = self._formateador()
        try:
            self.area.mostrar(self.esc, fmt, cs.contexto_graficas(self.esc, self.panel.get("ut")))
            self.formulas.actualizar(self.esc, fmt)
        except Exception as e:
            traceback.print_exc()
            self._sin_resultados("Ocurrió un error inesperado al mostrar los resultados.")
            QMessageBox.critical(self, "Error inesperado", f"Detalle técnico: {type(e).__name__}: {e}")
            return
        self._marcar_desactualizado(self.desactualizado)

    def _sin_resultados(self, mensaje):
        """Retira todos los resultados anteriores para que no se confundan con los actuales."""
        self.esc = None
        self.area.limpiar(mensaje)
        self.formulas.cerrar()
        self._marcar_desactualizado(False)
        self.avisar("Sin resultados vigentes.")

    def _datos_cambiaron(self):
        if self.esc is not None and not self.desactualizado:
            self._marcar_desactualizado(True)

    def _presentacion_cambio(self):
        if self.esc is not None:
            self._mostrar()

    # ------------------------------------------------------------------
    # Fórmulas y tema
    # ------------------------------------------------------------------
    def mostrar_formula(self, clave):
        if self.esc is None:
            return
        self.formulas.abrir(self.esc, clave, self._formateador())
        self.p_resultados.tarjetas.marcar_activa(clave)

    def alternar_tema(self):
        tema.aplicar(QApplication.instance(), "oscuro" if tema.actual() == "claro" else "claro")
        self.barra.actualizar_tema()
        self.area.repintar()
        self.formulas.repintar()

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------
    def exportar_csv(self):
        if self.esc is None or self.desactualizado:
            return
        try:
            tablas = self.area.tablas_para_exportar(self.esc)
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
