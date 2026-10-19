"""Pruebas de costos, ingresos e indicadores diarios."""
import math
import unittest

from utilidades import cargar_referencia, cerca

from domain import costos as dc
from domain import modelos_colas as mc


class TestCostos(unittest.TestCase):

    def test_referencia_original(self):
        ref = cargar_referencia()
        for caso in ref["costos"]:
            r = mc.resolver(*caso["entrada"])
            c = dc.costos(r, caso["H"], ref["cfgs"][caso["cfg"]])
            for clave, valor in caso["salida"].items():
                self.assertTrue(cerca(c[clave], valor), f"{caso} {clave}: {c[clave]} != {valor}")

    def test_calculo_manual(self):
        # M/M/1 con λ=10/h, μ=15/h: Lq = 4/3, L = 2, ociosos = 1/3.
        r = mc.resolver_infinita(10, 15, 1)
        cfg = dc.configuracion_costos(c_servidor=10, c_servidor_u="hora", c_espera=0.5,
                                      c_espera_u="minuto", base_espera="Lq", c_ocio=6,
                                      ingreso=2, frac_ingreso=0.5)
        c = dc.costos(r, 8, cfg)
        self.assertAlmostEqual(c["ct_s"], 1 * 10 * 8)
        self.assertAlmostEqual(c["ct_te"], 4 / 3 * 8 * 30)          # 0,5 $/min = 30 $/h
        self.assertAlmostEqual(c["ct_ocio"], 1 / 3 * 8 * 6)
        self.assertAlmostEqual(c["ct"], c["ct_s"] + c["ct_te"] + c["ct_ocio"])
        self.assertAlmostEqual(c["ingreso"], 10 * 8 * 0.5 * 2)
        self.assertAlmostEqual(c["rentabilidad"], c["ingreso"] / c["ct"])

    def test_base_L(self):
        r = mc.resolver_infinita(10, 15, 1)
        cfg = dc.configuracion_costos(c_espera=1, c_espera_u="hora", base_espera="L")
        self.assertAlmostEqual(dc.costos(r, 10, cfg)["ct_te"], 2 * 10)

    def test_sin_costos_rentabilidad_no_definida(self):
        r = mc.resolver_infinita(10, 15, 1)
        c = dc.costos(r, 8, dc.configuracion_costos())
        self.assertEqual(c["ct"], 0)
        self.assertTrue(math.isnan(c["rentabilidad"]))

    def test_finita_cobra_k_contratados(self):
        # Con k > M se pagan los k servidores aunque solo trabajen M a la vez.
        r = mc.resolver_finita(0.1, 0.5, 5, 4)
        c = dc.costos(r, 8, dc.configuracion_costos(c_servidor=100))
        self.assertAlmostEqual(c["ct_s"], 500)

    def test_ingreso_usa_lambda_efectiva(self):
        r = mc.resolver_finita(0.1, 0.5, 2, 4)
        c = dc.costos(r, 8, dc.configuracion_costos(ingreso=10))
        self.assertAlmostEqual(c["ingreso"], r["lam_ef"] * 8 * 10)

    def test_configuracion_invalida(self):
        for kwargs in ({"c_servidor": -1}, {"c_espera": math.nan}, {"c_ocio": -0.1},
                       {"ingreso": -5}, {"frac_ingreso": 1.5}, {"frac_ingreso": -0.1},
                       {"c_servidor_u": "minuto"}, {"base_espera": "W"}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                dc.configuracion_costos(**kwargs)


class TestIndicadoresDiarios(unittest.TestCase):

    def test_horas_por_estado(self):
        r = mc.resolver_infinita(30, 12, 6)
        H = 8
        horas = dict(dc.horas_por_estado(r, H))
        self.assertAlmostEqual(horas["Todos los servidores desocupados a la vez (P0)"], r["P0"] * H)
        ocio = horas["Horas de ocio sumadas de todos los servidores"]
        trabajo = horas["Horas de trabajo sumadas de todos los servidores"]
        self.assertAlmostEqual(ocio + trabajo, 6 * H)
        self.assertAlmostEqual(horas["Uno o varios servidores desocupados (P(n<k))"]
                               + horas["Todos los servidores ocupados (P(n≥k))"], H)

    def test_clientes_por_dia(self):
        r = mc.resolver_finita(0.1, 0.5, 2, 4)
        filas = dict(dc.clientes_por_dia(r, 8))
        self.assertAlmostEqual(filas["Clientes que llegan"], r["lam_ef"] * 8)
        self.assertAlmostEqual(filas["Clientes que deben esperar"] + filas["Clientes atendidos en cuanto llegan"],
                               filas["Clientes que llegan"])


if __name__ == "__main__":
    unittest.main()
