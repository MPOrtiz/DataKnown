"""Herramientas que el agente puede usar."""
import sys
from pathlib import Path

import pandas as pd
import statsmodels.api as sm

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src import datos  # noqa: E402

EQUIPOS = ["Equipo1", "Equipo2"]
INSUMOS = ["X", "Y", "Z"]

mensual = pd.read_csv(datos.PROCESSED / "equipos_mensual.csv", index_col="Date", parse_dates=True)
pronostico = pd.read_csv(datos.PROCESSED / "pronostico_12m.csv", header=[0, 1], index_col=0, parse_dates=True)

# fórmula de cada equipo (regresión lineal sin constante, notebooks 2 y 3)
pesos = {
    "Equipo1": sm.OLS(mensual["Equipo1"], mensual[["X", "Y"]]).fit().params,
    "Equipo2": sm.OLS(mensual["Equipo2"], mensual[["X", "Y", "Z"]]).fit().params,
}

# elasticidad: % que se mueve el equipo por cada 1% de su insumo (con los precios del último mes)
ultimo = mensual.iloc[-1]
elasticidades = {eq: {i: round(float(p[i] * ultimo[i] / ultimo[eq]), 2) for i in p.index} for eq, p in pesos.items()}

# resultados clave de los notebooks 3 y 4
RESUMEN = {
    "datos": "Precios mensuales (promedio del mes) de ene-2010 a ago-2023. Se excluyó el 2014-03-25 por un error de captura en Z.",
    "formula": {eq: {k: round(float(v), 3) for k, v in p.items()} for eq, p in pesos.items()},
    "interpretacion": "Equipo1 = 0.2·X + 0.8·Y; Equipo2 = (X + Y + Z) / 3. Z no influye en Equipo1. "
                      "Los equipos reaccionan a sus insumos en el mismo mes, sin rezagos. "
                      "Los pesos son en unidades de precio, no en porcentaje: el impacto % depende del nivel de precio de cada insumo.",
    "elasticidades": elasticidades,
    "elasticidades_nota": "Cambio % del equipo por cada 1% de cambio en el insumo, con los precios del último mes.",
    "modelo_elegido": "Regresión lineal. Se compararon 8 modelos (lineal, Ridge, Lasso, árbol, Random Forest, "
                      "Gradient Boosting, KNN, SVR); los lineales tuvieron ~0.27% de error y los de árboles 9-18 veces más.",
    "pronostico_insumos": "Simulación de 5,000-10,000 escenarios con block bootstrap de los retornos conjuntos de X, Y, Z; "
                          "volatilidad ampliada 1.3x para calibrar los intervalos.",
    "error_por_horizonte_MAPE": {"1 mes": "4-5%", "3 meses": "9-12%", "6 meses": "13-16%", "12 meses": "20-25%"},
    "cobertura_intervalo_90": "87-89% en el backtest",
    "horizonte_recomendado": "6 meses, actualizando el pronóstico cada mes. Los meses 7 a 12 son escenarios.",
    "ultimo_dato": str(mensual.index[-1].date()),
}


def consultar_pronostico(serie, mes=None):
    """Percentiles del pronóstico para un equipo o insumo, de un mes o de los 12."""
    if serie not in EQUIPOS + INSUMOS:
        return {"error": f"Serie desconocida: {serie}. Opciones: {EQUIPOS + INSUMOS}"}
    tabla = pronostico[serie].round(1)
    if mes:
        tabla = tabla[tabla.index.strftime("%Y-%m") == mes[:7]]
        if tabla.empty:
            return {"error": f"Sin pronóstico para {mes}. Rango disponible: "
                             f"{pronostico.index[0]:%Y-%m} a {pronostico.index[-1]:%Y-%m}"}
    tabla.index = tabla.index.strftime("%Y-%m")
    return {"serie": serie, "unidades": "precio promedio mensual",
            "nota": "P50 = escenario central; P5-P95 = rango de 90%",
            "pronostico": tabla.to_dict(orient="index")}


def consultar_historico(serie, meses=12):
    """Últimos valores mensuales observados de un equipo o insumo."""
    if serie not in EQUIPOS + INSUMOS:
        return {"error": f"Serie desconocida: {serie}. Opciones: {EQUIPOS + INSUMOS}"}
    s = mensual[serie].tail(int(meses)).round(1)
    s.index = s.index.strftime("%Y-%m")
    total = mensual[serie]
    return {"serie": serie, "valores": s.to_dict(),
            "minimo_historico": [round(total.min(), 1), f"{total.idxmin():%Y-%m}"],
            "maximo_historico": [round(total.max(), 1), f"{total.idxmax():%Y-%m}"]}


