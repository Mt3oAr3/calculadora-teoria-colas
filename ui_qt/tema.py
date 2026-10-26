"""
tema.py
Paleta de marca (claro / oscuro), medidas de layout y la hoja de estilos QSS de toda la interfaz Qt.

Colores base de la marca: rojo #ea0f02 (principal), verde #00841d (secundario), blanco y negro.
Todos los colores de la interfaz salen de PALETAS (tokens): ningún otro módulo escribe colores
literales. Los widgets eligen su aspecto con propiedades dinámicas (p. ej. rol="ayuda",
nivel="ok", error="true") que la hoja de estilos resuelve.

Tokens derivados (ajustados para cumplir contraste WCAG, ver PARES_CONTRASTE):
  primario_texto / secundario_texto: rojo y verde para TEXTO y bordes finos sobre superficies
  (más oscuros en claro, más claros en oscuro); los colores base se usan como relleno.
"""
from string import Template

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

ROJO_MARCA = "#ea0f02"
VERDE_MARCA = "#00841d"

PALETAS = {
    "claro": {
        # Marca
        "primario": ROJO_MARCA, "primario_hover": "#c90d02", "primario_presionado": "#a80b01",
        "primario_tinte": "#fde9e8", "primario_texto": "#c40c01", "primario_sobre": "#ffffff",
        "secundario": VERDE_MARCA, "secundario_hover": "#006f18", "secundario_tinte": "#e6f3e9",
        "secundario_texto": "#00701a",
        # Neutros
        "fondo": "#ffffff", "superficie": "#f6f6f6", "superficie_elevada": "#ffffff",
        "superficie_hover": "#ececec", "barra": "#f6f6f6",
        "borde": "#e2e2e2", "borde_fuerte": "#cfcfcf", "borde_control": "#8c8c8c",
        "texto": "#000000", "texto_2": "#4d4d4d", "texto_3": "#6b6b6b",
        # Tablas
        "tabla_fondo": "#ffffff", "fila_alterna": "#f3f3f3", "seleccion": "#fde9e8",
        "fila_cumple": "#ebebeb", "fila_mejor": "#e6f3e9", "encabezado_tabla": "#f6f6f6",
        # Estados
        "advertencia_fondo": "#fff4dc", "advertencia_borde": "#d98a00", "advertencia_texto": "#5c3300",
        "advertencia_boton": "#9a5a00", "advertencia_boton_hover": "#7f4a00", "advertencia_boton_texto": "#ffffff",
        "error": "#b00b02", "error_fondo": "#fdecea",
        "ok": "#00701a", "ok_fondo": "#e6f3e9",
        "aviso": "#7a4600", "aviso_fondo": "#fff4dc",
        "info_fondo": "#f4f4f4", "info_borde": "#dedede", "info_icono": VERDE_MARCA, "info_icono_sobre": "#ffffff",
        # Panel de fórmulas y sombras
        "formula_fondo": "#f7f7f7", "formula_borde": "#dcdcdc", "resultado_fondo": "#fde9e8",
        "sombra": "#00000026", "sombra_panel": "#00000038",
        # Gráficas (matplotlib): fondo, ejes, rejilla y series
        "grafica_fondo": "#ffffff", "grafica_ejes": "#8c8c8c", "grafica_rejilla": "#e6e6e6",
        "serie_1": ROJO_MARCA, "serie_2": VERDE_MARCA, "serie_3": "#3d3d3d",
    },
    "oscuro": {
        "primario": ROJO_MARCA, "primario_hover": "#ff3a2d", "primario_presionado": "#c90d02",
        "primario_tinte": "#3a1614", "primario_texto": "#ff6b5f", "primario_sobre": "#ffffff",
        "secundario": VERDE_MARCA, "secundario_hover": "#00a024", "secundario_tinte": "#12301b",
        "secundario_texto": "#4cc964",
        "fondo": "#121212", "superficie": "#1e1e1e", "superficie_elevada": "#242424",
        "superficie_hover": "#2c2c2c", "barra": "#181818",
        "borde": "#2e2e2e", "borde_fuerte": "#3d3d3d", "borde_control": "#7a7a7a",
        "texto": "#ffffff", "texto_2": "#c4c4c4", "texto_3": "#9e9e9e",
        "tabla_fondo": "#1a1a1a", "fila_alterna": "#232323", "seleccion": "#3a1614",
        "fila_cumple": "#2e2e2e", "fila_mejor": "#12301b", "encabezado_tabla": "#1e1e1e",
        "advertencia_fondo": "#3a2a10", "advertencia_borde": "#c98a2e", "advertencia_texto": "#ffd391",
        "advertencia_boton": "#e0a040", "advertencia_boton_hover": "#f0b860", "advertencia_boton_texto": "#1f1400",
        "error": "#ff7a6e", "error_fondo": "#3b1715",
        "ok": "#4cc964", "ok_fondo": "#12301b",
        "aviso": "#f0b05a", "aviso_fondo": "#3a2a10",
        "info_fondo": "#1e1e1e", "info_borde": "#333333", "info_icono": "#4cc964", "info_icono_sobre": "#0b1f0f",
        "formula_fondo": "#1c1c1c", "formula_borde": "#353535", "resultado_fondo": "#3a1614",
        "sombra": "#00000099", "sombra_panel": "#000000a0",
        "grafica_fondo": "#1a1a1a", "grafica_ejes": "#7a7a7a", "grafica_rejilla": "#2e2e2e",
        "serie_1": "#ff4a3d", "serie_2": "#4cc964", "serie_3": "#c4c4c4",
    },
}

