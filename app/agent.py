import operator
import os
from typing import TypedDict, List, Literal, Annotated

from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from database import get_conn, normalizar, MINIMO_DEFAULT
from prompts import construir_system_prompt
from tools import TOOLS, llm

llm_con_tools = llm.bind_tools(TOOLS)


class LogisState(TypedDict):
    pedido:          str
    tipo_consulta:   Literal["simple", "agente"]
    respuesta_final: str
    messages:        Annotated[List, operator.add]


def extraer_texto(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return str(content).strip()


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
            SystemMessage(content=construir_system_prompt(state["pedido"])),
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
        with get_conn() as conn:
            filas = conn.execute("SELECT material, cantidad, precio, minimo FROM productos ORDER BY material").fetchall()
        lineas = ["📋 **INVENTARIO COMPLETO**\n",
                  "| Producto | Stock | Mínimo | Precio | Estado |",
                  "|----------|-------|--------|--------|--------|"]
        for row in filas:
            s = int(row["cantidad"]); m = int(row["minimo"]); p = float(row["precio"])
            lineas.append(f"| {row['material'].upper()} | {s} | {m} | ${p:,.0f} | {icono(s, m)} |")
        lineas.append(f"\n**Total:** {len(filas)} productos")
        return {"respuesta_final": "\n".join(lineas)}

    if tipo == "agotados":
        with get_conn() as conn:
            filas = conn.execute("SELECT material, precio FROM productos WHERE cantidad = 0 ORDER BY material").fetchall()
        if not filas:
            return {"respuesta_final": "✅ No hay productos agotados."}
        lineas = [f"🔴 **PRODUCTOS AGOTADOS ({len(filas)})**\n",
                  "| Producto | Precio Unit. |", "|----------|-------------|"]
        total = 0
        for row in filas:
            lineas.append(f"| {row['material'].upper()} | ${row['precio']:,.0f} |")
            total += float(row["precio"])
        lineas.append(f"\n💰 **Inversión estimada (1 ud c/u):** ${total:,.0f}")
        return {"respuesta_final": "\n".join(lineas)}

    if tipo == "alertas":
        with get_conn() as conn:
            filas = conn.execute("SELECT material, cantidad, precio, minimo FROM productos ORDER BY material").fetchall()
        criticos, bajos = [], []
        for row in filas:
            s = int(row["cantidad"]); m = int(row["minimo"]); p = float(row["precio"])
            fila = f"| {row['material'].upper()} | {s} | {m} | ${p:,.0f} |"
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
app    = workflow.compile(checkpointer=memory)
