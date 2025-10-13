from flask import Flask
from db import db
from models import Usuario, Treino, Progresso, Exercicio, Mensagem, Conversa

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///users.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "JSA329103291IOKSA381938"
db.init_app(app)

from route import *

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)