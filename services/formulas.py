"""
formulas.py
«Cómo se calculó»: para un indicador de un Escenario devuelve su fórmula
(mathtext de matplotlib, sin LaTeX externo), la misma fórmula con los valores
sustituidos, el resultado y una explicación breve.

Reglas:
  * Las fórmulas son las que implementa domain/modelos_colas.py y domain/costos.py,
    y cambian según el modelo (M/M/1, M/M/k, población finita).
  * Todo valor sustituido sale del Escenario (esc.p, esc.r, esc.costos) o de las
    funciones del dominio que arman las tablas; el resultado mostrado es SIEMPRE
    el valor del dominio, nunca uno recalculado aquí. Los términos intermedios
    (p. ej. Σ aⁿ/n!) se leen de la distribución Pn del escenario: Pn / P0.
  * Se generan al pedirlas; no se guardan entre cálculos.

Claves: las de los indicadores ('rho', 'P0', 'Pw', 'Lq', ...), las de costos
('ct_s', 'ct_te', ...) y otras con parámetro: 'Pn:3', 'dist:3', 'prob:i:a:b',
'horas:i', 'clientes:i', 'sistemas:i' (ver Fila.clave en calculadora_service).
"""
from dataclasses import dataclass

from domain import costos as dc
from domain import modelos_colas as mc
from domain.unidades import ABREV, horas_por_unidad

from .tablas import Valor

MAX_TERMINOS = 4        # términos que se muestran al desarrollar una suma


@dataclass(frozen=True)
class Formula:
    clave: str
    titulo: str
    latex: str              # fórmula general (mathtext sin los $)
    pasos: tuple            # renglones con los valores sustituidos
    resultado: Valor        # valor del dominio, con su tipo para el Formateador
    explicacion: str
    extras: tuple = ()      # fórmulas relacionadas (p. ej. probabilidades acumuladas)


class FormulaNoDisponible(ValueError):
    """La clave no existe o no aplica al escenario (p. ej. sistema inestable)."""


# ----------------------------------------------------------------------------
# Utilidades de escritura
# ----------------------------------------------------------------------------
def _fr(num, den):
    return r"\frac{" + num + "}{" + den + "}"


def _pot(base, exp):
    return "{" + base + "}^{" + str(exp) + "}"


def _sub(nombre, i):
    return nombre + "_{" + str(i) + "}"


class _Ctx:
    """Escenario + formateador, con atajos para escribir números en mathtext."""

    def __init__(self, esc, fmt):
        self.esc, self.fmt = esc, fmt
        self.p, self.r, self.c = esc.p, esc.r, esc.costos
        self.finita = esc.p.finita
        self.k = self.r.get("k_ef", self.p.k)
        self.S = self.p.S

    def n(self, x, d=None):
        """Número con coma decimal; {,} evita el espacio que mathtext pone tras la coma."""
        t = self.fmt.num(x, d)
        return r"\mathrm{-}" if t == self.fmt.NO_DEFINIDO else t.replace(",", "{,}")

    def dinero(self, x, d=2):
        """Monto con 2 decimales; d=None usa los decimales elegidos (valores intermedios)."""
        return r"\$\," + self.n(x, d)

    def horas(self, h):
        """Tiempo en horas y, si se eligió otra unidad, también en esa unidad."""
        txt = self.n(h) + r"\ \mathrm{h}"
        u = self.fmt.unidad_tiempo
        if u != "hora":
            txt += " = " + self.n(self.fmt.a_unidad(h)) + r"\ \mathrm{" + ABREV[u] + "}"
        return txt

    def pn(self, i):
        p = self.r["p"]
        return p[i] if 0 <= i < len(p) else 0.0

    def cociente_p0(self, i):
        """Pn / P0: el coeficiente de Pn sin normalizar (aⁿ/n!, etc.), leído del escenario."""
        P0 = self.r["P0"]
        return self.pn(i) / P0 if P0 > 0 else float("nan")

    def acum(self, i):
        return mc.prob_acumulada(self.r["p"], i)

    def suma(self, lhs, terminos, valor):
        """Pasos de una suma desarrollada; si es larga, el resultado va en un segundo renglón."""
        if len(terminos) <= 2:
            return [lhs + " = " + self.desarrollo(terminos) + " = " + self.n(valor)]
        return [lhs + " = " + self.desarrollo(terminos), "= " + self.n(valor)]

    def desarrollo(self, terminos):
        """Suma desarrollada 'a + b + c + … ' con los primeros términos (lista de textos)."""
        if not terminos:
            return "0"
        if len(terminos) <= MAX_TERMINOS + 1:
            return " + ".join(terminos)
        return " + ".join(terminos[:MAX_TERMINOS]) + r" + \ldots"


def _f(clave, titulo, latex, pasos, resultado, explicacion, extras=()):
    return Formula(clave, titulo, latex, tuple(pasos), resultado, explicacion, tuple(extras))


