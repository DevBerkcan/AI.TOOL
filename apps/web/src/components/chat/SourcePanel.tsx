'use client';

import { SourceReference } from '@/types';

interface SourcePanelProps {
  sources: SourceReference[];
  onClose: () => void;
}

export default function SourcePanel({ sources, onClose }: SourcePanelProps) {
  return (
    <div className="w-80 border-l border-slate-800 bg-slate-900/50 flex flex-col shrink-0">
      <div className="h-14 border-b border-slate-800 flex items-center justify-between px-4">
        <h2 className="text-sm font-medium text-slate-300">Quellen</h2>
        <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {sources.map((src, i) => (
          <div key={i} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3">
            <div className="flex items-start gap-2 mb-2">
              <span className="text-xs font-medium text-blue-400 bg-blue-400/10 px-1.5 py-0.5 rounded">
                [{i + 1}]
              </span>
              <h3 className="text-sm font-medium text-slate-200 leading-snug">{src.title}</h3>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed mb-2">{src.snippet}</p>

            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Score: {(src.score * 100).toFixed(0)}%
              </span>
              {src.source_url && (
                <a
                  href={src.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-400 hover:underline"
                >
                  Original öffnen →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
