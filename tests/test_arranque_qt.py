"""
Arranque de la interfaz Qt: una sola QApplication y una sola ventana visible, sin ventanas
temporales (antes cada tabla aparecía un instante como ventana propia), y sin Tkinter ni pyplot.
Se omite si PySide6 no está instalado.
"""
import importlib.util
import os
import subprocess
import sys
import unittest

from utilidades import RAIZ

HAY_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAY_QT, "PySide6 no está instalado")
class TestArranqueQt(unittest.TestCase):

    def test_solo_se_muestra_la_ventana_principal(self):
        from ui_qt import soporte_pruebas as sp
        sp.aplicacion()
        from ui_qt.ventana_principal import VentanaPrincipal
        espia = sp.espiar_ventanas()
        try:
            v = VentanaPrincipal()
            v.show()
            sp.esperar(300)
            v.mostrar_formula("Lq")                      # el panel superpuesto tampoco es ventana propia
            sp.esperar(300)
        finally:
            espia.detener()
        try:
            nombres = [type(w).__name__ for w in espia.mostradas]
            self.assertEqual(espia.mostradas, [v], f"ventanas mostradas durante el arranque: {nombres}")
            self.assertEqual(sp.ventanas_visibles(), [v])
        finally:
            v.formulas.cerrar()
            v.close()
            v.deleteLater()
            sp.procesar()

    def test_importar_ui_qt_no_carga_tkinter_ni_pyplot(self):
        """En un proceso aparte: importar ui_qt (y armar la ventana) no carga tkinter ni pyplot."""
        codigo = (
            "import os, sys; sys.path.insert(0, %r)\n"
            "os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
            "import ui_qt.app, ui_qt.ventana_principal\n"
            "from ui_qt import soporte_pruebas as sp\n"
            "sp.aplicacion()\n"
            "v = ui_qt.ventana_principal.VentanaPrincipal(); v.show(); sp.procesar()\n"
            "import matplotlib\n"
            "print('tkinter' in sys.modules, 'matplotlib.pyplot' in sys.modules, matplotlib.rcParams['backend'])\n"
        ) % RAIZ
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        salida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, env=entorno,
                                timeout=120)
        self.assertEqual(salida.returncode, 0, salida.stderr[-2000:])
        tk, pyplot, backend = salida.stdout.strip().splitlines()[-1].split()
        self.assertEqual(tk, "False", "ui_qt cargó tkinter")
        self.assertEqual(pyplot, "False", "ui_qt cargó matplotlib.pyplot")
        self.assertEqual(backend.lower(), "agg")


if __name__ == "__main__":
    unittest.main()