# ----------------------------------------------------------------------------
# Medidas del modelo
# ----------------------------------------------------------------------------
def _rho(c):
    r, n = c.r, c.n
    if c.finita:
        nota = f" Como k > M, solo trabajan k = {c.k} servidores a la vez." if c.p.k > c.k else ""
        return _f("rho", "Utilización de los servidores ρ",
                  r"\rho = " + _fr(r"k - \bar{s}", "k") + r",\quad \bar{s} = \sum_{n=0}^{k-1}(k-n)\,P_n",
                  [r"\bar{s} = " + n(r["ociosos"]) + r"\ \mathrm{servidores\ ociosos}",
                   r"\rho = " + _fr(f"{c.k} - " + n(r["ociosos"]), str(c.k)) + " = " + n(r["util"])],
                  Valor(r["util"], "pct"),
                  "En población finita la utilización es la fracción de servidores ocupados en promedio: "
                  "k menos los servidores ociosos esperados, dividido entre k." + nota)
    if c.k == 1:
        latex, sust = r"\rho = " + _fr(r"\lambda", r"\mu"), _fr(n(r["lam"]), n(r["mu"]))
    else:
        latex = r"\rho = " + _fr(r"\lambda", r"k\,\mu")
        sust = _fr(n(r["lam"]), f"{c.k}" + r" \cdot " + n(r["mu"]))
    return _f("rho", "Utilización por servidor ρ", latex, [r"\rho = " + sust + " = " + n(r["rho"])],
              Valor(r["util"], "pct"),
              "Fracción del tiempo que cada servidor está ocupado. λ y μ están en clientes por hora. "
              "El sistema es estable solo si ρ < 1.")


def _p0(c):
    r, n, k = c.r, c.n, c.k
    if c.finita:
        s1 = sum(c.cociente_p0(i) for i in range(0, k + 1))
        s2 = sum(c.cociente_p0(i) for i in range(k + 1, c.p.M + 1))
        latex = (r"P_0 = \left[\sum_{n=0}^{k}" + _fr("M!", r"(M-n)!\,n!") + r"\,r^n + \sum_{n=k+1}^{M}"
                 + _fr("M!", r"(M-n)!\,k!\,k^{n-k}") + r"\,r^n\right]^{-1}")
        pasos = [r"r = \lambda/\mu = " + n(r["a"]) + r",\quad M = " + str(c.p.M) + r",\quad k = " + str(k),
                 r"\sum_{n=0}^{" + str(k) + "} = " + n(s1) + r",\quad \sum_{n=" + str(k + 1) + "}^{"
                 + str(c.p.M) + "} = " + n(s2),
                 r"P_0 = " + _fr("1", n(s1) + " + " + n(s2)) + " = " + n(r["P0"])]
        expl = ("Probabilidad de que no haya unidades en el sistema (población finita). r = λ/μ con λ la tasa de "
                "llegada de cada unidad. Las sumas son los términos de Pn antes de normalizar.")
    elif k == 1:
        latex = r"P_0 = 1 - \rho"
        pasos = [r"P_0 = 1 - " + n(r["rho"]) + " = " + n(r["P0"])]
        expl = "Probabilidad de que el sistema esté vacío (caso k = 1 de la fórmula general M/M/k)."
    else:
        suma = sum(c.cociente_p0(i) for i in range(k))
        cola = r["Pk"] / r["P0"] if r["P0"] > 0 else float("nan")
        latex = (r"P_0 = \left[\sum_{n=0}^{k-1}" + _fr("a^n", "n!") + " + " + _fr("a^k", "k!") + r"\cdot"
                 + _fr("1", r"1-\rho") + r"\right]^{-1},\quad a = " + _fr(r"\lambda", r"\mu"))
        pasos = [r"a = " + n(r["a"]) + r",\quad \rho = " + n(r["rho"]),
                 r"\sum_{n=0}^{" + str(k - 1) + "}" + _fr("a^n", "n!") + " = " + n(suma) + r",\quad "
                 + _fr(_pot("a", k), f"{k}!") + r"\cdot" + _fr("1", "1-" + n(r["rho"])) + " = " + n(cola),
                 r"P_0 = " + _fr("1", n(suma) + " + " + n(cola)) + " = " + n(r["P0"])]
        expl = "Probabilidad de que no haya clientes en el sistema M/M/k (a = λ/μ es el tráfico ofrecido)."
    return _f("P0", "Probabilidad de sistema vacío P0", latex, pasos, Valor(r["P0"]), expl)


def _pw(c):
    r, n, k = c.r, c.n, c.k
    if c.finita:
        num = sum((c.p.M - i) * c.pn(i) for i in range(k, c.p.M + 1))
        return _f("Pw", "Probabilidad de esperar Pw",
                  r"P_w = " + _fr(r"\sum_{n=k}^{M}(M-n)\,P_n", r"\sum_{n=0}^{M}(M-n)\,P_n") + " = "
                  + _fr(r"\sum_{n=k}^{M}(M-n)\,P_n", "M-L"),
                  [r"P_w = " + _fr(n(num), n(r["operando"])) + " = " + n(r["frac_espera"])],
                  Valor(r["frac_espera"]),
                  "Probabilidad de que una unidad que llega encuentre todos los servidores ocupados. En población "
                  "finita las llegadas son proporcionales a las unidades fuera del sistema (M − n).")
    if k == 1:
        return _f("Pw", "Probabilidad de esperar Pw", r"P_w = P(n \geq 1) = \rho",
                  [r"P_w = " + n(r["rho"])], Valor(r["frac_espera"]),
                  "En M/M/1 un cliente espera si el servidor está ocupado, lo que ocurre una fracción ρ del tiempo.")
    ak = c.cociente_p0(k)
    kmu = f"{k}" + r"\cdot " + n(r["mu"])
    factor = k * r["mu"] / (k * r["mu"] - r["lam"])
    return _f("Pw", "Probabilidad de esperar Pw (Erlang C)",
              r"P_w = " + _fr("a^k", "k!") + r"\cdot" + _fr(r"k\mu", r"k\mu-\lambda") + r"\cdot P_0",
              [_fr(_pot("a", k), f"{k}!") + " = " + _fr(_pot(n(r["a"]), k), f"{k}!") + " = " + n(ak),
               _fr(r"k\mu", r"k\mu-\lambda") + " = " + _fr(kmu, kmu + " - " + n(r["lam"])) + " = " + n(factor),
               r"P_w = " + n(ak) + r"\cdot " + n(factor) + r"\cdot " + n(r["P0"]) + " = " + n(r["frac_espera"])],
              Valor(r["frac_espera"]),
              "Fórmula de Erlang C: probabilidad de que un cliente que llega encuentre los k servidores ocupados "
              "y deba hacer cola. Es igual a P(n ≥ k).")


