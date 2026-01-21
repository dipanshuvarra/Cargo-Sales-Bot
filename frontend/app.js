// Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// State management
let conversationHistory = [];
let pendingConfirmation = null;
let accumulatedSlots = {};  // Store collected slots
let recognition = null;

// DOM elements
const textInput = document.getElementById('text-input');
const sendBtn = document.getElementById('send-btn');
const voiceBtn = document.getElementById('voice-btn');
const conversationHistoryEl = document.getElementById('conversation-history');
const voiceIndicator = document.getElementById('voice-indicator');
const clearChatBtn = document.getElementById('clear-chat');
const refreshBookingsBtn = document.getElementById('refresh-bookings');
const bookingsListEl = document.getElementById('bookings-list');
const confirmationModal = document.getElementById('confirmation-modal');
const confirmationMessage = document.getElementById('confirmation-message');
const confirmYesBtn = document.getElementById('confirm-yes');
const confirmNoBtn = document.getElementById('confirm-no');
const connectionStatus = document.getElementById('connection-status');

// Initialize Web Speech API
function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            voiceBtn.classList.add('recording');
            voiceIndicator.classList.remove('hidden');
        };

        recognition.onend = () => {
            voiceBtn.classList.remove('recording');
            voiceIndicator.classList.add('hidden');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            textInput.value = transcript;
            sendMessage();
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            voiceBtn.classList.remove('recording');
            voiceIndicator.classList.add('hidden');

            if (event.error === 'no-speech') {
                addMessage('assistant', "I didn't hear anything. Please try again.");
            } else if (event.error === 'not-allowed') {
                addMessage('assistant', "Microphone access is required for voice input. Please enable it in your browser settings.");
            }
        };
    } else {
        console.warn('Speech recognition not supported');
        voiceBtn.disabled = true;
        voiceBtn.title = 'Voice input not supported in this browser';
    }
}

// Add message to conversation
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Parse content for better formatting
    if (typeof content === 'string') {
        // Convert line breaks to paragraphs
        const paragraphs = content.split('\n').filter(p => p.trim());
        contentDiv.innerHTML = paragraphs.map(p => `<p>${escapeHtml(p)}</p>`).join('');
    } else {
        contentDiv.innerHTML = `<p>${escapeHtml(String(content))}</p>`;
    }

    messageDiv.appendChild(contentDiv);
    conversationHistoryEl.appendChild(messageDiv);

    // Smooth scroll to bottom
    setTimeout(() => {
        conversationHistoryEl.scrollTo({
            top: conversationHistoryEl.scrollHeight,
            behavior: 'smooth'
        });
    }, 100);

    // Add to history
    conversationHistory.push({ role, content });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Send message to API
