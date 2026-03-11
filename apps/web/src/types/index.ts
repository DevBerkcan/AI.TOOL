/** Shared types for the Knowledge Copilot frontend. */

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: 'admin' | 'user' | 'viewer';
  tenant_id: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceReference[];
  model_used?: string;
  created_at?: string;
}

export interface SourceReference {
  document_id: string;
  title: string;
  source_url?: string;
  snippet: string;
  score: number;
}

export interface Conversation {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  title: string;
  source_type: string;
  status: string;
  source_url?: string;
  chunks_count: number;
  created_at: string;
  last_synced_at?: string;
}

export interface Connector {
  id: string;
  type: string;
  name: string;
  is_active: boolean;
  last_sync_at?: string;
  sync_interval_min: number;
  created_at: string;
}

export interface SyncJob {
  id: string;
  connector_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  documents_synced: number;
  documents_failed: number;
  error_message?: string;
}

export interface DashboardStats {
  total_documents: number;
  total_chunks: number;
  queries_last_7d: number;
  total_users: number;
  active_connectors: number;
}

export interface SSEEvent {
  event: 'token' | 'status' | 'done' | 'error';
  data: string;
}
