export interface User {
  id: string
  username: string
  created_at: string
}

export interface UserSession {
  id: string
  session_token: string
  ip_address: string | null
  user_agent: string | null
  last_active_at: string | null
  expires_at: string | null
  created_at: string
}

export interface Notebook {
  id: string
  name: string
  is_default: boolean
  created_at: string
  updated_at: string
  note_count: number
}

export interface Note {
  id: string
  notebook_id: string
  title: string | null
  content: string
  raw_transcription: string | null
  created_at: string
  updated_at: string
}

export interface NoteListItem {
  id: string
  notebook_id: string
  title: string | null
  content_preview: string
  /** Raw character length of the note body. */
  content_length?: number
  /** Server-side approximate token count (cl100k-style). */
  token_estimate?: number
  created_at: string
  updated_at: string
}

export interface BulkDeleteResult {
  status: string
  deleted_count: number
}

export interface BulkMoveResult {
  status: string
  moved_count: number
}

export interface NoteSearchResult {
  note_id: string
  notebook_id: string
  notebook_name: string
  title: string | null
  content_snippet: string
}

export interface ExportTaskInfo {
  id: string
  task_type: 'single' | 'bulk'
  format: 'md' | 'pdf'
  note_id: string | null
  status: 'pending' | 'claimed' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  filename: string | null
  error: string | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
}
