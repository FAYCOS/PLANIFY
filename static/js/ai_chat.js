/**
 * Chatbot IA - Interface utilisateur
 * Design Apple Minimal Ultra
 */

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function getPublicApiToken() {
    const meta = document.querySelector('meta[name="public-api-token"]');
    return meta ? meta.getAttribute('content') : '';
}

class AIChat {
    constructor() {
        this.conversationId = this.generateConversationId();
        this.isOpen = false;
        this.isTyping = false;
        this.init();
    }

    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    init() {
        this.createChatUI();
        this.attachEventListeners();
        // Charger le message de bienvenue avec le nom de l'entreprise
        setTimeout(() => this.loadWelcomeMessage(), 500);
    }
    
    async loadWelcomeMessage() {
        try {
            const headers = {};
            const publicToken = getPublicApiToken();
            if (publicToken) {
                headers['X-Public-Token'] = publicToken;
            }
            const response = await fetch('/api/chat/welcome', { headers });
            const data = await response.json();
            
            if (data.success && data.message) {
                this.addMessage(data.message, 'bot');
            } else {
                this.addMessage("Bonjour ! Quel type d'événement organisez-vous ?", 'bot');
            }
        } catch (error) {
            console.error('Erreur chargement message de bienvenue:', error);
            this.addMessage("Bonjour ! Quel type d'événement organisez-vous ?", 'bot');
        }
    }

