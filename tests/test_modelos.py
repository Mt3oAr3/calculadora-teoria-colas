"""
Pruebas de las fórmulas de los modelos PICS, PICM, PFCS y PFCM.
Se comparan contra: (1) fórmulas cerradas independientes, (2) ejemplos del
apunte y (3) la referencia generada con el código original.
"""
import math
import unittest

from utilidades import cargar_referencia, cerca

from domain import modelos_colas as mc
from domain.errores import ErrorModelo


def p0_mmk_factorial(lam, mu, k):
    """P0 de M/M/k con la fórmula de libro (factoriales directos)."""
    a = lam / mu
    suma = sum(a ** n / math.factorial(n) for n in range(k))
    return 1 / (suma + a ** k / math.factorial(k) * (k * mu) / (k * mu - lam))


def p0_finita_factorial(lam, mu, k, M):
    r = lam / mu
    total = 0.0
    for n in range(M + 1):
        if n <= k:
            total += math.factorial(M) / (math.factorial(M - n) * math.factorial(n)) * r ** n
        else:
            total += math.factorial(M) / (math.factorial(M - n) * math.factorial(k) * k ** (n - k)) * r ** n
    return 1 / total


class TestReferenciaOriginal(unittest.TestCase):
    """Los casos válidos deben conservar los resultados de la versión original."""

    @classmethod
    def setUpClass(cls):
        cls.ref = cargar_referencia()

    def comparar(self, r, esperado, contexto):
        self.assertEqual(r["ok"], esperado["ok"], contexto)
        for clave, valor in esperado.items():
            if clave in ("ok", "finita"):
                continue
            if clave == "p_inicio":
                for i, (x, y) in enumerate(zip(r["p"], valor)):
                    self.assertTrue(cerca(x, y), f"{contexto} p[{i}]: {x} != {y}")
                continue
            self.assertTrue(cerca(r[clave], valor), f"{contexto} {clave}: {r[clave]} != {valor}")

    def test_infinita(self):
        for caso in self.ref["infinita"]:
            lam, mu, k = caso["entrada"]
            self.comparar(mc.resolver_infinita(lam, mu, k), caso["salida"], f"infinita {caso['entrada']}")

    def test_finita(self):
        for caso in self.ref["finita"]:
            lam, mu, k, M = caso["entrada"]
            self.comparar(mc.resolver_finita(lam, mu, k, M), caso["salida"], f"finita {caso['entrada']}")

    def test_barridos(self):
        for caso in self.ref["barrido_k"]:
            res = mc.barrido_k(*caso["entrada"])
            self.assertEqual(len(res), len(caso["salida"]))
            for r, esp in zip(res, caso["salida"]):
                self.comparar(r, esp, f"barrido_k {caso['entrada']}")
        for caso in self.ref["barrido_M"]:
            res = mc.barrido_M(*caso["entrada"])
            self.assertEqual(len(res), len(caso["salida"]))
            for r, esp in zip(res, caso["salida"]):
                self.comparar(r, esp, f"barrido_M {caso['entrada']}")


