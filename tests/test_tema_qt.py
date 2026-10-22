"""
Cambio de tema coherente: tras cada cambio claro ⇄ oscuro, los colores que se PINTAN en una
muestra de widgets (ventana, barra superior, tarjeta, tabla, banner, panel de fórmulas y
gráfica) son los de los tokens del tema activo; ninguno conserva el anterior.
Se omite si PySide6 no está instalado.
"""
import importlib.util
import unittest

import utilidades  # noqa: F401  (agrega la raíz del proyecto al path)

HAY_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAY_QT, "PySide6 no está instalado")
class TestTemaQt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from ui_qt import soporte_pruebas as sp
        from ui_qt import tema
        cls.sp, cls.tema = sp, tema
        sp.aplicacion()
        from ui_qt.ventana_principal import VentanaPrincipal
        cls.Ventana = VentanaPrincipal
        cls.v = VentanaPrincipal("claro")
        cls.v.resize(1366, 768)
        cls.v.show()
        for clave, valor in dict(k="3", lam="28", cS="50", cW="20").items():
            cls.v.panel.poner(clave, valor)
        cls.v.calcular()
        sp.esperar(300)

    @classmethod
    def tearDownClass(cls):
        cls.v.formulas.cerrar()
        cls.v.aplicar_tema("claro")
        cls.v.close()
        cls.v.deleteLater()
        cls.sp.procesar()

    def muestra(self, v):
        """{elemento: (color pintado, token esperado)} del estado actual de la ventana."""
        sp, t = self.sp, self.tema
        tarjeta = v.p_resultados.tarjetas.tarjetas[0]
        vista = v.p_resultados.tabla.vista
        return {
            "ventana (fondo del área)": (sp.color_pixel(v.area, 3, 3), t.color("fondo")),
            "barra superior": (sp.color_pixel(v.barra, 2, 2), t.color("barra")),
            "tarjeta (fondo)": (sp.color_pixel(tarjeta, 5, tarjeta.height() // 2), t.color("superficie")),
            "tarjeta (texto del valor)": (sp.color_texto(tarjeta.valor), t.color("texto")),
            "tabla (fondo fila 0)": (sp.color_pixel(vista.viewport(), vista.viewport().width() - 3, 5),
                                     t.color("tabla_fondo")),
            "tabla (texto)": (sp.color_texto(vista), t.color("texto")),
            "encabezado del modelo (texto)": (sp.color_texto(v.area.encabezado.lbl_modelo), t.color("texto")),
        }

    def comprobar(self, v, nombre):
        self.assertEqual(self.tema.actual(), nombre)
        for elemento, (pintado, esperado) in self.muestra(v).items():
            self.assertEqual(pintado, esperado.lower()[:7], f"{nombre}: {elemento}")

    def test_alternar_varias_veces(self):
        v, sp, t = self.v, self.sp, self.tema
        v.area.ir_a(0)
        for nombre in ("oscuro", "claro", "oscuro", "claro"):
            v.aplicar_tema(nombre)
            sp.procesar()
            self.comprobar(v, nombre)

    def test_banner_y_panel_de_formulas_siguen_al_tema(self):
        v, sp, t = self.v, self.sp, self.tema
        v.area.ir_a(0)
        v.mostrar_formula("Lq")
        v.panel.poner("k", "4")                            # muestra el banner
        sp.esperar(500)
        try:
            for nombre in ("oscuro", "claro", "oscuro"):
                v.aplicar_tema(nombre)
                sp.procesar()
                b, f = v.banner, v.formulas
                self.assertEqual(sp.color_pixel(b, b.width() - 3, 3), t.color("advertencia_fondo"), nombre)
                self.assertEqual(sp.color_texto(b.texto), t.color("advertencia_texto"), nombre)
                self.assertEqual(sp.color_pixel(f, f.width() - 4, f.height() - 4), t.color("superficie_elevada"),
                                 nombre)
                self.assertEqual(sp.color_texto(f.btn_cerrar), t.color("texto"), nombre)
                # las ecuaciones se regeneran con el texto del tema (no quedan pixmaps del anterior)
                self.assertTrue(f._imagenes)
                self.assertTrue(all(img._color == t.color("texto") for img in f._imagenes), nombre)
        finally:
            v.formulas.cerrar()
            v.calcular()
            sp.esperar(300)

    def test_grafica_sigue_al_tema(self):
        v, sp, t = self.v, self.sp, self.tema
        pag = v.p_graficas
        for nombre in ("oscuro", "claro", "oscuro"):
            v.area.ir_a(0)                                 # la gráfica no está a la vista: queda pendiente
            v.aplicar_tema(nombre)
            sp.procesar()
            self.assertTrue(pag.pendiente, nombre)
            v.area.ir_a(4)                                 # al abrir la pestaña se redibuja
            sp.esperar(200)
            self.assertFalse(pag.pendiente, nombre)
            self.assertEqual(sp.color_figura(pag.fig), t.color("grafica_fondo"), nombre)
            self.assertEqual(sp.color_pixel(pag.canvas, 3, 3), t.color("grafica_fondo"), nombre)
        # con la pestaña a la vista se redibuja en el mismo cambio
        v.aplicar_tema("claro")
        sp.procesar()
        self.assertFalse(pag.pendiente)
        self.assertEqual(sp.color_figura(pag.fig), t.color("grafica_fondo"))

    def test_arranque_en_oscuro_sin_pasar_por_claro(self):
        sp, t = self.sp, self.tema
        espia = sp.espiar_ventanas()
        v2 = self.Ventana("oscuro")
        v2.resize(1366, 768)
        try:
            self.assertEqual(t.actual(), "oscuro")         # tema aplicado ANTES de mostrar
            v2.show()
            sp.procesar()
            self.comprobar(v2, "oscuro")
            self.assertEqual(espia.mostradas, [v2])
        finally:
            espia.detener()
            v2.close()
            v2.deleteLater()
            sp.procesar()
            self.v.aplicar_tema("claro")
            sp.procesar()

    def test_barra_de_titulo_sin_errores_fuera_de_windows_nativo(self):
        from ui_qt.barra_titulo import aplicar_barra_titulo
        self.assertFalse(aplicar_barra_titulo(self.v, True))   # offscreen: fallback silencioso


if __name__ == "__main__":
    unittest.main()
