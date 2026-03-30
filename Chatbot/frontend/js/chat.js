/**
 * BankBot AI - Chat Application Logic
 * Handles chat messaging, conversation management, and UI interactions.
 */

const API_BASE = window.location.origin;
let currentConversationId = null;
let isProcessing = false;

// ==================== AUTH CHECK ====================
const token = localStorage.getItem('bankbot_token');
const user = JSON.parse(localStorage.getItem('bankbot_user') || '{}');

if (!token || !user.id) {
    window.location.href = '/';
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
    setupUserInfo();
    loadConversations();
    setupEventListeners();
});

function setupUserInfo() {
    const initials = (user.full_name || 'U').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    document.getElementById('userAvatar').textContent = initials;
    document.getElementById('userName').textContent = user.full_name || user.username;
    document.getElementById('userRole').textContent = `${user.role} • ${user.department || ''}`;
}

function setupEventListeners() {
    // Send message
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    
    // Textarea handling
    const input = document.getElementById('chatInput');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    input.addEventListener('input', autoResize);
    
    // New chat
    document.getElementById('newChatBtn').addEventListener('click', startNewChat);
    
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', logout);
    
    // Quick actions
    document.querySelectorAll('.quick-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('chatInput').value = btn.dataset.query;
            sendMessage();
        });
    });
    
    // Mobile menu toggle
    document.getElementById('menuToggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
    });
}

function autoResize() {
    const el = document.getElementById('chatInput');
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// ==================== API CALLS ====================
async function apiCall(endpoint, method = 'GET', body = null) {
    const opts = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };
    if (body) opts.body = JSON.stringify(body);
    
    const res = await fetch(`${API_BASE}${endpoint}`, opts);
    if (res.status === 401) {
        localStorage.removeItem('bankbot_token');
        localStorage.removeItem('bankbot_user');
        window.location.href = '/';
        return null;
    }
    return res.json();
}

// ==================== CONVERSATIONS ====================
async function loadConversations() {
    const data = await apiCall('/api/chat/conversations');
    if (!data) return;
    
    const list = document.getElementById('conversationsList');
    list.innerHTML = '';
    
    if (data.conversations.length === 0) {
        list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-tertiary);font-size:0.813rem;">No conversations yet.<br>Start a new one!</div>';
        return;
    }
    
    data.conversations.forEach(conv => {
        const div = document.createElement('div');
        div.className = `conv-item${conv.id === currentConversationId ? ' active' : ''}`;
        div.innerHTML = `
            <span class="conv-icon">💬</span>
            <span class="conv-title">${escapeHtml(conv.title)}</span>
            <span class="conv-delete" data-id="${conv.id}" title="Delete">✕</span>
        `;
        div.addEventListener('click', (e) => {
            if (!e.target.classList.contains('conv-delete')) {
                loadConversation(conv.id);
            }
        });
        div.querySelector('.conv-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });
        list.appendChild(div);
    });
}

async function loadConversation(convId) {
    currentConversationId = convId;
    const data = await apiCall(`/api/chat/history/${convId}`);
    if (!data) return;
    
    const container = document.getElementById('chatMessages');
    container.innerHTML = '';
    
    // Hide welcome screen
    const welcome = document.getElementById('welcomeScreen');
    if (welcome) welcome.remove();
    
    data.messages.forEach(msg => {
        appendMessage(msg.role === 'user' ? 'user' : 'bot', msg.content, msg.sources, msg.confidence, msg.category);
    });
    
    scrollToBottom();
    loadConversations(); // refresh active state
    
    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('open');
}

function startNewChat() {
    currentConversationId = null;
    const container = document.getElementById('chatMessages');
    container.innerHTML = `
        <div class="welcome-screen" id="welcomeScreen">
            <div class="welcome-icon">🏦</div>
            <h2>Welcome to BankBot AI</h2>
            <p>Your intelligent banking knowledge companion. Ask me anything about banking policies, procedures, compliance requirements, and product guidelines.</p>
            <div class="quick-actions">
                <button class="quick-action-btn" data-query="What is the KYC process for opening a savings account?">
                    <span class="qa-icon">📋</span><span>KYC process for savings account</span>
                </button>
                <button class="quick-action-btn" data-query="What are the RBI guidelines for NPA classification?">
                    <span class="qa-icon">📊</span><span>RBI NPA classification guidelines</span>
                </button>
                <button class="quick-action-btn" data-query="How to handle a credit card dispute?">
                    <span class="qa-icon">💳</span><span>Credit card dispute handling</span>
                </button>
                <button class="quick-action-btn" data-query="What are the NEFT, RTGS, and IMPS limits?">
                    <span class="qa-icon">📱</span><span>NEFT/RTGS/IMPS limits</span>
                </button>
                <button class="quick-action-btn" data-query="Explain the Anti-Money Laundering policy">
                    <span class="qa-icon">🔒</span><span>AML policy overview</span>
                </button>
                <button class="quick-action-btn" data-query="What is the home loan eligibility criteria?">
                    <span class="qa-icon">🏠</span><span>Home loan eligibility</span>
                </button>
            </div>
        </div>
    `;
    // Re-attach quick action listeners
    document.querySelectorAll('.quick-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('chatInput').value = btn.dataset.query;
            sendMessage();
        });
    });
    document.getElementById('chatTitle').textContent = 'Banking Knowledge Assistant';
    document.getElementById('sidebar').classList.remove('open');
}