# Pares (primer plano, fondo, mínimo, descripción) que deben cumplir WCAG en los dos temas:
# 4.5 para texto normal, 3.0 para texto grande e iconos / bordes de componentes.
PARES_CONTRASTE = [
    ("texto", "fondo", 4.5, "texto principal sobre la ventana"),
    ("texto", "superficie", 4.5, "texto principal sobre paneles"),
    ("texto_2", "superficie", 4.5, "texto secundario / ayudas"),
    ("texto_3", "superficie", 4.5, "texto atenuado (ceros, notas)"),
    ("texto_3", "fondo", 4.5, "texto atenuado sobre la ventana"),
    ("texto", "fila_alterna", 4.5, "texto en filas alternas"),
    ("texto", "seleccion", 4.5, "texto en la fila seleccionada"),
    ("texto", "fila_mejor", 4.5, "texto en la fila de menor costo"),
    ("texto", "fila_cumple", 4.5, "texto en filas que cumplen"),
    ("texto_2", "encabezado_tabla", 4.5, "encabezados de tabla"),
    ("primario_sobre", "primario", 4.5, "texto del botón Calcular"),
    ("primario_texto", "superficie", 4.5, "acentos rojos (símbolo de tarjeta, pestaña activa)"),
    ("primario_texto", "fondo", 4.5, "acentos rojos sobre la ventana"),
    ("primario_texto", "resultado_fondo", 4.5, "resultado en el panel de fórmulas"),
    ("secundario_texto", "superficie", 4.5, "botones secundarios y éxito"),
    ("secundario_texto", "fondo", 4.5, "texto verde sobre la ventana"),
    ("ok", "ok_fondo", 4.5, "mensaje de éxito"),
    ("advertencia_texto", "advertencia_fondo", 4.5, "texto del aviso ámbar"),
    ("advertencia_boton_texto", "advertencia_boton", 4.5, "botón del aviso ámbar"),
    ("aviso", "aviso_fondo", 4.5, "mensaje de sistema inestable"),
    ("error", "error_fondo", 4.5, "mensaje de error"),
    ("error", "superficie", 4.5, "error junto al campo"),
    ("texto", "info_fondo", 4.5, "texto de las cajas informativas"),
    ("info_icono", "info_fondo", 3.0, "icono «i» de las cajas informativas"),
    ("borde_control", "superficie_elevada", 3.0, "borde de campos y casillas"),
    ("borde_control", "superficie", 3.0, "borde de casillas sobre paneles"),
    ("primario_texto", "superficie_elevada", 3.0, "borde de campo con foco"),
    ("primario", "fondo", 3.0, "botón principal sobre la ventana"),
    ("secundario_texto", "superficie_elevada", 3.0, "contorno de botones secundarios"),
    ("secundario_texto", "secundario_tinte", 4.5, "botón secundario con el cursor encima"),
    ("secundario_texto", "fila_mejor", 4.5, "texto verde de la fila de menor costo"),
    ("info_icono_sobre", "info_icono", 3.0, "letra «i» dentro del icono informativo"),
    ("texto_3", "fila_alterna", 4.5, "ceros atenuados en filas alternas"),
    ("texto", "grafica_fondo", 4.5, "títulos de las gráficas"),
    ("texto_2", "grafica_fondo", 4.5, "rótulos y valores de las gráficas"),
    ("serie_1", "grafica_fondo", 3.0, "primera serie de las gráficas"),
    ("serie_2", "grafica_fondo", 3.0, "segunda serie de las gráficas"),
    ("serie_3", "grafica_fondo", 3.0, "tercera serie de las gráficas"),
    ("grafica_ejes", "grafica_fondo", 3.0, "ejes de las gráficas"),
    ("texto_2", "barra", 4.5, "botón de parámetros en la barra superior"),
    ("primario_texto", "primario_tinte", 4.5, "botón de parámetros con el panel visible"),
    ("texto", "superficie_elevada", 4.5, "opciones de las listas desplegables"),
    ("texto", "superficie_hover", 4.5, "opción de una lista con el cursor encima"),
    ("texto", "primario_tinte", 4.5, "opción elegida de una lista desplegable"),
    ("texto_2", "superficie_elevada", 3.0, "flecha (chevron) de las listas desplegables"),
]

