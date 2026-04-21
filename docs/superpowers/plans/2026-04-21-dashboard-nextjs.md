# Dashboard (Next.js) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A live read-only dashboard for claudhaus built with Next.js 14 (App Router) — showing bot status, sessions, memory, scheduled tasks, skills, and connectors.

**Architecture:** Next.js 14 App Router + TypeScript in `dashboard-ui/`. Next.js API routes read SQLite via `better-sqlite3` and files via `fs` — no Python backend needed. Void Indigo color system defined as CSS custom properties in `globals.css` and wired into Tailwind. `next start` served via systemd on port 3000. Dashboard auto-refreshes via `setInterval` + SWR.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, better-sqlite3, SWR (data fetching), Lucide React (icons).

---

## Color System — "Void Indigo"

Defined once in `globals.css` as CSS custom properties. Tailwind `tailwind.config.ts` maps them to utility classes. Used on the dashboard and later on the landing page/docs.

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#07071a` | Page background |
| `--color-surface` | `#0d0d26` | Header, sidebar |
| `--color-card` | `#12122e` | Card backgrounds |
| `--color-border` | `#1c1c45` | Card borders, dividers |
| `--color-primary` | `#7b6ef6` | Electric indigo — accents, active |
| `--color-primary-dim` | `rgba(123,110,246,.10)` | Hover glow, icon backgrounds |
| `--color-secondary` | `#06d6a0` | Mint — online, healthy |
| `--color-danger` | `#ff4d6d` | Error, offline |
| `--color-warning` | `#ffd166` | Warning, pending |
| `--color-text` | `#e8e8f8` | Primary text |
| `--color-muted` | `#5a5a7a` | Labels, timestamps |

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `dashboard-ui/package.json` | Create | Next.js 14 + deps |
| `dashboard-ui/next.config.ts` | Create | Next.js config |
| `dashboard-ui/tsconfig.json` | Create | TypeScript config |
| `dashboard-ui/tailwind.config.ts` | Create | Void Indigo theme tokens |
| `dashboard-ui/postcss.config.js` | Create | Tailwind PostCSS |
| `dashboard-ui/app/globals.css` | Create | CSS variables + base reset |
| `dashboard-ui/app/layout.tsx` | Create | Root layout with header |
| `dashboard-ui/app/page.tsx` | Create | Dashboard page — stat cards + panels |
| `dashboard-ui/lib/db.ts` | Create | better-sqlite3 wrapper — all DB queries |
| `dashboard-ui/lib/files.ts` | Create | File system helpers — skills, connectors, memory |
| `dashboard-ui/app/api/stats/route.ts` | Create | GET /api/stats |
| `dashboard-ui/app/api/activity/route.ts` | Create | GET /api/activity |
| `dashboard-ui/app/api/tasks/route.ts` | Create | GET /api/tasks |
| `dashboard-ui/app/api/skills/route.ts` | Create | GET /api/skills |
| `dashboard-ui/app/api/connectors/route.ts` | Create | GET /api/connectors |
| `dashboard-ui/components/StatCard.tsx` | Create | Stat card component |
| `dashboard-ui/components/Panel.tsx` | Create | Panel wrapper component |
| `dashboard-ui/components/ActivityFeed.tsx` | Create | Activity rows with role badges |
| `dashboard-ui/components/TaskList.tsx` | Create | Scheduled tasks list |
| `systemd/claude-dashboard.service` | Modify | Run `next start --port 3000` |
| `scripts/install-systemd.sh` | Modify | Enable dashboard service |
| `.gitignore` | Modify | Ignore `dashboard-ui/.next`, `dashboard-ui/node_modules` |

---

## Task 1: Scaffold — package.json, configs, install deps

**Files:**
- Create: `dashboard-ui/package.json`
- Create: `dashboard-ui/next.config.ts`
- Create: `dashboard-ui/tsconfig.json`
- Create: `dashboard-ui/tailwind.config.ts`
- Create: `dashboard-ui/postcss.config.js`

- [ ] **Step 1: Create dashboard-ui/ directory and package.json**

```bash
mkdir -p dashboard-ui
```

Write `dashboard-ui/package.json`:
```json
{
  "name": "claudhaus-dashboard",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000"
  },
  "dependencies": {
    "next": "14.2.29",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "better-sqlite3": "^9.6.0",
    "swr": "^2.2.5",
    "lucide-react": "^0.408.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.11",
    "@types/node": "^20.14.9",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3"
  }
}
```

