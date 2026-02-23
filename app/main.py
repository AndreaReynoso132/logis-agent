import logging
import uuid

import gradio as gr
from dotenv import load_dotenv

from agent import app, LogisState
from database import guardar_feedback, cargar_inventario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("logis")

load_dotenv()

try:
    log.info(f"Inventario cargado desde DB: {cargar_inventario()} productos")
except Exception as e:
    log.error(f"Error al conectar con la DB: {e}")


def chat(message: str, history: list, session_id: str) -> str:
    state: LogisState = {
        "pedido":          message,
        "tipo_consulta":   "simple",
        "respuesta_final": "",
        "messages":        [],
    }
    try:
        result = app.invoke(state, {"configurable": {"thread_id": session_id}})
        respuesta = result.get("respuesta_final", "⚠️ Error procesando la consulta.")
        guardar_feedback(message, respuesta)
        return respuesta
    except Exception as e:
        log.error(f"Error: {e}")
        return f"⚠️ Error inesperado: {e}"


def nueva_sesion() -> str:
    return str(uuid.uuid4())


with gr.Blocks(title="Logis – Stock & Precios") as demo:
    session_id = gr.State(nueva_sesion)
    gr.Markdown("# 🛢️ Logis: Asistente de Stock & Precios")
    gr.Markdown("*Lubricantes · Químicos · GLP · Filtros · Accesorios*")
    gr.ChatInterface(
        fn=lambda msg, hist: chat(msg, hist, session_id.value),
        examples=[
            "Hola",
            "¿Hay stock de elaion f50 5w-40 4l?",
            "Precio de blue32 urea 20l",
            "¿Qué productos están agotados?",
            "Mostrar alertas de stock",
            "¿Conviene reponer blue32 urea 1000l ibc?",
            "¿Qué productos críticos debería reponer primero?",
            "Actualizá stock de nafta super 10l a 15",
            "Sumá +5 a blue32 urea 1000l ibc",
            "Listado completo",
        ],
    )

if __name__ == "__main__":
    demo.launch(share=False)