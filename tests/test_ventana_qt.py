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

    def test_nota_sin_costos(self):
        nota = self.v.p_costos.nota
        self.v.area.ir_a(2)
        self.sp.procesar()
        self.assertTrue(nota.isVisible())                  # valores iniciales: todo en 0
        self.v.panel.poner("cW", "5")
        self.v.calcular()
        self.sp.procesar()
        self.assertFalse(nota.isVisible())


if __name__ == "__main__":
    unittest.main()
