import logging
import os
import re
import uuid
from typing import TypedDict, List, Literal, Optional, Annotated
import operator

import gradio as gr
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("logis")

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "materiales.csv")
MINIMO_DEFAULT = 10

INVENTARIO: dict = {}


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "").lower().strip())


def cargar_inventario() -> int:
    global INVENTARIO
    df = pd.read_csv(CSV_PATH)
    df["material"] = df["material"].apply(normalizar)
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
    df["precio"]   = pd.to_numeric(df["precio"],   errors="coerce").fillna(0).astype(float)
    if "minimo" not in df.columns:
        df["minimo"] = MINIMO_DEFAULT
    else:
        df["minimo"] = pd.to_numeric(df["minimo"], errors="coerce").fillna(MINIMO_DEFAULT).astype(int)
    INVENTARIO = df.set_index("material").to_dict("index")
    return len(INVENTARIO)


def guardar_csv():
    rows = [{"material": m, "cantidad": d.get("cantidad", 0),
             "precio": d.get("precio", 0.0), "minimo": d.get("minimo", MINIMO_DEFAULT)}
            for m, d in INVENTARIO.items()]
    pd.DataFrame(rows).to_csv(CSV_PATH, index=False)


try:
    log.info(f"Inventario cargado: {cargar_inventario()} productos")
except Exception as e:
    log.error(f"Error al cargar CSV: {e}")


def buscar_fuzzy(pedido: str) -> Optional[str]:
    p = normalizar(pedido)
    tokens = [t for t in re.split(r"[\s,./-]+", p) if len(t) > 2]
    best, best_score = None, 0
    for mat in INVENTARIO:
        if mat in p:
            return mat
        score = sum(1 for t in tokens if t in mat)
        if score >= 2 and score > best_score:
            best_score, best = score, mat
    return best


llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=1.0)


