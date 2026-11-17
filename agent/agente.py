"""Agente de costos: LLM en Azure OpenAI + herramientas + memoria de la conversación."""
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(str(Path(__file__).resolve().parent))
from herramientas import ESQUEMAS, FUNCIONES  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

INSTRUCCIONES = f"""Eres un analista de costos de un proyecto de construcción. Ayudas a la gerencia a entender
y planear el costo de dos equipos (Equipo1 y Equipo2), que dependen de tres materias primas (X, Y, Z).

Reglas:
- Cualquier número sobre pronósticos, históricos o escenarios lo obtienes con las herramientas. Nunca lo inventes.
- Cuando des un pronóstico, menciona el escenario central (P50) y el rango de 90% (P5-P95).
- Para comparar la incertidumbre entre equipos usa rango_90_pct (ancho relativo), no la diferencia en unidades.
  Un rango_90_pct MAYOR significa MÁS incertidumbre. Para decir cuál equipo es más incierto usa
  comparacion_incertidumbre_6_meses de resultados_modelo; no hagas la comparación por tu cuenta.
- Si preguntan por contexto de mercado, noticias o tendencias, usa buscar_noticias y cita las fuentes con su enlace.
  Distingue claramente lo que dice el modelo (datos históricos) de lo que dicen las noticias.
- Para cualquier impacto de un cambio en las materias primas usa simular_escenario. No lo calcules a mano:
  los pesos de la fórmula son en unidades de precio, no en porcentaje (por ejemplo, Z pesa 1/3 en Equipo2,
  pero un +10% en Z mueve al Equipo2 bastante más que 3.3% porque Z tiene un precio mucho mayor).
- Si una noticia sugiere un cambio fuerte en una materia prima, usa simular_escenario para estimar el impacto.
- El último dato real es ago-2023. Para el análisis, "hoy" es ago-2023: "el próximo mes" es sep-2023 y
  "los próximos 6 meses" son sep-2023 a feb-2024 (horizonte recomendado). El pronóstico llega a ago-2024;
  de mar-2024 en adelante es un escenario, no un pronóstico.
- Responde siempre y únicamente en español, claro y breve, pensando en alguien de finanzas, no en un estadístico.
Fecha real del sistema (solo para fechar noticias): {date.today():%Y-%m-%d}."""

MAX_PASOS = 6


class Agente:
    def __init__(self):
        self.cliente = OpenAI(
            base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/openai/v1/",
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
        )
        self.modelo = os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.mensajes = [{"role": "system", "content": INSTRUCCIONES}]  # memoria

    def preguntar(self, texto):
        """Responde una pregunta. Devuelve la respuesta y la lista de herramientas que usó."""
        self.mensajes.append({"role": "user", "content": texto})
        usadas = []

        for _ in range(MAX_PASOS):
            r = self.cliente.chat.completions.create(model=self.modelo, messages=self.mensajes, tools=ESQUEMAS)
            msg = r.choices[0].message

            if not msg.tool_calls:  # ya no necesita herramientas: responde
                self.mensajes.append({"role": "assistant", "content": msg.content})
                return msg.content, usadas

            # el modelo decidió usar una o varias herramientas
            self.mensajes.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [tc.model_dump(exclude_none=True) for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                try:
                    resultado = FUNCIONES[tc.function.name](**args)
                except Exception as e:
                    resultado = {"error": str(e)}
                usadas.append({"herramienta": tc.function.name, "argumentos": args})
                self.mensajes.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(resultado, ensure_ascii=False, default=str),
                })

        return "No pude completar la respuesta con los pasos disponibles. Intenta con una pregunta más concreta.", usadas


if __name__ == "__main__":
    # prueba rápida desde la terminal: python agent/agente.py "tu pregunta"
    agente = Agente()
    pregunta = " ".join(sys.argv[1:]) or "¿Cuánto costará el Equipo1 en diciembre de 2023?"
    respuesta, usadas = agente.preguntar(pregunta)
    print("Herramientas usadas:", [u["herramienta"] for u in usadas])
    print()
    print(respuesta)
