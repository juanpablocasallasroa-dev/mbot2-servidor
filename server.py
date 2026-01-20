"""
SERVIDOR PYTHON PARA MBOT2
Archivo: server.py

Instrucciones para ejecutar:
1. Instala dependencias: pip install -r requirements.txt
2. Ejecuta: python server.py
3. El servidor estará en http://localhost:5000
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime
import json

# Crear aplicación Flask
app = Flask(__name__)
CORS(app)  # Permitir peticiones desde cualquier origen

# Configurar WebSocket
socketio = SocketIO(app, cors_allowed_origins="*")

# Base de datos en memoria (simulada)
robots_conectados = {}
misiones = []
telemetria_historico = []

print("=" * 60)
print("🤖 SERVIDOR MBOT2 CON IA")
print("=" * 60)

# ============================================
# ENDPOINTS REST API
# ============================================

@app.route('/')
def inicio():
    """Página principal - muestra info del servidor"""
    return jsonify({
        'servidor': 'mBot2 AI Server',
        'estado': 'online',
        'version': '1.0',
        'robots_conectados': len(robots_conectados),
        'misiones_activas': len(misiones),
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            'GET  / - Esta página',
            'GET  /health - Estado del servidor',
            'POST /api/robot/conectar - Conectar robot',
            'POST /api/robot/datos - Enviar datos del robot',
            'POST /api/mision/crear - Crear nueva misión',
            'GET  /api/robots - Ver todos los robots',
            'GET  /api/telemetria - Ver datos históricos'
        ]
    })

@app.route('/health')
def health():
    """Verificar que el servidor funciona"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/robot/conectar', methods=['POST'])
def conectar_robot():
    """
    Conectar un nuevo mBot2 al servidor
    
    Ejemplo de uso desde el mBot2:
    POST /api/robot/conectar
    {
        "robot_id": "mbot_001",
        "nombre": "Mi Robot"
    }
    """
    datos = request.json
    robot_id = datos.get('robot_id', 'mbot_desconocido')
    nombre = datos.get('nombre', 'Robot sin nombre')
    
    # Registrar robot
    robots_conectados[robot_id] = {
        'id': robot_id,
        'nombre': nombre,
        'estado': 'conectado',
        'conectado_desde': datetime.now().isoformat(),
        'ultima_actualizacion': datetime.now().isoformat(),
        'bateria': 100,
        'mision_actual': None,
        'posicion': {'x': 0, 'y': 0}
    }
    
    print(f"✅ Robot conectado: {robot_id} ({nombre})")
    
    return jsonify({
        'exito': True,
        'mensaje': f'Robot {robot_id} conectado exitosamente',
        'robot_id': robot_id
    })

@app.route('/api/robot/datos', methods=['POST'])
def recibir_datos_robot():
    """
    Recibir datos de sensores del mBot2
    
    Ejemplo:
    POST /api/robot/datos
    {
        "robot_id": "mbot_001",
        "sensor_linea": [0, 1, 1, 0],
        "distancia": 25.5,
        "bateria": 87,
        "color_detectado": "rojo",
        "posicion": {"x": 10, "y": 5}
    }
    """
    datos = request.json
    robot_id = datos.get('robot_id')
    
    if robot_id not in robots_conectados:
        return jsonify({'error': 'Robot no conectado'}), 400
    
    # Actualizar datos del robot
    robots_conectados[robot_id]['ultima_actualizacion'] = datetime.now().isoformat()
    robots_conectados[robot_id]['bateria'] = datos.get('bateria', 100)
    robots_conectados[robot_id]['posicion'] = datos.get('posicion', {'x': 0, 'y': 0})
    
    # Guardar en histórico
    entrada_telemetria = {
        'robot_id': robot_id,
        'timestamp': datetime.now().isoformat(),
        'sensor_linea': datos.get('sensor_linea'),
        'distancia': datos.get('distancia'),
        'bateria': datos.get('bateria'),
        'color_detectado': datos.get('color_detectado'),
        'posicion': datos.get('posicion')
    }
    telemetria_historico.append(entrada_telemetria)
    
    # Limitar histórico a últimos 1000 registros
    if len(telemetria_historico) > 1000:
        telemetria_historico.pop(0)
    
    # AQUÍ VA LA INTELIGENCIA ARTIFICIAL
    comando_ia = procesar_con_ia(datos)
    
    print(f"📊 Datos de {robot_id}: Dist={datos.get('distancia')}cm, Bat={datos.get('bateria')}%")
    
    return jsonify({
        'exito': True,
        'comando': comando_ia
    })

@app.route('/api/mision/crear', methods=['POST'])
def crear_mision():
    """
    Crear una nueva misión para el robot
    
    Ejemplo:
    POST /api/mision/crear
    {
        "robot_id": "mbot_001",
        "tipo": "recoger_objeto",
        "objetivo": "cubo_rojo",
        "destino": {"x": 50, "y": 50}
    }
    """
    datos = request.json
    robot_id = datos.get('robot_id')
    
    if robot_id not in robots_conectados:
        return jsonify({'error': 'Robot no conectado'}), 400
    
    mision = {
        'id': f"mision_{len(misiones) + 1}",
        'robot_id': robot_id,
        'tipo': datos.get('tipo'),
        'objetivo': datos.get('objetivo'),
        'destino': datos.get('destino'),
        'estado': 'pendiente',
        'creada_en': datetime.now().isoformat()
    }
    
    misiones.append(mision)
    robots_conectados[robot_id]['mision_actual'] = mision['id']
    
    print(f"📋 Nueva misión creada: {mision['id']} para {robot_id}")
    
    # Notificar al robot por WebSocket
    socketio.emit('nueva_mision', mision, room=robot_id)
    
    return jsonify({
        'exito': True,
        'mision': mision
    })

