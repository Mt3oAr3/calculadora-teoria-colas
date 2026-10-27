"""
ventana_principal.py
Ventana principal de la versión Qt. Coordina el mismo flujo que ui/app.py:

    PanelEntradas --(texto)--> calculadora_service.leer_parametros()
                  --> calculadora_service.calcular_escenario()
                  --> AreaResultados (encabezado, pestañas con tarjetas y tablas)
    clic en tarjeta o fila --> PanelFormulas («Cómo se calculó»)
    clic en fila de «Comparar k y M» --> PanelFormulas con el escenario de esa fila

Distribución: barra superior fina, banner global de datos desactualizados y, debajo,
[panel de parámetros | área de resultados | «Cómo se calculó»]. Los dos paneles laterales
cambian de verdad el ancho del área, animados por un único AnimadorPaneles (ui_qt/animacion.py):
mientras se mueven, lo caro (medir tablas, redibujar la gráfica, renderizar ecuaciones) se
difiere y se hace una sola vez al terminar.
El panel de parámetros se oculta / muestra con el botón de la barra o Ctrl+B; vuelve solo si
hay campos con error o se pide ir a una sección, y se oculta solo si al abrir «Cómo se
calculó» el área quedaría demasiado angosta (vuelve al cerrarla). Su estado (visible y ancho)
se recuerda entre sesiones con QSettings.

Distingue tres tipos de fallo:
    ErrorEntrada  -> se marcan los campos en el formulario.
    ErrorModelo   -> limitación matemática / numérica, se explica en el encabezado.
    otro          -> error inesperado: mensaje breve al usuario y traza en consola.
En cualquier fallo se retiran los resultados anteriores para no confundirlos.
"""
import traceback

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QSplitter,
                               QVBoxLayout, QWidget)

from domain.errores import ErrorEntrada, ErrorModelo
from services import calculadora_service as cs
from services import exportacion_service as ex
from services.tablas import Formateador

from . import animacion, tema
from .area_resultados import PESTANAS, AreaResultados
from .banner_desactualizado import BannerDesactualizado
from .barra_superior import BarraSuperior
from .barra_titulo import aplicar_barra_titulo
from .panel_entradas import PanelEntradas
from .animacion import AnimadorPaneles
from .panel_formulas import PanelFormulas

TITULO = "Calculadora de Teoría de Colas - Técnicas de Simulación"
TAMANO_INICIAL = (1480, 900)
TAMANO_MINIMO = (1100, 680)
AJUSTES = ("TecnicasDeSimulacion", "CalculadoraColas")      # organización y aplicación de QSettings


