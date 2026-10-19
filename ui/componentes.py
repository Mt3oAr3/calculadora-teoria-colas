"""
componentes.py
Widgets reutilizables: panel con desplazamiento, tabla que dibuja una
services.tablas.Tabla y tarjeta de indicador.
"""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from . import estilos as es


class PanelDesplazable(ttk.Frame):
    """Frame con barra de desplazamiento vertical. Los hijos van en `self.interior`."""

    def __init__(self, padre, ancho=360, estilo_interior="TFrame"):
        super().__init__(padre)
        self.canvas = tk.Canvas(self, width=ancho, highlightthickness=0, background=es.FONDO)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = ttk.Frame(self.canvas, style=estilo_interior, padding=(10, 10, 6, 10))
        self._ventana = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>",
                           lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        # El interior ocupa todo el ancho visible
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._ventana, width=e.width))
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.barra.pack(side="right", fill="y")
        # La rueda del ratón solo desplaza este panel cuando el puntero está encima
        self.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._rueda))
        self.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _rueda(self, e):
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def mostrar_widget(self, widget):
        """Desplaza el panel para que `widget` quede visible."""
        self.update_idletasks()
        alto_total = max(1, self.interior.winfo_height())
        y = widget.winfo_rooty() - self.interior.winfo_rooty()
        self.canvas.yview_moveto(max(0.0, (y - 40) / alto_total))


class VistaTabla(ttk.Frame):
    """
    Treeview que se llena con una Tabla (services.tablas). Ajusta el ancho de
    columnas al contenido, alinea números a la derecha y muestra un mensaje
    cuando no hay filas.
    """
    ANCHO_MIN, ANCHO_MAX_NUM, ANCHO_MAX_TEXTO = 56, 170, 460

    def __init__(self, padre, alto=10):
        super().__init__(padre)
        self.tv = ttk.Treeview(self, show="headings", height=alto, selectmode="browse")
        sy = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        sx = ttk.Scrollbar(self, orient="horizontal", command=self.tv.xview)
        self.tv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tv.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        # Prioridad de color: el último tag configurado gana
        self.tv.tag_configure("par", background=es.FILA_PAR)
        self.tv.tag_configure("principal", background=es.FILA_PRINCIPAL, font=es.fuente(10, "bold"))
        self.tv.tag_configure("ok", background=es.FILA_CUMPLE)
        self.tv.tag_configure("mejor", background=es.FILA_MEJOR)
        self.tv.tag_configure("actual", font=es.fuente(10, "bold"))
        self._f_celda = tkfont.Font(font=es.fuente(10, "bold"))
        self._f_titulo = tkfont.Font(font=es.fuente(9, "bold"))
        self.mensaje = ttk.Label(self, text="", style="Nota.TLabel", background=es.SUPERFICIE,
                                 justify="center", wraplength=520)

    def mostrar(self, tabla, fmt):
        textos = tabla.textos(fmt)
        ids = [f"c{i}" for i in range(len(tabla.columnas))]
        self.tv.delete(*self.tv.get_children())
        self.tv.configure(columns=ids)
        for i, (cid, col) in enumerate(zip(ids, tabla.columnas)):
            contenido = [fila[i] for fila in textos]
            ancho = max([self._f_titulo.measure(col.titulo) + 34]
                        + [self._f_celda.measure(t) + 18 for t in contenido[:400]])
            tope = self.ANCHO_MAX_NUM if col.numerica else self.ANCHO_MAX_TEXTO
            ancho = max(self.ANCHO_MIN, min(ancho, tope))
            self.tv.heading(cid, text=col.titulo, anchor="e" if col.numerica else "w")
            self.tv.column(cid, width=ancho, minwidth=self.ANCHO_MIN,
                           anchor="e" if col.numerica else "w", stretch=not col.numerica)
        for n, (fila, txt) in enumerate(zip(tabla.filas, textos)):
            tags = (("par",) if n % 2 else ()) + tuple(fila.etiquetas)
            self.tv.insert("", "end", values=txt, tags=tags)
        if textos:
            self.mensaje.place_forget()
        else:
            self._mostrar_mensaje(tabla.mensaje_vacio or "Sin datos.")

    def limpiar(self, mensaje=""):
        self.tv.delete(*self.tv.get_children())
        if mensaje:
            self._mostrar_mensaje(mensaje)
        else:
            self.mensaje.place_forget()

    def _mostrar_mensaje(self, texto):
        self.mensaje.configure(text=texto)
        self.mensaje.place(relx=0.5, rely=0.45, anchor="center")


class TarjetaIndicador(ttk.Frame):
    """Tarjeta con nombre, símbolo y valor grande de un indicador principal."""

    def __init__(self, padre):
        super().__init__(padre, style="Tarjeta.TFrame", padding=(12, 8))
        arriba = ttk.Frame(self, style="Superficie.TFrame")
        arriba.pack(fill="x")
        self.nombre = ttk.Label(arriba, style="TarjetaNombre.TLabel")
        self.nombre.pack(side="left")
        self.simbolo = ttk.Label(arriba, style="TarjetaSimbolo.TLabel")
        self.simbolo.pack(side="right")
        self.valor = ttk.Label(self, style="TarjetaValor.TLabel")
        self.valor.pack(anchor="w", pady=(2, 0))

    def mostrar(self, simbolo, nombre, texto, vigente=True):
        self.simbolo.configure(text=simbolo)
        self.nombre.configure(text=nombre)
        self.valor.configure(text=texto, style="TarjetaValor.TLabel" if vigente else "TarjetaValorViejo.TLabel")

    def marcar_vigente(self, vigente):
        self.valor.configure(style="TarjetaValor.TLabel" if vigente else "TarjetaValorViejo.TLabel")
