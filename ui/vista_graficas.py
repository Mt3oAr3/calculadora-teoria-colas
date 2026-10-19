"""
vista_graficas.py
Pestaña «Gráficas»: índice de gráficas agrupado por categoría a la izquierda,
figura matplotlib a la derecha y acciones para guardar PNG.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from services import exportacion_service as ex
from visualization import graficas_colas as gc

from . import estilos as es


class VistaGraficas:

    def __init__(self, notebook, avisar):
        self._avisar = avisar           # función para mensajes en la barra de estado
        self.ctx = None

        t = ttk.Frame(notebook, padding=10)
        notebook.add(t, text="Gráficas")
        t.columnconfigure(1, weight=1)
        t.rowconfigure(1, weight=1)

        # Índice por categoría
        izq = ttk.Frame(t)
        izq.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))
        ttk.Label(izq, text="Gráficas", style="Seccion.TLabel").pack(anchor="w", pady=(0, 4))
        self.arbol = ttk.Treeview(izq, show="tree", selectmode="browse", height=18)
        self.arbol.column("#0", width=250)
        self.arbol.pack(fill="y", expand=True)
        self.arbol.tag_configure("no_aplica", foreground=es.TINTA_3)
        self.arbol.tag_configure("categoria", font=es.fuente(10, "bold"))
        self.orden = []
        for cat in gc.CATEGORIAS:
            nodo = self.arbol.insert("", "end", iid=f"cat_{cat}", text=cat, open=True, tags=("categoria",))
            for g in gc.GRAFICAS:
                if g.categoria == cat:
                    texto = ("vs M · " if g.por_M else "vs k · ") + g.titulo.split(" en función")[0]
                    self.arbol.insert(nodo, "end", iid=g.gid, text=texto)
                    self.orden.append(g.gid)
        self.arbol.bind("<<TreeviewSelect>>", self._al_seleccionar)
        nav = ttk.Frame(izq)
        nav.pack(fill="x", pady=(6, 0))
        ttk.Button(nav, text="◀ Anterior", style="Chico.TButton", command=lambda: self._mover(-1)).pack(side="left")
        ttk.Button(nav, text="Siguiente ▶", style="Chico.TButton", command=lambda: self._mover(1)).pack(side="right")
        ttk.Label(izq, text="Las gráficas «vs k» usan el rango «k máximo»; las «vs M» usan «M máximo» "
                            "con el k actual (solo población finita).", style="Nota.TLabel",
                  wraplength=250, justify="left").pack(anchor="w", pady=(8, 0))

        # Barra de acciones
        barra = ttk.Frame(t)
        barra.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        self.v_valores = tk.BooleanVar(value=True)
        ttk.Checkbutton(barra, text="Mostrar valores en los puntos", variable=self.v_valores,
                        command=self.dibujar).pack(side="left")
        self.btn_todas = ttk.Button(barra, text="Guardar todas (PNG)", style="Chico.TButton", command=self.guardar_todas)
        self.btn_todas.pack(side="right", padx=2)
        self.btn_esta = ttk.Button(barra, text="Guardar esta (PNG)", style="Chico.TButton", command=self.guardar_esta)
        self.btn_esta.pack(side="right", padx=2)

        zona = ttk.Frame(t)
        zona.grid(row=1, column=1, sticky="nsew")
        self.fig = Figure(figsize=(6, 4), dpi=100, layout="constrained")
        self.canvas = FigureCanvasTkAgg(self.fig, master=zona)
        NavigationToolbar2Tk(self.canvas, zona).update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.arbol.selection_set(self.orden[0])
        self._habilitar(False)

    # ------------------------------------------------------------------
    def _gid(self):
        sel = self.arbol.selection()
        return sel[0] if sel and sel[0] in self.orden else self.orden[0]

    def _al_seleccionar(self, _e=None):
        sel = self.arbol.selection()
        if sel and sel[0].startswith("cat_"):
            hijos = self.arbol.get_children(sel[0])
            if hijos:
                self.arbol.selection_set(hijos[0])
            return
        self.dibujar()

    def _mover(self, paso):
        i = (self.orden.index(self._gid()) + paso) % len(self.orden)
        self.arbol.selection_set(self.orden[i])
        self.arbol.see(self.orden[i])

    def _habilitar(self, si):
        for b in (self.btn_esta, self.btn_todas):
            b.state(["!disabled"] if si else ["disabled"])

    def mostrar(self, ctx):
        self.ctx = ctx
        for g in gc.GRAFICAS:
            aplica = ctx["finita"] or not g.por_M
            self.arbol.item(g.gid, tags=() if aplica else ("no_aplica",))
        self._habilitar(True)
        self.dibujar()

    def dibujar(self):
        if self.ctx is None:
            return
        self.ctx["mostrar_valores"] = self.v_valores.get()
        gc.dibujar(self.fig, self._gid(), self.ctx)
        self.canvas.draw_idle()

    def limpiar(self, mensaje):
        self.ctx = None
        self._habilitar(False)
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.axis("off")
        ax.text(0.5, 0.5, mensaje, ha="center", va="center", fontsize=11, color=gc.TINTA_2, wrap=True)
        self.canvas.draw_idle()

    def guardar_esta(self):
        if self.ctx is None:
            return
        gid = self._gid()
        ruta = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")],
                                            initialfile=f"{gid}.png")
        if not ruta:
            return
        try:
            ex.guardar_grafica(ruta, gid, self.ctx)
        except OSError as e:
            messagebox.showerror("No se pudo guardar", f"No se pudo guardar la gráfica:\n{e.strerror or e}")
            return
        self._avisar(f"Gráfica guardada en {ruta}")

    def guardar_todas(self):
        if self.ctx is None:
            return
        carpeta = filedialog.askdirectory(title="Carpeta para guardar las gráficas")
        if not carpeta:
            return
        try:
            rutas = ex.guardar_todas(carpeta, self.ctx)
        except OSError as e:
            messagebox.showerror("No se pudo guardar", f"No se pudieron guardar las gráficas:\n{e.strerror or e}")
            return
        self._avisar(f"Se guardaron {len(rutas)} gráficas en {carpeta}")
        messagebox.showinfo("Gráficas guardadas", f"Se guardaron {len(rutas)} gráficas en:\n{carpeta}")
