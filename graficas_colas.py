"""
graficas_colas.py
Dibuja las gráficas de tendencia sobre una matplotlib.figure.Figure.
No depende de Tkinter, así que también sirve para guardar PNG desde un script.
"""
import math
import modelos_colas as mc

GRAFICAS = [
    ("P0_k",    "Probabilidad de sistema vacío en función de k"),
    ("Pesp_k",  "Probabilidad de esperar en función de k"),
    ("Pno_k",   "Probabilidad de no esperar en función de k"),
    ("Wq_k",    "Tiempo de espera en función de k"),
    ("W_k",     "Tiempo en el sistema en función de k"),
    ("Costo_k", "Análisis de costos en función de k: CT(TE), CT(S), CT"),
    ("Costo_M", "PFCS - PFCM: análisis de costos en función de M"),
    ("Pesp_M",  "Probabilidad de esperar en función de M"),
    ("Pno_M",   "Probabilidad de no esperar en función de M"),
    ("Wq_M",    "Tiempo de espera en función de M"),
    ("W_M",     "Tiempo en el sistema en función de M"),
]

COLORES = {"a": "#1D5CC2", "b": "#C98300", "c": "#23806F", "act": "#7A8699", "min": "#B3261E"}
ABREV = {"minuto": "min", "hora": "h", "día": "día"}


def _limpio(v):
    return v if (v is not None and isinstance(v, (int, float)) and math.isfinite(v)) else float("nan")


def _etiquetar(ax, xs, ys, decimales=3):
    if len(xs) > 16:
        return
    for x, y in zip(xs, ys):
        if math.isfinite(y):
            ax.annotate(f"{y:.{decimales}f}", (x, y), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=8, color="#334")


def dibujar(fig, gid, ctx):
    """
    ctx = {
      'finita': bool, 'barrido_k': [...], 'barrido_M': [...],
      'k': k actual, 'M': M actual, 'H': horas/día,
      'unidad_tiempo': 'minuto'|'hora'|'día', 'cfg': costos, 'subtitulo': str
    }
    """
    fig.clear()
    ax = fig.add_subplot(111)
    titulo = dict(GRAFICAS).get(gid, gid)
    por_M = gid.endswith("_M")

    if por_M and not ctx["finita"]:
        ax.axis("off")
        ax.text(0.5, 0.5, "Esta gráfica es solo para población finita (PFCS / PFCM).\n"
                "Cambia la población a 'Finita' e indica M.",
                ha="center", va="center", fontsize=12, color="#556275")
        fig.suptitle(titulo, fontsize=12, fontweight="bold")
        return

    datos = ctx["barrido_M"] if por_M else ctx["barrido_k"]
    datos = [r for r in datos if r.get("ok")]
    if not datos:
        ax.axis("off")
        ax.text(0.5, 0.5, "No hay datos válidos para graficar.", ha="center", va="center")
        return

    xs = [r["M"] if por_M else r["k"] for r in datos]
    x_act = ctx["M"] if por_M else ctx["k"]
    xlabel = "Tamaño de la población M" if por_M else "Número de servidores k"
    u = ctx["unidad_tiempo"]
    f_t = 1.0 / mc.horas_por_unidad(u, ctx["H"])   # horas -> unidad elegida

    if gid in ("P0_k",):
        ys = [_limpio(r["P0"]) for r in datos]
        ax.plot(xs, ys, marker="o", color=COLORES["a"], label="P0")
        _etiquetar(ax, xs, ys)
        ax.set_ylabel("Probabilidad")
        ax.set_ylim(0, 1.05)
    elif gid in ("Pesp_k", "Pesp_M"):
        ys = [_limpio(r["frac_espera"]) for r in datos]
        ax.plot(xs, ys, marker="o", color=COLORES["b"], label="Probabilidad de esperar")
        _etiquetar(ax, xs, ys)
        ax.set_ylabel("Probabilidad")
        ax.set_ylim(0, 1.05)
    elif gid in ("Pno_k", "Pno_M"):
        ys = [_limpio(r["frac_no_espera"]) for r in datos]
        ax.plot(xs, ys, marker="o", color=COLORES["c"], label="Probabilidad de no esperar")
        _etiquetar(ax, xs, ys)
        ax.set_ylabel("Probabilidad")
        ax.set_ylim(0, 1.05)
    elif gid in ("Wq_k", "Wq_M"):
        ys = [_limpio(r["Wq"]) * f_t for r in datos]
        ax.plot(xs, ys, marker="o", color=COLORES["b"], label="Wq")
        _etiquetar(ax, xs, ys)
        ax.set_ylabel(f"Tiempo en cola ({ABREV[u]})")
    elif gid in ("W_k", "W_M"):
        ys = [_limpio(r["W"]) * f_t for r in datos]
        ax.plot(xs, ys, marker="o", color=COLORES["a"], label="W")
        _etiquetar(ax, xs, ys)
        ax.set_ylabel(f"Tiempo en el sistema ({ABREV[u]})")
    elif gid in ("Costo_k", "Costo_M"):
        cs = [mc.costos(r, ctx["H"], ctx["cfg"]) for r in datos]
        te = [c["ct_te"] + c["ct_ocio"] for c in cs]
        s = [c["ct_s"] for c in cs]
        ct = [c["ct"] for c in cs]
        ax.plot(xs, te, marker="o", color=COLORES["b"], label="CT(TE) tiempo de espera"
                + (" + ocio" if any(c["ct_ocio"] for c in cs) else ""))
        ax.plot(xs, s, marker="s", color=COLORES["c"], label="CT(S) servidores")
        ax.plot(xs, ct, marker="D", color=COLORES["a"], linewidth=2.2, label="CT costo total")
        if any(v > 0 for v in ct) and not por_M:
            i = min(range(len(ct)), key=lambda j: ct[j])
            ax.scatter([xs[i]], [ct[i]], s=140, facecolors="none", edgecolors=COLORES["min"],
                       linewidths=2, zorder=5, label=f"Mínimo CT en {'M' if por_M else 'k'} = {xs[i]}")
            ax.annotate(f"$ {ct[i]:,.2f}", (xs[i], ct[i]), textcoords="offset points",
                        xytext=(0, -16), ha="center", fontsize=9, color=COLORES["min"])
        elif not any(v > 0 for v in ct):
            ax.text(0.5, 0.92, "Ingresa los costos en el panel para ver las tendencias.",
                    transform=ax.transAxes, ha="center", fontsize=9, color="#B3261E")
        ax.set_ylabel("Costo por día ($)")

    if x_act in xs:
        ax.axvline(x_act, linestyle="--", color=COLORES["act"], alpha=0.7,
                   label=f"Valor actual = {x_act}")
    ax.set_xlabel(xlabel)
    if len(xs) <= 30:
        ax.set_xticks(xs)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="best")
    fig.suptitle(titulo, fontsize=12, fontweight="bold")
    if ctx.get("subtitulo"):
        ax.set_title(ctx["subtitulo"], fontsize=9, color="#556275")
    if fig.get_layout_engine() is None:
        fig.tight_layout()
