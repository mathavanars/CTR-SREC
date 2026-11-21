/**
 * ArthMitra - AI Financial Coach Chat Page Module
 * Indian personal finance intelligence, streaming text reveal, suggested prompt chips, auto-scroll & safe rendering
 */

import { apiRequest } from '../api.js';
import { icons } from '../assets/icons.js';
import { sanitizeHTML, showToast, renderSkeletonCards } from '../ui.js';

let chatMessages = [];
let isGenerating = false;

const SUGGESTED_PROMPTS = [
  'How can I save tax under the New vs Old Tax Regime for FY 2024-25?',
  'Should I prepay my SBI Home Loan or invest in a Nifty 50 Index Fund?',
  'Am I saving enough for an emergency buffer covering 6 months?',
  'Review my current asset allocation split between Equity, Debt, and Gold',
  'What are the advantages of NPS Section 80CCD(1B) additional ₹50,000 deduction?'
];

export async function render(container) {
  isGenerating = false;

  container.innerHTML = `
    <div class="flex flex-col gap-6" aria-busy="true">
      <div class="skeleton-card" style="height: 500px;"></div>
    </div>
  `;

  const { data, error } = await apiRequest('/chat/history');
  chatMessages = (data && data.length > 0) ? data : [
    {
      id: 'c-welcome',
      sender: 'assistant',
      text: 'Namaste! I am ArthMitra, your personal AI Financial Planning Assistant. How can I help optimize your investments, tax deductions, or loan repayment strategies today?',
      timestamp: new Date().toISOString()
    }
  ];

  container.innerHTML = `
    <div class="flex flex-col gap-4">
      
      <!-- Top Title Strip -->
      <div class="flex justify-between items-center">
        <div>
          <h1>AI Financial Coach</h1>
          <p class="text-secondary">Specialized guidance in Indian taxation, mutual funds, provident funds & liabilities</p>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" id="btn-clear-chat">
          ${icons.trash(14)}
          <span>Clear Chat</span>
        </button>
      </div>

      <!-- Main Chat Container -->
      <div class="chat-container">
        
        <!-- Header -->
        <div class="chat-header">
          <div class="flex items-center gap-3">
            <div class="user-avatar-sm" style="background: linear-gradient(135deg, #2563EB, #1D4ED8);">
              ${icons.bot(18)}
            </div>
            <div>
              <strong class="text-sm text-primary block">ArthMitra Coach</strong>
              <small class="text-success font-medium flex items-center gap-1">
                <span style="width: 7px; height: 7px; border-radius: 50%; background-color: var(--color-success); display: inline-block;"></span>
                Online & Ready
              </small>
            </div>
          </div>
          <span class="badge badge-neutral">Trained on Indian Finance & Tax Slabs</span>
        </div>

        <!-- Scrollable Messages Feed -->
        <div class="chat-messages" id="chat-messages-feed" role="log" aria-live="polite">
          ${renderMessageList(chatMessages)}
        </div>

        <!-- Suggested Prompt Chips -->
        <div class="chat-prompt-chips">
          ${SUGGESTED_PROMPTS.map(p => `
            <button type="button" class="prompt-chip" data-prompt="${sanitizeHTML(p)}">
              ${sanitizeHTML(p)}
            </button>
          `).join('')}
        </div>

        <!-- Message Input Bar -->
        <div class="chat-input-area">
          <textarea
            id="chat-textarea"
            class="chat-textarea"
            placeholder="Ask about tax saving, mutual funds, loan prepayments, or retirement... (Enter to send, Shift+Enter for new line)"
            rows="1"
            aria-label="Your financial question"
          ></textarea>
          <button type="button" class="btn btn-primary" id="btn-send-chat" aria-label="Send message">
            ${icons.send(18)}
            <span class="no-mobile">Send</span>
          </button>
        </div>

      </div>

    </div>
  `;

  const messagesFeed = container.querySelector('#chat-messages-feed');
  const textarea = container.querySelector('#chat-textarea');
  const sendBtn = container.querySelector('#btn-send-chat');

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesFeed.scrollTop = messagesFeed.scrollHeight;
  };
  scrollToBottom();

  // Send message action
  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || textarea.value).trim();
    if (!text || isGenerating) return;

    textarea.value = '';
    textarea.style.height = '48px';

    // 1. Append user bubble
    const userMsg = {
      id: 'c-' + Date.now(),
      sender: 'user',
      text,
      timestamp: new Date().toISOString()
    };
    chatMessages.push(userMsg);
    messagesFeed.insertAdjacentHTML('beforeend', renderSingleMessage(userMsg));
    scrollToBottom();

    // 2. Append typing indicator bubble
    isGenerating = true;
    sendBtn.disabled = true;
    const typingId = 'typing-bubble';
    messagesFeed.insertAdjacentHTML('beforeend', `
      <div class="chat-bubble chat-bubble-assistant" id="${typingId}">
        <div class="user-avatar-sm" style="background: linear-gradient(135deg, #2563EB, #1D4ED8);">${icons.bot(16)}</div>
        <div class="chat-bubble-content">
          <div class="typing-dots">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    `);
    scrollToBottom();

    // 3. API Call
    const { data: resData, error: resErr } = await apiRequest('/chat/message', {
      method: 'POST',
      body: JSON.stringify({ message: text })
    });

    // Remove typing indicator
    container.querySelector(`#${typingId}`)?.remove();
    isGenerating = false;
    sendBtn.disabled = false;

    if (resErr) {
      showToast({ title: 'AI Error', message: resErr, type: 'danger' });
      messagesFeed.insertAdjacentHTML('beforeend', `
        <div class="chat-bubble chat-bubble-assistant">
          <div class="user-avatar-sm" style="background: #EF4444;">!</div>
          <div class="chat-bubble-content" style="border-color: var(--color-danger);">
            <p class="text-danger font-medium">Failed to reach the AI financial coach.</p>
            <button type="button" class="btn btn-sm btn-outline mt-2 btn-retry-msg" data-text="${sanitizeHTML(text)}">
              ${icons.refresh(14)}
              <span>Retry Question</span>
            </button>
          </div>
        </div>
      `);
      container.querySelector('.btn-retry-msg')?.addEventListener('click', (e) => {
        const retryText = e.currentTarget.getAttribute('data-text');
        handleSendMessage(retryText);
      });
      scrollToBottom();
      return;
    }

    // 4. Streaming-style progressive reveal
    const fullReply = resData.reply || 'I could not generate a response. Please try again.';
    const botMsgId = 'msg-' + Date.now();
    messagesFeed.insertAdjacentHTML('beforeend', `
      <div class="chat-bubble chat-bubble-assistant">
        <div class="user-avatar-sm" style="background: linear-gradient(135deg, #2563EB, #1D4ED8);">${icons.bot(16)}</div>
        <div class="chat-bubble-content" id="${botMsgId}"></div>
      </div>
    `);

    const botContentEl = container.querySelector(`#${botMsgId}`);
    let charIndex = 0;
    const chunkSize = 4;
    const streamTimer = setInterval(() => {
      charIndex += chunkSize;
      const currentSlice = fullReply.slice(0, charIndex);
      botContentEl.innerHTML = formatMarkdownSafely(currentSlice);
      scrollToBottom();

      if (charIndex >= fullReply.length) {
        clearInterval(streamTimer);
        chatMessages.push({
          id: botMsgId,
          sender: 'assistant',
          text: fullReply,
          timestamp: new Date().toISOString()
        });
      }
    }, 20);
  };

  // Click & Keydown listeners
  sendBtn.addEventListener('click', () => handleSendMessage());

  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Prompt chips
  container.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      handleSendMessage(prompt);
    });
  });

  // Clear chat
  container.querySelector('#btn-clear-chat')?.addEventListener('click', () => {
    chatMessages = [
      {
        id: 'c-welcome-2',
        sender: 'assistant',
        text: 'Chat history cleared. How can I assist you with your finances today?',
        timestamp: new Date().toISOString()
      }
    ];
    messagesFeed.innerHTML = renderMessageList(chatMessages);
    showToast({ title: 'Chat Reset', message: 'Chat history has been cleared.', type: 'info' });
  });
}

