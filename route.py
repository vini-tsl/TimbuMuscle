from sqlite3 import IntegrityError
from flask_login import current_user
from app import app
from flask import render_template, request, redirect, url_for, jsonify, session, flash
import secrets
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import Usuario, Treino, Progresso, Mensagem, Conversa, ChamadoSuporte, MensagemSuporte
from datetime import datetime, timedelta
from db import db
from sqlalchemy import desc, text
from sqlalchemy.exc import SQLAlchemyError

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

def buscar_usuario_por_key(key):
    """NOVA função - busca segura que SEMPRE retorna objeto Usuario"""
    print(f"🔍 Buscando usuário com key: {key}")
    
    if not key or key == 'None':
        print("❌ Key inválida")
        return None
    
    try:
        # Busca DIRETAMENTE no banco
        usuario = Usuario.query.filter_by(key=key).first()
        
        if usuario:
            print(f"✅ Usuário encontrado: {usuario.nome} (objeto)")
            
            # Atualiza último acesso se a coluna existir
            try:
                if hasattr(usuario, 'ultimo_acesso'):
                    from datetime import datetime
                    usuario.ultimo_acesso = datetime.utcnow()
                    db.session.commit()
                    print("🕒 Último acesso atualizado")
            except Exception as e:
                print(f"⚠️  Não foi possível atualizar último acesso: {e}")
                
            return usuario
        else:
            print("❌ Nenhum usuário encontrado")
            return None
            
    except Exception as e:
        print(f"❌ Erro na busca: {e}")
        return None

@app.route("/perfil/<key>", methods=['GET', 'POST'])
def perfil(key):
    user = buscar_usuario_por_key(key)
    if not user:
        return "Usuário não encontrado", 404
    return render_template("perfil.html", key=key, user=user)

@app.route("/suporte/<key>")
def suporte(key):
    print(f"Tentando acessar suporte com key: {key}")  # Debug
    
    user = buscar_usuario_por_key(key)
    
    # DEBUG: Verificar o que a função retorna
    print(f"Resultado de buscar_usuario_por_key: {user}")
    
    if user is None:
        print("USUÁRIO NÃO ENCONTRADO! Redirecionando para login...")
        return redirect(url_for('login'))
    
    print(f"Usuário encontrado: {user.nome} (ID: {user.id})")  # Debug
    
    # Verificar se existe chamado ativo (AGORA COM SEGURANÇA)
    try:
        chamado_ativo = ChamadoSuporte.query.filter_by(
            usuario_id=user.id, 
            status='aberto'
        ).first()
        
        print(f"Chamado ativo encontrado: {chamado_ativo}")  # Debug
        
    except Exception as e:
        print(f"Erro ao buscar chamado ativo: {e}")
        chamado_ativo = None
    
    return render_template("suporte.html", key=key, user=user, chamado_ativo=chamado_ativo)

@app.route('/debug-users')
def debug_users():
    """Rota para debug - mostra todos os usuários e suas keys"""
    try:
        usuarios = Usuario.query.all()
        debug_info = []
        
        for usuario in usuarios:
            debug_info.append({
                'id': usuario.id,
                'nome': usuario.nome,
                'email': usuario.email,
                'key': usuario.key,
                'tipo': usuario.tipo,
                'ultimo_acesso': usuario.ultimo_acesso.isoformat() if usuario.ultimo_acesso else 'Nunca'
            })
        
        return jsonify({
            'total_usuarios': len(debug_info),
            'usuarios': debug_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/criar-chamado', methods=['POST'])
def criar_chamado():
    data = request.get_json()
    key = data.get('key')
    tipo = data.get('tipo')
    
    user = buscar_usuario_por_key(key)
    if not user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado'})
    
    # Verificar se já existe chamado aberto
    chamado_existente = ChamadoSuporte.query.filter_by(
        usuario_id=user.id, 
        status='aberto'
    ).first()
    
    if chamado_existente:
        return jsonify({'success': False, 'message': 'Já existe um chamado em aberto'})
    
    # Encontrar profissional disponível
    profissional = encontrar_profissional_disponivel(tipo)
    
    # Criar novo chamado
    novo_chamado = ChamadoSuporte(
        usuario_id=user.id,
        profissional_id=profissional.id if profissional else None,
        tipo=tipo,
        status='aberto'
    )
    
    db.session.add(novo_chamado)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'chamado_id': novo_chamado.id,
        'message': 'Chamado criado com sucesso'
    })

