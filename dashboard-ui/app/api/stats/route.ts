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