class TestPoblacionInfinita(unittest.TestCase):

    def test_mm1_formulas_cerradas(self):
        lam, mu = 10, 15
        r = mc.resolver_infinita(lam, mu, 1)
        rho = lam / mu
        self.assertAlmostEqual(r["P0"], 1 - rho)
        self.assertAlmostEqual(r["L"], rho / (1 - rho))
        self.assertAlmostEqual(r["Lq"], rho ** 2 / (1 - rho))
        self.assertAlmostEqual(r["W"], 1 / (mu - lam))
        self.assertAlmostEqual(r["Wq"], rho / (mu - lam))
        self.assertAlmostEqual(r["frac_espera"], rho)
        for n in range(10):
            self.assertAlmostEqual(r["p"][n], (1 - rho) * rho ** n)

    def test_mmk_contra_factoriales(self):
        for lam, mu, k in [(2, 3, 2), (30, 12, 6), (45, 20, 4), (9, 1, 12), (1, 4, 3)]:
            r = mc.resolver_infinita(lam, mu, k)
            P0 = p0_mmk_factorial(lam, mu, k)
            a, rho = lam / mu, lam / (k * mu)
            Lq = P0 * a ** k * rho / (math.factorial(k) * (1 - rho) ** 2)
            self.assertTrue(math.isclose(r["P0"], P0, rel_tol=1e-12))
            self.assertTrue(math.isclose(r["Lq"], Lq, rel_tol=1e-12))
            self.assertAlmostEqual(r["Wn"], 1 / (k * mu - lam))

    def test_ejemplos_del_apunte(self):
        r = mc.resolver_infinita(2, 3, 2)              # refinería
        self.assertAlmostEqual(r["P0"], 0.5)
        self.assertAlmostEqual(r["Pk"], 1 / 6)
        self.assertAlmostEqual(r["Wq"], 1 / 24)
        r = mc.resolver_infinita(30, 12, 6)            # teléfonos
        self.assertAlmostEqual(r["P0"], 0.08162, places=5)
        self.assertAlmostEqual(r["Pk"], 0.0474, places=4)

    def test_ley_de_little_y_suma_de_probabilidades(self):
        for lam, mu, k in [(10, 15, 1), (30, 12, 6), (0.99, 1, 1)]:
            r = mc.resolver_infinita(lam, mu, k)
            self.assertAlmostEqual(r["L"], lam * r["W"])
            self.assertAlmostEqual(r["Lq"], lam * r["Wq"])
            self.assertGreater(sum(r["p"]), 1 - 1e-9)
            self.assertAlmostEqual(r["ociosos"], k - lam / mu)

    def test_inestable(self):
        r = mc.resolver_infinita(3, 1, 2)
        self.assertFalse(r["ok"])
        self.assertEqual(r["k_min"], 4)

    def test_rho_igual_a_uno_es_inestable(self):
        r = mc.resolver_infinita(2, 1, 2)
        self.assertFalse(r["ok"])
        self.assertEqual(r["k_min"], 3)

    def test_rho_uno_con_redondeo_flotante(self):
        # 0.3/0.1 = 2.9999999999999996: con k = 3 el ρ real es 1 (inestable).
        # La versión original lo declaraba estable con Lq ≈ 1e15.
        r = mc.resolver_infinita(0.3, 0.1, 3)
        self.assertFalse(r["ok"])
        self.assertEqual(mc.k_minimo_estable(0.3, 0.1), 4)

    def test_k_minimo_estable(self):
        self.assertEqual(mc.k_minimo_estable(30, 12), 3)
        self.assertEqual(mc.k_minimo_estable(1, 2), 1)
        self.assertEqual(mc.k_minimo_estable(4, 2), 3)

    def test_distribucion_cubre_n_igual_k(self):
        # λ=μ=1, k=50: la masa se concentra en n pequeños. La versión original
        # truncaba p en n≈15 y P(n=k) lanzaba IndexError en la interfaz.
        r = mc.resolver_infinita(1, 1, 50)
        self.assertGreater(len(r["p"]), 51)
        esperado = r["P0"] * 1 / math.factorial(50)
        self.assertTrue(math.isclose(r["p"][50], esperado, rel_tol=1e-9))

    def test_trafico_grande_sin_desbordar(self):
        # a = 800: a^k/k! supera 1e308. La versión original devolvía NaN.
        r = mc.resolver_infinita(800, 1, 820)
        self.assertTrue(r["ok"])
        for clave in ("Lq", "L", "W", "Wq", "Pk"):
            self.assertTrue(math.isfinite(r[clave]), clave)
        self.assertAlmostEqual(r["L"], 800 * r["W"])
        self.assertGreater(sum(r["p"]), 1 - 1e-9)