def _lq(c):
    r, n, k = c.r, c.n, c.k
    if c.finita:
        terminos = [f"{i - k}" + r"\cdot " + n(c.pn(i)) for i in range(k + 1, c.p.M + 1)]
        return _f("Lq", "Clientes en cola Lq", r"L_q = \sum_{n=k+1}^{M}(n-k)\,P_n",
                  c.suma(r"L_q", terminos, r["Lq"]), Valor(r["Lq"]),
                  "Número medio de unidades esperando: cada estado con n > k aporta n − k unidades en cola, "
                  "ponderado por su probabilidad.")
    if k == 1:
        return _f("Lq", "Clientes en cola Lq", r"L_q = " + _fr(r"\rho^2", r"1-\rho"),
                  [r"L_q = " + _fr(_pot(n(r["rho"]), 2), "1 - " + n(r["rho"])) + " = " + n(r["Lq"])],
                  Valor(r["Lq"]), "Número medio de clientes esperando en la cola de un M/M/1.")
    ak = c.cociente_p0(k)
    return _f("Lq", "Clientes en cola Lq",
              r"L_q = P_0\cdot" + _fr("a^k", "k!") + r"\cdot" + _fr(r"\rho", r"(1-\rho)^2"),
              [r"L_q = " + n(r["P0"]) + r"\cdot " + n(ak) + r"\cdot" + _fr(n(r["rho"]), "(1 - " + n(r["rho"]) + ")^2")
               + " = " + n(r["Lq"])],
              Valor(r["Lq"]), "Número medio de clientes esperando en la cola de un M/M/k (a = λ/μ).")


def _l(c):
    r, n = c.r, c.n
    if c.finita:
        terminos = [f"{i}" + r"\cdot " + n(c.pn(i)) for i in range(1, c.p.M + 1)]
        return _f("L", "Clientes en el sistema L", r"L = \sum_{n=0}^{M} n\,P_n",
                  c.suma(r"L", terminos, r["L"]), Valor(r["L"]),
                  "Número medio de unidades en el sistema (en cola más en servicio).")
    return _f("L", "Clientes en el sistema L", r"L = L_q + " + _fr(r"\lambda", r"\mu"),
              [r"L = " + n(r["Lq"]) + " + " + _fr(n(r["lam"]), n(r["mu"])) + " = " + n(r["L"])], Valor(r["L"]),
              "Clientes en cola más los que están siendo atendidos (λ/μ servidores ocupados en promedio).")


def _paso_lam_ef(c):
    r, n = c.r, c.n
    return r"\lambda_{ef} = \lambda\,(M-L) = " + n(r["lam"]) + r"\cdot " + n(r["operando"]) + " = " + n(r["lam_ef"])


def _wq(c):
    r, n = c.r, c.n
    if c.finita:
        return _f("Wq", "Tiempo en cola Wq", r"W_q = " + _fr("L_q", r"\lambda_{ef}") + r",\quad \lambda_{ef} = "
                  r"\lambda\,(M-L)",
                  [_paso_lam_ef(c), r"W_q = " + _fr(n(r["Lq"]), n(r["lam_ef"])) + " = " + c.horas(r["Wq"])],
                  Valor(r["Wq"], "tiempo"),
                  "Ley de Little con la tasa de llegadas efectiva (solo llegan las unidades que están fuera "
                  "del sistema). Las tasas están por hora, así que el tiempo sale en horas.")
    return _f("Wq", "Tiempo en cola Wq", r"W_q = " + _fr("L_q", r"\lambda"),
              [r"W_q = " + _fr(n(r["Lq"]), n(r["lam"])) + " = " + c.horas(r["Wq"])], Valor(r["Wq"], "tiempo"),
              "Ley de Little: espera media en la cola. λ está en clientes por hora, así que el tiempo sale en horas.")


def _w(c):
    r, n = c.r, c.n
    if c.finita:
        return _f("W", "Tiempo en el sistema W", r"W = " + _fr("L", r"\lambda_{ef}"),
                  [_paso_lam_ef(c), r"W = " + _fr(n(r["L"]), n(r["lam_ef"])) + " = " + c.horas(r["W"])],
                  Valor(r["W"], "tiempo"), "Ley de Little con la tasa de llegadas efectiva λ(M − L).")
    return _f("W", "Tiempo en el sistema W", r"W = W_q + " + _fr("1", r"\mu"),
              [r"W = " + n(r["Wq"]) + " + " + _fr("1", n(r["mu"])) + " = " + c.horas(r["W"])],
              Valor(r["W"], "tiempo"), "Espera en cola más el tiempo medio de servicio 1/μ (en horas).")


