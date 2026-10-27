"""
Pruebas de la ventana Qt sin pantalla (offscreen): aviso de desactualizado,
tarjetas, botón «Calcular» y nota de costos. Se omiten si PySide6 no está instalado.
"""
import importlib.util
import unittest

import utilidades  # noqa: F401  (agrega la raíz del proyecto al path)

HAY_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAY_QT, "PySide6 no está instalado")
class TestVentanaQt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from ui_qt import soporte_pruebas as sp
        cls.sp = sp
        sp.aplicacion()
        from ui_qt.banner_desactualizado import BannerDesactualizado
        from ui_qt.ventana_principal import VentanaPrincipal
        cls.Banner = BannerDesactualizado
        cls.v = VentanaPrincipal()
        cls.v.resize(1366, 768)
        cls.v.show()
        sp.procesar()

    @classmethod
    def tearDownClass(cls):
        cls.v.formulas.cerrar()
        cls.v.animador.terminar()
        cls.v.close()
        cls.v.deleteLater()
        cls.sp.procesar()

    def setUp(self):
        self.v.mostrar_parametros(True, animar=False)
        self.v.formulas.cerrar()
        self.v.animador.terminar()                 # sin paneles a medio camino entre pruebas
        self.sp.procesar()
        self.v.panel.restablecer()
        self.v.calcular()
        self.v.area.ir_a(0)
        self.sp.procesar()

    def test_un_solo_aviso_de_desactualizado(self):
        avisos = self.v.findChildren(self.Banner)
        self.assertEqual(len(avisos), 1)
        banner = avisos[0]
        self.assertFalse(banner.activo)
        self.v.panel.poner("k", "2")                       # datos cambiados sin recalcular
        self.sp.esperar(500)
        self.assertTrue(banner.activo and banner.isVisible())
        self.assertFalse(self.v.panel.btn_exportar.isEnabled())
        self.assertNotIn("Parámetros modificados", self.v.estado.text())
        self.v.calcular()
        self.sp.esperar(500)
        self.assertFalse(banner.activo or banner.isVisible())

    def test_tarjetas_solo_en_resultados(self):
        tarjetas = self.v.p_resultados.tarjetas
        self.assertTrue(tarjetas.isVisible())
        for i in range(1, 5):
            self.v.area.ir_a(i)
            self.sp.procesar()
            self.assertFalse(tarjetas.isVisible(), f"pestaña {i}")
        self.v.area.ir_a(0)
        self.sp.procesar()
        self.assertTrue(tarjetas.isVisible())

    def test_tarjetas_en_una_fila_a_1366(self):
        self.assertEqual(self.v.p_resultados.tarjetas.columnas, 7)

    def test_calcular_visible_al_tamano_minimo(self):
        for s in self.v.panel.secciones.values():
            s.abrir(True)
        tam = self.v.size()
        try:
            self.v.resize(self.v.minimumSize())
            self.sp.procesar()
            self.assertTrue(self.sp.visible_en_ventana(self.v.panel.btn_calcular))
            self.v.resize(1366, 768)
            self.sp.procesar()
            self.assertTrue(self.sp.visible_en_ventana(self.v.panel.btn_calcular))
        finally:
            self.v.resize(tam)
            self.sp.procesar()

    def _abrir_formula(self, clave="Lq"):
        self.v.mostrar_formula(clave)
        self.sp.esperar(400)
        self.assertTrue(self.v.formulas.abierto and self.v.formulas.isVisible())

    def _comprobar_acoplado(self, exacto=True):
        """«Cómo se calculó» acoplado a la derecha: el área termina donde empieza el panel (sin taparla).
        exacto: el ancho es la fracción del centro con que se abrió (al alternar los parámetros se conserva)."""
        v = self.v
        geo, centro, area = v.formulas.geometry(), v.centro.rect(), v.area.geometry()
        self.assertEqual(geo.right(), centro.right())
        self.assertEqual(area.right() + 1, geo.left())
        self.assertEqual(geo.height(), centro.height())
        self.assertEqual(area.width() + geo.width(), centro.width())
        L = __import__("ui_qt.tema", fromlist=["LAYOUT"]).LAYOUT
        total = v.divisor.width() - ((v.panel.width() + v.divisor.handleWidth()) if v.panel.isVisible() else 0)
        esperado = max(L["drawer_min"], min(L["drawer_max"], int(total * L["drawer_fraccion"])))
        if exacto:
            self.assertLessEqual(abs(geo.width() - esperado), 1)
        else:
            self.assertTrue(L["drawer_min"] <= geo.width() <= L["drawer_max"], geo.width())

    def test_panel_de_formulas_acoplado_achica_el_area(self):
        area = self.v.area.width()
        self._abrir_formula()
        self._comprobar_acoplado()
        self.assertEqual(self.v.area.width(), area - self.v.formulas.width())
        self.v.formulas.cerrar()
        self.sp.esperar(400)
        self.assertFalse(self.v.formulas.isVisible())
        self.assertEqual(self.v.area.width(), area)

    def test_esc_cierra_el_panel(self):
        self._abrir_formula()
        self.v.activateWindow()
        self.sp.tecla(self.v, "Escape")
        self.sp.esperar(400)
        self.assertFalse(self.v.formulas.abierto or self.v.formulas.isVisible())

    def test_clic_fuera_cierra_y_seleccion_resaltada(self):
        self._abrir_formula("Pw")
        activa = [t.clave for t in self.v.p_resultados.tarjetas.tarjetas if t.property("activa") == "true"]
        self.assertEqual(activa, ["Pw"])
        self.sp.clic(self.v.panel.secciones["modelo"].cabecera)       # clic fuera del panel
        self.sp.esperar(400)
        self.assertFalse(self.v.formulas.abierto)
        activa = [t for t in self.v.p_resultados.tarjetas.tarjetas if t.property("activa") == "true"]
        self.assertEqual(activa, [])

    def test_sin_aviso_dentro_del_panel(self):
        self._abrir_formula()
        self.v.panel.poner("k", "2")
        self.sp.esperar(300)
        textos = " ".join(w.text() for w in self.v.formulas.findChildren(type(self.v.estado)))
        self.assertNotIn("cambiaron", textos)
        self.assertNotIn("desactualiz", textos.lower())

    # ------------------------------------------------------------------
    # Estado vacío de costos
    # ------------------------------------------------------------------
    def test_estado_vacio_solo_sin_costos(self):
        pag = self.v.p_costos
        self.v.area.ir_a(2)
        self.sp.procesar()
        self.assertTrue(pag.mostrando_vacio and pag.vacio.isVisible())    # valores iniciales: todo en 0
        self.assertFalse(pag.tabla_cost.vista.isVisible())
        self.v.panel.poner("cW", "5")                                     # solo costo de espera
        self.v.calcular()
        self.sp.procesar()
        self.assertFalse(pag.mostrando_vacio or pag.vacio.isVisible())
        self.assertTrue(pag.tabla_cost.vista.isVisible())

    def test_ceros_atenuados_y_rentabilidad_no_aplica(self):
        from ui_qt import tema
        sp = self.sp
        self.v.panel.poner("cW", "5")                                     # cS, cI e ingreso siguen en 0
        self.v.calcular()
        self.sp.procesar()
        m = self.v.p_costos.tabla_cost.vista.model()
        filas = {sp.celda(m, r, 0): r for r in range(m.rowCount())}
        self.assertEqual(sp.celda(m, filas["CT(S) costo de servidores"], 1, "color").name(), tema.color("texto_3"))
        self.assertIsNone(sp.celda(m, filas["CT(TE) costo del tiempo de espera"], 1, "color"))
        self.assertEqual(sp.celda(m, filas["Rentabilidad (ingresos ÷ gastos)"], 1), "—")

    def test_boton_ir_a_costos(self):
        self.v.panel.secciones["costos"].abrir(False)
        self.v.panel.scroll.verticalScrollBar().setValue(0)
        self.v.area.ir_a(2)
        self.v.activateWindow()
        self.sp.procesar()
        self.sp.clic(self.v.p_costos.vacio.boton)
        self.sp.procesar()
        seccion = self.v.panel.secciones["costos"]
        campo = self.v.panel.widgets["cS"]
        self.assertTrue(seccion.cuerpo.isVisible())
        self.assertTrue(campo.hasFocus())
        visor = self.v.panel.scroll.viewport()
        arriba = campo.mapTo(visor, campo.rect().topLeft()).y()
        self.assertTrue(0 <= arriba and arriba + campo.height() <= visor.height(), "el campo no quedó a la vista")

    # ------------------------------------------------------------------
    # Tablas, cajas informativas, banner y sombra
    # ------------------------------------------------------------------
    def _tablas(self):
        """Todas las tablas con datos; población finita para que también haya tabla «en función de M»."""
        from ui_qt.vista_tabla import VistaTabla
        self.v.panel.poner("poblacion", "Finita")
        self.v.panel.poner("cW", "5")
        self.v.calcular()
        self.sp.procesar()
        return [t for t in self.v.area.findChildren(VistaTabla) if t.modelo.tabla is not None]

    def test_numeros_a_la_derecha_en_todas_las_tablas(self):
        sp = self.sp
        tablas = self._tablas()
        self.assertGreaterEqual(len(tablas), 7)
        for t in tablas:
            m = t.vista.model()
            for c, col in enumerate(t.modelo.tabla.columnas):
                bien = sp.a_la_derecha if col.numerica else sp.a_la_izquierda
                self.assertTrue(bien(sp.encabezado(m, c, "alineacion")), f"{t.modelo.tabla.titulo} / {col.titulo}")
                for r in range(m.rowCount()):
                    self.assertTrue(bien(sp.celda(m, r, c, "alineacion")),
                                    f"{t.modelo.tabla.titulo} / {col.titulo}: fila {r}")

    def test_orden_no_desalinea_las_cifras(self):
        sp = self.sp
        t = self.v.p_probabilidades.tabla_dist
        sp.ordenar(t.vista, 2)
        sp.procesar()
        m = t.vista.model()
        titulo = sp.encabezado(m, 2)
        self.assertTrue(titulo.startswith("↓ "), titulo)      # flecha delante: el borde derecho no cambia
        self.assertTrue(sp.a_la_derecha(sp.encabezado(m, 2, "alineacion")))
        sp.sin_orden(t.vista)

    def test_filas_alternas_en_todas_las_tablas(self):
        for t in self._tablas():
            self.assertTrue(t.vista.alternatingRowColors(), t.modelo.tabla.titulo)

    def test_cajas_informativas_sin_cortes(self):
        from ui_qt.info_box import InfoBox
        for i in range(5):
            self.v.area.ir_a(i)
            self.sp.procesar()
            for caja in self.v.area.findChildren(InfoBox):
                if caja.isVisible():
                    necesario = caja.layout().heightForWidth(caja.width())
                    self.assertGreaterEqual(caja.height(), necesario, caja.text()[:40])
                    self.assertGreaterEqual(caja.texto.height(), caja.texto.heightForWidth(caja.texto.width()))

    def test_banner_con_aire_y_boton_centrado(self):
        from ui_qt import tema
        self.v.panel.poner("k", "2")
        self.sp.esperar(500)
        b = self.v.banner
        m = b.layout().contentsMargins()
        self.assertGreaterEqual(m.top(), 10)
        self.assertGreaterEqual(m.left(), 14)
        self.assertGreaterEqual(b.layout().spacing(), 12)
        centro_boton = b.boton.geometry().center().y()
        centro_texto = b.texto.geometry().center().y()
        self.assertLessEqual(abs(centro_boton - centro_texto), 2)
        self.assertEqual(tema.LAYOUT["banner_margen"], (m.left(), m.top(), m.right(), m.bottom()))

    # ------------------------------------------------------------------
    # Panel de parámetros ocultable (Ctrl+B)
    # ------------------------------------------------------------------
    def test_alternar_oculta_y_muestra_parametros(self):
        v, sp = self.v, self.sp
        ancho = v.panel.width()
        sp.clic(v.barra.btn_parametros)
        sp.esperar(400)
        self.assertFalse(v.parametros_visibles or v.panel.isVisible())
        self.assertFalse(v.barra.btn_parametros.isChecked())
        self.assertEqual(v.area.width(), v.divisor.width())           # resultados a todo el ancho
        # F5 sigue calculando con el panel oculto, y el panel no reaparece
        v.panel.poner("k", "2")
        v.activateWindow()
        sp.tecla(v, "F5")
        sp.procesar()
        self.assertEqual(v.esc.p.k, 2)
        self.assertFalse(v.panel.isVisible())
        # «Cómo se calculó» se acopla al área ensanchada
        self._abrir_formula()
        self._comprobar_acoplado()
        v.formulas.cerrar()
        self._esperar_fin()
        sp.tecla(v, "B", ctrl=True)                                   # Ctrl+B lo vuelve a mostrar
        sp.esperar(400)
        self.assertTrue(v.parametros_visibles and v.panel.isVisible())
        self.assertTrue(v.barra.btn_parametros.isChecked())
        self.assertEqual(v.panel.width(), ancho)                       # con el último ancho que tenía
        self.assertEqual(v.panel.width() + v.divisor.handleWidth() + v.area.width(), v.divisor.width())

    def test_calcular_con_error_reabre_parametros(self):
        v = self.v
        v.mostrar_parametros(False, animar=False)
        self.assertTrue(v.panel.isHidden())
        v.panel.poner("k", "abc")
        v.activateWindow()
        v.calcular()
        self.sp.esperar(400)
        self.assertTrue(v.parametros_visibles and v.panel.isVisible())
        campo = v.panel.widgets["k"]
        self.assertTrue(campo.property("error"))
        self.assertTrue(campo.isVisible())
        self.assertTrue(campo.hasFocus())                 # el foco llega cuando el panel terminó de aparecer

    def _anchos_por_cuadro(self, pista):
        """Lista que va recibiendo el ancho aplicado en cada cuadro de la pista dada."""
        anchos = []
        self.v.animador.avanzo.connect(lambda nombre, ancho: anchos.append(ancho) if nombre == pista else None)
        return anchos

    def _esperar_fin(self, tope_ms=2000):
        for _ in range(tope_ms // 10):
            if not self.v.animador.activa():
                break
            self.sp.esperar(10)
        self.sp.procesar()
        self.assertFalse(self.v.animador.activa(), "la animación no terminó")

    def test_animacion_mueve_el_area_y_difiere_lo_caro(self):
        """El área cambia de ancho en cada cuadro; tablas y gráfica se recalculan una sola vez, al final."""
        from ui_qt import animacion
        v, sp = self.v, self.sp
        for pestana, pesado in ((3, lambda: v.p_comparacion.tabla_k.pendiente),
                                (4, lambda: v.p_graficas.canvas._foto is not None)):
            v.area.ir_a(pestana)
            sp.procesar()
            areas, vio_diferido = [], False
            v.mostrar_parametros(False)
            while v.animador.activa():
                sp.esperar(10)
                areas.append(v.area.width())
                vio_diferido = vio_diferido or (animacion.animando() and pesado())
            sp.procesar()
            self.assertGreaterEqual(len(set(areas)), 3, f"pestaña {pestana}: el área no creció por cuadros")
            self.assertEqual(areas, sorted(areas), f"pestaña {pestana}: el área no creció de forma continua")
            self.assertTrue(vio_diferido, f"pestaña {pestana}: el trabajo caro no se difirió")
            self.assertFalse(pesado(), f"pestaña {pestana}: quedó trabajo pendiente al terminar")
            self.assertEqual(v.area.width(), v.divisor.width())
            v.mostrar_parametros(True, animar=False)
            sp.procesar()

    def _invertir(self, desde_visible):
        """
        Ctrl+B a mitad de camino: registra el ancho de cada cuadro y comprueba que el sentido se
        invierte, que ningún cuadro salta más de un tercio del recorrido y el estado final. No depende
        de un único tiempo de espera: espera a que el panel esté en el tramo central.
        """
        from ui_qt.ventana_principal import ajustes
        v, sp = self.v, self.sp
        v.mostrar_parametros(desde_visible, animar=False)
        sp.procesar()
        ancho = v._ancho_panel
        anchos = self._anchos_por_cuadro("parametros")
        v.activateWindow()
        sp.tecla(v, "B", ctrl=True)
        for _ in range(200):                       # hasta llegar al tramo central (o como mucho 2 s)
            if anchos and ancho / 4 < anchos[-1] < 3 * ancho / 4:
                break
            sp.esperar(5)
        self.assertTrue(v.animador.activa() and ancho / 4 < anchos[-1] < 3 * ancho / 4, anchos)
        corte = len(anchos)
        sp.tecla(v, "B", ctrl=True)                # se invierte a mitad de camino
        self._esperar_fin()
        ida, vuelta = anchos[:corte], anchos[corte:]
        signo = -1 if desde_visible else 1         # sentido de la ida
        self.assertTrue(all(signo * (b - a) >= 0 for a, b in zip(ida, ida[1:])), ida)
        self.assertTrue(vuelta, "no hubo cuadros después de invertir")
        self.assertTrue(all(signo * (b - a) <= 0 for a, b in zip([ida[-1]] + vuelta, vuelta)), vuelta)
        saltos = [abs(b - a) for a, b in zip(anchos, anchos[1:])]
        self.assertLessEqual(max(saltos), ancho / 3, anchos)
        self.assertEqual(v.parametros_visibles, desde_visible)
        self.assertEqual(v.panel.isVisible(), desde_visible)
        self.assertEqual(v.barra.btn_parametros.isChecked(), desde_visible)
        self.assertEqual(ajustes().value("panel/visible"), "true" if desde_visible else "false")
        if desde_visible:
            self.assertEqual(v.panel.width(), ancho)
        else:
            self.assertEqual(v.area.width(), v.divisor.width())

    def test_ctrl_b_a_mitad_invierte_al_ocultar(self):
        self._invertir(desde_visible=True)

    def test_ctrl_b_a_mitad_invierte_al_mostrar(self):
        self._invertir(desde_visible=False)

    def test_panel_de_formulas_abierto_no_se_desacomoda(self):
        v = self.v
        self._abrir_formula()
        for visible in (False, True):
            v.mostrar_parametros(visible)
            self._esperar_fin()
            self.assertTrue(v.formulas.abierto)
            self._comprobar_acoplado(exacto=False)

    def test_formula_en_ventana_angosta_oculta_parametros_y_los_restaura(self):
        from ui_qt.ventana_principal import TAMANO_MINIMO, ajustes
        v, sp = self.v, self.sp
        tam = v.size()
        try:
            v.resize(*TAMANO_MINIMO)
            sp.procesar()
            self._abrir_formula()
            self._esperar_fin()
            self.assertFalse(v.panel.isVisible())                  # dejó lugar a la fórmula
            self.assertGreaterEqual(v.area.width(), __import__("ui_qt.tema", fromlist=["x"]).LAYOUT["area_ancho_min"])
            self.assertEqual(ajustes().value("panel/visible"), "true")   # no es una elección del usuario
            v.formulas.cerrar()
            self._esperar_fin()
            self.assertTrue(v.panel.isVisible())                   # vuelve al cerrar la fórmula
            # Si el usuario lo cambia a mano mientras la fórmula está abierta, no se restaura solo
            self._abrir_formula()
            self._esperar_fin()
            v.mostrar_parametros(True)
            self._esperar_fin()
            v.mostrar_parametros(False)
            self._esperar_fin()
            v.formulas.cerrar()
            self._esperar_fin()
            self.assertFalse(v.panel.isVisible())
        finally:
            v.mostrar_parametros(True, animar=False)
            v.resize(tam)
            sp.procesar()

    def test_formula_en_graficas_deja_lugar_a_la_grafica(self):
        """Gráficas necesita más ancho que area_ancho_min: con la fórmula abierta, nada se corta."""
        v, sp = self.v, self.sp
        try:
            v.area.ir_a(4)
            sp.procesar()
            self._abrir_formula()
            self._esperar_fin()
            pagina = v.area.pestanas.currentWidget()
            self.assertFalse(pagina.horizontalScrollBar().isVisible())
            self.assertGreaterEqual(v.area.width(), v._ancho_util_area())
            v.formulas.cerrar()
            self._esperar_fin()
            self.assertTrue(v.panel.isVisible())
            # Con la fórmula abierta en Resultados, Ctrl+5 lleva a Gráficas: también se le hace lugar
            v.area.ir_a(0)
            self._abrir_formula()
            self._esperar_fin()
            self.assertTrue(v.panel.isVisible())
            v.activateWindow()
            sp.tecla(v, "5", ctrl=True)
            self._esperar_fin()
            self.assertTrue(v.formulas.abierto)
            self.assertFalse(v.area.pestanas.currentWidget().horizontalScrollBar().isVisible())
        finally:
            v.formulas.cerrar()
            v.animador.terminar()
            v.mostrar_parametros(True, animar=False)
            sp.procesar()

    def test_redimensionar_durante_la_animacion_termina_limpio(self):
        v, sp = self.v, self.sp
        tam = v.size()
        try:
            v.mostrar_formula("Lq")
            v.mostrar_parametros(False)
            sp.esperar(40)
            self.assertTrue(v.animador.activa())
            v.resize(1300, 760)
            sp.procesar()
            self.assertFalse(v.animador.activa())
            self.assertFalse(v.panel.isVisible())
            self._comprobar_acoplado()
        finally:
            v.formulas.cerrar()
            v.animador.terminar()
            v.resize(tam)
            sp.procesar()

    def test_el_scroll_de_la_pestana_no_salta(self):
        v, sp = self.v, self.sp
        v.area.ir_a(1)                                            # Probabilidades: página larga
        sp.procesar()
        barra = v.area.pestanas.currentWidget().verticalScrollBar()
        barra.setValue(barra.maximum() // 2)
        valor = barra.value()
        self.assertGreater(valor, 0)
        for visible in (False, True):
            v.mostrar_parametros(visible)
            self._esperar_fin()
            sp.esperar(50)
            self.assertEqual(barra.value(), min(valor, barra.maximum()))

    def test_ir_a_costos_reabre_parametros(self):
        v = self.v
        v.mostrar_parametros(False, animar=False)
        v.area.ir_a_costos.emit()
        self.sp.esperar(400)
        self.assertTrue(v.panel.isVisible())
        self.assertTrue(v.panel.secciones["costos"].cuerpo.isVisible())

    def test_parametros_recordados_entre_sesiones(self):
        v, sp = self.v, self.sp
        v.divisor.moveSplitter(v.panel.minimumWidth() + 40, 1)
        sp.procesar()
        ancho = v.panel.width()
        v.mostrar_parametros(False, animar=False)
        from ui_qt.ventana_principal import VentanaPrincipal
        otra = VentanaPrincipal()
        try:
            self.assertFalse(otra.parametros_visibles)
            self.assertTrue(otra.panel.isHidden())
            self.assertFalse(otra.barra.btn_parametros.isChecked())
            otra.resize(1366, 768)
            otra.show()
            otra.mostrar_parametros(True, animar=False)
            sp.procesar()
            self.assertEqual(otra.panel.width(), ancho)
        finally:
            otra.formulas.cerrar()
            otra.close()                     # guarda «visible»: no afecta a las demás pruebas
            otra.deleteLater()
            sp.procesar()

    # ------------------------------------------------------------------
    # «Cómo se calculó» desde una fila de «Comparar k y M»
    # ------------------------------------------------------------------
    def _titulo_formula(self):
        return [w.text() for w in self.v.formulas.findChildren(type(self.v.estado))
                if w.objectName() == "FormulaTitulo"][0]

    def _textos_formula(self):
        return " ".join(w.text() for w in self.v.formulas.findChildren(type(self.v.estado)))

    def test_clic_en_fila_de_comparacion_abre_su_formula(self):
        v, sp = self.v, self.sp
        pag, f = v.p_comparacion, v.formulas
        v.panel.poner("lam", "40")                  # M/M/k: la tabla de k empieza en k = 3
        v.calcular()
        v.area.ir_a(3)
        pag.cb_metrica.setCurrentText("Wq (tiempo en cola)")
        sp.procesar()
        vista = pag.tabla_k.vista
        k = int(sp.celda(vista.model(), 1, 0))
        sp.clic_fila(vista, 1)
        sp.esperar(400)
        self.assertTrue(f.abierto and f.isVisible())
        self.assertEqual((f.clave, f.contexto), ("Wq", f"k = {k}"))
        self.assertEqual(f._esc.p.k, k)                               # escenario de la fila, no el vigente
        self.assertIsNot(f._esc, v.esc)
        self.assertEqual(f._esc.r["Wq"], next(r for r in v.esc.barrido_k if r["k"] == k)["Wq"])
        self.assertIn(f"Wq para k = {k}", self._titulo_formula())
        self.assertIn(f"M/M/{k}", self._textos_formula())
        self.assertEqual(sp.filas_seleccionadas(vista), [1])          # la fila queda resaltada

        # Otra métrica en la barra con el panel abierto: misma fila, nueva fórmula
        pag.cb_metrica.setCurrentText("Probabilidad de esperar")
        sp.procesar()
        self.assertTrue(f.abierto)
        self.assertEqual((f.clave, f.contexto, f._esc.p.k), ("Pw", f"k = {k}", k))
        self.assertEqual(sp.filas_seleccionadas(vista), [1])

        # Clic en otra fila: cambia la fórmula en vez de cerrar el panel
        k0 = int(sp.celda(vista.model(), 0, 0))
        sp.clic_fila(vista, 0)
        sp.esperar(300)
        self.assertTrue(f.abierto)
        self.assertEqual((f.contexto, f._esc.p.k), (f"k = {k0}", k0))

        # Cambio de tema y de presentación: se regenera con el escenario de la fila
        v.aplicar_tema("oscuro")
        try:
            self.assertEqual((f.contexto, f._esc.p.k), (f"k = {k0}", k0))
        finally:
            v.aplicar_tema("claro")
        v.panel.poner("dec", "2")
        sp.procesar()
        self.assertEqual((f.contexto, f._esc.p.k, f._fmt.decimales), (f"k = {k0}", k0, 2))

        # Métrica que no aplica (solo población finita): mensaje claro, sin fallar
        pag.cb_metrica.setCurrentText("Fracción de unidades operando (finita)")
        sp.procesar()
        self.assertTrue(f.abierto)
        self.assertIn(f"para k = {k0}", self._titulo_formula())
        self.assertIn("solo aplica a población finita", self._textos_formula())

        # Recalcular: si la fila sigue en la comparación se regenera con su escenario (del nuevo cálculo)...
        pag.cb_metrica.setCurrentText("Wq (tiempo en cola)")
        v.panel.poner("cS", "10")
        v.calcular()
        sp.esperar(300)
        self.assertTrue(f.abierto)
        self.assertEqual((f.contexto, f._esc.p.k, f._esc.p.cfg), (f"k = {k0}", k0, v.esc.p.cfg))
        self.assertIsNot(f._esc, v.esc)
        # ... y si ya no está (k máximo menor: la tabla llega hasta k = 7), el panel se cierra
        ultima = vista.model().rowCount() - 1
        self.assertEqual(int(sp.celda(vista.model(), ultima, 0)), 10)
        sp.clic_fila(vista, ultima)
        sp.esperar(300)
        self.assertEqual(f.contexto, "k = 10")
        v.panel.poner("kmax", "1")
        v.calcular()
        sp.esperar(400)
        self.assertFalse(f.abierto)
        self.assertIsNone(pag.fila)
        self.assertEqual(sp.filas_seleccionadas(vista), [])

        # Clic fuera: se cierra y la fila deja de estar resaltada
        sp.clic_fila(vista, 0)
        sp.esperar(300)
        self.assertTrue(f.abierto)
        self.assertEqual(sp.filas_seleccionadas(vista), [0])
        sp.clic(v.panel.secciones["modelo"].cabecera)
        sp.esperar(400)
        self.assertFalse(f.abierto)
        self.assertIsNone(pag.fila)
        self.assertEqual(sp.filas_seleccionadas(vista), [])

    # ------------------------------------------------------------------
    # Listas desplegables (ui_qt/combo.py)

    # ------------------------------------------------------------------
    def test_listas_desplegables_con_estilo_propio(self):
        from ui_qt import tema
        from ui_qt.combo import Combo
        sp, v = self.sp, self.v
        listas = sp.listas_desplegables(v)
        self.assertGreaterEqual(len(listas), 8)
        for c in listas:
            self.assertIsInstance(c, Combo, "todas las listas se crean con combo.crear_combo")
            self.assertEqual(type(c.itemDelegate()).__name__, "QStyledItemDelegate")
        combo = v.p_comparacion.cb_metrica
        v.area.ir_a(3)
        try:
            for nombre in ("claro", "oscuro"):
                v.aplicar_tema(nombre)
                sp.procesar()
                combo.showPopup()
                sp.esperar(200)
                lista = combo.view().window()
                self.assertTrue(combo.abierto)
                self.assertEqual(sp.alfa_pixel(lista, 0, 0), 0, f"{nombre}: esquina sin redondear")
                self.assertEqual(sp.color_pixel(lista, 0, lista.height() // 2), tema.color("borde_fuerte"), nombre)
                self.assertEqual(sp.color_pixel(lista, lista.width() // 2, 2), tema.color("superficie_elevada"),
                                 nombre)
                combo.hidePopup()
                sp.procesar()
                self.assertFalse(combo.abierto)
        finally:
            combo.hidePopup()
            v.aplicar_tema("claro")
            sp.procesar()

    def test_panel_de_formulas_con_borde_y_sin_sombra(self):
        from ui_qt import tema
        self._abrir_formula()
        f = self.v.formulas
        self.assertIsNone(f.graphicsEffect())
        self.assertFalse(hasattr(f, "sombra"))
        self.assertEqual(self.sp.color_pixel(f, 0, f.height() // 2), tema.color("borde"))

    # ------------------------------------------------------------------
    # Comparar k y M: chips, bloque de M y tablas largas
    # ------------------------------------------------------------------
    def test_comparar_chips_y_bloque_de_M(self):
        v, sp = self.v, self.sp
        pag = v.p_comparacion
        v.area.ir_a(3)
        sp.procesar()
        self.assertTrue(pag.tabla_M.isHidden())                   # población infinita: sin bloque vacío
        self.assertTrue(pag.info_M.isVisible())
        textos = [c.text() for c in pag.chips_k.chips]
        self.assertTrue(textos[0].startswith("Menor k que cumple"), textos)
        self.assertTrue(any(t.startswith("Mínimo por estabilidad") for t in textos), textos)
        pag.chips_k.chips[0].click()                              # chip -> fila resaltada y su fórmula
        sp.esperar(400)
        k = pag.res_k.valor_que_cumple
        self.assertEqual(v.formulas.contexto, f"k = {k}")
        fila = sp.filas_seleccionadas(pag.tabla_k.vista)
        self.assertEqual(len(fila), 1)
        self.assertEqual(int(sp.celda(pag.tabla_k.vista.model(), fila[0], 0)), k)

    def test_comparar_tabla_larga_con_barra_propia(self):
        from ui_qt import tema
        v, sp = self.v, self.sp
        pag = v.p_comparacion
        v.panel.poner("lam", "40")
        v.panel.poner("kmax", "200")
        v.calcular()
        v.area.ir_a(3)
        sp.procesar()
        vista = pag.tabla_k.vista
        filas_max = tema.LAYOUT["tabla_filas_max"]
        self.assertGreater(vista.model().rowCount(), filas_max)
        self.assertLessEqual(vista.viewport().height(), (filas_max + 1) * tema.LAYOUT["tabla_alto_fila"])
        self.assertTrue(vista.verticalScrollBar().isVisible())
        primera = pag.res_k.valor_que_cumple                      # la primera fila que cumple, a la vista
        fila = next(r for r in range(vista.model().rowCount()) if int(sp.celda(vista.model(), r, 0)) == primera)
        rect = vista.visualRect(vista.model().index(fila, 0))
        self.assertTrue(vista.viewport().rect().contains(rect))

    # ------------------------------------------------------------------
    # Gráficas: índice sin cortes
    # ------------------------------------------------------------------
    def test_indice_de_graficas_sin_cortes(self):
        from ui_qt.ventana_principal import TAMANO_MINIMO
        v, sp = self.v, self.sp
        tam = v.size()
        try:
            v.resize(*TAMANO_MINIMO)
            v.area.ir_a(4)
            sp.procesar()
            g = v.p_graficas
            texto, panel = g.ancho_indice()
            self.assertGreaterEqual(g.arbol.width(), texto)
            self.assertEqual(g.arbol.textElideMode(), sp.sin_elidir())
            self.assertGreaterEqual(g.izq.width(), panel)
            for b in g.izq.findChildren(type(g.btn_esta)):
                self.assertGreaterEqual(b.width(), b.minimumSizeHint().width(), b.text())
            g.div.moveSplitter(10, 1)                             # el divisor no lo deja más angosto
            sp.procesar()
            self.assertGreaterEqual(g.izq.width(), panel)
            pagina = v.area.pestanas.currentWidget()             # nada se corta en horizontal
            self.assertFalse(pagina.horizontalScrollBar().isVisible())
            borde = g.btn_todas.mapTo(g.izq, g.btn_todas.rect().topRight()).x()
            self.assertLess(borde, g.izq.width())
        finally:
            v.resize(tam)
            sp.procesar()


if __name__ == "__main__":
    unittest.main()
