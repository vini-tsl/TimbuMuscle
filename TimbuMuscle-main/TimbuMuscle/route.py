from main import app
from flask import render_template, request, redirect, url_for, jsonify, session, flash
import secrets
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

@app.route("/")
def homepage():
    return render_template("index.html")

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        try:
            with open("bdd.txt", "r") as file:
                for linha in file:
                    partes = linha.strip().split(" | ")
                    dados = {}
                    for parte in partes:
                        if ": " in parte:
                            chave, valor = parte.split(": ", 1)
                            dados[chave] = valor

                    if dados.get("email") == email and dados.get("senha") == senha:
                        key = dados.get("key")
                        user = dados.get("nome")
                        return redirect(url_for("usuarios", key=key, user=user))
        except FileNotFoundError:
            pass

        return render_template("login.html", erro="Credenciais inválidas")

    return render_template("login.html")

@app.route("/registrar", methods=["POST"])
def registrar():
    key = secrets.token_hex(6)
    nome = request.form.get("nome")
    email = request.form.get("email")
    senha = request.form.get("senha")
    telefone = request.form.get("telefone")

    try:
        with open("bdd.txt", "r") as file:
            for linha in file:
                partes = linha.strip().split(" | ")
                dados = {}
                for parte in partes:
                    if ": " in parte:
                        chave, valor = parte.split(": ", 1)
                        dados[chave] = valor

                if dados.get("nome") == nome:
                    return render_template("login.html", erro="Nome de usuário já cadastrado.")
                if dados.get("email") == email:
                    return render_template("login.html", erro="Email já cadastrado.")
                if dados.get("telefone") == telefone:
                    return render_template("login.html", erro="Telefone já cadastrado.")
                
                if dados.get("key") == key:
                    while True:
                        key = secrets.token_hex(6)
                        if dados.get("key") != key:
                            break
                        
    except FileNotFoundError:
        pass

    with open("bdd.txt", "a") as file:
        file.write(f"key: {key} | nome: {nome} | telefone: {telefone}| email: {email} | senha: {senha}\n")

    return render_template("login.html", sucesso="Cadastro realizado com sucesso!")

@app.route("/esq_senha", methods=["GET", "POST"])
def esq_senha():
    if request.method == "POST":
        email = request.form.get("email")
        found = False
        try:
            with open("bdd.txt", "r") as file:
                for linha in file:
                    if f"email: {email}" in linha:
                        found = True
                        break
        except FileNotFoundError:
            return jsonify({"error": "Arquivo de usuários não encontrado."}), 500
        
        if not found:
            return jsonify({"error": "Email não cadastrado."}), 400
        
        codigo = f"{random.randint(100000, 999999)}"
        session["email_reset"] = email
        session["codigo_reset"] = codigo
        

        sucesso = enviar_codigo_por_email(email, codigo)
        if not sucesso:
            flash("Falha ao enviar email. Tente novamente mais tarde.", "erro")
            return redirect(url_for("esq_senha"))

        
        return jsonify({"message": "Código enviado para o email."})
    
    return render_template("esq_senha.html")

@app.route("/verificar_codigo", methods=["POST"])
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

@app.route("/alterar_senha", methods=["POST"])
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
        linhas = []
        atualizado = False
        with open("bdd.txt", "r") as file:
            for linha in file:
                if f"email: {email}" in linha:
                    partes = linha.strip().split(" | ")
                    dados = {}
                    for parte in partes:
                        if ": " in parte:
                            chave, valor = parte.split(": ", 1)
                            dados[chave] = valor
                    dados["senha"] = nova_senha
                    nova_linha = " | ".join([f"{k}: {v}" for k, v in dados.items()])
                    linhas.append(nova_linha + "\n")
                    atualizado = True
                else:
                    linhas.append(linha)
        if atualizado:
            with open("bdd.txt", "w") as file:
                file.writelines(linhas)
            session.pop("codigo_reset", None)
            session.pop("codigo_verificado", None)
            session.pop("email_reset", None)
            return jsonify({"message": "Senha alterada com sucesso."})
        else:
            return jsonify({"error": "Usuário não encontrado."}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao atualizar senha: {str(e)}"}), 500

@app.route("/usuarios/<key>", methods=['GET', 'POST'])
def usuarios(key):
    user = buscar_usuario_por_key(key)
    return render_template("usuarios.html", key=key, user=user)

@app.route("/formulario/<key>")
def formulario(key):
    user = buscar_usuario_por_key(key)
    return render_template("formulario.html", key=key, user=user)

@app.route("/treino/<key>")
def mostrar_treinos(key):
    user = buscar_usuario_por_key(key)
    return render_template('treino.html', key=key, user=user)

def buscar_usuario_por_key(key_procurado):
    with open("bdd.txt", "r") as arquivo:
        for linha in arquivo:
            if f"key: {key_procurado}" in linha:
                partes = linha.strip().split(" | ")
                dados = {}
                for parte in partes:
                    k, v = parte.split(": ", 1)
                    dados[k.strip()] = v.strip()
                return dados
    return None

@app.route("/perfil/<key>", methods=['GET', 'POST'])
def perfil(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return "Usuário não encontrado", 404
    return render_template("perfil.html", key=key, user=user)





