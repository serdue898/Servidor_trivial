
class Jugador(db.Model):
    id_jugador = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    def to_dict(self):
        return self.__dict__
