"""
barra_titulo.py
En Windows 10 (20H1+) y 11, pide al gestor de ventanas (DWM) que la barra de título nativa
siga al tema de la aplicación (atributo DWMWA_USE_IMMERSIVE_DARK_MODE).

Fallback silencioso: en otros sistemas, en plataformas Qt que no son la nativa de Windows
(p. ej. «offscreen» en las pruebas) o si el atributo no existe, no hace nada.
"""
import sys

DWMWA_USE_IMMERSIVE_DARK_MODE = 20              # Windows 10 20H1+ y Windows 11
DWMWA_USE_IMMERSIVE_DARK_MODE_ANTIGUO = 19      # Windows 10 1809 – 1909


def aplicar_barra_titulo(ventana, oscuro):
    """Devuelve True si Windows aceptó el cambio de color de la barra de título."""
    if sys.platform != "win32":
        return False
    try:
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.platformName() != "windows":
            return False
        import ctypes
        from ctypes import wintypes
        hwnd = wintypes.HWND(int(ventana.winId()))
        valor = ctypes.c_int(1 if oscuro else 0)
        dwm = ctypes.windll.dwmapi
        for atributo in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_ANTIGUO):
            if dwm.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(valor), ctypes.sizeof(valor)) == 0:
                return True
    except (AttributeError, OSError, ValueError):
        pass
    return False
