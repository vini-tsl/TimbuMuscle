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
    
    # Relacionamentos
    treinos = db.relationship('Treino', backref='aluno', lazy=True)
    progressos = db.relationship('Progresso', backref='aluno', lazy=True)
    

class Treino(db.Model):
    __tablename__ = 'treinos'
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50))  # Iniciante, Intermediário, Avançado
    descricao = db.Column(db.Text)
    status = db.Column(db.String(20), default='ativo')  # ativo, inativo, completo
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    data_previsao = db.Column(db.DateTime)
    
    exercicios = db.relationship('Exercicio', backref='treino', lazy=True)

class Exercicio(db.Model):
    __tablename__ = 'exercicios'
    
    id = db.Column(db.Integer, primary_key=True)
    treino_id = db.Column(db.Integer, db.ForeignKey('treinos.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    series = db.Column(db.Integer)
    repeticoes = db.Column(db.String(50))
    descricao = db.Column(db.Text)

class Progresso(db.Model):
    __tablename__ = 'progressos'
    
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    treino_id = db.Column(db.Integer, db.ForeignKey('treinos.id'), nullable=False)
    porcentagem = db.Column(db.Integer, default=0)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)