from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
import secrets
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import Usuario
from db import db
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)

def enviar_codigo_por_email(destinatario, codigo):
    remetente = "timbumuscle@gmail.com"
    senha = "cyhg qwah ibtz dwsn"

    assunto = "Código de verificação - TimbuMuscle"
    corpo = f"""
    <html>
      <body>
        <h2>Seu código de verificação</h2>
        <p>Use o código abaixo para redefinir sua senha:</p>
        <h1 style="color: #FF4B2B;">{codigo}</h1>
        <p>Se você não solicitou isso, ignore este email.</p>
      </body>
    </html>
    """

    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = assunto
    mensagem["From"] = remetente
    mensagem["To"] = destinatario

    parte_html = MIMEText(corpo, "html")
    mensagem.attach(parte_html)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
            servidor.starttls()
            servidor.login(remetente, senha)
            servidor.sendmail(remetente, destinatario, mensagem.as_string())
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao enviar email: {e}")
        return False

@auth_bp.route("/")
def homepage():
    return render_template("index.html")

@auth_bp.route("/sobre")
def sobre():
    return render_template("sobre.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.senha_hash == senha:  # Ajuste conforme seu modelo
            if usuario.tipo == "profissional":
                return redirect(url_for("profissional.profissional", key=usuario.key))
            return redirect(url_for("usuarios.usuarios", key=usuario.key))

        return render_template("login.html", erro="Credenciais inválidas")

    return render_template("login.html")

@auth_bp.route("/registrar", methods=["POST"])
def registrar():
    key = secrets.token_hex(6)
    nome = request.form.get("nome")
    email = request.form.get("email")
    senha = request.form.get("senha")
    telefone = request.form.get("telefone") 

    if Usuario.query.filter_by(nome=nome).first():
        return render_template("login.html", erro="Nome de usuário já cadastrado.")
    
    if Usuario.query.filter_by(email=email).first():
        return render_template("login.html", erro="Email já cadastrado.")
    
    if Usuario.query.filter_by(telefone=telefone).first():
        return render_template("login.html", erro="Telefone já cadastrado.")
    
    while Usuario.query.filter_by(key=key).first():
        key = secrets.token_hex(6)
                        
    novo_usuario = Usuario(
        key=key,
        nome=nome,
        email=email,
        senha_hash=senha,
        telefone=telefone
    )
    
    try:
        db.session.add(novo_usuario)
        db.session.commit()
        return render_template("login.html", sucesso="Cadastro realizado com sucesso!")
    
    except IntegrityError:
        db.session.rollback()
        return render_template("login.html", erro="Erro ao cadastrar usuário. Tente novamente.")

@auth_bp.route("/esq_senha", methods=["GET", "POST"])
def esq_senha():
    if request.method == "POST":
        email = request.form.get("email")

        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            return jsonify({"error": "Email não cadastrado."}), 400
        
        codigo = f"{random.randint(100000, 999999)}"
        session["email_reset"] = email
        session["codigo_reset"] = codigo
        
        sucesso = enviar_codigo_por_email(email, codigo)

        if not sucesso:
            flash("Falha ao enviar email. Tente novamente mais tarde.", "erro")
            return redirect(url_for("auth.esq_senha"))

        return jsonify({"message": "Código enviado para o email."})
    
    return render_template("esq_senha.html")

@auth_bp.route("/verificar_codigo", methods=["POST"])
def verificar_codigo():
    codigo_enviado = request.form.get("codigo")
    codigo_armazenado = session.get("codigo_reset")
    
    if not codigo_armazenado:
        return jsonify({"error": "Nenhum código gerado para esta sessão."}), 400
    
    if codigo_enviado == codigo_armazenado:
        session["codigo_verificado"] = True
        return jsonify({"message": "Código confirmado."})
    else:
        return jsonify({"error": "Código inválido."}), 400

@auth_bp.route("/alterar_senha", methods=["POST"])
def alterar_senha():
    if not session.get("codigo_verificado"):
        return jsonify({"error": "Código não verificado."}), 400
    
    nova_senha = request.form.get("nova_senha")
    confirmar_senha = request.form.get("confirmar_senha")
    email = session.get("email_reset")
    
    if not nova_senha or not confirmar_senha:
        return jsonify({"error": "Preencha todos os campos."}), 400
    if nova_senha != confirmar_senha:
        return jsonify({"error": "Senhas não conferem."}), 400
    if len(nova_senha) < 6:
        return jsonify({"error": "Senha deve ter ao menos 6 caracteres."}), 400
    
    try:
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            return jsonify({"error": "Usuário não encontrado."}), 400
        
        usuario.senha_hash = nova_senha
        db.session.commit()
        
        session.pop("codigo_reset", None)
        session.pop("codigo_verificado", None)
        session.pop("email_reset", None)
        
        return jsonify({"message": "Senha alterada com sucesso."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao atualizar senha: {str(e)}"}), 500
    
