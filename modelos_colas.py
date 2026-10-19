"""
modelos_colas.py
Fórmulas de teoría de colas (llegadas Poisson, servicio exponencial):

    PICS  -> M/M/1        Población infinita, canal simple
    PICM  -> M/M/k        Población infinita, canal múltiple
    PFCS  -> M/M/1/M/M    Población finita, canal simple
    PFCM  -> M/M/k/M/M    Población finita, canal múltiple

Todas las tasas se trabajan internamente en clientes por HORA y todos los
tiempos se devuelven en HORAS. La interfaz se encarga de convertir unidades.
"""

# ----------------------------------------------------------------------------
# Conversión de unidades
# ----------------------------------------------------------------------------
UNIDADES = ["minuto", "hora", "día"]


def horas_por_unidad(unidad, horas_dia):
    """Cuántas horas tiene una unidad. Un 'día' equivale a las horas de operación."""
    if unidad == "minuto":
        return 1.0 / 60.0
    if unidad == "hora":
        return 1.0
    return float(horas_dia)


def tasa_por_hora(es_tasa, valor, unidad, horas_dia):
    """
    Convierte el dato del enunciado a tasa por hora.
      es_tasa=True : 'valor' clientes por 'unidad'   -> valor / horas
      es_tasa=False: un cliente cada 'valor' unidades -> 1 / (valor * horas)
    """
    if valor is None or valor <= 0:
        raise ValueError("Las tasas y los tiempos deben ser mayores que cero.")
    h = horas_por_unidad(unidad, horas_dia)
    return valor / h if es_tasa else 1.0 / (valor * h)


def nombre_modelo(finita, k):
    if finita:
        return ("PFCS", "M/M/1/M/M") if k == 1 else ("PFCM", f"M/M/{k}/M/M")
    return ("PICS", "M/M/1") if k == 1 else ("PICM", f"M/M/{k}")


def k_minimo_estable(lam, mu):
    """Menor k que cumple λ/(kμ) < 1 en población infinita."""
    return int(lam / mu) + 1


