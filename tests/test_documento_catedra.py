"""
Pruebas contra el documento de la cátedra («Técnicas de Simulación», Teoría de colas) y
contra la notación y presentación que se tomaron de él.

Tolerancia: la del redondeo con que el documento escribe cada valor (medio dígito del último
decimal: «0,600» -> ±0,0005, «0,13» -> ±0,005), salvo donde el documento arrastra redondeos
intermedios; ahí se indica la tolerancia explícita.
"""
import importlib.util
import unittest

import utilidades  # noqa: F401  (agrega la raíz del proyecto al path)

from domain import modelos_colas as mc
from domain.errores import ErrorEntrada
from services import calculadora_service as cs
from services import comparacion_service as cmp
from services import formulas as fm
from services.tablas import Formateador, Valor

HAY_QT = importlib.util.find_spec("PySide6") is not None
TASA = cs.MODO_LAM[0]
BASE_L = "Tiempo en el sistema, L (costo de servicio)"
BASE_LQ = "Tiempo en cola, Lq (costo de espera)"


def entradas(**cambios):
    d = dict(cs.VALORES_INICIALES)
    d.update({k: str(v) for k, v in cambios.items()})
    return d


def escenario(**cambios):
    return cs.calcular_escenario(cs.leer_parametros(entradas(**cambios)))


def por_hora(lam, mu, **cambios):
    """Escenario con λ y μ dados como tasas por hora (como en los ejemplos del documento)."""
    return escenario(lam_modo=TASA, lam=lam, lam_u="hora", mu_modo=TASA, mu=mu, mu_u="hora", **cambios)


class CasoDocumento(unittest.TestCase):

    def doc(self, valor, texto_doc, tol=None, msg=None):
        """Compara con el valor del documento escrito con coma decimal; tolerancia = su redondeo."""
        esperado = float(texto_doc.replace(",", "."))
        if tol is None:
            decimales = len(texto_doc.split(",")[1]) if "," in texto_doc else 0
            tol = 0.5 * 10 ** -decimales + 1e-12
        self.assertLessEqual(abs(valor - esperado), tol, msg or f"{valor} vs documento {texto_doc} (±{tol:g})")


# ----------------------------------------------------------------------------
# Ejemplos del documento
# ----------------------------------------------------------------------------
class TestEjemplosPoblacionInfinita(CasoDocumento):

    def test_mm1_lam5_mu10(self):
        esc = por_hora(5, 10, H=8, cW="3,5", cW_u="hora", cW_b=BASE_L)
        self.doc(esc.r["rho"], "0,5")
        self.doc(esc.r["W"], "0,2")
        self.doc(esc.costos["ct"], "28")                 # L × 8 h × 3,5 $/h, base L

    def test_mm1_lam2_mu3_tiempo_de_independientes(self):
        r = mc.resolver(2, 3, 1)
        # Clientes independientes (30 % de las llegadas) que esperan: λ · H · 0,30 · Pk · Wn horas por día
        self.doc(2 * 8 * 0.30 * r["Pk"] * r["Wn"], "3,2")

    def test_mm1_lam2_mu6_costo(self):
        esc = por_hora(2, 6, H=8, cW="8,5", cW_u="hora", cW_b=BASE_L)
        self.doc(esc.r["W"], "0,25")
        self.doc(esc.costos["ct"], "34")

    def test_dos_maquinas_contra_una_rapida(self):
        # 2 máquinas de 5 $/día con μ = 10 contra 1 máquina de 10 $/día con μ = 15; 3,5 $/h sobre L
        dos = por_hora(5, 10, k=2, H=8, cS=5, cS_u="día", cW="3,5", cW_u="hora", cW_b=BASE_L)
        self.doc(dos.r["P0"], "0,600")
        self.doc(dos.r["W"], "0,107")
        self.doc(dos.costos["ct"], "24,98", tol=0.1)     # el documento usa W ya redondeado a 0,107
        una = por_hora(5, 15, k=1, H=8, cS=10, cS_u="día", cW="3,5", cW_u="hora", cW_b=BASE_L)
        self.doc(una.r["W"], "0,10")
        self.doc(una.costos["ct"], "24")

    def test_refineria_dos_canales(self):
        r = mc.resolver(2, 3, 2)
        self.doc(r["P0"], "0,50")
        self.doc(r["Pk"], "0,1667")                      # el documento escribe 0,16
        self.doc(r["Wq"], "0,0417")                      # el documento escribe 0,042
        # Wn = Wq / Pk exacto: 0,25 (el documento da 0,2625 por dividir valores ya redondeados)
        self.assertAlmostEqual(r["Wn"], 0.25, places=12)
        self.assertAlmostEqual(r["Wq"] / r["Pk"], r["Wn"], places=12)

    def test_central_telefonica(self):
        cinco, seis = mc.resolver(30, 12, 5), mc.resolver(30, 12, 6)
        self.doc(cinco["P0"], "0,0801")
        self.doc(cinco["Pk"], "0,13")
        self.doc(seis["P0"], "0,08162")
        self.doc(seis["Pk"], "0,047")


