from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO , emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
import json 


app = Flask(__name__)
socketio = SocketIO(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./trivial.db'
db = SQLAlchemy(app)
class Jugador(db.Model):
    id_jugador = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    contraseña = db.Column(db.String(50))
    avatar = 0
    partida=0
    host = False
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
    def __init__(self, id_jugador, id_partida, casillaActual, jugadorActual, avatar, juegos):
        self.id_jugador = id_jugador
        self.partida = id_partida
        self.casillaActual = casillaActual
        self.jugadorActual = jugadorActual
        self.avatar = avatar
        self.juegos = juegos
    def to_dict(self):
        jugador_dict = {key: value for key, value in self.__dict__.items() if key != '_sa_instance_state'}
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
    #si el host es nulo devuelve false
    if jugador_dict.get('host') == None:
        jugador_nuevo.host = False
    else:
        jugador_nuevo.host = jugador_dict.get('host')
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
    print("Desconectando jugador")

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
        jugadores_conectados.remove(jugador_a_eliminar)
        jugadores_partida = [jugador for jugador in jugadores_conectados if jugador.partida == jugador_a_eliminar.partida]
        # Verifjugadores
        if not jugadores_partida:
            db.session.delete(Partida.query.filter_by(id_partida=jugador_a_eliminar.partida).first())
            db.session.commit()
            return

        # Notificar a los demás jugadores sobre la actualización
        if jugador_a_eliminar.host:
            jugadores_conectados[0].host = True
        print(f"eliminado el jugador con id {jugador_id}")
        handle_notificarJugadores()
    else:
        print(f"No se encontró el jugador con id {jugador_id}")

@socketio.on('actualizarJugador')
def handle_actualizar_jugador(data):
    # Deserializar el objeto JSON recibido del cliente
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return

    # Obtener el id del jugador a desconectar
    jugador_id = jugador_dict.get('nombre')
    jugador_avatar = jugador_dict.get('avatar')
    # Buscar el jugador en la lista por su id
    jugador_a_actualizar = next((jugador for jugador in jugadores_conectados if jugador.nombre == jugador_id), None)

    # Verificar si se encontró el jugador
    if jugador_a_actualizar:
        # Actualizar el jugador de la lista
        jugador_a_actualizar.avatar = jugador_dict.get('avatar')
        jugador_a_actualizar.partida = jugador_dict.get('partida')
        # Notificar a los demás jugadores sobre la actualización
        handle_notificarJugadores()
    else:
        print(f"No se encontró el jugador con id {jugador_id}")

@socketio.on('actualizarJugadores')
def handle_notificarJugadores():
    # Emitir la lista actualizada a todos los clientes
    socketio.emit('listaJugadores', [j.to_dict() for j in jugadores_conectados])
    print(j.to_dict() for j in jugadores_conectados)

@socketio.on('empezarPartida')
def handle_empezar_partida(data):
    id_partida = data
    jugadoresEnPartida=[]
    juegosNuevos = [False,False,False,False]
    for jugador in jugadores_conectados:
        if jugador.partida == id_partida:
            jugadoresEnPartida.append(jugador)
    for jugador in jugadoresEnPartida:
        primero =0
        if jugadoresEnPartida.index(jugador) == 0:
            primero = 1
        jugador = JugadorEnPartida(id_jugador=jugador.id_jugador, id_partida=id_partida, casillaActual="4_4", jugadorActual=primero, avatar=jugador.avatar, juego1=0, juego2=0, juego3=0, juego4=0)
        db.session.add(jugador)
    db.session.commit()
    jugadores = db.session.query(JugadorEnPartida).filter_by(id_partida=id_partida).all()
    jugadoresEnPartida = []
    for jugador in jugadores:
        
        primero =False
        if jugadores.index(jugador) == 0:
            primero = True
        jugador = cambiarBaseAJugadorEnPartida(jugador)
        jugadoresEnPartida.append(jugador)
    socketio.emit('empezarPartida', [j.to_dict() for j in jugadoresEnPartida])
    jugadores_conectados.clear()

def cambiarBaseAJugadorEnPartida(jugador):
    juegos = [jugador.juego1==1, jugador.juego2==1, jugador.juego3==1, jugador.juego4==1]

    return jugadorEnPartidaOnline(id_jugador=jugador.id_jugador, id_partida=jugador.id_partida, casillaActual=jugador.casillaActual, jugadorActual=jugador.jugadorActual==1, avatar=jugador.avatar, juegos=juegos)

@socketio.on('moverJugador')
def handle_mover_jugador(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return
    socketio.emit('moverJugadorOnline', jugador_dict)

@socketio.on('crearPartida')
def handle_crear_partida(data):
    if existePartida(data):
        socketio.emit('partidaCreada',"null")
        return
    db.session.add(Partida(nombre=data, finalizada=False))
    db.session.commit()
    partida = Partida.query.filter_by(nombre=data).first()
    socketio.emit('partidaCreada', partida.id_partida)
    
def existePartida(name):
    partida = Partida.query.filter_by(nombre=name).first()
    if partida:
        return  True
    else:
        return False

def cambioJugador(jugador):
    return JugadorEnPartida(id_jugador=jugador.id_jugador, id_partida=jugador.id_partida, casillaActual=jugador.casillaActual, jugadorActual=jugador.jugadorActual, avatar=jugador.avatar, juego1=jugador.juegos[0], juego2=jugador.juegos[1], juego3=jugador.juegos[2], juego4=jugador.juegos[3])

@socketio.on('registrarJugador')
def handle_registrar_jugador(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return
    existe =existeJugador(jugador_dict.get('nombre'))
    if existe :
        jugador = Jugador(nombre=jugador_dict.get('nombre'), contraseña=jugador_dict.get('contraseña'))
        db.session.add(jugador)
        db.session.commit()
        jugador = Jugador.query.filter_by(nombre=jugador_dict.get('nombre')).first()
        jugador.avatar = jugador_dict.get('avatar')
        socketio.emit('registrarJugador', jugador.to_dict())
        return
    socketio.emit('registrarJugador', "null")
    
@socketio.on('login')
def handle_login(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return

    jugador = Jugador.query.filter_by(nombre=jugador_dict.get('nombre')).first()

    if jugador:
        if jugador.contraseña == jugador_dict.get('contraseña'):
            jugador.avatar = jugador_dict.get('avatar')
            
            # Obtener el ID de sesión del cliente que envió la solicitud
            client_sid = request.sid
            
            # Emitir el mensaje solo al cliente que envió la solicitud
            socketio.emit('login', jugador.to_dict(), room=client_sid)
        else:
            socketio.emit('login', "error")
    else:
        socketio.emit('login', "null")

# Resto del código ...  
if __name__ == '__main__':
    with app.app_context():  # Asegúrate de estar dentro del contexto de la aplicación Flask
        db.create_all()
    socketio.run(app,host='0.0.0.0', port=5000, debug=True)