def _pn(c, i, clave=None, titulo=None, resultado=None):
    """Pn con la fórmula del modelo; resultado = Pn del escenario (o el valor dado por la tabla)."""
    r, n, k = c.r, c.n, c.k
    valor = c.pn(i) if resultado is None else resultado
    if c.finita:
        M = c.p.M
        if i <= k:
            latex = r"P_n = " + _fr("M!", r"(M-n)!\,n!") + r"\,r^n\,P_0\quad (n \leq k)"
            coef = _fr(f"{M}!", f"{M - i}!" + r"\," + f"{i}!")
        else:
            latex = r"P_n = " + _fr("M!", r"(M-n)!\,k!\,k^{n-k}") + r"\,r^n\,P_0\quad (n > k)"
            coef = _fr(f"{M}!", f"{M - i}!" + r"\," + f"{k}!" + r"\," + _pot(str(k), i - k))
        pasos = [_sub("P", i) + " = " + coef + r"\cdot " + _pot(n(r["a"]), i) + r"\cdot " + n(r["P0"])
                 + " = " + n(valor)]
        expl = (f"Probabilidad de que haya exactamente {i} unidades en el sistema (población finita, M = {M}, "
                f"r = λ/μ por unidad).")
    elif k == 1:
        latex = r"P_n = \rho^n\,P_0"
        pasos = [_sub("P", i) + " = " + _pot(n(r["rho"]), i) + r"\cdot " + n(r["P0"]) + " = " + n(valor)]
        expl = f"Probabilidad de que haya exactamente {i} clientes en un M/M/1."
    elif i < k:
        latex = r"P_n = " + _fr("a^n", "n!") + r"\,P_0\quad (n < k)"
        pasos = [_sub("P", i) + " = " + _fr(_pot(n(r["a"]), i), f"{i}!") + r"\cdot " + n(r["P0"]) + " = " + n(valor)]
        expl = f"Probabilidad de que haya exactamente {i} clientes (menos que k: todos son atendidos)."
    else:
        latex = r"P_n = " + _fr("a^n", r"k!\,k^{n-k}") + r"\,P_0\quad (n \geq k)"
        pasos = [_sub("P", i) + " = " + _fr(_pot(n(r["a"]), i), f"{k}!" + r"\cdot " + _pot(str(k), i - k))
                 + r"\cdot " + n(r["P0"]) + " = " + n(valor)]
        expl = f"Probabilidad de que haya exactamente {i} clientes (k ocupados y {i - k} en cola)."
    return _f(clave or f"Pn:{i}", titulo or f"Probabilidad de {i} en el sistema P{i}", latex, pasos,
              Valor(valor), expl)


def _suma_p(c, desde, hasta, nombre, valor, explicacion, clave):
    """P(desde ≤ n ≤ hasta) como suma de Pn."""
    terminos = [c.n(c.pn(i)) for i in range(desde, hasta + 1)]
    latex = nombre + r" = \sum_{n=" + str(desde) + "}^{" + str(hasta) + "} P_n"
    return _f(clave, nombre.replace(r"\leq", "≤").replace(r"\geq", "≥"), latex,
              c.suma(nombre, terminos, valor), Valor(valor), explicacion)


def _complemento(c, latex_nombre, hasta, valor, explicacion, clave, titulo):
    """1 − P(n ≤ hasta)."""
    return _f(clave, titulo, latex_nombre + r" = 1 - P(n \leq " + str(hasta) + ")",
              [latex_nombre + " = 1 - " + c.n(c.acum(hasta)) + " = " + c.n(valor)], Valor(valor), explicacion)


def _acumuladas(c, i):
    filas = {f[0]: f for f in mc.distribucion(c.r)}
    if i not in filas:
        raise FormulaNoDisponible(f"La distribución mostrada no incluye n = {i}.")
    menor_igual, mayor_igual = filas[i][3], filas[i][4]
    extras = [_suma_p(c, 0, i, r"P(n \leq " + str(i) + ")", menor_igual,
                      f"Probabilidad de que haya como máximo {i} en el sistema.", f"acum:{i}")]
    if i == 0:
        extras.append(_f(f"sup:{i}", "P(n ≥ 0)", r"P(n \geq 0) = 1", [r"P(n \geq 0) = 1"], Valor(mayor_igual),
                         "Siempre hay 0 o más clientes."))
    else:
        extras.append(_complemento(c, r"P(n \geq " + str(i) + ")", i - 1, mayor_igual,
                                   f"Probabilidad de que haya al menos {i} en el sistema.", f"sup:{i}",
                                   f"P(n ≥ {i})"))
    return extras


def _dist(c, i):
    base = _pn(c, i, clave=f"dist:{i}")
    return Formula(base.clave, base.titulo, base.latex, base.pasos, base.resultado, base.explicacion,
                   tuple(_acumuladas(c, i)))


