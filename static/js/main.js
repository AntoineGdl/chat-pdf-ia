document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const questionInput = document.getElementById('question-input');
    const sendBtn = document.getElementById('send-btn');
    const reloadBtn = document.getElementById('reload-btn');
    const statsDiv = document.getElementById('stats');

    // Charger les statistiques au démarrage
    loadStats();

    // Gestionnaire pour le bouton d'envoi
    sendBtn.addEventListener('click', sendQuestion);

    // Gestionnaire pour la touche Entrée
    questionInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendQuestion();
        }
    });

    // Gestionnaire pour le bouton de rechargement
    reloadBtn.addEventListener('click', reloadDocuments);

    function loadStats() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statsDiv.textContent = `${data.sections_count} sections de documentation disponibles`;
                } else {
                    statsDiv.textContent = "Erreur lors du chargement des statistiques";
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                statsDiv.textContent = "Erreur de connexion";
            });
    }

    function reloadDocuments() {
        // Désactiver le bouton pendant le chargement
        reloadBtn.disabled = true;
        reloadBtn.textContent = 'Chargement en cours...';

        // Ajouter un message système
        addMessage('system', 'Rechargement de la documentation en cours...');

        fetch('/api/reload', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addMessage('system', `Rechargement terminé. ${data.sections_count} sections disponibles.`);
            } else {
                addMessage('system', 'Erreur lors du rechargement de la documentation.');
            }

            // Mise à jour des stats et réactivation du bouton
            statsDiv.textContent = `${data.sections_count} sections de documentation disponibles`;
            reloadBtn.disabled = false;
            reloadBtn.textContent = 'Recharger la documentation';
        })
        .catch(error => {
            console.error('Erreur:', error);
            addMessage('system', 'Erreur de connexion lors du rechargement.');
            reloadBtn.disabled = false;
            reloadBtn.textContent = 'Recharger la documentation';
        });
    }

    function sendQuestion() {
        const question = questionInput.value.trim();

        if (!question) return;

        // Afficher la question
        addMessage('user', question);

        // Vider l'input et désactiver
        questionInput.value = '';
        questionInput.disabled = true;
        sendBtn.disabled = true;

        // Message de chargement
        const loadingMsgId = Date.now();
        addMessage('assistant', 'Recherche en cours...', loadingMsgId);

        fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question
            })
        })
        .then(response => response.json())
        .then(data => {
            // Supprimer le message de chargement
            removeMessage(loadingMsgId);

            if (data.success) {
                addMessage('assistant', data.answer);
            } else {
                addMessage('system', 'Erreur: ' + (data.error || 'Problème inconnu'));
            }

            // Réactiver les contrôles
            questionInput.disabled = false;
            sendBtn.disabled = false;
            questionInput.focus();
        })
        .catch(error => {
            console.error('Erreur:', error);
            removeMessage(loadingMsgId);
            addMessage('system', 'Erreur de connexion. Veuillez réessayer.');
            questionInput.disabled = false;
            sendBtn.disabled = false;
            questionInput.focus();
        });
    }

    function addMessage(type, content, id = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        if (id) {
            messageDiv.id = `msg-${id}`;
        }

        // Formater avec des sauts de ligne
        messageDiv.innerHTML = content.replace(/\n/g, '<br>');

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeMessage(id) {
        const messageDiv = document.getElementById(`msg-${id}`);
        if (messageDiv) {
            messageDiv.remove();
        }
    }
});