@app.route('/api/robots', methods=['GET'])
def listar_robots():
    """Ver todos los robots conectados"""
    return jsonify({
        'total': len(robots_conectados),
        'robots': list(robots_conectados.values())
    })

@app.route('/api/telemetria', methods=['GET'])
def obtener_telemetria():
    """Ver datos históricos"""
    limite = request.args.get('limite', 50, type=int)
    robot_id = request.args.get('robot_id')
    
    datos = telemetria_historico[-limite:]
    
    if robot_id:
        datos = [d for d in datos if d['robot_id'] == robot_id]
    
    return jsonify({
        'total': len(datos),
        'datos': datos
    })

# ============================================
# LÓGICA DE INTELIGENCIA ARTIFICIAL
# ============================================

def procesar_con_ia(datos_robot):
    """
    Procesar datos del robot y generar comandos inteligentes
    Aquí puedes agregar tus algoritmos de IA
    """
    comando = {
        'accion': 'continuar',
        'velocidad': 100,
        'direccion': 'adelante'
    }
    
    # Ejemplo 1: Detectar obstáculos
    distancia = datos_robot.get('distancia', 100)
    if distancia < 15:
        comando['accion'] = 'detener'
        comando['velocidad'] = 0
        comando['alerta'] = '⚠️ Obstáculo detectado'
        print(f"🚨 OBSTÁCULO: {distancia}cm")
    elif distancia < 30:
        comando['accion'] = 'reducir_velocidad'
        comando['velocidad'] = 50
    
    # Ejemplo 2: Seguimiento de línea inteligente
    sensor_linea = datos_robot.get('sensor_linea', [0, 0, 0, 0])
    if sensor_linea == [0, 1, 1, 0]:  # Centrado
        comando['direccion'] = 'adelante'
    elif sensor_linea == [1, 1, 0, 0]:  # Desviado a la izquierda
        comando['direccion'] = 'derecha'
        comando['giro'] = 15
    elif sensor_linea == [0, 0, 1, 1]:  # Desviado a la derecha
        comando['direccion'] = 'izquierda'
        comando['giro'] = 15
    
    # Ejemplo 3: Detección de colores
    color = datos_robot.get('color_detectado')
    if color == 'rojo':
        comando['accion'] = 'agarrar_objeto'
        comando['mensaje'] = '🔴 Objeto rojo detectado - activando garra'
    elif color == 'verde':
        comando['accion'] = 'continuar'
        comando['mensaje'] = '🟢 Zona segura'
    
    # Ejemplo 4: Batería baja
    bateria = datos_robot.get('bateria', 100)
    if bateria < 20:
        comando['accion'] = 'regresar_base'
        comando['alerta'] = '🔋 Batería baja - retornando a base'
    
    return comando

# ============================================
# WEBSOCKET - COMUNICACIÓN EN TIEMPO REAL
# ============================================

@socketio.on('connect')
def manejar_conexion():
    """Cuando un robot se conecta por WebSocket"""
    print('🔌 Cliente conectado via WebSocket')
    emit('servidor_listo', {'mensaje': 'Conexión establecida'})

@socketio.on('disconnect')
def manejar_desconexion():
    """Cuando un robot se desconecta"""
    print('🔌 Cliente desconectado')

@socketio.on('datos_tiempo_real')
def recibir_datos_tiempo_real(datos):
    """Recibir datos en tiempo real del robot"""
    robot_id = datos.get('robot_id')
    print(f"📡 Datos en tiempo real de {robot_id}")
    
    # Procesar y responder inmediatamente
    comando = procesar_con_ia(datos)
    emit('comando_ia', comando)

@socketio.on('heartbeat')
def heartbeat(datos):
    """Mantener conexión activa"""
    robot_id = datos.get('robot_id')
    if robot_id in robots_conectados:
        robots_conectados[robot_id]['ultima_actualizacion'] = datetime.now().isoformat()
    emit('heartbeat_ok', {'timestamp': datetime.now().isoformat()})

# ============================================
# INICIAR SERVIDOR
# ============================================

if __name__ == '__main__':
    print("\n🚀 Iniciando servidor...")
    print("📍 URL Local: http://localhost:5000")
    print("📍 URL Red Local: http://0.0.0.0:5000")
    print("\n💡 Presiona Ctrl+C para detener\n")
    print("=" * 60)
    
    # Iniciar servidor
    socketio.run(
        app,
        host='0.0.0.0',  # Accesible desde otras computadoras
        port=5000,
        debug=True,       # Modo desarrollo (quitar en producción)
        allow_unsafe_werkzeug=True
    )