- [ ] **Step 2: Create next.config.ts**

```typescript
import type { NextConfig } from 'next'

const config: NextConfig = {
  output: 'standalone',
}

export default config
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Create tailwind.config.ts**

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:        'var(--color-bg)',
        surface:   'var(--color-surface)',
        card:      'var(--color-card)',
        border:    'var(--color-border)',
        primary:   'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        danger:    'var(--color-danger)',
        warning:   'var(--color-warning)',
        txt:       'var(--color-text)',
        muted:     'var(--color-muted)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
```

- [ ] **Step 5: Create postcss.config.js**

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 6: Install dependencies**

```bash
cd dashboard-ui && npm install --legacy-peer-deps
```

Wait for install to complete. Verify with:
```bash
ls node_modules/next node_modules/better-sqlite3 node_modules/swr
```

- [ ] **Step 7: Commit**

```bash
cd ..
git add dashboard-ui/package.json dashboard-ui/package-lock.json dashboard-ui/next.config.ts dashboard-ui/tsconfig.json dashboard-ui/tailwind.config.ts dashboard-ui/postcss.config.js
git commit -m "feat(dashboard): scaffold Next.js 14 app with Void Indigo Tailwind config"
```

---

## Task 2: Data lib — db.ts and files.ts

**Files:**
- Create: `dashboard-ui/lib/db.ts`
- Create: `dashboard-ui/lib/files.ts`

- [ ] **Step 1: Create dashboard-ui/lib/db.ts**

```typescript
// dashboard-ui/lib/db.ts
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
```

- [ ] **Step 2: Create dashboard-ui/lib/files.ts**

```typescript
// dashboard-ui/lib/files.ts
import fs from 'fs'
import path from 'path'

const ROOT = path.join(process.cwd(), '..')
const WORKSPACE = path.join(ROOT, 'workspaces', 'main')
const SKILLS_DIR = path.join(ROOT, 'agents', 'main', 'skills')

// Connector registry mirrored from agents/main/connectors.py
const CONNECTOR_REGISTRY: Record<string, string> = {
  github:       'GitHub — issues, PRs, file contents, repo search',
  hubspot:      'HubSpot — contacts, deals, companies, emails, pipelines',
  slack:        'Slack — send messages, read channels, list users',
  linear:       'Linear — issues, projects, cycles, teams',
  notion:       'Notion — pages, databases, blocks',
  'google-drive': 'Google Drive — files, folders, shared drives',
  gmail:        'Gmail — send email, read inbox, manage labels',
  'google-calendar': 'Google Calendar — events, availability, invites',
  postgres:     'PostgreSQL — query and inspect databases',
  sqlite:       'SQLite — query local SQLite databases',
  stripe:       'Stripe — payments, customers, invoices, subscriptions',
  jira:         'Jira — issues, sprints, projects, boards',
}

function readClaudeJson(): Record<string, unknown> {
  try {
    const p = path.join(process.env.HOME || '', '.claude.json')
    return JSON.parse(fs.readFileSync(p, 'utf-8'))
  } catch { return {} }
}

function getInstalledConnectors(): Set<string> {
  const data = readClaudeJson()
  const servers = (data.mcpServers as Record<string, unknown>) || {}
  return new Set(Object.keys(servers))
}

export interface MemoryStats {
  memory_kb: number
  dreams_count: number
  daily_notes: number
}

export function getMemoryStats(): MemoryStats {
  let memory_kb = 0
  let dreams_count = 0
  let daily_notes = 0

  try {
    const memPath = path.join(WORKSPACE, 'MEMORY.md')
    if (fs.existsSync(memPath)) {
      memory_kb = Math.round(fs.statSync(memPath).size / 1024 * 10) / 10
    }
  } catch {}

  try {
    const dreamsPath = path.join(WORKSPACE, 'DREAMS.md')
    if (fs.existsSync(dreamsPath)) {
      dreams_count = fs.readFileSync(dreamsPath, 'utf-8')
        .split('\n').filter(l => l.trim().startsWith('-')).length
    }
  } catch {}

  try {
    const dailyDir = path.join(WORKSPACE, 'memory')
    if (fs.existsSync(dailyDir)) {
      daily_notes = fs.readdirSync(dailyDir).filter(f => f.endsWith('.md')).length
    }
  } catch {}

  return { memory_kb, dreams_count, daily_notes }
}

export interface SkillRow { name: string; preview: string }

export function getSkills(): SkillRow[] {
  try {
    if (!fs.existsSync(SKILLS_DIR)) return []
    return fs.readdirSync(SKILLS_DIR)
      .filter(f => f.endsWith('.md'))
      .sort()
      .map(f => {
        const content = fs.readFileSync(path.join(SKILLS_DIR, f), 'utf-8')
        const preview = content.split('\n').find(l => l.trim())?.trim().slice(0, 100) || ''
        return { name: f.replace('.md', ''), preview }
      })
  } catch { return [] }
}

export interface ConnectorRow { name: string; description: string; installed: boolean }

export function getConnectors(): ConnectorRow[] {
  const installed = getInstalledConnectors()
  return Object.entries(CONNECTOR_REGISTRY).map(([name, description]) => ({
    name,
    description,
    installed: installed.has(name),
  }))
}

export function getSkillCount(): number {
  try {
    if (!fs.existsSync(SKILLS_DIR)) return 0
    return fs.readdirSync(SKILLS_DIR).filter(f => f.endsWith('.md')).length
  } catch { return 0 }
}

export function getConnectorCount(): number {
  return getInstalledConnectors().size
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd dashboard-ui && npx tsc --noEmit 2>&1 | head -20
```