class TestEjemplosPoblacionFinita(CasoDocumento):

    def test_un_mecanico_cuatro_maquinas(self):
        r = mc.resolver(0.1, 0.5, 1, True, 4)
        self.doc(r["P0"], "0,4", tol=0.02)
        self.doc(r["L"], "1", tol=0.02)

    def test_dos_sistemas_de_dos_maquinas(self):
        esc = por_hora("0,1", "0,5", poblacion="Finita", k=1, M=2, S=2, H=8,
                       cS=50, cS_u="día", cW=20, cW_u="hora", cW_b=BASE_L)
        self.doc(esc.r["P0"], "0,68", tol=0.03)
        self.doc(esc.r["L"], "0,4", tol=0.03)
        self.doc(esc.costos["ct"], "228", tol=8)         # 2 × 50 + 2 × L × 8 × 20, con L ≈ 0,4

    def test_dos_mecanicos_cuatro_maquinas(self):
        r = mc.resolver(0.1, 0.5, 2, True, 4)
        # El documento redondea los términos de P0 antes de sumar: misma tolerancia que el caso k = 1
        self.doc(r["P0"], "0,48", tol=0.02)
        self.doc(r["L"], "0,68", tol=0.02)

    def test_p0_al_crecer_la_poblacion(self):
        for M, p0 in ((4, "0,647"), (5, "0,56"), (6, "0,485")):
            self.doc(mc.resolver(0.1, 1, 1, True, M)["P0"], p0, msg=f"M = {M}")


