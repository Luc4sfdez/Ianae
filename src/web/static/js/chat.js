// IANAE MVP - Chat JavaScript con AJAX
class IANAEChat {
    constructor() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.statusText = document.getElementById('statusText');
        this.statusDot = document.querySelector('.status-dot');
        
        this.isConnected = false;
        this.isTyping = false;
        
        this.bindEvents();
        this.checkConnection();
    }
    
    bindEvents() {
        // Enviar mensaje con botón
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enviar mensaje con Enter
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize del input
        this.messageInput.addEventListener('input', () => {
            this.updateSendButton();
        });
    }
    
    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isTyping;
        
        if (this.isTyping) {
            document.getElementById('sendIcon').textContent = '⏳';
        } else if (hasText) {
            document.getElementById('sendIcon').textContent = '📤';
        } else {
            document.getElementById('sendIcon').textContent = '💬';
        }
    }
    
    async checkConnection() {
        try {
            const response = await fetch('/health');
            if (response.ok) {
                this.setStatus('connected', 'Conectado');
                this.isConnected = true;
            } else {
                throw new Error('Server error');
            }
        } catch (error) {
            this.setStatus('error', 'Error de conexión');
            this.isConnected = false;
        }
    }
    
    setStatus(type, text) {
        this.statusText.textContent = text;
        this.statusDot.className = `status-dot ${type}`;
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping || !this.isConnected) return;
        
        // Añadir mensaje del usuario
        this.addMessage('user', message);
        
        // Limpiar input y deshabilitar
        this.messageInput.value = '';
        this.isTyping = true;
        this.updateSendButton();
        
        // Mostrar loading
        this.showLoading(true);
        
        try {
            // Enviar a backend con AJAX
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Añadir respuesta de IANAE
            this.addMessage('ianae', data.response, data.context_info);
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('ianae', 
                `❌ Error de conexión: ${error.message}. Verifica que el servidor esté funcionando.`,
                { error: true }
            );
        } finally {
            this.isTyping = false;
            this.updateSendButton();
            this.showLoading(false);
            this.messageInput.focus();
        }
    }
    
    addMessage(sender, content, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const now = new Date();
        const timeString = now.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        let avatarContent;
        let senderName;
        
        if (sender === 'user') {
            avatarContent = '👤';
            senderName = 'Tú';
        } else {
            avatarContent = '🧠';
            senderName = 'IANAE';
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatarContent}</div>
            <div class="message-content">
                <strong>${senderName}:</strong> ${this.formatMessage(content)}
                ${metadata.context_info ? `<div class="context-info">${metadata.context_info}</div>` : ''}
                <div class="message-time">${timeString}</div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(content) {
        // Formatear mensajes con markdown básico
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }
    
    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.add('show');
        } else {
            this.loadingOverlay.classList.remove('show');
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }
}

// Funciones globales para el HTML
let chatInstance;

function initializeChat() {
    chatInstance = new IANAEChat();
    console.log('🧠 IANAE Chat initialized');
}

async function loadMemoryStats() {
    try {
        const response = await fetch('/memory-stats');
        if (response.ok) {
            const stats = await response.json();
            console.log('Stats recibidas:', stats); // Debug
            
            // Actualizar números reales
            const conceptElement = document.getElementById('conceptCount');
            const relationElement = document.getElementById('relationCount');
            
            if (conceptElement) {
                conceptElement.textContent = stats.concepts || '---';
            }
            if (relationElement) {
                relationElement.textContent = stats.relations || '---';
            }
            
            console.log('Stats actualizadas en UI');
        } else {
            console.error('Error cargando stats:', response.status);
        }
    } catch (error) {
        console.error('Error en loadMemoryStats:', error);
    }
}

// Utilidades adicionales
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        console.log('Copied to clipboard');
    });
}

function downloadChat() {
    const messages = document.querySelectorAll('.message');
    let chatText = '# Chat with IANAE\n\n';
    
    messages.forEach(msg => {
        const sender = msg.classList.contains('user-message') ? 'Usuario' : 'IANAE';
        const content = msg.querySelector('.message-content').textContent;
        const time = msg.querySelector('.message-time').textContent;
        
        chatText += `## ${sender} (${time})\n${content}\n\n`;
    });
    
    const blob = new Blob([chatText], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ianae-chat-${new Date().toISOString().split('T')[0]}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

// Debug helpers
window.IANAE_DEBUG = {
    chat: () => chatInstance,
    sendTest: (msg) => {
        chatInstance.messageInput.value = msg || 'Test message';
        chatInstance.sendMessage();
    },
    clearChat: () => {
        const messages = chatInstance.messagesContainer;
        messages.innerHTML = '';
    }
};