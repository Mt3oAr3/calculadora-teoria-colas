"""Pruebas de la comparación de escenarios en función de k y de M."""
import unittest

import utilidades  # noqa: F401

from domain import costos as dc
from domain.errores import ErrorEntrada
from services import calculadora_service as cs
from services import comparacion_service as cmp
from services.tablas import Formateador


def escenario(**cambios):
    d = dict(cs.VALORES_INICIALES)
    d.update({k: str(v) for k, v in cambios.items()})
    return cs.calcular_escenario(cs.leer_parametros(d))


class TestCondicion(unittest.TestCase):

    def test_leer_condicion(self):
        c = cmp.leer_condicion("Wq (tiempo en cola)", "≤", "0,5", "minuto")
        self.assertEqual(c.limite, 0.5)
        self.assertIn("min", c.describir())

    def test_condicion_invalida_es_error_explicito(self):
        # La versión original trataba un límite inválido como «no cumple» en silencio.
        for args in (("Wq (tiempo en cola)", "≤", "abc"), ("Wq (tiempo en cola)", "<", "1"),
                     ("No existe", "≤", "1"), ("Lq (clientes en cola)", "≤", "inf")):
            with self.assertRaises(ErrorEntrada):
                cmp.leer_condicion(*args, "minuto")

    def test_metrica_de_tiempo_en_unidad_elegida(self):
        esc = escenario()                           # M/M/1, Wq = 0,1333 h = 8 min
        r = esc.r
        cond_min = cmp.leer_condicion("Wq (tiempo en cola)", "≤", "8.01", "minuto")
        cond_h = cmp.leer_condicion("Wq (tiempo en cola)", "≤", "8.01", "hora")
        self.assertTrue(cmp.cumple(r, cond_min, esc.p))
        self.assertTrue(cmp.cumple(r, cond_h, esc.p))
        self.assertFalse(cmp.cumple(r, cmp.leer_condicion("Wq (tiempo en cola)", "≤", "7.9", "minuto"), esc.p))

    def test_metrica_solo_finita_no_cumple_en_infinita(self):
        esc = escenario()
        cond = cmp.leer_condicion("Fracción de unidades operando (finita)", "≥", "0", "minuto")
        self.assertFalse(cmp.cumple(esc.r, cond, esc.p))


class TestComparacionK(unittest.TestCase):

    def test_infinita_empieza_en_k_estable(self):
        esc = escenario(lam="40", kmax="6")        # λ/μ = 40/15 → k mínimo 3
        cond = cmp.leer_condicion("Probabilidad de esperar", "≤", "0.2", "minuto")
        res = cmp.comparar_k(esc, cond, Formateador())
        ks = [f.celdas[0].dato for f in res.tabla.filas]
        self.assertEqual(ks[0], 3)
        self.assertEqual(ks[-1], 7)                 # max(kmax, k_min + 4)
        self.assertIn("Mínimo por estabilidad: k = 3", res.resumen)
        # El primer k que cumple es el menor k con P(esperar) ≤ 0,2
        cumplen = [f.celdas[0].dato for f in res.tabla.filas if "ok" in f.etiquetas]
        self.assertEqual(res.valor_que_cumple, cumplen[0])
        for f in res.tabla.filas:
            self.assertEqual("ok" in f.etiquetas, f.celdas[4].dato <= 0.2 + 1e-12)

    def test_menor_costo(self):
        esc = escenario(lam="40", cS="200", cW="30", kmax="8")
        cond = cmp.leer_condicion("Costo total diario CT", "≤", "1e9", "minuto")
        res = cmp.comparar_k(esc, cond, Formateador())
        cts = {r["k"]: dc.costos(r, esc.p.H, esc.p.cfg)["ct"] for r in esc.barrido_k}
        self.assertEqual(res.k_menor_costo, min(cts, key=cts.get))
        mejores = [f for f in res.tabla.filas if "mejor" in f.etiquetas]
        self.assertEqual(len(mejores), 1)

    def test_sin_costos_no_hay_mejor(self):
        res = cmp.comparar_k(escenario(), cmp.leer_condicion("L (clientes en el sistema)", "≤", "1", "hora"),
                             Formateador())
        self.assertIsNone(res.k_menor_costo)

    def test_columna_operando_solo_en_finita(self):
        cond = cmp.leer_condicion("L (clientes en el sistema)", "≤", "1", "hora")
        inf = cmp.comparar_k(escenario(), cond, Formateador())
        fin = cmp.comparar_k(escenario(poblacion="Finita", M="5", k="2"), cond, Formateador())
        self.assertNotIn("% operando", inf.tabla.encabezados)
        self.assertIn("% operando", fin.tabla.encabezados)
        self.assertEqual([f.celdas[0].dato for f in fin.tabla.filas], [1, 2, 3, 4, 5])


class TestComparacionM(unittest.TestCase):

    def test_mayor_M_que_cumple(self):
        esc = escenario(poblacion="Finita", k="2", M="4", lam_modo=cs.MODO_LAM[0], lam="0.1",
                        lam_u="hora", mu_modo=cs.MODO_MU[0], mu="0.5", mu_u="hora", Mmax="20")
        cond = cmp.leer_condicion("Probabilidad de esperar", "≤", "0.3", "minuto")
        res = cmp.comparar_M(esc, cond, Formateador())
        cumplen = [f.celdas[0].dato for f in res.tabla.filas if "ok" in f.etiquetas]
        self.assertEqual(res.valor_que_cumple, max(cumplen))
        actual = [f.celdas[0].dato for f in res.tabla.filas if "actual" in f.etiquetas]
        self.assertEqual(actual, [4])

    def test_infinita_no_aplica(self):
        res = cmp.comparar_M(escenario(), cmp.leer_condicion("L (clientes en el sistema)", "≤", "1", "hora"),
                             Formateador())
        self.assertEqual(res.tabla.filas, [])
        self.assertIn("solo para población finita", res.resumen)


if __name__ == "__main__":
    unittest.main()
