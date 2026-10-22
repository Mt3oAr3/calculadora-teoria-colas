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
        cls.v.close()
        cls.v.deleteLater()
        cls.sp.procesar()

    def setUp(self):
        self.v.formulas.cerrar()
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

    def test_panel_no_cambia_el_ancho_de_la_tabla(self):
        tabla = self.v.p_resultados.tabla.vista
        tarjetas = self.v.p_resultados.tarjetas
        antes = (tabla.width(), [tabla.columnWidth(c) for c in range(tabla.model().columnCount())],
                 tarjetas.width())
        self._abrir_formula()
        despues = (tabla.width(), [tabla.columnWidth(c) for c in range(tabla.model().columnCount())],
                   tarjetas.width())
        self.assertEqual(antes, despues)
        # superpuesto al borde derecho del área de resultados, con ancho ≈ 40 %
        area = self.v.area
        geo = self.v.formulas.geometry()
        self.assertEqual(geo.right(), area.rect().right())
        self.assertLessEqual(abs(geo.width() - 0.40 * area.width()), 0.05 * area.width() + 1)

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

    def test_sombra_del_panel(self):
        self._abrir_formula()
        f = self.v.formulas
        self.assertIsNone(f.graphicsEffect())                 # sin efecto: nada se redibuja fuera de pantalla
        s = f.sombra
        self.assertTrue(s.isVisible())
        self.assertEqual(s.geometry().right() + 1, f.geometry().left())
        self.assertEqual(s.height(), f.height())
        self.assertGreater(s.width(), 20)


if __name__ == "__main__":
    unittest.main()
