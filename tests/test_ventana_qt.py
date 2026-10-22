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
