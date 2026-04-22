import { describe, it, expect } from 'vitest'
import path from 'path'
import { getAllSlugsFromDir, extractHeadings } from '@/lib/mdx'
import fs from 'fs'
import os from 'os'

describe('getAllSlugsFromDir', () => {
  it('returns slug arrays for MDX files in a directory', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mdx-test-'))
    fs.writeFileSync(path.join(tmp, 'introduction.mdx'), '# Intro')
    fs.mkdirSync(path.join(tmp, 'guides'))
    fs.writeFileSync(path.join(tmp, 'guides', 'quick-start.mdx'), '# Quick Start')

    const slugs = getAllSlugsFromDir(tmp)

    expect(slugs).toContainEqual(['introduction'])
    expect(slugs).toContainEqual(['guides', 'quick-start'])

    fs.rmSync(tmp, { recursive: true })
  })

  it('returns empty array for empty directory', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mdx-empty-'))
    expect(getAllSlugsFromDir(tmp)).toEqual([])
    fs.rmSync(tmp, { recursive: true })
  })
})

describe('extractHeadings', () => {
  it('extracts h1, h2, h3 with ids', () => {
    const md = `# Getting Started\n\n## Prerequisites\n\n### Node.js setup`
    const headings = extractHeadings(md)
    expect(headings).toEqual([
      { id: 'getting-started', text: 'Getting Started', level: 1 },
      { id: 'prerequisites',   text: 'Prerequisites',   level: 2 },
      { id: 'nodejs-setup',    text: 'Node.js setup',   level: 3 },
    ])
  })

  it('handles empty content', () => {
    expect(extractHeadings('')).toEqual([])
  })
})
