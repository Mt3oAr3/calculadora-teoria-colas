"""
estilos.py
Paleta, tipografías y estilos ttk de toda la aplicación, en un solo lugar.
Diseño sobrio: fondo gris claro, superficies blancas, un color de acento y
colores de estado reservados (correcto / aviso / error).
"""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

FONDO = "#f3f4f6"
SUPERFICIE = "#ffffff"
BORDE = "#d6d9df"
TINTA = "#1f2430"
TINTA_2 = "#4f5665"
TINTA_3 = "#8a909c"
ACENTO = "#2a5fb0"
ACENTO_ACTIVO = "#214d91"
DESHABILITADO = "#b9bec8"

# Estados: (texto, fondo)
ESTADOS = {
    "ok": ("#1b6e47", "#e2f2e9"),
    "aviso": ("#7a5200", "#fff2d1"),
    "error": ("#a52a21", "#fbe6e4"),
    "info": ("#4f5665", "#eceef2"),
}
FILA_CUMPLE = "#dcf0e5"
FILA_MEJOR = "#ffefc2"
FILA_PRINCIPAL = "#eef3fb"
FILA_PAR = "#fafbfc"
ENTRADA_ERROR = "#fdeceb"

FAMILIA = "Segoe UI"
MONO = "Consolas"


def fuente(tam=10, peso="normal"):
    return (FAMILIA, tam, peso)


def aplicar(raiz):
    """Configura el tema ttk. Llamar una vez al crear la ventana principal."""
    raiz.configure(background=FONDO)
    estilo = ttk.Style(raiz)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
    base = tkfont.nametofont("TkDefaultFont")
    base.configure(family=FAMILIA, size=10)
    for nombre in ("TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(nombre).configure(family=FAMILIA, size=10)
        except tk.TclError:
            pass

    estilo.configure(".", background=FONDO, foreground=TINTA, font=fuente(10), bordercolor=BORDE)
    estilo.configure("TFrame", background=FONDO)
    estilo.configure("Superficie.TFrame", background=SUPERFICIE)
    estilo.configure("TLabel", background=FONDO, foreground=TINTA)
    estilo.configure("Superficie.TLabel", background=SUPERFICIE)
    estilo.configure("TSeparator", background=BORDE)

    # Grupos del formulario
    estilo.configure("Campo.TLabel", background=SUPERFICIE, foreground=TINTA)
    estilo.configure("Unidad.TLabel", background=SUPERFICIE, foreground=TINTA_2, font=fuente(9))
    estilo.configure("Ayuda.TLabel", background=SUPERFICIE, foreground=TINTA_3, font=fuente(8))
    estilo.configure("Previa.TLabel", background=SUPERFICIE, foreground=TINTA_2, font=fuente(9))
    estilo.configure("Subgrupo.TLabel", background=SUPERFICIE, foreground=TINTA, font=fuente(9, "bold"))
    estilo.configure("ErrorCampo.TLabel", background=SUPERFICIE, foreground=ESTADOS["error"][0],
                     font=fuente(8))
    estilo.map("Campo.TLabel", foreground=[("disabled", DESHABILITADO)], background=[("disabled", SUPERFICIE)])
    estilo.configure("GrupoTitulo.TLabel", background=FONDO, foreground=ACENTO, font=fuente(10, "bold"))
    estilo.configure("GrupoCuerpo.TFrame", background=SUPERFICIE, bordercolor=BORDE, relief="solid",
                     borderwidth=1)
    estilo.configure("TRadiobutton", background=SUPERFICIE)
    estilo.configure("TCheckbutton", background=FONDO)

    estilo.configure("TEntry", padding=(4, 2), fieldbackground=SUPERFICIE)
    estilo.map("TEntry", fieldbackground=[("disabled", FONDO)], foreground=[("disabled", TINTA_3)])
    estilo.configure("Error.TEntry", fieldbackground=ENTRADA_ERROR, bordercolor=ESTADOS["error"][0],
                     lightcolor=ESTADOS["error"][0], darkcolor=ESTADOS["error"][0])
    estilo.configure("TCombobox", padding=(4, 2))
    estilo.map("TCombobox", fieldbackground=[("readonly", SUPERFICIE), ("disabled", FONDO)],
               foreground=[("disabled", TINTA_3)])

    # Botones
    estilo.configure("TButton", padding=(10, 4))
    estilo.configure("Accion.TButton", background=ACENTO, foreground="#ffffff", bordercolor=ACENTO,
                     font=fuente(10, "bold"), padding=(12, 6))
    estilo.map("Accion.TButton", background=[("disabled", DESHABILITADO), ("active", ACENTO_ACTIVO)],
               foreground=[("disabled", "#f5f5f5")])
    estilo.configure("Secundario.TButton", padding=(10, 6))
    estilo.configure("Chico.TButton", padding=(8, 2))

    # Encabezado y resumen
    estilo.configure("Modelo.TLabel", font=fuente(20, "bold"), foreground=TINTA)
    estilo.configure("Descripcion.TLabel", font=fuente(10), foreground=TINTA_2)
    for nivel, (texto, fondo) in ESTADOS.items():
        estilo.configure(f"Insignia.{nivel}.TLabel", background=fondo, foreground=texto,
                         font=fuente(9, "bold"), padding=(10, 3))
        estilo.configure(f"Mensaje.{nivel}.TLabel", background=fondo, foreground=texto,
                         font=fuente(10), padding=(10, 6))
    estilo.configure("Tarjeta.TFrame", background=SUPERFICIE, bordercolor=BORDE, relief="solid", borderwidth=1)
    estilo.configure("TarjetaNombre.TLabel", background=SUPERFICIE, foreground=TINTA_2, font=fuente(9))
    estilo.configure("TarjetaValor.TLabel", background=SUPERFICIE, foreground=TINTA, font=fuente(16, "bold"))
    estilo.configure("TarjetaValorViejo.TLabel", background=SUPERFICIE, foreground=TINTA_3, font=fuente(16, "bold"))
    estilo.configure("TarjetaSimbolo.TLabel", background=SUPERFICIE, foreground=ACENTO, font=fuente(9, "bold"))
    estilo.configure("Seccion.TLabel", font=fuente(10, "bold"), foreground=TINTA)
    estilo.configure("Nota.TLabel", font=fuente(9), foreground=TINTA_2)
    estilo.configure("Barra.TLabel", font=fuente(9), foreground=TINTA_2, padding=(12, 3))

    # Pestañas y tablas
    estilo.configure("TNotebook", background=FONDO, borderwidth=0)
    estilo.configure("TNotebook.Tab", padding=(14, 6), font=fuente(10))
    estilo.map("TNotebook.Tab", background=[("selected", SUPERFICIE)], foreground=[("selected", ACENTO)])
    estilo.configure("Treeview", rowheight=24, background=SUPERFICIE, fieldbackground=SUPERFICIE,
                     font=fuente(10), bordercolor=BORDE)
    estilo.configure("Treeview.Heading", font=fuente(9, "bold"), background="#e9ecf1", foreground=TINTA,
                     padding=(6, 4))
    estilo.map("Treeview", background=[("selected", "#cfdcf2")], foreground=[("selected", TINTA)])
    estilo.configure("Leyenda.TLabel", font=fuente(9), foreground=TINTA_2, padding=(6, 1))
    return estilo
