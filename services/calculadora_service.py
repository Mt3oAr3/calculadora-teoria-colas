"""
calculadora_service.py
Une la interfaz con el dominio:

  1. leer_parametros(): valida el texto escrito en el formulario y lo convierte
     a números en unidades internas (tasas por hora). No corrige datos: si algo
     es inválido lanza ErrorEntrada indicando el campo y cómo arreglarlo.
  2. calcular_escenario(): resuelve el modelo y los barridos de k y M.
  3. tabla_*() / indicadores_principales(): datos listos para mostrar o exportar.
"""
import math
from dataclasses import dataclass, field

from domain import costos as dc
from domain import modelos_colas as mc
from domain import unidades as du
from domain.errores import ErrorEntrada

from .tablas import Columna, Fila, Tabla, Valor

# ----------------------------------------------------------------------------
# Opciones del formulario
# ----------------------------------------------------------------------------
POBLACIONES = ["Infinita", "Finita"]
MODO_LAM = ["Tasa (clientes por unidad)", "Tiempo entre llegadas"]
MODO_MU = ["Tasa (clientes por unidad)", "Tiempo medio de servicio"]
BASES_ESPERA = {"Lq (solo espera en cola)": "Lq", "L (espera + servicio)": "L"}
DECIMALES = ["2", "3", "4", "6"]

# Valores iniciales: un M/M/1 estable de ejemplo (λ = 10 clientes/h, servicio
# de 4 min → μ = 15/h, ρ ≈ 0,67), jornada de 12 h, 7 días, sin costos.
VALORES_INICIALES = {
    "poblacion": "Infinita", "k": "1", "S": "1", "M": "4",
    "lam_modo": MODO_LAM[0], "lam_u": "hora", "lam": "10",
    "mu_modo": MODO_MU[1], "mu_u": "minuto", "mu": "4",
    "H": "12", "D": "7",
    "cS": "0", "cS_u": "día", "cW": "0", "cW_u": "hora", "cW_b": "Lq (solo espera en cola)",
    "cI": "0", "ing": "0", "ingF": "1",
    "kmax": "10", "Mmax": "30",
    "ut": "minuto", "dec": "4",
    "pa": "2", "pb": "3",
}


@dataclass(frozen=True)
class ReglaNumerica:
    etiqueta: str
    entero: bool = False
    minimo: float | None = None
    maximo: float | None = None
    minimo_excluido: bool = False       # True: debe ser estrictamente mayor que el mínimo
    solo_finita: bool = False


# Límites superiores: kmax ≤ 200 y M ≤ 10000 mantienen tablas legibles y cálculos
# instantáneos; Mmax ≤ 300 es el límite que ya tenía la versión original.
REGLAS = {
    "k": ReglaNumerica("Servidores k", entero=True, minimo=1, maximo=1000),
    "S": ReglaNumerica("Sistemas idénticos", entero=True, minimo=1, maximo=100),
    "M": ReglaNumerica("Población M", entero=True, minimo=1, maximo=10000, solo_finita=True),
    "lam": ReglaNumerica("Llegadas λ (valor)", minimo=0, minimo_excluido=True),
    "mu": ReglaNumerica("Servicio μ (valor)", minimo=0, minimo_excluido=True),
    "H": ReglaNumerica("Horas por día", minimo=0, maximo=24, minimo_excluido=True),
    "D": ReglaNumerica("Días por semana", minimo=0, maximo=7, minimo_excluido=True),
    "cS": ReglaNumerica("Costo por servidor", minimo=0),
    "cW": ReglaNumerica("Costo de espera", minimo=0),
    "cI": ReglaNumerica("Costo por hora de servidor ocioso", minimo=0),
    "ing": ReglaNumerica("Ingreso por cliente", minimo=0),
    "ingF": ReglaNumerica("Fracción de clientes con ingreso", minimo=0, maximo=1),
    "kmax": ReglaNumerica("k máximo", entero=True, minimo=1, maximo=200),
    "Mmax": ReglaNumerica("M máximo", entero=True, minimo=2, maximo=300, solo_finita=True),
}

OPCIONES = {
    "poblacion": POBLACIONES, "lam_modo": MODO_LAM, "mu_modo": MODO_MU,
    "lam_u": du.UNIDADES, "mu_u": du.UNIDADES, "cS_u": dc.UNIDADES_COSTO_SERVIDOR,
    "cW_u": du.UNIDADES, "cW_b": list(BASES_ESPERA),
}