def encontrar_profissional_disponivel(tipo):
    # Primeiro tenta encontrar profissionais online
    profissionais_online = Usuario.query.filter_by(
        tipo='profissional',
        online=True
    ).all()
    
    if profissionais_online:
        # Retorna o primeiro profissional online
        return profissionais_online[0]
    
    # Se não há online, busca o com acesso mais recente
    profissional_recente = Usuario.query.filter_by(
        tipo='profissional'
    ).order_by(desc(Usuario.ultimo_acesso)).first()
    
    return profissional_recente

@app.route('/chat-suporte/<int:chamado_id>')
def chat_suporte(chamado_id):
    key = request.args.get('key')
    user = buscar_usuario_por_key(key)
    chamado = ChamadoSuporte.query.get_or_404(chamado_id)
    
    # Verificar se o usuário tem acesso a este chamado
    if chamado.usuario_id != user.id and chamado.profissional_id != user.id:
        return "Acesso não autorizado", 403
    
    mensagens = MensagemSuporte.query.filter_by(chamado_id=chamado_id).order_by(MensagemSuporte.data_envio).all()
    
    return render_template('chat_suporte.html', 
                         key=key, 
                         user=user, 
                         chamado=chamado, 
                         mensagens=mensagens)

@app.route('/api/enviar-mensagem-suporte', methods=['POST'])
def enviar_mensagem_suporte():
    data = request.get_json()
    key = data.get('key')
    chamado_id = data.get('chamado_id')
    mensagem = data.get('mensagem')
    
    user = buscar_usuario_por_key(key)
    chamado = ChamadoSuporte.query.get(chamado_id)
    
    if not chamado or chamado.status == 'fechado':
        return jsonify({'success': False, 'message': 'Chamado não encontrado ou fechado'})
    
    # Verificar permissão
    if user.id not in [chamado.usuario_id, chamado.profissional_id]:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    nova_mensagem = MensagemSuporte(
        chamado_id=chamado_id,
        remetente_id=user.id,
        mensagem=mensagem
    )
    
    db.session.add(nova_mensagem)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/fechar-chamado', methods=['POST'])
def fechar_chamado():
    data = request.get_json()
    key = data.get('key')
    chamado_id = data.get('chamado_id')
    
    user = buscar_usuario_por_key(key)
    chamado = ChamadoSuporte.query.get(chamado_id)
    
    # Apenas profissionais podem fechar chamados
    if user.tipo != 'profissional' or user.id != chamado.profissional_id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    chamado.status = 'fechado'
    chamado.data_fechamento = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True})

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

@app.route('/api/estatisticas')
@app.route('/api/estatisticas/<key>')
def api_estatisticas(key=None):
    if key:
        usuario = Usuario.query.filter_by(key=key).first()
        if not usuario or usuario.tipo != "profissional":
            return jsonify({'error': 'Acesso não autorizado'}), 403
    
    total_alunos = Usuario.query.filter_by(tipo='usuario').count()
    treinos_ativos = Treino.query.filter_by(status='ativo').count()
    alunos_com_treino = Usuario.query.filter_by(tipo='usuario').join(Treino).filter(Treino.status == 'ativo').count()
    alunos_inativos = total_alunos - alunos_com_treino
    
    return jsonify({
        'total_alunos': total_alunos,
        'alunos_ativos': alunos_com_treino,
        'treinos_ativos': treinos_ativos,
        'alunos_inativos': alunos_inativos,
        'chats_ativos': 5
    })