# ----------------------------------------------------------------------------
# Tarea 2: costo de servicio (base L) y costo de espera (base Lq)
# ----------------------------------------------------------------------------
class TestCostoServicioYEspera(unittest.TestCase):

    def test_etiquetas_segun_la_base(self):
        L, Lq = cs.etiquetas_costo("L"), cs.etiquetas_costo("Lq")
        self.assertEqual((L.nombre, L.concepto), ("Costo de servicio", "CT servicio (L)"))
        self.assertEqual((Lq.nombre, Lq.concepto), ("Costo de espera", "CT espera (Lq)"))
        self.assertIn("en el sistema (atendido o esperando)", L.ayuda)
        self.assertIn("solo mientras espera en la cola", Lq.ayuda)
        self.assertEqual(L.formula, "S·L·H·costo por hora")
        self.assertEqual(Lq.formula, "S·Lq·H·costo por hora")
        # Acepta el cfg, la base o el texto de la opción (también los textos antiguos)
        self.assertEqual(cs.etiquetas_costo(BASE_L), L)
        self.assertEqual(cs.etiquetas_costo("L (espera + servicio)"), L)
        self.assertEqual(cs.etiquetas_costo({"base_espera": "Lq", "c_ocio": 2}).encabezado, "CT espera (Lq) + ocio")

    def test_opciones_y_valor_por_defecto(self):
        self.assertEqual(list(cs.BASES_ESPERA), [BASE_L, BASE_LQ])
        self.assertEqual(cs.BASES_ESPERA[cs.VALORES_INICIALES["cW_b"]], "Lq")       # se mantiene el defecto

    def test_textos_antiguos_se_traducen(self):
        for viejo, base in (("Lq (solo espera en cola)", "Lq"), ("L (espera + servicio)", "L")):
            self.assertEqual(cs.leer_parametros(entradas(cW_b=viejo)).cfg["base_espera"], base)

    def test_tabla_de_costos(self):
        for base, concepto in ((BASE_L, "CT servicio (L): costo de servicio"),
                               (BASE_LQ, "CT espera (Lq): costo de espera")):
            t = cs.tabla_costos(escenario(cW=5, cW_b=base))
            filas = {f.clave: f.celdas for f in t.filas}
            self.assertEqual(filas["ct_s"][0], "CT servidores (sueldo/arriendo)")
            self.assertEqual(filas["ct_te"][0], concepto)
            self.assertTrue(filas["ct_te"][3].startswith(cs.etiquetas_costo(cs.BASES_ESPERA[base]).formula))
            self.assertEqual(t.encabezados, ["Concepto", "Por día ($)", "Por semana ($)", "Detalle"])

    def test_encabezados_y_negrita_en_comparacion(self):
        fmt = Formateador()
        for base, simbolo, otra in ((BASE_L, "L", "Lq"), (BASE_LQ, "Lq", "L")):
            esc = escenario(cW=5, cW_b=base)
            cond = cmp.leer_condicion("Wq (tiempo en cola)", "≤", "1", "minuto")
            t = cmp.comparar_k(esc, cond, fmt).tabla
            nombre = "servicio" if simbolo == "L" else "espera"
            self.assertEqual(t.encabezados[-3:], ["CT servidores ($/día)", f"CT {nombre} ({simbolo}) ($/día)",
                                                  "CT ($/día)"])
            destacadas = {c.titulo for c in t.columnas if c.destacada}
            self.assertEqual(destacadas, {"k", simbolo, "CT ($/día)"})
            self.assertIn(otra, t.encabezados)                       # las dos medidas siguen en la tabla
        con_ocio = escenario(cW=5, cI=2)
        t = cmp.comparar_k(con_ocio, cmp.leer_condicion("Wq (tiempo en cola)", "≤", "1", "minuto"), fmt).tabla
        self.assertIn("CT espera (Lq) + ocio ($/día)", t.encabezados)

    def test_como_se_calculo(self):
        fmt = Formateador(4, "hora", 8)
        servicio = fm.formula(por_hora(5, 10, H=8, cW="3,5", cW_b=BASE_L), "ct_te", fmt)
        self.assertEqual(servicio.titulo, "CT servicio (L): costo de servicio")
        self.assertIn(r"CT_{\mathrm{servicio}} = L\cdot H", servicio.latex)
        self.assertIn("1{,}0000", servicio.pasos[-1])               # L = 1 sustituido
        self.assertAlmostEqual(servicio.resultado.dato, 28)
        espera = fm.formula(por_hora(5, 10, H=8, cW="3,5", cW_b=BASE_LQ), "ct_te", fmt)
        self.assertIn(r"CT_{\mathrm{espera}} = L_q\cdot H", espera.latex)
        self.assertIn("0{,}5000", espera.pasos[-1])                 # Lq = 0,5 sustituido
        self.assertAlmostEqual(espera.resultado.dato, 0.5 * 8 * 3.5)

    def test_estado_vacio_nombra_el_costo(self):
        self.assertIn("costo de servicio", cs.texto_sin_costos("L"))
        self.assertIn("costo de espera", cs.texto_sin_costos("Lq"))