def extraer_texto(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return str(content).strip()


@tool
def consultar_producto(nombre_producto: str) -> str:
    """Consulta el stock, precio y estado de UN producto específico.
    Usá esta herramienta cuando el usuario pregunta por stock o precio de un producto."""
    mat = buscar_fuzzy(nombre_producto)
    if not mat:
        sugs = [m for m in INVENTARIO if any(t in m for t in nombre_producto.lower().split() if len(t) > 2)][:3]
        sug_txt = ", ".join(s.upper() for s in sugs) if sugs else "ninguno"
        return f"Producto '{nombre_producto}' no encontrado. Similares: {sug_txt}"
    d = INVENTARIO[mat]
    stock  = int(d.get("cantidad", 0))
    precio = float(d.get("precio", 0))
    minimo = int(d.get("minimo", MINIMO_DEFAULT))
    if stock == 0:
        estado = "AGOTADO"
    elif stock < minimo:
        estado = f"STOCK BAJO (faltan {minimo - stock} uds para el mínimo)"
    else:
        estado = "OK"
    return (
        f"PRODUCTO: {mat.upper()}\n"
        f"- Stock actual: {stock} uds\n"
        f"- Stock mínimo: {minimo} uds\n"
        f"- Precio unitario: ${precio:,.2f}\n"
        f"- Valor en inventario: ${stock * precio:,.2f}\n"
        f"- Estado: {estado}"
    )


@tool
def listar_productos_criticos() -> str:
    """Devuelve todos los productos agotados y con stock bajo.
    Usá esta herramienta cuando el usuario pide un análisis de múltiples productos o priorización de reposición."""
    agotados, bajos = [], []
    for mat, d in sorted(INVENTARIO.items()):
        stock  = int(d.get("cantidad", 0))
        minimo = int(d.get("minimo", MINIMO_DEFAULT))
        precio = float(d.get("precio", 0))
        if stock == 0:
            agotados.append(f"{mat.upper()} | stock: 0 | precio: ${precio:,.0f}")
        elif stock < minimo:
            bajos.append(f"{mat.upper()} | stock: {stock}/{minimo} | precio: ${precio:,.0f}")
    resultado = []
    if agotados:
        resultado.append(f"AGOTADOS ({len(agotados)}):\n" + "\n".join(agotados))
    if bajos:
        resultado.append(f"STOCK BAJO ({len(bajos)}):\n" + "\n".join(bajos))
    if not resultado:
        return "Todo el inventario está en niveles óptimos."
    return "\n\n".join(resultado)


@tool
def modificar_stock(nombre_producto: str, cantidad: int, es_absoluto: bool = True) -> str:
    """Modifica el stock de un producto.
    - nombre_producto: nombre del producto
    - cantidad: número entero (positivo o negativo)
    - es_absoluto: True = setear a ese valor exacto, False = sumar/restar al actual"""
    mat = buscar_fuzzy(nombre_producto)
    if not mat:
        return f"Producto '{nombre_producto}' no encontrado en el inventario."
    actual = int(INVENTARIO[mat].get("cantidad", 0))
    nuevo  = cantidad if es_absoluto else actual + cantidad
    if nuevo < 0:
        return f"Error: el stock no puede quedar negativo. Actual: {actual}, cambio: {cantidad:+}."
    INVENTARIO[mat]["cantidad"] = nuevo
    try:
        guardar_csv()
    except Exception as e:
        return f"Stock actualizado en memoria pero error al guardar CSV: {e}"
    accion = f"establecido a {nuevo}" if es_absoluto else f"{actual} → {nuevo} ({cantidad:+})"
    return f"✅ Stock de {mat.upper()} {accion} uds."


@tool
def obtener_inventario_completo() -> str:
    """Devuelve el inventario completo con todos los productos, stock y precios.
    Usá esta herramienta solo si el usuario pide ver TODOS los productos."""
    lineas = ["INVENTARIO COMPLETO:"]
    for mat, d in sorted(INVENTARIO.items()):
        stock  = int(d.get("cantidad", 0))
        minimo = int(d.get("minimo", MINIMO_DEFAULT))
        precio = float(d.get("precio", 0))
        estado = "AGOTADO" if stock == 0 else ("BAJO" if stock < minimo else "OK")
        lineas.append(f"- {mat.upper()} | {stock} uds | ${precio:,.0f} | {estado}")
    lineas.append(f"\nTotal: {len(INVENTARIO)} productos")
    return "\n".join(lineas)


TOOLS = [consultar_producto, listar_productos_criticos, modificar_stock, obtener_inventario_completo]
llm_con_tools = llm.bind_tools(TOOLS)


class LogisState(TypedDict):
    pedido:          str
    tipo_consulta:   Literal["simple", "agente"]
    respuesta_final: str
    messages:        Annotated[List, operator.add]


SYSTEM_PROMPT_AGENTE = """Eres Logis, asistente experto en gestión de stock de lubricantes, químicos, GLP y accesorios industriales.

Tenés acceso a estas herramientas:
- consultar_producto: para ver stock/precio de un producto específico
- listar_productos_criticos: para ver agotados y stock bajo
- modificar_stock: para actualizar cantidades
- obtener_inventario_completo: solo si piden ver TODO el inventario

IMPORTANTE:
- Siempre usá las herramientas para obtener datos reales antes de responder
- Podés encadenar herramientas: ej. listar críticos → consultar cada uno → recomendar
- Respondé en español, de forma concisa y práctica
- Para análisis estratégico, considerá: riesgo de quiebre, capital inmovilizado, urgencia operativa
- Finalizá recomendaciones con "**Recomendación:**"
"""


def icono(stock: int, minimo: int) -> str:
    return "🔴 AGOTADO" if stock == 0 else ("🟡 BAJO" if stock < minimo else "🟢 OK")


def nodo_clasificar(state: LogisState) -> dict:
    pedido = normalizar(state["pedido"])
    SIMPLES = {
        "saludo":   ["hola", "buenos", "buenas", "gracias", "hey", "que tal"],
        "listado":  ["listado completo", "inventario completo", "todos los productos", "catalogo"],
        "agotados": ["agotado", "sin stock", "faltante", "quiebre"],
        "alertas":  ["mostrar alertas", "ver alertas", "alertas de stock", "reporte alertas"],
    }
    for tipo, keywords in SIMPLES.items():
        if any(k in pedido for k in keywords):
            return {"tipo_consulta": "simple", "respuesta_final": tipo}
    return {
        "tipo_consulta": "agente",
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT_AGENTE),
            HumanMessage(content=state["pedido"])
        ]
    }


