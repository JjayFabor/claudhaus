import { describe, it, expect } from 'vitest'
import { docsNav, apiNav } from '@/lib/nav'

describe('docsNav', () => {
  it('is a non-empty array', () => {
    expect(Array.isArray(docsNav)).toBe(true)
    expect(docsNav.length).toBeGreaterThan(0)
  })

  it('every section has a title and items array', () => {
    for (const section of docsNav) {
      expect(typeof section.title).toBe('string')
      expect(Array.isArray(section.items)).toBe(true)
      expect(section.items.length).toBeGreaterThan(0)
    }
  })

  it('every item has a title and slug string', () => {
    for (const section of docsNav) {
      for (const item of section.items) {
        expect(typeof item.title).toBe('string')
        expect(typeof item.slug).toBe('string')
        expect(item.slug.length).toBeGreaterThan(0)
      }
    }
  })

  it('contains introduction slug', () => {
    const all = docsNav.flatMap(s => s.items.map(i => i.slug))
    expect(all).toContain('introduction')
  })
})

describe('apiNav', () => {
  it('is a non-empty array', () => {
    expect(Array.isArray(apiNav)).toBe(true)
    expect(apiNav.length).toBeGreaterThan(0)
  })

  it('contains overview slug', () => {
    const all = apiNav.flatMap(s => s.items.map(i => i.slug))
    expect(all).toContain('overview')
  })
})