# ----------------------------------------------------------------------------
# Tarea 3: notación del documento (Pk en infinita, Pw en finita)
# ----------------------------------------------------------------------------
class TestNotacion(unittest.TestCase):

    def test_pk_en_infinita_sin_fila_repetida(self):
        esc = escenario(k=2)
        self.assertEqual([i.simbolo for i in cs.indicadores_principales(esc)][2], "Pk")
        simbolos = [f.celdas[0] for f in cs.tabla_resultados(esc).filas]
        self.assertIn("1−Pk", simbolos)
        self.assertNotIn("P(n≥k)", simbolos)                       # sería el mismo valor que Pk
        self.assertNotIn("Pw", simbolos)

    def test_pw_y_pnk_en_finita(self):
        esc = escenario(poblacion="Finita", k=2, M=4)
        simbolos = [f.celdas[0] for f in cs.tabla_resultados(esc).filas]
        self.assertIn("Pw", simbolos)
        self.assertIn("P(n≥k)", simbolos)                          # aquí difieren
        self.assertIn("1−Pw", simbolos)
        self.assertNotEqual(esc.r["frac_espera"], esc.r["Pk"])

    def test_claves_internas_intactas(self):
        esc = escenario(k=2)
        ind = cs.indicadores_principales(esc)[2]
        self.assertEqual(ind.clave, "Pw")                          # la fórmula se sigue pidiendo con "Pw"
        m = cmp.metrica_por_nombre("Pk (probabilidad de esperar)")
        self.assertEqual((m.clave, cmp.clave_formula(m)), ("frac_espera", "Pw"))
        self.assertIs(cmp.metrica_por_nombre("Probabilidad de esperar"), m)     # el nombre de siempre sigue

    def test_formulas_con_el_simbolo_del_modelo(self):
        fmt = Formateador()
        inf = fm.formula(escenario(k=2), "Pw", fmt)
        self.assertIn("Pk", inf.titulo)
        self.assertTrue(inf.latex.startswith("P_k"))
        fin = fm.formula(escenario(poblacion="Finita", k=2, M=4), "Pw", fmt)
        self.assertIn("Pw", fin.titulo)
        self.assertTrue(fin.latex.startswith("P_w"))
        self.assertIn("1 - P_k", fm.formula(escenario(k=2), "frac_no_espera", fmt).latex)
        self.assertIn(r"\frac{W_q}{P_k}", fm.formula(escenario(k=2), "Wn", fmt).latex)

    def test_encabezado_de_probabilidad_de_esperar(self):
        fmt = Formateador()
        cond = cmp.leer_condicion("Wq (tiempo en cola)", "≤", "1", "minuto")
        self.assertIn("Pk", cmp.comparar_k(escenario(), cond, fmt).tabla.encabezados)
        fin = escenario(poblacion="Finita", k=2, M=4)
        self.assertIn("Pw", cmp.comparar_k(fin, cond, fmt).tabla.encabezados)
        self.assertIn("Pw", cmp.comparar_M(fin, cond, fmt).tabla.encabezados)
        for t in (cmp.comparar_k(fin, cond, fmt).tabla, cmp.comparar_M(fin, cond, fmt).tabla):
            self.assertNotIn("P(esperar)", t.encabezados)

    def test_metricas_segun_poblacion(self):
        inf, fin = cmp.metricas_disponibles(False), cmp.metricas_disponibles(True)
        self.assertIn("Pk (probabilidad de esperar)", inf)
        self.assertNotIn("Fracción de unidades operando (finita)", inf)
        self.assertNotIn("P(n≥k) todos ocupados", inf)
        self.assertIn("Pw (probabilidad de esperar)", fin)
        self.assertIn("Fracción de unidades operando (finita)", fin)
        self.assertIn("P(n≥k) todos ocupados", fin)
        self.assertEqual(cmp.texto_inicial(False), "Pk (probabilidad de esperar)")


