import fs from 'fs'
import path from 'path'

const ROOT = path.join(process.cwd(), '..')
const WORKSPACE = path.join(ROOT, 'workspaces', 'main')
const SKILLS_DIR = path.join(ROOT, 'agents', 'main', 'skills')

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
  playwright:   'Playwright — browser automation: navigate, screenshot, click, fill forms, scrape',
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