@app.route('/api/alunos/<key>')
def api_alunos(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario or usuario.tipo != "profissional":
        return jsonify({'error': 'Acesso não autorizado'}), 403
        
    alunos = Usuario.query.filter_by(tipo='usuario').all()
    
    alunos_data = []
    for aluno in alunos:
        # Buscar treino ativo do aluno
        treino_ativo = Treino.query.filter_by(aluno_id=aluno.id, status='ativo').first()
        
        # Buscar progresso
        progresso = Progresso.query.filter_by(aluno_id=aluno.id).order_by(Progresso.data_registro.desc()).first()
        
        # Evitar erro se treino_ativo for None
        treino_nome = treino_ativo.nome if treino_ativo else 'Sem treino'
        treino_tipo = treino_ativo.tipo if treino_ativo else '-'
        status = 'Ativo' if treino_ativo else 'Inativo'
        
        alunos_data.append({
            'id': aluno.id,
            'nome': aluno.nome,
            'treino': treino_nome,
            'nivel': treino_tipo,
            'progresso': progresso.porcentagem if progresso else 0,
            'status': status,
            'ultimo_acesso': 'Hoje'  # Implementar lógica real
        })
    
    return jsonify(alunos_data)

@app.route("/suporte_profissional/<key>")
def suporte_pro(key):
    """Página do suporte profissional estilo WhatsApp"""
    user = Usuario.query.filter_by(key=key).first()
    
    if not user or user.tipo != 'profissional':
        return redirect(url_for('login'))
    
    return render_template("suporte_profissional.html", key=key, user=user)

@app.route('/api/chamados-profissional/<key>')
def api_chamados_profissional(key):
    """Retorna os chamados do profissional para o template WhatsApp"""
    user = Usuario.query.filter_by(key=key).first()
    
    if not user or user.tipo != 'profissional':
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    # Buscar chamados do profissional
    chamados = ChamadoSuporte.query.filter_by(profissional_id=user.id)\
        .order_by(ChamadoSuporte.data_abertura.desc())\
        .all()
    
    chamados_data = []
    for chamado in chamados:
        # Buscar última mensagem
        ultima_mensagem = MensagemSuporte.query.filter_by(chamado_id=chamado.id)\
            .order_by(MensagemSuporte.data_envio.desc())\
            .first()
        
        # Contar mensagens não lidas
        mensagens_nao_lidas = MensagemSuporte.query.filter_by(
            chamado_id=chamado.id, 
            lida=False
        ).filter(MensagemSuporte.remetente_id != user.id).count()
        
        # Buscar todas as mensagens do chat
        mensagens = MensagemSuporte.query.filter_by(chamado_id=chamado.id)\
            .order_by(MensagemSuporte.data_envio)\
            .all()
        
        chamados_data.append({
            'id': chamado.id,
            'usuario': {
                'nome': chamado.usuario.nome,
                'telefone': chamado.usuario.telefone
            },
            'status': chamado.status,
            'ultima_mensagem': ultima_mensagem.mensagem if ultima_mensagem else 'Nenhuma mensagem',
            'data_ultima_mensagem': ultima_mensagem.data_envio.strftime('%H:%M') if ultima_mensagem else chamado.data_abertura.strftime('%H:%M'),
            'mensagens_nao_lidas': mensagens_nao_lidas,
            'mensagens': [
                {
                    'conteudo': msg.mensagem,
                    'remetente_id': msg.remetente_id,
                    'data_envio': msg.data_envio.strftime('%H:%M')
                } for msg in mensagens
            ]
        })
    
    return jsonify({
        'success': True,
        'chamados': chamados_data
    })

@app.route('/api/enviar-mensagem-profissional', methods=['POST'])
def enviar_mensagem_profissional():
    """Envia mensagem no chat profissional"""
    data = request.get_json()
    key = data.get('key')
    chamado_id = data.get('chamado_id')
    mensagem = data.get('mensagem')
    
    user = Usuario.query.filter_by(key=key).first()
    chamado = ChamadoSuporte.query.get(chamado_id)
    
    if not user or not chamado:
        return jsonify({'success': False, 'message': 'Usuário ou chamado não encontrado'})
    
    if chamado.status == 'fechado':
        return jsonify({'success': False, 'message': 'Este chamado está fechado'})
    
    # Verificar se o profissional tem acesso a este chamado
    if chamado.profissional_id != user.id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    # Criar mensagem
    nova_mensagem = MensagemSuporte(
        chamado_id=chamado_id,
        remetente_id=user.id,
        mensagem=mensagem
    )
    
    db.session.add(nova_mensagem)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Mensagem enviada'})

@app.route('/api/fechar-chamado-profissional', methods=['POST'])
def fechar_chamado_profissional():
    """Fecha o chamado (apenas profissional)"""
    data = request.get_json()
    key = data.get('key')
    chamado_id = data.get('chamado_id')
    
    user = Usuario.query.filter_by(key=key).first()
    chamado = ChamadoSuporte.query.get(chamado_id)
    
    if not user or not chamado:
        return jsonify({'success': False, 'message': 'Usuário ou chamado não encontrado'})
    
    # Apenas profissionais podem fechar chamados
    if user.tipo != 'profissional' or user.id != chamado.profissional_id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    if chamado.status == 'fechado':
        return jsonify({'success': False, 'message': 'Chamado já está fechado'})
    
    # Fechar chamado
    chamado.status = 'fechado'
    chamado.data_fechamento = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Chamado fechado com sucesso'})

@app.route('/api/marcar-mensagens-lidas', methods=['POST'])
def marcar_mensagens_lidas():
    """Marca as mensagens de um chamado como lidas"""
    data = request.get_json()
    key = data.get('key')
    chamado_id = data.get('chamado_id')
    
    user = Usuario.query.filter_by(key=key).first()
    if not user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado'})
    
    # Marcar mensagens não lidas como lidas
    mensagens_nao_lidas = MensagemSuporte.query.filter_by(
        chamado_id=chamado_id, 
        lida=False
    ).filter(MensagemSuporte.remetente_id != user.id).all()
    
    for mensagem in mensagens_nao_lidas:
        mensagem.lida = True
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Mensagens marcadas como lidas'})

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
        
        profissional = current_user
        destinatario_id = conversa.usuario_id
    
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
    
    conversa.data_ultima_mensagem = datetime.utcnow()
    
    db.session.add(mensagem)
    db.session.commit()
    
    return jsonify({'success': True, 'mensagem_id': mensagem.id})

# ROTAS DE CORREÇÃO DO BANCO - COLOCAR JUNTAS

@app.route('/debug-missing-columns')
def debug_missing_columns():
    """Mostra quais colunas estão faltando no banco"""
    try:
        result = db.session.execute(text("PRAGMA table_info(usuarios)"))
        existing_columns = [row[1] for row in result]
        
        expected_columns = ['id', 'key', 'nome', 'email', 'senha_hash', 'telefone', 
                          'tipo', 'data_criacao', 'online', 'ultimo_acesso']
        
        missing_columns = [col for col in expected_columns if col not in existing_columns]
        
        return jsonify({
            'existing_columns': existing_columns,
            'missing_columns': missing_columns
        })
    except Exception as e:
        return f"Erro: {str(e)}"

@app.route('/fix-all-missing-columns')
def fix_all_missing_columns():
    """Adiciona TODAS as colunas faltantes de uma vez - CORRIGIDO para SQLite"""
    try:
        result = db.session.execute(text("PRAGMA table_info(usuarios)"))
        existing_columns = [row[1] for row in result]
        
        columns_to_add = []
        
        if 'online' not in existing_columns:
            columns_to_add.append("ADD COLUMN online BOOLEAN DEFAULT 0")
        
        if 'ultimo_acesso' not in existing_columns:
            # SQLite não aceita CURRENT_TIMESTAMP em ALTER TABLE, usamos um valor fixo
            columns_to_add.append("ADD COLUMN ultimo_acesso DATETIME")
        
        if not columns_to_add:
            return "Todas as colunas já existem!"
        
        for column_sql in columns_to_add:
            db.session.execute(text(f"ALTER TABLE usuarios {column_sql}"))
        
        db.session.commit()
        
        # AGORA atualiza os dados com o valor correto
        if 'ultimo_acesso' in [col.split(' ')[2] for col in columns_to_add]:
            from datetime import datetime
            # Atualiza todos os registros com a data atual
            db.session.execute(text("UPDATE usuarios SET ultimo_acesso = :now WHERE ultimo_acesso IS NULL"), 
                            {'now': datetime.utcnow()})
            db.session.commit()
        
        return f"✅ Colunas adicionadas: {', '.join(columns_to_add)}"
    except Exception as e:
        db.session.rollback()
        return f"❌ Erro: {str(e)}"

@app.route('/migrar-ultimo-acesso')
def migrar_ultimo_acesso():
    """Migra dados existentes para ter ultimo_acesso"""
    try:
        usuarios = Usuario.query.all()
        for usuario in usuarios:
            if not hasattr(usuario, 'ultimo_acesso') or usuario.ultimo_acesso is None:
                usuario.ultimo_acesso = usuario.data_criacao
        db.session.commit()
        return "Migração concluída com sucesso"
    except Exception as e:
        return f"Erro na migração: {str(e)}"

@app.route('/emergency-fix-database')
def emergency_fix_database():
    """Solução de emergência para problemas no banco"""
    try:
        result1 = "Colunas: "
        try:
            db.session.execute(text("ALTER TABLE usuarios ADD COLUMN online BOOLEAN DEFAULT 0"))
            result1 += "online OK "
        except:
            result1 += "online já existe "
        
        try:
            db.session.execute(text("ALTER TABLE usuarios ADD COLUMN ultimo_acesso DATETIME DEFAULT CURRENT_TIMESTAMP"))
            result1 += "ultimo_acesso OK "
        except:
            result1 += "ultimo_acesso já existe "
        
        db.session.commit()
        
        result2 = "Dados: "
        try:
            db.session.execute(text("UPDATE usuarios SET ultimo_acesso = data_criacao WHERE ultimo_acesso IS NULL"))
            db.session.commit()
            result2 += "migrados OK"
        except Exception as e:
            result2 += f"erro: {e}"
        
        return f"✅ Correção aplicada!<br>{result1}<br>{result2}"
    except Exception as e:
        return f"❌ Erro: {str(e)}"
        
    except Exception as e:
        db.session.rollback()
        return f"Erro: {str(e)}"
    
@app.route('/debug-routes')
def debug_routes():
    """Mostra todas as rotas disponíveis no sistema"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify(routes)

def get_usuario_by_id(usuario_id):
    """Busca usuário por ID de forma segura"""
    try:
        return Usuario.query.get(usuario_id)
    except:
        return None


@app.context_processor
def utility_processor():
    return dict(get_usuario_by_id=get_usuario_by_id)

@app.route('/admin/fechar-chamado/<int:chamado_id>', methods=['POST'])
def fechar_chamado_admin(chamado_id):
    """Força o fechamento de um chamado (admin)"""
    try:
        chamado = ChamadoSuporte.query.get(chamado_id)
        
        if not chamado:
            return jsonify({'success': False, 'message': 'Chamado não encontrado'})
        
        if chamado.status == 'fechado':
            return jsonify({'success': False, 'message': 'Chamado já está fechado'})
        
        # Forçar fechamento
        chamado.status = 'fechado'
        chamado.data_fechamento = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Chamado #{chamado_id} fechado com sucesso',
            'chamado': {
                'id': chamado.id,
                'usuario': chamado.usuario.nome,
                'profissional': chamado.profissional.nome if chamado.profissional else 'N/A',
                'tipo': chamado.tipo,
                'data_abertura': chamado.data_abertura.strftime('%d/%m/%Y %H:%M'),
                'data_fechamento': chamado.data_fechamento.strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao fechar chamado: {str(e)}'})
    
@app.route('/admin/chamados')
def admin_chamados():
    """Página administrativa para gerenciar chamados"""
    with app.app_context():
        # Chamados abertos
        chamados_abertos = ChamadoSuporte.query.filter_by(status='aberto').all()
        
        # Chamados fechados (últimos 10)
        chamados_fechados = ChamadoSuporte.query.filter_by(status='fechado')\
            .order_by(ChamadoSuporte.data_fechamento.desc())\
            .limit(10)\
            .all()
        
        html = """
        <html>
            <head>
                <title>Gerenciar Chamados</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .section { margin-bottom: 40px; }
                    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #f2f2f2; }
                    .aberto { background-color: #fff3cd; }
                    .fechado { background-color: #d4edda; }
                    .btn { padding: 5px 10px; text-decoration: none; border-radius: 3px; border: none; cursor: pointer; }
                    .btn-danger { background: #d63031; color: white; }
                    .btn-success { background: #28a745; color: white; }
                    .btn-warning { background: #ffc107; color: black; }
                </style>
                <script>
                    function fecharChamado(chamadoId) {
                        if (confirm('Tem certeza que deseja fechar este chamado?')) {
                            fetch('/admin/fechar-chamado/' + chamadoId, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' }
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    alert(data.message);
                                    location.reload();
                                } else {
                                    alert('Erro: ' + data.message);
                                }
                            });
                        }
                    }
                </script>
            </head>
            <body>
                <h1>🎯 Gerenciar Chamados de Suporte</h1>
        """
        
        # Chamados Abertos
        html += f"""
                <div class="section">
                    <h2>📋 Chamados Abertos ({len(chamados_abertos)})</h2>
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Usuário</th>
                            <th>Profissional</th>
                            <th>Tipo</th>
                            <th>Data Abertura</th>
                            <th>Ações</th>
                        </tr>
        """
        
        for chamado in chamados_abertos:
            html += f"""
                        <tr class="aberto">
                            <td>{chamado.id}</td>
                            <td>{chamado.usuario.nome}</td>
                            <td>{chamado.profissional.nome if chamado.profissional else 'N/A'}</td>
                            <td>{chamado.tipo}</td>
                            <td>{chamado.data_abertura.strftime('%d/%m/%Y %H:%M')}</td>
                            <td>
                                <button class="btn btn-danger" onclick="fecharChamado({chamado.id})">
                                    🔒 Fechar
                                </button>
                                <a href="/chat-suporte/{chamado.id}?key=admin" class="btn btn-warning" target="_blank">
                                    💬 Ver Chat
                                </a>
                            </td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
        """
        
        # Chamados Fechados
        html += f"""
                <div class="section">
                    <h2>📁 Chamados Fechados (Últimos 10)</h2>
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Usuário</th>
                            <th>Profissional</th>
                            <th>Tipo</th>
                            <th>Data Abertura</th>
                            <th>Data Fechamento</th>
                        </tr>
        """
        
        for chamado in chamados_fechados:
            html += f"""
                        <tr class="fechado">
                            <td>{chamado.id}</td>
                            <td>{chamado.usuario.nome}</td>
                            <td>{chamado.profissional.nome if chamado.profissional else 'N/A'}</td>
                            <td>{chamado.tipo}</td>
                            <td>{chamado.data_abertura.strftime('%d/%m/%Y %H:%M')}</td>
                            <td>{chamado.data_fechamento.strftime('%d/%m/%Y %H:%M')}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
            </body>
        </html>
        """
        
        return html
    
@app.route('/api/criar-chamado-profissional', methods=['POST'])
def criar_chamado_profissional():
    """Cria chamado específico para profissional"""
    data = request.get_json()
    key = data.get('key')
    
    user = Usuario.query.filter_by(key=key).first()
    if not user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado'})
    
    # Verificar se já existe chamado aberto
    chamado_existente = ChamadoSuporte.query.filter_by(
        usuario_id=user.id, 
        status='aberto',
        tipo='profissional'
    ).first()
    
    if chamado_existente:
        return jsonify({
            'success': True, 
            'chamado_id': chamado_existente.id,
            'redirect': True
        })
    
    # Encontrar profissional específico
    profissional = Usuario.query.filter_by(tipo='profissional').first()
    
    if not profissional:
        return jsonify({'success': False, 'message': 'Nenhum profissional disponível'})
    
    # Criar novo chamado
    novo_chamado = ChamadoSuporte(
        usuario_id=user.id,
        profissional_id=profissional.id,
        tipo='profissional',
        status='aberto'
    )
    
    db.session.add(novo_chamado)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'chamado_id': novo_chamado.id,
        'profissional_nome': profissional.nome,
        'redirect': True
    })

@app.route('/chat-profissional/<int:chamado_id>')
def chat_profissional(chamado_id):
    """Página do chat com profissional"""
    key = request.args.get('key')
    user = Usuario.query.filter_by(key=key).first()
    
    if not user:
        return redirect(url_for('login'))
    
    chamado = ChamadoSuporte.query.get_or_404(chamado_id)
    
    # Verificar se o usuário tem acesso a este chamado
    if chamado.usuario_id != user.id and chamado.profissional_id != user.id:
        return "Acesso não autorizado", 403
    
    # Carregar mensagens
    mensagens = MensagemSuporte.query.filter_by(chamado_id=chamado_id)\
        .order_by(MensagemSuporte.data_envio)\
        .all()
    
    return render_template('chat_profissional.html', 
                         key=key, 
                         user=user, 
                         chamado=chamado, 
                         mensagens=mensagens)



@app.route('/api/carregar-mensagens/<int:chamado_id>')
def carregar_mensagens(chamado_id):
    """Carrega mensagens do chat (para atualização em tempo real)"""
    key = request.args.get('key')
    user = Usuario.query.filter_by(key=key).first()
    
    if not user:
        return jsonify({'success': False})
    
    # Verificar último ID de mensagem do cliente (para implementar depois)
    # Por enquanto, sempre retorna que há novas mensagens
    
    return jsonify({
        'success': True,
        'novas_mensagens': True
    })