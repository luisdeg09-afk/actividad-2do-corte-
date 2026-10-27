AUTOR = "Escribe aquí tu nombre"

import streamlit as st

st.set_page_config(
    page_title="App de Diseño Experimental",
    page_icon="🌱",
    layout="wide",
)

st.title("App de Diseño Experimental")
st.subheader("Ingeniería Agrícola – Universidad de Sucre")
st.write(
    "El diseño experimental permite planear ensayos de campo para comparar "
    "tratamientos de manera ordenada y obtener conclusiones confiables. "
    "En agricultura ayuda, por ejemplo, a evaluar variedades, fertilizantes "
    "y prácticas de manejo considerando la variabilidad de las parcelas."
)

st.header("Módulos")
st.table(
    [
        {
            "Módulo": "DCA — Diseño completamente al azar",
            "Cuándo se usa": "Cuando las unidades experimentales son relativamente homogéneas.",
            "Ejemplo agrícola": "Comparar dosis de fertilizante en parcelas uniformes.",
            "Estado": "Disponible",
        },
        {
            "Módulo": "DBCA — Diseño en bloques completos al azar",
            "Cuándo se usa": "Cuando se puede controlar una fuente de variación agrupando unidades en bloques.",
            "Ejemplo agrícola": "Comparar variedades de maíz en bloques definidos por la pendiente del terreno.",
            "Estado": "En construcción",
        },
        {
            "Módulo": "DCL — Diseño en cuadrado latino",
            "Cuándo se usa": "Cuando se deben controlar dos fuentes de variación mediante filas y columnas.",
            "Ejemplo agrícola": "Evaluar fertilizantes controlando gradientes de suelo en dos direcciones.",
            "Estado": "En construcción",
        },
        {
            "Módulo": "DPD — Diseño de parcelas divididas",
            "Cuándo se usa": "Cuando se estudian factores con distintos tamaños de parcela o niveles de precisión.",
            "Ejemplo agrícola": "Evaluar sistemas de riego en parcelas principales y variedades en subparcelas.",
            "Estado": "En construcción",
        },
        {
            "Módulo": "Factoriales",
            "Cuándo se usa": "Cuando se estudian simultáneamente varios factores y sus interacciones.",
            "Ejemplo agrícola": "Comparar dosis de nitrógeno y densidades de siembra en un cultivo.",
            "Estado": "En construcción",
        },
        {
            "Módulo": "RSM — Metodología de superficie de respuesta",
            "Cuándo se usa": "Cuando se busca modelar y optimizar una respuesta en función de factores cuantitativos.",
            "Ejemplo agrícola": "Encontrar la combinación de riego y fertilización que maximiza el rendimiento.",
            "Estado": "En construcción",
        },
    ]
)

st.header("Instrucciones de uso")
st.markdown(
    """
1. Elige un módulo en el menú lateral.
2. Carga los datos del ensayo cuando el módulo esté disponible.
3. Revisa los resultados y su interpretación.
4. Verifica los supuestos y compara los resultados con tu cálculo manual.
"""
)

st.warning(
    "Esta app apoya el aprendizaje. El estudiante interpreta los resultados, "
    "verifica supuestos y compara con su cálculo manual."
)

with st.sidebar:
    st.header("Información del curso")
    st.write(f"Autor: {AUTOR}")
    st.write("Curso: Diseño Experimental")
    st.write("Semestre: 2026-2")
