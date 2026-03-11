'use client';

import { ChatMessage, SourceReference } from '@/types';
import ReactMarkdown from 'react-markdown';

interface MessageListProps {
  messages: ChatMessage[];
  onSourceClick: (sources: SourceReference[]) => void;
  isLoading: boolean;
}

export default function MessageList({ messages, onSourceClick, isLoading }: MessageListProps) {
  return (
    <div className="max-w-3xl mx-auto py-6 px-4 space-y-6">
      {messages.map((msg, i) => (
        <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
          {msg.role === 'assistant' && (
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
          )}

          <div className={`max-w-[80%] ${msg.role === 'user'
            ? 'bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2.5'
            : 'text-slate-200'
          }`}>
            {msg.role === 'assistant' ? (
              <div className="chat-markdown">
                <ReactMarkdown>{msg.content || (isLoading && i === messages.length - 1 ? '...' : '')}</ReactMarkdown>
              </div>
            ) : (
              <p className="text-sm">{msg.content}</p>
            )}

            {/* Sources */}
            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-700/50">
                <p className="text-xs text-slate-400 mb-2">Quellen:</p>
                <div className="flex flex-wrap gap-1.5">
                  {msg.sources.map((src, j) => (
                    <button
                      key={j}
                      onClick={() => onSourceClick(msg.sources!)}
                      className="text-xs bg-slate-800 hover:bg-slate-700 text-blue-400 px-2 py-1 rounded border border-slate-700 transition-colors"
                    >
                      [{j + 1}] {src.title}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Feedback buttons */}
            {msg.role === 'assistant' && msg.content && !isLoading && (
              <div className="flex gap-1 mt-2">
                <button className="p-1 text-slate-500 hover:text-green-400 transition-colors" title="Hilfreich">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                </button>
                <button className="p-1 text-slate-500 hover:text-red-400 transition-colors" title="Nicht hilfreich">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Loading indicator */}
      {isLoading && messages.length > 0 && messages[messages.length - 1]?.content === '' && (
        <div className="flex gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
