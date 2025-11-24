from flask import Blueprint, render_template, request, redirect, url_for
from models import Usuario, Treino

usuarios_bp = Blueprint('usuarios', __name__)

def buscar_usuario_por_key(key):
    """Busca usuário por key"""
    if not key or key == 'None':
        return None
    
    try:
        usuario = Usuario.query.filter_by(key=key).first()
        return usuario
    except Exception as e:
        print(f"Erro na busca: {e}")
        return None

@usuarios_bp.route("/usuarios/<key>", methods=['GET', 'POST'])
def usuarios(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return redirect(url_for('auth.login'))
    return render_template("usuarios.html", key=key, user=user)

@usuarios_bp.route("/formulario/<key>")
def formulario(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return redirect(url_for('auth.login'))
    return render_template("formulario.html", key=key, user=user)

@usuarios_bp.route("/treino/<key>")
def mostrar_treinos(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return redirect(url_for('auth.login'))
    return render_template('treinos.html', key=key, user=user)

@usuarios_bp.route("/perfil/<key>", methods=['GET', 'POST'])
def perfil(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return redirect(url_for('auth.login'))
    return render_template("perfil.html", key=key, user=user)

@usuarios_bp.route("/chat_nutri/<key>")
def chat_nutri(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return redirect(url_for('auth.login'))
    return render_template("chat_nutri.html", key=key, user=user)

@usuarios_bp.route("/chat_personal/<key>")
def chat_personal(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return redirect(url_for('auth.login'))
    return render_template("chat_personal.html", key=key, user=user)

@usuarios_bp.route('/executar-treino/<int:treino_id>/<key>')
def executar_treino(treino_id, key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario:
        return "Usuário não encontrado", 404
    
    treino = Treino.query.get(treino_id)
    if not treino or treino.aluno_id != usuario.id:
        return "Treino não encontrado", 404
    
    return render_template('executar_treino.html', 
                         user=usuario, 
                         key=key, 
                         treino=treino)