import json
from flask import Flask, jsonify


app = Flask(__name__)
#para acceder a las preguntas en la api se debe ingresar a la siguiente ruta
#http://127.0.0.1:5000/preguntas
#ejecute la aplicacion desde visual o en su defecto desde la consola con el comando python api.py
@app.route('/preguntas', methods=['GET'])
def obtener_asignaturas():
    with open('C:/Users/ADMIN/Downloads/leerJson/preguntas.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        print(data)
    # Configura la cabecera para especificar la codificación UTF-8
    response = jsonify(data)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
