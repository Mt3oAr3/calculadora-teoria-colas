"""
vista_graficas.py
Página «Gráficas»: índice por categoría, figura de visualization.graficas_colas
incrustada con FigureCanvasQTAgg y acciones para guardar PNG.

El panel izquierdo (índice y botones) mide lo que su texto más largo: nada se corta ni se
elide. El divisor no lo deja más angosto; al achicar la página se achica primero la gráfica.
"""
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QPainter, QResizeEvent
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QHBoxLayout, QMessageBox, QPushButton,
                               QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from services import exportacion_service as ex
from visualization import graficas_colas as gc

from . import animacion, tema
from .info_box import InfoBox
from .vista_tabla import encabezado_pagina

ROL_GID = Qt.UserRole


class _Lienzo(FigureCanvasQTAgg):
    """
    Lienzo de matplotlib que no se redibuja en cada cuadro de la animación de los paneles: mientras
    dura muestra el último render escalado al tamaño del cuadro y redibuja una vez al terminar.
    """

    def __init__(self, figura):
        super().__init__(figura)
        self._foto = None
        self._diferido = False
        animacion.indicador.cambio.connect(self._animacion_cambio)

    def _animacion_cambio(self, activa):
        if activa:
            self._foto = self.grab() if self.isVisible() else None
            return
        self._foto = None
        if self._diferido:
            self._diferido = False
            super().resizeEvent(QResizeEvent(self.size(), self.size()))    # redimensiona la figura y redibuja
        self.update()

    def resizeEvent(self, e):
        if self._foto is not None:
            self._diferido = True
            QWidget.resizeEvent(self, e)
            self.update()
            return
        super().resizeEvent(e)

    def paintEvent(self, e):
        if self._foto is None:
            super().paintEvent(e)
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._foto)
        p.end()


