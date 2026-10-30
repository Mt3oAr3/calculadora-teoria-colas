"""
vista_comparacion.py
Página «Comparar k y M»: condición de búsqueda, leyenda de colores y las
tablas en función de k y de M (calculadas en comparacion_service).

Clic en una fila -> formula_pedida(escenario de esa fila, clave de la fórmula, métrica, fila):
«Cómo se calculó» de la métrica elegida en la barra para ese k o M. La fila queda
resaltada y, si cambia la métrica o el cálculo, se vuelve a pedir la fórmula de la misma
fila; si la fila ya no está, fila_perdida (la ventana cierra el panel).

La lista de métricas depende de la población: en infinita no se ofrecen las que solo aplican
a población finita ni P(n≥k), que ahí es Pk. Al cambiar de población se conserva la métrica
elegida si sigue disponible.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from domain.errores import ErrorEntrada
from services import calculadora_service as cs
from services import comparacion_service as cmp

from . import tema
from .chips import FilaChips
from .combo import crear_combo
from .info_box import InfoBox
from .vista_tabla import VistaTabla, encabezado_pagina


def _muestra(tipo, texto):
    caja = QWidget()
    lay = QHBoxLayout(caja)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    m = QLabel()
    m.setProperty("rol", "muestra")
    m.setProperty("tipo", tipo)
    m.setFixedSize(16, 12)
    lay.addWidget(m)
    t = QLabel(texto)
    t.setProperty("rol", "leyenda")
    lay.addWidget(t)
    return caja


class PaginaComparacion(QWidget):
    formula_pedida = Signal(object, str, str, str)    # escenario de la fila, clave, métrica, fila ("k = 3")
    fila_perdida = Signal()                           # la fila del panel ya no está en la comparación

    def __init__(self, unidad_tiempo, padre=None):
        super().__init__(padre)
        self.setObjectName("Pagina")
        self.esc = self.fmt = None
        self._unidad_tiempo = unidad_tiempo      # función que devuelve la unidad elegida
        self.res_k = self.res_M = None
        self.fila = None                         # (tipo, valor) de la fila con el panel abierto, o None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(encabezado_pagina("Comparar k y M",
                                        "Busca el menor k (o el mayor M) que cumple una condición y el k de menor "
                                        "costo total. Clic en el encabezado de una columna para ordenar."))

        lbl = QLabel("Condición de búsqueda")
        lbl.setProperty("rol", "subgrupo")
        lay.addWidget(lbl)
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.cb_metrica = crear_combo(cmp.metricas_disponibles(False), cmp.texto_inicial(False), minimo_contenido=14)
        # Cambiar la métrica con el panel abierto actualiza la fórmula de la fila (no cierra el panel)
        self.cb_metrica.setProperty("abre_formula", True)
        self.cb_op = crear_combo(cmp.OPERADORES, "≤")
        self.ent_lim = QLineEdit("0,5")
        self.ent_lim.setFixedWidth(70)
        self.ent_lim.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_unidad = QLabel("")
        self.lbl_unidad.setProperty("rol", "unidad")
        self.lbl_unidad.setMinimumWidth(30)
        btn = QPushButton("Buscar")
        for w in (self.cb_metrica, self.cb_op, self.ent_lim, self.lbl_unidad, btn):
            fila.addWidget(w)
        fila.setStretch(0, 1)
        lay.addLayout(fila)
        self.lbl_err = QLabel("")
        self.lbl_err.setProperty("rol", "error")
        self.lbl_err.setWordWrap(True)
        self.lbl_err.hide()
        lay.addWidget(self.lbl_err)
        btn.clicked.connect(self.actualizar)
        self.ent_lim.returnPressed.connect(self.actualizar)
        self.cb_metrica.currentTextChanged.connect(lambda _t: self.actualizar())
        self.cb_op.currentTextChanged.connect(lambda _t: self.actualizar())

        leyenda = QHBoxLayout()
        leyenda.setSpacing(16)
        leyenda.addWidget(_muestra("cumple", "Cumple la condición"))
        leyenda.addWidget(_muestra("mejor", "Menor costo total"))
        leyenda.addStretch(1)
        lay.addLayout(leyenda)
        self.info = InfoBox(self._texto_info("Lq"))
        lay.addWidget(self.info)

        # Barridos largos (k máximo hasta 200, M hasta 300): la tabla no pasa de tabla_filas_max filas y
        # tiene su propia barra vertical; el encabezado queda siempre a la vista.
        filas_max = tema.LAYOUT["tabla_filas_max"]
        self.tabla_k = VistaTabla("En función de k", ordenable=True, filas_min=3, filas_max=filas_max)
        self.tabla_M = VistaTabla("En función de M", ordenable=True, filas_min=3, filas_max=filas_max)
        self.chips_k, self.chips_M = FilaChips(), FilaChips()
        self.tabla_k.agregar_bajo_titulo(self.chips_k)
        self.tabla_M.agregar_bajo_titulo(self.chips_M)
        # Población infinita: en lugar de un bloque vacío para M, una sola línea informativa
        self.info_M = InfoBox("La tabla en función de M solo aplica a población finita.")
        self.info_M.hide()
        lay.addWidget(self.tabla_k)
        lay.addWidget(self.tabla_M)
        lay.addWidget(self.info_M)
        lay.addStretch(1)
        for tabla in (self.tabla_k, self.tabla_M):
            tabla.fila_clicada.connect(self._fila_clicada)
        for chips in (self.chips_k, self.chips_M):
            chips.elegido.connect(lambda tipo, valor: self._fila_clicada(cmp.clave_fila(tipo, valor)))

    @staticmethod
    def _texto_info(base):
        return (f"Negrita: valor actual, y las columnas k, {base} (base del costo por cliente) y CT. Probabilidades "
                "en decimal; ρ en %. Los tiempos usan la unidad de «Mostrar tiempos en». "
                "Verde: el k de menor costo total.")

    def mostrar(self, esc, fmt):
        self.esc, self.fmt = esc, fmt
        self._poner_metricas(esc.p.finita)
        self.info.setText(self._texto_info(cs.etiquetas_costo(esc.p.cfg).base))
        self.actualizar()

    def _poner_metricas(self, finita):
        """Métricas de la población elegida; conserva la elegida si sigue disponible (si no, la inicial)."""
        textos = cmp.metricas_disponibles(finita)
        cb = self.cb_metrica
        if textos == [cb.itemText(i) for i in range(cb.count())]:
            return
        try:
            clave = cmp.metrica_por_nombre(cb.currentText()).clave
        except KeyError:
            clave = None
        elegido = next((t for t in textos if cmp.metrica_por_nombre(t).clave == clave), cmp.texto_inicial(finita))
        cb.blockSignals(True)
        cb.clear()
        cb.addItems(textos)
        cb.setCurrentText(elegido)
        cb.blockSignals(False)
        vista = cb.view()
        vista.setMinimumWidth(vista.sizeHintForColumn(0) + tema.LAYOUT["combo_lista_extra"])

    def _marcar(self, error):
        self.ent_lim.setProperty("error", error)
        tema.refrescar(self.ent_lim)

    def actualizar(self):
        if self.esc is None:
            return
        try:
            cond = cmp.leer_condicion(self.cb_metrica.currentText(), self.cb_op.currentText(),
                                      self.ent_lim.text(), self._unidad_tiempo())
        except ErrorEntrada as e:
            self._marcar(True)
            self.lbl_err.setText(e.errores[0][1])
            self.lbl_err.show()
            self.res_k = self.res_M = None
            self.chips_k.poner([])
            self.chips_M.poner([])
            self.tabla_k.limpiar("Corrige la condición para ver la comparación.")
            self.tabla_M.limpiar("")
            self._perder_fila()
            return
        self._marcar(False)
        self.lbl_err.hide()
        self.lbl_unidad.setText(self.fmt.abrev_tiempo if cond.metrica.es_tiempo else "")
        self.res_k = cmp.comparar_k(self.esc, cond, self.fmt)
        self.res_M = cmp.comparar_M(self.esc, cond, self.fmt)
        self.chips_k.poner(self.res_k.destacados, self._estilos(self.res_k))
        self.tabla_k.mostrar(self.res_k.tabla, self.fmt)
        finita = self.esc.p.finita
        self.tabla_M.setVisible(finita)
        self.info_M.setVisible(not finita)
        self.chips_M.poner(self.res_M.destacados if finita else [], {0: "cumple"})
        self.tabla_M.mostrar(self.res_M.tabla, self.fmt)
        if self.fila is not None:
            self._pedir_formula()
        else:                       # sin fila elegida, cada tabla muestra su primera fila que cumple
            for tabla, res, tipo in ((self.tabla_k, self.res_k, "k"), (self.tabla_M, self.res_M, "M")):
                if res.valor_que_cumple is not None:
                    tabla.desplazar_a_clave(cmp.clave_fila(tipo, res.valor_que_cumple))

    @staticmethod
    def _estilos(res):
        """Aspecto de cada chip: el que cumple como las filas que cumplen, el de menor costo en verde."""
        estilos = {}
        for i, d in enumerate(res.destacados):
            if d.texto.startswith("Menor costo"):
                estilos[i] = "mejor"
            elif d.texto.startswith(("Menor k", "Ningún")):
                estilos[i] = "cumple"
        return estilos

    # ------------------------------------------------------------------
    # «Cómo se calculó» de una fila
    # ------------------------------------------------------------------
    def _fila_clicada(self, clave):
        fila = cmp.leer_clave_fila(clave)
        if fila is not None and self.esc is not None:
            self.fila = fila
            self._pedir_formula()

    def _pedir_formula(self):
        """Pide la fórmula de la métrica de la barra para la fila elegida (con el escenario de esa fila)."""
        tipo, valor = self.fila
        tabla = self.tabla_k if tipo == "k" else self.tabla_M
        try:
            metrica = cmp.metrica_por_nombre(self.cb_metrica.currentText())
            esc = cmp.escenario_de_fila(self.esc, tipo, valor)
        except (KeyError, ValueError):
            self._perder_fila()
            return
        if not tabla.seleccionar_clave(cmp.clave_fila(tipo, valor)):
            self._perder_fila()
            return
        self.formula_pedida.emit(esc, cmp.clave_formula(metrica), self.cb_metrica.currentText(),
                                 cmp.describir_fila(tipo, valor))

    def _perder_fila(self):
        if self.fila is not None:
            self.soltar_fila()
            self.fila_perdida.emit()

    def soltar_fila(self):
        """El panel se cerró o pasó a otra fórmula: la fila deja de estar resaltada."""
        self.fila = None
        self.tabla_k.quitar_seleccion()
        self.tabla_M.quitar_seleccion()

    def tablas_para_exportar(self):
        """Tablas «Variando k» y «Variando M». Lanza ErrorEntrada si la condición no es válida."""
        if self.res_k is None:
            raise ErrorEntrada([("cond_v", "La condición de comparación no es válida; corrígela antes de exportar.")])
        return [self.res_k.tabla, self.res_M.tabla]

    def limpiar(self, mensaje):
        self.esc = None
        self.fila = None
        self.res_k = self.res_M = None
        self.chips_k.poner([])
        self.chips_M.poner([])
        self.tabla_k.limpiar(mensaje)
        self.tabla_M.limpiar("")

    def repintar(self):
        self.tabla_k.repintar()
        self.tabla_M.repintar()
