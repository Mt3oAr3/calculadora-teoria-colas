"""
app.py
Ventana principal de la Calculadora de Teoría de Colas (Tkinter + matplotlib).

Coordina el flujo:
    PanelEntradas --(texto)--> calculadora_service.leer_parametros()
                  --> calculadora_service.calcular_escenario()
                  --> PanelResumen, VistaResultados, VistaComparacion, VistaGraficas

Distingue tres tipos de fallo:
    ErrorEntrada  -> se marcan los campos en el formulario.
    ErrorModelo   -> limitación matemática / numérica, se explica en el resumen.
    otro          -> error inesperado: mensaje breve al usuario y traza en consola.
En cualquier fallo se retiran los resultados anteriores para no confundirlos.
"""
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")

from domain.errores import ErrorEntrada, ErrorModelo  # noqa: E402
from services import calculadora_service as cs  # noqa: E402
from services import exportacion_service as ex  # noqa: E402
from services.tablas import Formateador  # noqa: E402

from . import estilos  # noqa: E402
from .panel_entradas import PanelEntradas  # noqa: E402
from .panel_resumen import PanelResumen  # noqa: E402
from .vista_comparacion import VistaComparacion  # noqa: E402
from .vista_graficas import VistaGraficas  # noqa: E402
from .vista_resultados import VistaResultados  # noqa: E402

TITULO = "Calculadora de Teoría de Colas - Técnicas de Simulación"


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(TITULO)
        self.geometry("1380x840")
        self.minsize(1100, 680)
        estilos.aplicar(self)
        self.esc = None                  # escenario vigente (None si no hay resultados válidos)
        self.desactualizado = False      # True si se editaron datos después de calcular
        self._construir()
        self.bind("<F5>", lambda e: self.calcular())
        self.calcular()

    # ------------------------------------------------------------------
    def _construir(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.panel = PanelEntradas(self, al_calcular=self.calcular, al_exportar=self.exportar_csv,
                                   al_cambiar_datos=self._datos_cambiaron,
                                   al_cambiar_presentacion=self._presentacion_cambio)
        self.panel.grid(row=0, column=0, sticky="ns")
        ttk.Separator(self, orient="vertical").grid(row=0, column=0, sticky="nse")

        der = ttk.Frame(self, padding=(14, 0, 14, 8))
        der.grid(row=0, column=1, sticky="nsew")
        self.resumen = PanelResumen(der)
        self.resumen.pack(fill="x")
        self.nb = ttk.Notebook(der)
        self.nb.pack(fill="both", expand=True)
        self.resultados = VistaResultados(self.nb)
        self.comparacion = VistaComparacion(self.nb, unidad_tiempo=lambda: self.panel.get("ut"))
        self.graficas = VistaGraficas(self.nb, avisar=self.avisar)

        self.barra = ttk.Label(self, text="Listo.", style="Barra.TLabel", anchor="w")
        self.barra.grid(row=1, column=0, columnspan=2, sticky="ew")

    def avisar(self, texto):
        self.barra.configure(text=texto)

    def _formateador(self):
        H = self.esc.p.H if self.esc else 8.0
        return Formateador(int(self.panel.get("dec")), self.panel.get("ut"), H)

    # ------------------------------------------------------------------
    # Cálculo
    # ------------------------------------------------------------------
    def calcular(self):
        self.panel.limpiar_errores()
        try:
            p = cs.leer_parametros(self.panel.valores())
        except ErrorEntrada as e:
            self.panel.marcar_errores(e.errores)
            n = len(e.errores)
            detalle = e.errores[0][1] + (f"  (y {n - 1} error(es) más)" if n > 1 else "")
            self._sin_resultados(f"Revisa los datos marcados en rojo en el panel de parámetros. {detalle}")
            return
        try:
            esc = cs.calcular_escenario(p)
        except ErrorModelo as e:
            self._sin_resultados(f"Limitación del modelo: {e}")
            return
        except Exception as e:  # error del programa: no mostrar resultados dudosos
            traceback.print_exc()
            self._sin_resultados("Ocurrió un error inesperado al calcular. No se muestran resultados.")
            messagebox.showerror("Error inesperado",
                                 "Ocurrió un error inesperado al calcular.\n\n"
                                 f"Detalle técnico: {type(e).__name__}: {e}")
            return
        self.esc = esc
        self.desactualizado = False
        self._mostrar()
        self.avisar(f"Calculado {esc.kendall}." + ("" if esc.estable else " Sistema inestable."))

    def _mostrar(self):
        """Dibuja el escenario vigente en todas las vistas con la presentación elegida."""
        fmt = self._formateador()
        try:
            self.resumen.mostrar(self.esc, fmt)
            self.resultados.mostrar(self.esc, fmt)
            self.comparacion.mostrar(self.esc, fmt)
            self.graficas.mostrar(cs.contexto_graficas(self.esc, self.panel.get("ut")))
        except Exception as e:
            traceback.print_exc()
            self._sin_resultados("Ocurrió un error inesperado al mostrar los resultados.")
            messagebox.showerror("Error inesperado", f"Detalle técnico: {type(e).__name__}: {e}")
            return
        if self.desactualizado:
            self.resumen.marcar_desactualizado(True)
        self.panel.habilitar_exportar(not self.desactualizado)

    def _sin_resultados(self, mensaje):
        """Retira todos los resultados anteriores para que no se confundan con los actuales."""
        self.esc = None
        self.desactualizado = False
        self.resumen.limpiar(mensaje)
        self.resultados.limpiar("Sin resultados. Corrige los datos y pulsa «Calcular».")
        self.comparacion.limpiar("Sin resultados.")
        self.graficas.limpiar("Sin resultados para graficar.")
        self.panel.habilitar_exportar(False)
        self.avisar("Sin resultados vigentes.")

    def _datos_cambiaron(self):
        if self.esc is not None and not self.desactualizado:
            self.desactualizado = True
            self.resumen.marcar_desactualizado(True)
            self.panel.habilitar_exportar(False)
            self.avisar("Parámetros modificados: pulsa «Calcular» (Enter o F5) para actualizar.")

    def _presentacion_cambio(self):
        if self.esc is not None:
            self._mostrar()

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------
    def exportar_csv(self):
        if self.esc is None or self.desactualizado:
            return
        try:
            tablas = self.resultados.tablas_para_exportar() + self.comparacion.tablas_para_exportar()
        except ErrorEntrada as e:
            messagebox.showwarning("No se puede exportar", e.errores[0][1])
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="resultados_colas.csv")
        if not ruta:
            return
        try:
            ex.exportar_csv(ruta, tablas, self._formateador())
        except OSError as e:
            messagebox.showerror("No se pudo guardar",
                                 f"No se pudo escribir el archivo (¿está abierto en Excel?).\n\n{e.strerror or e}")
            return
        self.avisar(f"Tablas exportadas a {ruta}")
        messagebox.showinfo("Exportado", f"Tablas guardadas en:\n{ruta}")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
