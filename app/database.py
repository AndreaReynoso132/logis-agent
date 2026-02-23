import os
import re
import sqlite3
from typing import Optional

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DB_PATH        = os.path.join(BASE_DIR, "logis.db")
MINIMO_DEFAULT = 10


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "").lower().strip())


def cargar_inventario() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]


def guardar_en_db(material: str, cantidad: int):
    with get_conn() as conn:
        conn.execute("UPDATE productos SET cantidad = ? WHERE material = ?", (cantidad, material))


def guardar_feedback(pregunta: str, respuesta: str):
    with get_conn() as conn:
        conn.execute("INSERT INTO feedback (pregunta, respuesta) VALUES (?, ?)", (pregunta, respuesta))


def buscar_feedback_similar(pregunta: str, max_resultados: int = 3) -> list:
    tokens = [t for t in re.split(r"\s+", normalizar(pregunta)) if len(t) > 3]
    if not tokens:
        return []
    with get_conn() as conn:
        todos = conn.execute("SELECT pregunta, respuesta FROM feedback ORDER BY id DESC LIMIT 100").fetchall()
    similares = []
    for row in todos:
        coincidencias = sum(1 for t in tokens if t in normalizar(row["pregunta"]))
        if coincidencias >= 2:
            similares.append({
                "score":     coincidencias,
                "pregunta":  row["pregunta"],
                "respuesta": row["respuesta"]
            })
    similares.sort(key=lambda x: x["score"], reverse=True)
    return similares[:max_resultados]


def buscar_fuzzy(pedido: str) -> Optional[str]:
    p = normalizar(pedido)
    tokens = [t for t in re.split(r"[\s,./-]+", p) if len(t) > 2]
    with get_conn() as conn:
        materiales = [row["material"] for row in conn.execute("SELECT material FROM productos")]
    best, best_score = None, 0
    for mat in materiales:
        if mat in p:
            return mat
        score = sum(1 for t in tokens if t in mat)
        if score >= 2 and score > best_score:
            best_score, best = score, mat
    return best


def obtener_producto(material: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM productos WHERE material = ?", (material,)).fetchone()
    return dict(row) if row else None