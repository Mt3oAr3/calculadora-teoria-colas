"""
Pruebas de services/formulas.py («Cómo se calculó»): el resultado que muestra
cada fórmula es el valor del dominio, para todos los modelos, y el mathtext es válido.
"""
import math
import unittest

import utilidades  # noqa: F401  (agrega la raíz del proyecto al path)

import matplotlib
matplotlib.use("Agg")
from matplotlib.mathtext import MathTextParser  # noqa: E402

from domain import costos as dc  # noqa: E402
from domain import modelos_colas as mc  # noqa: E402
from services import calculadora_service as cs  # noqa: E402
from services import comparacion_service as cmp  # noqa: E402
from services import formulas as fm  # noqa: E402
from services.tablas import Formateador  # noqa: E402

TASA, TIEMPO = cs.MODO_LAM[0], cs.MODO_LAM[1]
SERVICIO = cs.MODO_MU[1]


def escenario(**cambios):
    d = dict(cs.VALORES_INICIALES)
    d.update({k: str(v) for k, v in cambios.items()})
    return cs.calcular_escenario(cs.leer_parametros(d))


# Un escenario de cada modelo, con costos, ociosidad, ingresos y S > 1 para cubrir todas las fórmulas.
ESCENARIOS = {
    "M/M/1": dict(cS=10, cS_u="hora", cW=50, cI=5, ing=3, ingF=0.8),
    "M/M/3 con S=2": dict(k=3, S=2, lam=30, mu=5, cS=100, cW=20, cW_u="día", cI=2, ing=1),
    "M/M/1/5/5": dict(poblacion="Finita", k=1, M=5, lam=0.1, mu=0.5, mu_modo=cs.MODO_MU[0], mu_u="hora",
                      cS=50, cW=8, cW_b="L (espera + servicio)", ing=10),
    "M/M/2/6/6 con S=3": dict(poblacion="Finita", k=2, M=6, S=3, lam=0.3, mu=1, mu_modo=cs.MODO_MU[0],
                              mu_u="hora", cS=40, cW=15, cI=3),
    "finita con k > M": dict(poblacion="Finita", k=4, M=3, lam=1, mu=2, mu_modo=cs.MODO_MU[0], mu_u="hora"),
}

# columna con el valor de cada tabla
TABLAS = [(cs.tabla_resultados, 2), (lambda e: cs.tabla_probabilidades(e, 2, 3), 1),
          (lambda e: cs.tabla_probabilidades(e, 0, 1), 1), (cs.tabla_distribucion, 2),
          (cs.tabla_por_dia, 1), (cs.tabla_costos, 1)]


def esperado(esc, clave):
    """Valor del dominio para cada clave, obtenido directamente del escenario o del dominio."""
    r, p = esc.r, esc.p
    if clave in esc.costos:
        return esc.costos[clave]
    directos = {"rho": "util", "Pw": "frac_espera"}
    if clave in directos:
        return r[directos[clave]]
    if clave in ("S_Lq", "S_L"):
        return p.S * r[clave[2:]]
    if clave in r:
        return r[clave]
    nombre, _, resto = clave.partition(":")
    args = [int(x) for x in resto.split(":")]
    if nombre in ("Pn", "dist"):
        return r["p"][args[0]]
    if nombre == "prob":
        return mc.probabilidades_rango(r, args[1], args[2])[args[0]][2]
    if nombre == "horas":
        return dc.horas_por_estado(r, p.H)[args[0]][1]
    if nombre == "clientes":
        return dc.clientes_por_dia(r, p.H)[args[0]][1]
    if nombre == "sistemas":
        return dc.totales_sistemas(r, p.H, p.S)[args[0]][1]
    raise AssertionError(f"clave sin valor esperado: {clave}")


def cerca(a, b):
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)


