"""Módulo interactivo para analizar un diseño completamente al azar."""

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
import plotly.express as px
import streamlit as st
from scipy.stats import f as distribucion_f

from utils.anova_utils import (
    ajustar_dca,
    cargar_datos,
    coeficiente_variacion,
    interpretar_dca,
    resumen_tratamientos,
    tabla_anova,
    tukey,
    validar_dca,
)


@st.cache_data
def cargar_datos_cache(nombre_archivo: str, contenido: bytes | None = None) -> pd.DataFrame:
    """Carga datos usando las utilidades compartidas y conserva el resultado en caché.

    Args:
        nombre_archivo: Nombre o ruta del archivo CSV o XLSX.
        contenido: Contenido binario del archivo cargado desde la interfaz.

    Returns:
        Datos experimentales leídos en un DataFrame.
    """
    if contenido is None:
        return cargar_datos(nombre_archivo)

    archivo = BytesIO(contenido)
    archivo.name = nombre_archivo
    return cargar_datos(archivo)


st.title("Diseño completamente al azar (DCA)")
st.write(
    "El diseño completamente al azar compara tratamientos asignándolos al azar "
    "a unidades experimentales homogéneas. En este ejemplo se evalúa la humedad "
    "obtenida con cuatro secadores solares (A, B, C y D), con cuatro réplicas "
    "por secador."
)

archivo_cargado = st.file_uploader(
    "Carga los datos del ensayo",
    type=["csv", "xlsx"],
    help="Se aceptan archivos CSV o Excel en formato .xlsx.",
)

if archivo_cargado is None:
    ruta_ejemplo = Path(__file__).resolve().parents[1] / "data" / "dca_secadores.csv"
    st.caption("No se cargó un archivo; se usan los datos de ejemplo de los cuatro secadores solares.")
    nombre_archivo = str(ruta_ejemplo)
    contenido_archivo = None
else:
    nombre_archivo = archivo_cargado.name
    contenido_archivo = archivo_cargado.getvalue()

try:
    datos = cargar_datos_cache(nombre_archivo, contenido_archivo)
except (BadZipFile, ImportError, OSError, UnicodeDecodeError, ValueError, pd.errors.ParserError) as error:
    st.error(f"No se pudieron cargar los datos: {error}")
    st.stop()

if len(datos.columns) < 2:
    st.error("El archivo debe contener al menos una columna de tratamiento y una de respuesta.")
    st.stop()

columnas = list(datos.columns)
columnas_numericas = [
    columna for columna in columnas if pd.api.types.is_numeric_dtype(datos[columna])
]
indice_respuesta = next(
    (
        columnas.index(columna)
        for columna in reversed(columnas_numericas)
        if columnas.index(columna) != 0
    ),
    1,
)

columna_tratamiento = st.selectbox(
    "Columna de tratamiento",
    options=columnas,
    index=0,
)
columna_respuesta = st.selectbox(
    "Columna de respuesta",
    options=columnas,
    index=indice_respuesta,
)
alfa = st.slider(
    "Nivel de significancia (α)",
    min_value=0.01,
    max_value=0.10,
    value=0.05,
    step=0.01,
    format="%.2f",
)

if columna_tratamiento == columna_respuesta:
    st.error("Selecciona columnas diferentes para el tratamiento y la respuesta.")
    st.stop()

# Valida que haya tratamientos, réplicas y respuestas numéricas antes del análisis.
errores = validar_dca(datos, columna_tratamiento, columna_respuesta)
if errores:
    for error in errores:
        st.error(error)
    st.stop()

# Convierte la respuesta a número para que el modelo y los gráficos usen la escala cuantitativa.
datos_analisis = datos.copy()
datos_analisis[columna_respuesta] = pd.to_numeric(datos_analisis[columna_respuesta])

# Ajusta el modelo de un factor para separar la variación de tratamientos del error experimental.
modelo = ajustar_dca(datos_analisis, columna_tratamiento, columna_respuesta)