def campo_aplica(clave, finita):
    """¿El campo se usa con la población elegida?"""
    regla = REGLAS.get(clave)
    return not (regla and regla.solo_finita and not finita)


def convertir_numero(texto, regla):
    """
    Convierte el texto de un campo según su regla. Devuelve el número o lanza
    ValueError con un mensaje para el usuario (sin el nombre del campo).
    """
    txt = (texto or "").strip().replace(",", ".")
    if not txt:
        raise ValueError("es obligatorio.")
    try:
        x = float(txt)
    except ValueError:
        raise ValueError(f"«{texto.strip()}» no es un número. Usa por ejemplo 2,5 o 10.") from None
    if not math.isfinite(x):
        raise ValueError("debe ser un número finito.")
    if regla.entero:
        if x != int(x):
            raise ValueError(f"debe ser un número entero (escribiste {texto.strip()}).")
        x = int(x)
    if regla.minimo is not None:
        if regla.minimo_excluido and x <= regla.minimo:
            raise ValueError(f"debe ser mayor que {_n(regla.minimo)}.")
        if not regla.minimo_excluido and x < regla.minimo:
            raise ValueError(f"debe ser mayor o igual a {_n(regla.minimo)}.")
    if regla.maximo is not None and x > regla.maximo:
        raise ValueError(f"debe ser como máximo {_n(regla.maximo)}.")
    return x


def _n(x):
    return str(int(x)) if float(x).is_integer() else str(x).replace(".", ",")


# ----------------------------------------------------------------------------
# Parámetros validados
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Parametros:
    finita: bool
    k: int
    S: int                 # sistemas idénticos e independientes (1 = normal)
    M: int | None          # None en población infinita
    lam: float             # clientes por hora (en finita: por unidad de la población)
    mu: float              # clientes por hora por servidor
    H: float               # horas de operación por día
    D: float               # días por semana
    cfg: dict              # configuración de costos (domain.costos)
    kmax: int
    Mmax: int | None


def leer_parametros(entradas):
    """
    entradas: dict clave -> texto del formulario (ver VALORES_INICIALES).
    Devuelve Parametros o lanza ErrorEntrada con TODOS los campos inválidos.
    Los campos que no aplican al modelo (p. ej. M en población infinita) no se validan.
    """
    errores = []
    for clave, opciones in OPCIONES.items():
        if entradas.get(clave) not in opciones:
            errores.append((clave, f"Selecciona una opción válida en «{clave}»."))
    finita = entradas.get("poblacion") == "Finita"

    num = {}
    for clave, regla in REGLAS.items():
        if not campo_aplica(clave, finita):
            continue
        try:
            num[clave] = convertir_numero(entradas.get(clave, ""), regla)
        except ValueError as e:
            errores.append((clave, f"{regla.etiqueta} {e}"))

    # Conversión de λ y μ a tasa por hora (necesita H si la unidad es 'día')
    tasas = {}
    for clave, modos in (("lam", MODO_LAM), ("mu", MODO_MU)):
        if clave in num and ("H" in num or entradas.get(f"{clave}_u") != "día"):
            try:
                tasas[clave] = du.tasa_por_hora(entradas[f"{clave}_modo"] == modos[0], num[clave],
                                                entradas[f"{clave}_u"], num.get("H", 1.0))
            except (ValueError, KeyError) as e:
                errores.append((clave, f"{REGLAS[clave].etiqueta}: {e}"))

    if errores:
        raise ErrorEntrada(errores)

    cfg = dc.configuracion_costos(
        c_servidor=num["cS"], c_servidor_u=entradas["cS_u"],
        c_espera=num["cW"], c_espera_u=entradas["cW_u"], base_espera=BASES_ESPERA[entradas["cW_b"]],
        c_ocio=num["cI"], ingreso=num["ing"], frac_ingreso=num["ingF"], sistemas=num["S"])
    return Parametros(finita=finita, k=num["k"], S=num["S"], M=num.get("M"), lam=tasas["lam"], mu=tasas["mu"],
                      H=num["H"], D=num["D"], cfg=cfg, kmax=num["kmax"], Mmax=num.get("Mmax"))


