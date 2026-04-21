import Database from 'better-sqlite3'
import path from 'path'

const DB_PATH = path.join(process.cwd(), '..', 'data', 'memory.db')

function getDb() {
  try {
    return new Database(DB_PATH, { readonly: true, fileMustExist: true })
  } catch {
    return null
  }
}

export interface SessionStats {
  session_count: number
  task_count: number
}

export interface ActivityRow {
  chat_id: number
  role: string
  content: string
  created_at: string
}

export interface TaskRow {
  id: number
  chat_id: number
  task_prompt: string
  schedule_str: string
  enabled: boolean
  created_at: string
}

export function getSessionStats(): SessionStats {
  const db = getDb()
  if (!db) return { session_count: 0, task_count: 0 }
  try {
    const session_count = (db.prepare('SELECT COUNT(*) as n FROM sessions').get() as { n: number }).n
    const task_count = (db.prepare('SELECT COUNT(*) as n FROM scheduled_tasks WHERE enabled=1').get() as { n: number }).n
    return { session_count, task_count }
  } catch { return { session_count: 0, task_count: 0 } }
  finally { db.close() }
}

export function getRecentActivity(limit = 15): ActivityRow[] {
  const db = getDb()
  if (!db) return []
  try {
    const rows = db.prepare(
      'SELECT chat_id, role, content, created_at FROM conversations ORDER BY id DESC LIMIT ?'
    ).all(limit) as ActivityRow[]
    return rows.map(r => ({
      ...r,
      content: r.content.length > 160 ? r.content.slice(0, 160) + '…' : r.content,
    }))
  } catch { return [] }
  finally { db.close() }
}

export function getScheduledTasks(): TaskRow[] {
  const db = getDb()
  if (!db) return []
  try {
    const rows = db.prepare(
      'SELECT id, chat_id, task_prompt, schedule_str, enabled, created_at FROM scheduled_tasks ORDER BY id DESC'
    ).all() as (Omit<TaskRow, 'enabled'> & { enabled: number })[]
    return rows.map(r => ({
      ...r,
      task_prompt: r.task_prompt.length > 120 ? r.task_prompt.slice(0, 120) + '…' : r.task_prompt,
      enabled: Boolean(r.enabled),
    }))
  } catch { return [] }
  finally { db.close() }
}
