"""
Accesibilidad de la paleta (ui_qt/tema.py): contraste WCAG 2.x de los pares texto/fondo y
componente/fondo en los temas claro y oscuro. ≥ 4.5:1 texto normal, ≥ 3:1 texto grande,
iconos y bordes de componentes. Se omite si PySide6 no está instalado.
"""
import importlib.util
import re
import unittest

import utilidades  # noqa: F401  (agrega la raíz del proyecto al path)

HAY_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAY_QT, "PySide6 no está instalado")
class TestContraste(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from ui_qt import tema
        cls.tema = tema

    def test_formula_de_contraste(self):
        c = self.tema.contraste
        self.assertAlmostEqual(c("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(c("#ffffff", "#ffffff"), 1.0, places=6)
        self.assertAlmostEqual(c("#777777", "#ffffff"), 4.48, places=2)     # valor de referencia WCAG

    def test_pares_de_los_dos_temas(self):
        fallos = []
        for nombre, paleta in self.tema.PALETAS.items():
            for frente, fondo, minimo, desc in self.tema.PARES_CONTRASTE:
                r = self.tema.contraste(paleta[frente], paleta[fondo])
                if r < minimo:
                    fallos.append(f"{nombre}: {desc} ({frente} sobre {fondo}) = {r:.2f} < {minimo}")
        self.assertEqual(fallos, [], "\n".join(fallos))

    def test_colores_de_marca_intactos(self):
        for paleta in self.tema.PALETAS.values():
            self.assertEqual(paleta["primario"], "#ea0f02")
            self.assertEqual(paleta["secundario"], "#00841d")

    def test_sin_azul_en_la_paleta(self):
        """Ningún token es azul (tono 190°–260° con saturación apreciable)."""
        import colorsys
        for nombre, paleta in self.tema.PALETAS.items():
            for token, valor in paleta.items():
                r, g, b = (int(valor[i:i + 2], 16) / 255 for i in (1, 3, 5))
                h, l_, s = colorsys.rgb_to_hls(r, g, b)
                self.assertFalse(190 <= h * 360 <= 260 and s > 0.25 and 0.1 < l_ < 0.95,
                                 f"{nombre}.{token} = {valor} es azul")

    def test_sin_colores_sueltos_en_ui_qt(self):
        """Solo tema.py escribe colores #rrggbb dentro de ui_qt/."""
        import os
        from utilidades import RAIZ
        carpeta = os.path.join(RAIZ, "ui_qt")
        patron = re.compile(r"#[0-9a-fA-F]{6}\b")
        for archivo in os.listdir(carpeta):
            if archivo.endswith(".py") and archivo != "tema.py":
                with open(os.path.join(carpeta, archivo), encoding="utf-8") as fh:
                    self.assertIsNone(patron.search(fh.read()), f"color literal en ui_qt/{archivo}")


if __name__ == "__main__":
    unittest.main()
