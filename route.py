from sqlite3 import IntegrityError

from flask_login import current_user
from app import app
from flask import render_template, request, redirect, url_for, jsonify, session, flash
import secrets
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import Usuario, Treino, Progresso, Mensagem, Conversa
from datetime import datetime, timedelta
from db import db


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

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            if usuario.tipo == "profissional":
                return redirect(url_for("profissional", key=usuario.key, usuario=usuario))
            return redirect(url_for("usuarios", key=usuario.key, usuario=usuario))


       

        return render_template("login.html", erro="Credenciais inválidas")

    return render_template("login.html")

@app.route("/registrar", methods=["POST"])
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

@app.route("/esq_senha", methods=["GET", "POST"])
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
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            return jsonify({"error": "Usuário não encontrado."}), 400
        
        usuario.senha = nova_senha
        db.session.commit()
        
        session.pop("codigo_reset", None)
        session.pop("codigo_verificado", None)
        session.pop("email_reset", None)
        
        return jsonify({"message": "Senha alterada com sucesso."})
    except Exception as e:
        db.session.rollback()
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
    usuario = Usuario.query.filter_by(key=key_procurado).first()
    
    if usuario:
        return {
            'id': usuario.id,
            'key': usuario.key,
            'nome': usuario.nome,
            'email': usuario.email,
            'telefone': usuario.telefone
        }
    
    return None

