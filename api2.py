from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
import json 

app = Flask(__name__)
socketio = SocketIO(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./trivial.db'
db = SQLAlchemy(app)
class Jugador(db.Model):
    id_jugador = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    avatar = 0
    partida=0
    def to_dict(self):
        # Excluir el campo '_sa_instance_state' de la representación del diccionario
        jugador_dict = {key: value for key, value in self.__dict__.items() if key != '_sa_instance_state'}

        # Convertir el diccionario a una cadena JSON
        jugador_json = json.dumps(jugador_dict, default=str)

        return jugador_json

class Partida(db.Model):
    id_partida = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    finalizada = db.Column(db.Boolean)

class JugadorEnPartida(db.Model):
    id_jugador = db.Column(db.Integer, db.ForeignKey('jugador.id_jugador'), primary_key=True)
    id_partida = db.Column(db.Integer, db.ForeignKey('partida.id_partida'), primary_key=True)
    casillaActual = db.Column(db.String(50))
    jugadorActual = db.Column(db.Integer)
    avatar = db.Column(db.String(50))
    juego1 = db.Column(db.Integer)
    juego2 = db.Column(db.Integer)
    juego3 = db.Column(db.Integer)
    juego4 = db.Column(db.Integer)

    def to_dict(self):
        # Excluir el campo '_sa_instance_state' de la representación del diccionario
        jugador_dict = {key: value for key, value in self.__dict__.items() if key != '_sa_instance_state'}

        # Convertir el diccionario a una cadena JSON
        jugador_json = json.dumps(jugador_dict, default=str)

        return jugador_json

class jugadorEnPartidaOnline():
    id_jugador = 0
    id_partida = 0
    casillaActual = ""
    jugadorActual = 0
    avatar = 0
    juegos =[]

    def to_dict(self):
        # Excluir el campo '_sa_instance_state' de la representación del diccionario
        jugador_dict = {key: value for key, value in self.__dict__.items() if key != '_sa_instance_state'}

        # Convertir el diccionario a una cadena JSON
        jugador_json = json.dumps(jugador_dict, default=str)

        return jugador_json

# Ruta original para obtener preguntas
@app.route('/preguntas', methods=['GET'])
def obtener_asignaturas():
    with open('C:/Users/ADMIN/Downloads/leerJson/preguntas.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    response = jsonify(data)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

# Nueva ruta para recibir datos de movimiento mediante POST
@app.route('/enviar_movimiento', methods=['POST'])
def recibir_movimiento():
    if request.method == 'POST':
        # Obtén los datos del movimiento desde el cuerpo de la solicitud
        datos_movimiento = request.get_json()

        # Aquí puedes procesar los datos del movimiento según tus necesidades
        movimiento_recibido = datos_movimiento.get('movimiento', '')

        # Puedes emitir el movimiento a otros jugadores mediante sockets
        socketio.emit('nuevo_movimiento', movimiento_recibido)

        # Devuelve una respuesta si es necesario
        return jsonify({"mensaje": "Movimiento recibido correctamente"})
@socketio.on('obtener_partidas')
def handle_obtener_partidas():
    print("Obteniendo partidas")
    partidas = Partida.query.all()
    partidas_json = [{"id": partida.id_partida, "nombre": partida.nombre} for partida in partidas]
    
    # Devuelve los datos en lugar de un objeto Response
    return partidas_json
jugadores_conectados = []
@socketio.on('addJugador')
def handle_add_jugador(data):
    # Deserializar el objeto JSON recibido del cliente
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return
    # Crear un objeto Jugador
    jugador = Jugador(nombre=jugador_dict.get('nombre'),partida=jugador_dict.get('partida'))
    if existeJugador(jugador_dict.get('nombre')):
        db.session.add(jugador)
        db.session.commit()
    jugador_nuevo = Jugador.query.filter_by(nombre=jugador_dict.get('nombre')).first()
    jugador_nuevo.avatar = jugador_dict.get('avatar')
    jugador_nuevo.partida = jugador_dict.get('partida')
    jugadores_conectados.append(jugador_nuevo)
    handle_notificarJugadores()

def existeJugador(name):
    jugador = Jugador.query.filter_by(nombre=name).first()
    if jugador:
        return  False
    else:
        return True

@socketio.on('desconectar')
def handle_delete_jugador(data):
    # Deserializar el objeto JSON recibido del cliente
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return

    # Obtener el id del jugador a desconectar
    jugador_id = jugador_dict.get('nombre')

    # Buscar el jugador en la lista por su id
    jugador_a_eliminar = next((jugador for jugador in jugadores_conectados if jugador.nombre == jugador_id), None)

    # Verificar si se encontró el jugador
    if jugador_a_eliminar:
        # Eliminar el jugador de la lista
        jugadores_conectados.remove(jugador_a_eliminar)
        # Notificar a los demás jugadores sobre la actualización
        handle_notificarJugadores()
    else:
        print(f"No se encontró el jugador con id {jugador_id}")

@socketio.on('actualizarJugadores')

def handle_notificarJugadores():
    # Emitir la lista actualizada a todos los clientes
    socketio.emit('listaJugadores', [j.to_dict() for j in jugadores_conectados])
    print(jugadores_conectados)



@socketio.on('empezarPartida')
def handle_empezar_partida(data):
    id_partida = data
    jugadoresEnPartida=[]
    juegosNuevos = [0,0,0,0]
    for jugador in jugadores_conectados:
        if jugador.partida == id_partida:
            jugadoresEnPartida.append(jugador)
    for jugador in jugadoresEnPartida:
        primero =False
        if jugadoresEnPartida.index(jugador) == 0:
            primero = True
        jugador = JugadorEnPartida(id_jugador=jugador.id_jugador, id_partida=id_partida, casillaActual="4_4", jugadorActual=primero, avatar=jugador.avatar, juego1=0, juego2=0, juego3=0, juego4=0)
        db.session.add(jugador)
    jugadores = db.session.query(JugadorEnPartida).filter_by(id_partida=id_partida).all()
    jugadoresEnPartida = []
    for jugador in jugadores:
        
        primero =False
        if jugadores.index(jugador) == 0:
            primero = True
        jugador = jugadorEnPartidaOnline(id_jugador=jugador.id_jugador, id_partida=id_partida, casillaActual="4_4", jugadorActual=primero, avatar=jugador.avatar, juegos=juegosNuevos)
        jugadoresEnPartida.append(jugador)
    socketio.emit('empezarPartida', [j.to_dict() for j in jugadoresEnPartida])

@socketio.on('moverJugador')
def handle_mover_jugador(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return
    jugadorEnPartida = jugadorEnPartidaOnline(id_jugador=jugador_dict.get("id_jugador"))
    jugadorEnPartidaBase = cambioJugador(jugadorEnPartida)
    
    
def cambioJugador(jugador):
    return JugadorEnPartida(id_jugador=jugador.id_jugador, id_partida=jugador.id_partida, casillaActual=jugador.casillaActual, jugadorActual=jugador.jugadorActual, avatar=jugador.avatar, juego1=jugador.juegos[0], juego2=jugador.juegos[1], juego3=jugador.juegos[2], juego4=jugador.juegos[3])

def handle_notificarJugadores(data):
    # Emitir la lista actualizada a todos los clientes
    socketio.emit('listaJugadores', [j.to_dict() for j in jugadores_conectados])
    print(jugadores_conectados)

# Resto del código ...  
if __name__ == '__main__':
    with app.app_context():  # Asegúrate de estar dentro del contexto de la aplicación Flask
        db.create_all()
    socketio.run(app,host='0.0.0.0', port=5000, debug=True)