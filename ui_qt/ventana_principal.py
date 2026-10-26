"""
ventana_principal.py
Ventana principal de la versión Qt. Coordina el mismo flujo que ui/app.py:

    PanelEntradas --(texto)--> calculadora_service.leer_parametros()
                  --> calculadora_service.calcular_escenario()
                  --> AreaResultados (encabezado, pestañas con tarjetas y tablas)
    clic en tarjeta o fila --> PanelFormulas («Cómo se calculó»)
    clic en fila de «Comparar k y M» --> PanelFormulas con el escenario de esa fila

Distribución: barra superior fina, banner global de datos desactualizados y, debajo,
el panel de parámetros a la izquierda y el área de resultados con pestañas a la derecha.
El panel de parámetros se oculta / muestra con el botón de la barra o Ctrl+B; la animación
desplaza capturas (TransicionPanel) y el divisor se reacomoda una sola vez al terminar. Se
vuelve a mostrar solo si hay campos con error o se pide ir a una sección. Su estado (visible
y ancho) se recuerda entre sesiones con QSettings.

Distingue tres tipos de fallo:
    ErrorEntrada  -> se marcan los campos en el formulario.
    ErrorModelo   -> limitación matemática / numérica, se explica en el encabezado.
    otro          -> error inesperado: mensaje breve al usuario y traza en consola.
En cualquier fallo se retiran los resultados anteriores para no confundirlos.
"""
import traceback

