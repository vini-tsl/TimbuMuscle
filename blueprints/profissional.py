from flask import Blueprint, render_template, jsonify, redirect, url_for, flash
from models import Usuario, Treino, Progresso
from sqlalchemy import desc

profissional_bp = Blueprint('profissional', __name__)

@profissional_bp.route("/profissional/<key>")
def profissional(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario or usuario.tipo != "profissional":
        flash('Acesso restrito a profissionais', 'danger')
        return redirect(url_for('auth.login'))
    
    alunos = Usuario.query.filter_by(tipo='usuario').all()
    alunos_ativos = Usuario.query.filter_by(tipo='usuario').count()
    treinos_ativos = Treino.query.filter_by(status='ativo').count()
    
    return render_template('profissional.html',
                          key=key, 
                          user=usuario,
                          alunos=alunos,
                          alunos_ativos=alunos_ativos,
                          treinos_ativos=treinos_ativos)

@profissional_bp.route('/api/estatisticas')
@profissional_bp.route('/api/estatisticas/<key>')
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

@profissional_bp.route('/api/alunos/<key>')
def api_alunos(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario or usuario.tipo != "profissional":
        return jsonify({'error': 'Acesso não autorizado'}), 403
        
    alunos = Usuario.query.filter_by(tipo='usuario').all()
    
    alunos_data = []
    for aluno in alunos:
        treino_ativo = Treino.query.filter_by(aluno_id=aluno.id, status='ativo').first()
        progresso = Progresso.query.filter_by(aluno_id=aluno.id).order_by(Progresso.data_registro.desc()).first()
        
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
            'ultimo_acesso': 'Hoje'
        })
    
    return jsonify(alunos_data)