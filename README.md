# Calculadora de Teoría de Colas

Aplicación de escritorio (Python + Tkinter + Matplotlib) para resolver problemas de
líneas de espera con llegadas Poisson y servicio exponencial. Calcula las medidas de
desempeño, probabilidades, indicadores por día, costos, compara escenarios variando
el número de servidores **k** o la población **M** y dibuja 11 gráficas de tendencia.

## Modelos implementados

| Sigla | Kendall      | Población | Canales |
|-------|--------------|-----------|---------|
| PICS  | M/M/1        | Infinita  | 1       |
| PICM  | M/M/k        | Infinita  | k       |
| PFCS  | M/M/1/M/M    | Finita    | 1       |
| PFCM  | M/M/k/M/M    | Finita    | k       |

Supuestos relevantes:

- Disciplina FIFO, servidores idénticos en paralelo y una sola cola.
- **Población infinita:** el sistema es estable solo si ρ = λ/(kμ) < 1. Si no lo es,
  la app lo informa y muestra el k mínimo estable (las comparaciones siguen disponibles).
  Un ρ que difiere de 1 en menos de 1e-12 se considera ρ = 1 (inestable).
- **Población finita:** λ es la tasa de llegada de **cada** unidad; siempre es estable.
  La λ efectiva es λ(M − L) y la probabilidad de esperar es la vista por quien llega.
  Si k > M solo pueden trabajar M servidores a la vez (k efectivo = M); el costo de
  servidores sí cobra los k contratados (la app lo avisa).
- Internamente todas las tasas están en clientes **por hora** y los tiempos en **horas**.
  Un «día» en las unidades equivale a las horas de operación (cada 4 días con 8 h/día =
  cada 32 h).

## Funcionalidades

- Panel de parámetros agrupado: modelo, capacidad y población, llegadas y servicio
  (como tasa o como tiempo, en minutos, horas o días), configuración operativa,
  costos e ingresos, rango de análisis y presentación (unidad de tiempo y decimales).
- Tarjetas con los indicadores principales: ρ, P0, probabilidad de esperar, Lq, L,
  Wq, W (y M − L en población finita) y estado de estabilidad.
- Pestañas: **Resultados** (todas las medidas), **Probabilidades** (P(n = a), rangos,
  probabilidades de la cola y distribución completa), **Por día y costos**,
  **Comparar k y M** (búsqueda por condición y menor costo) y **Gráficas**.
- Exportación de tablas a CSV y de gráficas a PNG (una o todas).

## Requisitos e instalación

1. Python **3.10 o superior**. Tkinter viene incluido en Windows y macOS; en Linux:
   `sudo apt install python3-tk`.
2. Instalar la dependencia:

       pip install -r requirements.txt

   (Única dependencia externa: `matplotlib`.)

## Ejecutar

    python main.py

## Ejecutar las pruebas

Las pruebas usan `unittest` (biblioteca estándar) y no abren la interfaz:

    python -m unittest discover -s tests -v

## Organización del proyecto

```text
calculadora_colas/
├── main.py                      Punto de entrada
├── domain/                      Matemática pura (sin Tkinter ni matplotlib)
│   ├── modelos_colas.py         Fórmulas M/M/k y M/M/k/M/M, probabilidades, barridos de k y M
│   ├── unidades.py              Conversión de tasas/tiempos a «por hora»
│   ├── costos.py                CT(S), CT(TE), ocio, ingresos, horas por estado
│   └── errores.py               ErrorEntrada (dato inválido) y ErrorModelo (limitación numérica)
├── services/                    Coordinación entre la interfaz y el dominio (sin Tkinter)
│   ├── calculadora_service.py   Validación del formulario, escenario, tablas e indicadores
│   ├── comparacion_service.py   Tablas en función de k y M con una condición
│   ├── exportacion_service.py   CSV y PNG a partir de datos (no de widgets)
│   └── tablas.py                Estructura Tabla/Valor y formato de números
├── visualization/
│   └── graficas_colas.py        Las 11 gráficas sobre una Figure de matplotlib
├── ui/                          Interfaz Tkinter
│   ├── app.py                   Ventana principal y flujo de cálculo
│   ├── panel_entradas.py        Formulario agrupado, errores por campo, acciones
│   ├── panel_resumen.py         Modelo, estado y tarjetas de indicadores
│   ├── vista_resultados.py      Pestañas Resultados, Probabilidades, Por día y costos
│   ├── vista_comparacion.py     Pestaña Comparar k y M
│   ├── vista_graficas.py        Pestaña Gráficas
│   ├── componentes.py           Panel desplazable, tabla y tarjeta reutilizables
│   └── estilos.py               Colores, tipografías y estilos ttk
└── tests/                       Pruebas automatizadas (unittest)
    ├── datos/referencia_original.json
    ├── test_modelos.py  test_unidades.py  test_costos.py
    ├── test_servicios.py  test_comparaciones.py  test_arquitectura.py
```

