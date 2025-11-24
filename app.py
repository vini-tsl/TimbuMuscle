from flask import Flask
from db import db
from models import Usuario, Treino, Progresso, ExercicioTreino, Mensagem, Conversa, CatalogoExercicio

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///users.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "JSA329103291IOKSA381938"
db.init_app(app)

# Importar e registrar blueprints
from blueprints.auth import auth_bp
from blueprints.usuarios import usuarios_bp
from blueprints.profissional import profissional_bp
from blueprints.suporte import suporte_bp
from blueprints.chat import chat_bp
from blueprints.admin import admin_bp
from blueprints.treinos import treinos_bp
from blueprints.formulario import formulario_bp

app.register_blueprint(formulario_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(profissional_bp)
app.register_blueprint(suporte_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(treinos_bp)  

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)