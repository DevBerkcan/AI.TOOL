'use client';

import { useState } from 'react';
import { useChat } from '@/hooks/useChat';
import ChatInput from '@/components/chat/ChatInput';
import MessageList from '@/components/chat/MessageList';
import SourcePanel from '@/components/chat/SourcePanel';
import Sidebar from '@/components/chat/Sidebar';
import { SourceReference } from '@/types';

export default function ChatPage() {
  const { messages, isLoading, sendMessage, stopGeneration, clearChat } = useChat();
  const [selectedSources, setSelectedSources] = useState<SourceReference[]>([]);
  const [showSources, setShowSources] = useState(false);

  const handleSourceClick = (sources: SourceReference[]) => {
    setSelectedSources(sources);
    setShowSources(true);
  };

  return (
    <div className="h-screen flex bg-slate-950">
      {/* Sidebar */}
      <Sidebar onNewChat={clearChat} />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 border-b border-slate-800 flex items-center px-4 justify-between shrink-0">
          <h1 className="text-sm font-medium text-slate-300">RealCore Knowledge AI</h1>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
              GPT-4o
            </span>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-lg font-medium text-white mb-2">Frag dein Unternehmenswissen</h2>
              <p className="text-slate-400 text-sm max-w-md mb-6">
                Stelle Fragen zu internen Dokumenten, Prozessen und Richtlinien.
                Die Antworten basieren auf deinen synchronisierten Quellen.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
                {[
                  'Wie funktioniert unser Deployment Prozess?',
                  'Welche Richtlinie gilt für Datenlöschung?',
                  'Wo finde ich das Onboarding für neue Entwickler?',
                  'Welche Schritte gelten für Angebotsfreigaben?',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="text-left text-sm text-slate-300 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-lg p-3 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <MessageList messages={messages} onSourceClick={handleSourceClick} isLoading={isLoading} />
          )}
        </div>

        {/* Input */}
        <ChatInput
          onSend={sendMessage}
          onStop={stopGeneration}
          isLoading={isLoading}
        />
      </div>

      {/* Source Panel */}
      {showSources && (
        <SourcePanel
          sources={selectedSources}
          onClose={() => setShowSources(false)}
        />
      )}
    </div>
  );
}
