"""
main_qt.py
Punto de entrada de la interfaz moderna (PySide6) de la Calculadora de Teoría de Colas.

    python main_qt.py            (tema claro)
    python main_qt.py --oscuro   (tema oscuro)

La versión Tkinter sigue disponible con: python main.py
"""
from ui_qt.app import main

if __name__ == "__main__":
    main()