def vista_previa_tasa(es_tasa, valor_txt, unidad, horas_txt):
    """Tasa por hora para mostrar mientras se escribe; None si aún no es válida."""
    try:
        valor = convertir_numero(valor_txt, REGLAS["lam"])
        H = convertir_numero(horas_txt, REGLAS["H"]) if unidad == "día" else 1.0
        return du.tasa_por_hora(es_tasa, valor, unidad, H)
    except ValueError:
        return None


def leer_rango(a_txt, b_txt):
    """Rango [a, b] de la pestaña Probabilidades: enteros con 0 ≤ a ≤ b."""
    regla = ReglaNumerica("", entero=True, minimo=0, maximo=100000)
    errores, valores = [], {}
    for clave, nombre, txt in (("pa", "a", a_txt), ("pb", "b", b_txt)):
        try:
            valores[clave] = convertir_numero(txt, regla)
        except ValueError as e:
            errores.append((clave, f"El valor {nombre} {e}"))
    if not errores and valores["pb"] < valores["pa"]:
        errores.append(("pb", "El valor b debe ser mayor o igual que a."))
    if errores:
        raise ErrorEntrada(errores)
    return valores["pa"], valores["pb"]


# ----------------------------------------------------------------------------
# Escenario calculado
# ----------------------------------------------------------------------------
@dataclass
class Escenario:
    p: Parametros
    r: dict                         # resultado del modelo (domain.modelos_colas)
    barrido_k: list
    barrido_M: list
    sigla: str
    kendall: str
    costos: dict | None = None      # None si el sistema es inestable
    avisos: list = field(default_factory=list)

    @property
    def estable(self):
        return self.r["ok"]

    @property
    def descripcion(self):
        p = self.p
        pob = f"población finita de {p.M}" if p.finita else "población infinita"
        canales = "un canal" if p.k == 1 else f"{p.k} canales"
        sis = f" · {p.S} sistemas idénticos" if p.S > 1 else ""
        return f"{self.sigla} · {pob} · {canales}{sis}"


def calcular_escenario(p):
    """Resuelve el modelo y los barridos. Propaga ErrorModelo si el dominio no puede evaluarlo."""
    r = mc.resolver(p.lam, p.mu, p.k, p.finita, p.M)
    sigla, kendall = mc.nombre_modelo(p.finita, p.k, p.M if p.finita else None)
    esc = Escenario(
        p=p, r=r, sigla=sigla, kendall=kendall,
        barrido_k=mc.barrido_k(p.lam, p.mu, p.finita, p.M, p.kmax),
        barrido_M=mc.barrido_M(p.lam, p.mu, p.k, p.Mmax) if p.finita else [],
        costos=dc.costos(r, p.H, p.cfg) if r["ok"] else None,
    )
    if p.finita and p.k > p.M:
        esc.avisos.append(f"Como k > M, solo pueden trabajar {p.M} servidores a la vez "
                          f"(k efectivo = {p.M}); el costo de servidores sí cuenta los {p.k}.")
    return esc


def mensaje_estado(esc, fmt):
    """Texto de estabilidad / factibilidad del modelo."""
    r = esc.r
    if not r["ok"]:
        return (f"Sistema inestable: ρ = λ/(kμ) = {fmt.num(r['rho'])} ≥ 1, la cola crece sin límite. "
                f"Se necesitan al menos k = {r['k_min']} servidores (ver «Comparar k y M»).")
    if esc.p.finita:
        txt = (f"Población finita: siempre estable. λ/μ por unidad = {fmt.num(r['a'])}. "
               f"λ efectiva = λ(M − L) = {fmt.num(r['lam_ef'])} por hora.")
    else:
        txt = f"Sistema estable: ρ = λ/(kμ) = {fmt.num(r['rho'])} < 1. Tráfico λ/μ = {fmt.num(r['a'])}."
    return " ".join([txt] + esc.avisos)


# ----------------------------------------------------------------------------
# Indicadores principales y tablas
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Indicador:
    simbolo: str
    nombre: str
    valor: Valor
    ayuda: str
    clave: str = ""        # clave de la fórmula en services/formulas.py


