"""
panel_entradas.py
Formulario de parámetros en secciones plegables, con unidades visibles,
vista previa de λ y μ por hora, errores por campo y el botón «Calcular»
siempre visible abajo.

Igual que la versión Tkinter, no valida ni calcula: entrega el texto de cada
campo (valores()) y la validación la hace calculadora_service.leer_parametros().

Los campos que no aplican al modelo (M y M máximo en población infinita) se ocultan con
su etiqueta, unidad, ayuda y el aire que los separa del campo anterior, sin dejar huecos;
conservan lo escrito y reaparecen al elegir «Finita».
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QRadioButton, QScrollArea, QVBoxLayout, QWidget)

from domain.unidades import ABREV, UNIDADES
from services import calculadora_service as cs

from . import tema
from .combo import crear_combo
from .seccion_plegable import SeccionPlegable

L = tema.LAYOUT

# Campos que solo cambian la presentación (no exigen recalcular)
CAMPOS_PRESENTACION = ("ut", "dec")


def etiqueta(texto, rol, ajustar=False):
    lbl = QLabel(texto)
    lbl.setProperty("rol", rol)
    lbl.setWordWrap(ajustar)
    return lbl


def _combo(opciones):
    """Lista que no exige el ancho de su opción más larga (el panel no se corta a la derecha)."""
    return crear_combo(opciones, minimo_contenido=6)


def _ancho_para_opciones(combo, minimo=0):
    """
    Ancho mínimo para que se lea entera la opción más larga. Se mide con la fuente de la hoja de
    estilos (ensurePolished): medida antes, con la fuente por defecto, el texto quedaba cortado.
    """
    combo.ensurePolished()
    mas_larga = max(combo.fontMetrics().horizontalAdvance(combo.itemText(i)) for i in range(combo.count()))
    combo.setMinimumWidth(max(minimo, mas_larga + L["form_relleno_combo"]))


class PanelEntradas(QWidget):
    calcular = Signal()
    exportar = Signal()
    datos_cambiaron = Signal()
    presentacion_cambio = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("PanelEntradas")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.widgets = {}         # clave -> QLineEdit / QComboBox
        self.etiquetas = {}       # clave -> QLabel del campo
        self.unidades = {}        # clave -> QLabel de unidad
        self.errores = {}         # clave -> QLabel de error (oculto)
        self.ayudas = {}          # clave -> QLabel de ayuda
        self._filas = {}          # clave -> (sección, fila de separación o None, widgets del campo)
        self.secciones = {}
        self._silencio = True     # no notificar cambios mientras se construye

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Cabecera fija; una línea bajo ella indica que la lista se desplazó
        self.cabecera = cab = QWidget()
        cab.setObjectName("CabeceraEntradas")
        cab.setAttribute(Qt.WA_StyledBackground, True)
        lc = QVBoxLayout(cab)
        lc.setContentsMargins(*L["form_margen_cabecera"])
        lc.addWidget(etiqueta("Parámetros", "titulo"))
        lc.addWidget(etiqueta("Enter calcula · los tiempos y tasas se convierten a «por hora».", "nota", True))
        lay.addWidget(cab)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        cuerpo = QWidget()
        cuerpo.setObjectName("CuerpoEntradas")
        self._cuerpo = QVBoxLayout(cuerpo)
        self._cuerpo.setContentsMargins(*L["form_margen_cuerpo"])
        self._cuerpo.setSpacing(2)
        self._grupo_modelo()
        self._grupo_llegadas_servicio()
        self._grupo_operacion()
        self._grupo_costos()
        self._grupo_analisis()
        self._grupo_presentacion()
        self._cuerpo.addStretch(1)
        self.scroll.setWidget(cuerpo)
        self.scroll.verticalScrollBar().valueChanged.connect(self._desplazado)
        lay.addWidget(self.scroll, 1)
        # Nunca más angosto que el formulario: sin barra horizontal, nada se corta
        self.setMinimumWidth(cuerpo.minimumSizeHint().width() + self.scroll.verticalScrollBar().sizeHint().width())

        lay.addWidget(self._barra_acciones())
        self._conectar()
        self.restablecer(notificar=False)
        self._silencio = False

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _seccion(self, clave, titulo, abierta=True):
        s = SeccionPlegable(titulo, abierta)
        self.secciones[clave] = s
        self._cuerpo.addWidget(s)
        return s

    def _campo(self, s, clave, texto, unidad="", ayuda="", opciones=None, unidad_combo=None, ancho_completo=False):
        """
        Fila: etiqueta | entrada o lista | unidad. Debajo: ayuda y error (oculto).
        ancho_completo: la lista va en su propia fila, a todo el ancho (opciones con textos largos).
        """
        separador = s.fila if s.fila > 0 else None
        s.separar()
        lbl = etiqueta(texto, "campo")
        s.agregar(lbl, 0, 3 if ancho_completo else 1)
        if ancho_completo:
            s.siguiente()
        if opciones is not None:
            w = _combo(opciones)
        else:
            w = QLineEdit()
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            w.returnPressed.connect(self.calcular.emit)
            w.setMinimumWidth(L["form_ancho_campo"])
        sin_unidad = opciones is not None and not unidad and unidad_combo is None
        if ancho_completo:
            s.agregar(w, 0, 3)
        else:
            s.agregar(w, 1, 2 if sin_unidad else 1)
        if opciones is not None:
            _ancho_para_opciones(w)              # ya dentro del panel: con la fuente que se verá
        propios = [lbl, w]
        if unidad_combo is not None:
            c = _combo(unidad_combo[1])
            self.widgets[unidad_combo[0]] = c
            s.agregar(c, 2, 1)
            _ancho_para_opciones(c, L["form_ancho_unidad"])
            propios.append(c)
        elif unidad:
            u = etiqueta(unidad, "unidad")
            self.unidades[clave] = u
            s.agregar(u, 2, 1)
            propios.append(u)
        s.siguiente()
        if ayuda:
            self.ayudas[clave] = a = etiqueta(ayuda, "ayuda", True)
            s.agregar(a)
            s.siguiente()
            propios.append(a)
        err = etiqueta("", "error", True)
        err.hide()
        s.agregar(err)
        s.siguiente()
        self.widgets[clave], self.etiquetas[clave], self.errores[clave] = w, lbl, err
        self._filas[clave] = (s, separador, propios)
        return w

    def _desplazado(self, valor):
        desplazado = "true" if valor > 0 else "false"
        if self.cabecera.property("desplazado") != desplazado:
            self.cabecera.setProperty("desplazado", desplazado)
            tema.refrescar(self.cabecera)

    def _subtitulo(self, s, texto):
        s.separar()
        lbl = etiqueta(texto, "subgrupo")
        s.agregar(lbl)
        s.siguiente()

    def _previa(self, s):
        lbl = etiqueta("", "previa", True)
        s.agregar(lbl)
        s.siguiente()
        return lbl

    def _grupo_modelo(self):
        s = self._seccion("modelo", "Modelo")
        s.agregar(etiqueta("Población", "campo"), 0, 1)
        radios = QWidget()
        lr = QHBoxLayout(radios)
        lr.setContentsMargins(0, 0, 0, 0)
        self.grupo_poblacion = QButtonGroup(self)
        self.radios = {}
        for texto in cs.POBLACIONES:
            rb = QRadioButton(texto)
            self.grupo_poblacion.addButton(rb)
            self.radios[texto] = rb
            lr.addWidget(rb)
        lr.addStretch(1)
        s.agregar(radios, 1, 2)
        s.siguiente()
        self._campo(s, "k", "Servidores k", "servidores", "Canales de servicio en paralelo (entero ≥ 1).")
        self._campo(s, "S", "Sistemas idénticos S", "sistemas",
                    "Ej.: 2 cajas iguales, cada una con su propia cola (cada una M/M/k). "
                    "Costos y totales se suman. Usa 1 si hay un solo sistema.")
        self._campo(s, "M", "Población M", "unidades", "Unidades de la población que pueden llegar al sistema.")

    def _grupo_llegadas_servicio(self):
        s = self._seccion("llegadas", "Llegadas y servicio")
        self._subtitulo(s, "Llegadas λ")
        self._campo(s, "lam_modo", "Dato", opciones=cs.MODO_LAM)
        self._campo(s, "lam", "Valor", unidad_combo=("lam_u", UNIDADES))
        self.lbl_previa_lam = self._previa(s)
        self._subtitulo(s, "Servicio μ (por servidor)")
        self._campo(s, "mu_modo", "Dato", opciones=cs.MODO_MU)
        self._campo(s, "mu", "Valor", unidad_combo=("mu_u", UNIDADES))
        self.lbl_previa_mu = self._previa(s)

    def _grupo_operacion(self):
        s = self._seccion("operacion", "Operación")
        self._campo(s, "H", "Horas por día", "h/día",
                    "Un «día» en las unidades equivale a estas horas (cada 4 días con 8 h/día = cada 32 h).")
        self._campo(s, "D", "Días por semana", "días", "Para los totales semanales (máximo 7).")

    def _grupo_costos(self):
        s = self._seccion("costos", "Costos e ingresos")
        # Dos renglones fijos: la columna de etiquetas no se ensancha y el panel conserva su ancho
        self._campo(s, "cS", "Costo por servidor\n(sueldo/arriendo)", unidad_combo=("cS_u", ["hora", "día"]),
                    ayuda="$ por servidor contratado; no depende de L ni de Lq.")
        # «Se cobra sobre» elige entre costo de servicio (base L) y costo de espera (base Lq): son
        # excluyentes y comparten el campo cW, cuya etiqueta y ayuda cambian con la elección.
        self._campo(s, "cW_b", "Se cobra sobre", opciones=list(cs.BASES_ESPERA), ancho_completo=True)
        e = cs.etiquetas_costo(cs.VALORES_INICIALES["cW_b"])
        self._campo(s, "cW", e.nombre, unidad_combo=("cW_u", UNIDADES), ayuda=e.ayuda)
        self._campo(s, "cI", "Servidor ocioso", "$/h")
        self._campo(s, "ing", "Ingreso por cliente", "$")
        self._campo(s, "ingF", "Fracción con ingreso", "0 a 1 o %", "Ej.: 0,3 o 30 %.")

    def _grupo_analisis(self):
        s = self._seccion("analisis", "Análisis", abierta=False)
        self._campo(s, "kmax", "k máximo", "servidores", "Rango de tablas y gráficas en función de k (≤ 200).")
        self._campo(s, "Mmax", "M máximo", "unidades", "Rango de la tabla y gráficas en función de M (2 a 300).")

    def _grupo_presentacion(self):
        s = self._seccion("presentacion", "Presentación", abierta=False)
        self._campo(s, "ut", "Mostrar tiempos en", opciones=UNIDADES)
        self._campo(s, "dec", "Decimales", opciones=cs.DECIMALES)

    def _barra_acciones(self):
        barra = QFrame()
        barra.setObjectName("Acciones")
        g = QGridLayout(barra)
        g.setContentsMargins(14, 10, 14, 12)
        g.setSpacing(6)
        self.btn_calcular = QPushButton("Calcular   (Enter)")
        self.btn_calcular.setObjectName("Primario")
        self.btn_calcular.setCursor(Qt.PointingHandCursor)
        self.btn_calcular.clicked.connect(self.calcular.emit)
        self.btn_exportar = QPushButton("Exportar CSV")
        self.btn_exportar.setObjectName("Secundario")
        self.btn_exportar.clicked.connect(self.exportar.emit)
        btn_ini = QPushButton("Valores iniciales")
        btn_ini.setObjectName("Secundario")
        btn_ini.clicked.connect(lambda: self.restablecer())
        g.addWidget(self.btn_calcular, 0, 0, 1, 2)
        g.addWidget(self.btn_exportar, 1, 0)
        g.addWidget(btn_ini, 1, 1)
        return barra

    def _conectar(self):
        for clave, w in self.widgets.items():
            destino = self._cambio_presentacion if clave in CAMPOS_PRESENTACION else self._cambio_datos
            if isinstance(w, QComboBox):
                w.currentTextChanged.connect(lambda _t, d=destino: d())
            else:
                w.textChanged.connect(lambda _t, d=destino: d())
        self.grupo_poblacion.buttonToggled.connect(lambda _b, marcado: marcado and self._cambio_datos())

    # ------------------------------------------------------------------
    # Valores
    # ------------------------------------------------------------------
    def valores(self):
        d = {c: self.get(c) for c in self.widgets}
        d["poblacion"] = self.get("poblacion")
        return d

    def get(self, clave):
        if clave == "poblacion":
            b = self.grupo_poblacion.checkedButton()
            return b.text() if b else ""
        w = self.widgets[clave]
        return w.currentText() if isinstance(w, QComboBox) else w.text()

    def poner(self, clave, texto):
        if clave == "poblacion":
            self.radios[texto].setChecked(True)
            return
        if clave == "cW_b":
            texto = cs.BASES_ESPERA_ANTIGUAS.get(texto, texto)      # estados guardados con los textos viejos
        w = self.widgets[clave]
        if isinstance(w, QComboBox):
            w.setCurrentText(texto)
        else:
            w.setText(texto)

    def cargar(self, valores, notificar=True):
        """Carga varios campos de una vez (ignora los que no son del formulario) y notifica un solo cambio."""
        self._silencio = True
        for clave, texto in valores.items():
            if clave == "poblacion" or clave in self.widgets:
                self.poner(clave, texto)
        self._silencio = False
        self._actualizar_dependencias()
        if notificar:
            self.datos_cambiaron.emit()

    @property
    def finita(self):
        return self.get("poblacion") == "Finita"

    def restablecer(self, notificar=True):
        self.limpiar_errores()
        self.cargar(cs.VALORES_INICIALES, notificar)

    def _cambio_datos(self):
        if self._silencio:
            return
        self._actualizar_dependencias()
        self.datos_cambiaron.emit()

    def _cambio_presentacion(self):
        if not self._silencio:
            self.presentacion_cambio.emit()

    def campo_visible(self, clave):
        """True si el campo se muestra (no está oculto por no aplicar al modelo)."""
        return not self.widgets[clave].isHidden()

    def _mostrar_campo(self, clave, visible):
        """Muestra u oculta el campo entero (etiqueta, entrada, unidad, ayuda y su separación)."""
        seccion, separador, propios = self._filas[clave]
        for w in propios:
            w.setVisible(visible)
        if separador is not None:
            seccion.rejilla.setRowMinimumHeight(separador, L["form_separacion_campos"] if visible else 0)
        if not visible:
            self._ocultar_error(clave)

    def _actualizar_dependencias(self):
        """Muestra solo los campos que aplican al modelo y actualiza etiquetas y vistas previas."""
        finita = self.finita
        for clave in ("M", "Mmax"):
            self._mostrar_campo(clave, cs.campo_aplica(clave, finita))
        e = cs.etiquetas_costo(self.get("cW_b"))
        self.etiquetas["cW"].setText(e.nombre)
        self.ayudas["cW"].setText(e.ayuda)
        self.etiquetas["lam"].setText("Valor (por unidad)" if finita else "Valor")
        self._vista_previa("lam", cs.MODO_LAM, self.lbl_previa_lam, "λ")
        self._vista_previa("mu", cs.MODO_MU, self.lbl_previa_mu, "μ")

    def _vista_previa(self, clave, modos, lbl, simbolo):
        es_tasa = self.get(f"{clave}_modo") == modos[0]
        unidad = self.get(f"{clave}_u")
        tasa = cs.vista_previa_tasa(es_tasa, self.get(clave), unidad, self.get("H"))
        leyenda = f"clientes por {unidad}" if es_tasa else f"{ABREV[unidad]} por cliente"
        txt = f"({leyenda})  →  {simbolo} = "
        txt += (f"{tasa:.6g}".replace(".", ",") + " /h") if tasa is not None else "—"
        if clave == "lam" and self.finita:
            txt += " por unidad"
        lbl.setText(txt)

    def habilitar_exportar(self, habilitado):
        self.btn_exportar.setEnabled(habilitado)

    # ------------------------------------------------------------------
    # Errores por campo
    # ------------------------------------------------------------------
    def ir_a_seccion(self, seccion, campo):
        """Abre la sección, la desplaza a la vista y enfoca el campo indicado."""
        s = self.secciones[seccion]
        s.abrir(True)
        w = self.widgets[campo]
        self.scroll.widget().adjustSize()
        self.scroll.ensureWidgetVisible(s.cabecera, 0, 0)
        self.scroll.ensureWidgetVisible(w, 0, 40)
        w.setFocus(Qt.OtherFocusReason)
        if isinstance(w, QLineEdit):
            w.selectAll()

    def marcar_errores(self, errores):
        """errores: lista de (clave, mensaje). Resalta, abre su sección y enfoca el primero."""
        self.limpiar_errores()
        primero = None
        for clave, mensaje in errores:
            w = self.widgets.get(clave)
            if w is None:
                continue
            if isinstance(w, QLineEdit):
                w.setProperty("error", True)
                tema.refrescar(w)
            if clave in self.errores:
                self.errores[clave].setText(f"{tema.ICONOS['error']}  {mensaje}")
                self.errores[clave].show()
            primero = primero or w
        if primero is not None:
            for s in self.secciones.values():
                if s.isAncestorOf(primero):
                    s.abrir(True)
            self.scroll.ensureWidgetVisible(primero, 0, 40)
            primero.setFocus()

    def _ocultar_error(self, clave):
        w = self.widgets.get(clave)
        if isinstance(w, QLineEdit) and w.property("error"):
            w.setProperty("error", False)
            tema.refrescar(w)
        if clave in self.errores:
            self.errores[clave].hide()

    def limpiar_errores(self):
        for clave in self.widgets:
            self._ocultar_error(clave)