Expected: no output (no errors).

- [ ] **Step 4: Commit**

```bash
cd ..
git add dashboard-ui/lib/
git commit -m "feat(dashboard): data lib — db.ts (better-sqlite3) and files.ts"
```

---

## Task 3: API routes

**Files:**
- Create: `dashboard-ui/app/api/stats/route.ts`
- Create: `dashboard-ui/app/api/activity/route.ts`
- Create: `dashboard-ui/app/api/tasks/route.ts`
- Create: `dashboard-ui/app/api/skills/route.ts`
- Create: `dashboard-ui/app/api/connectors/route.ts`

- [ ] **Step 1: Create all api route directories and files**

```bash
mkdir -p dashboard-ui/app/api/stats dashboard-ui/app/api/activity dashboard-ui/app/api/tasks dashboard-ui/app/api/skills dashboard-ui/app/api/connectors
```

`dashboard-ui/app/api/stats/route.ts`:
```typescript
import { NextResponse } from 'next/server'
import { getSessionStats } from '@/lib/db'
import { getMemoryStats, getSkillCount, getConnectorCount } from '@/lib/files'

export const dynamic = 'force-dynamic'

export async function GET() {
  const { session_count, task_count } = getSessionStats()
  const { memory_kb, dreams_count, daily_notes } = getMemoryStats()
  return NextResponse.json({
    session_count,
    task_count,
    skill_count: getSkillCount(),
    connector_count: getConnectorCount(),
    memory_kb,
    dreams_count,
    daily_notes,
  })
}
```

`dashboard-ui/app/api/activity/route.ts`:
```typescript
import { NextResponse } from 'next/server'
import { getRecentActivity } from '@/lib/db'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json(getRecentActivity(15))
}
```

`dashboard-ui/app/api/tasks/route.ts`:
```typescript
import { NextResponse } from 'next/server'
import { getScheduledTasks } from '@/lib/db'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json(getScheduledTasks())
}
```

`dashboard-ui/app/api/skills/route.ts`:
```typescript
import { NextResponse } from 'next/server'
import { getSkills } from '@/lib/files'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json(getSkills())
}
```

`dashboard-ui/app/api/connectors/route.ts`:
```typescript
import { NextResponse } from 'next/server'
import { getConnectors } from '@/lib/files'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json(getConnectors())
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard-ui/app/api/
git commit -m "feat(dashboard): API routes — stats, activity, tasks, skills, connectors"
```

---

## Task 4: globals.css + layout

**Files:**
- Create: `dashboard-ui/app/globals.css`
- Create: `dashboard-ui/app/layout.tsx`

- [ ] **Step 1: Create globals.css**

