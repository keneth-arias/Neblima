# Calibración de probabilidades con SciPy

El calibrador horario de Neblima ajusta una regresión logística de una variable con pendiente no negativa y penalización cuadrática. El entorno de TimeF ya incluía SciPy en su archivo de versiones. Se declara ahora como dependencia directa para usar el optimizador L-BFGS-B y la función logística estable. Si la optimización falla, el ajuste se detiene antes de publicar. Un bloque con una sola clase o puntaje constante produce una frecuencia explícita.
