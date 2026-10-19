"""
panel_resumen.py
Encabezado con el modelo (notación de Kendall), insignia de estado, mensaje
de estabilidad y tarjetas con los indicadores principales.
"""
from tkinter import ttk

from services import calculadora_service as cs

from .componentes import TarjetaIndicador

COLUMNAS_TARJETAS = 4
TEXTO_INSIGNIA = {"ok": "● Estable", "aviso": "● Inestable", "error": "● Sin resultados",
                  "info": "● Desactualizado"}


class PanelResumen(ttk.Frame):

    def __init__(self, padre):
        super().__init__(padre, padding=(4, 10, 0, 6))
        cab = ttk.Frame(self)
        cab.pack(fill="x")
        self.lbl_modelo = ttk.Label(cab, text="—", style="Modelo.TLabel")
        self.lbl_modelo.pack(side="left")
        self.lbl_desc = ttk.Label(cab, text="", style="Descripcion.TLabel")
        self.lbl_desc.pack(side="left", padx=14, pady=(8, 0))
        self.insignia = ttk.Label(cab, text="", style="Insignia.info.TLabel")
        self.insignia.pack(side="right", pady=(6, 0))

        self.mensaje = ttk.Label(self, text="", style="Mensaje.info.TLabel", wraplength=900, justify="left")
        self.mensaje.pack(fill="x", pady=(8, 8))
        self.bind("<Configure>", lambda e: self.mensaje.configure(wraplength=max(300, e.width - 30)))

        self.zona_tarjetas = ttk.Frame(self)
        self.zona_tarjetas.pack(fill="x")
        for c in range(COLUMNAS_TARJETAS):
            self.zona_tarjetas.columnconfigure(c, weight=1, uniform="tarjetas")
        self.tarjetas = []
        self._nivel = "info"

    def _tarjetas(self, n):
        while len(self.tarjetas) < n:
            i = len(self.tarjetas)
            t = TarjetaIndicador(self.zona_tarjetas)
            t.grid(row=i // COLUMNAS_TARJETAS, column=i % COLUMNAS_TARJETAS, sticky="ew", padx=(0, 8), pady=(0, 8))
            self.tarjetas.append(t)
        # Un frame de Tk no se encoge al quitarle todos los hijos: se oculta entero.
        if n == 0:
            self.zona_tarjetas.pack_forget()
        elif not self.zona_tarjetas.winfo_manager():
            self.zona_tarjetas.pack(fill="x")
        for i, t in enumerate(self.tarjetas):
            if i < n:
                t.grid()
            else:
                t.grid_remove()
        return self.tarjetas[:n]

    def _estado(self, nivel, mensaje):
        self._nivel = nivel
        self.insignia.configure(text=TEXTO_INSIGNIA[nivel], style=f"Insignia.{nivel}.TLabel")
        self.mensaje.configure(text=mensaje, style=f"Mensaje.{nivel}.TLabel")

    def mostrar(self, esc, fmt):
        self.lbl_modelo.configure(text=esc.kendall)
        self.lbl_desc.configure(text=esc.descripcion)
        self._estado("ok" if esc.estable else "aviso", cs.mensaje_estado(esc, fmt))
        indicadores = cs.indicadores_principales(esc)
        for tarjeta, ind in zip(self._tarjetas(len(indicadores)), indicadores):
            tarjeta.mostrar(ind.simbolo, ind.nombre, fmt.texto(ind.valor))

    def limpiar(self, mensaje):
        """Sin resultados vigentes (error de entrada, de modelo o inesperado)."""
        self.lbl_modelo.configure(text="—")
        self.lbl_desc.configure(text="")
        self._estado("error", mensaje)
        self._tarjetas(0)

    def marcar_desactualizado(self, desactualizado, mensaje_vigente=None):
        """Atenúa los valores y avisa que los parámetros cambiaron desde el último cálculo."""
        for t in self.tarjetas:
            t.marcar_vigente(not desactualizado)
        if desactualizado:
            self._estado("info", "Los parámetros cambiaron desde el último cálculo: los valores mostrados "
                                 "corresponden a los datos anteriores. Pulsa «Calcular» para actualizarlos.")
        elif mensaje_vigente is not None:
            self._estado(*mensaje_vigente)