```css
/* dashboard-ui/app/globals.css — claudhaus · Void Indigo */
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --color-bg:          #07071a;
  --color-surface:     #0d0d26;
  --color-card:        #12122e;
  --color-border:      #1c1c45;
  --color-primary:     #7b6ef6;
  --color-primary-dim: rgba(123, 110, 246, 0.10);
  --color-secondary:   #06d6a0;
  --color-danger:      #ff4d6d;
  --color-warning:     #ffd166;
  --color-text:        #e8e8f8;
  --color-muted:       #5a5a7a;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background-color: var(--color-bg);
  color: var(--color-text);
  font-family: 'Inter', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 4px; }
* { scrollbar-width: thin; scrollbar-color: var(--color-border) transparent; }
```

- [ ] **Step 2: Create layout.tsx**

```tsx
// dashboard-ui/app/layout.tsx
import type { Metadata } from 'next'
import './globals.css'
import { Zap } from 'lucide-react'

export const metadata: Metadata = {
  title: 'claudhaus',
  description: 'Personal AI command center dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="sticky top-0 z-50 flex items-center justify-between px-6 h-14 bg-surface border-b border-border">
          <div className="flex items-center gap-2 font-bold text-sm tracking-tight">
            <Zap size={16} className="text-primary" />
            claudhaus
          </div>
          <div className="flex items-center gap-5 text-xs text-muted">
            <span className="flex items-center gap-1.5 text-secondary font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_6px_var(--color-secondary)] animate-pulse" />
              online
            </span>
          </div>
        </header>
        <main className="max-w-[1200px] mx-auto px-6 py-8 pb-16">
          {children}
        </main>
      </body>
    </html>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard-ui/app/globals.css dashboard-ui/app/layout.tsx
git commit -m "feat(dashboard): Void Indigo globals.css and root layout"
```

---

## Task 5: Components

**Files:**
- Create: `dashboard-ui/components/StatCard.tsx`
- Create: `dashboard-ui/components/Panel.tsx`
- Create: `dashboard-ui/components/ActivityFeed.tsx`
- Create: `dashboard-ui/components/TaskList.tsx`

- [ ] **Step 1: Create all component files**

```bash
mkdir -p dashboard-ui/components
```

`dashboard-ui/components/StatCard.tsx`:
```tsx
import type { ReactNode } from 'react'

interface Props {
  label: string
  value: string | number
  icon: ReactNode
  unit?: string
}

export default function StatCard({ label, value, icon, unit }: Props) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-2 hover:border-primary hover:shadow-[0_0_0_1px_rgba(123,110,246,.10)] transition-all duration-150">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-primary"
           style={{ background: 'var(--color-primary-dim)' }}>
        {icon}
      </div>
      <div className="flex items-end gap-1 leading-none">
        <span className="text-3xl font-bold tracking-tight">{value}</span>
        {unit && <span className="text-sm font-medium text-muted mb-0.5">{unit}</span>}
      </div>
      <div className="text-xs font-medium text-muted">{label}</div>
    </div>
  )
}
```

`dashboard-ui/components/Panel.tsx`:
```tsx
import type { ReactNode } from 'react'

interface Props {
  title: string
  count?: number | string
  children: ReactNode
  full?: boolean
}

export default function Panel({ title, count, children, full }: Props) {
  return (
    <div className={`bg-card border border-border rounded-xl overflow-hidden${full ? ' col-span-full' : ''}`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="text-[11px] font-semibold tracking-widest uppercase text-muted">{title}</span>
        {count !== undefined && (
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full text-primary"
                style={{ background: 'var(--color-primary-dim)' }}>
            {count}
          </span>
        )}
      </div>
      <div className="max-h-80 overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
```

`dashboard-ui/components/ActivityFeed.tsx`:
```tsx
'use client'
import useSWR from 'swr'
import Panel from './Panel'

interface ActivityRow { chat_id: number; role: string; content: string; created_at: string }

const fetcher = (url: string) => fetch(url).then(r => r.json())

export default function ActivityFeed() {
  const { data: rows = [] } = useSWR<ActivityRow[]>('/api/activity', fetcher, { refreshInterval: 30000 })

  return (
    <Panel title="Recent Activity" count="last 15">
      {rows.length === 0 ? (
        <p className="text-center text-sm text-muted py-8">No activity yet.</p>
      ) : rows.map((row, i) => (
        <div key={i} className="flex items-start gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
          <span className={`flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded mt-0.5 ${
            row.role === 'user'
              ? 'bg-[rgba(123,110,246,.2)] text-primary'
              : 'bg-[rgba(6,214,160,.15)] text-secondary'
          }`}>
            {row.role.slice(0, 4).toUpperCase()}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm truncate">{row.content}</p>
            <p className="text-[11px] text-muted font-mono mt-0.5">
              chat {row.chat_id} · {row.created_at}
            </p>
          </div>
        </div>
      ))}
    </Panel>
  )
}
```