async function sendMessage() {
    const message = textInput.value.trim();
    if (!message) return;

    // Add user message to UI
    addMessage('user', message);
    textInput.value = '';

    try {
        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing';
        typingDiv.innerHTML = '<div class="message-content"><p>...</p></div>';
        conversationHistoryEl.appendChild(typingDiv);

        // Scroll to show typing indicator
        setTimeout(() => {
            conversationHistoryEl.scrollTo({
                top: conversationHistoryEl.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);

        // Call conversation API
        const response = await fetch(`${API_BASE_URL}/conversation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                conversation_history: conversationHistory.slice(-10), // Last 10 messages
                pending_confirmation: pendingConfirmation,
                accumulated_slots: accumulatedSlots
            })
        });

        // Remove typing indicator
        typingDiv.remove();

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        // Update accumulated slots if present
        if (data.accumulated_slots) {
            accumulatedSlots = data.accumulated_slots;
            console.log("Updated slots:", accumulatedSlots);
        }

        // Add assistant response
        addMessage('assistant', data.response);

        // Speak response
        speak(data.response);

        // Handle confirmation
        if (data.needs_confirmation) {
            pendingConfirmation = data.confirmation_data;
            showConfirmationModal(data.response);
        } else {
            pendingConfirmation = null;
        }

        // Refresh bookings if booking-related
        if (['book', 'cancel', 'track'].includes(data.intent)) {
            setTimeout(loadBookings, 500);
        }

        // Update connection status
        updateConnectionStatus(true);

    } catch (error) {
        console.error('Error sending message:', error);

        // Remove typing indicator if exists
        const typingDiv = conversationHistoryEl.querySelector('.typing');
        if (typingDiv) typingDiv.remove();

        addMessage('assistant', 'Sorry, I encountered an error. Please make sure the backend server is running and try again.');
        updateConnectionStatus(false);
    }
}

// Show confirmation modal
function showConfirmationModal(message) {
    confirmationMessage.textContent = message;
    confirmationModal.classList.remove('hidden');
}

// Hide confirmation modal
function hideConfirmationModal() {
    confirmationModal.classList.add('hidden');
}

// Update connection status
function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.textContent = 'Connected';
        connectionStatus.previousElementSibling.style.background = 'var(--success)';
    } else {
        connectionStatus.textContent = 'Disconnected';
        connectionStatus.previousElementSibling.style.background = 'var(--error)';
    }
}

// Load bookings
async function loadBookings() {
    try {
        const response = await fetch(`${API_BASE_URL}/bookings?limit=10`);

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        if (data.bookings && data.bookings.length > 0) {
            bookingsListEl.innerHTML = data.bookings.map(booking => `
                <div class="booking-card">
                    <div class="booking-header">
                        <span class="booking-id">${booking.booking_id}</span>
                        <span class="booking-status ${booking.status}">${booking.status}</span>
                    </div>
                    <div class="booking-details">
                        <div class="booking-route">${booking.origin} → ${booking.destination}</div>
                        <div>${booking.weight}t ${booking.cargo_type}</div>
                        <div>Date: ${booking.shipping_date}</div>
                        <div class="booking-price">$${booking.price.toFixed(2)}</div>
                    </div>
                </div>
            `).join('');
        } else {
            bookingsListEl.innerHTML = `
                <div class="empty-state">
                    <svg width="60" height="60" viewBox="0 0 60 60" fill="none" opacity="0.3">
                        <path d="M30 10L50 20V40L30 50L10 40V20L30 10Z" stroke="currentColor" stroke-width="2"/>
                    </svg>
                    <p>No bookings yet</p>
                </div>
            `;
        }

        updateConnectionStatus(true);

    } catch (error) {
        console.error('Error loading bookings:', error);
        updateConnectionStatus(false);
    }
}

// Text-to-Speech
function speak(text) {
    if (!('speechSynthesis' in window)) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    // Get voices and select a good English one
    let voices = window.speechSynthesis.getVoices();

    // If voices aren't loaded yet, wait for them
    if (voices.length === 0) {
        window.speechSynthesis.onvoiceschanged = () => {
            voices = window.speechSynthesis.getVoices();
            setVoiceAndSpeak(utterance, voices);
        };
    } else {
        setVoiceAndSpeak(utterance, voices);
    }
}

function setVoiceAndSpeak(utterance, voices) {
    // Prefer Microsoft Zira (common good Windows voice) or Google US English
    const preferredVoice = voices.find(voice =>
        voice.name.includes('Zira') ||
        voice.name.includes('Google US English') ||
        (voice.lang === 'en-US' && voice.name.includes('Female'))
    ) || voices.find(voice => voice.lang === 'en-US');

    if (preferredVoice) {
        utterance.voice = preferredVoice;
    }

    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    window.speechSynthesis.speak(utterance);
}

// Clear conversation
function clearConversation() {
    conversationHistory = [];
    pendingConfirmation = null;
    accumulatedSlots = {};

    conversationHistoryEl.innerHTML = `
        <div class="message assistant">
            <div class="message-content">
                <p>👋 Hello! I'm your air cargo booking assistant. I can help you:</p>
                <ul>
                    <li>Get price quotes</li>
                    <li>Create bookings</li>
                    <li>Track shipments</li>
                    <li>Cancel bookings</li>
                </ul>
                <p>Try saying: <em>"I need a quote from New York to London for 5 tonnes of general cargo"</em></p>
            </div>
        </div>
    `;
}

// Check API health
async function checkHealth() {
    try {
        const response = await fetch('http://localhost:8000/health');
        if (response.ok) {
            updateConnectionStatus(true);
        } else {
            updateConnectionStatus(false);
        }
    } catch (error) {
        updateConnectionStatus(false);
    }
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);

textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

voiceBtn.addEventListener('click', () => {
    if (recognition) {
        if (voiceBtn.classList.contains('recording')) {
            recognition.stop();
        } else {
            recognition.start();
        }
    }
});

clearChatBtn.addEventListener('click', () => {
    if (confirm('Clear conversation history?')) {
        clearConversation();
    }
});

refreshBookingsBtn.addEventListener('click', loadBookings);

confirmYesBtn.addEventListener('click', () => {
    hideConfirmationModal();
    // Send confirmation
    textInput.value = 'yes, confirm';
    sendMessage();
});

confirmNoBtn.addEventListener('click', () => {
    hideConfirmationModal();
    pendingConfirmation = null;
    // Send cancellation
    textInput.value = 'no, cancel';
    sendMessage();
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initSpeechRecognition();
    loadBookings();
    checkHealth();

    // Check health every 30 seconds
    setInterval(checkHealth, 30000);

    // Focus input
    textInput.focus();
});

// Handle modal click outside
confirmationModal.addEventListener('click', (e) => {
    if (e.target === confirmationModal) {
        hideConfirmationModal();
        pendingConfirmation = null;
    }
});