# Calcula la tabla ANOVA que contrasta si las medias de humedad de los secadores son iguales.
anova = tabla_anova(modelo)
fila_tratamientos = anova.loc[anova["Fuente"] == "Tratamientos"].iloc[0]
p_valor = float(fila_tratamientos["p-valor"])
f_critica = float(
    distribucion_f.ppf(
        1 - alfa,
        fila_tratamientos["gl"],
        anova.loc[anova["Fuente"] == "Error", "gl"].iloc[0],
    )
)

# Resume las observaciones para describir réplicas, totales, medias y dispersión por secador.
resumen = resumen_tratamientos(
    datos_analisis, columna_tratamiento, columna_respuesta
)

# Expresa el error residual en relación con la humedad media general para facilitar su interpretación.
cv = coeficiente_variacion(modelo, datos_analisis, columna_respuesta)

pestanas = st.tabs(["Datos", "ANOVA", "Comparaciones", "Gráficos"])

with pestanas[0]:
    st.subheader("Datos del ensayo")
    st.dataframe(datos, width="stretch", hide_index=True)
    st.subheader("Resumen por tratamiento")
    st.dataframe(
        resumen,
        width="stretch",
        hide_index=True,
        column_config={
            "total": st.column_config.NumberColumn(format="%.4f"),
            "media": st.column_config.NumberColumn(format="%.4f"),
            "desviación estándar": st.column_config.NumberColumn(format="%.4f"),
        },
    )

with pestanas[1]:
    st.subheader("Análisis de varianza")
    st.dataframe(
        anova,
        width="stretch",
        hide_index=True,
        column_config={
            "gl": st.column_config.NumberColumn(format="%d"),
            "SC": st.column_config.NumberColumn(format="%.4f"),
            "CM": st.column_config.NumberColumn(format="%.4f"),
            "F": st.column_config.NumberColumn(format="%.4f"),
            "p-valor": st.column_config.NumberColumn(format="%.4f"),
        },
    )
    columna_f, columna_cv = st.columns(2)
    columna_f.metric("F crítica", f"{f_critica:.4f}")
    columna_cv.metric("Coeficiente de variación (CV)", f"{cv:.4f} %")

    # Interpreta el contraste global para decidir si existe evidencia de diferencias entre medias.
    interpretacion = interpretar_dca(anova, alfa)
    if p_valor < alfa:
        st.success(interpretacion)
    else:
        st.info(interpretacion)

with pestanas[2]:
    st.subheader("Comparaciones múltiples de Tukey")
    if p_valor < alfa:
        # Compara pares de medias solo después de detectar diferencias globales en el ANOVA.
        comparaciones, dms = tukey(
            datos_analisis,
            columna_tratamiento,
            columna_respuesta,
            alfa,
        )
        st.dataframe(comparaciones, width="stretch", hide_index=True)
        st.metric("Diferencia mínima significativa (DMS)", f"{dms:.4f}")
    else:
        st.info(
            f"No se realiza la prueba de Tukey porque el p-valor ({p_valor:.4f}) "
            f"no es menor que α ({alfa:.2f}); el ANOVA no detectó diferencias "
            "estadísticamente significativas entre las medias."
        )

with pestanas[3]:
    st.subheader("Distribución de la respuesta por tratamiento")
    figura_cajas = px.box(
        datos_analisis,
        x=columna_tratamiento,
        y=columna_respuesta,
        points="all",
        labels={
            columna_tratamiento: "Tratamiento",
            columna_respuesta: "Respuesta",
        },
    )
    st.plotly_chart(figura_cajas, width="stretch")

    st.subheader("Medias por tratamiento")
    figura_medias = px.bar(
        resumen,
        x="Tratamiento",
        y="media",
        error_y="desviación estándar",
        labels={"Tratamiento": "Tratamiento", "media": "Media de la respuesta"},
    )
    st.plotly_chart(figura_medias, width="stretch")
