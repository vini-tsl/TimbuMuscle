from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_login import current_user
from models import Usuario, ChamadoSuporte, MensagemSuporte, Conversa, Mensagem
from db import db
from datetime import datetime
from sqlalchemy import desc

suporte_bp = Blueprint('suporte', __name__)

def buscar_usuario_por_key(key):
    return Usuario.query.filter_by(key=key).first()

@suporte_bp.route("/suporte/<key>")
def suporte(key):
    user = buscar_usuario_por_key(key)
    
    if user is None:
        return redirect(url_for('auth.login'))
    
    chamado_ativo = ChamadoSuporte.query.filter_by(
        usuario_id=user.id, 
        status='aberto'
    ).first()
    
    return render_template("suporte.html", key=key, user=user, chamado_ativo=chamado_ativo)

@suporte_bp.route('/api/criar-chamado', methods=['POST'])
def criar_chamado():
    data = request.get_json()
    key = data.get('key')
    tipo = data.get('tipo')
    
    user = buscar_usuario_por_key(key)
    if not user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado'})
    
    chamado_existente = ChamadoSuporte.query.filter_by(
        usuario_id=user.id, 
        status='aberto'
    ).first()
    
    if chamado_existente:
        return jsonify({'success': False, 'message': 'Já existe um chamado em aberto'})
    
    profissional = encontrar_profissional_disponivel(tipo)
    
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
    profissionais_online = Usuario.query.filter_by(
        tipo='profissional',
        online=True
    ).all()
    
    if profissionais_online:
        return profissionais_online[0]
    
    profissional_recente = Usuario.query.filter_by(
        tipo='profissional'
    ).order_by(desc(Usuario.ultimo_acesso)).first()
    
    return profissional_recente

@suporte_bp.route("/suporte_profissional/<key>")
def suporte_pro(key):
    """Página do suporte profissional estilo WhatsApp"""
    user = Usuario.query.filter_by(key=key).first()
    
    if not user or user.tipo != 'profissional':
        return redirect(url_for('login'))
    
    return render_template("suporte_profissional.html", key=key, user=user)

@suporte_bp.route('/api/chamados-profissional/<key>')
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

@suporte_bp.route('/api/enviar-mensagem-profissional', methods=['POST'])
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

@suporte_bp.route('/api/fechar-chamado-profissional', methods=['POST'])
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

@suporte_bp.route('/api/marcar-mensagens-lidas', methods=['POST'])
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

@suporte_bp.route('/api/conversas/<key>')
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
@suporte_bp.route('/api/mensagens/<key>/<int:conversa_id>')
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
@suporte_bp.route('/api/enviar/<key>', methods=['POST'])
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