function renderMessageList(messages) {
  return messages.map(msg => renderSingleMessage(msg)).join('');
}

function renderSingleMessage(msg) {
  const isUser = msg.sender === 'user';
  return `
    <div class="chat-bubble ${isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}">
      ${!isUser ? `<div class="user-avatar-sm" style="background: linear-gradient(135deg, #2563EB, #1D4ED8);">${icons.bot(16)}</div>` : ''}
      <div class="chat-bubble-content">
        ${formatMarkdownSafely(msg.text)}
      </div>
    </div>
  `;
}

/**
 * Format markdown bullet points, bolding, and newlines safely without raw unescaped innerHTML
 */
function formatMarkdownSafely(text) {
  if (!text) return '';
  // Step 1: Escape raw HTML
  let clean = sanitizeHTML(text);

  // Step 2: Bold (**text**)
  clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Step 3: Bullet points (• or * )
  clean = clean.replace(/(?:^|\n)[•*]\s*(.*?)(?=\n|$)/g, '<li>$1</li>');
  clean = clean.replace(/(<li>.*?<\/li>)/g, '<ul>$1</ul>');
  // Combine adjacent <ul> tags
  clean = clean.replace(/<\/ul>\s*<ul>/g, '');

  // Step 4: Numbered list (1. text)
  clean = clean.replace(/(?:^|\n)\d+\.\s*(.*?)(?=\n|$)/g, '<li>$1</li>');

  // Step 5: Paragraphs on double newline
  const paragraphs = clean.split('\n\n').map(p => {
    if (p.startsWith('<ul>') || p.startsWith('<ol>')) return p;
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  });

  return paragraphs.join('');
}

export function destroy() {
  isGenerating = false;
}