Reglas de dependencia (verificadas por `tests/test_arquitectura.py`):
`ui → services → domain`, y `visualization → domain`. El dominio no importa Tkinter,
matplotlib ni otras capas.

## Flujo de datos

1. `PanelEntradas` entrega el **texto** de cada campo.
2. `calculadora_service.leer_parametros()` valida cada campo (sin corregir nada) y
   convierte λ y μ a tasas por hora. Si hay errores lanza `ErrorEntrada` con la lista
   de campos; la interfaz los marca en rojo con un mensaje de cómo corregirlos.
3. `calculadora_service.calcular_escenario()` llama a `domain.modelos_colas` para el
   modelo actual y los barridos de k y M, y a `domain.costos`.
4. Los servicios construyen objetos `Tabla` (valores numéricos crudos + tipo). La
   interfaz los muestra con un `Formateador` (coma decimal, unidad de tiempo elegida);
   la exportación CSV usa exactamente las mismas tablas.
5. Si el cálculo falla (dato inválido, `ErrorModelo` o error inesperado) se retiran los
   resultados anteriores. Si se editan datos después de calcular, los resultados se
   marcan como **desactualizados** y la exportación se deshabilita hasta recalcular.
   Cambiar la unidad de tiempo o los decimales solo cambia la presentación.

## Validación de entradas

| Campo | Regla |
|-------|-------|
| k | entero, 1 a 1000 |
| M (solo finita) | entero, 1 a 10 000 |
| Valor de λ y μ | número > 0 |
| Horas por día | > 0 y ≤ 24 |
| Días por semana | > 0 y ≤ 7 |
| Costos e ingreso por cliente | ≥ 0 |
| Fracción con ingreso | entre 0 y 1 |
| k máximo | entero, 1 a 200 |
| M máximo (solo finita) | entero, 2 a 300 |
| Rango a, b (Probabilidades) | enteros, 0 ≤ a ≤ b |

Se aceptan coma o punto decimal. Los campos que no aplican al modelo se deshabilitan
(conservan su valor) y no se validan.

## Exportación CSV

Igual que la versión anterior: separador `;`, UTF-8 con BOM (se abre bien en Excel),
secciones *Resultados, Probabilidades, Por día, Costos, Variando k, Variando M*, cada
una con título, encabezados, filas y una línea en blanco. Cambios: la columna
«% operando» de *Variando k* solo aparece en población finita, la columna de costo de
espera se titula «CT(TE)+ocio» cuando hay costo de ocio, y las columnas de tiempo
indican la unidad en el encabezado (p. ej. «Wq (min)»).

## Valores iniciales

Al abrir se resuelve un M/M/1 de ejemplo estable: λ = 10 clientes/h, servicio de
4 min (μ = 15/h, ρ ≈ 0,67), jornada de 12 h, 7 días y sin costos. El botón
«Valores iniciales» los restablece.

## Correcciones respecto de la versión anterior

Cada corrección tiene su prueba en `tests/`:

- **Desbordamiento numérico:** con población finita y M grande (p. ej. λ = 0,1, μ = 0,5,
  k = 2, M = 300, dentro del rango permitido de «M máximo») los términos superaban 1e308 y
  los resultados salían NaN sin aviso. Ahora se calculan en escala logarítmica (mismas
  fórmulas). Igual en población infinita con λ/μ ≳ 700.
- **P(n = k) con k grande** (p. ej. λ = μ, k = 50): la distribución se truncaba antes de
  n = k y la pestaña Resultados fallaba con `IndexError`. Ahora la distribución llega al
  menos hasta n = k + 1.
- **ρ = 1 por redondeo:** 0,3/0,1 = 2,9999999999999996 hacía que k = 3 pareciera estable
  (Lq ≈ 10¹⁵). Ahora se aplica una tolerancia de 1e-12.
- **λ efectiva nula:** se rechaza explícitamente con un mensaje (antes, división entre cero).
- **Entradas corregidas en silencio:** k = 2,7 se convertía en 3, k = −5 en 1, M máximo
  se recortaba a [2, 300], etc. Ahora se rechazan con un mensaje por campo.
- **Condición de comparación inválida:** antes equivalía a «no cumple»; ahora se informa.

Los resultados de todos los casos válidos coinciden con la versión anterior.
`tests/datos/referencia_original.json` se generó ejecutando el `modelos_colas.py`
original (commit `e65163c`), y las pruebas comparan contra esos valores con una
tolerancia relativa de 1e-9.
