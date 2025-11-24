const key = document.body.dataset.key;
let todosAlunos = []; // Variável global para armazenar todos os alunos

// Dados mock para fallback
const dadosMock = {
    estatisticas: {
        total_alunos: 0,
        alunos_ativos: 0,
        alunos_inativos: 0,
        chats_ativos: 0
    },
    alunos: []
};

// Carregar dados ao iniciar a página
document.addEventListener('DOMContentLoaded', function() {
    carregarEstatisticas();
    carregarAlunos();
    
    // Adicionar evento de pesquisa
    document.getElementById('searchInput').addEventListener('input', filtrarPesquisa);
});

async function carregarEstatisticas() {
    try {
        // Agora passando a key na URL
        const response = await fetch(`/api/estatisticas/${key}`);
        
        if (!response.ok) {
            if (response.status === 403) {
                console.warn('Acesso não autorizado às estatísticas');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        exibirEstatisticas(data);
        
    } catch (error) {
        console.warn('API não disponível, usando dados mock:', error.message);
        exibirEstatisticas(dadosMock.estatisticas);
    }
}

function exibirEstatisticas(data) {
    document.getElementById('statsContainer').innerHTML = `
        <div class="card stat-card">
            <div class="stat-icon icon-primary">
                <i class="fas fa-users"></i>
            </div>
            <div class="stat-info">
                <h3>${data.total_alunos || data.alunos_ativos}</h3>
                <p>Total de Alunos</p>
            </div>
        </div>
        
        <div class="card stat-card">
            <div class="stat-icon icon-secondary">
                <i class="fas fa-dumbbell"></i>
            </div>
            <div class="stat-info">
                <h3>${data.alunos_ativos}</h3>
                <p>Com Treinos Ativos</p>
            </div>
        </div>
        
        <div class="card stat-card">
            <div class="stat-icon icon-accent">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="stat-info">
                <h3>${data.alunos_inativos}</h3>
                <p>Precisam de Acompanhamento</p>
            </div>
        </div>
        
        <div class="card stat-card">
            <div class="stat-icon icon-primary">
                <i class="fas fa-comments"></i>
            </div>
            <div class="stat-info">
                <h3>${data.chats_ativos}</h3>
                <p>Chats Ativos</p>
            </div>
        </div>
    `;
}

async function carregarAlunos() {
    try {
        const response = await fetch(`/api/alunos/${key}`);
        
        if (!response.ok) {
            if (response.status === 403) {
                alert('Acesso não autorizado! Redirecionando para login...');
                window.location.href = '/login';
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const alunos = await response.json();
        todosAlunos = alunos;
        renderizarAlunos(alunos);
        
    } catch (error) {
        console.warn('API não disponível, usando dados mock:', error.message);
        todosAlunos = dadosMock.alunos;
        renderizarAlunos(dadosMock.alunos);
    }
}

function renderizarAlunos(alunos) {
    const tbody = document.getElementById('alunosBody');
    tbody.innerHTML = '';
    
    if (alunos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: var(--gray);">
                    <i class="fas fa-users" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>
                    Nenhum aluno encontrado
                </td>
            </tr>
        `;
        return;
    }
    
    alunos.forEach(aluno => {
        const statusText = aluno.status === 'Ativo' ? 'Ativo' : 'Precisa de Acompanhamento';
        const statusClass = aluno.status === 'Ativo' ? 'status-active' : 'status-inactive';
        
        const row = `
            <tr>
                <td>
                    <div style="display: flex; align-items: center;">
                        <div class="chat-contact-avatar">${aluno.nome[0]}</div>
                        <div>${aluno.nome}</div>
                    </div>
                </td>
                <td>${aluno.treino} - ${aluno.nivel}</td>
                <td>${aluno.ultimo_acesso}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${aluno.progresso}%"></div>
                    </div>
                    <small style="color: var(--gray); font-size: 0.8rem; display: block; text-align: center; margin-top: 5px;">
                        ${aluno.progresso}%
                    </small>
                </td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="action-btn btn-primary" onclick="verAluno(${aluno.id})" title="Ver Detalhes">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn" onclick="abrirChat(${aluno.id})" title="Enviar Mensagem">
                        <i class="fas fa-comment"></i>
                    </button>
                    ${aluno.status !== 'Ativo' ? `
                    <button class="action-btn btn-warning" onclick="criarTreino(${aluno.id})" title="Criar Treino">
                        <i class="fas fa-plus"></i>
                    </button>
                    ` : ''}
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function filtrarAlunos(tipo) {
    // Verifica se existem alunos para filtrar
    if (!todosAlunos || todosAlunos.length === 0) {
        console.log('Nenhum aluno disponível para filtrar');
        return;
    }
    
    // Atualizar tabs ativas
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    let alunosFiltrados = [];
    
    switch(tipo) {
        case 'todos':
            alunosFiltrados = todosAlunos;
            console.log(`Mostrando todos os ${todosAlunos.length} alunos`);
            break;
            
        case 'ativos':
            // Alunos com status "Ativo" = Com Treinos Ativos
            alunosFiltrados = todosAlunos.filter(aluno => aluno.status === 'Ativo');
            console.log(`${alunosFiltrados.length} alunos com treinos ativos`);
            break;
            
        case 'inativos':
            // Alunos com status diferente de "Ativo" = Precisam de Acompanhamento
            alunosFiltrados = todosAlunos.filter(aluno => aluno.status !== 'Ativo');
            console.log(`${alunosFiltrados.length} alunos precisam de acompanhamento`);
            break;
            
        default:
            alunosFiltrados = todosAlunos;
            console.log(`Filtro desconhecido, mostrando todos os ${todosAlunos.length} alunos`);
    }
    
    renderizarAlunos(alunosFiltrados);
    
    // Mostrar mensagem se não houver resultados
    if (alunosFiltrados.length === 0) {
        const tbody = document.getElementById('alunosBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: var(--gray);">
                    <i class="fas fa-users" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>
                    Nenhum aluno encontrado para este filtro
                </td>
            </tr>
        `;
    }
}

function filtrarPesquisa() {
    const termo = document.getElementById('searchInput').value.toLowerCase();
    const linhas = document.querySelectorAll('#alunosBody tr');
    
    linhas.forEach(linha => {
        const texto = linha.textContent.toLowerCase();
        linha.style.display = texto.includes(termo) ? '' : 'none';
    });
}

function verAluno(alunoId) {
    // Redirecionar para página de detalhes do aluno /${alunoId}?key=${key}
    window.location.href = `/aluno/key=${key}`;
}

function abrirChat(alunoId) {
    // Abrir chat com o aluno /${alunoId}
    window.location.href = `/suporte_profissional/key=${key}`;
}

function criarTreino(alunoId) {
    // Criar treino para aluno que precisa de acompanhamento /${alunoId}
    window.location.href = `/criar-treino}/key=${key}`;
}