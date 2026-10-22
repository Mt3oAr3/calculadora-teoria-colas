"""
tema.py
Paletas claro / oscuro y la hoja de estilos QSS de toda la interfaz Qt.

Todos los colores de la interfaz salen de PALETAS: ningún otro módulo escribe
colores literales. Los widgets eligen su aspecto con propiedades dinámicas
(p. ej. rol="ayuda", nivel="ok", error="true") que la hoja de estilos resuelve.
"""
from string import Template

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

PALETAS = {
    "claro": {
        "fondo": "#f3f4f7", "superficie": "#ffffff", "superficie_alt": "#f7f8fa",
        "superficie_hover": "#edf0f4", "lateral": "#e9ecf1", "borde": "#dde1e7", "borde_fuerte": "#c3cad5",
        "texto": "#1c2331", "texto_2": "#4a5466", "texto_3": "#7f8898",
        "acento": "#2f6fde", "acento_hover": "#2459b8", "acento_suave": "#e6eefc", "acento_texto": "#ffffff",
        "seleccion": "#d5e3fb",
        "error": "#c0392b", "error_fondo": "#fdecea",
        "ok": "#17784c", "ok_fondo": "#e4f3ea",
        "aviso": "#9a5208", "aviso_fondo": "#fdf0de",
        "info": "#2f6fde", "info_fondo": "#e6eefc",
        "fila_cumple": "#e1f3e7", "fila_mejor": "#fff1c7", "fila_principal": "#f2f6fd",
        "sombra": "#1c233126",
    },
    "oscuro": {
        "fondo": "#13161c", "superficie": "#1b1f27", "superficie_alt": "#20252e",
        "superficie_hover": "#262c37", "lateral": "#171a21", "borde": "#2c3340", "borde_fuerte": "#3c4454",
        "texto": "#e5e8ee", "texto_2": "#a9b1bf", "texto_3": "#737d8e",
        "acento": "#5b8def", "acento_hover": "#79a3f3", "acento_suave": "#1f2d48", "acento_texto": "#ffffff",
        "seleccion": "#284066",
        "error": "#ff7a70", "error_fondo": "#3b1f21",
        "ok": "#4cc38a", "ok_fondo": "#152e25",
        "aviso": "#f0a54a", "aviso_fondo": "#382814",
        "info": "#79a3f3", "info_fondo": "#1d2942",
        "fila_cumple": "#183224", "fila_mejor": "#3a3216", "fila_principal": "#1e2533",
        "sombra": "#00000099",
    },
}
NOMBRES = {"claro": "Tema claro", "oscuro": "Tema oscuro"}
FUENTE = "Segoe UI"
TAM_FUENTE = 10

_actual = "claro"


def actual():
    return _actual


def color(rol):
    """Color (texto #rrggbb o #rrggbbaa) del rol en el tema vigente."""
    return PALETAS[_actual][rol]


def qcolor(rol):
    """QColor del rol; acepta el formato #rrggbbaa de la paleta."""
    h = color(rol)
    c = QColor(h[:7])
    if len(h) == 9:
        c.setAlpha(int(h[7:], 16))
    return c


