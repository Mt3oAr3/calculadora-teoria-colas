"""Pruebas de conversión de unidades."""
import math
import unittest

from utilidades import cargar_referencia, cerca

from domain import unidades as du


class TestUnidades(unittest.TestCase):

    def test_referencia_original(self):
        for caso in cargar_referencia()["unidades"]:
            es_tasa, valor, u, H = caso["entrada"]
            self.assertTrue(cerca(du.tasa_por_hora(es_tasa, valor, u, H), caso["salida"]), caso)

    def test_tasas(self):
        self.assertAlmostEqual(du.tasa_por_hora(True, 30, "hora", 8), 30)
        self.assertAlmostEqual(du.tasa_por_hora(True, 2, "minuto", 8), 120)
        self.assertAlmostEqual(du.tasa_por_hora(True, 16, "día", 8), 2)

    def test_tiempos(self):
        self.assertAlmostEqual(du.tasa_por_hora(False, 4, "minuto", 8), 15)
        self.assertAlmostEqual(du.tasa_por_hora(False, 0.5, "hora", 8), 2)
        # "Cada 4 días" con 8 h/día = un cliente cada 32 horas de operación.
        self.assertAlmostEqual(du.tasa_por_hora(False, 4, "día", 8), 1 / 32)

    def test_horas_a_unidad(self):
        self.assertAlmostEqual(du.horas_a_unidad(0.25, "minuto", 8), 15)
        self.assertAlmostEqual(du.horas_a_unidad(4, "día", 8), 0.5)
        self.assertAlmostEqual(du.horas_a_unidad(3, "hora", 8), 3)

    def test_valores_invalidos(self):
        for valor in (0, -1, None, math.nan, math.inf):
            with self.assertRaises(ValueError):
                du.tasa_por_hora(True, valor, "hora", 8)

    def test_unidad_desconocida(self):
        with self.assertRaises(ValueError):
            du.horas_por_unidad("semana", 8)

    def test_horas_por_dia_invalidas(self):
        for H in (0, -8, math.nan):
            with self.assertRaises(ValueError):
                du.horas_por_unidad("día", H)
        # Minuto y hora no dependen de H
        self.assertAlmostEqual(du.horas_por_unidad("minuto", 0), 1 / 60)


if __name__ == "__main__":
    unittest.main()
