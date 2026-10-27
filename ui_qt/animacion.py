"""
animacion.py
Animación de los paneles laterales (parámetros a la izquierda, «Cómo se calculó» a la derecha).

  * AnimadorPaneles: un único controlador para los dos anchos. Un solo reloj (QAbstractAnimation
    sin fin) aplica en cada cuadro el ancho de todas las «pistas» activas, así dos paneles que se
    animan a la vez no se pisan y el layout se resuelve una vez por cuadro. Cada pista lleva su
    propio inicio, destino, duración y curva: invertir a mitad de camino sigue desde el ancho
    actual con una curva que arranca en reposo (InOutSine); un arranque normal usa OutCubic.
  * indicador: «animando» global. Mientras está activo, lo caro de un cambio de tamaño se
    difiere (medir columnas y filas de las tablas, redibujar la gráfica de matplotlib, volver a
    renderizar las ecuaciones) y se hace una sola vez al terminar (señal cambio(False)).
"""
from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QObject, Signal

# Lo más que avanza la animación en un cuadro (ms). Si un cuadro llega tarde (el sistema estuvo
# ocupado), la animación se estira en lugar de saltar: ningún cuadro mueve el panel de golpe.
PASO_MAX_MS = 20


class _Indicador(QObject):
    cambio = Signal(bool)

    def __init__(self):
        super().__init__()
        self.activo = False

    def poner(self, activo):
        if activo != self.activo:
            self.activo = activo
            self.cambio.emit(activo)


indicador = _Indicador()


def animando():
    """True mientras algún panel lateral cambia de ancho."""
    return indicador.activo


class _Reloj(QAbstractAnimation):
    """Animación sin duración fija: solo marca el paso del tiempo (sincronizada con el refresco de Qt)."""

    def __init__(self, al_avanzar, padre=None):
        super().__init__(padre)
        self._al_avanzar = al_avanzar

    def duration(self):
        return -1

    def updateCurrentTime(self, ms):
        self._al_avanzar(ms)


class _Pista:
    def __init__(self, aplicar, ancho):
        self.aplicar = aplicar      # función(ancho entero) que cambia la geometría real
        self.actual = float(ancho)
        self.aplicado = int(ancho)
        self.inicio = self.destino = float(ancho)
        self.t0 = 0
        self.duracion = 1
        self.curva = QEasingCurve(QEasingCurve.OutCubic)
        self.activa = False


class AnimadorPaneles(QObject):
    avanzo = Signal(str, int)       # pista y ancho aplicado en este cuadro (para pruebas y mediciones)
    terminado = Signal(str)         # la pista llegó a su destino

    def __init__(self, duracion_ms, padre=None):
        super().__init__(padre)
        self.duracion_ms = duracion_ms
        self.pistas = {}
        self._reloj = _Reloj(self._avanzar, self)
        self._ultimo_ms = 0             # tiempo del reloj en el cuadro anterior
        self._tiempo = 0                # tiempo de animación (avanza a lo sumo PASO_MAX_MS por cuadro)

    def agregar(self, nombre, aplicar, ancho=0):
        self.pistas[nombre] = _Pista(aplicar, ancho)

    def ancho(self, nombre):
        return self.pistas[nombre].aplicado

    def destino(self, nombre):
        return self.pistas[nombre].destino

    def activa(self, nombre=None):
        if nombre is not None:
            return self.pistas[nombre].activa
        return any(p.activa for p in self.pistas.values())

    def fijar(self, nombre, ancho):
        """Sin animar (p. ej. al restaurar el estado): la pista queda quieta en `ancho`."""
        p = self.pistas[nombre]
        p.actual = p.inicio = p.destino = float(ancho)
        p.aplicado = int(ancho)

    def animar(self, nombre, destino, recorrido, animar=True):
        """
        Lleva la pista a `destino`. `recorrido`: ancho de un recorrido completo (la duración es
        proporcional a lo que falta). Si la pista ya iba en sentido contrario, se invierte desde el
        ancho actual con una curva que arranca en reposo.
        """
        p = self.pistas[nombre]
        invertida = p.activa and (destino - p.actual) * (p.destino - p.inicio) < 0
        p.inicio, p.destino = p.actual, float(destino)
        distancia = abs(destino - p.actual)
        if not animar or distancia < 1:
            p.activa = False
            self._aplicar(nombre, p, destino)
            if not self.activa():
                self._reloj.stop()
            self.terminado.emit(nombre)
            if not self.activa():
                indicador.poner(False)
            return
        p.curva = QEasingCurve(QEasingCurve.InOutSine if invertida else QEasingCurve.OutCubic)
        p.duracion = max(1, round(self.duracion_ms * min(1.0, distancia / max(1, recorrido))))
        corriendo = self._reloj.state() == QAbstractAnimation.Running
        if not corriendo:
            self._ultimo_ms = self._tiempo = 0
        p.t0 = self._tiempo
        p.activa = True
        if not corriendo:
            indicador.poner(True)
            self._reloj.start()

    def terminar(self):
        """Lleva todas las pistas activas a su destino ya (p. ej. si la ventana cambia de tamaño)."""
        if self.activa():
            self._avanzar(None)

    # ------------------------------------------------------------------
    def _aplicar(self, nombre, p, ancho):
        p.actual = float(ancho)
        entero = int(round(ancho))
        if entero != p.aplicado:            # sin cambio de píxel entero no se toca la geometría
            p.aplicado = entero
            p.aplicar(entero)
            self.avanzo.emit(nombre, entero)

    def _avanzar(self, ms):
        if ms is not None:
            self._tiempo += min(max(0, ms - self._ultimo_ms), PASO_MAX_MS)
            self._ultimo_ms = ms
        terminadas = []
        for nombre, p in self.pistas.items():
            if not p.activa:
                continue
            x = 1.0 if ms is None else min(1.0, max(0.0, (self._tiempo - p.t0) / p.duracion))
            if x >= 1.0:
                p.activa = False
                self._aplicar(nombre, p, p.destino)
                terminadas.append(nombre)
            else:
                self._aplicar(nombre, p, p.inicio + (p.destino - p.inicio) * p.curva.valueForProgress(x))
        if not self.activa():
            self._reloj.stop()
        for nombre in terminadas:           # geometría final primero ...
            self.terminado.emit(nombre)
        if not self.activa():
            indicador.poner(False)          # ... y después, una sola vez, el trabajo diferido
