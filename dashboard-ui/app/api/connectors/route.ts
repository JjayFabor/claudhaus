import { NextResponse } from 'next/server'
import { getConnectors } from '@/lib/files'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json(getConnectors())
}
