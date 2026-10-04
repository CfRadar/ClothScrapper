import React, { useState } from 'react';
import { MessageSquare, Send, Bot, User, Loader2 } from 'lucide-react';
import type { ChatMessage, PlatformKeywords } from '../types';
import { chat as sendChatMessage } from '../api';

interface ChatBlockProps {
  runId: string;
  onPatchKeywords: (patches: PlatformKeywords[]) => void;
}

export const ChatBlock: React.FC<ChatBlockProps> = ({ runId, onPatchKeywords }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const userText = input.trim();
    setInput('');
    setError(null);

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: userText,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsSending(true);

    try {
      const response = await sendChatMessage(runId, userText);

      const botMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.reply,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, botMsg]);

      // If keywords were patched, update parent state
      if (response.keywords_patch && response.keywords_patch.length > 0) {
        onPatchKeywords(response.keywords_patch);
      }
    } catch (err: unknown) {
      setError((err as Error)?.message || 'Failed to send message.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="my-8 rounded-2xl bg-slate-900 border border-slate-800 p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-800">
        <MessageSquare className="w-5 h-5 text-sky-400" />
        <h2 className="text-lg font-bold text-slate-100">AI Analyst Assistant</h2>
      </div>

      {/* Messages Scroll Area */}
      <div className="space-y-3 mb-4 max-h-80 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <p className="text-xs text-slate-500 italic py-2">
            Ask any question or customize keywords (e.g., &ldquo;Make Myntra keywords more Gen-Z&rdquo;, &ldquo;Add Hindi/Hinglish terms for Flipkart&rdquo;, &ldquo;Remove sleeve tags&rdquo;).
          </p>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className={`flex items-start gap-2.5 text-xs md:text-sm ${
                m.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {m.role === 'assistant' && (
                <div className="p-1 rounded-md bg-sky-950 border border-sky-800/80 text-sky-400 mt-0.5 shrink-0">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}
              <div
                className={`px-3.5 py-2 rounded-xl max-w-[80%] leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-sky-600 text-white'
                    : 'bg-slate-800 text-slate-200 border border-slate-700/80'
                }`}
              >
                {m.content}
              </div>
              {m.role === 'user' && (
                <div className="p-1 rounded-md bg-slate-800 border border-slate-700 text-slate-300 mt-0.5 shrink-0">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))
        )}

        {isSending && (
          <div className="flex items-center gap-2 text-xs text-slate-400 italic">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />
            <span>AI Analyst is updating keyword recommendations...</span>
          </div>
        )}
      </div>

      {error && <p className="mb-3 text-xs text-rose-400">{error}</p>}

      {/* Chat Input Form */}
      <form onSubmit={handleSend} className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isSending}
          placeholder="Ask a question or customise the keywords (e.g. make Myntra keywords more Gen-Z)..."
          className="flex-1 px-4 py-2 text-xs md:text-sm bg-slate-800/90 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
        />
        <button
          type="submit"
          disabled={isSending || !input.trim()}
          aria-label="Send message"
          className={`p-2.5 rounded-xl text-white transition-all cursor-pointer ${
            isSending || !input.trim()
              ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
              : 'bg-sky-600 hover:bg-sky-500'
          }`}
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
