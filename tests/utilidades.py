"""Utilidades compartidas por las pruebas."""
import json
import math
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

RUTA_REFERENCIA = os.path.join(os.path.dirname(__file__), "datos", "referencia_original.json")


def cargar_referencia():
    """
    Resultados generados con el código ORIGINAL (commit e65163c, antes de la
    refactorización). Ver README, sección Pruebas. Los valores no finitos se
    guardaron como null.
    """
    with open(RUTA_REFERENCIA, encoding="utf-8") as fh:
        return json.load(fh)


def cerca(a, b, rel=1e-9, abs_=1e-12):
    """Compara valores numéricos; None (JSON) equivale a NaN/no finito."""
    def no_finito(x):
        return x is None or (isinstance(x, float) and not math.isfinite(x))
    if no_finito(a) or no_finito(b):
        return no_finito(a) and no_finito(b)
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)
