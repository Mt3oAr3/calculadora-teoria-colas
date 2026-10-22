"""
encabezado_modelo.py
Encabezado del área de resultados: modelo (notación de Kendall), descripción,
insignia de estado (estable / inestable / sin resultados) y mensaje de estabilidad.
El aviso de datos desactualizados NO va aquí: lo muestra el banner global.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from services import calculadora_service as cs

from . import tema

TEXTO_INSIGNIA = {"ok": "Estable", "aviso": "Inestable", "error": "Sin resultados"}


class EncabezadoModelo(QWidget):

    def __init__(self, padre=None):
        super().__init__(padre)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
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

    def _estado(self, nivel, texto):
        for w in (self.insignia, self.mensaje):
            w.setProperty("nivel", nivel)
            tema.refrescar(w)
        # Icono + texto: el estado nunca se comunica solo con color
        icono = tema.ICONOS[nivel]
        self.insignia.setText(f"{icono} {TEXTO_INSIGNIA[nivel]}")
        self.mensaje.setText(f"{icono}  {texto}")

    def mostrar(self, esc, fmt):
        self.lbl_modelo.setText(esc.kendall)
        self.lbl_desc.setText(esc.descripcion)
        self._estado("ok" if esc.estable else "aviso", cs.mensaje_estado(esc, fmt))

    def limpiar(self, mensaje):
        """Sin resultados vigentes (error de entrada, de modelo o inesperado)."""
        self.lbl_modelo.setText("—")
        self.lbl_desc.setText("")
        self._estado("error", mensaje)
