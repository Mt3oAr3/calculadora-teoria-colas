"""
vista_comparacion.py
Pestaña «Comparar k y M»: condición de búsqueda, leyenda de colores y las
tablas en función de k y de M (calculadas en comparacion_service).
"""
import tkinter as tk
from tkinter import ttk

from domain.errores import ErrorEntrada
from services import comparacion_service as cmp

from . import estilos as es
from .componentes import VistaTabla


class VistaComparacion:

    def __init__(self, notebook, unidad_tiempo):
        self.esc = None
        self.fmt = None
        self._unidad_tiempo = unidad_tiempo      # función que devuelve la unidad elegida
        self.res_k = self.res_M = None

        t = ttk.Frame(notebook, padding=10)
        notebook.add(t, text="Comparar k y M")

        top = ttk.Frame(t)
        top.pack(fill="x")
        ttk.Label(top, text="Condición:").pack(side="left")
        self.v_metrica = tk.StringVar(value=cmp.METRICA_INICIAL)
        self.v_op = tk.StringVar(value="≤")
        self.v_lim = tk.StringVar(value="0.5")
        cb = ttk.Combobox(top, textvariable=self.v_metrica, values=[m.nombre for m in cmp.METRICAS],
                          state="readonly", width=34)
        cb.pack(side="left", padx=4)
        ttk.Combobox(top, textvariable=self.v_op, values=cmp.OPERADORES, state="readonly",
                     width=3).pack(side="left", padx=4)
        self.ent_lim = ttk.Entry(top, textvariable=self.v_lim, width=10, justify="right")
        self.ent_lim.pack(side="left", padx=4)
        self.lbl_unidad = ttk.Label(top, text="", style="Nota.TLabel", width=5)
        self.lbl_unidad.pack(side="left")
        ttk.Button(top, text="Buscar", style="Chico.TButton", command=self.actualizar).pack(side="left", padx=6)
        self.ent_lim.bind("<Return>", lambda e: self.actualizar())
        cb.bind("<<ComboboxSelected>>", lambda e: self.actualizar())
        self.v_op.trace_add("write", lambda *a: self.actualizar())
        self.lbl_err = ttk.Label(top, text="", foreground=es.ESTADOS["error"][0])
        self.lbl_err.pack(side="left", padx=6)

        leyenda = ttk.Frame(t)
        leyenda.pack(fill="x", pady=(6, 0))
        for texto, color in (("Cumple la condición", es.FILA_CUMPLE), ("Menor costo total", es.FILA_MEJOR)):
            tk.Label(leyenda, text="   ", background=color, relief="flat").pack(side="left", padx=(0, 4))
            ttk.Label(leyenda, text=texto, style="Leyenda.TLabel").pack(side="left", padx=(0, 12))
        ttk.Label(leyenda, text="Negrita: valor actual.   Los tiempos usan la unidad de «Mostrar tiempos en».",
                  style="Leyenda.TLabel").pack(side="left")

        paneles = ttk.PanedWindow(t, orient="vertical")
        paneles.pack(fill="both", expand=True, pady=(8, 0))
        arriba, abajo = ttk.Frame(paneles), ttk.Frame(paneles)
        paneles.add(arriba, weight=1)
        paneles.add(abajo, weight=1)
        self.lbl_k = ttk.Label(arriba, text="", style="Seccion.TLabel", wraplength=900, justify="left")
        self.lbl_k.pack(anchor="w", pady=(0, 4))
        self.tabla_k = VistaTabla(arriba, alto=7)
        self.tabla_k.pack(fill="both", expand=True)
        self.lbl_M = ttk.Label(abajo, text="", style="Seccion.TLabel", wraplength=900, justify="left")
        self.lbl_M.pack(anchor="w", pady=(10, 4))
        self.tabla_M = VistaTabla(abajo, alto=7)
        self.tabla_M.pack(fill="both", expand=True)

    def mostrar(self, esc, fmt):
        self.esc, self.fmt = esc, fmt
        self.actualizar()

    def actualizar(self):
        if self.esc is None:
            return
        try:
            cond = cmp.leer_condicion(self.v_metrica.get(), self.v_op.get(), self.v_lim.get(),
                                      self._unidad_tiempo())
        except ErrorEntrada as e:
            self.ent_lim.configure(style="Error.TEntry")
            self.lbl_err.configure(text=e.errores[0][1])
            self.res_k = self.res_M = None
            self.lbl_k.configure(text="")
            self.lbl_M.configure(text="")
            self.tabla_k.limpiar("Corrige la condición para ver la comparación.")
            self.tabla_M.limpiar("")
            return
        self.ent_lim.configure(style="TEntry")
        self.lbl_err.configure(text="")
        self.lbl_unidad.configure(text=self.fmt.abrev_tiempo if cond.metrica.es_tiempo else "")
        self.res_k = cmp.comparar_k(self.esc, cond, self.fmt)
        self.res_M = cmp.comparar_M(self.esc, cond, self.fmt)
        self.lbl_k.configure(text="En función de k:  " + self.res_k.resumen)
        self.tabla_k.mostrar(self.res_k.tabla, self.fmt)
        self.lbl_M.configure(text="En función de M:  " + self.res_M.resumen)
        self.tabla_M.mostrar(self.res_M.tabla, self.fmt)

    def tablas_para_exportar(self):
        """Tablas «Variando k» y «Variando M». Lanza ErrorEntrada si la condición no es válida."""
        if self.res_k is None:
            raise ErrorEntrada([("cond_v", "La condición de comparación no es válida; corrígela antes de exportar.")])
        return [self.res_k.tabla, self.res_M.tabla]

    def limpiar(self, mensaje):
        self.esc = None
        self.res_k = self.res_M = None
        self.lbl_k.configure(text="")
        self.lbl_M.configure(text="")
        self.tabla_k.limpiar(mensaje)
        self.tabla_M.limpiar("")