def simular_escenario(cambios, mes=None):
    """Costo de los equipos si los insumos cambian un % respecto al escenario central.

    cambios: dict como {"Y": 10, "X": -5} (porcentajes).
    """
    malos = [k for k in cambios if k not in INSUMOS]
    if malos:
        return {"error": f"Insumos desconocidos: {malos}. Opciones: {INSUMOS}"}
    fecha = pronostico.index[0] if mes is None else pd.Timestamp(mes[:7] + "-01")
    if fecha not in pronostico.index:
        return {"error": f"Mes fuera del pronóstico ({pronostico.index[0]:%Y-%m} a {pronostico.index[-1]:%Y-%m})"}

    base = {ins: pronostico.loc[fecha, (ins, "P50")] for ins in INSUMOS}
    nuevo = {ins: base[ins] * (1 + cambios.get(ins, 0) / 100) for ins in INSUMOS}

    resultado = {}
    for eq, p in pesos.items():
        cambio = sum(p[i] * nuevo[i] for i in p.index) / sum(p[i] * base[i] for i in p.index) - 1
        central = pronostico.loc[fecha, (eq, "P50")]  # mismo P50 que consultar_pronostico
        resultado[eq] = {"escenario_central": round(float(central), 1),
                         "con_cambios": round(float(central * (1 + cambio)), 1),
                         "diferencia_pct": round(float(cambio) * 100, 2)}
    return {"mes": f"{fecha:%Y-%m}", "cambios_aplicados_pct": cambios, "resultado": resultado}


def resultados_modelo():
    """Resumen de la metodología y los resultados del análisis."""
    return RESUMEN


def buscar_noticias(consulta, max_resultados=5):
    """Noticias recientes de la web sobre un tema de mercado."""
    from ddgs import DDGS

    try:
        noticias = DDGS().news(consulta, max_results=int(max_resultados))
    except Exception as e:  # sin internet, límite de peticiones, etc.
        return {"error": f"No se pudo buscar: {e}"}
    return {"consulta": consulta,
            "noticias": [{"titulo": n.get("title"), "fecha": n.get("date"), "fuente": n.get("source"),
                          "resumen": n.get("body"), "url": n.get("url")} for n in noticias]}


FUNCIONES = {
    "consultar_pronostico": consultar_pronostico,
    "consultar_historico": consultar_historico,
    "simular_escenario": simular_escenario,
    "resultados_modelo": resultados_modelo,
    "buscar_noticias": buscar_noticias,
}

_serie = {"type": "string", "enum": EQUIPOS + INSUMOS,
          "description": "Equipo1, Equipo2 o una materia prima (X, Y, Z)"}

ESQUEMAS = [
    {"type": "function", "function": {
        "name": "consultar_pronostico",
        "description": "Pronóstico mensual (P5, P25, P50, P75, P95) de un equipo o materia prima, "
                       "de sep-2023 a ago-2024. Sin mes devuelve los 12 meses.",
        "parameters": {"type": "object", "properties": {
            "serie": _serie,
            "mes": {"type": "string", "description": "Mes en formato AAAA-MM. Opcional."}},
            "required": ["serie"]}}},
    {"type": "function", "function": {
        "name": "consultar_historico",
        "description": "Últimos precios mensuales observados de un equipo o materia prima, con su mínimo y máximo histórico.",
        "parameters": {"type": "object", "properties": {
            "serie": _serie,
            "meses": {"type": "integer", "description": "Cuántos meses hacia atrás. Default 12."}},
            "required": ["serie"]}}},
    {"type": "function", "function": {
        "name": "simular_escenario",
        "description": "Calcula el costo de los equipos si una o varias materias primas suben o bajan un porcentaje "
                       "respecto al escenario central del pronóstico. Úsala para preguntas tipo '¿y si X sube 10%?'.",
        "parameters": {"type": "object", "properties": {
            "cambios": {"type": "object", "description": "Cambio en % por insumo, ej. {\"Y\": 10, \"Z\": -5}",
                        "additionalProperties": {"type": "number"}},
            "mes": {"type": "string", "description": "Mes AAAA-MM. Default: el primer mes del pronóstico."}},
            "required": ["cambios"]}}},
    {"type": "function", "function": {
        "name": "resultados_modelo",
        "description": "Resumen de la metodología: fórmula de cada equipo, modelo elegido, error por horizonte, "
                       "calibración de intervalos y horizonte recomendado.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "buscar_noticias",
        "description": "Busca noticias recientes en la web (precios de commodities, construcción, economía). "
                       "Úsala para complementar el pronóstico con contexto de mercado.",
        "parameters": {"type": "object", "properties": {
            "consulta": {"type": "string", "description": "Términos de búsqueda, de preferencia en inglés"},
            "max_resultados": {"type": "integer", "description": "Default 5"}},
            "required": ["consulta"]}}},
]