def _prob(c, i, a, b):
    """Filas de mc.probabilidades_rango(r, a, b) (pestaña Probabilidades)."""
    simbolo, significado, v = mc.probabilidades_rango(c.r, a, b)[i]
    k, clave = c.k, f"prob:{i}:{a}:{b}"
    titulo = f"{simbolo}: {significado.lower()}"
    if i == 0:
        return _pn(c, a, clave, titulo, v)
    if i == 1:
        return _suma_p(c, 0, a, r"P(n \leq " + str(a) + ")", v, significado + ".", clave)
    if i in (2, 3):
        hasta = a - 1 if i == 2 else a
        nombre = (r"P(n \geq " if i == 2 else "P(n > ") + str(a) + ")"
        if hasta < 0:
            return _f(clave, titulo, nombre + " = 1", [nombre + " = 1"], Valor(v), "Siempre hay 0 o más clientes.")
        return _complemento(c, nombre, hasta, v, significado + ".", clave, titulo)
    if i == 4:
        nombre = "P(" + str(a) + r" \leq n \leq " + str(b) + ")"
        return _f(clave, titulo, nombre + r" = P(n \leq " + str(b) + r") - P(n \leq " + str(a - 1) + ")",
                  [nombre + " = " + c.n(c.acum(b)) + " - " + c.n(c.acum(a - 1)) + " = " + c.n(v)], Valor(v),
                  significado + ".")
    # Probabilidades de la cola: cola = n − k
    cola = r"\mathrm{cola}"
    if i == 5:
        if a == 0:
            return _suma_p(c, 0, k, r"P(n \leq " + str(k) + ")", v,
                           "Nadie espera cuando hay k o menos clientes en el sistema.", clave)
        return _pn(c, k + a, clave, titulo, v)
    if i == 6:
        nombre = "P(" + cola + r" \geq " + str(a) + ")"
        if a == 0:
            return _f(clave, titulo, nombre + " = 1", [nombre + " = 1"], Valor(v), "La cola nunca es negativa.")
        return _complemento(c, nombre, k + a - 1, v, significado + f" (n ≥ k + {a}).", clave, titulo)
    if i == 7:
        return _complemento(c, "P(" + cola + " > " + str(a) + ")", k + a, v, significado + ".", clave, titulo)
    if i == 8:
        nombre = "P(" + cola + r" \leq " + str(a) + ")"
        return _f(clave, titulo, nombre + r" = P(n \leq k + " + str(a) + ")",
                  [nombre + r" = P(n \leq " + str(k + a) + ") = " + c.n(v)], Valor(v), significado + ".")
    nombre = "P(" + str(a) + r" \leq " + cola + r" \leq " + str(b) + ")"
    if a == 0:
        return _f(clave, titulo, nombre + r" = P(n \leq k + " + str(b) + ")",
                  [nombre + " = " + c.n(c.acum(k + b)) + " = " + c.n(v)], Valor(v), significado + ".")
    return _f(clave, titulo, nombre + r" = P(n \leq k + b) - P(n \leq k + a - 1)",
              [nombre + " = " + c.n(c.acum(k + b)) + " - " + c.n(c.acum(k + a - 1)) + " = " + c.n(v)],
              Valor(v), significado + ".")


def _plt(c):
    r, n = c.r, c.n
    return _f("Plt", "Algún servidor libre P(n<k)", r"P(n<k) = \sum_{n=0}^{k-1}P_n = 1 - P(n \geq k)",
              [r"P(n<k) = 1 - " + n(r["Pk"]) + " = " + n(r["Plt"])], Valor(r["Plt"]),
              "Probabilidad de que al menos un servidor esté desocupado.")


def _pk(c):
    r, n, k = c.r, c.n, c.k
    if c.finita:
        terminos = [n(c.pn(i)) for i in range(k, c.p.M + 1)]
        return _f("Pk", "Todos ocupados P(n≥k)", r"P(n \geq k) = \sum_{n=k}^{M}P_n",
                  c.suma(r"P(n \geq " + str(k) + ")", terminos, r["Pk"]), Valor(r["Pk"]),
                  "Fracción del tiempo con todos los servidores ocupados. En población finita no coincide con la "
                  "probabilidad de esperar vista por quien llega (Pw).")
    cola = r["Pk"] / r["P0"] if r["P0"] > 0 else float("nan")
    return _f("Pk", "Todos ocupados P(n≥k)",
              r"P(n \geq k) = " + _fr("a^k", "k!") + r"\cdot" + _fr("1", r"1-\rho") + r"\cdot P_0",
              [r"P(n \geq " + str(k) + ") = " + n(cola) + r"\cdot " + n(r["P0"]) + " = " + n(r["Pk"])],
              Valor(r["Pk"]), "Fracción del tiempo con los k servidores ocupados; en población infinita es Pw.")


def _pgt(c):
    r, n, k = c.r, c.n, c.k
    if c.finita:
        terminos = [n(c.pn(i)) for i in range(k + 1, c.p.M + 1)]
        return _f("Pgt", "Hay línea de espera P(n>k)", r"P(n > k) = \sum_{n=k+1}^{M}P_n",
                  c.suma(r"P(n > " + str(k) + ")", terminos, r["Pgt"]), Valor(r["Pgt"]),
                  "Probabilidad de que haya al menos una unidad esperando.")
    return _f("Pgt", "Hay línea de espera P(n>k)", r"P(n > k) = P(n \geq k)\cdot\rho",
              [r"P(n > " + str(k) + ") = " + n(r["Pk"]) + r"\cdot " + n(r["rho"]) + " = " + n(r["Pgt"])],
              Valor(r["Pgt"]), "Probabilidad de que haya al menos un cliente esperando en cola.")