class TestFormulas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = MathTextParser("path")

    def assertMathtext(self, texto, contexto):
        try:
            self.parser.parse(f"${texto}$")
        except ValueError as e:
            self.fail(f"{contexto}: mathtext inválido «{texto}»: {e}")

    def revisar(self, f, esc, fmt, contexto):
        self.assertTrue(f.titulo and f.explicacion, contexto)
        self.assertTrue(f.pasos, contexto)
        for t in (f.latex,) + f.pasos:
            self.assertMathtext(t, contexto)
        self.assertNotEqual(fmt.texto(f.resultado), "", contexto)
        for extra in f.extras:
            self.revisar(extra, esc, fmt, contexto + " / " + extra.clave)

    def test_resultado_es_el_del_dominio_en_todas_las_filas(self):
        for nombre, cambios in ESCENARIOS.items():
            esc = escenario(**cambios)
            fmt = Formateador(4, "minuto", esc.p.H)
            claves = {ind.clave for ind in cs.indicadores_principales(esc)}
            for hacer_tabla, col in TABLAS:
                for fila in hacer_tabla(esc).filas:
                    self.assertIsNotNone(fila.clave, f"{nombre}: fila sin clave {fila.celdas[0]}")
                    f = fm.formula(esc, fila.clave, fmt)
                    ctx = f"{nombre} · {fila.clave}"
                    # lo que muestra la fórmula = lo que muestra la tabla = valor del dominio
                    self.assertTrue(cerca(f.resultado.dato, fila.celdas[col].dato), ctx)
                    self.assertTrue(cerca(f.resultado.dato, esperado(esc, fila.clave)), ctx)
                    self.revisar(f, esc, fmt, ctx)
                    claves.discard(fila.clave)
            for clave in claves:     # tarjetas que no estuvieran en las tablas
                f = fm.formula(esc, clave, fmt)
                self.assertTrue(cerca(f.resultado.dato, esperado(esc, clave)), f"{nombre} · {clave}")

    def test_formula_cambia_segun_modelo(self):
        fmt = Formateador()
        mm1 = fm.formula(escenario(), "Lq", fmt).latex
        mmk = fm.formula(escenario(k=2), "Lq", fmt).latex
        fin = fm.formula(escenario(poblacion="Finita", k=2, M=4, lam=0.1, mu=0.5, mu_modo=cs.MODO_MU[0],
                                   mu_u="hora"), "Lq", fmt).latex
        self.assertIn(r"\rho^2", mm1)
        self.assertIn("a^k", mmk)
        self.assertIn(r"\sum", fin)
        self.assertEqual(len({mm1, mmk, fin}), 3)
        self.assertIn("Erlang", fm.formula(escenario(k=2), "Pw", fmt).titulo)

    def test_acumuladas_de_la_distribucion(self):
        esc = escenario(k=2)
        f = fm.formula(esc, "dist:3", Formateador())
        filas = {fila[0]: fila for fila in mc.distribucion(esc.r)}
        self.assertEqual(len(f.extras), 2)
        self.assertTrue(cerca(f.extras[0].resultado.dato, filas[3][3]))     # P(n ≤ 3)
        self.assertTrue(cerca(f.extras[1].resultado.dato, filas[3][4]))     # P(n ≥ 3)

    def test_tiempos_y_costos_usan_unidades(self):
        esc = escenario(cS=10, cW=40, cW_u="día", H=8)
        fmt = Formateador(4, "minuto", esc.p.H)
        wq = fm.formula(esc, "Wq", fmt)
        self.assertEqual(wq.resultado.tipo, "tiempo")
        self.assertIn(r"\mathrm{min}", wq.pasos[-1])
        te = fm.formula(esc, "ct_te", fmt)
        self.assertEqual(len(te.pasos), 2)          # conversión del costo por día a por hora
        self.assertTrue(cerca(te.resultado.dato, esc.costos["ct_te"]))
        self.assertEqual(len(fm.formula(esc, "ct", fmt).extras), 3)

    def test_no_disponible(self):
        fmt = Formateador()
        with self.assertRaises(fm.FormulaNoDisponible):
            fm.formula(escenario(lam=20, mu=4), "Lq", fmt)          # inestable (ρ = 1,33)
        with self.assertRaises(fm.FormulaNoDisponible):
            fm.formula(escenario(), "operando", fmt)                 # solo finita
        with self.assertRaises(fm.FormulaNoDisponible):
            fm.formula(escenario(), "sistemas:0", fmt)               # S = 1
        for clave in ("xyz", "Pn:a", "Pn:-1", "prob:1", "dist:99999"):
            with self.assertRaises(fm.FormulaNoDisponible, msg=clave):
                fm.formula(escenario(), clave, fmt)


