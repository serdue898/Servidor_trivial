from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit, join_room,leave_room
from flask_sqlalchemy import SQLAlchemy
import json
from flask_bcrypt import Bcrypt


app = Flask(__name__)
bcrypt = Bcrypt(app)
socketio = SocketIO(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./trivial.db'
db = SQLAlchemy(app)


class Jugador(db.Model):
    id_jugador = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    contraseña = db.Column(db.String(50))
    avatar = 0
    partida = 0
    host = False

    def to_dict(self):
        jugador_dict = {key: value for key, value in self.__dict__.items() if key != '_sa_instance_state'}
        jugador_json = json.dumps(jugador_dict, default=str)
        return jugador_json
    # Método para establecer la contraseña y crear su hash
    def establecer_contraseña(self, contraseña):
        self.contraseña = bcrypt.generate_password_hash(contraseña).decode('utf-8')

    # Método para verificar la contraseña
    def verificar_contraseña(self, contraseña):
        return bcrypt.check_password_hash(self.contraseña, contraseña)

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
        jugador_dict = {key: value for key, value in self.__dict__.items() if key != '_sa_instance_state'}
        jugador_json = json.dumps(jugador_dict, default=str)
        return jugador_json


class JugadorEnPartidaOnline():
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


jugadores_conectados = {}
jugadores_loggeados = []




@socketio.on('obtener_partidas')
def handle_obtener_partidas():
    print("Obteniendo partidas")
    partidas = Partida.query.filter_by(finalizada=False).all()
    partidas_json = [{"id": partida.id_partida, "nombre": partida.nombre} for partida in partidas]
    return partidas_json


@socketio.on('addJugador')
def handle_add_jugador(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return

    jugador = Jugador(nombre=jugador_dict.get('nombre'), partida=jugador_dict.get('partida'))
    if existeJugador(jugador_dict.get('nombre')):
        db.session.add(jugador)
        db.session.commit()

    jugador_nuevo = Jugador.query.filter_by(nombre=jugador_dict.get('nombre')).first()
    jugador_nuevo.avatar = jugador_dict.get('avatar')
    jugador_nuevo.partida = jugador_dict.get('partida')

    if jugador_dict.get('host') == None:
        jugador_nuevo.host = False
    else:
        jugador_nuevo.host = jugador_dict.get('host')

    if jugador_nuevo.partida not in jugadores_conectados:
        jugadores_conectados[jugador_nuevo.partida] = []

    jugadores_conectados[jugador_nuevo.partida].append(jugador_nuevo)
    join_room(jugador_nuevo.partida)
    handle_notificarJugadores(jugador_nuevo.partida)


def existeJugador(name):
    jugador = Jugador.query.filter_by(nombre=name).first()
    if jugador:
        return False
    else:
        return True


@socketio.on('desconectar')
def handle_delete_jugador(data):
    print("Desconectando jugador")

    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return

    jugador_id = jugador_dict.get('nombre')

    jugador_a_eliminar = next((jugador for jugador in jugadores_conectados[jugador_dict.get('partida')] if jugador.nombre == jugador_id), None)

    if jugador_a_eliminar:
        jugadores_conectados[jugador_a_eliminar.partida].remove(jugador_a_eliminar)
        handle_desloggear_jugador(jugador_a_eliminar.nombre)
        
        
        jugadores_partida = jugadores_conectados[jugador_a_eliminar.partida]
        leave_room(jugador_a_eliminar.partida)
        if not jugadores_partida:
            db.session.delete(Partida.query.filter_by(id_partida=jugador_a_eliminar.partida).first())
            db.session.commit()
            return

        if jugador_a_eliminar.host:
            jugadores_partida[0].host = True
        print(f"eliminado el jugador con id {jugador_id}")
        handle_notificarJugadores(jugador_a_eliminar.partida)
    else:
        print(f"No se encontró el jugador con id {jugador_id}")

@socketio.on('desloggear')
def handle_desloggear_jugador(data):
    try:
            jugador_a_eliminar = next((jugador for jugador in jugadores_loggeados if jugador.nombre == data), None)
            jugadores_loggeados.remove(jugador_a_eliminar)
    except:
        print("no estaba loggeado")


@socketio.on('actualizarJugador')
def handle_actualizar_jugador(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return

    jugador_id = jugador_dict.get('nombre')
    jugador_avatar = jugador_dict.get('avatar')

    jugador_a_actualizar = next((jugador for jugador in jugadores_conectados[jugador_dict.get('partida')] if
                                 jugador.nombre == jugador_id), None)

    if jugador_a_actualizar:
        jugador_a_actualizar.avatar = jugador_dict.get('avatar')
        jugador_a_actualizar.partida = jugador_dict.get('partida')
        handle_notificarJugadores(jugador_a_actualizar.partida)
    else:
        print(f"No se encontró el jugador con id {jugador_id}")


@socketio.on('actualizarJugadores')
def handle_notificarJugadores(partida):
    join_room(partida)
    socketio.emit('listaJugadores', [j.to_dict() for j in jugadores_conectados.get(partida, [])], room=partida)


@socketio.on('empezarPartida')
def handle_empezar_partida(data):
    id_partida = data
    jugadoresEnPartida = jugadores_conectados.get(id_partida, [])
    juegosNuevos = [False, False, False, False]

    for jugador in jugadoresEnPartida:
        primero = 0
        if jugadoresEnPartida.index(jugador) == 0:
            primero = 1
        jugador = JugadorEnPartida(id_jugador=jugador.id_jugador, id_partida=id_partida, casillaActual="4_4",
                                   jugadorActual=primero, avatar=jugador.avatar, juego1=0, juego2=0, juego3=0,
                                   juego4=0)
        db.session.add(jugador)
    
    db.session.query(Partida).filter_by(id_partida=id_partida).first().finalizada = True

    db.session.commit()
    jugadores = db.session.query(JugadorEnPartida).filter_by(id_partida=id_partida).all()
    jugadoresEnPartida = []

    for jugador in jugadores:
        primero = False
        if jugadores.index(jugador) == 0:
            primero = True
        jugador = cambiarBaseAJugadorEnPartida(jugador)
        jugadoresEnPartida.append(jugador)

    socketio.emit('empezarPartida', [j.to_dict() for j in jugadoresEnPartida], room=id_partida)

    jugadores_conectados[id_partida] = jugadoresEnPartida


def cambiarBaseAJugadorEnPartida(jugador):
    juegos = [jugador.juego1 == 1, jugador.juego2 == 1, jugador.juego3 == 1, jugador.juego4 == 1]

    return JugadorEnPartidaOnline(id_jugador=jugador.id_jugador, id_partida=jugador.id_partida,
                                  casillaActual=jugador.casillaActual, jugadorActual=jugador.jugadorActual == 1,
                                  avatar=jugador.avatar, juegos=juegos)

def jsonAJugadorEnPartidaOnline(jugador_dict):
    jugadoractual = JugadorEnPartidaOnline(
        id_jugador=jugador_dict.get('id_jugador'),
        id_partida=jugador_dict.get('partida'),
        casillaActual=jugador_dict.get('casillaActual'),
        jugadorActual=jugador_dict.get('jugadorActual'),
        avatar=jugador_dict.get('avatar'),
        juegos=jugador_dict.get('juegos')
    )
    return jugadoractual
   

@socketio.on('moverJugador')
def handle_mover_jugador(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return
    jugadoractual = jugador_dict

    jugadorfalladonuevo = next((jugador for jugador in jugadores_conectados[jugador_dict.get('partida')] if jugador.id_jugador == jugador_dict.get("id_jugador")), None)
    popsicionnueva = jugadores_conectados[jugador_dict.get('partida')].index(jugadorfalladonuevo)
    jugadores_conectados[jugador_dict.get('partida')][popsicionnueva]= jsonAJugadorEnPartidaOnline(jugadoractual)

    if (not jugador_dict.get('jugadorActual')):
        jugadorfallado = next((jugador for jugador in jugadores_conectados[jugador_dict.get('partida')] if jugador.id_jugador == jugador_dict.get("id_jugador")), None)

        #coger la posicion del jugadorfallado
        popsicion = jugadores_conectados[jugador_dict.get('partida')].index(jugadorfallado)
        jugadores_conectados[jugador_dict.get('partida')][popsicion].jugadorActual = False
        popsicion += 1
        if (popsicion == len(jugadores_conectados[jugador_dict.get('partida')])):
            jugadoractualnuevo = jugadores_conectados[jugador_dict.get('partida')][0]
            jugadores_conectados[jugador_dict.get('partida')][0].jugadorActual = True
            jugadoractual = jugadoractualnuevo.to_dict()
        else:
            jugadores_conectados[jugador_dict.get('partida')][popsicion].jugadorActual = True
            jugadoractualnuevo = jugadores_conectados[jugador_dict.get('partida')][popsicion]
            jugadoractual = jugadoractualnuevo.to_dict()


    socketio.emit('moverJugadorOnline', jugadoractual , room=jugador_dict.get('partida'))


@socketio.on('crearPartida')
def handle_crear_partida(data):
    if existePartida(data):
        socketio.emit('partidaCreada', "null")
        return
    
    db.session.add(Partida(nombre=data, finalizada=False))
    db.session.commit()

    partida = Partida.query.filter_by(nombre=data).first()

    nueva_partida = partida.id_partida
    join_room(nueva_partida)

    if nueva_partida not in jugadores_conectados:
        jugadores_conectados[nueva_partida] = []

    

    socketio.emit('partidaCreada', nueva_partida)


def existePartida(name):
    partida = Partida.query.filter_by(nombre=name).first()
    if partida:
        return True
    else:
        return False


def cambioJugador(jugador):
    return JugadorEnPartida(id_jugador=jugador.id_jugador, id_partida=jugador.id_partida,
                            casillaActual=jugador.casillaActual, jugadorActual=jugador.jugadorActual,
                            avatar=jugador.avatar, juego1=jugador.juegos[0], juego2=jugador.juegos[1],
                            juego3=jugador.juegos[2], juego4=jugador.juegos[3])


@socketio.on('registrarJugador')
def handle_registrar_jugador(data):
    jugador_json = data
    try:
        jugador_dict = json.loads(jugador_json)
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return
    existe = existeJugador(jugador_dict.get('nombre'))
    if existe:
        jugador = Jugador(nombre=jugador_dict.get('nombre'))
        jugador.establecer_contraseña(jugador_dict.get('contraseña'))
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

    client_sid = request.sid
    jugadores_nombre = [jugador.nombre for jugador in jugadores_loggeados]

    if jugador_dict.get('nombre') in jugadores_nombre:
        socketio.emit('login_respuesta', "loggeado", room=client_sid)
        return

    jugador = Jugador.query.filter_by(nombre=jugador_dict.get('nombre')).first()
    jugadores_loggeados.append(jugador)

    if jugador:
        if jugador.verificar_contraseña(jugador_dict.get('contraseña')):
            jugador.avatar = jugador_dict.get('avatar')

            socketio.emit('login_respuesta', jugador.to_dict(), room=client_sid)
        else:
            socketio.emit('login_respuesta', "error", room=client_sid)
    else:
        socketio.emit('login_respuesta', "null", room=client_sid)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
