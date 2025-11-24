from db import db
from datetime import datetime

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    telefone = db.Column(db.String(20))
    tipo = db.Column(db.String(20), default='usuario')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    online = db.Column(db.Boolean, default=False)
    ultimo_acesso = db.Column(db.DateTime, default=datetime.utcnow)
    
     # Informações do formulário para IA
    idade = db.Column(db.Integer, nullable=True)
    peso = db.Column(db.Float, nullable=True)
    altura = db.Column(db.Float, nullable=True)
    objetivo = db.Column(db.String(50), nullable=True)
    nivel_experiencia = db.Column(db.String(20), nullable=True)
    restricoes_medicas = db.Column(db.Text, nullable=True)
    dias_treino_semana = db.Column(db.Integer, nullable=True)
    tempo_treino_dia = db.Column(db.Integer, nullable=True)
    
    # Controle de formulário
    formulario_preenchido = db.Column(db.Boolean, default=False)
    data_formulario = db.Column(db.DateTime, nullable=True)

    # Relacionamentos
    treinos = db.relationship('Treino', backref='aluno', lazy=True)
    progressos = db.relationship('Progresso', backref='aluno', lazy=True)
    historico_treinos = db.relationship('HistoricoTreino', backref='aluno', lazy=True)
    mensagens_enviadas = db.relationship('Mensagem', foreign_keys='Mensagem.remetente_id', backref='remetente', lazy=True)
    mensagens_recebidas = db.relationship('Mensagem', foreign_keys='Mensagem.destinatario_id', backref='destinatario', lazy=True)
    conversas = db.relationship('Conversa', foreign_keys='Conversa.usuario_id', backref='usuario', lazy=True)

class HistoricoTreino(db.Model):
    __tablename__ = 'historico_treinos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    treino_id = db.Column(db.Integer, db.ForeignKey('treinos.id'), nullable=False)
    data_execucao = db.Column(db.DateTime, default=datetime.utcnow)
    duracao_minutos = db.Column(db.Integer)  # Tempo que levou para completar
    dificuldade_percebida = db.Column(db.String(20))  # Muito Fácil, Fácil, Moderado, Difícil, Muito Difícil
    feedback_usuario = db.Column(db.Text)  # Feedback opcional do usuário
    ajuste_recomendado = db.Column(db.String(50))  # Aumentar, Manter, Reduzir

class CatalogoExercicio(db.Model):
    __tablename__ = 'catalogo_exercicios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    grupo_muscular = db.Column(db.String(50), nullable=False)
    equipamento = db.Column(db.String(50), nullable=False)
    nivel_dificuldade = db.Column(db.String(20), nullable=False)  # Iniciante, Intermediário, Avançado
    instrucoes = db.Column(db.Text)
    video_url = db.Column(db.String(255))
    imagem_url = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)


class Treino(db.Model):
    __tablename__ = 'treinos'
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50))  # A, B, C ou Superior, Inferior, etc.
    descricao = db.Column(db.Text)
    status = db.Column(db.String(20), default='ativo')  # ativo, inativo, completo
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    data_previsao = db.Column(db.DateTime)
    dia_semana = db.Column(db.String(20))  # Segunda, Terça, etc.
    ordem = db.Column(db.Integer)  # Ordem dos treinos na semana
    
    exercicios = db.relationship('ExercicioTreino', backref='treino', lazy=True)

class ExercicioTreino(db.Model):
    __tablename__ = 'exercicios_treino'
    
    id = db.Column(db.Integer, primary_key=True)
    treino_id = db.Column(db.Integer, db.ForeignKey('treinos.id'), nullable=False)
    catalogo_exercicio_id = db.Column(db.Integer, db.ForeignKey('catalogo_exercicios.id'), nullable=False)
    series = db.Column(db.Integer)
    repeticoes = db.Column(db.String(50))
    descanso = db.Column(db.String(20))  # 60s, 90s, etc.
    ordem = db.Column(db.Integer)  # Ordem no treino
    
    # Relacionamento com catálogo
    catalogo = db.relationship('CatalogoExercicio', backref='treinos_exercicio')

class Progresso(db.Model):
    __tablename__ = 'progressos'
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    treino_id = db.Column(db.Integer, db.ForeignKey('treinos.id'), nullable=False)
    porcentagem = db.Column(db.Integer, default=0)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)

class Conversa(db.Model):
    __tablename__ = 'conversas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    tipo_suporte = db.Column(db.String(20), nullable=False)  # 'geral', 'personal', 'nutricionista'
    status = db.Column(db.String(20), default='aberta')  # 'aberta', 'fechada', 'em_andamento'
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_ultima_mensagem = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    mensagens = db.relationship('Mensagem', backref='conversa', lazy=True)

class Mensagem(db.Model):
    __tablename__ = 'mensagens'
    
    id = db.Column(db.Integer, primary_key=True)
    conversa_id = db.Column(db.Integer, db.ForeignKey('conversas.id'), nullable=False)
    remetente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    lida = db.Column(db.Boolean, default=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices para melhor performance em consultas
    __table_args__ = (
        db.Index('ix_mensagens_conversa_id', 'conversa_id'),
        db.Index('ix_mensagens_remetente_id', 'remetente_id'),
        db.Index('ix_mensagens_destinatario_id', 'destinatario_id'),
    )

class ChamadoSuporte(db.Model):
    __tablename__ = 'chamado_suporte'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    tipo = db.Column(db.String(20), nullable=False, default='profissional')
    status = db.Column(db.String(20), default='aberto')
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    data_fechamento = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='chamados_usuario')
    profissional = db.relationship('Usuario', foreign_keys=[profissional_id], backref='chamados_profissional')
    mensagens = db.relationship('MensagemSuporte', backref='chamado', lazy=True, order_by='MensagemSuporte.data_envio')

class MensagemSuporte(db.Model):
    __tablename__ = 'mensagem_suporte'
    
    id = db.Column(db.Integer, primary_key=True)
    chamado_id = db.Column(db.Integer, db.ForeignKey('chamado_suporte.id'), nullable=False)
    remetente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    lida = db.Column(db.Boolean, default=False)
    
    # Relacionamento
    remetente = db.relationship('Usuario', backref='mensagens_suporte')