# ----------------------------------------------------------------------------
# Tarea 4: unidades y porcentajes
# ----------------------------------------------------------------------------
class TestUnidadesYPorcentajes(unittest.TestCase):

    def setUp(self):
        self.fmt = Formateador(4, "minuto", 12)

    def test_resultados_probabilidad_decimal_y_porcentaje(self):
        t = cs.tabla_resultados(escenario(k=2))
        self.assertEqual(t.encabezados, ["Símbolo", "Medida", "Valor", "Valor (%)", "Interpretación"])
        filas = {f.clave: self.fmt.texto(f.celdas[2]) + " | " + self.fmt.texto(f.celdas[3]) for f in t.filas}
        self.assertEqual(filas["P0"], "0,5000 | 50,00 %")
        self.assertRegex(filas["Pw"], r"^\d,\d{4} \| \d+,\d{2} %$")
        self.assertTrue(filas["rho"].endswith("% | "))            # ρ en %, sin repetir
        self.assertTrue(filas["Lq"].endswith(" clientes | "))
        self.assertTrue(filas["L"].endswith(" clientes | "))
        self.assertTrue(filas["Ln"].endswith(" clientes | "))
        self.assertTrue(filas["ociosos"].endswith(" servidores | "))
        self.assertTrue(filas["Wq"].endswith(" min | "))

    def test_unidades_en_finita_y_sistemas(self):
        t = cs.tabla_resultados(escenario(poblacion="Finita", k=2, M=4, S=2))
        filas = {f.clave: self.fmt.texto(f.celdas[2]) for f in t.filas}
        self.assertTrue(filas["operando"].endswith(" unidades"))
        self.assertTrue(filas["S_L"].endswith(" clientes"))
        self.assertTrue(filas["S_Lq"].endswith(" clientes"))
        self.assertTrue(filas["frac_operando"].endswith(" %"))

    def test_lambda_efectiva_en_la_unidad_elegida(self):
        esc = escenario(poblacion="Finita", k=2, M=4)
        lam_ef = esc.r["lam_ef"]
        fila = next(f for f in cs.tabla_resultados(esc).filas if f.clave == "lam_ef")
        self.assertEqual(fila.celdas[2].tipo, "tasa")
        self.assertEqual(Formateador(4, "hora", 12).texto(fila.celdas[2]),
                         Formateador(4).num(lam_ef) + " clientes/h")
        self.assertEqual(self.fmt.texto(fila.celdas[2]), Formateador(4).num(lam_ef / 60) + " clientes/min")
        self.assertEqual(Formateador(4, "día", 12).texto(fila.celdas[2]),
                         Formateador(4).num(lam_ef * 12) + " clientes/día")
        self.assertIn("clientes/min", cs.mensaje_estado(esc, self.fmt))
        self.assertNotIn(" /h", cs.mensaje_estado(esc, self.fmt))
        self.assertEqual(fm.formula(esc, "lam_ef", self.fmt).resultado.tipo, "tasa")

    def test_rho_en_porcentaje_en_tablas_de_comparacion(self):
        cond = cmp.leer_condicion("Wq (tiempo en cola)", "≤", "1", "minuto")
        t = cmp.comparar_k(escenario(), cond, self.fmt).tabla
        i = t.encabezados.index("ρ (%)")
        self.assertTrue(all(f.celdas[i].tipo == "pct" for f in t.filas))
        self.assertTrue(self.fmt.texto(t.filas[0].celdas[i]).endswith(" %"))
        # Probabilidades en decimal, sin columnas de más
        j = t.encabezados.index("Pk")
        self.assertEqual(t.filas[0].celdas[j].tipo, "num")

    def test_fraccion_con_ingreso_acepta_porcentaje(self):
        for texto, valor in (("0,3", 0.3), ("30 %", 0.3), ("30%", 0.3), ("100 %", 1.0), ("0", 0.0)):
            self.assertAlmostEqual(cs.leer_parametros(entradas(ingF=texto)).cfg["frac_ingreso"], valor, msg=texto)
        for malo in ("130 %", "-5 %", "x %", "%"):
            with self.assertRaises(ErrorEntrada, msg=malo):
                cs.leer_parametros(entradas(ingF=malo))
        with self.assertRaises(ErrorEntrada):           # solo ingF admite «%»
            cs.leer_parametros(entradas(cW="30 %"))

    def test_csv_con_las_mismas_reglas(self):
        import csv
        import io
        from services import exportacion_service as ex
        esc = escenario(poblacion="Finita", k=2, M=4, cW=5)
        buf = io.StringIO()
        ex.escribir_csv(buf, [cs.tabla_resultados(esc), cs.tabla_costos(esc)], self.fmt)
        texto = buf.getvalue()
        self.assertIn("clientes/min", texto)
        self.assertNotIn(" /h", texto)
        filas = list(csv.reader(io.StringIO(texto), delimiter=";"))
        self.assertIn(["Concepto", "Por día ($)", "Por semana ($)", "Detalle"], filas)
        pw = next(f for f in filas if f and f[0] == "Pw")
        self.assertTrue(pw[3].endswith(" %"))

    def test_formateador_tasa_no_definida(self):
        self.assertEqual(self.fmt.texto(Valor(float("nan"), "tasa")), "—")


