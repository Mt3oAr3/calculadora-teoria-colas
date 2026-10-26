"""
comparacion_service.py
Compara escenarios variando k (servidores) y M (población) y busca los que
cumplen una condición del tipo «métrica ≤ valor» o «métrica ≥ valor».

Cada fila de las tablas lleva la clave "cmp:k:<k>" o "cmp:M:<M>". Con ella,
escenario_de_fila() arma el Escenario de esa fila (el mismo resultado r del barrido,
sin recalcular) para que «Cómo se calculó» explique la métrica elegida en esa fila
(clave_formula() traduce la métrica a la clave de services.formulas).
"""
import math
from dataclasses import dataclass, replace

from domain import costos as dc
from domain import modelos_colas as mc
from domain import unidades as du
from domain.errores import ErrorEntrada

from .calculadora_service import Escenario
from .tablas import Columna, Fila, Tabla, Valor

OPERADORES = ["≤", "≥"]
_TOL = 1e-12


@dataclass(frozen=True)
class Metrica:
    nombre: str
    clave: str
    es_tiempo: bool = False
    solo_finita: bool = False


# Las de tiempo se comparan en la unidad elegida en «Mostrar tiempos en».
METRICAS = [
    Metrica("P0 (sistema vacío)", "P0"),
    Metrica("P(n<k) algún servidor libre", "Plt"),
    Metrica("Probabilidad de esperar", "frac_espera"),
    Metrica("Probabilidad de no esperar", "frac_no_espera"),
    Metrica("P(n≥k) todos ocupados", "Pk"),
    Metrica("P(n>k) hay cola", "Pgt"),
    Metrica("L (clientes en el sistema)", "L"),
    Metrica("Lq (clientes en cola)", "Lq"),
    Metrica("W (tiempo en el sistema)", "W", es_tiempo=True),
    Metrica("Wq (tiempo en cola)", "Wq", es_tiempo=True),
    Metrica("Wn (espera de los que esperan)", "Wn", es_tiempo=True),
    Metrica("Fracción de unidades operando (finita)", "frac_operando", solo_finita=True),
    Metrica("Costo total diario CT", "ct"),
]
METRICA_INICIAL = "Probabilidad de esperar"
_POR_NOMBRE = {m.nombre: m for m in METRICAS}
# Clave de cada métrica en services.formulas.formula: la misma, salvo la probabilidad de esperar
_CLAVE_FORMULA = {"frac_espera": "Pw"}
TIPOS_FILA = ("k", "M")


def metrica_por_nombre(nombre):
    """Metrica con ese nombre (el texto de la lista); KeyError si no existe."""
    return _POR_NOMBRE[nombre]


def clave_formula(metrica):
    """Clave de services.formulas.formula que explica la métrica."""
    return _CLAVE_FORMULA.get(metrica.clave, metrica.clave)


def clave_fila(tipo, valor):
    """Clave de la fila de la tabla en función de k ("cmp:k:3") o de M ("cmp:M:7")."""
    return f"cmp:{tipo}:{valor}"


def leer_clave_fila(clave):
    """(tipo, valor) de una clave de fila de comparación, o None si no lo es."""
    partes = (clave or "").split(":")
    if len(partes) == 3 and partes[0] == "cmp" and partes[1] in TIPOS_FILA and partes[2].isdigit():
        return partes[1], int(partes[2])
    return None


def describir_fila(tipo, valor):
    return f"{tipo} = {valor}"


def escenario_de_fila(esc, tipo, valor):
    """
    Escenario de la fila con k = valor (tipo "k") o M = valor (tipo "M") de la comparación.
    Usa el resultado r de esa fila del barrido (no recalcula nada): los mismos parámetros con
    k o M cambiado, sus costos y su notación. ValueError si la fila no está en el barrido.
    """
    if tipo not in TIPOS_FILA:
        raise ValueError(f"Tipo de fila desconocido: {tipo!r}")
    barrido = esc.barrido_k if tipo == "k" else esc.barrido_M
    r = next((r for r in barrido if r[tipo] == valor), None)
    if r is None:
        raise ValueError(f"No hay fila con {describir_fila(tipo, valor)} en la comparación.")
    p = replace(esc.p, **{tipo: valor})
    sigla, kendall = mc.nombre_modelo(p.finita, p.k, p.M if p.finita else None)
    return Escenario(p=p, r=r, barrido_k=[], barrido_M=[], sigla=sigla, kendall=kendall,
                     costos=dc.costos(r, p.H, p.cfg) if r["ok"] else None)


@dataclass(frozen=True)
class Condicion:
    metrica: Metrica
    operador: str
    limite: float
    unidad_tiempo: str

    def describir(self):
        u = f" {du.ABREV[self.unidad_tiempo]}" if self.metrica.es_tiempo else ""
        lim = f"{self.limite:g}".replace(".", ",")
        return f"{self.metrica.nombre} {self.operador} {lim}{u}"


def leer_condicion(nombre_metrica, operador, limite_txt, unidad_tiempo):
    if nombre_metrica not in _POR_NOMBRE:
        raise ErrorEntrada([("cond_m", "Elige una métrica de la lista.")])
    if operador not in OPERADORES:
        raise ErrorEntrada([("cond_op", "Elige ≤ o ≥.")])
    txt = (limite_txt or "").strip().replace(",", ".")
    try:
        limite = float(txt)
    except ValueError:
        raise ErrorEntrada([("cond_v", f"El valor de la condición «{limite_txt}» no es un número.")]) from None
    if not math.isfinite(limite):
        raise ErrorEntrada([("cond_v", "El valor de la condición debe ser un número finito.")])
    return Condicion(_POR_NOMBRE[nombre_metrica], operador, limite, unidad_tiempo)


