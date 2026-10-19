"""Comprueba las reglas de dependencia entre capas (sin abrir la interfaz)."""
import ast
import os
import unittest

from utilidades import RAIZ

# capa -> módulos de primer nivel que NO puede importar
PROHIBIDOS = {
    "domain": {"tkinter", "matplotlib", "services", "ui", "visualization"},
    "services": {"tkinter", "ui"},
    "visualization": {"tkinter", "ui", "services"},
}


def importaciones(ruta):
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for n in nodo.names:
                yield n.name.split(".")[0]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            yield nodo.module.split(".")[0]


class TestArquitectura(unittest.TestCase):

    def test_dependencias_entre_capas(self):
        for capa, prohibidos in PROHIBIDOS.items():
            carpeta = os.path.join(RAIZ, capa)
            for archivo in os.listdir(carpeta):
                if archivo.endswith(".py"):
                    usados = set(importaciones(os.path.join(carpeta, archivo)))
                    self.assertFalse(usados & prohibidos, f"{capa}/{archivo} importa {usados & prohibidos}")


if __name__ == "__main__":
    unittest.main()