class TestCampoAplica(unittest.TestCase):

    def test_m_oculto_no_se_valida(self):
        self.assertFalse(cs.campo_aplica("M", False))
        self.assertFalse(cs.campo_aplica("Mmax", False))
        self.assertTrue(cs.campo_aplica("M", True))
        p = cs.leer_parametros(entradas(M="no es un número", Mmax=""))      # infinita: se ignoran
        self.assertIsNone(p.M)
        with self.assertRaises(ErrorEntrada):
            cs.leer_parametros(entradas(poblacion="Finita", M="no es un número"))


# ----------------------------------------------------------------------------
# Interfaz Qt: M oculto, etiquetas de costo en vivo y símbolos
# ----------------------------------------------------------------------------
@unittest.skipUnless(HAY_QT, "PySide6 no está instalado")
class TestPanelQt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from ui_qt import soporte_pruebas as sp
        cls.sp = sp
        sp.aplicacion()
        from ui_qt.ventana_principal import VentanaPrincipal
        cls.v = VentanaPrincipal()
        cls.v.resize(1366, 768)
        cls.v.show()
        sp.procesar()

    @classmethod
    def tearDownClass(cls):
        cls.v.formulas.cerrar()
        cls.v.animador.terminar()
        cls.v.close()
        cls.v.deleteLater()
        cls.sp.procesar()

    def setUp(self):
        self.v.mostrar_parametros(True, animar=False)
        self.v.animador.terminar()
        self.panel = self.v.panel
        self.panel.restablecer()
        for s in self.panel.secciones.values():
            s.abrir(True)
        self.sp.procesar()

    def _partes(self, clave):
        p = self.panel
        return [p.widgets[clave], p.etiquetas[clave], p.unidades[clave], p.ayudas[clave]]

    def test_m_oculto_en_infinita_y_visible_en_finita(self):
        p = self.panel
        for clave in ("M", "Mmax"):
            self.assertFalse(p.campo_visible(clave))
            self.assertTrue(all(w.isHidden() for w in self._partes(clave)), clave)
        p.poner("poblacion", "Finita")
        self.sp.procesar()
        for clave in ("M", "Mmax"):
            self.assertTrue(p.campo_visible(clave))
            self.assertTrue(all(w.isVisible() for w in self._partes(clave)), clave)

    def _hueco_al_final(self, seccion, ultimo):
        """Espacio entre el último widget visible de la sección y su borde inferior, sin contar el margen."""
        s = self.panel.secciones[seccion]
        return s.cuerpo.height() - (ultimo.geometry().bottom() + 1) - s.rejilla.contentsMargins().bottom()

    def test_sin_huecos_al_ocultar(self):
        """
        M y M máximo son los últimos de su sección: ocultos, la sección termina tras el campo anterior
        con el mismo borde inferior que cuando se ven (sin el aire de separación ni filas vacías).
        """
        p, sp = self.panel, self.sp
        huecos = {}
        for poblacion, ultimos in (("Finita", {"modelo": "M", "analisis": "Mmax"}),
                                   ("Infinita", {"modelo": "S", "analisis": "kmax"})):
            p.poner("poblacion", poblacion)
            sp.esperar(100)
            for seccion, clave in ultimos.items():
                huecos[poblacion, seccion] = self._hueco_al_final(seccion, p.ayudas[clave])
        for seccion in ("modelo", "analisis"):
            self.assertEqual(huecos["Infinita", seccion], huecos["Finita", seccion], seccion)
            self.assertLessEqual(huecos["Infinita", seccion], 1, seccion)            # 1 px: borde del marco

    def test_valor_de_m_se_conserva(self):
        p = self.panel
        p.poner("poblacion", "Finita")
        p.poner("M", "17")
        p.poner("poblacion", "Infinita")
        p.poner("poblacion", "Finita")
        self.sp.procesar()
        self.assertEqual(p.get("M"), "17")

    def test_m_oculto_con_error_no_se_marca(self):
        p = self.panel
        p.poner("M", "abc")                          # infinita: M no se valida
        self.v.calcular()
        self.sp.procesar()
        self.assertIsNotNone(self.v.esc)
        self.assertTrue(p.errores["M"].isHidden())
        p.poner("poblacion", "Finita")
        self.v.calcular()
        self.sp.procesar()
        self.assertIsNone(self.v.esc)
        self.assertFalse(p.errores["M"].isHidden())
        p.poner("poblacion", "Infinita")             # al ocultarse se va también su error
        self.sp.procesar()
        self.assertTrue(p.errores["M"].isHidden())

    def test_orden_de_tabulacion(self):
        """Tab desde «Sistemas idénticos S»: en finita va a M; en infinita lo salta (va a la sección siguiente)."""
        p, sp = self.panel, self.sp
        self.v.activateWindow()
        for poblacion, siguiente in (("Infinita", p.secciones["llegadas"].cabecera), ("Finita", p.widgets["M"])):
            p.poner("poblacion", poblacion)
            sp.procesar()
            p.widgets["S"].setFocus()
            sp.procesar()
            sp.tecla(p.widgets["S"], "Tab")
            sp.procesar()
            self.assertIs(self.v.focusWidget(), siguiente, poblacion)
            if poblacion == "Finita":           # y de M sigue a la cabecera siguiente, como antes
                sp.tecla(p.widgets["M"], "Tab")
                sp.procesar()
                self.assertIs(self.v.focusWidget(), p.secciones["llegadas"].cabecera)

    def test_etiqueta_del_costo_cambia_en_vivo(self):
        p = self.panel
        self.assertEqual(p.etiquetas["cW"].text(), "Costo de espera")
        self.assertIn("solo mientras espera en la cola", p.ayudas["cW"].text())
        p.poner("cW_b", BASE_L)
        self.sp.procesar()
        self.assertEqual(p.etiquetas["cW"].text(), "Costo de servicio")
        self.assertIn("atendido o esperando", p.ayudas["cW"].text())
        self.assertEqual(p.etiquetas["cS"].text().replace("\n", " "), "Costo por servidor (sueldo/arriendo)")
        p.poner("cW_b", "Lq (solo espera en cola)")      # texto antiguo: se traduce
        self.assertEqual(p.get("cW_b"), BASE_LQ)

    def test_opciones_de_costo_sin_cortes(self):
        c = self.panel.widgets["cW_b"]
        for i in range(c.count()):
            self.assertGreater(c.minimumWidth(), c.fontMetrics().horizontalAdvance(c.itemText(i)))

    def test_simbolos_en_tarjetas_y_comparacion(self):
        v, sp = self.v, self.sp
        v.calcular()
        sp.procesar()
        tarjetas = [t.simbolo.text() for t in v.p_resultados.tarjetas.tarjetas[:7]]
        self.assertEqual(tarjetas[2], "Pk")
        pag = v.p_comparacion
        self.assertEqual(pag.cb_metrica.currentText(), "Pk (probabilidad de esperar)")
        self.panel.poner("poblacion", "Finita")
        v.calcular()
        sp.procesar()
        self.assertEqual(v.p_resultados.tarjetas.tarjetas[2].simbolo.text(), "Pw")
        self.assertEqual(pag.cb_metrica.currentText(), "Pw (probabilidad de esperar)")   # conserva la métrica
        opciones = [pag.cb_metrica.itemText(i) for i in range(pag.cb_metrica.count())]
        self.assertIn("Fracción de unidades operando (finita)", opciones)


if __name__ == "__main__":
    unittest.main()