def _no_espera(c):
    r, n = c.r, c.n
    return _f("frac_no_espera", "Probabilidad de no esperar", r"P(\mathrm{no\ esperar}) = 1 - P_w",
              [r"P(\mathrm{no\ esperar}) = 1 - " + n(r["frac_espera"]) + " = " + n(r["frac_no_espera"])],
              Valor(r["frac_no_espera"]),
              "Fracción de clientes que son atendidos en cuanto llegan.")


def _wn(c):
    r, n, k = c.r, c.n, c.k
    if c.finita:
        return _f("Wn", "Espera de los que sí esperan Wn", r"W_n = " + _fr("W_q", "P_w"),
                  [r"W_n = " + _fr(n(r["Wq"]), n(r["frac_espera"])) + " = " + c.horas(r["Wn"])],
                  Valor(r["Wn"], "tiempo"), "Espera media en cola contando solo a quienes deben esperar.")
    return _f("Wn", "Espera de los que sí esperan Wn", r"W_n = " + _fr("1", r"k\mu - \lambda"),
              [r"W_n = " + _fr("1", f"{k}" + r"\cdot " + n(r["mu"]) + " - " + n(r["lam"])) + " = " + c.horas(r["Wn"])],
              Valor(r["Wn"], "tiempo"), "Espera media en cola de los clientes que sí deben esperar (en horas).")


def _ln(c):
    r, n = c.r, c.n
    return _f("Ln", "Clientes en cola no vacía Ln", r"L_n = " + _fr("L_q", "P(n > k)"),
              [r"L_n = " + _fr(n(r["Lq"]), n(r["Pgt"])) + " = " + n(r["Ln"])], Valor(r["Ln"]),
              "Longitud media de la cola cuando hay al menos un cliente esperando.")


def _ociosos(c):
    r, n, k = c.r, c.n, c.k
    if c.finita:
        terminos = [f"{k - i}" + r"\cdot " + n(c.pn(i)) for i in range(k)]
        return _f("ociosos", "Servidores ociosos en promedio", r"\bar{s} = \sum_{n=0}^{k-1}(k-n)\,P_n",
                  c.suma(r"\bar{s}", terminos, r["ociosos"]), Valor(r["ociosos"]),
                  "Servidores desocupados en promedio: con n < k hay k − n libres.")
    return _f("ociosos", "Servidores ociosos en promedio", r"\bar{s} = k - " + _fr(r"\lambda", r"\mu"),
              [r"\bar{s} = " + str(k) + " - " + _fr(n(r["lam"]), n(r["mu"])) + " = " + n(r["ociosos"])],
              Valor(r["ociosos"]), "Servidores contratados menos los ocupados en promedio (λ/μ).")


def _operando(c):
    r, n = c.r, c.n
    return _f("operando", "Unidades operando M − L", r"M - L = \sum_{n=0}^{M}(M-n)\,P_n",
              [r"M - L = " + str(c.p.M) + " - " + n(r["L"]) + " = " + n(r["operando"])], Valor(r["operando"]),
              "Unidades de la población que están fuera del sistema (funcionando).")


def _lam_ef(c):
    return _f("lam_ef", "λ efectiva", r"\lambda_{ef} = \lambda\,(M-L)", [_paso_lam_ef(c)],
              Valor(c.r["lam_ef"], sufijo=" /h"), "Llegadas reales por hora: solo llegan las unidades que operan.")


def _frac_operando(c):
    r, n = c.r, c.n
    return _f("frac_operando", "Fracción de la población operando", _fr("M-L", "M"),
              [_fr(n(r["operando"]), str(c.p.M)) + " = " + n(r["frac_operando"])], Valor(r["frac_operando"], "pct"),
              "Proporción de unidades de la población fuera del sistema.")


def _s_mult(c, clave, simbolo, nombre, valor_uno, total):
    return _f(clave, f"{nombre} de los {c.S} sistemas", "S \\cdot " + simbolo,
              [str(c.S) + r"\cdot " + c.n(valor_uno) + " = " + c.n(total)], Valor(total),
              f"Los {c.S} sistemas son idénticos e independientes: el total es S veces el de uno.")


# ----------------------------------------------------------------------------
# Costos (domain.costos.costos)
# ----------------------------------------------------------------------------
def _pref_S(c):
    """Factor S en las fórmulas de costos (solo si hay varios sistemas)."""
    return ("S\\cdot ", f"{c.S}" + r"\cdot ") if c.S > 1 else ("", "")


def _nota_S(c):
    return f" Se suman los {c.S} sistemas idénticos." if c.S > 1 else ""


def _ct_s(c):
    cfg, H, k = c.p.cfg, c.p.H, c.r["k"]
    s, sv = _pref_S(c)
    if cfg["c_servidor_u"] == "hora":
        latex = r"CT(S) = " + s + r"k\cdot C_s\cdot H"
        paso = sv + f"{k}" + r"\cdot " + c.dinero(cfg["c_servidor"]) + r"\cdot " + c.n(H)
        expl = "Costo diario de los k servidores contratados: costo por hora × horas de operación."
    else:
        latex = r"CT(S) = " + s + r"k\cdot C_s"
        paso = sv + f"{k}" + r"\cdot " + c.dinero(cfg["c_servidor"])
        expl = "Costo diario de los k servidores contratados (costo por día de cada uno)."
    return _f("ct_s", "CT(S) costo de servidores", latex, [r"CT(S) = " + paso + " = " + c.dinero(c.c["ct_s"])],
              Valor(c.c["ct_s"], "dinero"), expl + _nota_S(c))


