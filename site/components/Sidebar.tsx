'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { NavSection } from '@/lib/nav'

interface SidebarProps {
  nav: NavSection[]
  basePath: '/docs' | '/api-reference'
}

export default function Sidebar({ nav, basePath }: SidebarProps) {
  const pathname = usePathname()

  return (
    <nav className="w-60 flex-shrink-0 hidden lg:block">
      {nav.map(section => (
        <div key={section.title} className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-text-muted mb-3 px-3">
            {section.title}
          </p>
          <ul className="space-y-0.5">
            {section.items.map(item => {
              const href = `${basePath}/${item.slug}`
              const active = pathname === href
              return (
                <li key={item.slug}>
                  <Link
                    href={href}
                    className={`block text-sm px-3 py-1.5 rounded-md transition-colors ${
                      active
                        ? 'bg-accent/10 text-accent font-medium'
                        : 'text-text-muted hover:text-text-primary hover:bg-surface'
                    }`}
                  >
                    {item.title}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </nav>
  )
}
