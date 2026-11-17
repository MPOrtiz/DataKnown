"""Interfaz de chat del agente de costos. Correr con: streamlit run agent/app.py"""
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent))
from agente import Agente  # noqa: E402
from herramientas import pronostico  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="Agente de costos de equipos", page_icon="🏗️", layout="wide")

EJEMPLOS = [
    "¿Cuánto costará cada equipo en los próximos 6 meses?",
    "¿Qué materias primas explican el precio de cada equipo?",
    "Si Y sube 15%, ¿cuánto impacta a cada equipo?",
    "¿Qué dicen las noticias del aluminio y cómo afectaría al Equipo2?",
    "¿Por qué el horizonte recomendado es de 6 meses?",
]

with st.sidebar:
    st.header("Sobre el agente")
    st.markdown(
        "Responde preguntas sobre el análisis de costos de los equipos y lo complementa con noticias del mercado.\n\n"
        "**Herramientas que puede usar:**\n"
        "- Consultar el pronóstico (sep-2023 a ago-2024)\n"
        "- Consultar el histórico\n"
        "- Simular escenarios de materias primas\n"
        "- Resumen de la metodología\n"
        "- Buscar noticias en la web"
    )
    with st.expander("¿Modelo de IA o agente?"):
        st.markdown(
            "Un **modelo de IA** recibe una entrada y devuelve una salida: el modelo de regresión de este proyecto "
            "recibe precios de X, Y, Z y devuelve el costo de los equipos.\n\n"
            "Un **agente** tiene un objetivo y decide cómo alcanzarlo:\n"
            "- **Autonomía:** decide qué herramientas usar y en qué orden según la pregunta.\n"
            "- **Herramientas:** ejecuta funciones (el pronóstico, simulaciones, búsqueda web).\n"
            "- **Memoria:** recuerda la conversación para responder preguntas de seguimiento.\n"
            "- **Acción:** no solo responde, ejecuta cálculos y búsquedas para llegar a la respuesta."
        )
    figura = RAIZ / "reports" / "figures" / "04_pronostico.png"
    if figura.exists():
        st.image(str(figura), caption="Pronóstico con rangos de 50% y 90%")
    if st.button("Nueva conversación"):
        st.session_state.clear()
        st.rerun()

st.title("🏗️ Agente de costos de equipos")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
ini, fin = pronostico.index[0], pronostico.index[-1]
st.caption(f"Pronóstico disponible de {MESES[ini.month - 1]}-{ini.year} a {MESES[fin.month - 1]}-{fin.year}. "
           "Horizonte recomendado: 6 meses.")

if "agente" not in st.session_state:
    st.session_state.agente = Agente()
    st.session_state.historial = []

for m in st.session_state.historial:
    with st.chat_message(m["rol"]):
        st.markdown(m["texto"])
        if m.get("herramientas"):
            with st.expander("Herramientas usadas"):
                st.json(m["herramientas"])

pregunta = st.chat_input("Escribe tu pregunta")
if not st.session_state.historial and not pregunta:
    st.write("Prueba con alguna de estas preguntas:")
    for ej in EJEMPLOS:
        if st.button(ej):
            pregunta = ej

if pregunta:
    st.session_state.historial.append({"rol": "user", "texto": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)
    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                respuesta, usadas = st.session_state.agente.preguntar(pregunta)
            except Exception as e:
                respuesta, usadas = f"Ocurrió un error al consultar el modelo: {e}", []
        st.markdown(respuesta)
        if usadas:
            with st.expander("Herramientas usadas"):
                st.json(usadas)
    st.session_state.historial.append({"rol": "assistant", "texto": respuesta, "herramientas": usadas})