class TestCasosDeAceptacion(unittest.TestCase):
    """Ejercicios de la materia: los valores que muestran las fórmulas."""

    def valores(self, **cambios):
        esc = escenario(**cambios)
        fmt = Formateador(4, "minuto", esc.p.H)
        return lambda clave: fm.formula(esc, clave, fmt).resultado.dato

    def test_ej4(self):
        base = dict(lam_modo=TIEMPO, lam=4, lam_u="minuto", mu_modo=SERVICIO, mu=3.33, mu_u="minuto",
                    cS=0, cI=250, cW=400, cW_u="hora", H=1)
        v = self.valores(**base)
        self.assertAlmostEqual(v("rho"), 0.8325, places=4)
        self.assertAlmostEqual(v("Lq"), 4.1376, places=4)
        self.assertAlmostEqual(v("Wq") * 60, 16.55, places=2)
        self.assertAlmostEqual(v("ct"), 1696.93, places=2)
        v2 = self.valores(k=2, **base)
        self.assertAlmostEqual(v2("Lq"), 0.1745, places=4)
        self.assertAlmostEqual(v2("ct"), 361.66, places=2)

    def test_ej9(self):
        base = dict(lam_modo=TIEMPO, lam=10, lam_u="día", mu_modo=TASA, mu=2 / 15, mu_u="día", H=8,
                    cS=150, cS_u="día", cW=275, cW_u="día")
        for k, ct in ((1, 768.75), (2, 333.75), (3, 454.04)):
            self.assertAlmostEqual(self.valores(k=k, **base)("ct"), ct, places=2)

    def test_ej18(self):
        v = self.valores(S=2, k=1, lam_modo=TASA, lam=30, lam_u="hora", mu_modo=SERVICIO, mu=1, mu_u="minuto",
                         H=10, cS=10, cS_u="hora", cW=50, cW_u="hora")
        self.assertAlmostEqual(v("ct"), 700, places=6)
        self.assertAlmostEqual(v("S_Lq"), 1, places=9)
        self.assertAlmostEqual(v("sistemas:1"), 10, places=9)          # horas-caja ociosas

    def test_ej22(self):
        v = self.valores(k=5, lam_modo=TIEMPO, lam=3, lam_u="minuto", mu_modo=SERVICIO, mu=10, mu_u="minuto",
                         H=6, cS=100, cS_u="día", cW=10, cW_u="hora", ing=50, ingF=0.87)
        self.assertAlmostEqual(v("Pw"), 0.3267, places=4)
        self.assertAlmostEqual(v("ct"), 539.20, places=2)
        self.assertAlmostEqual(v("ingreso"), 5220, places=6)

    def test_ej28(self):
        v = self.valores(k=2, lam_modo=TIEMPO, lam=50, lam_u="minuto", mu_modo=TASA, mu=12, mu_u="día", H=8,
                         cS=50, cS_u="día", cW=5, cW_u="hora", cW_b="L (espera + servicio)")
        self.assertAlmostEqual(v("ct"), 138.10, places=2)

    def test_ej30(self):
        base = dict(lam_modo=TASA, lam=28, lam_u="hora", mu_modo=SERVICIO, mu=5, mu_u="minuto", H=8,
                    cS=50, cS_u="día", cW=20, cW_u="hora")
        self.assertAlmostEqual(self.valores(k=3, **base)("ct"), 492.39, places=2)
        self.assertAlmostEqual(self.valores(k=4, **base)("ct"), 259.62, places=2)