def _ct_te(c):
    cfg, H, r = c.p.cfg, c.p.H, c.r
    s, sv = _pref_S(c)
    base = cfg["base_espera"]
    simb = "L_q" if base == "Lq" else "L"
    cw_hora = cfg["c_espera"] / horas_por_unidad(cfg["c_espera_u"], H)
    pasos = []
    if cfg["c_espera_u"] != "hora":
        pasos.append(r"C_w = " + _fr(c.dinero(cfg["c_espera"]), c.n(horas_por_unidad(cfg["c_espera_u"], H))
                                     + r"\ \mathrm{h}") + " = " + c.dinero(cw_hora, None) + r"\ \mathrm{por\ hora}")
    pasos.append(r"CT(TE) = " + sv + c.n(r[base]) + r"\cdot " + c.n(H) + r"\cdot " + c.dinero(cw_hora, None)
                 + " = " + c.dinero(c.c["ct_te"]))
    return _f("ct_te", "CT(TE) costo del tiempo de espera", r"CT(TE) = " + s + simb + r"\cdot H\cdot C_w", pasos,
              Valor(c.c["ct_te"], "dinero"),
              f"Clientes en {'cola' if base == 'Lq' else 'el sistema'} en promedio × horas de operación × costo por "
              "hora de espera de cada cliente." + _nota_S(c))


def _ct_ocio(c):
    cfg, H, r = c.p.cfg, c.p.H, c.r
    s, sv = _pref_S(c)
    return _f("ct_ocio", "Costo de ociosidad", r"CT(ocio) = " + s + r"\bar{s}\cdot H\cdot C_{ocio}",
              [r"CT(ocio) = " + sv + c.n(r["ociosos"]) + r"\cdot " + c.n(H) + r"\cdot " + c.dinero(cfg["c_ocio"])
               + " = " + c.dinero(c.c["ct_ocio"])],
              Valor(c.c["ct_ocio"], "dinero"),
              "Servidores ociosos en promedio × horas × costo por hora de servidor ocioso." + _nota_S(c))


def _ct(c):
    m = c.c
    return _f("ct", "CT costo total diario", r"CT = CT(S) + CT(TE) + CT(ocio)",
              [r"CT = " + c.dinero(m["ct_s"]) + " + " + c.dinero(m["ct_te"]) + " + " + c.dinero(m["ct_ocio"])
               + " = " + c.dinero(m["ct"])],
              Valor(m["ct"], "dinero"), "Costo total por día de operación." + _nota_S(c),
              (_ct_s(c), _ct_te(c), _ct_ocio(c)))


def _ingreso(c):
    cfg, H, r = c.p.cfg, c.p.H, c.r
    s, sv = _pref_S(c)
    lam = r"\lambda_{ef}" if c.finita else r"\lambda"
    return _f("ingreso", "Ingresos diarios", r"I = " + s + lam + r"\cdot H\cdot f\cdot I_c",
              [r"I = " + sv + c.n(r["lam_ef"]) + r"\cdot " + c.n(H) + r"\cdot " + c.n(cfg["frac_ingreso"])
               + r"\cdot " + c.dinero(cfg["ingreso"]) + " = " + c.dinero(c.c["ingreso"])],
              Valor(c.c["ingreso"], "dinero"),
              "Clientes que llegan por día × fracción que genera ingreso × ingreso por cliente." + _nota_S(c))


def _rentabilidad(c):
    m = c.c
    return _f("rentabilidad", "Rentabilidad", r"\mathrm{Rentabilidad} = " + _fr("I", "CT"),
              [r"\mathrm{Rentabilidad} = " + _fr(c.dinero(m["ingreso"]), c.dinero(m["ct"])) + " = "
               + c.n(m["rentabilidad"])],
              Valor(m["rentabilidad"]), "Ingresos por cada peso de costo total (no definida si CT = 0).")


# ----------------------------------------------------------------------------
# Operación diaria (domain.costos.horas_por_estado / clientes_por_dia / totales_sistemas)
# ----------------------------------------------------------------------------
# (fórmula, clave del factor en r; None = servidores ocupados k − ociosos)
_HORAS = [
    (r"P_0\cdot H", "P0"), (r"P(n<k)\cdot H", "Plt"), (r"P(n \geq k)\cdot H", "Pk"), (r"P(n > k)\cdot H", "Pgt"),
    (r"\bar{s}\cdot H", "ociosos"), (r"(k - \bar{s})\cdot H", None), (r"L_q\cdot H", "Lq"), (r"L\cdot H", "L"),
]


def _horas(c, i):
    concepto, horas = dc.horas_por_estado(c.r, c.p.H)[i]
    latex, clave = _HORAS[i]
    if clave is None:
        factor = f"({c.k} - " + c.n(c.r["ociosos"]) + ")"
    else:
        factor = c.n(c.r[clave])
    return _f(f"horas:{i}", concepto, latex, [factor + r"\cdot " + c.n(c.p.H) + " = " + c.n(horas) + r"\ \mathrm{h}"],
              Valor(horas, sufijo=" h"),
              "Tiempo por día en ese estado = probabilidad (o promedio) × horas de operación H.")