def valor_metrica(r, metrica, p, unidad_tiempo):
    """Valor de la métrica para un resultado r. NaN si no aplica al modelo."""
    if not r["ok"] or (metrica.solo_finita and not r["finita"]):
        return float("nan")
    if metrica.clave == "ct":
        return dc.costos(r, p.H, p.cfg)["ct"]
    v = r[metrica.clave]
    if v is None:
        return float("nan")
    return du.horas_a_unidad(v, unidad_tiempo, p.H) if metrica.es_tiempo else v


def cumple(r, cond, p):
    v = valor_metrica(r, cond.metrica, p, cond.unidad_tiempo)
    if not math.isfinite(v):
        return False                    # la métrica no está definida para este escenario
    return v <= cond.limite + _TOL if cond.operador == "≤" else v >= cond.limite - _TOL


@dataclass
class ResultadoComparacion:
    tabla: Tabla
    resumen: str
    valor_que_cumple: int | None = None     # k menor (o M mayor) que cumple la condición
    k_menor_costo: int | None = None


def _encabezado_te(p):
    return "CT(TE)+ocio" if p.cfg["c_ocio"] > 0 else "CT(TE)"


def comparar_k(esc, cond, fmt):
    """Tabla en función de k. En infinita empieza en el k mínimo estable."""
    p = esc.p
    u = fmt.abrev_tiempo
    titulos = ["k", "ρ", "P0", "P(n<k)", "P(esperar)", "P(n>k)", "Lq", "L",
               f"Wq ({u})", f"W ({u})", f"Wn ({u})"]
    if p.finita:
        titulos.append("% operando")
    titulos += ["CT(S)", _encabezado_te(p), "CT"]
    tabla = Tabla("Variando k", [Columna(t) for t in titulos])

    filas = [(r, dc.costos(r, p.H, p.cfg)) for r in esc.barrido_k if r["ok"]]
    hay_costos = any(c["ct"] > 0 for _, c in filas)
    i_mejor = min(range(len(filas)), key=lambda i: filas[i][1]["ct"]) if (filas and hay_costos) else -1
    primero = None
    for i, (r, c) in enumerate(filas):
        ok = cumple(r, cond, p)
        if ok and primero is None:
            primero = r["k"]
        etiquetas = tuple(e for e, activa in (("ok", ok), ("mejor", i == i_mejor), ("actual", r["k"] == p.k))
                          if activa)
        celdas = [Valor(r["k"], "entero"), Valor(r["util"]), Valor(r["P0"]), Valor(r["Plt"]),
                  Valor(r["frac_espera"]), Valor(r["Pgt"]), Valor(r["Lq"]), Valor(r["L"]),
                  Valor(r["Wq"], "tiempo_num"), Valor(r["W"], "tiempo_num"), Valor(r["Wn"], "tiempo_num")]
        if p.finita:
            celdas.append(Valor(r["frac_operando"], "pct"))
        celdas += [Valor(c["ct_s"], "dinero"), Valor(c["ct_te"] + c["ct_ocio"], "dinero"), Valor(c["ct"], "dinero")]
        tabla.filas.append(Fila(celdas, etiquetas, clave_fila("k", r["k"])))

    partes = [] if p.finita else [f"Mínimo por estabilidad: k = {mc.k_minimo_estable(p.lam, p.mu)}."]
    partes.append(f"Menor k con {cond.describir()}: k = {primero}." if primero is not None
                  else f"Ningún k del rango cumple {cond.describir()}.")
    k_mejor = filas[i_mejor][0]["k"] if i_mejor >= 0 else None
    if k_mejor is not None:
        partes.append(f"Menor costo total: k = {k_mejor} ({fmt.dinero(filas[i_mejor][1]['ct'])} por día).")
    return ResultadoComparacion(tabla, "  ".join(partes), primero, k_mejor)


def comparar_M(esc, cond, fmt):
    """Tabla en función de M (solo población finita) con el k actual."""
    p = esc.p
    u = fmt.abrev_tiempo
    titulos = ["M", "P0", "P(n<k)", "P(esperar)", "Lq", "L", "M − L", "% operando",
               f"Wq ({u})", f"W ({u})", "CT(S)", _encabezado_te(p), "CT"]
    tabla = Tabla("Variando M", [Columna(t) for t in titulos],
                  mensaje_vacio="La tabla en función de M solo aplica a población finita.")
    if not p.finita:
        return ResultadoComparacion(tabla, "Tabla en función de M: solo para población finita.")
    ultimo = None
    for r in esc.barrido_M:
        c = dc.costos(r, p.H, p.cfg)
        ok = cumple(r, cond, p)
        if ok:
            ultimo = r["M"]
        etiquetas = tuple(e for e, activa in (("ok", ok), ("actual", r["M"] == p.M)) if activa)
        tabla.filas.append(Fila([
            Valor(r["M"], "entero"), Valor(r["P0"]), Valor(r["Plt"]), Valor(r["frac_espera"]),
            Valor(r["Lq"]), Valor(r["L"]), Valor(r["operando"]), Valor(r["frac_operando"], "pct"),
            Valor(r["Wq"], "tiempo_num"), Valor(r["W"], "tiempo_num"),
            Valor(c["ct_s"], "dinero"), Valor(c["ct_te"] + c["ct_ocio"], "dinero"), Valor(c["ct"], "dinero"),
        ], etiquetas, clave_fila("M", r["M"])))

    resumen = (f"Mayor M con {cond.describir()} (k = {p.k}): M = {ultimo}." if ultimo is not None
               else f"Ningún M del rango cumple {cond.describir()}.")
    return ResultadoComparacion(tabla, resumen, ultimo)