class TestFormulasDeComparacion(unittest.TestCase):
    """«Cómo se calculó» de una fila de «Comparar k y M»: la fórmula del escenario de esa fila da el
    mismo valor que la tabla (valor_metrica) para cada métrica de la barra de búsqueda."""

    # M/M/1, M/M/k y población finita, con costos
    CASOS = {nombre: ESCENARIOS[nombre] for nombre in ("M/M/1", "M/M/3 con S=2", "M/M/2/6/6 con S=3")}

    def test_todas_las_metricas_tienen_formula(self):
        self.assertEqual(len(cmp.METRICAS), 13)
        self.assertEqual(cmp.clave_formula(cmp.metrica_por_nombre("Probabilidad de esperar")), "Pw")
        esc = escenario(**ESCENARIOS["M/M/2/6/6 con S=3"])
        for m in cmp.METRICAS:
            fm.formula(esc, cmp.clave_formula(m), Formateador())       # no lanza FormulaNoDisponible

    def test_resultado_es_el_de_la_fila_en_k_y_M(self):
        cond = cmp.leer_condicion(cmp.METRICA_INICIAL, "≤", "1", "hora")
        for nombre, cambios in self.CASOS.items():
            esc = escenario(Mmax=8, **cambios)
            fmt = Formateador(4, "hora", esc.p.H)
            filas = (cmp.comparar_k(esc, cond, fmt).tabla.filas, cmp.comparar_M(esc, cond, fmt).tabla.filas)
            barridos = (("k", esc.barrido_k), ("M", esc.barrido_M))
            self.assertTrue(esc.barrido_M or not esc.p.finita, nombre)
            for (tipo, barrido), filas_tabla in zip(barridos, filas):
                claves = {f.clave for f in filas_tabla}
                for r in barrido:
                    if not r["ok"]:
                        continue
                    clave = cmp.clave_fila(tipo, r[tipo])
                    self.assertIn(clave, claves, f"{nombre}: la tabla no tiene la fila {clave}")
                    self.assertEqual(cmp.leer_clave_fila(clave), (tipo, r[tipo]))
                    der = cmp.escenario_de_fila(esc, tipo, r[tipo])
                    self.assertIs(der.r, r)                       # el resultado del barrido, sin recalcular
                    self.assertEqual(getattr(der.p, tipo), r[tipo])
                    self.assertIn(f"M/M/{der.p.k}", der.kendall)
                    for m in cmp.METRICAS:
                        ctx = f"{nombre} · {clave} · {m.clave}"
                        v = cmp.valor_metrica(r, m, der.p, "hora")
                        try:
                            res = fm.formula(der, cmp.clave_formula(m), fmt).resultado.dato
                        except fm.FormulaNoDisponible:
                            self.assertTrue(m.solo_finita and not der.p.finita, ctx)
                            self.assertTrue(math.isnan(v), ctx)
                            continue
                        if math.isnan(v):
                            self.assertTrue(math.isnan(res), ctx)        # p. ej. Wn cuando nadie espera
                        else:
                            self.assertTrue(math.isclose(res, v, rel_tol=1e-9, abs_tol=1e-9), f"{ctx}: {res} ≠ {v}")

    def test_fila_inexistente(self):
        esc = escenario()
        with self.assertRaises(ValueError):
            cmp.escenario_de_fila(esc, "k", 999)
        with self.assertRaises(ValueError):
            cmp.escenario_de_fila(esc, "M", 3)                       # población infinita: sin barrido de M
        for clave in ("Lq", "cmp:x:3", "cmp:k:a", "cmp:k", None):
            self.assertIsNone(cmp.leer_clave_fila(clave), clave)


if __name__ == "__main__":

    unittest.main()
