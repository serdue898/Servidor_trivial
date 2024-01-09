class Partida(db.Model):
    id_partida = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    finalizada = db.Column(db.Boolean)