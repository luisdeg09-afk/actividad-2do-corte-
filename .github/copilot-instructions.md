# Instrucciones permanentes del repositorio

## Proyecto

Este repositorio contiene una aplicación de Diseño Experimental desarrollada en Python y Streamlit para el curso de Diseño Experimental del programa de Ingeniería Agrícola de la Universidad de Sucre.

## Estructura

- `app.py`: portada de la aplicación.
- `pages/`: un archivo por cada diseño experimental.
- `utils/`: funciones reutilizables; debe incluir `__init__.py`.
- `data/`: archivos CSV de ejemplo.
- `verificacion/`: scripts de R para verificar los análisis.

## Idioma y explicación

- Escribe todo el código, comentarios, docstrings y mensajes de la interfaz en español.
- Añade un comentario en cada paso estadístico que explique qué se calcula y por qué, con una explicación adecuada para estudiantes de Ingeniería Agrícola.
- Define funciones con anotaciones de tipos (*type hints*) y docstrings en estilo Google, redactados en español.

## Dependencias y análisis estadístico

- Las únicas librerías permitidas son `streamlit`, `pandas`, `numpy`, `scipy`, `statsmodels`, `plotly` y `openpyxl`. No agregues otras dependencias sin pedir permiso.
- Ajusta los modelos ANOVA con `statsmodels.formula.api.ols` y calcula la tabla con `statsmodels.stats.anova.anova_lm(typ=2)`.
- Realiza las comparaciones de Tukey con `statsmodels.stats.multicomp.pairwise_tukeyhsd`.
- No inventes ni codifiques resultados estadísticos: todos los números mostrados deben provenir del cálculo realizado con los datos.

## Verificación

Antes de terminar una tarea que incluya cambios ejecutables, ejecuta el código pertinente, revisa los errores que aparezcan y corrígelos. No declares la tarea terminada si los errores detectados siguen sin resolver.