`dashboard-ui/components/TaskList.tsx`:
```tsx
'use client'
import useSWR from 'swr'
import Panel from './Panel'

interface TaskRow { id: number; chat_id: number; task_prompt: string; schedule_str: string; enabled: boolean }

const fetcher = (url: string) => fetch(url).then(r => r.json())

export default function TaskList() {
  const { data: tasks = [] } = useSWR<TaskRow[]>('/api/tasks', fetcher, { refreshInterval: 30000 })

  return (
    <Panel title="Scheduled Tasks" count={tasks.length}>
      {tasks.length === 0 ? (
        <p className="text-center text-sm text-muted py-8">No scheduled tasks.</p>
      ) : tasks.map(t => (
        <div key={t.id} className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
          <span className="font-mono text-[11px] text-muted w-7 flex-shrink-0">#{t.id}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm truncate">{t.task_prompt}</p>
            <p className="text-[11px] font-mono text-muted mt-0.5">{t.schedule_str}</p>
          </div>
          <span className={`flex-shrink-0 w-2 h-2 rounded-full ${
            t.enabled
              ? 'bg-secondary shadow-[0_0_5px_var(--color-secondary)]'
              : 'bg-muted'
          }`} />
        </div>
      ))}
    </Panel>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard-ui/components/
git commit -m "feat(dashboard): StatCard, Panel, ActivityFeed, TaskList components"
```

---

## Task 6: Main page

**Files:**
- Create: `dashboard-ui/app/page.tsx`

- [ ] **Step 1: Create page.tsx**

```tsx
// dashboard-ui/app/page.tsx
import { Users, Clock, Pencil, Database, Plug, BookOpen } from 'lucide-react'
import StatCard from '@/components/StatCard'
import Panel from '@/components/Panel'
import ActivityFeed from '@/components/ActivityFeed'
import TaskList from '@/components/TaskList'
import { getSessionStats } from '@/lib/db'
import { getMemoryStats, getSkillCount, getConnectorCount, getSkills, getConnectors } from '@/lib/files'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export default function DashboardPage() {
  const { session_count, task_count } = getSessionStats()
  const { memory_kb, daily_notes } = getMemoryStats()
  const skill_count = getSkillCount()
  const connector_count = getConnectorCount()
  const skills = getSkills()
  const connectors = getConnectors()

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div>
        <p className="text-[11px] font-semibold tracking-widest uppercase text-muted mb-3">Overview</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard label="Active sessions"   value={session_count}  icon={<Users size={15} />} />
          <StatCard label="Scheduled tasks"   value={task_count}     icon={<Clock size={15} />} />
          <StatCard label="Skills"            value={skill_count}    icon={<Pencil size={15} />} />
          <StatCard label="Memory"            value={memory_kb}      icon={<Database size={15} />} unit="kb" />
          <StatCard label="Connectors"        value={connector_count} icon={<Plug size={15} />} />
          <StatCard label="Daily notes"       value={daily_notes}    icon={<BookOpen size={15} />} />
        </div>
      </div>

      {/* Activity + Tasks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <ActivityFeed />
        <TaskList />
      </div>

      {/* Skills + Connectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Panel title="Skills" count={skills.length}>
          {skills.length === 0 ? (
            <p className="text-center text-sm text-muted py-8">No skills saved yet.</p>
          ) : skills.map(s => (
            <div key={s.name} className="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
              <span className="font-mono text-xs text-primary flex-shrink-0 w-36 truncate">{s.name}</span>
              <span className="text-xs text-muted truncate">{s.preview}</span>
            </div>
          ))}
        </Panel>

        <Panel title="Connectors" count={`${connectors.filter(c => c.installed).length} / ${connectors.length}`}>
          {connectors.map(c => (
            <div key={c.name} className="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0 hover:bg-[rgba(123,110,246,.04)] transition-colors">
              <span className={`font-semibold text-sm capitalize flex-shrink-0 w-28 ${c.installed ? 'text-txt' : 'text-muted'}`}>
                {c.name}
              </span>
              <span className="text-xs text-muted flex-1 truncate">{c.description}</span>
              <span className={`flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded ${
                c.installed
                  ? 'bg-[rgba(6,214,160,.15)] text-secondary'
                  : 'bg-[rgba(90,90,122,.12)] text-muted'
              }`}>
                {c.installed ? 'ON' : 'OFF'}
              </span>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run build to verify no TypeScript/build errors**

```bash
cd dashboard-ui && npm run build 2>&1 | tail -20
```

Expected: build completes successfully (exit 0, shows "Route (app)" table).

If there are TypeScript errors, fix them before committing.

- [ ] **Step 3: Commit**

```bash
cd ..
git add dashboard-ui/app/page.tsx
git commit -m "feat(dashboard): main dashboard page with all panels"
```

---

## Task 7: Wiring, .gitignore, systemd, docs

**Files:**
- Modify: `.gitignore`
- Modify: `systemd/claude-dashboard.service`
- Modify: `scripts/install-systemd.sh`
- Modify: `CHANGELOG.md`
- Modify: `README.md`

- [ ] **Step 1: Update .gitignore**

Append to `.gitignore`:
```
# Dashboard (Next.js)
dashboard-ui/.next/
dashboard-ui/node_modules/
```

- [ ] **Step 2: Rewrite systemd/claude-dashboard.service**

```ini
[Unit]
Description=claudhaus — Dashboard (Next.js)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/JjayFiles/claude-command-center/dashboard-ui
EnvironmentFile=-%h/JjayFiles/claude-command-center/.env
ExecStartPre=/usr/bin/npm run build
ExecStart=/usr/bin/npm start
Restart=on-failure
RestartSec=10

