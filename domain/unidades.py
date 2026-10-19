"""
unidades.py
Conversión de unidades de tiempo.

Convención de todo el proyecto: las tasas se trabajan en clientes por HORA y
los tiempos se devuelven en HORAS. Un "día" equivale a las horas de operación
(con 8 h/día, "cada 4 días" significa cada 32 horas de operación).
"""
import math

UNIDADES = ["minuto", "hora", "día"]
ABREV = {"minuto": "min", "hora": "h", "día": "día"}


def horas_por_unidad(unidad, horas_dia):
    """Cuántas horas tiene una unidad. Un 'día' equivale a las horas de operación."""
    if unidad == "minuto":
        return 1.0 / 60.0
    if unidad == "hora":
        return 1.0
    if unidad == "día":
        if not (isinstance(horas_dia, (int, float)) and math.isfinite(horas_dia) and horas_dia > 0):
            raise ValueError("Las horas por día deben ser un número mayor que cero.")
        return float(horas_dia)
    raise ValueError(f"Unidad de tiempo desconocida: {unidad!r}.")


def tasa_por_hora(es_tasa, valor, unidad, horas_dia):
    """
    Convierte el dato del enunciado a tasa por hora.
      es_tasa=True : 'valor' clientes por 'unidad'   -> valor / horas
      es_tasa=False: un cliente cada 'valor' unidades -> 1 / (valor * horas)
    """
    if valor is None or not math.isfinite(valor) or valor <= 0:
        raise ValueError("Las tasas y los tiempos deben ser mayores que cero.")
    h = horas_por_unidad(unidad, horas_dia)
    return valor / h if es_tasa else 1.0 / (valor * h)


def horas_a_unidad(horas, unidad, horas_dia):
    """Expresa un tiempo dado en horas en la unidad pedida."""
    return horas / horas_por_unidad(unidad, horas_dia)
