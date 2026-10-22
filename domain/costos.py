"""
costos.py
Costos, ingresos e indicadores por jornada de operación.
Todos los montos se devuelven POR DÍA de operación (H horas).
"""
import math

from .unidades import horas_por_unidad

UNIDADES_COSTO_SERVIDOR = ["hora", "día"]
BASES_ESPERA = ["Lq", "L"]


def configuracion_costos(c_servidor=0.0, c_servidor_u="día", c_espera=0.0, c_espera_u="hora",
                         base_espera="Lq", c_ocio=0.0, ingreso=0.0, frac_ingreso=1.0, sistemas=1):
    """Construye y valida un diccionario de configuración de costos."""
    cfg = {"c_servidor": c_servidor, "c_servidor_u": c_servidor_u, "c_espera": c_espera,
           "c_espera_u": c_espera_u, "base_espera": base_espera, "c_ocio": c_ocio,
           "ingreso": ingreso, "frac_ingreso": frac_ingreso, "sistemas": sistemas}
    validar_configuracion(cfg)
    return cfg


def validar_configuracion(cfg):
    for clave in ("c_servidor", "c_espera", "c_ocio", "ingreso"):
        v = cfg[clave]
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"El valor '{clave}' debe ser un número mayor o igual a cero.")
    f = cfg["frac_ingreso"]
    if not isinstance(f, (int, float)) or not (0 <= f <= 1):
        raise ValueError("La fracción de clientes con ingreso debe estar entre 0 y 1.")
    s = cfg.get("sistemas", 1)
    if not isinstance(s, int) or isinstance(s, bool) or s < 1:
        raise ValueError("El número de sistemas idénticos debe ser un entero mayor o igual a 1.")
    if cfg["c_servidor_u"] not in UNIDADES_COSTO_SERVIDOR:
        raise ValueError(f"Unidad de costo de servidor desconocida: {cfg['c_servidor_u']!r}.")
    if cfg["base_espera"] not in BASES_ESPERA:
        raise ValueError(f"Base de costo de espera desconocida: {cfg['base_espera']!r}.")


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
      CT(S)  = costo de servidores (se pagan los k servidores contratados)
      CT(TE) = costo del tiempo de espera (Lq o L × horas × costo por hora)
      CT     = CT(S) + CT(TE) + costo de ocio
    Si cfg['sistemas'] = S > 1 (p. ej. 2 cajas independientes e idénticas, cada una
    con su cola) todos los montos son la SUMA de los S sistemas (S × el de uno).
    """
    H = horas_dia
    S = cfg.get("sistemas", 1) or 1
    cs = cfg.get("c_servidor", 0) or 0
    ct_s = S * r["k"] * (cs * H if cfg.get("c_servidor_u") == "hora" else cs)

    cw = cfg.get("c_espera", 0) or 0
    cw_hora = cw / horas_por_unidad(cfg.get("c_espera_u", "hora"), H)
    base = r["L"] if cfg.get("base_espera") == "L" else r["Lq"]
    ct_te = S * base * H * cw_hora

    ct_ocio = S * r["ociosos"] * H * (cfg.get("c_ocio", 0) or 0)
    ct = ct_s + ct_te + ct_ocio
    ingreso = S * r["lam_ef"] * H * cfg.get("frac_ingreso", 1) * (cfg.get("ingreso", 0) or 0)
    return {"ct_s": ct_s, "ct_te": ct_te, "ct_ocio": ct_ocio, "ct": ct,
            "ingreso": ingreso, "rentabilidad": ingreso / ct if ct > 0 else float("nan")}


def horas_por_estado(r, horas_dia):
    """
    Tiempo (en horas por día) que el sistema pasa en cada estado y horas-hombre
    acumuladas. Tiempo en un estado = probabilidad × horas de operación.
    Devuelve lista de (concepto, horas).
    """
    H = horas_dia
    return [
        ("Todos los servidores desocupados a la vez (P0)", r["P0"] * H),
        ("Uno o varios servidores desocupados (P(n<k))", r["Plt"] * H),
        ("Todos los servidores ocupados (P(n≥k))", r["Pk"] * H),
        ("Con clientes esperando en cola (P(n>k))", r["Pgt"] * H),
        ("Horas de ocio sumadas de todos los servidores", r["ociosos"] * H),
        ("Horas de trabajo sumadas de todos los servidores", (r["k_ef"] - r["ociosos"]) * H),
        ("Horas totales de espera en cola (Lq × horas)", r["Lq"] * H),
        ("Horas totales en el sistema (L × horas)", r["L"] * H),
    ]


def clientes_por_dia(r, horas_dia):
    """Clientes por día: llegan (λef·H), esperan y son atendidos de inmediato."""
    llegadas = r["lam_ef"] * horas_dia
    return [
        ("Clientes que llegan", llegadas),
        ("Clientes que deben esperar", llegadas * r["frac_espera"]),
        ("Clientes atendidos en cuanto llegan", llegadas * r["frac_no_espera"]),
    ]


def totales_sistemas(r, horas_dia, sistemas):
    """
    Totales de S sistemas idénticos e independientes (p. ej. 2 cajas, cada una con su
    cola). Devuelve lista de (concepto, valor, tipo) con tipo 'h' (horas) o 'clientes'.
    Vacía si S = 1.
    """
    S, H = sistemas, horas_dia
    if S <= 1:
        return []
    llegadas = S * r["lam_ef"] * H
    return [
        (f"Los {S} sistemas: clientes esperando a la vez (S × Lq)", S * r["Lq"], "clientes"),
        (f"Los {S} sistemas: horas de ocio sumadas (S × ociosos × horas)", S * r["ociosos"] * H, "h"),
        (f"Los {S} sistemas: todos desocupados a la vez (P0^S × horas)", (r["P0"] ** S) * H, "h"),
        (f"Los {S} sistemas: horas totales de espera (S × Lq × horas)", S * r["Lq"] * H, "h"),
        (f"Los {S} sistemas: clientes que llegan", llegadas, "clientes"),
        (f"Los {S} sistemas: clientes que deben esperar", llegadas * r["frac_espera"], "clientes"),
    ]
