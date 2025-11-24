from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from db import db
from models import Usuario, Treino, ExercicioTreino, CatalogoExercicio, Progresso, HistoricoTreino
from datetime import datetime
import json

formulario_bp = Blueprint('formulario', __name__)

@formulario_bp.route('/formulario/<key>')
def formulario(key):
    usuario = Usuario.query.filter_by(key=key).first()
    if not usuario:
        return "Usuário não encontrado", 404
    
    # Verificar se já preencheu o formulário
    #if usuario.formulario_preenchido:
        #return redirect(url_for('usuarios.usuarios', key=key))
    
    return render_template('formulario.html', user=usuario, key=key)

@formulario_bp.route('/api/salvar-formulario', methods=['POST'])
def salvar_formulario():
    try:
        data = request.get_json()
        key = data.get('key')
        
        usuario = Usuario.query.filter_by(key=key).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
        
        mapeamento_objetivos = {
            'massa': 'hipertrofia',
            'definicao': 'definicao',  # CORREÇÃO: era 'emagrecimento'
            'saude': 'hipertrofia',    # Padrão para saúde
            'forca': 'forca',
            'estetico': 'definicao'
        }
        
        # Tratar tempo
        tempo_str = data.get('tempo', '60')
        if tempo_str == 'mais':
            tempo_treino = 90
        else:
            tempo_treino = int(tempo_str)
        
        # Tratar frequência
        try:
            frequencia = int(data.get('frequencia', 3))
        except (ValueError, TypeError):
            frequencia = 3
        
        # Salvar respostas do formulário no usuário
        usuario.objetivo = mapeamento_objetivos.get(data.get('objetivo'), 'hipertrofia')
        usuario.nivel_experiencia = data.get('nivel', 'iniciante')
        usuario.dias_treino_semana = frequencia
        usuario.tempo_treino_dia = tempo_treino
        usuario.restricoes_medicas = data.get('lesao', 'nao')
        usuario.formulario_preenchido = True
        usuario.data_formulario = datetime.utcnow()
        
        # Salvar áreas de foco
        areas_foco = data.get('foco', [])
        if isinstance(areas_foco, list) and areas_foco:
            if usuario.restricoes_medicas and usuario.restricoes_medicas != 'nao':
                usuario.restricoes_medicas += f"\nÁreas de foco: {', '.join(areas_foco)}"
            else:
                usuario.restricoes_medicas = f"Áreas de foco: {', '.join(areas_foco)}"
        
        db.session.commit()
        
        # Gerar treinos com IA usando o catálogo
        treinos_gerados = gerar_treinos_ia_personalizado(usuario, data)
        
        return jsonify({
            'success': True, 
            'message': f'Formulário salvo! {len(treinos_gerados)} treinos personalizados gerados com exercícios do catálogo.',
            'treinos_gerados': len(treinos_gerados),
            'redirect_url': url_for('usuarios.mostrar_treinos', key=key)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

def gerar_treinos_ia_personalizado(usuario, respostas_formulario):
    """Gera treinos super personalizados baseado nas respostas do formulário usando catálogo"""
    
    try:
        print("🚀 INICIANDO GERAÇÃO DE TREINOS PERSONALIZADOS")
        
        # Verificar o catálogo primeiro
        verificar_catalogo_exercicios()
        
        # Limpar completamente treinos antigos
        limpar_treinos_antigos(usuario.id)
        
        objetivo = usuario.objetivo
        nivel = usuario.nivel_experiencia
        dias_semana = usuario.dias_treino_semana
        
        print(f"📊 Dados do usuário: Objetivo={objetivo}, Nível={nivel}, Dias={dias_semana}")
        
        # Estrutura de treinos
        estruturas_treino = criar_estrutura_personalizada(objetivo, dias_semana, [])
        
        treinos_criados = []
        dias_semana_lista = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
        
        for i, tipo_treino in enumerate(estruturas_treino):
            if i >= len(dias_semana_lista):
                break
                
            print(f"\n{'='*50}")
            print(f"🎯 CRIANDO: {tipo_treino} para {dias_semana_lista[i]}")
            print(f"{'='*50}")
            
            treino = Treino(
                aluno_id=usuario.id,
                nome=tipo_treino,
                tipo=tipo_treino.replace('Treino ', ''),
                descricao=f"Treino personalizado para {objetivo} - Nível {nivel}",
                status='ativo',
                dia_semana=dias_semana_lista[i],
                ordem=i+1
            )
            db.session.add(treino)
            db.session.flush()
            
            # Selecionar exercícios
            exercicios_selecionados = selecionar_exercicios_do_catalogo(
                tipo_treino, nivel, objetivo, usuario.tempo_treino_dia
            )
            
            print(f"📝 Adicionando {len(exercicios_selecionados)} exercícios ao treino...")
            
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
        
        # Validação final
        print(f"\n{'='*50}")
        print("✅ VALIDAÇÃO FINAL DOS TREINOS")
        print(f"{'='*50}")
        
        for treino in treinos_criados:
            treino_completo = Treino.query.get(treino.id)
            valid = validar_treino_gerado(treino_completo)
            if not valid:
                print(f"❌ TREINO COM PROBLEMAS: {treino.nome}")
        
        print(f"🎉 GERAÇÃO CONCLUÍDA: {len(treinos_criados)} treinos criados")
        return treinos_criados
        
    except Exception as e:
        db.session.rollback()
        print(f"💥 ERRO CRÍTICO na geração de treinos: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e

def criar_estrutura_personalizada(objetivo, dias_semana, areas_foco):
    """Cria estrutura de treino personalizada baseada nas áreas de foco"""
    
    # CORREÇÃO: Estrutura mais conservadora para evitar problemas
    estruturas_base = {
        'hipertrofia': {
            2: ['Treino Peito', 'Treino Pernas'],
            3: ['Treino Peito', 'Treino Costas', 'Treino Pernas'],
            4: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros'],
            5: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Braços'],
            6: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Braços', 'Treino Cardio']
        },
        'emagrecimento': {
            2: ['Full Body A', 'Full Body B'],
            3: ['Full Body A', 'Treino Cardio', 'Full Body B'],
            4: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Cardio'],
            5: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Cardio'],
            6: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Braços', 'Treino Cardio']
        },
        'forca': {
            2: ['Treino Peito', 'Treino Pernas'],
            3: ['Treino Peito', 'Treino Costas', 'Treino Pernas'],
            4: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros'],
            5: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Braços'],
            6: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Braços', 'Full Body A']
        },
        'definicao': {
            3: ['Treino Peito', 'Treino Costas', 'Treino Pernas'],
            4: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Cardio'],
            5: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Cardio'],
            6: ['Treino Peito', 'Treino Costas', 'Treino Pernas', 'Treino Ombros', 'Treino Braços', 'Treino Cardio']
        }
    }
    
    estrutura = estruturas_base.get(objetivo, estruturas_base['hipertrofia'])
    tipos_treino = estrutura.get(dias_semana, ['Treino Peito', 'Treino Pernas'])
    
    print(f"📅 Estrutura para {objetivo} com {dias_semana} dias: {tipos_treino}")
    return tipos_treino

def ajustar_para_areas_foco(tipos_treino, areas_foco, dias_semana):
    """Ajusta os tipos de treino para focar nas áreas escolhidas"""
    
    mapeamento_foco = {
        'peito': 'Peito',
        'costas': 'Costas',
        'pernas': 'Pernas',
        'gluteos': 'Pernas',
        'ombros': 'Ombros',
        'abdomen': 'Abdomen',
        'bracos': 'Braços'
    }
    
    # Converter áreas de foco para grupos de treino
    grupos_foco = []
    for area in areas_foco:
        if area in mapeamento_foco and mapeamento_foco[area] not in grupos_foco:
            grupos_foco.append(mapeamento_foco[area])
    
    if not grupos_foco:
        return tipos_treino
    
    # Criar treinos focados
    novos_tipos = []
    for i in range(dias_semana):
        if i < len(grupos_foco):
            grupo = grupos_foco[i]
            if grupo == 'Pernas':
                novos_tipos.append('Pernas/Glúteos')
            elif grupo == 'Braços':
                novos_tipos.append('Braços/Abdomen')
            else:
                novos_tipos.append(grupo)
        else:
            # Se mais dias que áreas focadas, adicionar full body
            novos_tipos.append(f'Full Body {chr(65 + i)}')
    
    return novos_tipos

def selecionar_exercicios_com_foco(tipo_treino, nivel, objetivo, tempo_disponivel, areas_foco):
    """Seleciona exercícios com foco nas áreas preferidas do usuário"""
    
    # Primeiro, selecionar exercícios baseados no tipo de treino
    exercicios_base = selecionar_exercicios_do_catalogo(tipo_treino, nivel, objetivo, tempo_disponivel)
    
    # Se há áreas de foco específicas, priorizar exercícios dessas áreas
    if areas_foco and 'geral' not in areas_foco:
        exercicios_prioritarios = priorizar_areas_foco(exercicios_base, areas_foco)
        return exercicios_prioritarios
    
    return exercicios_base

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

def priorizar_areas_foco(exercicios, areas_foco):
    """Prioriza exercícios das áreas de foco do usuário"""
    
    mapeamento_grupos = {
        'peito': 'Peito',
        'costas': 'Costas',
        'pernas': 'Pernas',
        'gluteos': 'Glúteos',
        'ombros': 'Ombros',
        'abdomen': 'Abdomen',
        'bracos': ['Bíceps', 'Tríceps']
    }
    
    exercicios_prioritarios = []
    exercicios_restantes = exercicios.copy()
    
    # Primeiro, adicionar exercícios das áreas de foco
    for area in areas_foco:
        if area in mapeamento_grupos:
            grupos_alvo = mapeamento_grupos[area]
            if isinstance(grupos_alvo, list):
                for grupo in grupos_alvo:
                    for exercicio in exercicios_restantes[:]:
                        exercicio_obj = CatalogoExercicio.query.get(exercicio['id'])
                        if exercicio_obj and exercicio_obj.grupo_muscular == grupo:
                            exercicios_prioritarios.append(exercicio)
                            exercicios_restantes.remove(exercicio)
            else:
                for exercicio in exercicios_restantes[:]:
                    exercicio_obj = CatalogoExercicio.query.get(exercicio['id'])
                    if exercicio_obj and exercicio_obj.grupo_muscular == grupos_alvo:
                        exercicios_prioritarios.append(exercicio)
                        exercicios_restantes.remove(exercicio)
    
    # Adicionar os exercícios restantes
    exercicios_prioritarios.extend(exercicios_restantes)
    
    return exercicios_prioritarios

@formulario_bp.route('/api/registrar-execucao-treino', methods=['POST'])
def registrar_execucao_treino():
    """Registra a execução de um treino para análise da IA"""
    try:
        data = request.get_json()
        key = data.get('key')
        treino_id = data.get('treino_id')
        duracao = data.get('duracao_minutos')
        dificuldade = data.get('dificuldade_percebida')
        feedback = data.get('feedback', '')
        
        usuario = Usuario.query.filter_by(key=key).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
        
        # Registrar histórico
        historico = HistoricoTreino(
            usuario_id=usuario.id,
            treino_id=treino_id,
            duracao_minutos=duracao,
            dificuldade_percebida=dificuldade,
            feedback_usuario=feedback
        )
        
        # Analisar e sugerir ajustes
        ajuste = analisar_desempenho_treino(usuario, treino_id, duracao, dificuldade)
        historico.ajuste_recomendado = ajuste
        
        db.session.add(historico)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'ajuste_recomendado': ajuste,
            'message': 'Treino registrado com sucesso!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def analisar_desempenho_treino(usuario, treino_id, duracao, dificuldade):
    """Analisa o desempenho do treino e sugere ajustes"""
    
    treino = Treino.query.get(treino_id)
    if not treino:
        return "manter"
    
    # Calcular tempo esperado baseado no número de exercícios
    num_exercicios = len(treino.exercicios_treino)
    tempo_esperado = num_exercicios * 15  # 15 minutos por exercício em média
    
    # Análise de dificuldade
    if dificuldade in ['muito_facil', 'facil'] and duracao < tempo_esperado * 0.7:
        return "aumentar"
    elif dificuldade in ['muito_dificil'] and duracao > tempo_esperado * 1.3:
        return "reduzir"
    else:
        return "manter"

@formulario_bp.route('/api/aplicar-ajuste-treino', methods=['POST'])
def aplicar_ajuste_treino():
    """Aplica ajustes automáticos nos treinos baseado no desempenho"""
    try:
        data = request.get_json()
        key = data.get('key')
        treino_id = data.get('treino_id')
        acao = data.get('acao')  # 'aumentar', 'manter', 'reduzir'
        
        usuario = Usuario.query.filter_by(key=key).first()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
        
        treino = Treino.query.get(treino_id)
        if not treino:
            return jsonify({'success': False, 'message': 'Treino não encontrado'})
        
        # Aplicar ajustes nos exercícios do treino
        for exercicio in treino.exercicios_treino:
            if acao == 'aumentar':
                # Aumentar intensidade
                if exercicio.series < 5:
                    exercicio.series += 1
                # Ajustar repetições
                repeticoes = exercicio.repeticoes.split('-')
                if len(repeticoes) == 2:
                    min_rep = int(repeticoes[0]) - 2
                    max_rep = int(repeticoes[1]) - 2
                    exercicio.repeticoes = f"{max(min_rep, 6)}-{max(max_rep, 8)}"
                    
            elif acao == 'reduzir':
                # Reduzir intensidade
                if exercicio.series > 2:
                    exercicio.series -= 1
                # Ajustar repetições
                repeticoes = exercicio.repeticoes.split('-')
                if len(repeticoes) == 2:
                    min_rep = int(repeticoes[0]) + 2
                    max_rep = int(repeticoes[1]) + 2
                    exercicio.repeticoes = f"{min_rep}-{max_rep}"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Treino ajustado para {acao} intensidade!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
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

def limpar_treinos_antigos(usuario_id):
    """Limpa completamente todos os treinos antigos do usuário"""
    try:
        # Buscar todos os treinos do usuário
        treinos_antigos = Treino.query.filter_by(aluno_id=usuario_id).all()
        
        for treino in treinos_antigos:
            # Deletar exercícios do treino
            ExercicioTreino.query.filter_by(treino_id=treino.id).delete()
            # Deletar progressos do treino
            Progresso.query.filter_by(treino_id=treino.id).delete()
            # Deletar histórico do treino
            HistoricoTreino.query.filter_by(treino_id=treino.id).delete()
            # Deletar o treino
            db.session.delete(treino)
        
        db.session.commit()
        print(f"Limpeza concluída: {len(treinos_antigos)} treinos removidos")
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro na limpeza: {str(e)}")
        raise e
    
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