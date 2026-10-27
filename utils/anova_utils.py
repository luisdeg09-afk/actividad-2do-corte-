"""Utilidades para cargar y analizar datos de un diseño completamente al azar."""

import json
import warnings
from pathlib import Path
from typing import IO

import numpy as np
import pandas as pd
from scipy.stats import studentized_range
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.regression.linear_model import RegressionResultsWrapper


def cargar_datos(archivo: str | Path | IO[bytes]) -> pd.DataFrame:
    """Carga datos desde un archivo CSV o Excel XLSX.

    Args:
        archivo: Ruta del archivo o archivo binario abierto, como una carga de Streamlit.

    Returns:
        Un DataFrame con los datos leídos.

    Raises:
        ValueError: Si la extensión no corresponde a CSV o XLSX.
    """
    # Identifica la extensión tanto en rutas como en archivos cargados desde la interfaz.
    nombre = archivo if isinstance(archivo, (str, Path)) else getattr(archivo, "name", "")
    extension = Path(nombre).suffix.lower()

    # Usa la lectura de Excel para XLSX y la detección automática de separador para CSV.
    if extension == ".xlsx":
        return pd.read_excel(archivo)
    if extension == ".csv":
        return pd.read_csv(archivo, sep=None, engine="python")

    raise ValueError("Formato no compatible: use un archivo CSV o Excel .xlsx.")


def validar_dca(df: pd.DataFrame, col_trat: str, col_resp: str) -> list[str]:
    """Valida las columnas y los datos requeridos para analizar un DCA.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna de respuesta numérica.

    Returns:
        Lista de errores en español; queda vacía si los datos son válidos.
    """
    errores: list[str] = []

    # Comprueba primero la estructura para no intentar analizar columnas inexistentes.
    faltantes = [col for col in (col_trat, col_resp) if col not in df.columns]
    if faltantes:
        errores.append(f"Faltan las columnas requeridas: {', '.join(faltantes)}.")
        return errores

    # Detecta valores ausentes porque cada unidad experimental debe aportar tratamiento y respuesta.
    if df[col_trat].isna().any():
        errores.append(f"La columna de tratamientos «{col_trat}» contiene datos faltantes.")
    if df[col_resp].isna().any():
        errores.append(f"La columna de respuesta «{col_resp}» contiene datos faltantes.")

    # Acepta valores numéricos o texto convertible a número, pero rechaza respuestas no interpretables.
    respuesta_numerica = pd.to_numeric(df[col_resp], errors="coerce")
    no_convertibles = df[col_resp].notna() & respuesta_numerica.isna()
    if no_convertibles.any():
        errores.append(f"La respuesta «{col_resp}» debe ser numérica.")

    # Cuenta los niveles y réplicas para asegurar que se pueda comparar la variación entre tratamientos.
    tratamientos = df[col_trat].dropna()
    if tratamientos.nunique() < 2:
        errores.append("El DCA requiere al menos 2 tratamientos.")
    conteos = tratamientos.value_counts()
    con_pocas_replicas = conteos[conteos < 2]
    if not con_pocas_replicas.empty:
        nombres = ", ".join(str(tratamiento) for tratamiento in con_pocas_replicas.index)
        errores.append(f"Cada tratamiento debe tener al menos 2 réplicas; revise: {nombres}.")

    return errores


def ajustar_dca(
    df: pd.DataFrame, col_trat: str, col_resp: str
) -> RegressionResultsWrapper:
    """Ajusta el modelo lineal de un diseño completamente al azar.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna de respuesta numérica.

    Returns:
        Modelo OLS ajustado con la respuesta en función del tratamiento.
    """
    # Q() protege nombres de columnas con espacios, tildes o caracteres especiales en la fórmula.
    respuesta = json.dumps(col_resp, ensure_ascii=False)
    tratamiento = json.dumps(col_trat, ensure_ascii=False)

    # Ajusta Y_ij = μ + τ_i + ε_ij para comparar las medias de los tratamientos.
    return ols(f"Q({respuesta}) ~ C(Q({tratamiento}))", data=df).fit()


def tabla_anova(modelo: RegressionResultsWrapper) -> pd.DataFrame:
    """Calcula y organiza la tabla ANOVA tipo II para el modelo ajustado.

    Args:
        modelo: Modelo OLS de un DCA, producido por :func:`ajustar_dca`.

    Returns:
        Tabla con las fuentes Tratamientos, Error y Total.
    """
    # La suma de cuadrados particiona la variación total en tratamientos y error: SCT = SCTrat + SCE.
    tabla = anova_lm(modelo, typ=2)
    filas = {}
    for fuente, fila in tabla.iterrows():
        if fuente == "Residual":
            nombre = "Error"
        elif "Intercept" not in str(fuente):
            nombre = "Tratamientos"
        else:
            continue
        filas[nombre] = fila

    if "Tratamientos" not in filas or "Error" not in filas:
        raise ValueError("El modelo no contiene las fuentes de variación de un DCA.")

    # Calcula cuadrados medios como SC/gl; el cuadrado medio del error estima la varianza residual.
    registros = []
    for fuente in ("Tratamientos", "Error"):
        fila = filas[fuente]
        gl = int(fila["df"])
        sc = float(fila["sum_sq"])
        registros.append(
            {
                "Fuente": fuente,
                "gl": gl,
                "SC": sc,
                "CM": sc / gl,
                "F": fila.get("F", np.nan),
                "p-valor": fila.get("PR(>F)", np.nan),
            }
        )

    # Calcula SC total corregida alrededor de la media general: SCTotal = SCTrat + SCE.
    registros.append(
        {
            "Fuente": "Total",
            "gl": int(modelo.df_model + modelo.df_resid),
            "SC": sum(registro["SC"] for registro in registros),
            "CM": np.nan,
            "F": np.nan,
            "p-valor": np.nan,
        }
    )
    return pd.DataFrame(registros, columns=["Fuente", "gl", "SC", "CM", "F", "p-valor"])


