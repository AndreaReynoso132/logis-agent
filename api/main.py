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
from database import guardar_feedback, cargar_inventario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("logis-api")

api = FastAPI(
    title="Logis API",
    description="API del agente de stock y precios Logis",
    version="0.1.0"
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