def nodo_simple(state: LogisState) -> dict:
    tipo = state["respuesta_final"]

    if tipo == "saludo":
        return {"respuesta_final": (
            "¡Hola! Soy **Logis**, tu asistente de **stock y precios** 🛢️\n\n"
            "Podés preguntarme:\n"
            "• *¿Hay stock de elaion f50 5w-40 4l?*\n"
            "• *¿Cuánto sale el blue32 urea 20l?*\n"
            "• *¿Qué productos están agotados?*\n"
            "• *Mostrar alertas de stock*\n"
            "• *Listado completo*\n"
            "• *¿Conviene reponer nafta super 10l?*\n"
            "• *Actualizá stock de nafta super 10l a 15*\n"
            "• *¿Qué productos críticos debería reponer primero?*\n"
        )}

    if tipo == "listado":
        lineas = ["📋 **INVENTARIO COMPLETO**\n",
                  "| Producto | Stock | Mínimo | Precio | Estado |",
                  "|----------|-------|--------|--------|--------|"]
        for mat, d in sorted(INVENTARIO.items()):
            s = int(d.get("cantidad", 0))
            m = int(d.get("minimo", MINIMO_DEFAULT))
            p = float(d.get("precio", 0))
            lineas.append(f"| {mat.upper()} | {s} | {m} | ${p:,.0f} | {icono(s, m)} |")
        lineas.append(f"\n**Total:** {len(INVENTARIO)} productos")
        return {"respuesta_final": "\n".join(lineas)}

    if tipo == "agotados":
        items = [(m.upper(), float(d.get("precio", 0)))
                 for m, d in INVENTARIO.items() if int(d.get("cantidad", 0)) == 0]
        if not items:
            return {"respuesta_final": "✅ No hay productos agotados."}
        lineas = [f"🔴 **PRODUCTOS AGOTADOS ({len(items)})**\n",
                  "| Producto | Precio Unit. |", "|----------|-------------|"]
        for nombre, precio in sorted(items):
            lineas.append(f"| {nombre} | ${precio:,.0f} |")
        lineas.append(f"\n💰 **Inversión estimada (1 ud c/u):** ${sum(p for _, p in items):,.0f}")
        return {"respuesta_final": "\n".join(lineas)}

    if tipo == "alertas":
        criticos, bajos = [], []
        for mat, d in sorted(INVENTARIO.items()):
            s = int(d.get("cantidad", 0))
            m = int(d.get("minimo", MINIMO_DEFAULT))
            p = float(d.get("precio", 0))
            fila = f"| {mat.upper()} | {s} | {m} | ${p:,.0f} |"
            if s == 0:
                criticos.append(fila)
            elif s < m:
                bajos.append(fila)
        enc = "| Producto | Stock | Mínimo | Precio |"
        sep = "|----------|-------|--------|--------|"
        lineas = ["🚨 **REPORTE DE ALERTAS**\n"]
        if criticos:
            lineas += [f"### 🔴 Agotados ({len(criticos)})", enc, sep] + criticos + [""]
        if bajos:
            lineas += [f"### 🟡 Stock Bajo ({len(bajos)})", enc, sep] + bajos + [""]
        if not criticos and not bajos:
            lineas.append("✅ Todo en orden.")
        else:
            lineas.append(f"**Resumen:** {len(criticos)} agotados · {len(bajos)} con stock bajo.")
        return {"respuesta_final": "\n".join(lineas)}

    return {"respuesta_final": "❓ Consulta no reconocida."}


def nodo_agente(state: LogisState) -> dict:
    response = llm_con_tools.invoke(state["messages"])
    return {"messages": [response]}


def nodo_tools(state: LogisState) -> dict:
    return ToolNode(TOOLS).invoke(state)


def nodo_formatear(state: LogisState) -> dict:
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            texto = extraer_texto(msg.content)
            if texto:
                return {"respuesta_final": texto}
    return {"respuesta_final": "⚠️ No pude generar una respuesta."}


def debe_continuar(state: LogisState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "formatear"


workflow = StateGraph(LogisState)
workflow.add_node("clasificar", nodo_clasificar)
workflow.add_node("simple",     nodo_simple)
workflow.add_node("agente",     nodo_agente)
workflow.add_node("tools",      nodo_tools)
workflow.add_node("formatear",  nodo_formatear)

workflow.add_edge(START, "clasificar")
workflow.add_conditional_edges("clasificar", lambda s: s["tipo_consulta"], {"simple": "simple", "agente": "agente"})
workflow.add_conditional_edges("agente", debe_continuar, {"tools": "tools", "formatear": "formatear"})
workflow.add_edge("tools",     "agente")
workflow.add_edge("simple",    END)
workflow.add_edge("formatear", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


def chat(message: str, history: list, session_id: str) -> str:
    state: LogisState = {
        "pedido":          message,
        "tipo_consulta":   "simple",
        "respuesta_final": "",
        "messages":        [],
    }
    try:
        result = app.invoke(state, {"configurable": {"thread_id": session_id}})
        return result.get("respuesta_final", "⚠️ Error procesando la consulta.")
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