def resumen_tratamientos(
    df: pd.DataFrame, col_trat: str, col_resp: str
) -> pd.DataFrame:
    """Resume el número de réplicas y la respuesta por tratamiento.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna de respuesta numérica.

    Returns:
        DataFrame con n, total, media y desviación estándar por tratamiento.
    """
    # Calcula n_i, total_i, media_i y s_i para describir la respuesta observada en cada tratamiento.
    resumen = df.groupby(col_trat, dropna=False)[col_resp].agg(
        n="count",
        total="sum",
        media="mean",
        desviacion_estandar="std",
    )
    return resumen.rename_axis("Tratamiento").reset_index().rename(
        columns={"desviacion_estandar": "desviación estándar"}
    )


def coeficiente_variacion(
    modelo: RegressionResultsWrapper, df: pd.DataFrame, col_resp: str
) -> float:
    """Calcula el coeficiente de variación residual del DCA.

    Args:
        modelo: Modelo OLS ajustado.
        df: Datos del experimento.
        col_resp: Nombre de la columna de respuesta numérica.

    Returns:
        Coeficiente de variación expresado como porcentaje.
    """
    # Divide la desviación residual por la media general para expresar el error en escala relativa.
    media_general = pd.to_numeric(df[col_resp]).mean()
    if media_general == 0:
        raise ValueError("No se puede calcular el CV porque la media general es cero.")

    # CV = sqrt(CME) / media general * 100; CME estima la variación no explicada por tratamientos.
    return float(np.sqrt(modelo.mse_resid) / media_general * 100)


def tukey(
    df: pd.DataFrame,
    col_trat: str,
    col_resp: str,
    alfa: float = 0.05,
) -> tuple[pd.DataFrame, float]:
    """Compara las medias con Tukey y calcula una diferencia mínima significativa.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna de respuesta numérica.
        alfa: Nivel de significancia entre 0 y 1.

    Returns:
        Una tabla de comparaciones de Tukey en español y la DMS.

    Raises:
        ValueError: Si alfa no está entre 0 y 1.
    """
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre 0 y 1.")

    # Compara las medias de pares de tratamientos y ajusta el error por comparaciones múltiples.
    resultado = pairwise_tukeyhsd(
        endog=df[col_resp],
        groups=df[col_trat],
        alpha=alfa,
    )
    datos_resumen = resultado.summary().data
    comparaciones = pd.DataFrame(datos_resumen[1:], columns=datos_resumen[0]).rename(
        columns={
            "group1": "Tratamiento 1",
            "group2": "Tratamiento 2",
            "meandiff": "Diferencia de medias",
            "p-adj": "p-valor ajustado",
            "lower": "Límite inferior",
            "upper": "Límite superior",
            "reject": "Diferencia significativa",
        }
    )

    # Obtiene CME, gl del error y réplicas por tratamiento a partir del modelo de un factor.
    modelo = ajustar_dca(df, col_trat, col_resp)
    conteos = df.groupby(col_trat)[col_resp].count()
    numero_tratamientos = len(conteos)
    if conteos.nunique() == 1:
        replicas = float(conteos.iloc[0])
    else:
        # En datos desbalanceados se usa la media armónica de réplicas como aproximación común.
        warnings.warn(
            "El diseño no está balanceado; la DMS calculada es aproximada.",
            UserWarning,
            stacklevel=2,
        )
        replicas = float(numero_tratamientos / (1 / conteos).sum())

    # DMS = q(1 - alfa; t; glE) * sqrt(CME / r), con q de rango studentizado.
    cuantil = studentized_range.ppf(
        1 - alfa, numero_tratamientos, modelo.df_resid
    )
    dms = float(cuantil * np.sqrt(modelo.mse_resid / replicas))
    return comparaciones, dms


def interpretar_dca(tabla: pd.DataFrame, alfa: float = 0.05) -> str:
    """Interpreta la prueba F de tratamientos de la tabla ANOVA.

    Args:
        tabla: Tabla ANOVA con las columnas Fuente y p-valor.
        alfa: Nivel de significancia entre 0 y 1.

    Returns:
        Explicación sencilla de la decisión sobre la hipótesis nula.

    Raises:
        ValueError: Si alfa es inválido o la tabla no contiene el resultado requerido.
    """
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre 0 y 1.")
    if not {"Fuente", "p-valor"}.issubset(tabla.columns):
        raise ValueError("La tabla debe incluir las columnas «Fuente» y «p-valor».")

    # Contrasta H0: todas las medias de tratamiento son iguales, usando el p-valor de tratamientos.
    fila = tabla.loc[tabla["Fuente"] == "Tratamientos", "p-valor"]
    if fila.empty or pd.isna(fila.iloc[0]):
        raise ValueError("La tabla no contiene un p-valor válido para Tratamientos.")
    p_valor = float(fila.iloc[0])

    # Compara p con alfa para decidir si la evidencia del ensayo permite rechazar H0.
    if p_valor <= alfa:
        return (
            f"Se rechaza H0 (p = {p_valor:.4g} ≤ α = {alfa:g}): hay evidencia "
            "de diferencias entre las medias de los tratamientos. Para decidir "
            "cuál conviene, revise sus medias, las comparaciones múltiples y "
            "la relevancia agronómica."
        )
    return (
        f"No se rechaza H0 (p = {p_valor:.4g} > α = {alfa:g}): el ensayo no "
        "aporta evidencia suficiente de diferencias entre las medias. Esto "
        "no demuestra que sean idénticas; considere la precisión del ensayo "
        "y el contexto agronómico."
    )