    createChatUI() {
        const chatHTML = `
            <!-- Bouton flottant -->
            <button id="aiChatButton" class="ai-chat-button" aria-label="Ouvrir l'assistant IA">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2C6.48 2 2 6.48 2 12C2 13.8 2.53 15.46 3.44 16.84L2.35 20.64C2.17 21.22 2.62 21.79 3.22 21.76L7.26 21.51C8.74 22.44 10.5 23 12.37 23C17.89 23 22.37 18.52 22.37 13C22.37 7.48 17.89 3 12.37 3L12 2Z" fill="currentColor"/>
                    <circle cx="8.5" cy="12" r="1.5" fill="white"/>
                    <circle cx="12" cy="12" r="1.5" fill="white"/>
                    <circle cx="15.5" cy="12" r="1.5" fill="white"/>
                </svg>
                <span class="ai-chat-badge">IA</span>
            </button>

            <!-- Fenêtre de chat -->
            <div id="aiChatWindow" class="ai-chat-window">
                <div class="ai-chat-header">
                    <div class="ai-chat-header-content">
                        <div class="ai-chat-avatar">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                                <path d="M12 2L2 7V12C2 16.55 5.84 20.74 12 22C18.16 20.74 22 16.55 22 12V7L12 2Z" fill="currentColor"/>
                            </svg>
                        </div>
                        <div>
                            <h3 class="ai-chat-title">Assistant Planify</h3>
                            <p class="ai-chat-status">
                                <span class="ai-chat-status-dot"></span>
                                En ligne
                            </p>
                        </div>
                    </div>
                    <button id="aiChatClose" class="ai-chat-close" aria-label="Fermer">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                    </button>
                </div>

                <div id="aiChatMessages" class="ai-chat-messages">
                    <!-- Messages apparaîtront ici -->
                </div>

                <div class="ai-chat-footer">
                    <form id="aiChatForm" class="ai-chat-input-container">
                        <input 
                            type="text" 
                            id="aiChatInput" 
                            class="ai-chat-input" 
                            placeholder="Posez votre question..."
                            autocomplete="off"
                        >
                        <button type="submit" class="ai-chat-send" aria-label="Envoyer">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                            </svg>
                        </button>
                    </form>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', chatHTML);
    }

    attachEventListeners() {
        const button = document.getElementById('aiChatButton');
        const closeBtn = document.getElementById('aiChatClose');
        const form = document.getElementById('aiChatForm');

        button.addEventListener('click', () => this.toggleChat());
        closeBtn.addEventListener('click', () => this.toggleChat());
        form.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    toggleChat() {
        const window = document.getElementById('aiChatWindow');
        const button = document.getElementById('aiChatButton');
        
        this.isOpen = !this.isOpen;
        
        if (this.isOpen) {
            window.classList.add('ai-chat-window-open');
            button.classList.add('ai-chat-button-hidden');
            document.getElementById('aiChatInput').focus();
        } else {
            window.classList.remove('ai-chat-window-open');
            button.classList.remove('ai-chat-button-hidden');
        }
    }

    sendWelcomeMessage() {
        this.addMessage(
            "Bonjour ! 👋 Je suis votre assistant Planify IA. Je vais vous aider à trouver la prestation parfaite pour votre événement. Pour commencer, quel type d'événement organisez-vous ?",
            'bot'
        );
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const input = document.getElementById('aiChatInput');
        const message = input.value.trim();
        
        if (!message || this.isTyping) return;
        
        // Afficher le message utilisateur
        this.addMessage(message, 'user');
        input.value = '';
        
        // Afficher l'indicateur de saisie
        this.showTypingIndicator();
        
        try {
            const csrfToken = getCsrfToken();
            const headers = {
                'Content-Type': 'application/json'
            };
            if (csrfToken) {
                headers['X-CSRF-Token'] = csrfToken;
            }
            const publicToken = getPublicApiToken();
            if (publicToken) {
                headers['X-Public-Token'] = publicToken;
            }
            const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId
                })
            });
            
            const data = await response.json();
            
            // Retirer l'indicateur de saisie
            this.hideTypingIndicator();
            
            if (data.success) {
                // Afficher la réponse de l'IA
                this.addMessage(data.response, 'bot');
                
                // Après 6 messages utilisateur, appliquer automatiquement les recommandations
                const userMessages = document.querySelectorAll('.ai-chat-message-user').length;
                if (userMessages >= 6) {
                    // Appliquer automatiquement les recommandations après 1 seconde
                    setTimeout(() => this.applyRecommendationsAuto(), 1000);
                }
            } else {
                this.addMessage("Désolé, une erreur est survenue. Pouvez-vous reformuler ?", 'bot');
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage("Erreur de connexion. Veuillez réessayer.", 'bot');
        }
    }

    addMessage(text, sender) {
        const messagesContainer = document.getElementById('aiChatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-chat-message ai-chat-message-${sender}`;
        
        if (sender === 'bot') {
            messageDiv.innerHTML = `
                <div class="ai-chat-avatar-small">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L2 7V12C2 16.55 5.84 20.74 12 22C18.16 20.74 22 16.55 22 12V7L12 2Z"/>
                    </svg>
                </div>
                <div class="ai-chat-bubble ai-chat-bubble-bot">
                    ${this.formatMessage(text)}
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="ai-chat-bubble ai-chat-bubble-user">
                    ${this.escapeHtml(text)}
                </div>
            `;
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Animation d'entrée
        setTimeout(() => messageDiv.classList.add('ai-chat-message-visible'), 10);
    }

    formatMessage(text) {
        // Remplacer les emojis et formater le texte
        return this.escapeHtml(text)
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showTypingIndicator() {
        this.isTyping = true;
        const messagesContainer = document.getElementById('aiChatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.id = 'aiTypingIndicator';
        typingDiv.className = 'ai-chat-message ai-chat-message-bot';
        typingDiv.innerHTML = `
            <div class="ai-chat-avatar-small">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L2 7V12C2 16.55 5.84 20.74 12 22C18.16 20.74 22 16.55 22 12V7L12 2Z"/>
                </svg>
            </div>
            <div class="ai-chat-bubble ai-chat-bubble-bot ai-chat-typing">
                <span></span><span></span><span></span>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
        this.isTyping = false;
        const indicator = document.getElementById('aiTypingIndicator');
        if (indicator) indicator.remove();
    }

    async applyRecommendations() {
        try {
            const headers = {};
            const publicToken = getPublicApiToken();
            if (publicToken) {
                headers['X-Public-Token'] = publicToken;
            }
            const response = await fetch(`/api/chat/recommendations/${this.conversationId}`, { headers });
            const data = await response.json();
            
            if (data.success && data.recommendations) {
                const reco = data.recommendations;
                
                // Pré-remplir le formulaire
                if (reco.type_evenement) {
                    const typeSelect = document.getElementById('type_evenement');
                    if (typeSelect) typeSelect.value = reco.type_evenement;
                }
                
                if (reco.services && reco.services.length > 0) {
                    reco.services.forEach(service => {
                        const checkbox = document.getElementById(`service_${service}`);
                        if (checkbox) checkbox.checked = true;
                    });
                }
                
                // Fermer le chat et afficher un message
                this.addMessage("✓ Formulaire pré-rempli avec vos préférences ! Complétez les informations manquantes et validez.", 'bot');
                
                setTimeout(() => {
                    this.toggleChat();
                    // Scroll vers le formulaire
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 2000);
            }
        } catch (error) {
            console.error('Erreur lors de l\'application des recommandations:', error);
        }
    }

    async applyRecommendationsAuto() {
        try {
            const headers = {};
            const publicToken = getPublicApiToken();
            if (publicToken) {
                headers['X-Public-Token'] = publicToken;
            }
            const response = await fetch(`/api/chat/recommendations/${this.conversationId}`, { headers });
            const data = await response.json();
            
            if (data.success && data.recommendations) {
                const reco = data.recommendations;
                
                // Pré-remplir le formulaire automatiquement
                if (reco.type_evenement) {
                    const typeSelect = document.getElementById('type_evenement');
                    if (typeSelect) {
                        typeSelect.value = reco.type_evenement;
                        // Animation visuelle
                        typeSelect.style.transition = 'all 0.3s ease';
                        typeSelect.style.background = '#e3f2fd';
                        setTimeout(() => typeSelect.style.background = '', 1000);
                    }
                }
                
                if (reco.nb_invites) {
                    const nbInvitesInput = document.getElementById('nb_invites');
                    if (nbInvitesInput) {
                        nbInvitesInput.value = reco.nb_invites;
                        nbInvitesInput.style.transition = 'all 0.3s ease';
                        nbInvitesInput.style.background = '#e3f2fd';
                        setTimeout(() => nbInvitesInput.style.background = '', 1000);
                    }
                }
                
                // Pré-remplir les infos client
                if (reco.client_nom) {
                    const nomInput = document.getElementById('nom');
                    if (nomInput) {
                        nomInput.value = reco.client_nom;
                        nomInput.style.transition = 'all 0.3s ease';
                        nomInput.style.background = '#e3f2fd';
                        setTimeout(() => nomInput.style.background = '', 1000);
                    }
                }
                
                if (reco.client_email) {
                    const emailInput = document.getElementById('email');
                    if (emailInput) {
                        emailInput.value = reco.client_email;
                        emailInput.style.transition = 'all 0.3s ease';
                        emailInput.style.background = '#e3f2fd';
                        setTimeout(() => emailInput.style.background = '', 1000);
                    }
                }
                
                if (reco.client_telephone) {
                    const telInput = document.getElementById('telephone');
                    if (telInput) {
                        telInput.value = reco.client_telephone;
                        telInput.style.transition = 'all 0.3s ease';
                        telInput.style.background = '#e3f2fd';
                        setTimeout(() => telInput.style.background = '', 1000);
                    }
                }
                
                if (reco.services && reco.services.length > 0) {
                    reco.services.forEach((service, index) => {
                        setTimeout(() => {
                            const checkbox = document.getElementById(`service_${service}`);
                            if (checkbox) {
                                checkbox.checked = true;
                                // Animation visuelle sur le parent
                                const parent = checkbox.closest('.checkbox-item');
                                if (parent) {
                                    parent.style.transition = 'all 0.3s ease';
                                    parent.style.background = '#e3f2fd';
                                    parent.style.borderColor = '#0071e3';
                                    setTimeout(() => {
                                        parent.style.background = '';
                                        parent.style.borderColor = '';
                                    }, 1000);
                                }
                            }
                        }, index * 200);
                    });
                }
                
                // Message de confirmation sans emoji
                this.addMessage("Parfait. Le formulaire a été pré-rempli avec vos informations. Pensez à indiquer la date et les horaires de votre événement dans le formulaire ci-dessus.", 'bot');
                
                // Scroll vers le formulaire après 1 seconde
                setTimeout(() => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 1000);
            }
        } catch (error) {
            console.error('Erreur lors de l\'application automatique:', error);
        }
    }
}

// Initialiser le chat quand la page est chargée
document.addEventListener('DOMContentLoaded', () => {
    window.aiChat = new AIChat();
});