NOMBRES = {"claro": "Tema claro", "oscuro": "Tema oscuro"}
# Iconos de estado: el color nunca es la única señal. Glifos sin variante emoji (o con U+FE0E)
# para que Windows no los pinte con la fuente de emoji a color.
ICONOS = {"error": "✕", "aviso": "⚠︎", "ok": "✓", "info": "i"}
FUENTE = "Segoe UI"
TAM_FUENTE = 10

# Medidas de layout (px) usadas por los componentes: ningún tamaño suelto por el código.
LAYOUT = {
    # Tarjetas de indicadores: ancho mínimo por tarjeta para usar la versión normal o la compacta
    "tarjeta_ancho_normal": 168, "tarjeta_ancho_compacta": 112, "tarjetas_espacio": 10,
    "tarjeta_margen": (14, 10, 14, 12), "tarjeta_margen_compacta": (10, 6, 10, 8),
    "tarjeta_sombra": 18,
    # Banner global de datos desactualizados
    "banner_ms": 160, "banner_margen": (16, 11, 16, 11), "banner_espacio": 14,
    "pagina_margen": (0, 12, 0, 12),
    # Márgenes del área de resultados y de la barra superior
    "area_margen": (16, 12, 16, 0), "barra_superior_margen": (10, 6, 12, 6), "barra_superior_espacio": 6,
    # Panel de parámetros ocultable (Ctrl+B): duración de la animación y ancho máximo recordado
    "panel_ms": 200, "panel_fraccion_max": 0.5,
    # Panel superpuesto «Cómo se calculó»
    "drawer_fraccion": 0.40, "drawer_min": 360, "drawer_max": 620, "drawer_ms": 180, "drawer_sombra": 28,
    "drawer_margen": 18, "drawer_espacio": 14,
    # Cajas informativas y estado vacío
    "info_margen": (12, 10, 14, 10), "info_espacio": 10, "info_icono": 18,
    "vacio_margen": (24, 28, 24, 28), "vacio_espacio": 8, "vacio_icono": 40,
    # Ecuaciones: tamaño en puntos (normal y mínimo antes de desplazar en horizontal)
    "formula_puntos": 17, "formula_puntos_min": 11, "caja_formula_margen": (16, 12, 16, 14),
    "caja_formula_espacio": 10,
    # Formulario de parámetros
    "form_espacio_v": 4, "form_espacio_h": 12, "form_separacion_campos": 6,
    "form_margen_cabecera": (16, 14, 16, 8), "form_margen_cuerpo": (12, 6, 12, 12),
    "seccion_margen": (12, 10, 12, 12), "form_ancho_campo": 72, "form_ancho_unidad": 80,
    "form_relleno_combo": 44,
    # Listas desplegables (ui_qt/combo.py): chevron propio y ancho extra de la lista emergente
    "combo_flecha_ancho": 9, "combo_flecha_grosor": 1.6, "combo_flecha_margen": 11, "combo_lista_extra": 40,
    "combo_lista_margen": 5,
    # Tablas
    "tabla_alto_fila": 30, "tabla_relleno_celda": 16, "tabla_relleno_vertical": 12,
    "tabla_ancho_min_texto": 140, "tabla_ancho_max": 420,
}

