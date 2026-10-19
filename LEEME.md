# Calculadora de Teoría de Colas

Programa con interfaz gráfica para resolver problemas de colas con los modelos
PICS (M/M/1), PICM (M/M/k), PFCS (M/M/1/M/M) y PFCM (M/M/k/M/M).

## Instalación
1. Python 3.9 o superior (Tkinter viene incluido en Windows y macOS;
   en Linux: `sudo apt install python3-tk`).
2. `pip install -r requirements.txt`

## Ejecutar
    python app_colas.py

## Archivos
- `modelos_colas.py`: fórmulas de los cuatro modelos, costos y barridos de k y M.
  Se puede probar solo con `python modelos_colas.py` (verifica ejemplos del apunte).
- `graficas_colas.py`: las 11 gráficas de tendencia (matplotlib).
- `app_colas.py`: la interfaz (Tkinter).

## Uso rápido
1. Elige población Infinita o Finita, k y M.
2. Ingresa λ y μ como vengan en el enunciado (tasa o tiempo, en minuto/hora/día).
3. Ingresa horas por día, días por semana y costos si el problema los pide.
4. Pulsa Calcular y revisa las pestañas: Resultados, Probabilidades,
   Por día y costos, Comparar k y M, Gráficas.
