"""Interfaz de chat del agente de costos. Correr con: streamlit run agent/app.py"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent))
from agente import Agente  # noqa: E402
from herramientas import mensual, pronostico  # noqa: E402

st.set_page_config(page_title="Agente de costos de equipos", page_icon="🏗️", layout="wide")

AZUL, AZUL_OSCURO, VERDE, NARANJA = "#2563EB", "#0F2A4A", "#16A34A", "#EA580C"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def mes_txt(fecha):
    return f"{MESES[fecha.month - 1]}-{fecha.year}"


st.markdown(f"""
<style>
.block-container {{padding-top: 1.5rem; max-width: 1200px;}}

.encabezado {{
    background: linear-gradient(120deg, {AZUL_OSCURO} 0%, {AZUL} 100%);
    color: white; padding: 1.4rem 1.8rem; border-radius: 16px; margin-bottom: 1rem;
}}
.encabezado h1 {{color: white; font-size: 1.9rem; margin: 0;}}
.encabezado p {{color: #DCE7F7; margin: .35rem 0 .8rem 0;}}
.etiqueta {{
    display: inline-block; background: rgba(255,255,255,.15); color: white;
    padding: .2rem .7rem; border-radius: 999px; font-size: .8rem; margin-right: .4rem;
}}

.tarjeta {{
    background: white; border-radius: 14px; padding: 1rem 1.1rem; border: 1px solid #E2E8F0;
    border-left: 5px solid {AZUL}; box-shadow: 0 1px 3px rgba(15,42,74,.06); height: 100%;
}}
.tarjeta .titulo {{color: #64748B; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em;}}
.tarjeta .valor {{color: {AZUL_OSCURO}; font-size: 1.7rem; font-weight: 700; margin: .15rem 0;}}
.tarjeta .detalle {{color: #475569; font-size: .85rem;}}

/* burbujas del chat */
[data-testid="stChatMessage"] {{border-radius: 16px; padding: .9rem 1.1rem; margin-bottom: .6rem;}}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
    background: {AZUL}; color: white; flex-direction: row-reverse;
    width: fit-content; max-width: 75%; margin-left: auto;
}}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {{color: white;}}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
    background: white; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(15,42,74,.06); margin-right: 8%;
}}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) strong {{color: {AZUL};}}
[data-testid="stChatMessageAvatarUser"] {{background: {AZUL_OSCURO};}}
[data-testid="stChatMessageAvatarAssistant"] {{background: {VERDE};}}

/* caja para escribir */
[data-testid="stChatInput"] {{border: 2px solid {AZUL}; border-radius: 14px; background: white;}}

/* botones de preguntas sugeridas */
.stMainBlockContainer .stButton button {{
    border-radius: 999px; border: 1px solid #BFD3F5; background: white; color: {AZUL_OSCURO};
    text-align: left; width: 100%;
}}
.stMainBlockContainer .stButton button:hover {{background: #E8EFFA; border-color: {AZUL}; color: {AZUL};}}

.herramienta {{
    display: inline-block; background: #ECFDF3; color: {VERDE}; border: 1px solid #BBF7D0;
    padding: .1rem .6rem; border-radius: 999px; font-size: .75rem; margin: .3rem .3rem 0 0;
}}

[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{color: white;}}
</style>
""", unsafe_allow_html=True)

NOMBRES = {
    "consultar_pronostico": "📈 pronóstico",
    "consultar_historico": "🗂️ histórico",
    "simular_escenario": "🧪 escenario",
    "resultados_modelo": "📘 metodología",
    "buscar_noticias": "📰 noticias",
}

EJEMPLOS = [
    "¿Cuánto costará cada equipo en los próximos 6 meses?",
    "¿Qué materias primas explican el precio de cada equipo?",
    "Si Y sube 15%, ¿cuánto impacta a cada equipo?",
    "¿Qué dicen las noticias del aluminio y cómo afectaría al Equipo2?",
    "¿Cuál equipo tiene más incertidumbre en su costo?",
    "¿Por qué el horizonte recomendado es de 6 meses?",
]


def chips(usadas):
    if usadas:
        conteo = {}
        for u in usadas:
            conteo[u["herramienta"]] = conteo.get(u["herramienta"], 0) + 1
        html = "".join(f'<span class="herramienta">{NOMBRES.get(h, h)}{f" ×{n}" if n > 1 else ""}</span>'
                       for h, n in conteo.items())
        st.markdown(html, unsafe_allow_html=True)
        with st.expander("Ver detalle de las herramientas"):
            st.json(usadas)


# ---------- barra lateral ----------
with st.sidebar:
    st.markdown("## 🏗️ Agente de costos")
    st.caption("Azure OpenAI · gpt-5.4-mini")
    st.markdown(
        "Responde preguntas sobre el costo de los equipos y lo complementa con noticias del mercado.\n\n"
        "**Herramientas**\n"
        "- 📈 Pronóstico (12 meses)\n"
        "- 🗂️ Histórico\n"
        "- 🧪 Escenarios de materias primas\n"
        "- 📘 Metodología\n"
        "- 📰 Noticias de la web"
    )
    st.divider()
    if st.button("🔄 Nueva conversación", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ---------- encabezado ----------
ini, fin = pronostico.index[0], pronostico.index[-1]
st.markdown(f"""
<div class="encabezado">
  <h1>🏗️ Agente de costos de equipos</h1>
  <p>Pronóstico del costo de Equipo1 y Equipo2 a partir de las materias primas X, Y y Z,
     con contexto de mercado en tiempo real.</p>
  <span class="etiqueta">Pronóstico {mes_txt(ini)} a {mes_txt(fin)}</span>
  <span class="etiqueta">Horizonte recomendado: 6 meses</span>
  <span class="etiqueta">Intervalos de 90%</span>
</div>
""", unsafe_allow_html=True)

# ---------- tarjetas ----------
def tarjeta(columna, titulo, valor, detalle, color=AZUL):
    columna.markdown(f"""
    <div class="tarjeta" style="border-left-color:{color}">
      <div class="titulo">{titulo}</div>
      <div class="valor">{valor}</div>
      <div class="detalle">{detalle}</div>
    </div>""", unsafe_allow_html=True)


c1, c2, c3, c4 = st.columns(4)
for col, eq, color in [(c1, "Equipo1", AZUL), (c2, "Equipo2", VERDE)]:
    p = pronostico[eq].iloc[5]
    tarjeta(col, f"{eq} · {mes_txt(pronostico.index[5])}", f"{p['P50']:,.0f}",
            f"Rango 90%: {p['P5']:,.0f} – {p['P95']:,.0f}", color)
tarjeta(c3, "Fórmula Equipo1", "0.2·X + 0.8·Y", "Z no influye", AZUL_OSCURO)
tarjeta(c4, "Fórmula Equipo2", "(X+Y+Z) / 3", "Mismo mes, sin rezagos", NARANJA)
st.write("")

tab_chat, tab_pronostico, tab_agente = st.tabs(["💬 Chat con el agente", "📈 Pronóstico", "🧠 ¿Modelo o agente?"])

# ---------- chat ----------
with tab_chat:
    if "agente" not in st.session_state:
        st.session_state.agente = Agente()
        st.session_state.historial = []

    pregunta = None
    if not st.session_state.historial:
        st.markdown("**Prueba con alguna de estas preguntas:**")
        cols = st.columns(2)
        for i, ej in enumerate(EJEMPLOS):
            if cols[i % 2].button(ej, key=f"ej{i}"):
                pregunta = ej

    for m in st.session_state.historial:
        with st.chat_message(m["rol"]):
            st.markdown(m["texto"])
            if m["rol"] == "assistant":
                chips(m.get("herramientas"))

    escrita = st.chat_input("Escribe tu pregunta sobre costos, escenarios o el mercado…")
    pregunta = escrita or pregunta

    if pregunta:
        st.session_state.historial.append({"rol": "user", "texto": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Analizando…"):
                try:
                    respuesta, usadas = st.session_state.agente.preguntar(pregunta)
                except Exception as e:
                    respuesta, usadas = f"Ocurrió un error al consultar el modelo: {e}", []
            st.markdown(respuesta)
            chips(usadas)
        st.session_state.historial.append({"rol": "assistant", "texto": respuesta, "herramientas": usadas})
        st.rerun()

# ---------- pronóstico ----------
with tab_pronostico:
    eq = st.radio("Equipo", ["Equipo1", "Equipo2"], horizontal=True)
    hist = mensual[eq].loc["2021":].rename("valor").reset_index().rename(columns={"Date": "fecha"})
    pr = pronostico[eq].reset_index().rename(columns={pronostico.index.name or "index": "fecha"})
    pr = pr.rename(columns={pr.columns[0]: "fecha"})

    eje_x = alt.X("fecha:T", title=None, axis=alt.Axis(
        labelExpr="['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][month(datum.value)]"
                  " + '-' + timeFormat(datum.value, '%y')"))
    base = alt.Chart(pr).encode(x=eje_x)
    banda90 = base.mark_area(opacity=.18, color=AZUL).encode(y=alt.Y("P5:Q", title="Costo"), y2="P95:Q")
    banda50 = base.mark_area(opacity=.35, color=AZUL).encode(y="P25:Q", y2="P75:Q")
    central = base.mark_line(color=AZUL, strokeWidth=2.5).encode(
        y="P50:Q",
        tooltip=[alt.Tooltip("fecha:T", title="mes", format="%m/%Y"), alt.Tooltip("P50:Q", format=",.1f"),
                 alt.Tooltip("P5:Q", format=",.1f"), alt.Tooltip("P95:Q", format=",.1f")])
    historico = alt.Chart(hist).mark_line(color=AZUL_OSCURO, strokeWidth=2).encode(
        x=eje_x, y=alt.Y("valor:Q", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("fecha:T", title="mes", format="%m/%Y"), alt.Tooltip("valor:Q", title="real", format=",.1f")])
    corte = alt.Chart(pd.DataFrame({"fecha": [pronostico.index[5]]})).mark_rule(
        color="#94A3B8", strokeDash=[4, 4]).encode(x="fecha:T")

    st.altair_chart((banda90 + banda50 + historico + central + corte).properties(height=380).interactive(),
                    use_container_width=True)
    st.caption("Línea oscura: histórico · Línea azul: escenario central · Bandas: rangos de 50% y 90% · "
               "Punteada: fin del horizonte recomendado (6 meses)")

    tabla = pronostico[eq].head(6).copy()
    tabla.index = [mes_txt(f) for f in tabla.index]
    tabla["Rango 90% (% del P50)"] = (tabla["P95"] - tabla["P5"]) / tabla["P50"] * 100
    st.dataframe(tabla.round(1), use_container_width=True)

# ---------- explicación ----------
with tab_agente:
    a, b = st.columns(2)
    a.markdown(f"""
    <div class="tarjeta" style="border-left-color:{AZUL_OSCURO}">
      <div class="titulo">Modelo de IA convencional</div>
      <p>Recibe una entrada y devuelve una salida. En este proyecto, la <b>regresión lineal</b> recibe los precios
      de X, Y y Z y devuelve el costo de cada equipo. No decide nada: siempre hace lo mismo.</p>
    </div>""", unsafe_allow_html=True)
    b.markdown(f"""
    <div class="tarjeta" style="border-left-color:{VERDE}">
      <div class="titulo">Agente de IA</div>
      <p>Tiene un objetivo y decide cómo alcanzarlo: interpreta la pregunta, elige qué herramientas usar,
      las ejecuta, revisa los resultados y redacta la respuesta.</p>
    </div>""", unsafe_allow_html=True)
    st.write("")
    st.markdown("""
| Concepto | Qué significa | Cómo se ve en este agente |
|---|---|---|
| **Autonomía** | Decide los pasos sin que se los indiquen | Elige entre 5 herramientas y en qué orden usarlas |
| **Uso de herramientas** | Ejecuta funciones externas | Pronóstico, histórico, simulación de escenarios, metodología y búsqueda web |
| **Memoria** | Recuerda el contexto | Entiende preguntas de seguimiento como "¿y si además Z baja 10%?" |
| **Capacidad de acción** | Hace, no solo responde | Corre simulaciones y busca noticias antes de contestar |
""")
