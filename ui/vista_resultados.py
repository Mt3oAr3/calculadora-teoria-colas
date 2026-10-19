"""
vista_resultados.py
Pestañas de resultados detallados: «Resultados», «Probabilidades» y
«Por día y costos». Las tablas vienen armadas desde calculadora_service.
"""
import tkinter as tk
from tkinter import ttk

from domain.errores import ErrorEntrada
from services import calculadora_service as cs

from .componentes import VistaTabla


def _marco(nb, titulo):
    t = ttk.Frame(nb, padding=10)
    nb.add(t, text=titulo)
    return t


class VistaResultados:

    def __init__(self, notebook):
        self.esc = None
        self.fmt = None
        self.rango = (int(cs.VALORES_INICIALES["pa"]), int(cs.VALORES_INICIALES["pb"]))

        # --- Resultados ---
        t = _marco(notebook, "Resultados")
        ttk.Label(t, text="Las filas resaltadas son los indicadores principales; el resto son métricas "
                          "secundarias. «—» indica que la medida no está definida para el modelo.",
                  style="Nota.TLabel").pack(anchor="w", pady=(0, 6))
        self.tabla_res = VistaTabla(t, alto=18)
        self.tabla_res.pack(fill="both", expand=True)

        # --- Probabilidades ---
        t = _marco(notebook, "Probabilidades")
        top = ttk.Frame(t)
        top.pack(fill="x")
        ttk.Label(top, text="Número de clientes  a =").pack(side="left")
        self.v_a = tk.StringVar(value=cs.VALORES_INICIALES["pa"])
        self.v_b = tk.StringVar(value=cs.VALORES_INICIALES["pb"])
        self.ent_a = ttk.Entry(top, textvariable=self.v_a, width=6, justify="right")
        self.ent_a.pack(side="left", padx=4)
        ttk.Label(top, text="hasta  b =").pack(side="left", padx=(8, 0))
        self.ent_b = ttk.Entry(top, textvariable=self.v_b, width=6, justify="right")
        self.ent_b.pack(side="left", padx=4)
        self.btn_prob = ttk.Button(top, text="Calcular probabilidades", style="Chico.TButton",
                                   command=self.actualizar_probabilidades)
        self.btn_prob.pack(side="left", padx=10)
        for e in (self.ent_a, self.ent_b):
            e.bind("<Return>", lambda ev: self.actualizar_probabilidades())
        self.lbl_err_prob = ttk.Label(top, text="", foreground="#a52a21")
        self.lbl_err_prob.pack(side="left", padx=6)
        self.tabla_prob = VistaTabla(t, alto=10)
        self.tabla_prob.pack(fill="x", pady=(8, 10))
        ttk.Label(t, text="Distribución completa  (fila en negrita: n = k)", style="Seccion.TLabel").pack(anchor="w")
        self.tabla_dist = VistaTabla(t, alto=10)
        self.tabla_dist.pack(fill="both", expand=True, pady=(4, 0))

        # --- Por día y costos ---
        t = _marco(notebook, "Por día y costos")
        ttk.Label(t, text="Operación diaria", style="Seccion.TLabel").pack(anchor="w")
        ttk.Label(t, text="Tiempo en un estado = probabilidad × horas.   Clientes que esperan = "
                          "λ efectiva × horas × probabilidad de esperar.", style="Nota.TLabel").pack(anchor="w", pady=(0, 4))
        self.tabla_dia = VistaTabla(t, alto=11)
        self.tabla_dia.pack(fill="x")
        ttk.Label(t, text="Costos e ingresos", style="Seccion.TLabel").pack(anchor="w", pady=(12, 4))
        self.tabla_cost = VistaTabla(t, alto=7)
        self.tabla_cost.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def mostrar(self, esc, fmt):
        self.esc, self.fmt = esc, fmt
        self.tabla_res.mostrar(cs.tabla_resultados(esc), fmt)
        self.tabla_dia.mostrar(cs.tabla_por_dia(esc), fmt)
        self.tabla_cost.mostrar(cs.tabla_costos(esc), fmt)
        self.tabla_dist.mostrar(cs.tabla_distribucion(esc), fmt)
        self.actualizar_probabilidades()

    def actualizar_probabilidades(self):
        if self.esc is None:
            return
        self.ent_a.configure(style="TEntry")
        self.ent_b.configure(style="TEntry")
        try:
            self.rango = cs.leer_rango(self.v_a.get(), self.v_b.get())
        except ErrorEntrada as e:
            for campo, _ in e.errores:
                (self.ent_a if campo == "pa" else self.ent_b).configure(style="Error.TEntry")
            self.lbl_err_prob.configure(text=e.errores[0][1])
            self.tabla_prob.limpiar("Corrige el rango a – b para ver estas probabilidades.")
            return
        self.lbl_err_prob.configure(text="")
        self.tabla_prob.mostrar(cs.tabla_probabilidades(self.esc, *self.rango), self.fmt)

    def tablas_para_exportar(self):
        """Tablas en el orden de exportación original: Resultados, Probabilidades, Por día, Costos."""
        esc = self.esc
        return [cs.tabla_resultados(esc), cs.tabla_probabilidades(esc, *self.rango),
                cs.tabla_por_dia(esc), cs.tabla_costos(esc)]

    def limpiar(self, mensaje):
        self.esc = None
        for t in (self.tabla_res, self.tabla_prob, self.tabla_dist, self.tabla_dia, self.tabla_cost):
            t.limpiar(mensaje)
