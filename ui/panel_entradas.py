"""
panel_entradas.py
Formulario de parámetros agrupado por categorías, con unidades visibles,
ayudas breves, errores por campo y una barra de acciones fija abajo.

No valida ni calcula nada: entrega el texto de cada campo (valores()) y la
validación la hace services.calculadora_service.leer_parametros().
"""
import tkinter as tk
from tkinter import ttk

from domain.unidades import ABREV, UNIDADES
from services import calculadora_service as cs

from .componentes import PanelDesplazable

# Campos que solo cambian la presentación (no exigen recalcular)
CAMPOS_PRESENTACION = ("ut", "dec")


class PanelEntradas(ttk.Frame):

    def __init__(self, padre, al_calcular, al_exportar, al_cambiar_datos, al_cambiar_presentacion):
        super().__init__(padre)
        self._al_calcular = al_calcular
        self._al_cambiar_datos = al_cambiar_datos
        self._al_cambiar_presentacion = al_cambiar_presentacion
        self.v = {}               # clave -> StringVar
        self.widgets = {}         # clave -> Entry / Combobox
        self.etiquetas = {}       # clave -> Label del campo
        self.errores = {}         # clave -> Label de error
        self._silencio = True     # no notificar cambios mientras se construye

        self.scroll = PanelDesplazable(self, ancho=372)
        self.scroll.pack(side="top", fill="both", expand=True)
        cuerpo = self.scroll.interior
        cuerpo.columnconfigure(0, weight=1)

        ttk.Label(cuerpo, text="Parámetros", style="Seccion.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._grupo_modelo(cuerpo, 1)
        self._grupo_capacidad(cuerpo, 2)
        self._grupo_llegadas_servicio(cuerpo, 3)
        self._grupo_operacion(cuerpo, 4)
        self._grupo_costos(cuerpo, 5)
        self._grupo_analisis(cuerpo, 6)
        self._grupo_presentacion(cuerpo, 7)

        # Barra de acciones fija (no se desplaza con el formulario)
        acciones = ttk.Frame(self, padding=(10, 8, 10, 10))
        acciones.pack(side="bottom", fill="x")
        ttk.Separator(self).pack(side="bottom", fill="x")
        acciones.columnconfigure(0, weight=1)
        acciones.columnconfigure(1, weight=1)
        self.btn_calcular = ttk.Button(acciones, text="Calcular  (Enter)", style="Accion.TButton",
                                       command=al_calcular)
        self.btn_calcular.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.btn_exportar = ttk.Button(acciones, text="Exportar tablas (CSV)", style="Secundario.TButton",
                                       command=al_exportar)
        self.btn_exportar.grid(row=1, column=0, sticky="ew", pady=(6, 0), padx=(0, 3))
        ttk.Button(acciones, text="Valores iniciales", style="Secundario.TButton",
                   command=self.restablecer).grid(row=1, column=1, sticky="ew", pady=(6, 0), padx=(3, 0))

        for clave, var in self.v.items():
            if clave in ("pa", "pb"):
                continue
            destino = self._cambio_presentacion if clave in CAMPOS_PRESENTACION else self._cambio_datos
            var.trace_add("write", lambda *_a, d=destino: d())
        self._actualizar_dependencias()
        self._silencio = False

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _grupo(self, padre, fila, titulo):
        marco = ttk.Frame(padre)
        marco.grid(row=fila, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(marco, text=titulo, style="GrupoTitulo.TLabel").pack(anchor="w", pady=(0, 3))
        g = ttk.Frame(marco, style="GrupoCuerpo.TFrame", padding=(10, 4, 10, 8))
        g.pack(fill="x")
        g.columnconfigure(1, weight=1)
        g._fila = 0
        return g

    def _var(self, clave):
        if clave not in self.v:
            self.v[clave] = tk.StringVar(value=cs.VALORES_INICIALES[clave])
        return self.v[clave]

    def _campo(self, g, clave, etiqueta, unidad="", ayuda="", opciones=None, unidad_widget=None, ancho=12):
        """Fila: etiqueta | entrada o lista | unidad. Debajo: ayuda y error (oculto)."""
        f = g._fila
        lbl = ttk.Label(g, text=etiqueta, style="Campo.TLabel")
        lbl.grid(row=f, column=0, sticky="w", pady=(3, 0), padx=(0, 8))
        if opciones is not None:
            w = ttk.Combobox(g, textvariable=self._var(clave), values=opciones, state="readonly", width=ancho)
        else:
            w = ttk.Entry(g, textvariable=self._var(clave), width=ancho, justify="right")
            w.bind("<Return>", lambda e: self._al_calcular())
        # Las listas sin unidad ocupan también la columna de unidad para no cortarse
        ancho_cols = 2 if (opciones is not None and not unidad and unidad_widget is None) else 1
        w.grid(row=f, column=1, columnspan=ancho_cols, sticky="ew", pady=(3, 0))
        if unidad_widget is not None:
            unidad_widget.grid(row=f, column=2, sticky="w", padx=(6, 0), pady=(3, 0))
        elif unidad:
            ttk.Label(g, text=unidad, style="Unidad.TLabel").grid(row=f, column=2, sticky="w", padx=(6, 0), pady=(3, 0))
        f += 1
        if ayuda:
            ttk.Label(g, text=ayuda, style="Ayuda.TLabel", wraplength=300, justify="left").grid(
                row=f, column=0, columnspan=3, sticky="w")
            f += 1
        err = ttk.Label(g, text="", style="ErrorCampo.TLabel", wraplength=300, justify="left")
        err.grid(row=f, column=0, columnspan=3, sticky="w")
        err.grid_remove()
        g._fila = f + 1
        self.widgets[clave], self.etiquetas[clave], self.errores[clave] = w, lbl, err
        return w

    def _combo_unidad(self, g, clave, opciones, ancho=8):
        c = ttk.Combobox(g, textvariable=self._var(clave), values=opciones, state="readonly", width=ancho)
        self.widgets[clave] = c
        return c

    def _subtitulo(self, g, texto):
        ttk.Label(g, text=texto, style="Subgrupo.TLabel").grid(row=g._fila, column=0, columnspan=3,
                                                               sticky="w", pady=(6, 0))
        g._fila += 1

    def _grupo_modelo(self, padre, fila):
        g = self._grupo(padre, fila, "Modelo de colas")
        ttk.Label(g, text="Población", style="Campo.TLabel").grid(row=0, column=0, sticky="w", pady=(3, 0))
        radios = ttk.Frame(g, style="Superficie.TFrame")
        radios.grid(row=0, column=1, columnspan=2, sticky="w", pady=(3, 0))
        for texto in cs.POBLACIONES:
            ttk.Radiobutton(radios, text=texto, value=texto, variable=self._var("poblacion")).pack(side="left", padx=(0, 10))
        g._fila = 1
        self._campo(g, "k", "Servidores k", "servidores", "Canales de servicio en paralelo (entero ≥ 1).")

    def _grupo_capacidad(self, padre, fila):
        g = self._grupo(padre, fila, "Capacidad y población")
        self._campo(g, "M", "Población M", "unidades",
                    "Solo población finita: número de unidades que pueden llegar.")

    def _grupo_llegadas_servicio(self, padre, fila):
        g = self._grupo(padre, fila, "Llegadas y servicio")
        self._subtitulo(g, "Llegadas λ")
        self._campo(g, "lam_modo", "Dato", opciones=cs.MODO_LAM, ancho=24)
        self._campo(g, "lam", "Valor", unidad_widget=self._combo_unidad(g, "lam_u", UNIDADES))
        self.lbl_previa_lam = ttk.Label(g, text="", style="Previa.TLabel")
        self.lbl_previa_lam.grid(row=g._fila, column=0, columnspan=3, sticky="w")
        g._fila += 1
        self._subtitulo(g, "Servicio μ (por servidor)")
        self._campo(g, "mu_modo", "Dato", opciones=cs.MODO_MU, ancho=24)
        self._campo(g, "mu", "Valor", unidad_widget=self._combo_unidad(g, "mu_u", UNIDADES))
        self.lbl_previa_mu = ttk.Label(g, text="", style="Previa.TLabel")
        self.lbl_previa_mu.grid(row=g._fila, column=0, columnspan=3, sticky="w")
        g._fila += 1

    def _grupo_operacion(self, padre, fila):
        g = self._grupo(padre, fila, "Configuración operativa")
        self._campo(g, "H", "Horas por día", "h/día",
                    "Un «día» en las unidades equivale a estas horas (cada 4 días con 8 h/día = cada 32 h).")
        self._campo(g, "D", "Días por semana", "días", "Para los totales semanales (máximo 7).")

    def _grupo_costos(self, padre, fila):
        g = self._grupo(padre, fila, "Costos e ingresos (opcional)")
        self._campo(g, "cS", "Costo por servidor", unidad_widget=self._combo_unidad(g, "cS_u", ["hora", "día"]))
        self._campo(g, "cW", "Costo de espera", unidad_widget=self._combo_unidad(g, "cW_u", UNIDADES),
                    ayuda="$ por cliente y por unidad de tiempo.")
        self._campo(g, "cW_b", "Se cobra sobre", opciones=list(cs.BASES_ESPERA), ancho=22)
        self._campo(g, "cI", "Servidor ocioso", "$/h")
        self._campo(g, "ing", "Ingreso por cliente", "$")
        self._campo(g, "ingF", "Fracción con ingreso", "0 a 1")

    def _grupo_analisis(self, padre, fila):
        g = self._grupo(padre, fila, "Análisis y comparación")
        self._campo(g, "kmax", "k máximo", "servidores", "Rango de las tablas y gráficas en función de k (≤ 200).")
        self._campo(g, "Mmax", "M máximo", "unidades", "Solo finita: rango en función de M (2 a 300).")

    def _grupo_presentacion(self, padre, fila):
        g = self._grupo(padre, fila, "Presentación de resultados")
        self._campo(g, "ut", "Mostrar tiempos en", opciones=UNIDADES, ancho=10)
        self._campo(g, "dec", "Decimales", opciones=cs.DECIMALES, ancho=10)

    # ------------------------------------------------------------------
    # Comportamiento
    # ------------------------------------------------------------------
    def valores(self):
        return {c: v.get() for c, v in self.v.items()}

    def get(self, clave):
        return self.v[clave].get()

    @property
    def finita(self):
        return self.v["poblacion"].get() == "Finita"

    def restablecer(self):
        self._silencio = True
        for clave, var in self.v.items():
            var.set(cs.VALORES_INICIALES[clave])
        self._silencio = False
        self.limpiar_errores()
        self._actualizar_dependencias()
        self._al_cambiar_datos()

    def _cambio_datos(self):
        if self._silencio:
            return
        self._actualizar_dependencias()
        self._al_cambiar_datos()

    def _cambio_presentacion(self):
        if not self._silencio:
            self._al_cambiar_presentacion()

    def _actualizar_dependencias(self):
        """Habilita solo los campos que aplican al modelo y actualiza las vistas previas."""
        finita = self.finita
        for clave in ("M", "Mmax"):
            estado = "normal" if cs.campo_aplica(clave, finita) else "disabled"
            self.widgets[clave].configure(state=estado)
            self.etiquetas[clave].state(["!disabled"] if estado == "normal" else ["disabled"])
            if estado == "disabled":
                self._ocultar_error(clave)
        self.etiquetas["lam"].configure(text="Valor (por unidad)" if finita else "Valor")
        self._vista_previa("lam", cs.MODO_LAM, self.lbl_previa_lam, "λ")
        self._vista_previa("mu", cs.MODO_MU, self.lbl_previa_mu, "μ")

    def _vista_previa(self, clave, modos, etiqueta, simbolo):
        es_tasa = self.get(f"{clave}_modo") == modos[0]
        unidad = self.get(f"{clave}_u")
        tasa = cs.vista_previa_tasa(es_tasa, self.get(clave), unidad, self.get("H"))
        leyenda = f"clientes por {unidad}" if es_tasa else f"{ABREV[unidad]} por cliente"
        txt = f"({leyenda})  →  {simbolo} = "
        txt += (f"{tasa:.6g}".replace(".", ",") + " /h") if tasa is not None else "—"
        if clave == "lam" and self.finita:
            txt += " por unidad"
        etiqueta.configure(text=txt)

    def habilitar_exportar(self, habilitado):
        self.btn_exportar.state(["!disabled"] if habilitado else ["disabled"])

    # Errores por campo -------------------------------------------------
    def marcar_errores(self, errores):
        """errores: lista de (clave, mensaje). Resalta y lleva la vista al primero."""
        self.limpiar_errores()
        primero = None
        for clave, mensaje in errores:
            if clave not in self.widgets:
                continue
            w = self.widgets[clave]
            if isinstance(w, ttk.Entry) and not isinstance(w, ttk.Combobox):
                w.configure(style="Error.TEntry")
            if clave in self.errores:
                self.errores[clave].configure(text=mensaje)
                self.errores[clave].grid()
            primero = primero or w
        if primero is not None:
            self.scroll.mostrar_widget(primero)
            primero.focus_set()

    def _ocultar_error(self, clave):
        w = self.widgets.get(clave)
        if isinstance(w, ttk.Entry) and not isinstance(w, ttk.Combobox):
            w.configure(style="TEntry")
        if clave in self.errores:
            self.errores[clave].grid_remove()

    def limpiar_errores(self):
        for clave in self.widgets:
            self._ocultar_error(clave)
