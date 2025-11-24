from flask import Blueprint, render_template, request, jsonify
from models import Usuario, ChamadoSuporte, MensagemSuporte, Mensagem
from db import db
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

def get_usuario_by_id(usuario_id):
    """Busca usuário por ID de forma segura"""
    try:
        return Usuario.query.get(usuario_id)
    except:
        return None
    
@chat_bp.context_processor
def utility_processor():
    return dict(get_usuario_by_id=get_usuario_by_id)

def buscar_usuario_por_key(key):
    return Usuario.query.filter_by(key=key).first()

@chat_bp.route('/chat-suporte/<int:chamado_id>')
def chat_suporte(chamado_id):
    key = request.args.get('key')
    user = buscar_usuario_por_key(key)
    chamado = ChamadoSuporte.query.get_or_404(chamado_id)
    
    if chamado.usuario_id != user.id and chamado.profissional_id != user.id:
        return "Acesso não autorizado", 403
    
    mensagens = MensagemSuporte.query.filter_by(chamado_id=chamado_id).order_by(MensagemSuporte.data_envio).all()
    
    return render_template('chat_suporte.html', 
                         key=key, 
                         user=user, 
                         chamado=chamado, 
                         mensagens=mensagens)

@chat_bp.route('/api/enviar-mensagem-suporte', methods=['POST'])
def enviar_mensagem_suporte():
    data = request.get_json()
    key = data.get('key')
    chamado_id = data.get('chamado_id')
    mensagem = data.get('mensagem')
    
    user = buscar_usuario_por_key(key)
    chamado = ChamadoSuporte.query.get(chamado_id)
    
    if not chamado or chamado.status == 'fechado':
        return jsonify({'success': False, 'message': 'Chamado não encontrado ou fechado'})
    
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

@chat_bp.route('/api/fechar-chamado', methods=['POST'])
def fechar_chamado():
    data = request.get_json()
    key = data.get('key')
    chamado_id = data.get('chamado_id')
    
    user = buscar_usuario_por_key(key)
    chamado = ChamadoSuporte.query.get(chamado_id)
    
    if user.tipo != 'profissional' or user.id != chamado.profissional_id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'})
    
    chamado.status = 'fechado'
    chamado.data_fechamento = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True})

@chat_bp.route('/api/buscar-mensagens-suporte')
def buscar_mensagens_suporte():
    key = request.args.get('key')
    chamado_id = request.args.get('chamado_id')
    ultima_mensagem_id = request.args.get('ultima_mensagem_id', 0, type=int)
    
    # Verificar se o usuário está autenticado
    usuario = buscar_usuario_por_key(key)
    if not usuario:
        return jsonify({'success': False, 'message': 'Usuário não autenticado'})
    
    # Buscar mensagens do sistema de suporte com ID maior que ultima_mensagem_id
    novas_mensagens = MensagemSuporte.query.filter(
        MensagemSuporte.chamado_id == chamado_id,
        MensagemSuporte.id > ultima_mensagem_id
    ).order_by(MensagemSuporte.data_envio.asc()).all()
    
    # Converter para formato JSON
    mensagens_json = []
    for msg in novas_mensagens:
        mensagem_data = {
            'id': msg.id,
            'mensagem': msg.mensagem,
            'remetente_id': msg.remetente_id,
            'data_envio': msg.data_envio.isoformat(),
            'remetente_nome': msg.remetente.nome if msg.remetente else 'Profissional'
        }
        mensagens_json.append(mensagem_data)
    
    return jsonify({
        'success': True,
        'mensagens': mensagens_json
    })