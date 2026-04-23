'use client'
import { useEffect, useState } from 'react'
import type { Heading } from '@/lib/mdx'

export default function Toc({ headings }: { headings: Heading[] }) {
  const [active, setActive] = useState('')

  useEffect(() => {
    if (headings.length === 0) return

    const observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActive(entry.target.id)
            break
          }
        }
      },
      { rootMargin: '-80px 0px -60% 0px' }
    )

    headings.forEach(h => {
      const el = document.getElementById(h.id)
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [headings])

  if (headings.length === 0) return null

  return (
    <aside className="w-52 flex-shrink-0 hidden xl:block">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-text-muted mb-3">
        On this page
      </p>
      <ul className="space-y-1">
        {headings.map(h => (
          <li key={h.id} style={{ paddingLeft: `${(h.level - 1) * 12}px` }}>
            <a
              href={`#${h.id}`}
              className={`block text-xs py-0.5 transition-colors hover:text-text-primary ${
                active === h.id ? 'text-accent font-medium' : 'text-text-muted'
              }`}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </aside>
  )
}
