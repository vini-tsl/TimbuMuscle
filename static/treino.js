// Funcionalidade de pesquisa
const searchInput = document.querySelector('input');
const treinoCards = document.querySelectorAll('.treino-card');

searchInput.addEventListener('input', function() {
    const searchTerm = this.value.toLowerCase();
    
    treinoCards.forEach(card => {
        const title = card.querySelector('.treino-header').textContent.toLowerCase();
        const content = card.querySelector('.treino-content').textContent.toLowerCase();
        
        if (title.includes(searchTerm) || content.includes(searchTerm)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
});


