"""
Carga, validación y limpieza de los datos.
Archivos:
- X.csv: separador ',', fechas ISO, orden descendente.
- Y.csv: separador ';', decimal ',', fechas dd/mm/aaaa, codificación con BOM.
- Z.csv: columnas invertidas (Price, Date).
- historico_equipos.csv: X, Y, Z y precios de Equipo1 y Equipo2 ya unidos.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# Fechas excluidas del entrenamiento, con su justificación (ver notebooks/01_eda.ipynb)
OUTLIERS = {
    "2014-03-25": (
        "Z = 1911.97 (+13% y regresa al día siguiente). El aluminio LME se movió <1% ese día: "
        "error de captura. Equipo2 refleja el error, por lo que se excluye la fila completa."
    ),
}


def cargar_x() -> pd.Series:
    df = pd.read_csv(RAW / "X.csv", parse_dates=["Date"])
    return df.set_index("Date").sort_index()["Price"].rename("X")


def cargar_y() -> pd.Series:
    df = pd.read_csv(RAW / "Y.csv", sep=";", decimal=",", encoding="utf-8-sig")
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
    return df.set_index("Date").sort_index()["Price"].rename("Y")


def cargar_z() -> pd.Series:
    df = pd.read_csv(RAW / "Z.csv", parse_dates=["Date"])
    return df.set_index("Date").sort_index()["Price"].rename("Z")


def cargar_equipos() -> pd.DataFrame:
    """Dataset principal: X, Y, Z, Equipo1, Equipo2 (diario, días hábiles)."""
    df = pd.read_csv(RAW / "historico_equipos.csv", parse_dates=["Date"])
    df = df.set_index("Date").sort_index()
    df.columns = ["X", "Y", "Z", "Equipo1", "Equipo2"]
    return df


def validar_consistencia(equipos: pd.DataFrame) -> pd.DataFrame:
    """Compara X, Y, Z dentro de historico_equipos contra sus archivos fuente."""
    fuentes = {"X": cargar_x(), "Y": cargar_y(), "Z": cargar_z()}
    filas = []
    for nombre, serie in fuentes.items():
        unido = equipos[[nombre]].join(serie.rename("fuente"), how="left")
        diff = (unido[nombre] - unido["fuente"]).abs()
        filas.append({
            "serie": nombre,
            "fechas_sin_fuente": int(unido["fuente"].isna().sum()),
            "pct_coincide": round(float((diff < 1e-6).mean() * 100), 2),
            "dif_max": float(diff.max()),
        })
    return pd.DataFrame(filas)


def limpiar(equipos: pd.DataFrame) -> pd.DataFrame:
    """Excluye las fechas marcadas como outlier."""
    fechas = pd.to_datetime(list(OUTLIERS))
    return equipos.drop(index=fechas, errors="ignore")


def agregar(equipos: pd.DataFrame, frecuencia: str = "MS") -> pd.DataFrame:
    """Promedio por periodo. 'MS' = mensual (inicio de mes), 'W-FRI' = semanal."""
    return equipos.resample(frecuencia).mean().dropna()