StandardOutput=append:%h/JjayFiles/claude-command-center/logs/dashboard.log
StandardError=append:%h/JjayFiles/claude-command-center/logs/dashboard.log

[Install]
WantedBy=default.target
```

- [ ] **Step 3: Add dashboard to install-systemd.sh**

In the `UNITS` array in `scripts/install-systemd.sh`, add:
```
claude-dashboard.service
```

After the main service start block, add:
```bash
systemctl --user enable --now claude-dashboard.service
echo "  claude-dashboard.service — enabled + started (http://localhost:3000)"
```

- [ ] **Step 4: Add [0.13.0] to CHANGELOG.md**

Add after `## [Unreleased]`:
```markdown
## [0.13.0] — Dashboard (Next.js) — 2026-04-21

### Added
- `dashboard-ui/` — Next.js 14 App Router dashboard; Void Indigo color system; stat cards (sessions, tasks, skills, memory, connectors, daily notes); live activity feed and scheduled tasks list (SWR, 30 s refresh); skills and connectors panels; served on port 3000
- `dashboard-ui/lib/db.ts` — better-sqlite3 read-only queries for sessions, conversations, scheduled_tasks
- `dashboard-ui/lib/files.ts` — fs-based helpers for memory stats, skills list, connectors list
- Five Next.js API routes: /api/stats, /api/activity, /api/tasks, /api/skills, /api/connectors
- Void Indigo CSS custom properties in globals.css — reusable for landing page and docs
- `systemd/claude-dashboard.service` — runs `npm start` in dashboard-ui/ on port 3000
```

- [ ] **Step 5: Add Dashboard section to README.md**

Add after the "## Configuration reference" section:
```markdown
## Dashboard

A live read-only dashboard served at `http://localhost:3000`.

Shows: active sessions, scheduled tasks, skills, memory size, connectors, daily notes, recent conversation activity.

Auto-refreshes every 30 seconds.

**Start manually:**
```bash
cd dashboard-ui
npm install
npm run build
npm start
```

**Via systemd (after running install-systemd.sh):**
```bash
systemctl --user start claude-dashboard.service
```
```

- [ ] **Step 6: Commit and push**

```bash
git add .gitignore systemd/claude-dashboard.service scripts/install-systemd.sh CHANGELOG.md README.md
git commit -m "feat(dashboard): wiring — systemd service, gitignore, CHANGELOG, README"
git push origin main
```
