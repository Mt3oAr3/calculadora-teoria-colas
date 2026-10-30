"""
tarjetas.py
Fila de tarjetas grandes con los indicadores principales (solo en la pestaña Resultados).

Reparto: todas en una fila si caben con tamaño normal; si no, en una fila con la
versión compacta; si tampoco, en filas parejas (p. ej. 4 + 3) de columnas iguales.
Cada tarjeta emite la clave del indicador al hacer clic (abre «Cómo se calculó»).
"""
from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from services import calculadora_service as cs

from . import tema


class TarjetaIndicador(QFrame):
    clicada = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Tarjeta")
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("abre_formula", True)
        # Ancho ignorado: el reparto lo decide FilaTarjetas según el espacio disponible,
        # así las tarjetas nunca fuerzan un ancho mínimo mayor que la ventana.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.clave = ""
        self._lay = QVBoxLayout(self)
        self._lay.setSpacing(2)
        self.simbolo = QLabel()
        self.simbolo.setObjectName("TarjetaSimbolo")
        self.valor = QLabel()
        self.valor.setObjectName("TarjetaValor")
        self.nombre = QLabel()
        self.nombre.setObjectName("TarjetaNombre")
        self.nombre.setWordWrap(True)
        for w in (self.simbolo, self.valor, self.nombre):
            self._lay.addWidget(w)
        self.sombra = QGraphicsDropShadowEffect(self)
        self.sombra.setBlurRadius(tema.LAYOUT["tarjeta_sombra"])
        self.sombra.setOffset(0, 2)
        self.setGraphicsEffect(self.sombra)
        self.compactar(False)
        self.actualizar_tema()

    def actualizar_tema(self):
        self.sombra.setColor(tema.qcolor("sombra"))

    def mostrar(self, ind, texto_valor):
        self.clave = ind.clave
        self.simbolo.setText(ind.simbolo)
        self.valor.setText(texto_valor)
        self.nombre.setText(ind.nombre)
        self.setToolTip(f"{ind.ayuda}\nClic para ver cómo se calculó.")

    def _propiedad(self, nombre, valor):
        if self.property(nombre) != valor:
            self.setProperty(nombre, valor)
            tema.refrescar(self)
            for w in self.findChildren(QLabel):
                tema.refrescar(w)

    def lineas_nombre(self, ancho_tarjeta):
        """Renglones que ocupa el nombre con ese ancho de tarjeta."""
        m = self._lay.contentsMargins()
        ancho = max(1, ancho_tarjeta - m.left() - m.right())
        texto = self.nombre.fontMetrics().boundingRect(0, 0, ancho, 10000, Qt.TextWordWrap, self.nombre.text())
        return max(1, -(-texto.height() // self.nombre.fontMetrics().lineSpacing()))

    def compactar(self, si):
        self._lay.setContentsMargins(*tema.LAYOUT["tarjeta_margen_compacta" if si else "tarjeta_margen"])
        self._propiedad("compacta", "true" if si else "false")

    def marcar_vigente(self, vigente):
        self._propiedad("vigente", "true" if vigente else "false")

    def marcar_activa(self, activa):
        self._propiedad("activa", "true" if activa else "false")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.clave and self.rect().contains(e.position().toPoint()):
            self.clicada.emit(self.clave)
        super().mouseReleaseEvent(e)


def reparto(n, ancho):
    """(columnas, compacta) para n tarjetas en `ancho` px."""
    esp = tema.LAYOUT["tarjetas_espacio"]
    por_tarjeta = (ancho - esp * (n - 1)) / n if n else 0
    if por_tarjeta >= tema.LAYOUT["tarjeta_ancho_normal"]:
        return n, False
    if por_tarjeta >= tema.LAYOUT["tarjeta_ancho_compacta"]:
        return n, True
    filas = 2
    while True:
        cols = -(-n // filas)                      # columnas parejas: 7 → 4 + 3, 8 → 4 + 4
        if (ancho - esp * (cols - 1)) / cols >= tema.LAYOUT["tarjeta_ancho_compacta"] or cols == 1:
            por = (ancho - esp * (cols - 1)) / cols
            return cols, por < tema.LAYOUT["tarjeta_ancho_normal"]
        filas += 1


class FilaTarjetas(QWidget):
    indicador_clicado = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.rejilla = QGridLayout(self)
        # márgenes para que la sombra de las tarjetas no se recorte
        self.rejilla.setContentsMargins(2, 2, 2, 6)
        self.rejilla.setSpacing(tema.LAYOUT["tarjetas_espacio"])
        self.tarjetas = []
        self._visibles = 0
        self._disposicion = None
        self._activa = None

    def _tarjetas(self, n):
        while len(self.tarjetas) < n:
            t = TarjetaIndicador()
            t.clicada.connect(self.indicador_clicado.emit)
            self.tarjetas.append(t)
        self._visibles = n
        self._disposicion = None
        self._reubicar()
        self.setVisible(n > 0)
        return self.tarjetas[:n]

    @property
    def columnas(self):
        return self._disposicion[0] if self._disposicion else 0

    def _reubicar(self):
        n = self._visibles
        if n == 0:
            return
        m = self.rejilla.contentsMargins()
        disp = reparto(n, self.width() - m.left() - m.right())
        if disp == self._disposicion:
            return
        self._disposicion = disp
        cols, compacta = disp
        for t in self.tarjetas:
            self.rejilla.removeWidget(t)
            t.hide()
        for c in range(self.rejilla.columnCount()):
            self.rejilla.setColumnStretch(c, 0)
        for i, t in enumerate(self.tarjetas[:n]):
            t.compactar(compacta)
            self.rejilla.addWidget(t, i // cols, i % cols)
            t.show()
        for c in range(cols):
            self.rejilla.setColumnStretch(c, 1)       # columnas iguales: tarjetas del mismo ancho
        self._igualar_alturas()

    def _igualar_alturas(self):
        """Todas las tarjetas igual de altas y con lugar para el nombre completo (sin cortes)."""
        n, cols = self._visibles, self.columnas
        if not n:
            return
        m = self.rejilla.contentsMargins()
        esp = tema.LAYOUT["tarjetas_espacio"]
        ancho = (self.width() - m.left() - m.right() - esp * (cols - 1)) // cols
        visibles = self.tarjetas[:n]
        lineas = max(t.lineas_nombre(ancho) for t in visibles)
        for t in visibles:
            t.nombre.setMinimumHeight(lineas * t.nombre.fontMetrics().lineSpacing())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reubicar()
        self._igualar_alturas()

    def mostrar(self, esc, fmt):
        indicadores = cs.indicadores_principales(esc)
        for tarjeta, ind in zip(self._tarjetas(len(indicadores)), indicadores):
            # Sin el sufijo de conteo («clientes», «unidades»): la unidad ya está en el nombre de la tarjeta
            tarjeta.mostrar(ind, fmt.texto(replace(ind.valor, sufijo="")))
            tarjeta.marcar_vigente(True)
        self.marcar_activa(self._activa)
        self._igualar_alturas()

    def limpiar(self):
        self._tarjetas(0)

    def marcar_desactualizado(self, desactualizado):
        """Atenúa los valores (el texto del aviso lo da el banner global)."""
        for t in self.tarjetas[:self._visibles]:
            t.marcar_vigente(not desactualizado)

    def marcar_activa(self, clave):
        """Resalta la tarjeta cuya fórmula está abierta (None: ninguna)."""
        self._activa = clave
        for t in self.tarjetas:
            t.marcar_activa(clave is not None and t.clave == clave)

    def actualizar_tema(self):
        for t in self.tarjetas:
            t.actualizar_tema()
