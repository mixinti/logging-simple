import requests    
import random      
import time        
from datetime import datetime, timezone  

URL_SERVIDOR = "http://localhost:5000/logs"  

SERVICIOS = [
    {
        "nombre": "api-gateway",
        "token":  "token-servicio-api",
    },
    {
        "nombre": "servicio-pagos",
        "token":  "token-servicio-pagos",
    },
    {
        "nombre": "servicio-usuarios",
        "token":  "token-servicio-usuarios",
    },
]

MENSAJES_POR_SEVERIDAD = {
    "INFO": [
        "Solicitud procesada correctamente.",
        "Conexión establecida con el servicio externo.",
        "Caché actualizado exitosamente.",
        "Tarea programada ejecutada sin errores.",
        "Configuración recargada.",
    ],
    "DEBUG": [
        "Iniciando ciclo de limpieza de sesiones.",
        "Variable de entorno DB_HOST leída: localhost.",
        "Pool de conexiones: 8/10 activas.",
        "Tiempo de respuesta: 142ms.",
        "Payload recibido: 2.3KB.",
    ],
    "WARNING": [
        "Tiempo de respuesta elevado: 2300ms.",
        "Reintentos de conexión: 3 de 5.",
        "Memoria al 78% de capacidad.",
        "Certificado SSL vence en 7 días.",
        "Tasa de error supera el umbral recomendado.",
    ],
    "ERROR": [
        "No se pudo conectar a la base de datos.",
        "Timeout al llamar al servicio externo.",
        "Token de autenticación expirado.",
        "Error 500 al procesar la solicitud del usuario #4821.",
        "Falla al escribir en el sistema de archivos.",
    ],
    "CRITICAL": [
        "¡Base de datos principal caída! Activando réplica.",
        "Memoria agotada. Proceso terminado.",
        "Brecha de seguridad detectada. Bloqueando acceso.",
        "Cascada de fallos en el servicio de pagos.",
        "El sistema de backups falló. Datos en riesgo.",
    ],
}

PROBABILIDADES = {
    "INFO":     0.45,   
    "DEBUG":    0.25,   
    "WARNING":  0.15,   
    "ERROR":    0.12,   
    "CRITICAL": 0.03,   
}


def generar_log(nombre_servicio):
    severidad = random.choices(
        population=list(PROBABILIDADES.keys()),       
        weights=list(PROBABILIDADES.values()),        
        k=1                                           
    )[0]

    timestamp = datetime.now(timezone.utc).isoformat()

    mensaje = random.choice(MENSAJES_POR_SEVERIDAD[severidad])

    return {
        "timestamp": timestamp,
        "service":   nombre_servicio,
        "severity":  severidad,
        "message":   mensaje,
    }


def enviar_log(log, token):\

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {token}",
    }

    try:
        respuesta = requests.post(URL_SERVIDOR, json=log, headers=headers, timeout=5)
        
        if respuesta.status_code in (200, 201, 207):
            print(f" [{log['severity']}] Enviado: {log['message'][:50]}...")
            return True
        else:
            print(f"Error {respuesta.status_code}: {respuesta.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("No se pudo conectar al servidor. ¿Está corriendo servidor.py?")
        return False
    except requests.exceptions.Timeout:
        print("El servidor tardó demasiado en responder.")
        return False


def enviar_lote(logs, token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {token}",
    }

    try:
        respuesta = requests.post(URL_SERVIDOR, json=logs, headers=headers, timeout=10)
        data = respuesta.json()
        print(f"Lote enviado: {data.get('guardados', 0)}/{len(logs)} guardados.")
        if "errores" in data:
            print(f"Errores: {data['errores']}")
        return respuesta.status_code in (200, 201, 207)

    except Exception as e:
        print(f"Excepción al enviar lote: {e}")
        return False

# SIMULACIONES

def simular_servicio_individual(servicio, cantidad=5):
    print(f"\n{'='*55}")
    print(f"Servicio: {servicio['nombre']}")
    print(f"{'='*55}")
    
    for i in range(cantidad):
        log = generar_log(servicio["nombre"])
        enviar_log(log, servicio["token"])
        time.sleep(0.3) 


def simular_envio_masivo(servicio, cantidad=20):
    print(f"\n{'='*55}")
    print(f"Envío masivo desde: {servicio['nombre']} ({cantidad} logs)")
    print(f"{'='*55}")
    
    logs = [generar_log(servicio["nombre"]) for _ in range(cantidad)]
    enviar_lote(logs, servicio["token"])


def simular_token_invalido():
    print(f"\n{'='*55}")
    print("Test con token INVÁLIDO (debe fallar con 401)")
    print(f"{'='*55}")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Token token-hacker-malicioso",
    }
    log = generar_log("Servicio Fantasma")

    try:
        respuesta = requests.post(URL_SERVIDOR, json=log, headers=headers, timeout=5)
        print(f"  Respuesta del servidor: {respuesta.status_code} - {respuesta.json()}")
    except Exception as e:
        print(f"  Error: {e}")

# PUNTO DE ENTRADA — Menú interactivo

if __name__ == "__main__":
    print("SISTEMA DE LOGGING DISTRIBUIDO — Clientes Simulados")
    print("=" * 55)
    print("¿Qué simulación querés correr?")
    print("  1. Cada servicio envía logs individuales")
    print("  2. Envío masivo de un servicio")
    print("  3. Test con token inválido")
    print("  4. Todo lo anterior")
    
    opcion = input("\nElegí una opción (1-4): ").strip()

    if opcion == "1":
        for servicio in SERVICIOS:
            simular_servicio_individual(servicio, cantidad=5)

    elif opcion == "2":
        simular_envio_masivo(SERVICIOS[0], cantidad=20)

    elif opcion == "3":
        simular_token_invalido()

    elif opcion == "4":
        for servicio in SERVICIOS:
            simular_servicio_individual(servicio, cantidad=3)
        simular_envio_masivo(SERVICIOS[1], cantidad=15)
        simular_token_invalido()
    else:
        print("Opción inválida. Corré el script de nuevo.")

    print("Simulación terminada.")
