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

class Partida(db.Model):
    id_partida = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    finalizada = db.Column(db.Boolean)

class JugadorEnPartida(db.Model):
    id_jugador = db.Column(db.Integer, db.ForeignKey('jugador.id_jugador'), primary_key=True)
    id_partida = db.Column(db.Integer, db.ForeignKey('partida.id_partida'), primary_key=True)
    casilla_actual = db.Column(db.String(50))
    jugador_actual = db.Column(db.Integer)
    avatar_partida = db.Column(db.String(50))
    juego1 = db.Column(db.Integer)
    juego2 = db.Column(db.Integer)
    juego3 = db.Column(db.Integer)
    juego4 = db.Column(db.Integer)
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
if __name__ == '__main__':
    with app.app_context():  # Asegúrate de estar dentro del contexto de la aplicación Flask
        db.create_all()
    socketio.run(app,host='0.0.0.0', port=5000, debug=True)