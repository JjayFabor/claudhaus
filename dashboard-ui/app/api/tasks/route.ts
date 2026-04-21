import { NextResponse } from 'next/server'
import { getScheduledTasks } from '@/lib/db'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json(getScheduledTasks())
}
