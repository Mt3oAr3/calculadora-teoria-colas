"""
tarjetas.py
Encabezado de resultados: modelo (notación de Kendall), insignia de estado,
mensaje de estabilidad y tarjetas grandes de los indicadores principales.

Las tarjetas se reparten en tantas columnas como quepan y emiten la clave del
indicador al hacer clic (abre el panel «Cómo se calculó»).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel,
                               QSizePolicy, QVBoxLayout, QWidget)

from services import calculadora_service as cs

from . import tema

ANCHO_MIN_TARJETA = 138
TEXTO_INSIGNIA = {"ok": "● Estable", "aviso": "● Inestable", "error": "● Sin resultados",
                  "info": "● Desactualizado"}
MENSAJE_DESACTUALIZADO = ("Los parámetros cambiaron desde el último cálculo: los valores mostrados corresponden "
                          "a los datos anteriores. Pulsa «Calcular» (Enter o F5) para actualizarlos.")


class TarjetaIndicador(QFrame):
    clicada = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Tarjeta")
        self.setCursor(Qt.PointingHandCursor)
        # Ancho ignorado: el número de columnas lo decide PanelResumen según el espacio disponible,
        # así las tarjetas nunca fuerzan un ancho mínimo mayor que la ventana.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.clave = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(2)
        self.simbolo = QLabel()
        self.simbolo.setObjectName("TarjetaSimbolo")
        self.valor = QLabel()
        self.valor.setObjectName("TarjetaValor")
        self.nombre = QLabel()
        self.nombre.setObjectName("TarjetaNombre")
        self.nombre.setWordWrap(True)
        for w in (self.simbolo, self.valor, self.nombre):
            lay.addWidget(w)
        self.sombra = QGraphicsDropShadowEffect(self)
        self.sombra.setBlurRadius(18)
        self.sombra.setOffset(0, 2)
        self.setGraphicsEffect(self.sombra)
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

    def marcar_vigente(self, vigente):
        self._propiedad("vigente", "true" if vigente else "false")

    def marcar_activa(self, activa):
        self._propiedad("activa", "true" if activa else "false")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.clave and self.rect().contains(e.position().toPoint()):
            self.clicada.emit(self.clave)
        super().mouseReleaseEvent(e)


class PanelResumen(QWidget):
    indicador_clicado = Signal(str)

    def __init__(self, padre=None):
        super().__init__(padre)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        cab = QHBoxLayout()
        cab.setSpacing(12)
        self.lbl_modelo = QLabel("—")
        self.lbl_modelo.setObjectName("Kendall")
        self.lbl_desc = QLabel("")
        self.lbl_desc.setObjectName("Descripcion")
        self.lbl_desc.setWordWrap(True)
        self.insignia = QLabel("")
        self.insignia.setProperty("rol", "insignia")
        cab.addWidget(self.lbl_modelo, 0, Qt.AlignVCenter)
        cab.addWidget(self.lbl_desc, 1, Qt.AlignVCenter)
        cab.addWidget(self.insignia, 0, Qt.AlignVCenter)
        lay.addLayout(cab)

        self.mensaje = QLabel("")
        self.mensaje.setProperty("rol", "mensaje")
        self.mensaje.setWordWrap(True)
        lay.addWidget(self.mensaje)

        self.zona = QWidget()
        self.rejilla = QGridLayout(self.zona)
        # márgenes para que la sombra de las tarjetas no se recorte
        self.rejilla.setContentsMargins(2, 2, 2, 6)
        self.rejilla.setSpacing(10)
        lay.addWidget(self.zona)
        self.tarjetas = []
        self._visibles = 0
        self._columnas = 0
        self._activa = None
        self._nivel_vigente = None

    # ------------------------------------------------------------------
    def _estado(self, nivel, texto):
        for w in (self.insignia, self.mensaje):
            w.setProperty("nivel", nivel)
            tema.refrescar(w)
        self.insignia.setText(TEXTO_INSIGNIA[nivel])
        self.mensaje.setText(texto)

    def _tarjetas(self, n):
        while len(self.tarjetas) < n:
            t = TarjetaIndicador()
            t.clicada.connect(self.indicador_clicado.emit)
            self.tarjetas.append(t)
        self._visibles = n
        self._columnas = 0
        self._reubicar()
        self.zona.setVisible(n > 0)
        return self.tarjetas[:n]

    def _reubicar(self):
        """Reparte las tarjetas visibles en las columnas que caben a lo ancho."""
        n = self._visibles
        if n == 0:
            return
        cols = max(2, min(n, self.width() // ANCHO_MIN_TARJETA))
        if n > cols:
            cols = -(-n // -(-n // cols))      # filas parejas: 8 → 4+4 y no 7+1
        if cols == self._columnas:
            return
        self._columnas = cols
        for t in self.tarjetas:
            self.rejilla.removeWidget(t)
            t.hide()
        for c in range(self.rejilla.columnCount()):
            self.rejilla.setColumnStretch(c, 0)
        for i, t in enumerate(self.tarjetas[:n]):
            self.rejilla.addWidget(t, i // cols, i % cols)
            t.show()
        for c in range(cols):
            self.rejilla.setColumnStretch(c, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reubicar()

    # ------------------------------------------------------------------
    def mostrar(self, esc, fmt):
        self.lbl_modelo.setText(esc.kendall)
        self.lbl_desc.setText(esc.descripcion)
        self._nivel_vigente = ("ok" if esc.estable else "aviso", cs.mensaje_estado(esc, fmt))
        self._estado(*self._nivel_vigente)
        indicadores = cs.indicadores_principales(esc)
        for tarjeta, ind in zip(self._tarjetas(len(indicadores)), indicadores):
            tarjeta.mostrar(ind, fmt.texto(ind.valor))
            tarjeta.marcar_vigente(True)
        self.marcar_activa(self._activa)

    def limpiar(self, mensaje):
        """Sin resultados vigentes (error de entrada, de modelo o inesperado)."""
        self.lbl_modelo.setText("—")
        self.lbl_desc.setText("")
        self._estado("error", mensaje)
        self._tarjetas(0)

    def marcar_desactualizado(self, desactualizado):
        """Atenúa los valores y avisa que los parámetros cambiaron desde el último cálculo."""
        for t in self.tarjetas[:self._visibles]:
            t.marcar_vigente(not desactualizado)
        if desactualizado:
            self._estado("info", MENSAJE_DESACTUALIZADO)
        elif self._nivel_vigente:
            self._estado(*self._nivel_vigente)

    def marcar_activa(self, clave):
        """Resalta la tarjeta cuya fórmula está abierta (None: ninguna)."""
        self._activa = clave
        for t in self.tarjetas:
            t.marcar_activa(clave is not None and t.clave == clave)

    def actualizar_tema(self):
        for t in self.tarjetas:
            t.actualizar_tema()