# ----------------------------------------------------------------------------
# Población infinita: M/M/1 y M/M/k
# ----------------------------------------------------------------------------
def resolver_infinita(lam, mu, k):
    a = lam / mu          # tráfico (λ/μ)
    rho = a / k           # utilización por servidor
    if rho >= 1:
        return {"ok": False, "finita": False, "k": k, "a": a, "rho": rho,
                "k_min": k_minimo_estable(lam, mu)}

    # P0 = 1 / [ Σ_{n=0}^{k-1} a^n/n!  +  a^k/k! · kμ/(kμ-λ) ]
    suma, termino = 0.0, 1.0
    for n in range(k):
        suma += termino
        termino *= a / (n + 1)          # al final: termino = a^k / k!
    P0 = 1.0 / (suma + termino / (1 - rho))

    # Distribución Pn (n<k: a^n/n! P0 ; n>=k: a^n/(k! k^(n-k)) P0)
    p = [P0]
    acumulado, n = P0, 0
    while acumulado < 1 - 1e-13 and n < 5000:
        n += 1
        p.append(p[-1] * a / min(n, k))
        acumulado += p[-1]

    Pk = termino / (1 - rho) * P0                 # P(n >= k): probabilidad de esperar
    Lq = P0 * termino * rho / (1 - rho) ** 2
    L = Lq + a
    Wq = Lq / lam
    W = Wq + 1 / mu
    Wn = 1 / (k * mu - lam)                       # espera de los que sí esperan
    Pgt = Pk * rho                                # P(n > k): hay cola

    return {
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


# ----------------------------------------------------------------------------
# Población finita: M/M/1/M/M y M/M/k/M/M
# ----------------------------------------------------------------------------
def resolver_finita(lam, mu, k, M):
    """λ es la tasa de llegada de CADA unidad de la población."""
    k_ef = min(k, M)
    r = lam / mu

    # Términos sin normalizar:
    #   n <= k : M! / ((M-n)! n!) r^n
    #   n >  k : M! / ((M-n)! k! k^(n-k)) r^n
    # Se calculan con la recurrencia t_n = t_{n-1} (M-n+1) r / min(n,k)
    t = [1.0]
    for n in range(1, M + 1):
        t.append(t[-1] * (M - n + 1) * r / min(n, k_ef))
    S = sum(t)
    p = [x / S for x in t]

    L = Lq = Pk = Pgt = espera_num = ociosos = 0.0
    for n, pn in enumerate(p):
        L += n * pn
        if n > k_ef:
            Lq += (n - k_ef) * pn
            Pgt += pn
        if n >= k_ef:
            Pk += pn
            espera_num += (M - n) * pn
        else:
            ociosos += (k_ef - n) * pn

    lam_ef = lam * (M - L)                         # llegadas efectivas
    W = L / lam_ef
    Wq = Lq / lam_ef
    # Una unidad que llega "ve" el sistema sin contarse: prob. de esperar
    frac_espera = espera_num / (M - L) if (M - L) > 0 else float("nan")
    util = (k_ef - ociosos) / k_ef

    return {
        "ok": True, "finita": True, "k": k, "k_ef": k_ef, "M": M,
        "lam": lam, "mu": mu, "a": r, "rho": util, "util": util,
        "P0": p[0], "p": p,
        "Pk": Pk, "Pgt": Pgt, "Plt": 1 - Pk,
        "frac_espera": frac_espera, "frac_no_espera": 1 - frac_espera,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "Wn": Wq / frac_espera if frac_espera > 0 else float("nan"),
        "Ln": Lq / Pgt if Pgt > 0 else float("nan"),
        "ociosos": ociosos, "lam_ef": lam_ef,
        "operando": M - L, "frac_operando": (M - L) / M,
    }


def resolver(lam, mu, k, finita=False, M=None):
    return resolver_finita(lam, mu, k, M) if finita else resolver_infinita(lam, mu, k)


# ----------------------------------------------------------------------------
# Costos
# ----------------------------------------------------------------------------
def costos(r, horas_dia, cfg):
    """
    cfg = {
      'c_servidor': valor, 'c_servidor_u': 'hora'|'día',
      'c_espera': valor,   'c_espera_u': 'minuto'|'hora'|'día',
      'base_espera': 'Lq'|'L',
      'c_ocio': costo por hora de servidor ocioso,
      'ingreso': ingreso por cliente, 'frac_ingreso': fracción que genera ingreso
    }
    Devuelve costos POR DÍA:
      CT(S)  = costo de servidores
      CT(TE) = costo del tiempo de espera (Lq o L × horas × costo por hora)
      CT     = CT(S) + CT(TE) + costo de ocio
    """
    H = horas_dia
    cs = cfg.get("c_servidor", 0) or 0
    ct_s = r["k"] * (cs * H if cfg.get("c_servidor_u") == "hora" else cs)

    cw = cfg.get("c_espera", 0) or 0
    cw_hora = cw / horas_por_unidad(cfg.get("c_espera_u", "hora"), H)
    base = r["L"] if cfg.get("base_espera") == "L" else r["Lq"]
    ct_te = base * H * cw_hora

    ct_ocio = r["ociosos"] * H * (cfg.get("c_ocio", 0) or 0)
    ct = ct_s + ct_te + ct_ocio
    ingreso = r["lam_ef"] * H * cfg.get("frac_ingreso", 1) * (cfg.get("ingreso", 0) or 0)
    return {"ct_s": ct_s, "ct_te": ct_te, "ct_ocio": ct_ocio, "ct": ct,
            "ingreso": ingreso, "rentabilidad": ingreso / ct if ct > 0 else float("nan")}


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
    # Verificación con los ejemplos del apunte
    r = resolver_infinita(2, 3, 2)
    print("Refinería 2 canales: P0=%.4f Pk=%.4f Wq=%.4f" % (r["P0"], r["Pk"], r["Wq"]))
    r = resolver_infinita(30, 12, 6)
    print("Teléfonos k=6: P0=%.5f Pk=%.4f" % (r["P0"], r["Pk"]))
    r = resolver_finita(0.1, 0.5, 2, 4)
    print("Mecánicos M=4 k=2: P0=%.4f L=%.4f" % (r["P0"], r["L"]))