class TestPoblacionFinita(unittest.TestCase):

    def test_contra_factoriales(self):
        for lam, mu, k, M in [(0.1, 0.5, 2, 4), (0.2, 1, 1, 5), (1, 1, 3, 10), (0.05, 0.3, 2, 20)]:
            r = mc.resolver_finita(lam, mu, k, M)
            self.assertTrue(math.isclose(r["P0"], p0_finita_factorial(lam, mu, k, M), rel_tol=1e-12))

    def test_ejemplo_mecanicos(self):
        r = mc.resolver_finita(0.1, 0.5, 2, 4)
        self.assertAlmostEqual(r["P0"], 0.4778, places=4)
        self.assertAlmostEqual(r["L"], 0.6896, places=4)

    def test_ley_de_little_y_lambda_efectiva(self):
        for lam, mu, k, M in [(0.1, 0.5, 2, 4), (1, 1, 3, 10), (0.2, 1, 1, 5)]:
            r = mc.resolver_finita(lam, mu, k, M)
            self.assertAlmostEqual(sum(r["p"]), 1.0)
            self.assertAlmostEqual(r["lam_ef"], lam * (M - r["L"]))
            self.assertAlmostEqual(r["L"], r["lam_ef"] * r["W"])
            self.assertAlmostEqual(r["Lq"], r["lam_ef"] * r["Wq"])
            self.assertAlmostEqual(r["operando"], M - r["L"])

    def test_k_mayor_que_M_equivale_a_k_igual_M(self):
        a = mc.resolver_finita(0.1, 0.5, 7, 4)
        b = mc.resolver_finita(0.1, 0.5, 4, 4)
        self.assertEqual(a["k_ef"], 4)
        self.assertEqual(a["k"], 7)
        for clave in ("P0", "L", "Lq", "W", "Wq", "ociosos"):
            self.assertAlmostEqual(a[clave], b[clave])
        self.assertEqual(a["Lq"], 0.0)
        self.assertTrue(math.isnan(a["Ln"]))      # no puede haber cola: Ln no aplica
        self.assertTrue(math.isnan(a["Wn"]))

    def test_poblacion_de_uno(self):
        lam, mu = 2, 1
        r = mc.resolver_finita(lam, mu, 1, 1)
        self.assertAlmostEqual(r["P0"], mu / (lam + mu))
        self.assertAlmostEqual(r["W"], 1 / mu)
        self.assertEqual(r["Wq"], 0.0)

    def test_M_grande_sin_desbordar(self):
        # Con M = 300 los términos superan 1e308. La versión original devolvía L = NaN.
        r = mc.resolver_finita(0.1, 0.5, 2, 300)
        for clave in ("P0", "L", "Lq", "W", "Wq", "lam_ef"):
            self.assertTrue(math.isfinite(r[clave]), clave)
        self.assertAlmostEqual(sum(r["p"]), 1.0)
        self.assertTrue(0 < r["L"] < 300)
        self.assertAlmostEqual(r["L"], r["lam_ef"] * r["W"])
        # Con M grande la λ total M·λ ≫ kμ: los servidores quedan saturados.
        self.assertAlmostEqual(r["util"], 1.0, places=6)

    def test_cociente_fuera_de_rango(self):
        with self.assertRaises(ErrorModelo):
            mc.resolver_finita(1e308, 1e-10, 1, 5)
        with self.assertRaises(ErrorModelo):
            mc.resolver_infinita(1e-300, 1e300, 1)


