function enviarPergunta(event) {
    // Verifica se pressionou "Enter" ou clicou no botão de enviar
    if (event.key === 'Enter' || event.type === 'click') {
        const userInput = document.getElementById('user-input').value.trim();
        if (userInput === '') return;  // Ignora se o campo estiver vazio

        // Exibe a mensagem do usuário no chat
        adicionarMensagem(userInput, 'user');
        document.getElementById('user-input').value = '';  // Limpa o campo de entrada

        // Envia a pergunta para o servidor Flask
        fetch('/pergunta', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pergunta: userInput })
        })
        .then(response => response.json())
        .then(data => {
            // Exibe a resposta do chatbot no chat
            adicionarMensagem(data.resposta, 'bot');
        })
        .catch(error => {
            console.error('Erro:', error);
            adicionarMensagem('Desculpe, houve um erro. Tente novamente.', 'bot');
        });
    }
}

function adicionarMensagem(mensagem, tipo) {
    const chatBox = document.getElementById('chat-box');
    const divMensagem = document.createElement('div');
    divMensagem.classList.add('message');
    divMensagem.classList.add(tipo === 'user' ? 'user-message' : 'bot-message');
    divMensagem.textContent = mensagem;
    chatBox.appendChild(divMensagem);
    chatBox.scrollTop = chatBox.scrollHeight;  // Faz o scroll para a última mensagem
}