def indicadores_principales(esc):
    """Indicadores clave del modelo (solo los que aplican). Vacío si es inestable."""
    r = esc.r
    if not r["ok"]:
        return []
    util = "Utilización de los servidores" if r["finita"] else "Utilización por servidor"
    lista = [
        Indicador("ρ", util, Valor(r["util"], "pct"), "Fracción del tiempo que trabaja cada servidor.", "rho"),
        Indicador("P0", "Sistema vacío", Valor(r["P0"]), "Probabilidad de que no haya clientes.", "P0"),
        Indicador("Pw", "Probabilidad de esperar", Valor(r["frac_espera"]),
                  "Fracción de clientes que llegan y deben hacer cola.", "Pw"),
        Indicador("Lq", "Clientes en cola", Valor(r["Lq"]), "Longitud media de la línea de espera.", "Lq"),
        Indicador("L", "Clientes en el sistema", Valor(r["L"]), "En cola más en servicio.", "L"),
        Indicador("Wq", "Tiempo en cola", Valor(r["Wq"], "tiempo"), "Espera media antes de ser atendido.", "Wq"),
        Indicador("W", "Tiempo en el sistema", Valor(r["W"], "tiempo"), "Espera más servicio.", "W"),
    ]
    if r["finita"]:
        lista.append(Indicador("M−L", "Unidades operando", Valor(r["operando"]),
                               "Unidades de la población fuera del sistema.", "operando"))
    return lista


def tabla_resultados(esc):
    cols = [Columna("Símbolo", False), Columna("Medida", False), Columna("Valor"),
            Columna("Interpretación", False)]
    t = Tabla("Resultados", cols, mensaje_vacio="Sin resultados: el sistema es inestable con estos datos.")
    r = esc.r
    if not r["ok"]:
        return t
    for ind in indicadores_principales(esc):
        t.filas.append(Fila([ind.simbolo, ind.nombre, ind.valor, ind.ayuda], ("principal",), ind.clave))
    if r["finita"]:
        t.filas.append(Fila(["λef", "λ efectiva", Valor(r["lam_ef"], sufijo=" /h"),
                             "λ(M − L): llegadas reales por hora."], ("principal",), "lam_ef"))
        t.filas.append(Fila(["%op", "Fracción de la población operando", Valor(r["frac_operando"], "pct"),
                             "(M − L) ÷ M."], (), "frac_operando"))
    pw_det = " (vista por quien llega)." if r["finita"] else " (= P(n≥k))."
    secundarias = [
        ("1−Pw", "Probabilidad de no esperar", Valor(r["frac_no_espera"]), "Atendidos en cuanto llegan.",
         "frac_no_espera"),
        ("P(n<k)", "Algún servidor libre", Valor(r["Plt"]), "Uno o varios desocupados.", "Plt"),
        ("P(n≥k)", "Todos ocupados", Valor(r["Pk"]), "Proporción del tiempo con todos ocupados" + pw_det, "Pk"),
        ("P(n>k)", "Hay línea de espera", Valor(r["Pgt"]), "Al menos un cliente en cola.", "Pgt"),
        ("P(n=k)", "Todos ocupados y nadie esperando", Valor(r["p"][r["k_ef"]]), "", f"Pn:{r['k_ef']}"),
        ("Wn", "Espera de los que sí esperan", Valor(r["Wn"], "tiempo"), "Wq ÷ probabilidad de esperar.", "Wn"),
        ("Ln", "Clientes en cola no vacía", Valor(r["Ln"]), "Lq ÷ P(n>k).", "Ln"),
        ("Ociosos", "Servidores ociosos en promedio", Valor(r["ociosos"]), "Para el costo de ociosidad.",
         "ociosos"),
    ]
    t.filas += [Fila(list(f[:4]), (), f[4]) for f in secundarias]
    S = esc.p.S
    if S > 1:
        t.filas.append(Fila(["S·Lq", f"Clientes en cola ({S} sistemas)", Valor(S * r["Lq"]),
                             "Suma de las colas de los sistemas idénticos."], ("principal",), "S_Lq"))
        t.filas.append(Fila(["S·L", f"Clientes en el sistema ({S} sistemas)", Valor(S * r["L"]),
                             "En cola más en servicio, todos los sistemas."], (), "S_L"))
    return t


def tabla_probabilidades(esc, a, b):
    cols = [Columna("Probabilidad", False), Columna("Significado", False), Columna("Valor")]
    t = Tabla("Probabilidades", cols, mensaje_vacio="Sin resultados: el sistema es inestable.")
    if esc.r["ok"]:
        t.filas = [Fila([s, sig, Valor(v)], (), f"prob:{i}:{a}:{b}")
                   for i, (s, sig, v) in enumerate(mc.probabilidades_rango(esc.r, a, b))]
    return t