_QSS = Template("""
QWidget { color: $texto; font-family: "$fuente"; font-size: ${tam}pt; }
QMainWindow, #Contenido, QStackedWidget, #Pagina { background: $fondo; }
QToolTip { background: $superficie; color: $texto; border: 1px solid $borde_fuerte; padding: 4px 6px; }
QSplitter::handle { background: $fondo; }
QSplitter::handle:hover { background: $borde; }

/* Barra lateral */
#BarraLateral { background: $lateral; border-right: 1px solid $borde; }
#Marca { font-size: 13pt; font-weight: 600; color: $texto; }
#MarcaSub { color: $texto_3; font-size: 9pt; }
#Navegacion { background: transparent; border: none; outline: 0; }
#Navegacion::item { padding: 9px 12px; margin: 2px 0; border-radius: 8px; color: $texto_2; }
#Navegacion::item:hover { background: $superficie_hover; color: $texto; }
#Navegacion::item:selected { background: $acento_suave; color: $acento; font-weight: 600; }

/* Panel de entradas */
#PanelEntradas { background: $superficie; border-right: 1px solid $borde; }
#PanelEntradas QScrollArea, #PanelEntradas #CuerpoEntradas { background: $superficie; border: none; }
#Acciones { background: $superficie; border-top: 1px solid $borde; }
#CabeceraSeccion { background: transparent; border: none; text-align: left; padding: 8px 4px;
                   font-weight: 600; color: $texto; }
#CabeceraSeccion:hover { color: $acento; }
#CuerpoSeccion { background: $superficie_alt; border: 1px solid $borde; border-radius: 10px; }

QLabel[rol="titulo"] { font-size: 15pt; font-weight: 600; }
QLabel[rol="subtitulo"] { color: $texto_2; }
QLabel[rol="seccion"] { font-size: 11pt; font-weight: 600; }
QLabel[rol="subgrupo"] { color: $texto_2; font-weight: 600; padding-top: 4px; }
QLabel[rol="campo"] { color: $texto; }
QLabel[rol="campo"]:disabled, QLabel[rol="unidad"]:disabled { color: $texto_3; }
QLabel[rol="unidad"] { color: $texto_3; }
QLabel[rol="ayuda"], QLabel[rol="nota"] { color: $texto_3; font-size: 9pt; }
QLabel[rol="previa"] { color: $acento; font-size: 9pt; }
QLabel[rol="error"] { color: $error; font-size: 9pt; }
QLabel[rol="leyenda"] { color: $texto_2; font-size: 9pt; }
QLabel[rol="muestra"] { border: 1px solid $borde_fuerte; border-radius: 3px; }
QLabel[rol="muestra"][tipo="cumple"] { background: $fila_cumple; }
QLabel[rol="muestra"][tipo="mejor"] { background: $fila_mejor; }

QLineEdit, QComboBox, QSpinBox {
    background: $superficie; border: 1px solid $borde_fuerte; border-radius: 7px;
    padding: 5px 8px; min-height: 18px; selection-background-color: $seleccion; selection-color: $texto;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid $acento; }
QLineEdit:disabled, QComboBox:disabled { background: $superficie_alt; color: $texto_3; border-color: $borde; }
QLineEdit[error="true"] { border: 1px solid $error; background: $error_fondo; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: $superficie; border: 1px solid $borde_fuerte; selection-background-color: $acento_suave;
    selection-color: $texto; outline: 0; padding: 4px;
}
QRadioButton, QCheckBox { spacing: 6px; background: transparent; }
QRadioButton::indicator, QCheckBox::indicator {
    width: 14px; height: 14px; border: 1px solid $borde_fuerte; background: $superficie;
}
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator:hover, QCheckBox::indicator:hover { border-color: $acento; }
QRadioButton::indicator:checked { border: 5px solid $acento; width: 6px; height: 6px; }
QCheckBox::indicator:checked { background: $acento; border-color: $acento; }

QPushButton {
    background: $superficie; color: $texto; border: 1px solid $borde_fuerte; border-radius: 8px;
    padding: 7px 14px;
}
QPushButton:hover { background: $superficie_hover; }
QPushButton:pressed { background: $borde; }
QPushButton:disabled { color: $texto_3; border-color: $borde; background: $superficie_alt; }
QPushButton#Primario {
    background: $acento; color: $acento_texto; border: none; font-weight: 600; padding: 10px 14px;
}
QPushButton#Primario:hover { background: $acento_hover; }
QPushButton#Plano { background: transparent; border: none; color: $texto_2; padding: 6px 8px; }
QPushButton#Plano:hover { background: $superficie_hover; color: $texto; }

/* Resumen y tarjetas */
QLabel#Kendall { font-size: 18pt; font-weight: 700; }
QLabel#Descripcion { color: $texto_2; }
QLabel[rol="insignia"] { border-radius: 10px; padding: 3px 10px; font-weight: 600; font-size: 9pt; }
QLabel[rol="insignia"][nivel="ok"] { background: $ok_fondo; color: $ok; }
QLabel[rol="insignia"][nivel="aviso"] { background: $aviso_fondo; color: $aviso; }
QLabel[rol="insignia"][nivel="error"] { background: $error_fondo; color: $error; }
QLabel[rol="insignia"][nivel="info"] { background: $info_fondo; color: $info; }
QLabel[rol="mensaje"] { border-radius: 8px; padding: 8px 12px; }
QLabel[rol="mensaje"][nivel="ok"] { background: $ok_fondo; color: $ok; }
QLabel[rol="mensaje"][nivel="aviso"] { background: $aviso_fondo; color: $aviso; }
QLabel[rol="mensaje"][nivel="error"] { background: $error_fondo; color: $error; }
QLabel[rol="mensaje"][nivel="info"] { background: $info_fondo; color: $info; }

#Tarjeta { background: $superficie; border: 1px solid $borde; border-radius: 12px; }
#Tarjeta:hover { border: 1px solid $acento; }
#Tarjeta[activa="true"] { border: 2px solid $acento; }
#Tarjeta QLabel { background: transparent; }
QLabel#TarjetaSimbolo { color: $acento; font-weight: 700; font-size: 10pt; }
QLabel#TarjetaNombre { color: $texto_3; font-size: 9pt; }
QLabel#TarjetaValor { font-size: 15pt; font-weight: 600; }
#Tarjeta[vigente="false"] QLabel#TarjetaValor { color: $texto_3; }

/* Tablas */
#Bloque { background: $superficie; border: 1px solid $borde; border-radius: 12px; }
QTableView {
    background: $superficie; alternate-background-color: $superficie_alt; border: none;
    gridline-color: $borde; selection-background-color: $seleccion; selection-color: $texto;
}
QTableView::item { padding: 4px 8px; }
QHeaderView::section {
    background: $superficie_alt; color: $texto_2; border: none; border-bottom: 1px solid $borde;
    padding: 7px 8px; font-weight: 600;
}
QTableCornerButton::section { background: $superficie_alt; border: none; }
QLabel[rol="vacio"] { color: $texto_3; padding: 24px; }

/* Panel de fórmulas */
#PanelFormulas { background: $superficie; border-left: 1px solid $borde; }
#ScrollFormulas, #CuerpoFormulas { background: $superficie; border: none; }
QLabel#FormulaTitulo { font-size: 13pt; font-weight: 600; }
QLabel#FormulaResultado { font-size: 15pt; font-weight: 700; color: $acento; }
#CajaFormula { background: $superficie_alt; border: 1px solid $borde; border-radius: 10px; }
#CajaFormula QLabel { background: transparent; }
#FilaFormula, #FilaFormula QWidget { background: transparent; border: none; }
QFrame[rol="separador"] { background: $borde; border: none; max-height: 1px; min-height: 1px; }

/* Barras de desplazamiento */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle { background: $borde_fuerte; border-radius: 4px; min-height: 30px; min-width: 30px; }
QScrollBar::handle:hover { background: $texto_3; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QStatusBar { background: $lateral; color: $texto_2; border-top: 1px solid $borde; }
QStatusBar QLabel { color: $texto_2; padding: 0 6px; }
QListWidget#IndiceGraficas, QTreeWidget#IndiceGraficas {
    background: $superficie; border: 1px solid $borde; border-radius: 10px; outline: 0; padding: 4px;
}
QTreeWidget#IndiceGraficas::item { padding: 4px 2px; }
QTreeWidget#IndiceGraficas::item:selected { background: $acento_suave; color: $acento; }
""")