_actual = "claro"


def actual():
    return _actual


def color(rol, nombre=None):
    """Color (texto #rrggbb o #rrggbbaa) del rol en el tema vigente (o en `nombre`)."""
    return PALETAS[nombre or _actual][rol]


def qcolor(rol):
    """QColor del rol; acepta el formato #rrggbbaa de la paleta."""
    h = color(rol)
    c = QColor(h[:7])
    if len(h) == 9:
        c.setAlpha(int(h[7:], 16))
    return c


def colores_grafica(nombre=None):
    """Colores para visualization.graficas_colas.dibujar (ctx['colores']) en el tema vigente."""
    p = PALETAS[nombre or _actual]
    return {"fondo": p["grafica_fondo"], "tinta": p["texto"], "tinta_2": p["texto_2"],
            "tinta_3": p["grafica_ejes"], "rejilla": p["grafica_rejilla"],
            "serie": [p["serie_1"], p["serie_2"], p["serie_3"]]}


def luminancia(hex_color):
    """Luminancia relativa WCAG 2.x de un color #rrggbb."""
    def canal(v):
        c = int(v, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_color.lstrip("#")[:6]
    r, g, b = (canal(h[i:i + 2]) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    """Razón de contraste WCAG entre dos colores #rrggbb (1 a 21)."""
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


_QSS = Template("""
QWidget { color: $texto; font-family: "$fuente"; font-size: ${tam}pt; }
QMainWindow, #Contenido, QStackedWidget, #Pagina { background: $fondo; }
QToolTip { background: $superficie_elevada; color: $texto; border: 1px solid $borde_fuerte; padding: 4px 6px; }
QSplitter::handle { background: $fondo; }
QSplitter::handle:hover { background: $borde; }

/* Barra superior */
#BarraSuperior { background: $barra; border-bottom: 1px solid $borde; }
#Marca { font-size: 11pt; font-weight: 600; color: $texto; }
#MarcaSub { color: $texto_3; font-size: 9pt; }
QPushButton#BotonParametros {
    background: transparent; color: $texto_2; border: 1px solid transparent; border-radius: 8px;
    padding: 3px 10px; font-size: 12pt;
}
QPushButton#BotonParametros:hover { background: $superficie_hover; color: $texto; }
QPushButton#BotonParametros:checked { background: $primario_tinte; color: $primario_texto; }
QPushButton#BotonParametros:checked:hover { border-color: $primario_texto; }

/* Banner global: datos cambiados sin recalcular (siempre ámbar, nunca rojo de marca) */
#Banner { background: $advertencia_fondo; border-bottom: 1px solid $advertencia_borde; }
#Banner QLabel { color: $advertencia_texto; background: transparent; }
QLabel#BannerIcono { font-weight: 700; }
QLabel#BannerTexto { font-weight: 600; }
QPushButton#BannerBoton {
    background: $advertencia_boton; color: $advertencia_boton_texto; border: none; font-weight: 600;
    padding: 5px 14px;
}
QPushButton#BannerBoton:hover { background: $advertencia_boton_hover; }

/* Pestañas */
#AreaResultados { background: $fondo; }
QTabWidget::pane { border: none; border-top: 1px solid $borde; background: $fondo; top: -1px; }
QTabWidget::tab-bar { left: 0; }
QTabBar { background: transparent; }
QTabBar::tab {
    background: transparent; color: $texto_2; border: none; border-bottom: 2px solid transparent;
    padding: 8px 14px; margin-right: 4px;
}
QTabBar::tab:hover { color: $texto; border-bottom: 2px solid $borde_fuerte; }
QTabBar::tab:selected { color: $primario_texto; font-weight: 600; border-bottom: 2px solid $primario; }
#PaginaScroll, #PaginaScroll > QWidget > QWidget { background: $fondo; border: none; }

/* Panel de entradas */
#PanelEntradas { background: $superficie; border-right: 1px solid $borde; }
#PanelEntradas QScrollArea, #PanelEntradas #CuerpoEntradas { background: $superficie; border: none; }
#Acciones { background: $superficie; border-top: 1px solid $borde; }
#CabeceraEntradas { background: $superficie; border-bottom: 1px solid transparent; }
#CabeceraEntradas[desplazado="true"] { border-bottom: 1px solid $borde_fuerte; }
#CabeceraSeccion { background: transparent; border: none; text-align: left; padding: 8px 4px;
                   font-weight: 600; color: $texto; }
#CabeceraSeccion:hover { color: $primario_texto; }
#CuerpoSeccion { background: $superficie_elevada; border: 1px solid $borde; border-radius: 10px; }

QLabel[rol="titulo"] { font-size: 15pt; font-weight: 600; }
QLabel[rol="subtitulo"] { color: $texto_2; }
QLabel[rol="seccion"] { font-size: 11pt; font-weight: 600; }
QLabel[rol="subgrupo"] { color: $texto_2; font-weight: 600; padding-top: 4px; }
QLabel[rol="campo"] { color: $texto; }
QLabel[rol="campo"]:disabled, QLabel[rol="unidad"]:disabled { color: $texto_3; }
QLabel[rol="unidad"] { color: $texto_3; }
QLabel[rol="ayuda"], QLabel[rol="nota"] { color: $texto_3; font-size: 9pt; }
QLabel[rol="previa"] { color: $texto_2; font-size: 9pt; }
QLabel[rol="error"] { color: $error; font-size: 9pt; }
QLabel[rol="leyenda"] { color: $texto_2; font-size: 9pt; }
QLabel[rol="muestra"] { border: 1px solid $borde_control; border-radius: 3px; }
QLabel[rol="muestra"][tipo="cumple"] { background: $fila_cumple; }
QLabel[rol="muestra"][tipo="mejor"] { background: $fila_mejor; border-color: $secundario_texto; }

QLineEdit, QComboBox, QSpinBox {
    background: $superficie_elevada; border: 1px solid $borde_control; border-radius: 7px;
    padding: 5px 8px; min-height: 18px; selection-background-color: $primario_tinte; selection-color: $texto;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid $primario_texto; }
QLineEdit:disabled, QComboBox:disabled { background: $superficie; color: $texto_3; border-color: $borde_fuerte; }
QLineEdit[error="true"] { border: 1px solid $error; background: $error_fondo; }
/* Listas desplegables (ui_qt/combo.py): la flecha es un chevron propio, la lista emergente un
   contenedor redondeado (#PopupCombo, ventana translúcida) y cada opción un ::item */
QComboBox { combobox-popup: 0; padding-right: 28px; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
#PopupCombo { background: $superficie_elevada; border: 1px solid $borde_fuerte; border-radius: 8px; }

QComboBox QAbstractItemView {
    background: transparent; border: none; outline: 0; padding: 0px; color: $texto;
    selection-background-color: $primario_tinte; selection-color: $texto;
}
QComboBox QAbstractItemView::item {
    min-height: 24px; padding: 4px 10px; border: none; border-radius: 6px; color: $texto;
}
QComboBox QAbstractItemView::item:hover { background: $superficie_hover; color: $texto; }
QComboBox QAbstractItemView::item:selected { background: $primario_tinte; color: $texto; }

QRadioButton, QCheckBox { spacing: 6px; background: transparent; }
QRadioButton::indicator, QCheckBox::indicator {
    width: 14px; height: 14px; border: 1px solid $borde_control; background: $superficie_elevada;
}
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator:hover, QCheckBox::indicator:hover { border-color: $primario_texto; }
QRadioButton::indicator:checked { border: 5px solid $primario; width: 6px; height: 6px; }
QCheckBox::indicator:checked { background: $primario; border-color: $primario; }

QPushButton {
    background: $superficie_elevada; color: $texto; border: 1px solid $borde_fuerte; border-radius: 8px;
    padding: 7px 14px;
}
QPushButton:hover { background: $superficie_hover; }
QPushButton:pressed { background: $borde; }
QPushButton:disabled { color: $texto_3; border-color: $borde; background: $superficie; }
QPushButton#Primario {
    background: $primario; color: $primario_sobre; border: none; font-weight: 600; padding: 10px 14px;
}
QPushButton#Primario:hover { background: $primario_hover; }
QPushButton#Primario:pressed { background: $primario_presionado; }
QPushButton#Secundario {
    background: transparent; color: $secundario_texto; border: 1px solid $secundario_texto; font-weight: 600;
}
QPushButton#Secundario:hover { background: $secundario_tinte; }
QPushButton#Secundario:pressed { background: $secundario_tinte; border-color: $secundario_hover; }
QPushButton#Secundario:disabled { color: $texto_3; border-color: $borde_fuerte; background: transparent; }
QPushButton#Plano { background: transparent; border: none; color: $texto_2; padding: 6px 8px; }
QPushButton#Plano:hover { background: $superficie_hover; color: $texto; }

/* Encabezado del modelo y tarjetas */
QLabel#Kendall { font-size: 18pt; font-weight: 700; }
QLabel#Descripcion { color: $texto_2; }
QLabel[rol="insignia"] { border-radius: 10px; padding: 3px 10px; font-weight: 600; font-size: 9pt; }
QLabel[rol="insignia"][nivel="ok"] { background: $ok_fondo; color: $ok; }
QLabel[rol="insignia"][nivel="aviso"] { background: $aviso_fondo; color: $aviso; }
QLabel[rol="insignia"][nivel="error"] { background: $error_fondo; color: $error; }
QLabel[rol="mensaje"] { border-radius: 8px; padding: 8px 12px; }
QLabel[rol="mensaje"][nivel="ok"] { background: $ok_fondo; color: $ok; }
QLabel[rol="mensaje"][nivel="aviso"] { background: $aviso_fondo; color: $aviso; }
QLabel[rol="mensaje"][nivel="error"] { background: $error_fondo; color: $error; }

#Tarjeta { background: $superficie; border: 1px solid $borde; border-radius: 12px; }
#Tarjeta:hover { border: 1px solid $primario_texto; }
#Tarjeta[activa="true"] { border: 2px solid $primario; background: $primario_tinte; }
#Tarjeta QLabel { background: transparent; }
QLabel#TarjetaSimbolo { color: $primario_texto; font-weight: 700; font-size: 10pt; }
QLabel#TarjetaNombre { color: $texto_3; font-size: 9pt; }
QLabel#TarjetaValor { font-size: 15pt; font-weight: 600; color: $texto; }
#Tarjeta[compacta="true"] QLabel#TarjetaSimbolo { font-size: 9pt; }
#Tarjeta[compacta="true"] QLabel#TarjetaNombre { font-size: 8pt; }
#Tarjeta[compacta="true"] QLabel#TarjetaValor { font-size: 12pt; }
#Tarjeta[vigente="false"] QLabel#TarjetaValor { color: $texto_3; }

/* Tablas */
#Bloque { background: $tabla_fondo; border: 1px solid $borde; border-radius: 12px; }
QTableView {
    background: $tabla_fondo; alternate-background-color: $fila_alterna; border: none;
    gridline-color: $borde; selection-background-color: $seleccion; selection-color: $texto;
}
QTableView::item { padding: 4px 8px; }
QHeaderView::section {
    background: $encabezado_tabla; color: $texto_2; border: none; border-bottom: 1px solid $borde;
    padding: 7px 8px; font-weight: 600;
}
QTableCornerButton::section { background: $encabezado_tabla; border: none; }
/* El orden se indica con ↑/↓ delante del título: la flecha nativa no ocupa lugar ni desalinea cifras */
QHeaderView::up-arrow, QHeaderView::down-arrow { image: none; width: 0px; height: 0px; }

/* Caja informativa (InfoBox) */
#InfoBox { background: $info_fondo; border: 1px solid $info_borde; border-radius: 8px; }
#InfoBox QLabel { background: transparent; }
QLabel#InfoIcono {
    background: $info_icono; color: $info_icono_sobre; border-radius: 9px; font-weight: 700; font-size: 9pt;
}
QLabel#InfoTexto { color: $texto; }

/* Estado vacío (sin costos) */
#EstadoVacio { background: transparent; }
QLabel#VacioIcono { color: $texto_3; font-size: 26pt; }
QLabel#VacioTitulo { font-size: 12pt; font-weight: 600; color: $texto; }
QLabel#VacioTexto { color: $texto_2; }
QLabel[rol="vacio"] { color: $texto_3; padding: 24px; }

/* Panel de fórmulas */
#PanelFormulas { background: $superficie_elevada; border-left: 1px solid $borde; }
#ScrollFormulas, #CuerpoFormulas { background: $superficie_elevada; border: none; }
QLabel#FormulaTitulo { font-size: 13pt; font-weight: 600; }
QLabel#FormulaResultado { font-size: 20pt; font-weight: 700; color: $primario_texto; }
QLabel#FormulaResultadoExtra { font-size: 12pt; font-weight: 600; color: $primario_texto; }
#CajaResultado { background: $resultado_fondo; border-radius: 10px; }
#CajaResultado QLabel { background: transparent; }
#CajaFormula { background: $formula_fondo; border: 1px solid $formula_borde; border-radius: 10px; }
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

QStatusBar { background: $barra; color: $texto_2; border-top: 1px solid $borde; }
QStatusBar QLabel { color: $texto_2; padding: 0 6px; }
QStatusBar QLabel[nivel="ok"] { color: $ok; font-weight: 600; }
QListWidget#IndiceGraficas, QTreeWidget#IndiceGraficas {
    background: $superficie_elevada; border: 1px solid $borde; border-radius: 10px; outline: 0; padding: 4px;
}
QTreeWidget#IndiceGraficas::item { padding: 4px 2px; }
QTreeWidget#IndiceGraficas::item:selected { background: $primario_tinte; color: $texto; }
""")


def hoja_estilo(nombre):
    return _QSS.substitute(PALETAS[nombre], fuente=FUENTE, tam=TAM_FUENTE)


def _paleta_qt(nombre):
    """QPalette coherente con la hoja de estilos (lo que QSS no cubre: flechas, casillas, menús)."""
    c = {k: QColor(v[:7]) for k, v in PALETAS[nombre].items()}
    p = QPalette()
    p.setColor(QPalette.Window, c["fondo"])
    p.setColor(QPalette.WindowText, c["texto"])
    p.setColor(QPalette.Base, c["tabla_fondo"])
    p.setColor(QPalette.AlternateBase, c["fila_alterna"])
    p.setColor(QPalette.Text, c["texto"])
    p.setColor(QPalette.Button, c["superficie_elevada"])
    p.setColor(QPalette.ButtonText, c["texto"])
    p.setColor(QPalette.Highlight, c["primario"])
    p.setColor(QPalette.HighlightedText, c["primario_sobre"])
    p.setColor(QPalette.Link, c["primario_texto"])
    p.setColor(QPalette.ToolTipBase, c["superficie_elevada"])
    p.setColor(QPalette.ToolTipText, c["texto"])
    p.setColor(QPalette.PlaceholderText, c["texto_3"])
    p.setColor(QPalette.Light, c["superficie_hover"])
    p.setColor(QPalette.Mid, c["borde_fuerte"])
    p.setColor(QPalette.Dark, c["borde_fuerte"])
    for rol in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, rol, c["texto_3"])
    return p


def aplicar(app: QApplication, nombre):
    """
    Aplica el tema a toda la aplicación en un solo paso: paleta + hoja de estilos, a nivel de
    QApplication (nunca widget por widget). El estilo Fusion y la fuente se fijan una sola vez:
    volver a ponerlos en cada cambio obligaba a Qt a repulir todos los widgets dos veces.
    Quien llama debe suspender el repintado de la ventana mientras dura (ver VentanaPrincipal).
    """
    global _actual
    _actual = nombre
    if app.property("tema_base") != "listo":
        app.setStyle("Fusion")
        app.setFont(QFont(FUENTE, TAM_FUENTE))
        app.setProperty("tema_base", "listo")
    app.setPalette(_paleta_qt(nombre))
    # Medido: reemplazar una hoja de estilos por otra cuesta ~4 veces más (≈930 ms con ~570
    # widgets) que vaciarla y aplicar la nueva (≈225 ms). Con el repintado suspendido por quien
    # llama, el paso intermedio sin estilos no llega a verse.
    if app.styleSheet():
        app.setStyleSheet("")
    app.setStyleSheet(hoja_estilo(nombre))


def refrescar(widget):
    """Vuelve a evaluar la hoja de estilos tras cambiar una propiedad dinámica."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
