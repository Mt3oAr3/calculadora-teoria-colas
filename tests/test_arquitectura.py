"""Comprueba las reglas de dependencia entre capas (sin abrir la interfaz)."""
import ast
import os
import unittest

from utilidades import RAIZ

# Bibliotecas de Qt: solo la capa ui_qt puede usarlas.
QT = {"PySide6", "shiboken6", "PyQt5", "PyQt6", "PySide2"}

# capa -> módulos de primer nivel que NO puede importar
PROHIBIDOS = {
    "domain": {"tkinter", "matplotlib", "services", "ui", "ui_qt", "visualization"} | QT,
    "services": {"tkinter", "ui", "ui_qt"} | QT,
    "visualization": {"tkinter", "ui", "ui_qt", "services"} | QT,
    "ui": {"ui_qt"} | QT,
    "ui_qt": {"tkinter", "ui"},
}
CARPETAS_IGNORADAS = {"venv", ".venv", "env", ".git", "__pycache__"}


def importaciones(ruta):
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for n in nodo.names:
                yield n.name.split(".")[0]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            yield nodo.module.split(".")[0]


def archivos_del_proyecto():
    """Todos los .py del proyecto (sin el entorno virtual), con su ruta relativa."""
    for carpeta, subcarpetas, archivos in os.walk(RAIZ):
        subcarpetas[:] = [d for d in subcarpetas if d not in CARPETAS_IGNORADAS]
        for archivo in archivos:
            if archivo.endswith(".py"):
                ruta = os.path.join(carpeta, archivo)
                yield os.path.relpath(ruta, RAIZ), ruta


class TestArquitectura(unittest.TestCase):

    def test_dependencias_entre_capas(self):
        for capa, prohibidos in PROHIBIDOS.items():
            carpeta = os.path.join(RAIZ, capa)
            for archivo in os.listdir(carpeta):
                if archivo.endswith(".py"):
                    usados = set(importaciones(os.path.join(carpeta, archivo)))
                    self.assertFalse(usados & prohibidos, f"{capa}/{archivo} importa {usados & prohibidos}")

    def test_qt_solo_dentro_de_ui_qt(self):
        """PySide6 (u otra Qt) solo puede importarse en ui_qt/; main_qt.py entra por ui_qt."""
        for relativa, ruta in archivos_del_proyecto():
            if relativa.split(os.sep)[0] == "ui_qt":
                continue
            usados = set(importaciones(ruta)) & QT
            self.assertFalse(usados, f"{relativa} importa Qt ({usados}); solo ui_qt/ puede hacerlo")

    def test_dominio_y_servicios_no_cargan_qt(self):
        """Importar domain y services no carga Qt (incluye importaciones indirectas)."""
        import subprocess
        import sys
        codigo = ("import sys; sys.path.insert(0, %r); import domain.modelos_colas, domain.costos, "
                  "services.calculadora_service, services.formulas, services.comparacion_service; "
                  "print(any(m.split('.')[0] in %r for m in sys.modules))" % (RAIZ, QT))
        salida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, check=True)
        self.assertEqual(salida.stdout.strip(), "False", salida.stderr)


if __name__ == "__main__":
    unittest.main()
