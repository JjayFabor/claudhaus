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
