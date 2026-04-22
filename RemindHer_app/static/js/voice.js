/**
 * ARIA — Adaptive Reminder & Intelligence Assistant
 * Intelligent voice assistant powered by Claude AI + Web Speech API
 */

class VoiceAssistant {
  constructor() {
    // ── Speech Recognition ────────────────────────────────────────────────
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.supported = !!SR;

    if (this.supported) {
      this.recognition = new SR();
      this.recognition.continuous = false;     // prevents Chrome silent abort bug
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.recognition.onstart  = () => { this.isListening = true;  this._setState('listening'); };
      this.recognition.onend    = () => { this.isListening = false; this._setState('idle'); };
      this.recognition.onerror  = (e) => this._handleRecognitionError(e);
      this.recognition.onresult = (e) => this._handleResult(e);
    }

    // ── Speech Synthesis ──────────────────────────────────────────────────
    this.synth = window.speechSynthesis;
    this.voice = null;
    this._loadVoices();
    if (this.synth.onvoiceschanged !== undefined) {
      this.synth.onvoiceschanged = () => this._loadVoices();
    }

    // ── State ─────────────────────────────────────────────────────────────
    this.isListening  = false;
    this.isSpeaking   = false;
    this.isProcessing = false;  // waiting for API response
    this.conversationActive = false;

    // ── Callbacks (set by UI code) ────────────────────────────────────────
    this.onTranscript  = null;   // (text, isFinal) => void
    this.onStateChange = null;   // (state) => void
    this.onResponse    = null;   // (responseText) => void
  }

  // ── Voice loading ─────────────────────────────────────────────────────────
  _loadVoices() {
    const voices = this.synth.getVoices();
    this.voice =
      voices.find(v => v.name === 'Google UK English Male') ||
      voices.find(v => v.name === 'Google US English')      ||
      voices.find(v => v.name === 'Daniel')                 ||
      voices.find(v => v.lang === 'en-US' && !v.localService) ||
      voices.find(v => v.lang === 'en-US') ||
      voices[0] || null;
  }

  // ── Public: Start listening ───────────────────────────────────────────────
  startListening() {
    if (!this.supported) {
      this._showFallback();
      return;
    }
    if (this.isListening || this.isProcessing) return;
    if (this.isSpeaking) this.synth.cancel();

    try {
      this.recognition.start();
    } catch (err) {
      console.error('[ARIA] Could not start recognition:', err);
      this._setState('error');
    }
  }

  stopListening() {
    if (this.isListening) this.recognition.stop();
  }