class PaginaGraficas(QWidget):
    aviso = Signal(str)          # mensaje para la barra de estado

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("Pagina")
        self.ctx = None
        self._mensaje = None
        self._pendiente = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(encabezado_pagina("Gráficas",
                                        "Las gráficas «vs k» usan el rango «k máximo»; las «vs M» usan «M máximo» "
                                        "con el k actual (solo población finita)."))

        self.div = div = QSplitter(Qt.Horizontal)
        div.setChildrenCollapsible(False)
        self.izq = izq = QWidget()
        li = QVBoxLayout(izq)
        li.setContentsMargins(0, 0, 0, 0)
        li.setSpacing(6)
        self.arbol = QTreeWidget()
        self.arbol.setObjectName("IndiceGraficas")
        self.arbol.setHeaderHidden(True)
        self.arbol.setTextElideMode(Qt.ElideNone)
        self.arbol.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.items = {}
        for cat in gc.CATEGORIAS:
            nodo = QTreeWidgetItem([cat])
            nodo.setFlags(Qt.ItemIsEnabled)
            f = nodo.font(0)
            f.setBold(True)
            nodo.setFont(0, f)
            self.arbol.addTopLevelItem(nodo)
            for g in gc.GRAFICAS:
                if g.categoria == cat:
                    it = QTreeWidgetItem([("vs M · " if g.por_M else "vs k · ") + g.titulo.split(" en función")[0]])
                    it.setData(0, ROL_GID, g.gid)
                    it.setToolTip(0, g.titulo)
                    nodo.addChild(it)
                    self.items[g.gid] = it
            nodo.setExpanded(True)
        self.orden = [g.gid for cat in gc.CATEGORIAS for g in gc.GRAFICAS if g.categoria == cat]
        self.arbol.currentItemChanged.connect(lambda *_a: self.dibujar())
        li.addWidget(self.arbol, 1)
        nav = QHBoxLayout()
        b_ant, b_sig = QPushButton("◀ Anterior"), QPushButton("Siguiente ▶")
        b_ant.clicked.connect(lambda: self._mover(-1))
        b_sig.clicked.connect(lambda: self._mover(1))
        nav.addWidget(b_ant)
        nav.addWidget(b_sig)
        li.addLayout(nav)
        # Acciones bajo el índice: así el ancho mínimo de la página es pequeño
        guardar = QHBoxLayout()
        self.btn_esta = QPushButton("Guardar PNG")
        self.btn_esta.setToolTip("Guardar la gráfica actual como imagen PNG")
        self.btn_todas = QPushButton("Guardar todas")
        self.btn_todas.setToolTip("Guardar todas las gráficas aplicables como PNG en una carpeta")
        self.btn_esta.clicked.connect(self.guardar_esta)
        self.btn_todas.clicked.connect(self.guardar_todas)
        guardar.addWidget(self.btn_esta)
        guardar.addWidget(self.btn_todas)
        li.addLayout(guardar)
        div.addWidget(izq)

        der = QFrame()
        der.setObjectName("Bloque")
        ld = QVBoxLayout(der)
        ld.setContentsMargins(10, 8, 10, 10)
        self.fig = Figure(figsize=(6, 4), dpi=100, layout="constrained")
        self.canvas = _Lienzo(self.fig)
        self.canvas.setMinimumSize(300, 260)     # legible aun a 1100 px con el panel de parámetros
        self.barra_mpl = NavigationToolbar2QT(self.canvas, der)
        self.barra_mpl.setMinimumWidth(1)       # si no cabe, la barra muestra el botón »
        self.chk_valores = QCheckBox("Valores en los puntos")
        self.chk_valores.setChecked(True)
        self.chk_valores.toggled.connect(lambda _v: self.dibujar())
        arriba = QHBoxLayout()
        arriba.addWidget(self.barra_mpl, 1)
        arriba.addWidget(self.chk_valores)
        ld.addLayout(arriba)
        ld.addWidget(self.canvas, 1)
        self.lbl_no_aplica = InfoBox("Las gráficas «vs M» (en gris) solo aplican a población finita.")
        self.lbl_no_aplica.hide()
        ld.addWidget(self.lbl_no_aplica)
        div.addWidget(der)
        div.setStretchFactor(0, 0)
        div.setStretchFactor(1, 1)           # al achicar la página, se achica primero la gráfica
        lay.addWidget(div, 1)
        self._ancho_indice = None
        self.ajustar_indice()

        self.arbol.setCurrentItem(self.items[self.orden[0]])
        self._habilitar(False)

    # ------------------------------------------------------------------
    def ancho_indice(self):
        """Ancho del panel izquierdo: el texto más largo del índice (con sangría, marco y barra) o el botón
        más ancho, lo que sea mayor."""
        a = self.arbol
        a.ensurePolished()
        m = a.contentsMargins()
        texto = (a.sizeHintForColumn(0) + a.indentation() + 2 * a.frameWidth() + m.left() + m.right()
                 + a.verticalScrollBar().sizeHint().width())
        botones = self.izq.layout().minimumSize().width()
        return texto, max(texto, botones)

    def ajustar_indice(self):
        """Fija el mínimo del índice y del panel izquierdo; recalcula si cambian la fuente o el tema."""
        texto, panel = self.ancho_indice()
        self.arbol.setMinimumWidth(texto)
        self.izq.setMinimumWidth(panel)
        if panel != self._ancho_indice:
            self._ancho_indice = panel
            total = sum(self.div.sizes()) or (panel + 760)
            self.div.setSizes([panel, max(1, total - panel)])

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() in (QEvent.FontChange, QEvent.StyleChange):
            self.ajustar_indice()

    def _gid(self):
        it = self.arbol.currentItem()
        gid = it.data(0, ROL_GID) if it else None
        return gid or self.orden[0]

    def _mover(self, paso):
        i = (self.orden.index(self._gid()) + paso) % len(self.orden)
        self.arbol.setCurrentItem(self.items[self.orden[i]])

    def _habilitar(self, si):
        self.btn_esta.setEnabled(si)
        self.btn_todas.setEnabled(si)

    def mostrar(self, ctx):
        self.ctx = ctx
        self._mensaje = None
        self._colorear_indice()
        self.lbl_no_aplica.setVisible(not ctx["finita"])
        self._habilitar(True)
        self.dibujar()

    def _colorear_indice(self):
        for g in gc.GRAFICAS:
            aplica = self.ctx is None or self.ctx["finita"] or not g.por_M
            self.items[g.gid].setForeground(0, tema.qcolor("texto" if aplica else "texto_3"))

    def dibujar(self):
        """Dibuja la gráfica elegida con los colores del tema vigente (o la deja pendiente si no se ve)."""
        if not self.isVisible():
            self._pendiente = True           # se dibuja al abrir la pestaña (showEvent)
            return
        self._pendiente = False
        if self.ctx is None:
            gc.mensaje(self.fig, "", self._mensaje or "", {"colores": tema.colores_grafica()})
        else:
            self.ctx["mostrar_valores"] = self.chk_valores.isChecked()
            self.ctx["colores"] = tema.colores_grafica()
            gc.dibujar(self.fig, self._gid(), self.ctx)
        # Títulos que saltan de línea si la gráfica es angosta (p. ej. a 1100 px con el panel de parámetros)
        for texto in self.fig.texts + [ax.title for ax in self.fig.axes]:
            texto.set_wrap(True)
        self.canvas.draw_idle()

    def limpiar(self, mensaje):
        self.ctx = None
        self._mensaje = mensaje
        self._habilitar(False)
        self.dibujar()

    def repintar(self):
        """Cambio de tema: el índice se colorea (y se vuelve a medir) ya; la figura, ahora si se ve o al abrir."""
        self._colorear_indice()
        self.ajustar_indice()
        self.dibujar()

    @property
    def pendiente(self):
        return self._pendiente

    def showEvent(self, e):
        super().showEvent(e)
        self.ajustar_indice()             # ya con la hoja de estilos aplicada
        if self._pendiente:
            self.dibujar()

    def _ctx_exportacion(self):
        """Los PNG se guardan siempre con los colores claros de impresión, sea cual sea el tema."""
        return {k: v for k, v in self.ctx.items() if k != "colores"}

    # ------------------------------------------------------------------
    def guardar_esta(self):
        if self.ctx is None:
            return
        gid = self._gid()
        ruta, _f = QFileDialog.getSaveFileName(self, "Guardar gráfica", f"{gid}.png", "Imagen PNG (*.png)")
        if not ruta:
            return
        try:
            ex.guardar_grafica(ruta, gid, self._ctx_exportacion())
        except OSError as e:
            QMessageBox.critical(self, "No se pudo guardar", f"No se pudo guardar la gráfica:\n{e.strerror or e}")
            return
        self.aviso.emit(f"Gráfica guardada en {ruta}")

    def guardar_todas(self):
        if self.ctx is None:
            return
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta para guardar las gráficas")
        if not carpeta:
            return
        try:
            rutas = ex.guardar_todas(carpeta, self._ctx_exportacion())
        except OSError as e:
            QMessageBox.critical(self, "No se pudo guardar", f"No se pudieron guardar las gráficas:\n{e.strerror or e}")
            return
        self.aviso.emit(f"Se guardaron {len(rutas)} gráficas en {carpeta}")
        QMessageBox.information(self, "Gráficas guardadas", f"Se guardaron {len(rutas)} gráficas en:\n{carpeta}")