def _clientes(c, i):
    concepto, v = dc.clientes_por_dia(c.r, c.p.H)[i]
    r, H, n = c.r, c.p.H, c.n
    lam = r"\lambda_{ef}" if c.finita else r"\lambda"
    latex = [lam + r"\cdot H", lam + r"\cdot H\cdot P_w", lam + r"\cdot H\cdot (1 - P_w)"][i]
    base = n(r["lam_ef"]) + r"\cdot " + n(H)
    paso = [base, base + r"\cdot " + n(r["frac_espera"]), base + r"\cdot " + n(r["frac_no_espera"])][i]
    return _f(f"clientes:{i}", concepto, latex, [paso + " = " + n(v)], Valor(v, sufijo=" clientes"),
              "Llegadas por día = tasa de llegadas (por hora) × horas de operación.")


def _sistemas(c, i):
    filas = dc.totales_sistemas(c.r, c.p.H, c.S)
    if i >= len(filas):
        raise FormulaNoDisponible("Solo hay totales de sistemas cuando S > 1.")
    concepto, v, tipo = filas[i]
    r, H, n, S = c.r, c.p.H, c.n, str(c.S)
    lam = r"\lambda_{ef}" if c.finita else r"\lambda"
    formulas = [
        (r"S\cdot L_q", S + r"\cdot " + n(r["Lq"])),
        (r"S\cdot \bar{s}\cdot H", S + r"\cdot " + n(r["ociosos"]) + r"\cdot " + n(H)),
        (r"P_0^{\,S}\cdot H", _pot(n(r["P0"]), S) + r"\cdot " + n(H)),
        (r"S\cdot L_q\cdot H", S + r"\cdot " + n(r["Lq"]) + r"\cdot " + n(H)),
        (r"S\cdot " + lam + r"\cdot H", S + r"\cdot " + n(r["lam_ef"]) + r"\cdot " + n(H)),
        (r"S\cdot " + lam + r"\cdot H\cdot P_w",
         S + r"\cdot " + n(r["lam_ef"]) + r"\cdot " + n(H) + r"\cdot " + n(r["frac_espera"])),
    ]
    latex, paso = formulas[i]
    unidad = r"\ \mathrm{h}" if tipo == "h" else ""
    expl = ("Los sistemas son independientes: todos vacíos a la vez tiene probabilidad P0 elevada a S."
            if i == 2 else "Los sistemas son idénticos e independientes: el total es S veces el de uno.")
    return _f(f"sistemas:{i}", concepto, latex, [paso + " = " + n(v) + unidad],
              Valor(v, sufijo=" h" if tipo == "h" else " clientes"), expl)


# ----------------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------------
_SIMPLES = {
    "rho": _rho, "P0": _p0, "Pw": _pw, "Lq": _lq, "L": _l, "Wq": _wq, "W": _w,
    "Plt": _plt, "Pk": _pk, "Pgt": _pgt, "frac_no_espera": _no_espera, "Wn": _wn, "Ln": _ln, "ociosos": _ociosos,
    "S_Lq": lambda c: _s_mult(c, "S_Lq", "L_q", "Clientes en cola", c.r["Lq"], c.S * c.r["Lq"]),
    "S_L": lambda c: _s_mult(c, "S_L", "L", "Clientes en el sistema", c.r["L"], c.S * c.r["L"]),
}
_SOLO_FINITA = {"operando": _operando, "lam_ef": _lam_ef, "frac_operando": _frac_operando}
_COSTOS = {"ct_s": _ct_s, "ct_te": _ct_te, "ct_ocio": _ct_ocio, "ct": _ct, "ingreso": _ingreso,
           "rentabilidad": _rentabilidad}
_CON_PARAMETRO = {"Pn": lambda c, i: _pn(c, i), "dist": _dist, "horas": _horas, "clientes": _clientes,
                  "sistemas": _sistemas}


def formula(esc, clave, fmt):
    """
    Formula del indicador `clave` para el escenario `esc`; `fmt` (services.tablas.Formateador)
    da el formato de los números. Lanza FormulaNoDisponible si no aplica.
    """
    if not esc.r["ok"]:
        raise FormulaNoDisponible("El sistema es inestable con estos datos: no hay resultados que explicar.")
    c = _Ctx(esc, fmt)
    if clave in _SIMPLES:
        return _SIMPLES[clave](c)
    if clave in _SOLO_FINITA:
        if not c.finita:
            raise FormulaNoDisponible("Esta medida solo aplica a población finita.")
        return _SOLO_FINITA[clave](c)
    if clave in _COSTOS:
        return _COSTOS[clave](c)
    nombre, _, resto = clave.partition(":")
    try:
        args = [int(x) for x in resto.split(":")] if resto else []
    except ValueError:
        args = None
    if nombre == "prob" and args and len(args) == 3:
        return _prob(c, *args)
    if nombre in _CON_PARAMETRO and args and len(args) == 1 and args[0] >= 0:
        return _CON_PARAMETRO[nombre](c, args[0])
    raise FormulaNoDisponible(f"No hay fórmula para «{clave}».")
