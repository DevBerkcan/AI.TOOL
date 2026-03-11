/** API client for RealCore Knowledge AI backend. */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { 'Content-Type': 'application/json' };
    if (this.token) h['Authorization'] = `Bearer ${this.token}`;
    return h;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { ...this.headers(), ...(options.headers || {}) },
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `API Error: ${res.status}`);
    }

    if (res.status === 204) return null as T;
    return res.json();
  }

  // ── Auth ──
  async getMe() {
    return this.request<{ id: string; email: string; display_name: string; role: string; tenant_id: string }>('/api/v1/auth/me');
  }

  // ── Chat ──
  chatStream(query: string, conversationId?: string): EventSource | null {
    // SSE streaming is handled by the ChatUI component directly
    return null;
  }

  async getConversations(limit = 20) {
    return this.request<Array<{ id: string; title: string; message_count: number; created_at: string }>>(`/api/v1/chat/conversations?limit=${limit}`);
  }

  async getConversation(id: string) {
    return this.request<{ id: string; messages: Array<any> }>(`/api/v1/chat/conversations/${id}`);
  }

  async deleteConversation(id: string) {
    return this.request<void>(`/api/v1/chat/conversations/${id}`, { method: 'DELETE' });
  }

  // ── Documents ──
  async uploadDocument(file: File) {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_URL}/api/v1/documents/upload`, {
      method: 'POST',
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
      body: form,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  }

  async getDocuments(limit = 50) {
    return this.request<Array<any>>(`/api/v1/documents?limit=${limit}`);
  }

  // ── Connectors ──
  async getConnectors() {
    return this.request<Array<any>>('/api/v1/connectors');
  }

  async createConnector(data: { type: string; name: string; config: Record<string, any> }) {
    return this.request<any>('/api/v1/connectors', { method: 'POST', body: JSON.stringify(data) });
  }

  async triggerSync(connectorId: string) {
    return this.request<any>(`/api/v1/connectors/${connectorId}/sync`, { method: 'POST' });
  }

  async getSyncJobs(connectorId: string) {
    return this.request<Array<any>>(`/api/v1/connectors/${connectorId}/syncs`);
  }

  // ── Feedback ──
  async submitFeedback(queryId: string, rating: 'positive' | 'negative', comment?: string) {
    return this.request<void>('/api/v1/feedback', {
      method: 'POST',
      body: JSON.stringify({ query_id: queryId, rating, comment }),
    });
  }

  // ── Admin ──
  async getStats() {
    return this.request<any>('/api/v1/admin/stats');
  }

  async getUsers() {
    return this.request<Array<any>>('/api/v1/admin/users');
  }

  async getAuditLogs(limit = 100) {
    return this.request<Array<any>>(`/api/v1/admin/audit-logs?limit=${limit}`);
  }

  async getModelConfigs() {
    return this.request<Array<any>>('/api/v1/admin/model-config');
  }
}

export const api = new ApiClient();
export default api;
