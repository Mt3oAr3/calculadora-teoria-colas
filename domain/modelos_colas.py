"""
modelos_colas.py
Fórmulas de teoría de colas (llegadas Poisson, servicio exponencial):

    PICS  -> M/M/1        Población infinita, canal simple
    PICM  -> M/M/k        Población infinita, canal múltiple
    PFCS  -> M/M/1/M/M    Población finita, canal simple
    PFCM  -> M/M/k/M/M    Población finita, canal múltiple

Todas las tasas se trabajan internamente en clientes por HORA y todos los
tiempos se devuelven en HORAS (ver domain/unidades.py).

Nota numérica: los términos a^n/n! (infinita) y M!/((M-n)! ...) r^n (finita)
crecen muy rápido; con M = 300 superan el máximo de un float (~1e308). Por eso
se calculan en escala logarítmica y se normalizan al final. Matemáticamente
las fórmulas son las mismas que en la versión original.
"""
import math

from .errores import ErrorModelo

# Límite de términos de la distribución Pn en población infinita (cola teórica infinita).
MAX_TERMINOS_DISTRIBUCION = 5000
# Tolerancia para decidir estabilidad: un ρ que difiere de 1 en menos de esto
# es 1 en aritmética de punto flotante (p. ej. 0.3/0.1 = 2.9999999999999996).
TOLERANCIA_ESTABILIDAD = 1e-12


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def _validar_parametros(lam, mu, k, M=None, requiere_M=False):
    """Rechaza parámetros sin sentido en el modelo (no los corrige)."""
    for nombre, v in (("λ", lam), ("μ", mu)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError(f"{nombre} debe ser un número finito mayor que cero (se recibió {v!r}).")
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError(f"k debe ser un entero mayor o igual a 1 (se recibió {k!r}).")
    if requiere_M and (isinstance(M, bool) or not isinstance(M, int) or M < 1):
        raise ValueError(f"M debe ser un entero mayor o igual a 1 (se recibió {M!r}).")


def _cociente_valido(lam, mu):
    """λ/μ debe ser representable; con magnitudes extremas puede dar inf o 0."""
    a = lam / mu
    if not (math.isfinite(a) and a > 0):
        raise ErrorModelo("La relación λ/μ está fuera del rango numérico representable. "
                          "Revisa las unidades de λ y μ.")
    return a


def _logsumexp(valores):
    """log(Σ e^x) sin desbordamiento."""
    maximo = max(valores)
    return maximo + math.log(sum(math.exp(x - maximo) for x in valores))


def _verificar_finitos(r, claves):
    malos = [c for c in claves if not math.isfinite(r[c])]
    if malos:
        raise ErrorModelo(
            "El modelo no puede evaluarse con precisión numérica para estos datos "
            f"(resultados no finitos en: {', '.join(malos)}). Revisa la magnitud de λ, μ, k y M.")


def nombre_modelo(finita, k, M=None):
    """
    Devuelve (sigla, notación de Kendall).
    Si se da M en población finita, la notación lo muestra: M/M/2/4/4.
    """
    if finita:
        sigla = "PFCS" if k == 1 else "PFCM"
        cap = "M" if M is None else str(M)
        return sigla, f"M/M/{k}/{cap}/{cap}"
    return ("PICS", "M/M/1") if k == 1 else ("PICM", f"M/M/{k}")


def k_minimo_estable(lam, mu):
    """Menor k que cumple λ/(kμ) < 1 en población infinita."""
    a = lam / mu
    k = int(a) + 1
    while a / k >= 1 - TOLERANCIA_ESTABILIDAD:
        k += 1
    return k


# ----------------------------------------------------------------------------
# Población infinita: M/M/1 y M/M/k
# ----------------------------------------------------------------------------
def resolver_infinita(lam, mu, k):
    _validar_parametros(lam, mu, k)
    a = _cociente_valido(lam, mu)   # tráfico (λ/μ)
    rho = a / k           # utilización por servidor
    if rho >= 1 - TOLERANCIA_ESTABILIDAD:
        return {"ok": False, "finita": False, "k": k, "a": a, "rho": rho,
                "k_min": k_minimo_estable(lam, mu)}

    # P0 = 1 / [ Σ_{n=0}^{k-1} a^n/n!  +  a^k/k! · kμ/(kμ-λ) ]   (kμ/(kμ-λ) = 1/(1-ρ))
    log_a = math.log(a)
    log_terminos = [n * log_a - math.lgamma(n + 1) for n in range(k)]
    log_ak = k * log_a - math.lgamma(k + 1)          # log(a^k / k!)
    log_cola = log_ak - math.log1p(-rho)             # log(a^k / k! · 1/(1-ρ))
    log_P0 = -_logsumexp(log_terminos + [log_cola])
    P0 = math.exp(log_P0)

    # Distribución Pn (n<k: a^n/n! P0 ; n>=k: a^n/(k! k^(n-k)) P0)
    # Recurrencia: P_n = P_{n-1} · a / min(n, k), en logaritmos.
    # Se corta cuando la probabilidad acumulada llega a 1 − 1e-13, pero siempre se
    # incluye hasta n = k + 1 para que P(n = k) exista aunque k sea grande.
    p = [P0]
    acumulado, n, log_pn = P0, 0, log_P0
    while (acumulado < 1 - 1e-13 or n <= k) and n < MAX_TERMINOS_DISTRIBUCION:
        n += 1
        log_pn += log_a - math.log(min(n, k))
        p.append(math.exp(log_pn))
        acumulado += p[-1]

    Pk = math.exp(log_cola + log_P0)                  # P(n >= k): probabilidad de esperar
    Lq = math.exp(log_P0 + log_ak + math.log(rho) - 2 * math.log1p(-rho))
    L = Lq + a
    Wq = Lq / lam
    W = Wq + 1 / mu
    Wn = 1 / (k * mu - lam)                           # espera de los que sí esperan
    Pgt = Pk * rho                                    # P(n > k): hay cola

    r = {
        "ok": True, "finita": False, "k": k, "k_ef": k, "M": None,
        "lam": lam, "mu": mu, "a": a, "rho": rho, "util": rho,
        "P0": P0, "p": p,
        "Pk": Pk, "Pgt": Pgt, "Plt": 1 - Pk,
        "frac_espera": Pk, "frac_no_espera": 1 - Pk,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq, "Wn": Wn,
        "Ln": Lq / Pgt if Pgt > 0 else float("nan"),
        "ociosos": k - a, "lam_ef": lam,
        "operando": None, "frac_operando": None,
    }
    _verificar_finitos(r, ("P0", "Pk", "L", "Lq", "W", "Wq"))
    return r


# ----------------------------------------------------------------------------
# Población finita: M/M/1/M/M y M/M/k/M/M
# ----------------------------------------------------------------------------
def resolver_finita(lam, mu, k, M):
    """
    λ es la tasa de llegada de CADA unidad de la población.
    Si k > M solo pueden trabajar M servidores a la vez: k_ef = min(k, M).
    """
    _validar_parametros(lam, mu, k, M, requiere_M=True)
    k_ef = min(k, M)
    r = _cociente_valido(lam, mu)

    # Términos sin normalizar:
    #   n <= k : M! / ((M-n)! n!) r^n
    #   n >  k : M! / ((M-n)! k! k^(n-k)) r^n
    # Recurrencia t_n = t_{n-1} (M-n+1) r / min(n,k), en logaritmos para no desbordar.
    log_r = math.log(r)
    log_t = [0.0]
    for n in range(1, M + 1):
        log_t.append(log_t[-1] + math.log(M - n + 1) + log_r - math.log(min(n, k_ef)))
    maximo = max(log_t)
    t = [math.exp(x - maximo) for x in log_t]      # el máximo pasa a valer 1
    S = sum(t)
    p = [x / S for x in t]

    L = Lq = Pk = Pgt = espera_num = ociosos = operando = 0.0
    for n, pn in enumerate(p):
        L += n * pn
        operando += (M - n) * pn                     # = M − L, sin restar números grandes
        if n > k_ef:
            Lq += (n - k_ef) * pn
            Pgt += pn
        if n >= k_ef:
            Pk += pn
            espera_num += (M - n) * pn
        else:
            ociosos += (k_ef - n) * pn

    # Los tiempos se obtienen dividiendo entre λ efectiva = λ(M − L). En teoría
    # siempre es > 0 (P_M < 1), pero con datos extremos puede anularse en punto flotante.
    if not operando > 0:
        raise ErrorModelo(
            "La λ efectiva λ(M − L) resultó nula: prácticamente toda la población está en el "
            "sistema y W, Wq no pueden calcularse. Revisa la relación λ/μ y el valor de M.")
    lam_ef = lam * operando                          # llegadas efectivas
    W = L / lam_ef
    Wq = Lq / lam_ef
    # Una unidad que llega "ve" el sistema sin contarse: prob. de esperar
    frac_espera = espera_num / operando
    util = (k_ef - ociosos) / k_ef

    res = {
        "ok": True, "finita": True, "k": k, "k_ef": k_ef, "M": M,
        "lam": lam, "mu": mu, "a": r, "rho": util, "util": util,
        "P0": p[0], "p": p,
        "Pk": Pk, "Pgt": Pgt, "Plt": 1 - Pk,
        "frac_espera": frac_espera, "frac_no_espera": 1 - frac_espera,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "Wn": Wq / frac_espera if frac_espera > 0 else float("nan"),
        "Ln": Lq / Pgt if Pgt > 0 else float("nan"),
        "ociosos": ociosos, "lam_ef": lam_ef,
        "operando": operando, "frac_operando": operando / M,
    }
    _verificar_finitos(res, ("P0", "Pk", "L", "Lq", "W", "Wq", "lam_ef"))
    return res


def resolver(lam, mu, k, finita=False, M=None):
    return resolver_finita(lam, mu, k, M) if finita else resolver_infinita(lam, mu, k)


# ----------------------------------------------------------------------------
# Probabilidades derivadas de la distribución Pn
# ----------------------------------------------------------------------------
def prob_acumulada(p, n):
    """P(N ≤ n). Para n < 0 vale 0."""
    return min(1.0, sum(p[: max(0, n + 1)]))


def probabilidades_rango(r, a, b):
    """
    Probabilidades del número en el sistema (n) y en la cola (n − k) para un
    valor a y un rango [a, b]. Devuelve lista de (símbolo, significado, valor).
    """
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("a y b deben ser enteros.")
    if a < 0 or b < a:
        raise ValueError("Se requiere 0 ≤ a ≤ b.")
    p, kk = r["p"], r["k_ef"]
    P = lambda n: p[n] if 0 <= n < len(p) else 0.0      # noqa: E731
    acum = lambda n: prob_acumulada(p, n)               # noqa: E731
    return [
        (f"P(n = {a})", f"Exactamente {a} en el sistema", P(a)),
        (f"P(n ≤ {a})", f"Como máximo {a} en el sistema", acum(a)),
        (f"P(n ≥ {a})", f"Al menos {a} en el sistema", 1 - acum(a - 1)),
        (f"P(n > {a})", f"Más de {a} en el sistema", 1 - acum(a)),
        (f"P({a} ≤ n ≤ {b})", f"Entre {a} y {b} en el sistema", acum(b) - acum(a - 1)),
        (f"P(cola = {a})", f"Exactamente {a} esperando", acum(kk) if a == 0 else P(kk + a)),
        (f"P(cola ≥ {a})", f"Al menos {a} esperando (n ≥ k+{a})", 1 - acum(kk + a - 1) if a > 0 else 1.0),
        (f"P(cola > {a})", f"Más de {a} esperando (n ≥ k+{a + 1})", 1 - acum(kk + a)),
        (f"P(cola ≤ {a})", f"Como máximo {a} esperando", acum(kk + a)),
        (f"P({a} ≤ cola ≤ {b})", f"Entre {a} y {b} esperando",
         acum(kk + b) if a == 0 else acum(kk + b) - acum(kk + a - 1)),
    ]


def distribucion(r, n_tope_infinita=150, umbral=1e-6):
    """
    Filas de la distribución para mostrar: (n, en cola, Pn, P(≤n), P(≥n)).
    En población infinita se corta cuando Pn ≤ umbral (mostrando al menos
    hasta k+2) o en n_tope_infinita; en finita se muestran n = 0..M.
    """
    p, kk = r["p"], r["k_ef"]
    n_max = len(p) - 1
    if not r["finita"]:
        n = 0
        while n < n_max and (n <= kk + 2 or p[n] > umbral) and n < n_tope_infinita:
            n += 1
        n_max = n
    filas, c = [], 0.0
    for n in range(n_max + 1):
        antes = c
        c += p[n]
        filas.append((n, max(0, n - kk), p[n], min(1.0, c), max(0.0, 1 - antes)))
    return filas


# ----------------------------------------------------------------------------
# Barridos para tablas y gráficas
# ----------------------------------------------------------------------------
def barrido_k(lam, mu, finita, M, k_max):
    """Resultados para varios k. En infinita empieza en el k mínimo estable."""
    if finita:
        k_ini, k_fin = 1, max(1, min(M, k_max))
    else:
        k_ini = k_minimo_estable(lam, mu)
        k_fin = max(k_max, k_ini + 4)
    return [resolver(lam, mu, k, finita, M) for k in range(k_ini, k_fin + 1)]


def barrido_M(lam, mu, k, M_max):
    """Resultados de población finita para M = 1..M_max con k fijo."""
    return [resolver_finita(lam, mu, k, M) for M in range(1, M_max + 1)]


if __name__ == "__main__":
    # Verificación rápida con los ejemplos del apunte
    r = resolver_infinita(2, 3, 2)
    print("Refinería 2 canales: P0=%.4f Pk=%.4f Wq=%.4f" % (r["P0"], r["Pk"], r["Wq"]))
    r = resolver_infinita(30, 12, 6)
    print("Teléfonos k=6: P0=%.5f Pk=%.4f" % (r["P0"], r["Pk"]))
    r = resolver_finita(0.1, 0.5, 2, 4)
    print("Mecánicos M=4 k=2: P0=%.4f L=%.4f" % (r["P0"], r["L"]))