  // ── Public: Speak ─────────────────────────────────────────────────────────
  speak(text, callback = null) {
    if (!text || !this.synth) return;

    // CRITICAL: cancel before speaking to clear queue
    this.synth.cancel();

    this.isSpeaking = true;
    this._setState('speaking');

    // Clean text for speech: remove any markdown symbols that slipped through
    const cleanText = text
      .replace(/[*_~`#]/g, '')
      .replace(/\n+/g, '. ')
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.voice  = this.voice;
    utterance.rate   = 1.05;
    utterance.pitch  = 0.95;
    utterance.volume = 1.0;

    utterance.onend   = () => { this.isSpeaking = false; this._setState('idle'); if (callback) callback(); };
    utterance.onerror = () => { this.isSpeaking = false; this._setState('idle'); };

    this.synth.speak(utterance);
  }

  // ── Handle recognition result ─────────────────────────────────────────────
  _handleResult(event) {
    let interim = '', final = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += transcript;
      else interim += transcript;
    }

    if (this.onTranscript) {
      this.onTranscript(final || interim, !!final);
    }

    if (final) {
      this._sendToAI(final.trim());
    }
  }

  // ── Send message to Claude AI backend ────────────────────────────────────
  async _sendToAI(userText) {
    if (!userText) return;

    this._setState('processing');
    this.isProcessing = true;

    try {
      const response = await fetch('/voice/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCSRF()
        },
        body: JSON.stringify({ message: userText })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();

      // Display response in UI
      if (this.onResponse) this.onResponse(data.message);

      // Speak the response, then execute action
      this.speak(data.message, () => {
        this._executeAction(data);
      });

    } catch (err) {
      console.error('[ARIA] API error:', err);
      this.speak("Sorry, I had trouble connecting. Please check your internet and try again.");
    } finally {
      this.isProcessing = false;
    }
  }

  // ── Execute app action after speaking ────────────────────────────────────
  _executeAction(data) {
    if (!data.action) return;

    switch (data.action) {
      case 'navigate':
        if (data.url) {
          setTimeout(() => window.location.href = data.url, 300);
        }
        break;
      case 'redirect':
        if (data.url) {
          setTimeout(() => window.open(data.url, '_blank'), 500);
        }
        break;
      case 'alert':
        if (data.message) {
          this._showToast(data.message);
        }
        break;
      case 'reload':
        setTimeout(() => window.location.reload(), 500);
        break;
    }
  }

  // ── Public: Send text message (for fallback/chips) ────────────────────────
  sendText(text) {
    if (this.onTranscript) this.onTranscript(text, true);
    this._sendToAI(text);
  }

  // ── Public: Clear conversation history ───────────────────────────────────
  clearHistory() {
    fetch('/voice/clear/', {
      method: 'POST',
      headers: { 'X-CSRFToken': this._getCSRF() }
    });
    this.speak("Sure, I've cleared our conversation. Fresh start!");
  }

  // ── Error handling ────────────────────────────────────────────────────────
  _handleRecognitionError(event) {
    this.isListening = false;
    this._setState('error');

    const messages = {
      'not-allowed': "I need microphone access to hear you. Please allow it in your browser settings, then refresh.",
      'no-speech':   "I didn't hear anything. Tap the button and try speaking again.",
      'network':     "Network error. Please check your connection.",
      'aborted':     null  // user stopped, no message needed
    };

    const msg = messages[event.error];
    if (msg) this.speak(msg);
  }

  _showFallback() {
    const fb = document.getElementById('voice-fallback');
    if (fb) fb.style.display = 'block';
    this.speak("Voice input isn't supported in your browser. You can type your message instead.");
  }

  _showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'voice-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  // ── State management ──────────────────────────────────────────────────────
  _setState(state) {
    this.state = state;
    if (this.onStateChange) this.onStateChange(state);
    document.dispatchEvent(new CustomEvent('voiceStateChange', { detail: { state } }));
  }

  _getCSRF() {
    return document.cookie.split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1] || '';
  }
}

// ── Global instance ───────────────────────────────────────────────────────────
window.ARIA = new VoiceAssistant();

// ── UI Controller ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const btn         = document.getElementById('voice-btn');
  const statusEl    = document.getElementById('voice-status');
  const transcriptEl = document.getElementById('voice-transcript');
  const responseEl  = document.getElementById('voice-response');
  const waveEl      = document.getElementById('voice-wave');

  // State → UI mapping
  const STATE_MAP = {
    idle:       { icon: '🎤', label: 'Tap to speak',    btnClass: 'voice-btn--idle' },
    listening:  { icon: '⏹',  label: 'Listening...',    btnClass: 'voice-btn--listening' },
    speaking:   { icon: '🔊', label: 'Speaking...',     btnClass: 'voice-btn--speaking' },
    processing: { icon: '⏳', label: 'Thinking...',     btnClass: 'voice-btn--processing' },
    error:      { icon: '⚠️', label: 'Error — try again', btnClass: 'voice-btn--error' }
  };

  document.addEventListener('voiceStateChange', (e) => {
    const state = e.detail.state;
    const ui = STATE_MAP[state] || STATE_MAP.idle;

    if (btn) {
      btn.className = `voice-btn ${ui.btnClass}`;
      const iconEl = btn.querySelector('.btn-icon');
      if (iconEl) iconEl.textContent = ui.icon;
    }
    if (statusEl) statusEl.textContent = ui.label;
    if (waveEl) {
      waveEl.classList.toggle('active', state === 'listening' || state === 'speaking');
    }
  });

  // Live transcript display
  window.ARIA.onTranscript = (text, isFinal) => {
    if (transcriptEl) {
      transcriptEl.textContent = text;
      transcriptEl.className = isFinal ? 'transcript final' : 'transcript interim';
    }
  };

  // AI response display
  window.ARIA.onResponse = (text) => {
    if (responseEl) {
      responseEl.textContent = text;
      responseEl.style.opacity = '1';
    }
  };

  // Button: push-to-talk
  if (btn) {
    btn.addEventListener('click', () => {
      if (window.ARIA.isListening) window.ARIA.stopListening();
      else window.ARIA.startListening();
    });
  }

  // Fallback text input
  const fallbackInput = document.getElementById('fallback-input');
  const fallbackBtn   = document.getElementById('fallback-send');
  if (fallbackBtn) {
    fallbackBtn.addEventListener('click', () => {
      const text = fallbackInput?.value?.trim();
      if (text) {
        window.ARIA.sendText(text);
        if (fallbackInput) fallbackInput.value = '';
      }
    });
  }
  if (fallbackInput) {
    fallbackInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') fallbackBtn?.click();
    });
  }

  // Show fallback if speech not supported
  if (!window.ARIA.supported) {
    document.getElementById('voice-fallback')?.style && (document.getElementById('voice-fallback').style.display = 'block');
  }

  // Greeting on voice page
  if (window.location.pathname === '/voice/' || window.location.pathname.startsWith('/voice/')) {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    setTimeout(() => {
      // Ask AI for personalized greeting
      window.ARIA.sendText(`${greeting}! Give me a quick personalized greeting and tell me if there's anything important in my app I should know about right now.`);
    }, 800);
  }
});

// Quick command function for chips/buttons
function quickCommand(text) {
  window.ARIA.sendText(text);
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie) {
        document.cookie.split(';').forEach(cookie => {
            const [key, value] = cookie.trim().split('=');
            if (key === name) cookieValue = decodeURIComponent(value);
        });
    }
    return cookieValue;
}

// Cooking timer class
class CookingTimer {
    constructor(endISO, displayEl) {
        this.end = new Date(endISO);
        this.el = displayEl;
        this.interval = null;
    }
    
    start(onDone) {
        this.interval = setInterval(() => {
            const rem = this.end - Date.now();
            if (rem <= 0) {
                clearInterval(this.interval);
                this.el.textContent = '00:00';
                this.el.classList.add('done');
                if (window.ARIA) window.ARIA.speak("Time is up! Your cooking step is complete.");
                if (onDone) onDone();
                return;
            }
            
            const m = Math.floor(rem / 60000);
            const s = Math.floor((rem % 60000) / 1000);
            this.el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        }, 1000);
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VoiceAssistant, CookingTimer, quickCommand, getCookie };
}
