from flask import Flask, request, jsonify  
import sqlite3                             
from datetime import datetime              

app = Flask(__name__)  

TOKENS_VALIDOS = {
    "token-servicio-api":      "API Gateway",
    "token-servicio-pagos":    "Servicio de Pagos",
    "token-servicio-usuarios": "Servicio de Usuarios",
}

DB_NOMBRE = "logs.db"

# BASE DE DATOS

def inicializar_db():
    with sqlite3.connect(DB_NOMBRE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT NOT NULL,
                service      TEXT NOT NULL,
                severity     TEXT NOT NULL,
                message      TEXT NOT NULL,
                received_at  TEXT NOT NULL
            )
        """)
        conn.commit()  
    print("Base de datos lista.")


def guardar_log(timestamp, service, severity, message):
    received_at = datetime.utcnow().isoformat()  
    with sqlite3.connect(DB_NOMBRE) as conn:
        conn.execute(
            "INSERT INTO logs (timestamp, service, severity, message, received_at) VALUES (?,?,?,?,?)",
            (timestamp, service, severity, message, received_at)
        )
        conn.commit()


# FUNCIÓN DE AUTENTICACIÓN

def verificar_token(request):

    auth_header = request.headers.get("Authorization", "")

    # Opción 1: token en el header 
    if auth_header.startswith("Token "): 
        token = auth_header.split(" ", 1)[1] 
        if token in TOKENS_VALIDOS:
            return True, TOKENS_VALIDOS[token]

    token_url = request.args.get("token", "")
    if token_url in TOKENS_VALIDOS:
        return True, TOKENS_VALIDOS[token_url]

    return False, None

# ENDPOINTS 

@app.route("/logs", methods=["POST"])
def recibir_logs():
    # 1. Verificar autenticación
    valido, nombre_servicio = verificar_token(request)
    if not valido:
        return jsonify({"error": "Quién sos, bro?"}), 401

    # 2. Leer el cuerpo del request 
    datos = request.get_json()
    if not datos:
        return jsonify({"error": "El body debe ser JSON válido."}), 400

    # 3. Soportar un solo log o varios logs a la vez
    if isinstance(datos, dict):
        logs_a_procesar = [datos]   
    elif isinstance(datos, list):
        logs_a_procesar = datos
    else:
        return jsonify({"error": "El body debe ser un log (objeto) o una lista de logs."}), 400

    # 4. Validar y guardar cada log
    CAMPOS_REQUERIDOS = {"timestamp", "service", "severity", "message"}
    SEVERIDADES_VALIDAS = {"INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"}

    guardados = 0
    errores = []

    for i, log in enumerate(logs_a_procesar):
        campos_faltantes = CAMPOS_REQUERIDOS - set(log.keys())
        if campos_faltantes:
            errores.append(f"Log #{i+1}: faltan campos {campos_faltantes}")
            continue  

        if log["severity"].upper() not in SEVERIDADES_VALIDAS:
            errores.append(f"Log #{i+1}: severidad inválida '{log['severity']}'")
            continue

        guardar_log(
            timestamp=log["timestamp"],
            service=log["service"],
            severity=log["severity"].upper(),
            message=log["message"]
        )
        guardados += 1

    # 5. Respuesta al cliente
    respuesta = {
        "guardados": guardados,
        "total_recibidos": len(logs_a_procesar),
    }
    if errores:
        respuesta["errores"] = errores

    codigo_http = 201 if not errores else 207
    return jsonify(respuesta), codigo_http


@app.route("/logs", methods=["GET"])
def consultar_logs():
    # 1. Autenticación requerida también para consultar
    valido, _ = verificar_token(request)
    if not valido:
        return jsonify({"error": "Quién sos, bro?"}), 401

    # 2. Leer los filtros opcionales de la URL
    timestamp_start   = request.args.get("timestamp_start")
    timestamp_end     = request.args.get("timestamp_end")
    received_at_start = request.args.get("received_at_start")
    received_at_end   = request.args.get("received_at_end")
    severity          = request.args.get("severity")
    service           = request.args.get("service")
    limit             = request.args.get("limit", 1000, type=int)  

    # 3. Construir la query SQL dinámicamente según los filtros
    query = "SELECT id, timestamp, service, severity, message, received_at FROM logs WHERE 1=1"
    params = [] 

    if timestamp_start:
        query += " AND timestamp >= ?" 
        params.append(timestamp_start)

    if timestamp_end:
        query += " AND timestamp <= ?" 
        params.append(timestamp_end)

    if received_at_start:
        query += " AND received_at >= ?" 
        params.append(received_at_start)

    if received_at_end:
        query += " AND received_at <= ?" 
        params.append(received_at_end)

    if severity:
        query += " AND severity = ?"
        params.append(severity.upper())

    if service:
        query += " AND service = ?" 
        params.append(service)

    query += " ORDER BY received_at DESC LIMIT ?"
    params.append(limit)

    # 4. Ejecutar la query y devolver resultados
    with sqlite3.connect(DB_NOMBRE) as conn:
        conn.row_factory = sqlite3.Row  
        cursor = conn.execute(query, params)
        filas = cursor.fetchall()

    logs = [
        {
            "id":          fila["id"],
            "timestamp":   fila["timestamp"],
            "service":     fila["service"],
            "severity":    fila["severity"],
            "message":     fila["message"],
            "received_at": fila["received_at"],
        }
        for fila in filas
    ]

    return jsonify({
        "total": len(logs),
        "filtros_aplicados": {
            "timestamp_start":   timestamp_start,
            "timestamp_end":     timestamp_end,
            "received_at_start": received_at_start,
            "received_at_end":   received_at_end,
            "severity":          severity,
            "service":           service,
            "limit":             limit,
        },
        "logs": logs
    }), 200

if __name__ == "__main__":
    inicializar_db()         
    print("Servidor corriendo en http://localhost:5000")
    app.run(debug=True, port=5000)