def ajustes():
    """Preferencias de la interfaz (archivo .ini del usuario; las pruebas lo redirigen a una carpeta temporal)."""
    return QSettings(QSettings.IniFormat, QSettings.UserScope, *AJUSTES)


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
        # La barra de título nativa sigue al tema desde antes de mostrarse (sin destello claro)
        aplicar_barra_titulo(self, tema.actual() == "oscuro")

    # ------------------------------------------------------------------
    def _construir(self):
        self.barra = BarraSuperior()
        self.barra.cambiar_tema.connect(self.alternar_tema)
        self.barra.alternar_parametros.connect(self.alternar_parametros)
        self.banner = BannerDesactualizado()
        self.banner.calcular.connect(self.calcular)

        self.panel = PanelEntradas()
        self.panel.calcular.connect(self.calcular)
        self.panel.exportar.connect(self.exportar_csv)
        self.panel.datos_cambiaron.connect(self._datos_cambiaron)
        self.panel.presentacion_cambio.connect(self._presentacion_cambio)

        self.area = AreaResultados(unidad_tiempo=lambda: self.panel.get("ut"))
        self.area.fila_clicada.connect(self.mostrar_formula)
        self.area.formula_fila.connect(self.mostrar_formula_fila)
        self.area.aviso.connect(self.avisar)
        self.area.ir_a_costos.connect(self._ir_a_costos)
        # Atajos a las páginas
        self.p_resultados, self.p_probabilidades = self.area.resultados, self.area.probabilidades
        self.p_costos, self.p_comparacion, self.p_graficas = self.area.costos, self.area.comparacion, self.area.graficas

        # Panel «Cómo se calculó»: acoplado a la derecha del área (centro = [área | fórmula])
        self.formulas = PanelFormulas()
        self.formulas.abriendo.connect(self._desplegar_formulas)
        self.formulas.cerrado.connect(self._formula_cerrada)
        self.area.fila_perdida.connect(self.formulas.cerrar)
        self.centro = QWidget()
        lc = QHBoxLayout(self.centro)
        lc.setContentsMargins(0, 0, 0, 0)
        lc.setSpacing(0)
        lc.addWidget(self.area, 1)
        lc.addWidget(self.formulas)

        self.divisor = QSplitter(Qt.Horizontal)
        self.divisor.setChildrenCollapsible(False)
        self.divisor.setHandleWidth(4)
        for w in (self.panel, self.centro):
            self.divisor.addWidget(w)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.splitterMoved.connect(self._recordar_ancho_panel)
        self._ancho_min_panel = self.panel.minimumWidth()
        self._al_mostrarse = None       # acción pendiente hasta que el panel termine de aparecer
        self._parametros_auto = False   # parámetros ocultos solo para dejar lugar a la fórmula
        self._scroll_guardado = None
        # Un único controlador anima los dos paneles (no se pisan si se mueven a la vez)
        self.animador = AnimadorPaneles(tema.LAYOUT["panel_ms"], self)
        self.animador.agregar("parametros", self._aplicar_ancho_parametros)
        self.animador.agregar("formulas", self._aplicar_ancho_formulas)
        self.animador.terminado.connect(self._fin_animacion)
        animacion.indicador.cambio.connect(self._animacion_cambio)
        self.area.pestanas.currentChanged.connect(self._pestana_cambio)
        self._restaurar_panel()

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
        QShortcut(QKeySequence("Ctrl+B"), self, self.alternar_parametros)
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
            errores = e.errores                  # los campos en rojo deben verse: el panel reaparece
            self._con_parametros_visibles(lambda: self.panel.marcar_errores(errores))
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
            # Si el panel muestra una fila de «Comparar k y M», la página de comparación lo regenera con
            # el escenario de esa fila (o lo cierra si la fila ya no está): nunca con el escenario vigente.
            self.area.mostrar(self.esc, fmt, cs.contexto_graficas(self.esc, self.panel.get("ut")))
            if self.formulas.contexto is None:
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
    # Paneles laterales: parámetros (izquierda) y «Cómo se calculó» (derecha)
    # ------------------------------------------------------------------
    @property
    def parametros_visibles(self):
        """True si el panel de parámetros está visible (o apareciendo)."""
        return self._panel_visible

    def _limitar_ancho(self, ancho):
        tope = int(max(self.width(), TAMANO_MINIMO[0]) * tema.LAYOUT["panel_fraccion_max"])
        return max(self._ancho_min_panel, min(int(ancho), tope))

    def _restaurar_panel(self):
        aj = ajustes()
        try:
            ancho = int(aj.value("panel/ancho", self._ancho_min_panel))
        except (TypeError, ValueError):
            ancho = self._ancho_min_panel
        self._ancho_panel = self._limitar_ancho(ancho)
        self._panel_visible = str(aj.value("panel/visible", "true")).lower() != "false"
        self.divisor.setSizes([self._ancho_panel, TAMANO_INICIAL[0] - self._ancho_panel])
        self.panel.setVisible(self._panel_visible)
        self.animador.fijar("parametros", self._ancho_panel if self._panel_visible else 0)
        self.barra.marcar_parametros(self._panel_visible)

    def _guardar_panel(self):
        """Se guarda la elección del usuario: si el panel se ocultó solo por la fórmula, cuenta como visible."""
        aj = ajustes()
        aj.setValue("panel/visible", "true" if (self._panel_visible or self._parametros_auto) else "false")
        aj.setValue("panel/ancho", int(self._ancho_panel))

    def _aplicar_ancho_parametros(self, ancho):
        """Un cuadro: el panel de parámetros toma `ancho` y el centro (resultados + fórmula) el resto."""
        total = self.divisor.width() - self.divisor.handleWidth()
        self.divisor.setSizes([ancho, max(1, total - ancho)])

    def _aplicar_ancho_formulas(self, ancho):
        self.formulas.setFixedWidth(ancho)

    def _recordar_ancho_panel(self, *_):
        """El usuario movió el divisor: ese es el ancho al que vuelve el panel al mostrarse."""
        if self._panel_visible and not self.animador.activa("parametros") and not self.panel.isHidden():
            self._ancho_panel = self.panel.width()
            self.animador.fijar("parametros", self._ancho_panel)

    def alternar_parametros(self):
        self.mostrar_parametros(not self._panel_visible)

    def mostrar_parametros(self, visible=True, animar=True, auto=False):
        """
        Muestra u oculta el panel de parámetros cambiando de verdad el ancho del área de resultados
        en cada cuadro (AnimadorPaneles). Si se pide lo contrario a mitad de camino, sigue desde el
        ancho actual sin tirón. `auto`: lo pide la apertura de «Cómo se calculó» (no es una elección
        del usuario). El estado guardado es siempre el destino final.
        """
        if visible == self._panel_visible:
            return
        if not auto:
            self._parametros_auto = False        # el usuario decidió: ya no se restaura solo
        self._panel_visible = visible
        self.barra.marcar_parametros(visible)
        if not visible and not self.animador.activa("parametros") and not self.panel.isHidden():
            self._ancho_panel = self._limitar_ancho(self.panel.width())
        self._guardar_panel()
        self.panel.setMinimumWidth(0)            # mientras se anima puede ser más angosto que el formulario
        if visible and self.panel.isHidden():
            self.panel.show()
            self.animador.fijar("parametros", 0)
            self._aplicar_ancho_parametros(0)
        self.animador.animar("parametros", self._ancho_panel if visible else 0, self._ancho_panel,
                             animar and self.isVisible())

    def _fin_animacion(self, pista):
        if pista == "parametros":
            if not self._panel_visible:
                self.panel.hide()                # oculto, el área de resultados ocupa todo el ancho
            self.panel.setMinimumWidth(self._ancho_min_panel)
            accion, self._al_mostrarse = self._al_mostrarse, None
            if accion is not None and self._panel_visible:
                accion()
        elif pista == "formulas" and not self.formulas.abierto:
            self.formulas.hide()

    def _con_parametros_visibles(self, accion):
        """
        Ejecuta `accion` (marcar errores, ir a una sección) con el panel a la vista: ya mismo y otra
        vez cuando termina de aparecer, para que el foco y el desplazamiento queden bien.
        """
        accion()
        if self.panel.isHidden() or self.animador.activa("parametros") or not self._panel_visible:
            self._al_mostrarse = accion
            self.mostrar_parametros(True)

    def _ancho_formulas(self, con_parametros):
        """Ancho de «Cómo se calculó» desplegado: una fracción del centro, entre drawer_min y drawer_max."""
        L = tema.LAYOUT
        total = self.divisor.width() - ((self._ancho_panel + self.divisor.handleWidth()) if con_parametros else 0)
        return max(1, min(total, int(min(L["drawer_max"], max(L["drawer_min"], total * L["drawer_fraccion"])))))

    def _ancho_util_area(self):
        """Ancho mínimo útil del área: area_ancho_min o lo que necesita la página visible sin cortarse."""
        L = tema.LAYOUT
        pagina = self.area.pestanas.currentWidget()
        contenido = pagina.widget().minimumSizeHint().width() if pagina.widget() is not None else 0
        necesario = (contenido + L["area_margen"][0] + L["area_margen"][2]
                     + pagina.verticalScrollBar().sizeHint().width() + 2 * pagina.frameWidth())
        return max(L["area_ancho_min"], necesario)

    def _dejar_lugar_a_la_formula(self):
        """Si con el panel de parámetros el área quedaría por debajo de su ancho útil, se oculta mientras
        la fórmula esté abierta (y vuelve al cerrarla). True si lo ocultó."""
        if not self._panel_visible:
            return False
        centro = self.divisor.width() - (self._ancho_panel + self.divisor.handleWidth())
        if centro - self._ancho_formulas(True) >= self._ancho_util_area():
            return False
        self.mostrar_parametros(False, animar=self.isVisible(), auto=True)
        self._parametros_auto = True
        self._guardar_panel()
        return True

    def _desplegar_formulas(self):
        """Se abrió «Cómo se calculó»: se le hace lugar y se despliega."""
        self._dejar_lugar_a_la_formula()
        ancho = self._ancho_formulas(self._panel_visible)
        self.formulas.poner_ancho_abierto(ancho)
        self.animador.animar("formulas", ancho, ancho, self.isVisible())

    def _pestana_cambio(self, _indice):
        """Otra pestaña con la fórmula abierta (p. ej. Ctrl+5): puede necesitar más ancho."""
        if self.formulas.abierto and self._dejar_lugar_a_la_formula():
            ancho = self._ancho_formulas(False)
            self.formulas.poner_ancho_abierto(ancho)
            self.animador.animar("formulas", ancho, ancho, self.isVisible())

    def _replegar_formulas(self):
        self.animador.animar("formulas", 0, self.formulas.ancho_abierto, self.isVisible())
        if self._parametros_auto:
            self._parametros_auto = False
            self.mostrar_parametros(True, animar=self.isVisible(), auto=True)

    def _animacion_cambio(self, activa):
        """Al empezar se recuerda el desplazamiento de la pestaña; al terminar (tablas ya recalculadas)
        se repone, para que la página no salte."""
        barra = self.area.pestanas.currentWidget().verticalScrollBar()
        if activa:
            self._scroll_guardado = (barra, barra.value())
        elif self._scroll_guardado is not None:
            barra, valor = self._scroll_guardado
            self._scroll_guardado = None
            QTimer.singleShot(0, lambda: barra.setValue(min(valor, barra.maximum())))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not hasattr(self, "animador"):
            return
        self.animador.terminar()                 # cambio de tamaño a mitad de camino: termina limpio
        if self.formulas.abierto:
            ancho = self._ancho_formulas(self._panel_visible)
            self.formulas.poner_ancho_abierto(ancho)
            self.animador.fijar("formulas", ancho)
            self._aplicar_ancho_formulas(ancho)

    def _ir_a_costos(self):
        self._con_parametros_visibles(lambda: self.panel.ir_a_seccion("costos", "cS"))

    def closeEvent(self, e):
        self._recordar_ancho_panel()
        self._guardar_panel()
        super().closeEvent(e)

    # ------------------------------------------------------------------
    # Fórmulas y tema
    # ------------------------------------------------------------------
    def mostrar_formula(self, clave):
        if self.esc is None:
            return
        self.p_comparacion.soltar_fila()
        self.formulas.abrir(self.esc, clave, self._formateador())
        self.p_resultados.tarjetas.marcar_activa(clave)

    def mostrar_formula_fila(self, esc_fila, clave, metrica, fila):
        """«Cómo se calculó» de `metrica` en una fila de «Comparar k y M» (escenario de esa fila)."""
        if self.esc is None:
            return
        self.p_resultados.tarjetas.marcar_activa(None)
        self.formulas.abrir(esc_fila, clave, self._formateador(), contexto=fila, nombre=metrica)

    def _formula_cerrada(self):
        self.p_resultados.tarjetas.marcar_activa(None)
        self.p_comparacion.soltar_fila()
        self._replegar_formulas()

    def alternar_tema(self):
        self.aplicar_tema("oscuro" if tema.actual() == "claro" else "claro")

    def aplicar_tema(self, nombre):
        """
        Cambia de tema en un solo paso visible: con el repintado de la ventana suspendido se aplican
        paleta + QSS (a nivel de aplicación) y se regeneran lo que pinta con matplotlib (gráfica
        visible y ecuaciones del panel abierto); al reactivar el repintado todo aparece a la vez.
        """
        self.setUpdatesEnabled(False)
        try:
            tema.aplicar(QApplication.instance(), nombre)
            self.barra.actualizar_tema()
            self.area.repintar()
            self.formulas.repintar()
        finally:
            self.setUpdatesEnabled(True)
        aplicar_barra_titulo(self, nombre == "oscuro")
        self.update()

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
