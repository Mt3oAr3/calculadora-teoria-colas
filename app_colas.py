"""
app_colas.py
Calculadora de Teoría de Colas con interfaz gráfica (Tkinter + matplotlib).

Ejecutar:  python app_colas.py
Requiere:  pip install matplotlib
"""
import csv
import math
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import modelos_colas as mc
import graficas_colas as gc

MODO_LAM = ["Tasa (clientes por unidad)", "Tiempo entre llegadas"]
MODO_MU = ["Tasa (clientes por unidad)", "Tiempo medio de servicio"]
ABREV = {"minuto": "min", "hora": "h", "día": "día"}


class PanelDesplazable(ttk.Frame):
    """Frame con barra de desplazamiento vertical para el panel de datos."""

    def __init__(self, padre, ancho=370):
        super().__init__(padre)
        self.canvas = tk.Canvas(self, width=ancho, highlightthickness=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = ttk.Frame(self.canvas, padding=10)
        self.interior.bind("<Configure>",
                           lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.canvas.configure(yscrollcommand=barra.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._rueda)

    def _rueda(self, e):
        if str(e.widget).startswith(str(self.canvas)):
            self.canvas.yview_scroll(int(-e.delta / 120), "units")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calculadora de Teoría de Colas - Técnicas de Simulación")
        self.geometry("1360x820")
        self.minsize(1000, 640)
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 20, "bold"))
        estilo.configure("Sub.TLabel", foreground="#556275")
        estilo.configure("Seccion.TLabel", font=("Segoe UI", 10, "bold"))
        estilo.configure("Estado.TLabel", font=("Segoe UI", 10))
        estilo.configure("Treeview", rowheight=24)
        estilo.configure("TButton", padding=(8, 3))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        self.v = {}               # variables de entrada
        self.r = None             # resultado actual
        self.barrido_k = []
        self.barrido_M = []
        self._construir()
        self.calcular()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _var(self, nombre, valor):
        self.v[nombre] = tk.StringVar(value=str(valor))
        return self.v[nombre]

    def _campo(self, padre, fila, texto, nombre, valor, ancho=12):
        ttk.Label(padre, text=texto).grid(row=fila, column=0, sticky="w", pady=2)
        e = ttk.Entry(padre, textvariable=self._var(nombre, valor), width=ancho)
        e.grid(row=fila, column=1, sticky="ew", pady=2)
        e.bind("<Return>", lambda ev: self.calcular())
        return e

    def _combo(self, padre, fila, texto, nombre, opciones, valor, ancho=20):
        ttk.Label(padre, text=texto).grid(row=fila, column=0, sticky="w", pady=2)
        c = ttk.Combobox(padre, textvariable=self._var(nombre, valor), values=opciones,
                         state="readonly", width=ancho)
        c.grid(row=fila, column=1, sticky="ew", pady=2)
        return c

    def _construir(self):
        # Encabezado
        cab = ttk.Frame(self, padding=(14, 10, 14, 4))
        cab.pack(fill="x")
        self.lbl_modelo = ttk.Label(cab, text="M/M/1", style="Titulo.TLabel")
        self.lbl_modelo.pack(side="left")
        self.lbl_desc = ttk.Label(cab, text="", style="Sub.TLabel")
        self.lbl_desc.pack(side="left", padx=14, pady=(8, 0))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)

        # ---------------- Panel de datos ----------------
        panel = PanelDesplazable(cuerpo)
        panel.pack(side="left", fill="y")
        f = panel.interior
        f.columnconfigure(1, weight=1)
        fila = 0

        ttk.Label(f, text="Modelo", style="Seccion.TLabel").grid(row=fila, column=0, sticky="w")
        fila += 1
        self._combo(f, fila, "Población", "poblacion", ["Infinita", "Finita"], "Infinita"); fila += 1
        self._campo(f, fila, "Servidores k", "k", 1); fila += 1
        self.ent_M = self._campo(f, fila, "Población M", "M", 4); fila += 1

        ttk.Separator(f).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=8); fila += 1
        ttk.Label(f, text="Llegadas λ", style="Seccion.TLabel").grid(row=fila, column=0, sticky="w"); fila += 1
        self._combo(f, fila, "Dato", "lam_modo", MODO_LAM, MODO_LAM[0]); fila += 1
        self._combo(f, fila, "Unidad", "lam_u", mc.UNIDADES, "hora"); fila += 1
        self._campo(f, fila, "Valor", "lam", 10); fila += 1
        self.lbl_lam = ttk.Label(f, text="", style="Sub.TLabel")
        self.lbl_lam.grid(row=fila, column=0, columnspan=2, sticky="w"); fila += 1

        ttk.Label(f, text="Servicio μ (por servidor)", style="Seccion.TLabel").grid(row=fila, column=0, columnspan=2, sticky="w", pady=(6, 0)); fila += 1
        self._combo(f, fila, "Dato", "mu_modo", MODO_MU, MODO_MU[1]); fila += 1
        self._combo(f, fila, "Unidad", "mu_u", mc.UNIDADES, "minuto"); fila += 1
        self._campo(f, fila, "Valor", "mu", 4); fila += 1
        self.lbl_mu = ttk.Label(f, text="", style="Sub.TLabel")
        self.lbl_mu.grid(row=fila, column=0, columnspan=2, sticky="w"); fila += 1

        ttk.Separator(f).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=8); fila += 1
        ttk.Label(f, text="Operación", style="Seccion.TLabel").grid(row=fila, column=0, sticky="w"); fila += 1
        self._campo(f, fila, "Horas por día", "H", 12); fila += 1
        self._campo(f, fila, "Días por semana", "D", 7); fila += 1
        self._combo(f, fila, "Mostrar tiempos en", "ut", mc.UNIDADES, "minuto"); fila += 1
        self._combo(f, fila, "Decimales", "dec", ["2", "3", "4", "6"], "4"); fila += 1

        ttk.Separator(f).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=8); fila += 1
        ttk.Label(f, text="Costos e ingresos", style="Seccion.TLabel").grid(row=fila, column=0, sticky="w"); fila += 1
        self._campo(f, fila, "Costo por servidor", "cS", 0); fila += 1
        self._combo(f, fila, "   por", "cS_u", ["hora", "día"], "día"); fila += 1
        self._campo(f, fila, "Costo de espera", "cW", 0); fila += 1
        self._combo(f, fila, "   por", "cW_u", mc.UNIDADES, "hora"); fila += 1
        self._combo(f, fila, "Se cobra", "cW_b",
                    ["Lq (solo espera en cola)", "L (espera + servicio)"], "Lq (solo espera en cola)"); fila += 1
        self._campo(f, fila, "Costo/hora servidor ocioso", "cI", 0); fila += 1
        self._campo(f, fila, "Ingreso por cliente", "ing", 0); fila += 1
        self._campo(f, fila, "Fracción con ingreso", "ingF", 1); fila += 1

        ttk.Separator(f).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=8); fila += 1
        ttk.Label(f, text="Rango de gráficas y tablas", style="Seccion.TLabel").grid(row=fila, column=0, columnspan=2, sticky="w"); fila += 1
        self._campo(f, fila, "k máximo", "kmax", 10); fila += 1
        self._campo(f, fila, "M máximo", "Mmax", 30); fila += 1

        ttk.Button(f, text="Calcular", command=self.calcular).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=(12, 4)); fila += 1
        ttk.Button(f, text="Exportar tablas a CSV", command=self.exportar_csv).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=2); fila += 1

        ttk.Label(f, wraplength=330, text="Un 'día' en las unidades equivale a las horas de\n"
                          "operación (cada 4 días con 8 h/día = cada 32 h).\n"
                          "En población finita, λ es la tasa de cada unidad.",
                  style="Sub.TLabel", justify="left").grid(row=fila, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # ---------------- Zona de resultados ----------------
        der = ttk.Frame(cuerpo, padding=(6, 0, 12, 10))
        der.pack(side="left", fill="both", expand=True)
        self.lbl_estado = ttk.Label(der, text="", style="Estado.TLabel", wraplength=900, justify="left")
        self.lbl_estado.pack(fill="x", pady=(0, 6))

        self.nb = ttk.Notebook(der)
        self.nb.pack(fill="both", expand=True)

        self._tab_resultados()
        self._tab_probabilidades()
        self._tab_dia()
        self._tab_comparar()
        self._tab_graficas()

    def _tabla(self, padre, columnas, anchos, alto=12):
        marco = ttk.Frame(padre)
        tv = ttk.Treeview(marco, columns=columnas, show="headings", height=alto)
        for c, w in zip(columnas, anchos):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="w" if w > 150 else "e", stretch=w > 150)
        sy = ttk.Scrollbar(marco, orient="vertical", command=tv.yview)
        sx = ttk.Scrollbar(marco, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tv.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)
        tv.tag_configure("ok", background="#DDF1EA")
        tv.tag_configure("mejor", background="#FFF1BF")
        tv.tag_configure("actual", font=("Segoe UI", 9, "bold"))
        return marco, tv

    def _tab_resultados(self):
        t = ttk.Frame(self.nb, padding=8)
        self.nb.add(t, text="Resultados")
        marco, self.tv_res = self._tabla(t, ("Símbolo", "Medida", "Valor", "Cuándo usarlo"),
                                         (80, 260, 130, 460), alto=20)
        marco.pack(fill="both", expand=True)

    def _tab_probabilidades(self):
        t = ttk.Frame(self.nb, padding=8)
        self.nb.add(t, text="Probabilidades")
        top = ttk.Frame(t)
        top.pack(fill="x")
        ttk.Label(top, text="n = a").pack(side="left")
        ea = ttk.Entry(top, textvariable=self._var("pa", 2), width=6)
        ea.pack(side="left", padx=4)
        ttk.Label(top, text="hasta b").pack(side="left", padx=(10, 0))
        eb = ttk.Entry(top, textvariable=self._var("pb", 3), width=6)
        eb.pack(side="left", padx=4)
        ttk.Button(top, text="Calcular", command=self.llenar_probabilidades).pack(side="left", padx=8)
        for e in (ea, eb):
            e.bind("<Return>", lambda ev: self.llenar_probabilidades())
        marco, self.tv_prob = self._tabla(t, ("Probabilidad", "Significado", "Valor"), (150, 360, 120), alto=11)
        marco.pack(fill="x", pady=8)
        ttk.Label(t, text="Distribución completa", style="Seccion.TLabel").pack(anchor="w")
        marco, self.tv_dist = self._tabla(t, ("n", "En cola", "Pn", "P(≤ n)", "P(≥ n)"),
                                          (60, 80, 120, 120, 120), alto=10)
        marco.pack(fill="both", expand=True)

    def _tab_dia(self):
        t = ttk.Frame(self.nb, padding=8)
        self.nb.add(t, text="Por día y costos")
        marco, self.tv_dia = self._tabla(t, ("Concepto", "Por día (h)", "Por día (min)", "Por semana"),
                                         (400, 130, 130, 150), alto=11)
        marco.pack(fill="x")
        ttk.Label(t, text="Tiempo en un estado = probabilidad × horas.  Clientes que esperan = λ × horas × probabilidad de esperar.",
                  style="Sub.TLabel").pack(anchor="w", pady=(4, 10))
        ttk.Label(t, text="Costos", style="Seccion.TLabel").pack(anchor="w")
        marco, self.tv_cost = self._tabla(t, ("Concepto", "Por día", "Por semana", "Detalle"),
                                          (260, 130, 130, 380), alto=7)
        marco.pack(fill="both", expand=True)

    def _tab_comparar(self):
        t = ttk.Frame(self.nb, padding=8)
        self.nb.add(t, text="Comparar k y M")
        top = ttk.Frame(t)
        top.pack(fill="x")
        self.metricas = self._lista_metricas()
        ttk.Label(top, text="Condición").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self._var("cond_m", self.metricas[2][0]),
                          values=[m[0] for m in self.metricas], state="readonly", width=34)
        cb.pack(side="left", padx=4)
        ttk.Combobox(top, textvariable=self._var("cond_op", "≤"), values=["≤", "≥"],
                     state="readonly", width=4).pack(side="left", padx=4)
        ent = ttk.Entry(top, textvariable=self._var("cond_v", 0.5), width=10)
        ent.pack(side="left", padx=4)
        ent.bind("<Return>", lambda e: self.llenar_comparar())
        cb.bind("<<ComboboxSelected>>", lambda e: self.llenar_comparar())
        ttk.Button(top, text="Buscar", command=self.llenar_comparar).pack(side="left", padx=6)
        ttk.Label(t, text="Las condiciones de tiempo usan la unidad de 'Mostrar tiempos en'. Verde: cumple. Amarillo: menor costo.",
                  style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

        self.lbl_k = ttk.Label(t, text="", style="Seccion.TLabel", wraplength=900)
        self.lbl_k.pack(anchor="w", pady=(8, 2))
        cols = ("k", "ρ", "P0", "P(n<k)", "P(esperar)", "P(n>k)", "Lq", "L", "Wq", "W", "Wn", "% operando", "CT(S)", "CT(TE)", "CT")
        marco, self.tv_k = self._tabla(t, cols, [50] + [88] * (len(cols) - 1), alto=8)
        marco.pack(fill="both", expand=True)

        self.lbl_M = ttk.Label(t, text="", style="Seccion.TLabel", wraplength=900)
        self.lbl_M.pack(anchor="w", pady=(10, 2))
        cols = ("M", "P0", "P(n<k)", "P(esperar)", "Lq", "L", "M − L", "% operando", "Wq", "W", "CT(S)", "CT(TE)", "CT")
        marco, self.tv_M = self._tabla(t, cols, [50] + [88] * (len(cols) - 1), alto=8)
        marco.pack(fill="both", expand=True)

    def _tab_graficas(self):
        t = ttk.Frame(self.nb, padding=8)
        self.nb.add(t, text="Gráficas")
        top = ttk.Frame(t)
        top.pack(fill="x")
        ttk.Label(top, text="Gráfica").pack(side="left")
        self.titulos_graf = [titulo for _, titulo in gc.GRAFICAS]
        self.cb_graf = ttk.Combobox(top, values=self.titulos_graf, state="readonly", width=42)
        self.cb_graf.current(0)
        self.cb_graf.pack(side="left", padx=6)
        self.cb_graf.bind("<<ComboboxSelected>>", lambda e: self.dibujar_grafica())
        ttk.Button(top, text="Anterior", command=lambda: self._mover_grafica(-1)).pack(side="left", padx=2)
        ttk.Button(top, text="Siguiente", command=lambda: self._mover_grafica(1)).pack(side="left", padx=2)
        fila2 = ttk.Frame(t)
        fila2.pack(fill="x", pady=(4, 4))
        ttk.Button(fila2, text="Guardar todas (PNG)", command=self.guardar_todas).pack(side="right", padx=2)
        ttk.Button(fila2, text="Guardar esta (PNG)", command=self.guardar_grafica).pack(side="right", padx=2)
        ttk.Label(fila2, text="Las de k usan 'k máximo'. Las de M usan 'M máximo' con el k actual (solo finita).",
                  style="Sub.TLabel").pack(side="left")
        zona = ttk.Frame(t)
        zona.pack(fill="both", expand=True)
        self.fig = Figure(figsize=(6, 4), dpi=100, layout="constrained")
        self.canvas = FigureCanvasTkAgg(self.fig, master=zona)
        NavigationToolbar2Tk(self.canvas, zona).update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _mover_grafica(self, paso):
        i = (self.cb_graf.current() + paso) % len(self.titulos_graf)
        self.cb_graf.current(i)
        self.dibujar_grafica()

    # ------------------------------------------------------------------
    # Lectura de datos
    # ------------------------------------------------------------------
    def _num(self, nombre, entero=False):
        txt = self.v[nombre].get().strip().replace(",", ".")
        try:
            x = float(txt)
        except ValueError:
            raise ValueError(f"Valor inválido en '{nombre}': {txt!r}")
        return int(round(x)) if entero else x

    def _leer(self):
        H = self._num("H")
        if H <= 0:
            raise ValueError("Las horas por día deben ser mayores que cero.")
        finita = self.v["poblacion"].get() == "Finita"
        k = max(1, self._num("k", True))
        M = max(1, self._num("M", True))
        lam = mc.tasa_por_hora(self.v["lam_modo"].get() == MODO_LAM[0], self._num("lam"), self.v["lam_u"].get(), H)
        mu = mc.tasa_por_hora(self.v["mu_modo"].get() == MODO_MU[0], self._num("mu"), self.v["mu_u"].get(), H)
        cfg = {
            "c_servidor": self._num("cS"), "c_servidor_u": self.v["cS_u"].get(),
            "c_espera": self._num("cW"), "c_espera_u": self.v["cW_u"].get(),
            "base_espera": "L" if self.v["cW_b"].get().startswith("L ") else "Lq",
            "c_ocio": self._num("cI"), "ingreso": self._num("ing"), "frac_ingreso": self._num("ingF"),
        }
        return {"H": H, "D": max(1, self._num("D")), "finita": finita, "k": k, "M": M,
                "lam": lam, "mu": mu, "cfg": cfg,
                "kmax": max(1, self._num("kmax", True)), "Mmax": max(2, min(300, self._num("Mmax", True)))}

    # ------------------------------------------------------------------
    # Formato
    # ------------------------------------------------------------------
    def f(self, x, d=None):
        if x is None or not isinstance(x, (int, float)) or not math.isfinite(x):
            return "—"
        d = int(self.v["dec"].get()) if d is None else d
        return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def pct(self, x):
        return self.f(x * 100, 2) + " %" if x is not None and math.isfinite(x) else "—"

    def money(self, x):
        return "$ " + self.f(x, 2)

    def t_out(self, horas):
        return horas / mc.horas_por_unidad(self.v["ut"].get(), self.d["H"])

    def tf(self, horas):
        if horas is None or not math.isfinite(horas):
            return "—"
        return f"{self.f(self.t_out(horas))} {ABREV[self.v['ut'].get()]}"

    @staticmethod
    def _vaciar(tv):
        tv.delete(*tv.get_children())

    # ------------------------------------------------------------------
    # Cálculo principal
    # ------------------------------------------------------------------
    def calcular(self):
        try:
            self.d = self._leer()
        except ValueError as e:
            messagebox.showerror("Datos inválidos", str(e))
            return
        d = self.d
        k, M = d["k"], d["M"]
        sigla, kendall = mc.nombre_modelo(d["finita"], k)
        self.lbl_modelo.config(text=kendall.replace("/M/M", f"/{M}/{M}") if d["finita"] else kendall)
        self.lbl_desc.config(text=f"{sigla} · población {'finita de ' + str(M) if d['finita'] else 'infinita'} · "
                                  f"{'un canal' if k == 1 else str(k) + ' canales'}")
        self.lbl_lam.config(text=f"λ = {self.f(d['lam'])} por hora")
        self.lbl_mu.config(text=f"μ = {self.f(d['mu'])} por hora")

        self.r = mc.resolver(d["lam"], d["mu"], k, d["finita"], M)
        self.barrido_k = mc.barrido_k(d["lam"], d["mu"], d["finita"], M, d["kmax"])
        self.barrido_M = mc.barrido_M(d["lam"], d["mu"], k, d["Mmax"]) if d["finita"] else []

        r = self.r
        if not r["ok"]:
            self.lbl_estado.config(foreground="#B3261E",
                                   text=f"Sistema inestable: λ/(kμ) = {self.f(r['rho'])} ≥ 1. La cola crece sin límite. "
                                        f"Se necesitan al menos k = {r['k_min']} servidores (revisa la pestaña Comparar).")
            for tv in (self.tv_res, self.tv_prob, self.tv_dist, self.tv_dia, self.tv_cost):
                self._vaciar(tv)
        else:
            if d["finita"]:
                txt = (f"Población finita: siempre estable. λ/μ por unidad = {self.f(r['a'])}. "
                       f"λ efectiva = λ(M − L) = {self.f(r['lam_ef'])} por hora.")
                if k > M:
                    txt += f" Como k > M, se usan {M} servidores efectivos."
            else:
                txt = f"Sistema estable: ρ = λ/(kμ) = {self.f(r['rho'])} < 1. Tráfico λ/μ = {self.f(r['a'])}."
            self.lbl_estado.config(foreground="#23806F", text=txt)
            self.llenar_resultados()
            self.llenar_probabilidades()
            self.llenar_dia()
        self.llenar_comparar()
        self.dibujar_grafica()

    # ------------------------------------------------------------------
    # Pestañas
    # ------------------------------------------------------------------
    def llenar_resultados(self):
        r, tv = self.r, self.tv_res
        self._vaciar(tv)
        filas = [
            ("ρ", "Utilización por servidor", self.f(r["util"]), "Proporción de tiempo que trabaja cada servidor."),
            ("P0", "Sistema vacío", self.f(r["P0"]), "Todos los servidores desocupados a la vez."),
            ("P(n<k)", "Algún servidor libre", self.f(r["Plt"]), "Uno o varios desocupados."),
            ("P(n≥k)", "Todos ocupados", self.f(r["Pk"]), "Proporción del tiempo con todos ocupados."),
            ("Pw", "Probabilidad de esperar", self.f(r["frac_espera"]),
             "Fracción de clientes que deben esperar" + (" (finita: vista por quien llega)." if r["finita"] else " (= P(n≥k)).")),
            ("1−Pw", "Probabilidad de no esperar", self.f(r["frac_no_espera"]), "Atendidos en cuanto llegan."),
            ("P(n>k)", "Hay línea de espera", self.f(r["Pgt"]), "Al menos un cliente en cola."),
            ("P(n=k)", "Todos ocupados y nadie esperando", self.f(r["p"][r["k_ef"]]), ""),
            ("L", "Clientes en el sistema", self.f(r["L"]), "Esperando más siendo atendidos."),
            ("Lq", "Clientes en cola", self.f(r["Lq"]), "Longitud media de la línea de espera."),
            ("W", "Tiempo en el sistema", self.tf(r["W"]), "Espera más servicio."),
            ("Wq", "Tiempo en cola", self.tf(r["Wq"]), "Promedio de todos los clientes."),
            ("Wn", "Espera de los que sí esperan", self.tf(r["Wn"]), "Wq ÷ probabilidad de esperar."),
            ("Ln", "Clientes en cola no vacía", self.f(r["Ln"]), "Lq ÷ P(n>k)."),
            ("Ociosos", "Servidores ociosos en promedio", self.f(r["ociosos"]), "Para costo de ociosidad."),
        ]
        if r["finita"]:
            filas += [
                ("M−L", "Unidades operando", self.f(r["operando"]), self.pct(r["frac_operando"]) + " de la población."),
                ("λef", "λ efectiva", self.f(r["lam_ef"]) + " /h", "λ(M − L): llegadas reales."),
            ]
        for fila in filas:
            tv.insert("", "end", values=fila)

    def llenar_probabilidades(self):
        r = self.r
        if not r or not r["ok"]:
            return
        p, kk = r["p"], r["k_ef"]
        try:
            a = max(0, self._num("pa", True))
            b = max(a, self._num("pb", True))
        except ValueError as e:
            messagebox.showerror("Datos inválidos", str(e))
            return
        P = lambda n: p[n] if 0 <= n < len(p) else 0.0
        acum = lambda n: min(1.0, sum(p[: max(0, n + 1)]))
        tv = self.tv_prob
        self._vaciar(tv)
        filas = [
            (f"P(n = {a})", f"Exactamente {a} en el sistema", P(a)),
            (f"P(n ≤ {a})", f"Como máximo {a} en el sistema", acum(a)),
            (f"P(n ≥ {a})", f"Al menos {a} en el sistema", 1 - acum(a - 1)),
            (f"P(n > {a})", f"Más de {a} en el sistema", 1 - acum(a)),
            (f"P({a} ≤ n ≤ {b})", f"Entre {a} y {b} en el sistema", acum(b) - acum(a - 1)),
            (f"P(cola = {a})", f"Exactamente {a} esperando", acum(kk) if a == 0 else P(kk + a)),
            (f"P(cola ≥ {a})", f"Al menos {a} esperando (n ≥ k+{a})", 1 - acum(kk + a - 1) if a > 0 else 1.0),
            (f"P(cola > {a})", f"Más de {a} esperando (n ≥ k+{a + 1})", 1 - acum(kk + a)),
            (f"P(cola ≤ {a})", f"Como máximo {a} esperando", acum(kk + a)),
            (f"P({a} ≤ cola ≤ {b})", f"Entre {a} y {b} esperando",
             acum(kk + b) if a == 0 else acum(kk + b) - acum(kk + a - 1)),
        ]
        for s, t, v in filas:
            tv.insert("", "end", values=(s, t, self.f(v)))

        tv = self.tv_dist
        self._vaciar(tv)
        n_max = len(p) - 1
        if not r["finita"]:
            n = 0
            while n < n_max and (n <= kk + 2 or p[n] > 1e-6) and n < 150:
                n += 1
            n_max = n
        c = 0.0
        for n in range(n_max + 1):
            antes = c
            c += p[n]
            tv.insert("", "end", values=(n, max(0, n - kk), self.f(p[n]), self.f(min(1, c)), self.f(max(0, 1 - antes))),
                      tags=("actual",) if n == kk else ())

    def llenar_dia(self):
        r, d = self.r, self.d
        H, D = d["H"], d["D"]
        llegadas = r["lam_ef"] * H
        horas = [
            ("Todos los servidores desocupados a la vez (P0)", r["P0"] * H),
            ("Uno o varios servidores desocupados (P(n<k))", r["Plt"] * H),
            ("Todos los servidores ocupados (P(n≥k))", r["Pk"] * H),
            ("Con clientes esperando en cola (P(n>k))", r["Pgt"] * H),
            ("Horas de ocio sumadas de todos los servidores", r["ociosos"] * H),
            ("Horas de trabajo sumadas de todos los servidores", (r["k_ef"] - r["ociosos"]) * H),
            ("Horas totales de espera en cola (Lq × horas)", r["Lq"] * H),
            ("Horas totales en el sistema (L × horas)", r["L"] * H),
        ]
        tv = self.tv_dia
        self._vaciar(tv)
        for t, v in horas:
            tv.insert("", "end", values=(t, self.f(v), self.f(v * 60), self.f(v * D) + " h"))
        for t, v in [("Clientes que llegan", llegadas),
                     ("Clientes que deben esperar", llegadas * r["frac_espera"]),
                     ("Clientes atendidos en cuanto llegan", llegadas * r["frac_no_espera"])]:
            tv.insert("", "end", values=(t, self.f(v) + " clientes", "", self.f(v * D) + " clientes"))

        c = mc.costos(r, H, d["cfg"])
        tv = self.tv_cost
        self._vaciar(tv)
        base = "L" if d["cfg"]["base_espera"] == "L" else "Lq"
        filas = [
            ("CT(S) costo de servidores", c["ct_s"], "k × costo por servidor"),
            ("CT(TE) costo del tiempo de espera", c["ct_te"], f"{base} × horas × costo por hora"),
            ("Costo de ociosidad", c["ct_ocio"], "Servidores ociosos × horas × costo por hora"),
            ("CT costo total", c["ct"], f"{self.money(c['ct'] / H)} por hora"),
            ("Ingresos", c["ingreso"], "λ efectiva × horas × fracción × ingreso"),
        ]
        for t, v, det in filas:
            tv.insert("", "end", values=(t, self.money(v), self.money(v * D), det))
        tv.insert("", "end", values=("Rentabilidad (ingresos ÷ gastos)", self.f(c["rentabilidad"]), "",
                                     f"Utilidad diaria: {self.money(c['ingreso'] - c['ct'])}"))

    # ------------------------------------------------------------------
    # Comparar
    # ------------------------------------------------------------------
    def _lista_metricas(self):
        # (nombre, función(r) -> valor, es_tiempo)
        return [
            ("P0 (sistema vacío)", lambda r: r["P0"], False),
            ("P(n<k) algún servidor libre", lambda r: r["Plt"], False),
            ("Probabilidad de esperar", lambda r: r["frac_espera"], False),
            ("Probabilidad de no esperar", lambda r: r["frac_no_espera"], False),
            ("P(n≥k) todos ocupados", lambda r: r["Pk"], False),
            ("P(n>k) hay cola", lambda r: r["Pgt"], False),
            ("L (clientes en el sistema)", lambda r: r["L"], False),
            ("Lq (clientes en cola)", lambda r: r["Lq"], False),
            ("W (tiempo en el sistema)", lambda r: self.t_out(r["W"]), True),
            ("Wq (tiempo en cola)", lambda r: self.t_out(r["Wq"]), True),
            ("Wn (espera de los que esperan)", lambda r: self.t_out(r["Wn"]), True),
            ("Fracción de unidades operando (finita)", lambda r: r["frac_operando"] if r["finita"] else float("nan"), False),
            ("Costo total diario CT", lambda r: mc.costos(r, self.d["H"], self.d["cfg"])["ct"], False),
        ]

    def _cumple(self, r):
        nombre = self.v["cond_m"].get()
        fn = next((m[1] for m in self.metricas if m[0] == nombre), None)
        try:
            lim = self._num("cond_v")
        except ValueError:
            return False
        try:
            val = fn(r)
        except Exception:
            return False
        if val is None or not math.isfinite(val):
            return False
        return val <= lim + 1e-12 if self.v["cond_op"].get() == "≤" else val >= lim - 1e-12

    def llenar_comparar(self):
        if not hasattr(self, "d"):
            return
        d = self.d
        nombre = self.v["cond_m"].get()
        es_t = next((m[2] for m in self.metricas if m[0] == nombre), False)
        cond_txt = f"{nombre} {self.v['cond_op'].get()} {self.v['cond_v'].get()}" + (f" {ABREV[self.v['ut'].get()]}" if es_t else "")

        # Tabla en función de k
        tv = self.tv_k
        self._vaciar(tv)
        filas = [(r, mc.costos(r, d["H"], d["cfg"])) for r in self.barrido_k if r["ok"]]
        hay_costos = any(c["ct"] > 0 for _, c in filas)
        mejor = min(range(len(filas)), key=lambda i: filas[i][1]["ct"]) if (filas and hay_costos) else -1
        primero = next((r["k"] for r, _ in filas if self._cumple(r)), None)
        for i, (r, c) in enumerate(filas):
            tags = []
            if self._cumple(r):
                tags.append("ok")
            if i == mejor:
                tags.append("mejor")
            if r["k"] == d["k"]:
                tags.append("actual")
            tv.insert("", "end", tags=tags, values=(
                r["k"], self.f(r["util"]), self.f(r["P0"]), self.f(r["Plt"]), self.f(r["frac_espera"]),
                self.f(r["Pgt"]), self.f(r["Lq"]), self.f(r["L"]), self.f(self.t_out(r["Wq"])),
                self.f(self.t_out(r["W"])), self.f(self.t_out(r["Wn"])),
                self.pct(r["frac_operando"]) if r["finita"] else "—",
                self.money(c["ct_s"]), self.money(c["ct_te"] + c["ct_ocio"]), self.money(c["ct"])))
        txt = "" if d["finita"] else f"Mínimo por estabilidad: k = {mc.k_minimo_estable(d['lam'], d['mu'])}.  "
        txt += f"Menor k con {cond_txt}: k = {primero}." if primero else f"Ningún k del rango cumple {cond_txt}."
        if mejor >= 0:
            txt += f"  Menor costo total: k = {filas[mejor][0]['k']} ({self.money(filas[mejor][1]['ct'])} por día)."
        self.lbl_k.config(text=txt)

        # Tabla en función de M
        tv = self.tv_M
        self._vaciar(tv)
        if not d["finita"]:
            self.lbl_M.config(text="Tabla en función de M: solo para población finita.")
            return
        ultimo = None
        for r in self.barrido_M:
            c = mc.costos(r, d["H"], d["cfg"])
            ok = self._cumple(r)
            if ok:
                ultimo = r["M"]
            tags = (["ok"] if ok else []) + (["actual"] if r["M"] == d["M"] else [])
            tv.insert("", "end", tags=tags, values=(
                r["M"], self.f(r["P0"]), self.f(r["Plt"]), self.f(r["frac_espera"]), self.f(r["Lq"]),
                self.f(r["L"]), self.f(r["operando"]), self.pct(r["frac_operando"]),
                self.f(self.t_out(r["Wq"])), self.f(self.t_out(r["W"])),
                self.money(c["ct_s"]), self.money(c["ct_te"] + c["ct_ocio"]), self.money(c["ct"])))
        self.lbl_M.config(text=(f"Mayor M con {cond_txt} (k = {d['k']}): M = {ultimo}." if ultimo
                                else f"Ningún M del rango cumple {cond_txt}."))

    # ------------------------------------------------------------------
    # Gráficas
    # ------------------------------------------------------------------
    def _ctx(self):
        d = self.d
        sigla, _ = mc.nombre_modelo(d["finita"], d["k"])
        sub = (f"λ = {d['lam']:.4g}/h, μ = {d['mu']:.4g}/h"
               + (f", M = {d['M']}" if d["finita"] else "") + f", k actual = {d['k']}")
        return {"finita": d["finita"], "barrido_k": self.barrido_k, "barrido_M": self.barrido_M,
                "k": d["k"], "M": d["M"], "H": d["H"], "unidad_tiempo": self.v["ut"].get(),
                "cfg": d["cfg"], "subtitulo": sub}

    def _gid(self):
        i = self.cb_graf.current()
        return gc.GRAFICAS[i if i >= 0 else 0][0]

    def dibujar_grafica(self):
        if not hasattr(self, "d"):
            return
        gc.dibujar(self.fig, self._gid(), self._ctx())
        self.canvas.draw_idle()

    def guardar_grafica(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")],
                                            initialfile=f"{self._gid()}.png")
        if ruta:
            self.fig.savefig(ruta, dpi=150)

    def guardar_todas(self):
        carpeta = filedialog.askdirectory(title="Carpeta para guardar las gráficas")
        if not carpeta:
            return
        ctx = self._ctx()
        n = 0
        for i, (gid, _) in enumerate(gc.GRAFICAS, start=1):
            if gid.endswith("_M") and not ctx["finita"]:
                continue
            fig = Figure(figsize=(9, 5.5), dpi=150, layout="constrained")
            gc.dibujar(fig, gid, ctx)
            fig.savefig(os.path.join(carpeta, f"{i:02d}_{gid}.png"))
            n += 1
        messagebox.showinfo("Gráficas guardadas", f"Se guardaron {n} gráficas en:\n{carpeta}")

    # ------------------------------------------------------------------
    # Exportar
    # ------------------------------------------------------------------
    def exportar_csv(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="resultados_colas.csv")
        if not ruta:
            return
        with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            for titulo, tv in (("Resultados", self.tv_res), ("Probabilidades", self.tv_prob),
                               ("Por día", self.tv_dia), ("Costos", self.tv_cost),
                               ("Variando k", self.tv_k), ("Variando M", self.tv_M)):
                w.writerow([titulo])
                w.writerow(tv["columns"])
                for item in tv.get_children():
                    w.writerow(tv.item(item, "values"))
                w.writerow([])
        messagebox.showinfo("Exportado", f"Tablas guardadas en:\n{ruta}")


if __name__ == "__main__":
    App().mainloop()
