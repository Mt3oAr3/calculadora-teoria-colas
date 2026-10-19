"""Pruebas de validación de entradas, armado del escenario, tablas y exportación."""
import csv
import io
import os
import tempfile
import unittest

import utilidades  # noqa: F401  (agrega la raíz del proyecto al path)

import matplotlib
matplotlib.use("Agg")

from domain.errores import ErrorEntrada
from services import calculadora_service as cs
from services import exportacion_service as ex
from services.tablas import Formateador, Valor


def entradas(**cambios):
    d = dict(cs.VALORES_INICIALES)
    d.update({k: str(v) for k, v in cambios.items()})
    return d


def campos_con_error(**cambios):
    try:
        cs.leer_parametros(entradas(**cambios))
    except ErrorEntrada as e:
        return {c for c, _ in e.errores}
    return set()


class TestLecturaParametros(unittest.TestCase):

    def test_valores_iniciales(self):
        p = cs.leer_parametros(entradas())
        self.assertFalse(p.finita)
        self.assertEqual(p.k, 1)
        self.assertIsNone(p.M)                      # M no aplica en infinita
        self.assertAlmostEqual(p.lam, 10)
        self.assertAlmostEqual(p.mu, 15)            # 4 min por servicio
        self.assertEqual(p.cfg["base_espera"], "Lq")

    def test_coma_decimal(self):
        p = cs.leer_parametros(entradas(lam="2,5"))
        self.assertAlmostEqual(p.lam, 2.5)

    def test_no_corrige_enteros_ni_negativos(self):
        # La versión original convertía k=2.7 en 3 y k=-5 en 1 sin avisar.
        self.assertEqual(campos_con_error(k="2.7"), {"k"})
        self.assertEqual(campos_con_error(k="-5"), {"k"})
        self.assertEqual(campos_con_error(k="0"), {"k"})
        self.assertEqual(cs.leer_parametros(entradas(k="3,0")).k, 3)

    def test_campos_numericos_invalidos(self):
        casos = {"lam": ["0", "-1", "abc", "", "inf", "nan"], "mu": ["0"], "H": ["0", "25"],
                 "D": ["0", "8"], "cS": ["-1"], "cW": ["-0.5"], "cI": ["-2"], "ing": ["-3"],
                 "ingF": ["1.2", "-0.1"], "kmax": ["0", "201", "2.5"]}
        for clave, valores in casos.items():
            for v in valores:
                self.assertIn(clave, campos_con_error(**{clave: v}), f"{clave}={v!r}")

    def test_reporta_todos_los_errores_a_la_vez(self):
        self.assertEqual(campos_con_error(k="x", lam="0", ingF="3"), {"k", "lam", "ingF"})

    def test_mensaje_explica_el_campo(self):
        with self.assertRaises(ErrorEntrada) as ctx:
            cs.leer_parametros(entradas(H="0"))
        campo, mensaje = ctx.exception.errores[0]
        self.assertEqual(campo, "H")
        self.assertIn("Horas por día", mensaje)
        self.assertIn("mayor que 0", mensaje)

    def test_campos_de_finita_solo_se_validan_en_finita(self):
        self.assertEqual(campos_con_error(M="abc", Mmax="0"), set())
        self.assertEqual(campos_con_error(poblacion="Finita", M="abc", Mmax="0"), {"M", "Mmax"})
        self.assertEqual(campos_con_error(poblacion="Finita", Mmax="301"), {"Mmax"})

    def test_opcion_invalida(self):
        self.assertIn("lam_u", campos_con_error(lam_u="semana"))

    def test_unidad_dia_usa_horas_de_operacion(self):
        p = cs.leer_parametros(entradas(lam_modo=cs.MODO_LAM[1], lam_u="día", lam="4", H="8"))
        self.assertAlmostEqual(p.lam, 1 / 32)

    def test_dia_con_horas_invalidas_no_duplica_error(self):
        self.assertEqual(campos_con_error(lam_u="día", H="0"), {"H"})

    def test_rango_probabilidades(self):
        self.assertEqual(cs.leer_rango("2", "3"), (2, 3))
        for a, b, campo in (("-1", "2", "pa"), ("x", "2", "pa"), ("3", "2", "pb"), ("1", "2.5", "pb")):
            with self.assertRaises(ErrorEntrada) as ctx:
                cs.leer_rango(a, b)
            self.assertEqual(ctx.exception.errores[0][0], campo)

    def test_vista_previa_tasa(self):
        self.assertAlmostEqual(cs.vista_previa_tasa(False, "4", "minuto", "8"), 15)
        self.assertIsNone(cs.vista_previa_tasa(True, "0", "hora", "8"))
        self.assertIsNone(cs.vista_previa_tasa(True, "5", "día", "0"))