@app.route("/perfil/<key>", methods=['GET', 'POST'])
def perfil(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return "Usuário não encontrado", 404
    return render_template("perfil.html", key=key, user=user)

@app.route("/suporte/<key>")
def suporte(key):
    user = buscar_usuario_por_key(key)
    return render_template("suporte.html", key=key, user=user)

@app.route("/chat_nutri/<key>")
def chat_nutri(key):
    user = buscar_usuario_por_key(key)
    return render_template("chat_nutri.html", key=key, user=user)

@app.route("/chat_personal/<key>")
def chat_personal(key):
    user = buscar_usuario_por_key(key)
    return render_template("chat_personal.html", key=key, user=user)

@app.route("/profissional/<key>")
def profissional(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario or usuario.tipo != "profissional":
        flash('Acesso restrito a profissionais', 'danger')
        return redirect(url_for('login'))
    
    # Buscar alunos do profissional (todos os usuários)
    alunos = Usuario.query.filter_by(tipo='usuario').all()
    
    # Estatísticas
    alunos_ativos = Usuario.query.filter_by(tipo='usuario').count()
    treinos_ativos = Treino.query.filter_by(status='ativo').count()
    
    # Alunos inativos (último acesso há mais de 7 dias)
    # Você precisaria adicionar um campo 'ultimo_acesso' no modelo Usuario
    # alunos_inativos = 0  # Implementar lógica
    
    return render_template('profissional.html',
                            key=key, 
                            user=usuario,
                            alunos=alunos,
                            alunos_ativos=alunos_ativos,
                            treinos_ativos=treinos_ativos)

@app.route('/api/alunos/<key>')
def api_alunos(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario.tipo == "profissional":
        return jsonify({'error': 'Acesso não autorizado'}), 403
        
    
    alunos = Usuario.query.filter_by(tipo='usuario').all()
    
    alunos_data = []
    for aluno in alunos:
        # Buscar treino ativo do aluno
        treino_ativo = Treino.query.filter_by(aluno_id=aluno.id, status='ativo').first()
        
        # Buscar progresso
        progresso = Progresso.query.filter_by(aluno_id=aluno.id).order_by(Progresso.data_registro.desc()).first()
        
        alunos_data.append({
            'id': aluno.id,
            'nome': aluno.nome,
            'treino': treino_ativo.nome if treino_ativo else 'Sem treino',
            'nivel': treino_ativo.tipo if treino_ativo else '-',
            'progresso': progresso.porcentagem if progresso else 0,
            'status': 'Ativo' if treino_ativo else 'Inativo',
            'ultimo_acesso': 'Hoje'  # Implementar lógica real
        })
    
    return jsonify(alunos_data)

@app.route('/api/estatisticas/<key>')

def api_estatisticas(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario.tipo == "profissional":
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    total_alunos = Usuario.query.filter_by(tipo='usuario').count()
    treinos_ativos = Treino.query.filter_by(status='ativo').count()
    # chats_ativos = 0  # Implementar sistema de chat
    
    return jsonify({
        'alunos_ativos': total_alunos,
        'treinos_ativos': treinos_ativos,
        'alunos_inativos': 0,  # Implementar lógica
        'chats_ativos': 5  # Placeholder
    }) 


@app.route("/suporte_profissional/<key>", methods=['GET'])
def suporte_pro(key):
    user = buscar_usuario_por_key(key)
    return render_template("suporte_profissional.html", key=key, user=user)

@app.route('/api/conversas/<key>')
def api_conversas(key):
    if current_user.key != key or not current_user.is_profissional():
        return jsonify({'error': 'Não autorizado'}), 403
    
    # Buscar todas as conversas com informações do usuário
    conversas = Conversa.query.join(Usuario).add_columns(
        Conversa.id,
        Usuario.nome,
        Usuario.id.label('usuario_id'),
        Conversa.tipo_suporte,
        Conversa.status,
        Conversa.data_ultima_mensagem
    ).filter(Conversa.usuario_id == Usuario.id).all()
    
    # Formatar resposta
    resultado = []
    for conversa in conversas:
        # Buscar última mensagem
        ultima_mensagem = Mensagem.query.filter_by(conversa_id=conversa.id).order_by(Mensagem.data_envio.desc()).first()
        
        # Contar mensagens não lidas
        nao_lidas = Mensagem.query.filter_by(
            conversa_id=conversa.id, 
            destinatario_id=current_user.id,
            lida=False
        ).count()
        
        resultado.append({
            'id': conversa.id,
            'name': conversa.nome,
            'type': conversa.tipo_suporte,
            'lastMessage': ultima_mensagem.conteudo if ultima_mensagem else 'Nenhuma mensagem',
            'time': conversa.data_ultima_mensagem.strftime('%H:%M') if conversa.data_ultima_mensagem else '',
            'unread': nao_lidas,
            'avatar': conversa.nome[0].upper() if conversa.nome else 'U',
            'status': 'online'  # Em uma aplicação real, verificar status real
        })
    
    return jsonify(resultado)

# API para carregar mensagens de uma conversa
@app.route('/api/mensagens/<key>/<int:conversa_id>')
def api_mensagens(key, conversa_id):
    if current_user.key != key:
        return jsonify({'error': 'Não autorizado'}), 403
    
    # Verificar se o usuário tem acesso à conversa
    conversa = Conversa.query.get_or_404(conversa_id)
    if not current_user.is_profissional() and conversa.usuario_id != current_user.id:
        return jsonify({'error': 'Acesso negado'}), 403
    
    # Buscar mensagens da conversa
    mensagens = Mensagem.query.filter_by(conversa_id=conversa_id).order_by(Mensagem.data_envio.asc()).all()
    
    # Marcar mensagens como lidas se for o destinatário
    for msg in mensagens:
        if msg.destinatario_id == current_user.id and not msg.lida:
            msg.lida = True
            db.session.commit()
    
    # Formatar resposta
    resultado = []
    for msg in mensagens:
        resultado.append({
            'content': msg.conteudo,
            'sent': msg.remetente_id == current_user.id,
            'time': msg.data_envio.strftime('%H:%M')
        })
    
    return jsonify(resultado)

# API para enviar mensagem
@app.route('/api/enviar/<key>', methods=['POST'])
def api_enviar(key):
    if current_user.key != key:
        return jsonify({'error': 'Não autorizado'}), 403
    
    data = request.get_json()
    conteudo = data.get('conteudo')
    tipo_suporte = data.get('tipo_suporte', 'geral')
    
    if not conteudo:
        return jsonify({'error': 'Mensagem vazia'}), 400
    
    # Para usuários: encontrar ou criar conversa
    if not current_user.is_profissional():
        # Encontrar profissional disponível baseado no tipo de suporte
        if tipo_suporte == 'personal':
            profissional = Usuario.query.filter_by(tipo='personal').first()
        elif tipo_suporte == 'nutricionista':
            profissional = Usuario.query.filter_by(tipo='nutricionista').first()
        else:
            # Se não especificado, encontrar qualquer profissional
            profissional = Usuario.query.filter(Usuario.tipo.in_(['personal', 'nutricionista'])).first()
        
        if not profissional:
            return jsonify({'error': 'Nenhum profissional disponível'}), 400
        
        # Verificar se já existe uma conversa aberta
        conversa = Conversa.query.filter_by(
            usuario_id=current_user.id, 
            tipo_suporte=tipo_suporte,
            status='aberta'
        ).first()
        
        # Se não existir, criar uma nova conversa
        if not conversa:
            conversa = Conversa(
                usuario_id=current_user.id,
                tipo_suporte=tipo_suporte,
                status='aberta'
            )
            db.session.add(conversa)
            db.session.commit()
    else:
        # Para profissionais: usar a conversa especificada
        conversa_id = data.get('conversa_id')
        if not conversa_id:
            return jsonify({'error': 'ID da conversa não especificado'}), 400
        
        conversa = Conversa.query.get_or_404(conversa_id)
        
        # Destinatário é o usuário da conversa
        profissional = current_user
        destinatario_id = conversa.usuario_id
    
    # Criar mensagem
    if current_user.is_profissional():
        mensagem = Mensagem(
            conversa_id=conversa.id,
            remetente_id=current_user.id,
            destinatario_id=conversa.usuario_id,
            conteudo=conteudo
        )
    else:
        mensagem = Mensagem(
            conversa_id=conversa.id,
            remetente_id=current_user.id,
            destinatario_id=profissional.id,
            conteudo=conteudo
        )
    
    # Atualizar data da última mensagem da conversa
    conversa.data_ultima_mensagem = datetime.utcnow()
    
    db.session.add(mensagem)
    db.session.commit()
    
    return jsonify({'success': True, 'mensagem_id': mensagem.id})