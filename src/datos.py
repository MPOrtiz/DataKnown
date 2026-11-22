"""Lectura y limpieza de los datos del caso."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# 2014-03-25: Z = 1911.97, error de captura (ver notebook 1)
FECHAS_EXCLUIDAS = ["2014-03-25"]


def leer_x():
    df = pd.read_csv(RAW / "X.csv", parse_dates=["Date"])
    return df.set_index("Date").sort_index()["Price"].rename("X")


def leer_y():
    # viene con ; como separador, coma decimal y fechas dd/mm/yyyy
    df = pd.read_csv(RAW / "Y.csv", sep=";", decimal=",", encoding="utf-8-sig")
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    return df.set_index("Date").sort_index()["Price"].rename("Y")


def leer_z():
    df = pd.read_csv(RAW / "Z.csv", parse_dates=["Date"])
    return df.set_index("Date").sort_index()["Price"].rename("Z")


def leer_equipos():
    df = pd.read_csv(RAW / "historico_equipos.csv", parse_dates=["Date"], index_col="Date")
    df.columns = ["X", "Y", "Z", "Equipo1", "Equipo2"]
    return df.sort_index()


def comparar_con_fuentes(df):
    """Revisa que X, Y, Z del histórico sean iguales a los de sus archivos originales."""
    res = {}
    for col, serie in [("X", leer_x()), ("Y", leer_y()), ("Z", leer_z())]:
        dif = (df[col] - serie.reindex(df.index)).abs()
        res[col] = {"sin_dato_en_fuente": dif.isna().sum(), "dif_maxima": dif.max()}
    return pd.DataFrame(res).T


def quitar_outliers(df):
    return df.drop(index=pd.to_datetime(FECHAS_EXCLUIDAS), errors="ignore")


def agregar(df, freq="MS"):
    # promedio del periodo; MS = mensual, W-FRI = semanal
    return df.resample(freq).mean().dropna()
