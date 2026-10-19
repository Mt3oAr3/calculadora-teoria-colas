"""
errores.py
Excepciones propias de la calculadora. Permiten que la interfaz distinga:

    ErrorEntrada  -> el usuario escribió un dato inválido (se indica el campo).
    ErrorModelo   -> los datos son válidos pero el modelo no puede evaluarse
                     (p. ej. desbordamiento numérico o λ efectiva nula).

Cualquier otra excepción se considera un error inesperado del programa.
"""


class ErrorCalculadora(Exception):
    """Base de todos los errores controlados de la calculadora."""


class ErrorEntrada(ErrorCalculadora):
    """
    Uno o varios campos con datos inválidos.
    `errores` es una lista de pares (campo, mensaje); `campo` es la clave
    interna del dato (por ejemplo 'lam' o 'k') para que la UI lo resalte.
    """

    def __init__(self, errores):
        self.errores = list(errores)
        super().__init__("; ".join(m for _, m in self.errores))


class ErrorModelo(ErrorCalculadora):
    """Limitación matemática o numérica del modelo con datos válidos."""
