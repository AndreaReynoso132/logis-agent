import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../app"))

import uuid
import logging
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import app as logis_app, LogisState
from database import guardar_feedback, cargar_inventario, get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("logis-api")

api = FastAPI(
    title="Logis API",
    description="API del agente de stock y precios Logis",
    version="0.2.0"
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message:    str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response:   str
    session_id: str


@api.get("/health")
def health():
    try:
        total = cargar_inventario()
        return {"status": "ok", "productos": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.get("/dashboard")
def dashboard():
    """Devuelve los datos del dashboard: métricas y productos críticos."""
    try:
        conn = get_conn()
        cur  = conn.cursor()

        # métricas principales
        cur.execute("SELECT COUNT(*) FROM productos")
        total_productos = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM productos WHERE cantidad = 0")
        agotados = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM productos WHERE cantidad < minimo AND cantidad > 0")
        criticos = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(cantidad * precio), 0) FROM productos")
        valor_total = cur.fetchone()[0]

        # productos críticos ordenados por urgencia
        cur.execute("""
            SELECT material, cantidad, minimo, precio,
                   (minimo - cantidad) as deficit,
                   CASE WHEN cantidad = 0 THEN 'agotado' ELSE 'critico' END as estado
            FROM productos
            WHERE cantidad < minimo
            ORDER BY cantidad ASC, deficit DESC
        """)
        rows = cur.fetchall()
        criticos_lista = [
            {
                "material": r[0],
                "cantidad": r[1],
                "minimo":   r[2],
                "precio":   r[3],
                "deficit":  r[4],
                "estado":   r[5],
            }
            for r in rows
        ]

        # top 5 por valor
        cur.execute("""
            SELECT material, cantidad, precio, (cantidad * precio) as valor_total
            FROM productos
            WHERE cantidad > 0
            ORDER BY valor_total DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        top_valor = [
            {
                "material":    r[0],
                "cantidad":    r[1],
                "precio":      r[2],
                "valor_total": r[3],
            }
            for r in rows
        ]

        conn.close()

        return {
            "metricas": {
                "total_productos": total_productos,
                "agotados":        agotados,
                "criticos":        criticos,
                "valor_total":     valor_total,
            },
            "criticos_lista": criticos_lista,
            "top_valor":      top_valor,
        }
    except Exception as e:
        log.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    state: LogisState = {
        "pedido":          req.message,
        "tipo_consulta":   "simple",
        "respuesta_final": "",
        "messages":        [],
    }
    try:
        result    = logis_app.invoke(state, {"configurable": {"thread_id": session_id}})
        respuesta = result.get("respuesta_final", "⚠️ Error procesando la consulta.")
        guardar_feedback(req.message, respuesta)
        return ChatResponse(response=respuesta, session_id=session_id)
    except Exception as e:
        log.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))