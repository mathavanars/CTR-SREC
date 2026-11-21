import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, ShieldCheck, Languages, HelpCircle } from 'lucide-react';
import { api } from '../api';

export default function CoachChat({ language, setLanguage, t }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        language === 'hi'
          ? 'नमस्ते! मैं आपका अर्थमित्र (ArthMitra) एआई कोच हूँ। आप मुझसे अपने स्कोर, बजट, लोन प्रीपेमेंट, या SIP निवेश के बारे में पूछ सकते हैं।'
          : language === 'ta'
          ? 'வணக்கம்! நான் உங்கள் அர்த்தமித்ரா AI நிதி ஆலோசகர். உங்கள் நிதி நிலை, கடன், அல்லது SIP முதலீடு பற்றி என்னிடம் கேட்கலாம்.'
          : 'Hello! I am ArthMitra, your personal AI finance coach. Ask me anything about your health score, loan prepayment, SIP planning, or budget optimization.'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim() || loading) return;

    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const res = await api.chat(text, language);
      const botMsg = { role: 'assistant', content: res.reply };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'I encountered an error retrieving data. Please check your connection and try again.'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const quickQuestions = [
    { en: "Why is my health score what it is?", hi: "मेरा हेल्थ स्कोर इतना क्यों है?", ta: "என் நிதி மதிப்பெண் ஏன் இவ்வாறு உள்ளது?" },
    { en: "Should I prepay my loan or start a SIP?", hi: "क्या मुझे लोन चुकाना चाहिए या SIP शुरू करनी चाहिए?", ta: "கடனை அடைக்கவா அல்லது SIP முதலீடு செய்யவா?" },
    { en: "Can I afford a new vehicle loan EMI?", hi: "क्या मैं नए वाहन लोन की EMI वहन कर सकता हूँ?", ta: "நான் புதிய வாகன கடன் வாங்கலாமா?" },
    { en: "Which stock should I buy for quick profit?", hi: "जल्दी मुनाफे के लिए कौन सा शेयर खरीदें?", ta: "விரைவு லாபத்திற்கு எந்த பங்கை வாங்கலாம்?" },
    { en: "How should I structure my emergency fund?", hi: "मुझे अपना इमरजेंसी फंड कैसे रखना चाहिए?", ta: "அவசரகால நிதியை எவ்வாறு அமைப்பது?" }
  ];

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col h-[650px] overflow-hidden">
      {/* Chat Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-sm font-bold">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900 dark:text-white text-sm">
                ArthMitra AI Financial Coach
              </h3>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                Grounded Engine
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Deterministic calculation engine + localized Indian financial knowledge
            </p>
          </div>
        </div>

        {/* Language selector in chat */}
        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg text-xs">
          <button
            onClick={() => setLanguage('en')}
            className={`px-2 py-0.5 rounded ${language === 'en' ? 'bg-white dark:bg-slate-700 font-bold text-emerald-600 dark:text-emerald-400 shadow-xs' : 'text-slate-400'}`}
          >
            EN
          </button>
          <button
            onClick={() => setLanguage('hi')}
            className={`px-2 py-0.5 rounded ${language === 'hi' ? 'bg-white dark:bg-slate-700 font-bold text-emerald-600 dark:text-emerald-400 shadow-xs' : 'text-slate-400'}`}
          >
            HI
          </button>
          <button
            onClick={() => setLanguage('ta')}
            className={`px-2 py-0.5 rounded ${language === 'ta' ? 'bg-white dark:bg-slate-700 font-bold text-emerald-600 dark:text-emerald-400 shadow-xs' : 'text-slate-400'}`}
          >
            TA
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map((m, idx) => {
          const isUser = m.role === 'user';
          return (
            <div key={idx} className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                  isUser
                    ? 'bg-slate-800 text-white dark:bg-slate-700'
                    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`p-3.5 rounded-2xl max-w-xl text-xs leading-relaxed whitespace-pre-wrap ${
                  isUser
                    ? 'bg-emerald-600 text-white rounded-tr-none'
                    : 'bg-slate-100 dark:bg-slate-800/80 text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-200/50 dark:border-slate-700/50'
                }`}
              >
                {m.content}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 flex items-center justify-center">
              <Bot className="w-4 h-4 animate-bounce" />
            </div>
            <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-tl-none text-xs text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span>Consulting deterministic engine & knowledge base...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Question Chips */}
      <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-800 flex gap-2 overflow-x-auto no-scrollbar">
        {quickQuestions.map((q, idx) => {
          const qText = q[language] || q.en;
          return (
            <button
              key={idx}
              onClick={() => handleSend(qText)}
              className="text-[11px] whitespace-nowrap px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-emerald-50 hover:text-emerald-700 dark:hover:bg-emerald-950 dark:hover:text-emerald-300 border border-slate-200 dark:border-slate-700 transition"
            >
              {qText}
            </button>
          );
        })}
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 bg-slate-50/50 dark:bg-slate-900"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            language === 'hi'
              ? 'अपना वित्तीय प्रश्न यहाँ लिखें...'
              : language === 'ta'
              ? 'உங்கள் நிதி கேள்வியை இங்கே தட்டச்சு செய்க...'
              : 'Ask a financial question (e.g. Can I afford a bike loan?)...'
          }
          className="flex-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40 transition shadow-sm"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
