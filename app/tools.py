from langchain_core.tools import tool
from database import buscar_fuzzy, obtener_producto, guardar_en_db, get_conn, MINIMO_DEFAULT


@tool
def consultar_producto(nombre_producto: str) -> str:
    """Consulta el stock, precio y estado de UN producto específico.
    Usá esta herramienta cuando el usuario pregunta por stock o precio de un producto."""
    mat = buscar_fuzzy(nombre_producto)
    if not mat:
        with get_conn() as conn:
            materiales = [row["material"] for row in conn.execute("SELECT material FROM productos")]
        sugs = [m for m in materiales if any(t in m for t in nombre_producto.lower().split() if len(t) > 2)][:3]
        sug_txt = ", ".join(s.upper() for s in sugs) if sugs else "ninguno"
        return f"Producto '{nombre_producto}' no encontrado. Similares: {sug_txt}"
    d = obtener_producto(mat)
    stock  = int(d["cantidad"])
    precio = float(d["precio"])
    minimo = int(d["minimo"])
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
    with get_conn() as conn:
        filas = conn.execute("SELECT material, cantidad, precio, minimo FROM productos ORDER BY material").fetchall()
    agotados, bajos = [], []
    for row in filas:
        stock = int(row["cantidad"]); minimo = int(row["minimo"]); precio = float(row["precio"])
        if stock == 0:
            agotados.append(f"{row['material'].upper()} | stock: 0 | precio: ${precio:,.0f}")
        elif stock < minimo:
            bajos.append(f"{row['material'].upper()} | stock: {stock}/{minimo} | precio: ${precio:,.0f}")
    resultado = []
    if agotados:
        resultado.append(f"AGOTADOS ({len(agotados)}):\n" + "\n".join(agotados))
    if bajos:
        resultado.append(f"STOCK BAJO ({len(bajos)}):\n" + "\n".join(bajos))
    return "\n\n".join(resultado) if resultado else "Todo el inventario está en niveles óptimos."


@tool
def modificar_stock(nombre_producto: str, cantidad: int, es_absoluto: bool = True) -> str:
    """Modifica el stock de un producto.
    - nombre_producto: nombre del producto
    - cantidad: número entero (positivo o negativo)
    - es_absoluto: True = setear a ese valor exacto, False = sumar/restar al actual"""
    mat = buscar_fuzzy(nombre_producto)
    if not mat:
        return f"Producto '{nombre_producto}' no encontrado en el inventario."
    d = obtener_producto(mat)
    actual = int(d["cantidad"])
    nuevo  = cantidad if es_absoluto else actual + cantidad
    if nuevo < 0:
        return f"Error: el stock no puede quedar negativo. Actual: {actual}, cambio: {cantidad:+}."
    guardar_en_db(mat, nuevo)
    accion = f"establecido a {nuevo}" if es_absoluto else f"{actual} → {nuevo} ({cantidad:+})"
    return f"✅ Stock de {mat.upper()} {accion} uds."


@tool
def obtener_inventario_completo() -> str:
    """Devuelve el inventario completo con todos los productos, stock y precios.
    Usá esta herramienta solo si el usuario pide ver TODOS los productos."""
    with get_conn() as conn:
        filas = conn.execute("SELECT material, cantidad, precio, minimo FROM productos ORDER BY material").fetchall()
    lineas = ["INVENTARIO COMPLETO:"]
    for row in filas:
        stock = int(row["cantidad"]); minimo = int(row["minimo"]); precio = float(row["precio"])
        estado = "AGOTADO" if stock == 0 else ("BAJO" if stock < minimo else "OK")
        lineas.append(f"- {row['material'].upper()} | {stock} uds | ${precio:,.0f} | {estado}")
    lineas.append(f"\nTotal: {len(filas)} productos")
    return "\n".join(lineas)