from PySide6.QtCore import Property, QAbstractAnimation, QEasingCurve, QPropertyAnimation, QSettings, Qt
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
from .barra_titulo import aplicar_barra_titulo
from .panel_entradas import PanelEntradas
from .panel_formulas import PanelFormulas
from .transicion_panel import TransicionPanel

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

        # Panel «Cómo se calculó»: superpuesto al área de resultados, no ocupa lugar en el layout
        self.formulas = PanelFormulas()
        self.formulas.anclar(self.area)
        self.formulas.cerrado.connect(self._formula_cerrada)
        self.area.fila_perdida.connect(self.formulas.cerrar)

        self.divisor = QSplitter(Qt.Horizontal)
        self.divisor.setChildrenCollapsible(False)
        self.divisor.setHandleWidth(4)
        for w in (self.panel, self.area):
            self.divisor.addWidget(w)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.splitterMoved.connect(self._recordar_ancho_panel)
        self._ancho_min_panel = self.panel.minimumWidth()
        self._al_mostrarse = None       # acción pendiente hasta que el panel termine de aparecer
        self._anim_panel = QPropertyAnimation(self, b"anchoParametros", self)
        self._anim_panel.setDuration(tema.LAYOUT["panel_ms"])
        self._anim_panel.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_panel.finished.connect(self._fin_animacion_panel)
        self._restaurar_panel()

        raiz = QWidget()
        lay = QVBoxLayout(raiz)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.barra)
        lay.addWidget(self.banner)
        lay.addWidget(self.divisor, 1)
        self.setCentralWidget(raiz)
        self.transicion = TransicionPanel(raiz)      # tapa el divisor solo mientras dura la animación

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
    # Panel de parámetros ocultable
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
        self.barra.marcar_parametros(self._panel_visible)

    def _guardar_panel(self):
        aj = ajustes()
        aj.setValue("panel/visible", "true" if self._panel_visible else "false")
        aj.setValue("panel/ancho", int(self._ancho_panel))

    def _animando(self):
        anim = getattr(self, "_anim_panel", None)        # QPropertyAnimation lee la propiedad al crearse
        return anim is not None and anim.state() == QAbstractAnimation.Running

    def _ancho_animado(self):
        if self._animando():
            return self.transicion.ancho
        return 0 if self.panel.isHidden() else self.panel.width()

    def _poner_ancho_animado(self, ancho):
        """Un cuadro de la animación: solo se desplazan las capturas (nada se reacomoda)."""
        self.transicion.poner_ancho(ancho)

    # Ancho visible del panel de parámetros como propiedad Qt: es lo único que anima QPropertyAnimation
    anchoParametros = Property(int, _ancho_animado, _poner_ancho_animado)

    def _recordar_ancho_panel(self, *_):
        """El usuario movió el divisor: ese es el ancho al que vuelve el panel al mostrarse."""
        if self._panel_visible and not self._animando() and not self.panel.isHidden():
            self._ancho_panel = self.panel.width()

    def alternar_parametros(self):
        self.mostrar_parametros(not self._panel_visible)

    def mostrar_parametros(self, visible=True, animar=True):
        """
        Muestra u oculta el panel de parámetros. La animación solo desplaza las capturas de
        TransicionPanel: el layout real (divisor, tablas, gráfica y panel «Cómo se calculó»,
        anclado al área de resultados) se aplica una sola vez, al terminar. Si se pide lo contrario
        a mitad de camino, la animación se invierte desde el ancho actual: como el layout real
        aún no cambió, no hay saltos. El estado guardado es siempre el destino final.
        """
        if visible == self._panel_visible:
            return
        animando = self._animando()
        self._panel_visible = visible
        self.barra.marcar_parametros(visible)
        if not visible and not animando and not self.panel.isHidden():
            self._ancho_panel = self._limitar_ancho(self.panel.width())
        self._guardar_panel()
        if not (animar and self.isVisible()):
            self._anim_panel.stop()
            self._fin_animacion_panel()
            return
        inicio = self._ancho_animado()
        self._anim_panel.stop()
        if not animando:
            self._capturar(inicio)
        fin = self._ancho_panel if visible else 0
        # Velocidad constante: invertir a mitad de camino tarda solo lo que falta recorrer
        self._anim_panel.setDuration(max(1, round(tema.LAYOUT["panel_ms"] * abs(fin - inicio) / self._ancho_panel)))
        self._anim_panel.setStartValue(inicio)
        self._anim_panel.setEndValue(fin)
        self._anim_panel.start()

    def _capturar(self, inicio):
        """Fotografía el panel (con su ancho de visible) y el área de resultados tal como están."""
        if self.panel.isHidden():
            self.panel.resize(self._ancho_panel, self.divisor.height())
        anclada = 0
        if self.formulas.isVisible():          # el drawer (y su sombra) siguen pegados al borde derecho
            izquierda = self.formulas.x() - (self.formulas.sombra.width() if self.formulas.sombra else 0)
            anclada = max(0, self.area.width() - izquierda)
        self.transicion.poner_ancho(inicio)
        self.transicion.preparar(self.divisor.geometry(), self.panel.grab(), self._ancho_panel, self.area.grab(),
                                 self.divisor.handleWidth(), anclada)


    def _fin_animacion_panel(self):
        """Aplica el layout final una sola vez y retira las capturas."""
        if self._panel_visible:
            self.panel.show()
            total = self.divisor.width() - self.divisor.handleWidth()
            self.divisor.setSizes([self._ancho_panel, max(1, total - self._ancho_panel)])
        else:
            self.panel.hide()                      # oculto, el área de resultados ocupa todo el ancho
        self.transicion.terminar()
        accion, self._al_mostrarse = self._al_mostrarse, None
        if accion is not None and self._panel_visible:
            accion()

    def _con_parametros_visibles(self, accion):
        """
        Ejecuta `accion` (marcar errores, ir a una sección) con el panel a la vista: ya mismo, para
        que la captura de la animación lo muestre, y otra vez cuando termina de aparecer, para que el
        foco y el desplazamiento funcionen (un widget oculto no recibe el foco).
        """
        accion()
        if self.panel.isHidden() or self._animando() or not self._panel_visible:
            self._al_mostrarse = accion
            self.mostrar_parametros(True)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._animando():                       # las capturas ya no calzan: se salta al final
            self._anim_panel.stop()
            self._fin_animacion_panel()

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