def tabla_distribucion(esc):
    cols = [Columna("n"), Columna("En cola"), Columna("Pn"), Columna("P(≤ n)"), Columna("P(≥ n)")]
    t = Tabla("Distribución de probabilidad", cols, mensaje_vacio="Sin resultados: el sistema es inestable.")
    if esc.r["ok"]:
        kk = esc.r["k_ef"]
        t.filas = [Fila([Valor(n, "entero"), Valor(c, "entero"), Valor(pn), Valor(ac), Valor(sup)],
                        ("actual",) if n == kk else (), f"dist:{n}")
                   for n, c, pn, ac, sup in mc.distribucion(esc.r)]
    return t


def tabla_por_dia(esc):
    cols = [Columna("Concepto", False), Columna("Por día (h)"), Columna("Por día (min)"), Columna("Por semana")]
    t = Tabla("Por día", cols, mensaje_vacio="Sin resultados: el sistema es inestable.")
    r, H, D = esc.r, esc.p.H, esc.p.D
    if not r["ok"]:
        return t
    for i, (concepto, horas) in enumerate(dc.horas_por_estado(r, H)):
        t.filas.append(Fila([concepto, Valor(horas), Valor(horas * 60), Valor(horas * D, sufijo=" h")],
                            (), f"horas:{i}"))
    for i, (concepto, n) in enumerate(dc.clientes_por_dia(r, H)):
        t.filas.append(Fila([concepto, Valor(n, sufijo=" clientes"), "", Valor(n * D, sufijo=" clientes")],
                            (), f"clientes:{i}"))
    for i, (concepto, v, tipo) in enumerate(dc.totales_sistemas(r, H, esc.p.S)):
        if tipo == "h":
            t.filas.append(Fila([concepto, Valor(v), Valor(v * 60), Valor(v * D, sufijo=" h")], (), f"sistemas:{i}"))
        else:
            t.filas.append(Fila([concepto, Valor(v, sufijo=" clientes"), "", Valor(v * D, sufijo=" clientes")],
                                (), f"sistemas:{i}"))
    return t


def tabla_costos(esc):
    cols = [Columna("Concepto", False), Columna("Por día"), Columna("Por semana"), Columna("Detalle", False)]
    t = Tabla("Costos", cols, mensaje_vacio="Sin resultados: el sistema es inestable.")
    c = esc.costos
    if c is None:
        return t
    D, H, S = esc.p.D, esc.p.H, esc.p.S
    base = esc.p.cfg["base_espera"]
    suma = f" (suma de {S} sistemas)" if S > 1 else ""
    filas = [
        ("CT(S) costo de servidores", c["ct_s"], "k × costo por servidor" + suma, "ct_s"),
        ("CT(TE) costo del tiempo de espera", c["ct_te"], f"{base} × horas × costo por hora" + suma, "ct_te"),
        ("Costo de ociosidad", c["ct_ocio"], "Servidores ociosos × horas × costo por hora" + suma, "ct_ocio"),
        ("CT costo total", c["ct"], Valor(c["ct"] / H, "dinero", sufijo=" por hora"), "ct"),
        ("Ingresos", c["ingreso"], "λ efectiva × horas × fracción × ingreso" + suma, "ingreso"),
    ]
    for concepto, v, detalle, clave in filas:
        etiquetas = ("principal",) if concepto.startswith("CT costo") else ()
        t.filas.append(Fila([concepto, Valor(v, "dinero"), Valor(v * D, "dinero"), detalle], etiquetas, clave))
    t.filas.append(Fila(["Rentabilidad (ingresos ÷ gastos)", Valor(c["rentabilidad"]), "",
                         Valor(c["ingreso"] - c["ct"], "dinero", prefijo="Utilidad diaria: ")], (), "rentabilidad"))
    return t


def contexto_graficas(esc, unidad_tiempo, mostrar_valores=True):
    """Datos que necesita visualization.graficas_colas.dibujar()."""
    p = esc.p
    sub = (f"λ = {p.lam:.4g}/h, μ = {p.mu:.4g}/h"
           + (f", M = {p.M}" if p.finita else "") + f", k actual = {p.k}")
    return {"finita": p.finita, "barrido_k": esc.barrido_k, "barrido_M": esc.barrido_M,
            "k": p.k, "M": p.M, "H": p.H, "unidad_tiempo": unidad_tiempo,
            "cfg": p.cfg, "subtitulo": sub, "mostrar_valores": mostrar_valores}
