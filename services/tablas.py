"""
tablas.py
Estructuras de datos para tablas de resultados, independientes de Tkinter.

Las celdas guardan el valor numérico CRUDO y su tipo; el texto se genera con
un Formateador. Así la interfaz y la exportación CSV usan exactamente los
mismos datos, sin leer el texto de los widgets.
"""
import math
from dataclasses import dataclass, field

from domain.unidades import ABREV, horas_a_unidad, horas_por_unidad


@dataclass(frozen=True)
class Valor:
    """
    Celda tipada.
      tipo: 'texto' | 'entero' | 'num' | 'pct' | 'dinero'
            'tiempo'     -> horas, se muestra convertido y con unidad ("12,0000 min")
            'tiempo_num' -> horas, se muestra convertido sin unidad (la unidad va en el encabezado)
            'tasa'       -> clientes por hora, se muestra por la unidad elegida ("0,3310 clientes/min")
      decimales: fuerza un número de decimales (None = el elegido por el usuario).
    """
    dato: object
    tipo: str = "num"
    sufijo: str = ""
    decimales: int | None = None
    prefijo: str = ""


@dataclass(frozen=True)
class Columna:
    titulo: str
    numerica: bool = True
    destacada: bool = False     # se muestra en negrita (p. ej. k y CT en «Comparar k y M»)


@dataclass
class Fila:
    celdas: list
    # Etiquetas de estado: 'principal', 'ok' (cumple condición), 'mejor' (menor costo), 'actual'
    etiquetas: tuple = ()
    # Indicador al que corresponde la fila (ver services/formulas.py); None si no tiene fórmula
    clave: str | None = None


@dataclass
class Tabla:
    titulo: str
    columnas: list
    filas: list = field(default_factory=list)
    mensaje_vacio: str = ""

    @property
    def encabezados(self):
        return [c.titulo for c in self.columnas]

    def textos(self, fmt):
        """Filas como listas de texto formateado."""
        return [[fmt.texto(c) for c in fila.celdas] for fila in self.filas]


def _finito(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


class Formateador:
    """
    Convierte números a texto con coma decimal y punto de miles (1.234,5678),
    igual que la versión original. Los valores no definidos se muestran "—".
    """
    NO_DEFINIDO = "—"

    def __init__(self, decimales=4, unidad_tiempo="minuto", horas_dia=8.0):
        self.decimales = int(decimales)
        self.unidad_tiempo = unidad_tiempo
        self.horas_dia = horas_dia

    @property
    def abrev_tiempo(self):
        return ABREV[self.unidad_tiempo]

    def num(self, x, d=None):
        if not _finito(x):
            return self.NO_DEFINIDO
        d = self.decimales if d is None else d
        return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def pct(self, x):
        return self.num(x * 100, 2) + " %" if _finito(x) else self.NO_DEFINIDO

    def dinero(self, x):
        return "$ " + self.num(x, 2) if _finito(x) else self.NO_DEFINIDO

    def a_unidad(self, horas):
        return horas_a_unidad(horas, self.unidad_tiempo, self.horas_dia) if _finito(horas) else float("nan")

    def tiempo(self, horas):
        if not _finito(horas):
            return self.NO_DEFINIDO
        return f"{self.num(self.a_unidad(horas))} {self.abrev_tiempo}"

    def tasa(self, por_hora):
        """Tasa (clientes por hora) expresada por la unidad de tiempo elegida."""
        if not _finito(por_hora):
            return self.NO_DEFINIDO
        por_unidad = por_hora * horas_por_unidad(self.unidad_tiempo, self.horas_dia)
        return f"{self.num(por_unidad)} clientes/{self.abrev_tiempo}"

    def texto(self, celda):
        if not isinstance(celda, Valor):
            return "" if celda is None else str(celda)
        x, t = celda.dato, celda.tipo
        if t == "texto":
            s = "" if x is None else str(x)
        elif t == "entero":
            s = str(x) if x is not None else self.NO_DEFINIDO
        elif t == "pct":
            s = self.pct(x)
        elif t == "dinero":
            s = self.dinero(x)
        elif t == "tiempo":
            s = self.tiempo(x)
        elif t == "tasa":
            s = self.tasa(x)
        elif t == "tiempo_num":
            s = self.num(self.a_unidad(x), celda.decimales)
        else:
            s = self.num(x, celda.decimales)
        if s != self.NO_DEFINIDO:
            s = celda.prefijo + s + celda.sufijo
        return s