async function deleteConversation(convId) {
    await apiCall(`/api/chat/conversations/${convId}`, 'DELETE');
    if (currentConversationId === convId) startNewChat();
    loadConversations();
}

// ==================== MESSAGING ====================
async function sendMessage() {
    if (isProcessing) return;
    
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    
    // Hide welcome screen
    const welcome = document.getElementById('welcomeScreen');
    if (welcome) welcome.remove();
    
    // Show user message
    appendMessage('user', message);
    input.value = '';
    input.style.height = 'auto';
    
    // Show typing indicator
    showTypingIndicator();
    isProcessing = true;
    document.getElementById('sendBtn').disabled = true;
    
    try {
        const data = await apiCall('/api/chat', 'POST', {
            message,
            conversation_id: currentConversationId
        });
        
        if (data) {
            currentConversationId = data.conversation_id;
            removeTypingIndicator();
            appendMessage('bot', data.response, data.sources, data.confidence, data.category);
            loadConversations();
        }
    } catch (err) {
        removeTypingIndicator();
        appendMessage('bot', '⚠️ Sorry, an error occurred while processing your request. Please try again.');
    } finally {
        isProcessing = false;
        document.getElementById('sendBtn').disabled = false;
        document.getElementById('chatInput').focus();
    }
}

// ==================== MESSAGE RENDERING ====================
function appendMessage(type, content, sources = [], confidence = 0, category = '') {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `message ${type === 'user' ? 'user-message' : 'bot-message'}`;
    
    const avatarText = type === 'user' ? (user.full_name || 'U').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : '🏦';
    
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        const tags = sources.map(s => `<span class="source-tag" title="Category: ${s.category || ''} | Similarity: ${(s.similarity * 100).toFixed(0)}%">📄 ${escapeHtml(s.title || s.doc_id)}</span>`).join('');
        sourcesHtml = `<div class="message-sources">${tags}</div>`;
    }
    
    let metaHtml = '';
    if (type === 'bot' && confidence > 0) {
        const confClass = confidence >= 0.6 ? 'high' : confidence >= 0.4 ? 'medium' : 'low';
        const confLabel = confidence >= 0.6 ? 'High' : confidence >= 0.4 ? 'Medium' : 'Low';
        metaHtml = `<div class="message-meta">
            <span class="confidence-indicator"><span class="confidence-dot confidence-${confClass}"></span> ${confLabel} confidence (${(confidence * 100).toFixed(0)}%)</span>
            ${category ? `<span>📁 ${category}</span>` : ''}
        </div>`;
    }
    
    div.innerHTML = `
        <div class="message-avatar">${avatarText}</div>
        <div class="message-body">
            <div class="message-content">${renderMarkdown(content)}</div>
            ${sourcesHtml}
            ${metaHtml}
        </div>
    `;
    
    container.appendChild(div);
    scrollToBottom();
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.id = 'typingIndicator';
    div.innerHTML = `
        <div class="message-avatar">🏦</div>
        <div class="typing-dots"><span></span><span></span><span></span></div>
    `;
    container.appendChild(div);
    scrollToBottom();
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    container.scrollTop = container.scrollHeight;
}

// ==================== UTILITIES ====================
function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Code
    html = html.replace(/`(.+?)`/g, '<code>$1</code>');
    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    // Unordered lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gs, (match) => `<ul>${match}</ul>`);
    // Fix nested ul
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = `<p>${html}</p>`;
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p><h3>/g, '<h3>');
    html = html.replace(/<\/h3><\/p>/g, '</h3>');
    html = html.replace(/<p><ul>/g, '<ul>');
    html = html.replace(/<\/ul><\/p>/g, '</ul>');
    html = html.replace(/<p><blockquote>/g, '<blockquote>');
    html = html.replace(/<\/blockquote><\/p>/g, '</blockquote>');
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function logout() {
    localStorage.removeItem('bankbot_token');
    localStorage.removeItem('bankbot_user');
    window.location.href = '/';
}
