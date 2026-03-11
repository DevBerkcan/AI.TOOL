'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { DashboardStats, Connector } from '@/types';

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: string }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="text-sm text-slate-400">{label}</span>
      </div>
      <span className="text-2xl font-bold text-white">{value}</span>
    </div>
  );
}

export default function AdminPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getStats().then(setStats).catch(e => setError(e.message));
    api.getConnectors().then(setConnectors).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="h-14 border-b border-slate-800 flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <Link href="/chat" className="text-slate-400 hover:text-white text-sm">← Chat</Link>
          <h1 className="text-sm font-medium text-white">Admin Dashboard</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-6">
        {error && (
          <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-3 rounded-lg mb-6 text-sm">
            {error}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <StatCard icon="📄" label="Dokumente" value={stats?.total_documents ?? '-'} />
          <StatCard icon="🧩" label="Chunks" value={stats?.total_chunks ?? '-'} />
          <StatCard icon="💬" label="Queries (7d)" value={stats?.queries_last_7d ?? '-'} />
          <StatCard icon="👥" label="Benutzer" value={stats?.total_users ?? '-'} />
          <StatCard icon="🔗" label="Connectoren" value={stats?.active_connectors ?? '-'} />
        </div>

        {/* Connectors */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-white">Connectoren</h2>
            <button className="text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg transition-colors">
              + Neuer Connector
            </button>
          </div>

          <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Name</th>
                  <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Typ</th>
                  <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Status</th>
                  <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Letzter Sync</th>
                  <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {connectors.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center text-sm text-slate-500 py-8">
                      Noch keine Connectoren konfiguriert.
                    </td>
                  </tr>
                ) : (
                  connectors.map((c) => (
                    <tr key={c.id} className="border-b border-slate-700/30 hover:bg-slate-800/30">
                      <td className="px-4 py-3 text-sm text-white">{c.name}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">{c.type}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded ${c.is_active ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>
                          {c.is_active ? 'Aktiv' : 'Inaktiv'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        {c.last_sync_at ? new Date(c.last_sync_at).toLocaleString('de-DE') : '-'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => api.triggerSync(c.id)}
                          className="text-xs text-blue-400 hover:text-blue-300"
                        >
                          Sync starten
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Quick links */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-medium text-white mb-2">Benutzer verwalten</h3>
            <p className="text-xs text-slate-400 mb-3">Rollen und Zugriff über Entra ID verwalten.</p>
            <button className="text-xs text-blue-400 hover:underline">Benutzer anzeigen →</button>
          </div>
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-medium text-white mb-2">AI Provider Config</h3>
            <p className="text-xs text-slate-400 mb-3">Modelle und Provider konfigurieren.</p>
            <button className="text-xs text-blue-400 hover:underline">Config öffnen →</button>
          </div>
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-medium text-white mb-2">Audit Logs</h3>
            <p className="text-xs text-slate-400 mb-3">Alle System-Aktivitäten einsehen.</p>
            <button className="text-xs text-blue-400 hover:underline">Logs anzeigen →</button>
          </div>
        </section>
      </main>
    </div>
  );
}
