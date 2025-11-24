from flask import Blueprint, render_template, request, jsonify, session
from db import db
from models import Usuario, Treino, ExercicioTreino, CatalogoExercicio, Progresso
import json
from datetime import datetime

treinos_bp = Blueprint('treinos', __name__)

@treinos_bp.route('/treinos/<key>')
def mostrar_treinos(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario:
        return "Usuário não encontrado", 404
    
    # Buscar treinos do usuário
    treinos = Treino.query.filter_by(aluno_id=usuario.id).order_by(Treino.ordem).all()
    
    # Buscar progresso
    progressos = {}
    for treino in treinos:
        progresso = Progresso.query.filter_by(aluno_id=usuario.id, treino_id=treino.id).first()
        progressos[treino.id] = progresso.porcentagem if progresso else 0
    
    return render_template('treinos.html', 
                         user=usuario, 
                         key=key, 
                         treinos=treinos, 
                         progressos=progressos)

@treinos_bp.route('/api/salvar-formulario-ia', methods=['POST'])
def salvar_formulario_ia():
    try:
        data = request.get_json()
        key = data.get('key')
        
        usuario = Usuario.query.filter_by(key=key).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
        
        # Atualizar informações do usuário
        usuario.idade = data.get('idade')
        usuario.peso = data.get('peso')
        usuario.altura = data.get('altura')
        usuario.objetivo = data.get('objetivo')
        usuario.nivel_experiencia = data.get('nivel_experiencia')
        usuario.restricoes_medicas = data.get('restricoes_medicas')
        usuario.dias_treino_semana = data.get('dias_treino_semana')
        usuario.tempo_treino_dia = data.get('tempo_treino_dia')
        
        db.session.commit()
        
        # Gerar treinos com IA
        treinos_gerados = gerar_treinos_ia(usuario)
        
        return jsonify({
            'success': True, 
            'message': 'Formulário salvo e treinos gerados com sucesso!',
            'treinos_gerados': len(treinos_gerados)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def gerar_treinos_ia(usuario):
    """Gera treinos personalizados baseado nas informações do usuário usando o catálogo"""
    
    # Limpar treinos existentes
    Treino.query.filter_by(aluno_id=usuario.id).delete()
    ExercicioTreino.query.filter(ExercicioTreino.treino_id.in_(
        db.session.query(Treino.id).filter_by(aluno_id=usuario.id)
    )).delete(synchronize_session=False)
    
    # Definir estrutura de treino baseado no objetivo
    objetivo = usuario.objetivo
    nivel = usuario.nivel_experiencia
    dias_semana = usuario.dias_treino_semana
    
    # Estruturas de treino baseadas no catálogo disponível
    estruturas_treino = {
        'hipertrofia': {
            2: ['Full Body A', 'Full Body B'],
            3: ['Push (Empurrar)', 'Pull (Puxar)', 'Legs (Pernas)'],
            4: ['Peito/Tríceps', 'Costas/Bíceps', 'Pernas', 'Ombros/Abdomen'],
            5: ['Peito', 'Costas', 'Pernas', 'Ombros', 'Braços/Abdomen'],
            6: ['Peito', 'Costas', 'Pernas', 'Ombros', 'Braços', 'Cardio/Abdomen']
        },
        'emagrecimento': {
            2: ['Full Body + Cardio A', 'Full Body + Cardio B'],
            3: ['Circuit Training A', 'HIIT Cardio', 'Circuit Training B'],
            4: ['Superiores + Cardio', 'Inferiores + Cardio', 'Full Body', 'Cardio Intenso'],
            5: ['Força Superior', 'Força Inferior', 'HIIT', 'Cardio Steady', 'Full Body Circuit']
        },
        'forca': {
            2: ['Força Superior', 'Força Inferior'],
            3: ['Força Peito/Ombro', 'Força Costas', 'Força Pernas'],
            4: ['Força Superior A', 'Força Inferior A', 'Força Superior B', 'Força Inferior B'],
            5: ['Força Compostos', 'Força Acessórios', 'Força Pernas', 'Técnica', 'Mobilidade']
        },
        'definicao': {
            3: ['Superiores Definção', 'Inferiores Definição', 'Full Body Circuit'],
            4: ['Push Definição', 'Pull Definição', 'Legs Definição', 'Cardio Definição'],
            5: ['Peito/Tríceps Def', 'Costas/Bíceps Def', 'Pernas/Glúteos Def', 'Ombros/Abdomen Def', 'Cardio HIIT']
        }
    }
    
    # Escolher estrutura baseada no objetivo
    estrutura = estruturas_treino.get(objetivo, estruturas_treino['hipertrofia'])
    tipos_treino = estrutura.get(dias_semana, ['Full Body A', 'Full Body B'])
    
    treinos_criados = []
    dias_semana_por_estrutura = {
    2: ['Segunda', 'Quarta'],
    3: ['Segunda', 'Quarta', 'Sexta'],
    4: ['Segunda', 'Terça', 'Quinta', 'Sexta'],
    5: ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'],
    6: ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    }

    dias_semana_lista = dias_semana_por_estrutura.get(dias_semana, ['Segunda', 'Quarta', 'Sexta'])
    
    for i, tipo_treino in enumerate(tipos_treino):
        treino = Treino(
            aluno_id=usuario.id,
            nome=f"Treino {tipo_treino}",
            tipo=tipo_treino,
            descricao=f"Treino personalizado para {objetivo} - Nível {nivel}",
            status='ativo',
            dia_semana=dias_semana_lista[i],
            ordem=i+1
        )
        db.session.add(treino)
        db.session.flush()
        
        # Selecionar exercícios do catálogo baseado no tipo de treino
        exercicios_selecionados = selecionar_exercicios_do_catalogo(tipo_treino, nivel, objetivo, usuario.tempo_treino_dia)
        
        for j, exercicio_info in enumerate(exercicios_selecionados):
            exercicio_treino = ExercicioTreino(
                treino_id=treino.id,
                catalogo_exercicio_id=exercicio_info['id'],
                series=exercicio_info['series'],
                repeticoes=exercicio_info['repeticoes'],
                descanso=exercicio_info['descanso'],
                ordem=j+1
            )
            db.session.add(exercicio_treino)
        
        treinos_criados.append(treino)
    
    db.session.commit()
    return treinos_criados

def selecionar_exercicios_do_catalogo(tipo_treino, nivel, objetivo, tempo_disponivel):
    """Seleciona exercícios inteligentemente do catálogo baseado no tipo de treino"""
    
    try:
        print(f"\n🔍 SELECIONANDO EXERCÍCIOS PARA: {tipo_treino}")
        
        # Parâmetros baseados no nível
        parametros = {
            'iniciante': {'series': 3, 'repeticoes': '12-15', 'descanso': '60s'},
            'intermediario': {'series': 3, 'repeticoes': '10-12', 'descanso': '75s'},
            'avancado': {'series': 4, 'repeticoes': '8-10', 'descanso': '90s'}
        }
        
        params = parametros.get(nivel, parametros['iniciante'])
        
        # CORREÇÃO COMPLETA: Mapeamento específico e restrito
        mapeamento_grupos = {
            # Treino de Peito (inclui ombros e tríceps)
            'Treino Peito': ['Peito', 'Ombros', 'Tríceps'],
            
            # Treino de Costas (inclui bíceps)
            'Treino Costas': ['Costas', 'Bíceps'],
            
            # Treino de Pernas
            'Treino Pernas': ['Pernas', 'Glúteos', 'Panturrilhas'],
            
            # Treino de Ombros (APENAS ombros)
            'Treino Ombros': ['Ombros'],
            
            # Treino de Braços (APENAS bíceps e tríceps)
            'Treino Braços': ['Bíceps', 'Tríceps'],
            
            # Cardio (APENAS cardio)
            'Treino Cardio': ['Cardio'],
            
            # Full Body
            'Full Body A': ['Peito', 'Costas', 'Pernas'],
            'Full Body B': ['Ombros', 'Bíceps', 'Tríceps']
        }
        
        # Obter grupos específicos para este treino
        grupos = mapeamento_grupos.get(tipo_treino, ['Peito', 'Costas', 'Pernas'])
        
        print(f"Grupos musculares para {tipo_treino}: {grupos}")
        
        # CORREÇÃO: Sempre limitar a 5 exercícios
        max_exercicios = 5
        exercicios_selecionados = []
        nomes_vistos = set()
        
        # CORREÇÃO: Buscar exercícios de forma controlada
        for grupo in grupos:
            if len(exercicios_selecionados) >= max_exercicios:
                break
                
            print(f"Buscando exercícios para grupo: {grupo}")
            
            # Buscar exercícios específicos do grupo
            exercicios_grupo = CatalogoExercicio.query.filter(
                CatalogoExercicio.grupo_muscular == grupo,
                CatalogoExercicio.ativo == True
            ).all()
            
            print(f"Encontrados {len(exercicios_grupo)} exercícios no grupo {grupo}")
            
            # Adicionar exercícios únicos deste grupo
            for exercicio in exercicios_grupo:
                if (exercicio.nome not in nomes_vistos and 
                    len(exercicios_selecionados) < max_exercicios):
                    
                    exercicios_selecionados.append(exercicio)
                    nomes_vistos.add(exercicio.nome)
                    print(f"  ✅ Adicionado: {exercicio.nome}")
                    
                if len(exercicios_selecionados) >= max_exercicios:
                    break
        
        # CORREÇÃO CRÍTICA: Se não encontrou exercícios suficientes, NÃO buscar de outros grupos
        # Isso evita a contaminação entre treinos
        if len(exercicios_selecionados) < 3:
            print(f"⚠️  Aviso: Apenas {len(exercicios_selecionados)} exercícios encontrados para {tipo_treino}")
            # Mantemos o que temos, mesmo que sejam poucos
        
        # Ajustar parâmetros baseados no objetivo
        if objetivo == 'forca':
            params['repeticoes'] = '4-6' if nivel == 'avancado' else '6-8'
            params['descanso'] = '120s' if nivel == 'avancado' else '90s'
        elif objetivo == 'emagrecimento':
            params['repeticoes'] = '15-20'
            params['descanso'] = '45s'
        
        resultado = [{
            'id': ex.id,
            'series': params['series'],
            'repeticoes': params['repeticoes'],
            'descanso': params['descanso']
        } for ex in exercicios_selecionados]
        
        print(f"🎯 Resultado final para {tipo_treino}: {len(resultado)} exercícios")
        for ex in exercicios_selecionados:
            print(f"   - {ex.nome} ({ex.grupo_muscular})")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Erro crítico ao selecionar exercícios para {tipo_treino}: {str(e)}")
        return []
    
def calcular_max_exercicios(tempo_disponivel):
    """Calcula o número máximo de exercícios baseado no tempo disponível"""
    # CORREÇÃO: Sempre limitar a 5 exercícios, independente do tempo
    if tempo_disponivel <= 45:
        return 4
    elif tempo_disponivel <= 60:
        return 5
    elif tempo_disponivel <= 75:
        return 5
    else:
        return 5  # Máximo de 5 exercícios
    
def selecionar_exercicios_ia(tipo_treino, nivel):
    """Seleciona exercícios do catálogo baseado no tipo de treino e nível"""
    
    # Definir parâmetros baseado no nível
    if nivel == 'iniciante':
        series = 3
        repeticoes = '12-15'
        descanso = '60s'
    elif nivel == 'intermediario':
        series = 4
        repeticoes = '8-12'
        descanso = '90s'
    else:  # avançado
        series = 4
        repeticoes = '6-10'
        descanso = '120s'
    
    # Selecionar exercícios baseado no tipo de treino
    if 'Superiores A' in tipo_treino:
        grupos = ['Peito', 'Costas', 'Ombros']
    elif 'Superiores B' in tipo_treino:
        grupos = ['Peito', 'Costas', 'Bíceps', 'Tríceps']
    elif 'Inferiores' in tipo_treino:
        grupos = ['Pernas', 'Glúteos', 'Panturrilhas']
    elif 'Full Body' in tipo_treino:
        grupos = ['Peito', 'Costas', 'Pernas', 'Ombros']
    else:  # Cardio ou outros
        grupos = ['Cardio']
    
    exercicios = CatalogoExercicio.query.filter(
        CatalogoExercicio.grupo_muscular.in_(grupos),
        CatalogoExercicio.nivel_dificuldade == nivel,
        CatalogoExercicio.ativo == True
    ).limit(6).all()
    
    return [{
        'id': ex.id,
        'series': series,
        'repeticoes': repeticoes,
        'descanso': descanso
    } for ex in exercicios]

@treinos_bp.route('/api/buscar-exercicios')
def buscar_exercicios():
    grupo = request.args.get('grupo')
    nivel = request.args.get('nivel')
    
    query = CatalogoExercicio.query.filter_by(ativo=True)
    
    if grupo:
        query = query.filter_by(grupo_muscular=grupo)
    if nivel:
        query = query.filter_by(nivel_dificuldade=nivel)
    
    exercicios = query.all()
    
    return jsonify({
        'success': True,
        'exercicios': [{
            'id': ex.id,
            'nome': ex.nome,
            'grupo_muscular': ex.grupo_muscular,
            'equipamento': ex.equipamento,
            'video_url': ex.video_url,
            'instrucoes': ex.instrucoes
        } for ex in exercicios]
    })

def validar_treino_gerado(treino):
    """Valida se o treino gerado está correto"""
    exercicios = treino.exercicios
    nomes_exercicios = [ex.catalogo.nome for ex in exercicios]
    grupos_exercicios = [ex.catalogo.grupo_muscular for ex in exercicios]
    
    print(f"\nValidando {treino.nome}:")
    print(f"  Exercícios: {len(exercicios)}")
    print(f"  Nomes: {nomes_exercicios}")
    print(f"  Grupos: {grupos_exercicios}")
    
    # Verificar se há no máximo 5 exercícios
    if len(exercicios) > 5:
        print(f"❌ AVISO: Treino {treino.nome} tem {len(exercicios)} exercícios (máximo é 5)")
        return False
    
    # Verificar se há exercícios duplicados
    if len(nomes_exercicios) != len(set(nomes_exercicios)):
        print(f"❌ AVISO: Treino {treino.nome} tem exercícios duplicados")
        return False
    
    print(f"✅ Treino {treino.nome} válido: {len(exercicios)} exercícios")
    return True

def verificar_catalogo_exercicios():
    """Verifica quantos exercícios existem por grupo muscular no catálogo"""
    print("\n🔍 VERIFICANDO CATÁLOGO DE EXERCÍCIOS:")
    
    grupos = ['Peito', 'Costas', 'Pernas', 'Ombros', 'Bíceps', 'Tríceps', 'Cardio', 'Glúteos', 'Panturrilhas']
    
    for grupo in grupos:
        count = CatalogoExercicio.query.filter(
            CatalogoExercicio.grupo_muscular == grupo,
            CatalogoExercicio.ativo == True
        ).count()
        print(f"  {grupo}: {count} exercícios")
    
    # Verificar exercícios problemáticos
    exercicios_problematicos = CatalogoExercicio.query.filter(
        CatalogoExercicio.grupo_muscular.notin_(grupos)
    ).all()
    
    if exercicios_problematicos:
        print(f"⚠️  Exercícios com grupos inválidos:")
        for ex in exercicios_problematicos:
            print(f"    - {ex.nome}: {ex.grupo_muscular}")