class TestParametrosInvalidos(unittest.TestCase):

    def test_tasas_invalidas(self):
        for lam, mu in [(0, 1), (-1, 1), (1, 0), (1, -2), (float("nan"), 1), (1, float("inf"))]:
            with self.assertRaises(ValueError):
                mc.resolver_infinita(lam, mu, 1)
            with self.assertRaises(ValueError):
                mc.resolver_finita(lam, mu, 1, 3)

    def test_servidores_y_poblacion_invalidos(self):
        for k in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                mc.resolver_infinita(1, 2, k)
        for M in (0, -3, 2.5, None):
            with self.assertRaises(ValueError):
                mc.resolver_finita(1, 2, 1, M)

    def test_resolver_finita_sin_M(self):
        with self.assertRaises(ValueError):
            mc.resolver(1, 2, 1, finita=True, M=None)


class TestProbabilidadesDerivadas(unittest.TestCase):

    def fuerza_bruta(self, r, conjunto):
        return sum(pn for n, pn in enumerate(r["p"]) if conjunto(n))

    def test_rango_contra_definicion(self):
        for r in (mc.resolver_infinita(30, 12, 6), mc.resolver_finita(0.1, 0.5, 2, 6)):
            kk = r["k_ef"]
            for a, b in [(0, 0), (0, 3), (2, 3), (1, 5)]:
                filas = {s: v for s, _, v in mc.probabilidades_rango(r, a, b)}
                fb = lambda c: self.fuerza_bruta(r, c)  # noqa: E731
                self.assertAlmostEqual(filas[f"P(n = {a})"], fb(lambda n: n == a))
                self.assertAlmostEqual(filas[f"P(n ≤ {a})"], fb(lambda n: n <= a))
                self.assertAlmostEqual(filas[f"P(n ≥ {a})"], fb(lambda n: n >= a), places=9)
                self.assertAlmostEqual(filas[f"P(n > {a})"], fb(lambda n: n > a), places=9)
                self.assertAlmostEqual(filas[f"P({a} ≤ n ≤ {b})"], fb(lambda n: a <= n <= b))
                cola = lambda n: max(0, n - kk)  # noqa: E731
                self.assertAlmostEqual(filas[f"P(cola = {a})"], fb(lambda n: cola(n) == a))
                self.assertAlmostEqual(filas[f"P(cola ≥ {a})"], fb(lambda n: cola(n) >= a), places=9)
                self.assertAlmostEqual(filas[f"P(cola > {a})"], fb(lambda n: cola(n) > a), places=9)
                self.assertAlmostEqual(filas[f"P(cola ≤ {a})"], fb(lambda n: cola(n) <= a))
                self.assertAlmostEqual(filas[f"P({a} ≤ cola ≤ {b})"], fb(lambda n: a <= cola(n) <= b))

    def test_rango_invalido(self):
        r = mc.resolver_infinita(10, 15, 1)
        for a, b in [(-1, 2), (3, 2), (1.5, 2)]:
            with self.assertRaises(ValueError):
                mc.probabilidades_rango(r, a, b)

    def test_distribucion(self):
        r = mc.resolver_finita(0.1, 0.5, 2, 4)
        filas = mc.distribucion(r)
        self.assertEqual([f[0] for f in filas], [0, 1, 2, 3, 4])
        self.assertEqual([f[1] for f in filas], [0, 0, 0, 1, 2])
        self.assertAlmostEqual(filas[-1][3], 1.0)
        self.assertAlmostEqual(filas[0][4], 1.0)
        filas = mc.distribucion(mc.resolver_infinita(10, 15, 1))
        self.assertGreaterEqual(filas[-1][0], 3)        # al menos hasta k + 2
        self.assertLessEqual(filas[-1][0], 150)

    def test_nombre_modelo(self):
        self.assertEqual(mc.nombre_modelo(False, 1), ("PICS", "M/M/1"))
        self.assertEqual(mc.nombre_modelo(False, 3), ("PICM", "M/M/3"))
        self.assertEqual(mc.nombre_modelo(True, 1), ("PFCS", "M/M/1/M/M"))
        self.assertEqual(mc.nombre_modelo(True, 2, 4), ("PFCM", "M/M/2/4/4"))


if __name__ == "__main__":
    unittest.main()