class TestEscenario(unittest.TestCase):

    def test_escenario_estable(self):
        esc = cs.calcular_escenario(cs.leer_parametros(entradas()))
        self.assertTrue(esc.estable)
        self.assertEqual(esc.kendall, "M/M/1")
        self.assertIn("estable", cs.mensaje_estado(esc, Formateador()))
        simbolos = [i.simbolo for i in cs.indicadores_principales(esc)]
        self.assertEqual(simbolos, ["ρ", "P0", "Pw", "Lq", "L", "Wq", "W"])

    def test_escenario_inestable_no_muestra_resultados(self):
        esc = cs.calcular_escenario(cs.leer_parametros(entradas(lam="20")))
        self.assertFalse(esc.estable)
        self.assertIsNone(esc.costos)
        self.assertEqual(cs.indicadores_principales(esc), [])
        self.assertEqual(cs.tabla_resultados(esc).filas, [])
        self.assertTrue(cs.tabla_resultados(esc).mensaje_vacio)
        self.assertIn("k = 2", cs.mensaje_estado(esc, Formateador()))
        self.assertTrue(esc.barrido_k)              # la comparación sigue disponible

    def test_escenario_finito(self):
        esc = cs.calcular_escenario(cs.leer_parametros(entradas(
            poblacion="Finita", k="2", M="4", lam_modo=cs.MODO_LAM[0], lam="0.1", lam_u="hora",
            mu_modo=cs.MODO_MU[0], mu="0.5", mu_u="hora", Mmax="10")))
        self.assertEqual(esc.kendall, "M/M/2/4/4")
        self.assertEqual(len(esc.barrido_M), 10)
        self.assertIn("M−L", [i.simbolo for i in cs.indicadores_principales(esc)])

    def test_aviso_k_mayor_que_M(self):
        esc = cs.calcular_escenario(cs.leer_parametros(entradas(poblacion="Finita", k="6", M="4")))
        self.assertTrue(esc.avisos)
        self.assertIn("k > M", cs.mensaje_estado(esc, Formateador()))

    def test_tablas_tienen_columnas_consistentes(self):
        esc = cs.calcular_escenario(cs.leer_parametros(entradas(cS="100", cW="20")))
        for t in (cs.tabla_resultados(esc), cs.tabla_probabilidades(esc, 2, 3),
                  cs.tabla_distribucion(esc), cs.tabla_por_dia(esc), cs.tabla_costos(esc)):
            self.assertTrue(t.filas, t.titulo)
            for fila in t.filas:
                self.assertEqual(len(fila.celdas), len(t.columnas), t.titulo)

    def test_tabla_costos_valores(self):
        esc = cs.calcular_escenario(cs.leer_parametros(entradas(cS="100", D="5")))
        t = cs.tabla_costos(esc)
        fila_cts = t.filas[0]
        self.assertEqual(fila_cts.celdas[1].dato, 100)
        self.assertEqual(fila_cts.celdas[2].dato, 500)


class TestFormateador(unittest.TestCase):

    def test_formato_numerico(self):
        f = Formateador(decimales=2, unidad_tiempo="minuto", horas_dia=8)
        self.assertEqual(f.num(1234.5678), "1.234,57")
        self.assertEqual(f.pct(0.5), "50,00 %")
        self.assertEqual(f.dinero(10), "$ 10,00")
        self.assertEqual(f.tiempo(0.25), "15,00 min")
        self.assertEqual(f.num(float("nan")), "—")
        self.assertEqual(f.texto(Valor(None, "tiempo")), "—")
        self.assertEqual(f.texto(Valor(2, sufijo=" h")), "2,00 h")


class TestExportacion(unittest.TestCase):

    def setUp(self):
        self.esc = cs.calcular_escenario(cs.leer_parametros(entradas(cS="50")))
        self.fmt = Formateador()

    def test_csv_secciones_y_formato(self):
        tablas = [cs.tabla_resultados(self.esc), cs.tabla_costos(self.esc)]
        buf = io.StringIO()
        ex.escribir_csv(buf, tablas, self.fmt)
        filas = list(csv.reader(io.StringIO(buf.getvalue()), delimiter=";"))
        self.assertEqual(filas[0], ["Resultados"])
        self.assertEqual(filas[1], ["Símbolo", "Medida", "Valor", "Interpretación"])
        n = len(tablas[0].filas)
        self.assertEqual(filas[2 + n], [])
        self.assertEqual(filas[3 + n], ["Costos"])
        self.assertEqual(filas[2][:3], ["ρ", "Utilización por servidor", "66,67 %"])

    def test_csv_archivo_utf8_bom(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "r.csv")
            ex.exportar_csv(ruta, [cs.tabla_resultados(self.esc)], self.fmt)
            with open(ruta, "rb") as fh:
                self.assertTrue(fh.read().startswith(b"\xef\xbb\xbf"))

    def test_guardar_graficas(self):
        ctx = cs.contexto_graficas(self.esc, "minuto")
        with tempfile.TemporaryDirectory() as d:
            rutas = ex.guardar_todas(d, ctx, dpi=40)
            self.assertEqual(len(rutas), 6)              # infinita: solo las gráficas de k
            self.assertTrue(all(os.path.getsize(r) > 0 for r in rutas))
            self.assertTrue(os.path.basename(rutas[0]).startswith("01_P0_k"))

    def test_todas_las_graficas_finita(self):
        esc = cs.calcular_escenario(cs.leer_parametros(entradas(poblacion="Finita", k="2", M="5", cS="10")))
        ctx = cs.contexto_graficas(esc, "hora", mostrar_valores=False)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(len(ex.guardar_todas(d, ctx, dpi=40)), 11)


if __name__ == "__main__":
    unittest.main()
