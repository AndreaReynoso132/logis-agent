import sqlite3
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "scripts", "materiales.csv")
DB_PATH  = os.path.join(BASE_DIR, "scripts", "logis.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        material TEXT    NOT NULL UNIQUE,
        cantidad INTEGER NOT NULL DEFAULT 0,
        precio   REAL    NOT NULL DEFAULT 0.0,
        minimo   INTEGER NOT NULL DEFAULT 10
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        pregunta  TEXT NOT NULL,
        respuesta TEXT NOT NULL
    )
""")

df = pd.read_csv(CSV_PATH)
df["material"] = df["material"].str.lower().str.strip()
df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
df["precio"]   = pd.to_numeric(df["precio"],   errors="coerce").fillna(0).astype(float)
df["minimo"]   = pd.to_numeric(df.get("minimo", 10), errors="coerce").fillna(10).astype(int)

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO productos (material, cantidad, precio, minimo)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(material) DO UPDATE SET
            cantidad = excluded.cantidad,
            precio   = excluded.precio,
            minimo   = excluded.minimo
    """, (row["material"], row["cantidad"], row["precio"], row["minimo"]))

conn.commit()

total = cursor.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
print(f"✅ Base de datos creada: {DB_PATH}")
print(f"✅ Productos migrados: {total}")
print(f"✅ Tabla feedback lista")

conn.close()