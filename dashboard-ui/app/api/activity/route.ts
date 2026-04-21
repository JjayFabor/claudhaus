import { NextResponse } from 'next/server'
import { getRecentActivity } from '@/lib/db'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json(getRecentActivity(15))
}