def hoja_estilo(nombre):
    return _QSS.substitute(PALETAS[nombre], fuente=FUENTE, tam=TAM_FUENTE)


def _paleta_qt(nombre):
    """QPalette coherente con la hoja de estilos (lo que QSS no cubre: flechas, casillas, menús)."""
    c = {k: QColor(v[:7]) for k, v in PALETAS[nombre].items()}
    p = QPalette()
    p.setColor(QPalette.Window, c["fondo"])
    p.setColor(QPalette.WindowText, c["texto"])
    p.setColor(QPalette.Base, c["superficie"])
    p.setColor(QPalette.AlternateBase, c["superficie_alt"])
    p.setColor(QPalette.Text, c["texto"])
    p.setColor(QPalette.Button, c["superficie"])
    p.setColor(QPalette.ButtonText, c["texto"])
    p.setColor(QPalette.Highlight, c["acento"])
    p.setColor(QPalette.HighlightedText, c["acento_texto"])
    p.setColor(QPalette.ToolTipBase, c["superficie"])
    p.setColor(QPalette.ToolTipText, c["texto"])
    p.setColor(QPalette.PlaceholderText, c["texto_3"])
    p.setColor(QPalette.Light, c["superficie_hover"])
    p.setColor(QPalette.Mid, c["borde_fuerte"])
    p.setColor(QPalette.Dark, c["borde_fuerte"])
    for rol in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, rol, c["texto_3"])
    return p


def aplicar(app: QApplication, nombre):
    """Aplica el tema a toda la aplicación (los widgets se repintan solos)."""
    global _actual
    _actual = nombre
    app.setStyle("Fusion")
    app.setFont(QFont(FUENTE, TAM_FUENTE))
    app.setPalette(_paleta_qt(nombre))
    app.setStyleSheet(hoja_estilo(nombre))


def refrescar(widget):
    """Vuelve a evaluar la hoja de estilos tras cambiar una propiedad dinámica."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
