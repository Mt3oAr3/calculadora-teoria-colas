"""
graficas_colas.py
Dibuja las gráficas de tendencia sobre una matplotlib.figure.Figure.
No depende de Tkinter: también sirve para guardar PNG desde un script.

Cada gráfica tiene un identificador estable (se usa en los nombres de archivo
NN_id.png al exportar), una categoría y si es en función de k o de M.
"""
import math
from dataclasses import dataclass

from domain import costos as dc
from domain.unidades import ABREV, horas_por_unidad


@dataclass(frozen=True)
class Grafica:
    gid: str
    titulo: str
    categoria: str          # 'Probabilidades' | 'Tiempos' | 'Costos'

    @property
    def por_M(self):
        return self.gid.endswith("_M")


# El orden se conserva respecto de la versión original (define la numeración de los PNG).
GRAFICAS = [
    Grafica("P0_k",    "Probabilidad de sistema vacío en función de k", "Probabilidades"),
    Grafica("Pesp_k",  "Probabilidad de esperar en función de k", "Probabilidades"),
    Grafica("Pno_k",   "Probabilidad de no esperar en función de k", "Probabilidades"),
    Grafica("Wq_k",    "Tiempo de espera en cola en función de k", "Tiempos"),
    Grafica("W_k",     "Tiempo en el sistema en función de k", "Tiempos"),
    Grafica("Costo_k", "Costos diarios en función de k: CT(TE), CT(S), CT", "Costos"),
    Grafica("Costo_M", "Costos diarios en función de M (PFCS / PFCM)", "Costos"),
    Grafica("Pesp_M",  "Probabilidad de esperar en función de M", "Probabilidades"),
    Grafica("Pno_M",   "Probabilidad de no esperar en función de M", "Probabilidades"),
    Grafica("Wq_M",    "Tiempo de espera en cola en función de M", "Tiempos"),
    Grafica("W_M",     "Tiempo en el sistema en función de M", "Tiempos"),
]
CATEGORIAS = ["Probabilidades", "Tiempos", "Costos"]
_POR_ID = {g.gid: g for g in GRAFICAS}

# Paleta de la marca: rojo y verde para las dos primeras series, negro/grises para el resto
# (las series también se distinguen por el marcador: o, s, D).
SERIE = ["#ea0f02", "#00841d", "#3d3d3d"]
TINTA = "#000000"
TINTA_2 = "#4d4d4d"
TINTA_3 = "#8c8c8c"
REJILLA = "#e6e6e6"
FONDO = "#ffffff"


def grafica(gid):
    return _POR_ID[gid]


def _limpio(v):
    return v if (v is not None and isinstance(v, (int, float)) and math.isfinite(v)) else float("nan")


def _num(x, d):
    """Número con coma decimal y punto de miles, como en las tablas."""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _etiquetar(ax, xs, ys, decimales=3, maximo=12):
    """Rotula los valores solo si hay pocos puntos, para no saturar."""
    if len(xs) > maximo:
        return
    for x, y in zip(xs, ys):
        if math.isfinite(y):
            ax.annotate(_num(y, decimales), (x, y), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8, color=TINTA_2)


def _estilo_ejes(ax):
    ax.set_facecolor(FONDO)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(TINTA_3)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(axis="y", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)


def _mensaje(fig, ax, titulo, texto):
    ax.axis("off")
    ax.text(0.5, 0.5, texto, ha="center", va="center", fontsize=11, color=TINTA_2)
    fig.suptitle(titulo, fontsize=12, fontweight="bold", color=TINTA)


def _linea(ax, xs, ys, color, etiqueta, marcador="o", ancho=2.0):
    ax.plot(xs, ys, marker=marcador, markersize=5, color=color, linewidth=ancho, label=etiqueta,
            markeredgecolor=FONDO, markeredgewidth=1.2)


def dibujar(fig, gid, ctx):
    """
    ctx = {
      'finita': bool, 'barrido_k': [...], 'barrido_M': [...],
      'k': k actual, 'M': M actual, 'H': horas/día,
      'unidad_tiempo': 'minuto'|'hora'|'día', 'cfg': costos, 'subtitulo': str,
      'mostrar_valores': bool (opcional, por defecto True)
    }
    """
    fig.clear()
    fig.set_facecolor(FONDO)
    ax = fig.add_subplot(111)
    g = grafica(gid)
    titulo = g.titulo
    por_M = g.por_M

    if por_M and not ctx["finita"]:
        _mensaje(fig, ax, titulo, "Esta gráfica es solo para población finita (PFCS / PFCM).\n"
                                  "Cambia la población a «Finita» e indica M.")
        return

    datos = [r for r in (ctx["barrido_M"] if por_M else ctx["barrido_k"]) if r.get("ok")]
    if not datos:
        _mensaje(fig, ax, titulo, "No hay datos válidos para graficar.")
        return

    _estilo_ejes(ax)
    rotular = ctx.get("mostrar_valores", True)
    xs = [r["M"] if por_M else r["k"] for r in datos]
    x_act = ctx["M"] if por_M else ctx["k"]
    xlabel = "Tamaño de la población M" if por_M else "Número de servidores k"
    u = ctx["unidad_tiempo"]
    f_t = 1.0 / horas_por_unidad(u, ctx["H"])   # horas -> unidad elegida
    leyenda = False

    if gid in ("P0_k", "Pesp_k", "Pesp_M", "Pno_k", "Pno_M"):
        clave = {"P0": "P0", "Pesp": "frac_espera", "Pno": "frac_no_espera"}[gid.split("_")[0]]
        ys = [_limpio(r[clave]) for r in datos]
        _linea(ax, xs, ys, SERIE[0], None)
        if rotular:
            _etiquetar(ax, xs, ys)
        ax.set_ylabel("Probabilidad", color=TINTA_2)
        ax.set_ylim(0, 1.08)
    elif gid in ("Wq_k", "Wq_M", "W_k", "W_M"):
        clave = gid.split("_")[0]
        ys = [_limpio(r[clave]) * f_t for r in datos]
        _linea(ax, xs, ys, SERIE[0], None)
        if rotular:
            _etiquetar(ax, xs, ys)
        nombre = "Tiempo en cola Wq" if clave == "Wq" else "Tiempo en el sistema W"
        ax.set_ylabel(f"{nombre} ({ABREV[u]})", color=TINTA_2)
        ax.set_ylim(bottom=0)
    elif gid in ("Costo_k", "Costo_M"):
        cs = [dc.costos(r, ctx["H"], ctx["cfg"]) for r in datos]
        ct = [c["ct"] for c in cs]
        if not any(v > 0 for v in ct):
            _mensaje(fig, ax, titulo, "Ingresa los costos en el panel de parámetros\n"
                                      "(grupo «Costos e ingresos») para ver esta gráfica.")
            return
        hay_ocio = any(c["ct_ocio"] for c in cs)
        _linea(ax, xs, [c["ct"] for c in cs], SERIE[0], "CT costo total", "o", 2.4)
        _linea(ax, xs, [c["ct_te"] + c["ct_ocio"] for c in cs], SERIE[1],
               "CT(TE) tiempo de espera" + (" + ocio" if hay_ocio else ""), "s")
        _linea(ax, xs, [c["ct_s"] for c in cs], SERIE[2], "CT(S) servidores", "D")
        leyenda = True
        if not por_M:
            i = min(range(len(ct)), key=lambda j: ct[j])
            ax.scatter([xs[i]], [ct[i]], s=150, facecolors="none", edgecolors=TINTA,
                       linewidths=1.6, zorder=5, label=f"Mínimo CT en k = {xs[i]}")
            ax.annotate(f"$ {_num(ct[i], 2)}", (xs[i], ct[i]), textcoords="offset points",
                        xytext=(0, -18), ha="center", fontsize=9, color=TINTA, fontweight="bold")
        ax.set_ylabel("Costo por día ($)", color=TINTA_2)
        ax.set_ylim(bottom=0)

    if x_act in xs:
        ax.axvline(x_act, linestyle="--", color=TINTA_3, linewidth=1.2, label=f"Valor actual = {x_act}")
        leyenda = True
    ax.set_xlabel(xlabel, color=TINTA_2)
    if len(xs) <= 30:
        ax.set_xticks(xs)
    if leyenda:
        # Leyenda fuera del área de datos para no tapar las curvas
        ax.legend(fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, labelcolor=TINTA)
    fig.suptitle(titulo, fontsize=12, fontweight="bold", color=TINTA)
    if ctx.get("subtitulo"):
        ax.set_title(ctx["subtitulo"], fontsize=9, color=TINTA_2)
    if fig.get_layout_engine() is None:
        fig.tight_layout()
