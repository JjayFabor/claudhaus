import Link from 'next/link'
import { Database, Pencil, Plug, Bot, Clock, Wrench } from 'lucide-react'

const features = [
  { icon: Database, title: 'Persistent Memory',  desc: 'Remembers facts, preferences, and past context across every session.' },
  { icon: Pencil,   title: 'Teachable Skills',   desc: 'Teach new workflows just by chatting — no config files, no restarts.' },
  { icon: Plug,     title: 'MCP Connectors',     desc: 'Self-installing integrations: GitHub, HubSpot, Slack, and more.' },
  { icon: Bot,      title: 'Sub-agents',         desc: 'Spawn focused specialists with their own workspaces and tool sets.' },
  { icon: Clock,    title: 'Scheduler',           desc: 'Schedule recurring tasks — reports, reminders, status checks.' },
  { icon: Wrench,   title: 'Self-Improving',     desc: 'Main reads and edits its own source code, syntax-checks, and restarts.' },
]

const comparison = [
  { feature: 'Model',            claudhaus: 'Claude-native (Agent SDK)',       openclaw: 'Multi-provider' },
  { feature: 'Setup',            claudhaus: 'One Python file, chat-driven',    openclaw: 'Config files + dashboard' },
  { feature: 'Memory',           claudhaus: 'BM25 search over Markdown',       openclaw: 'None built-in' },
  { feature: 'Integrations',     claudhaus: 'Self-installing MCP connectors',  openclaw: 'Config-file plugins' },
  { feature: 'Skills',           claudhaus: 'Teachable via chat, hot-loaded',  openclaw: 'Static plugins' },
  { feature: 'Sub-agents',       claudhaus: 'Spawnable via chat',              openclaw: 'Not built-in' },
  { feature: 'Self-improvement', claudhaus: 'Edits its own source code',       openclaw: 'No' },
  { feature: 'Target',           claudhaus: 'One person, personal ops',        openclaw: 'Teams, multi-user' },
]

const steps = [
  { n: 1, title: 'Clone & configure',         desc: 'git clone the repo and run the setup wizard. Done in under 5 minutes.' },
  { n: 2, title: 'Connect your Telegram bot', desc: 'Create a bot via BotFather, paste the token. Your agent is live.' },
  { n: 3, title: 'Start chatting',            desc: 'Name it, define its role, connect tools, and teach it your workflows — all by chatting.' },
]

export default function HomePage() {
  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden dot-grid">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[600px] h-[600px] rounded-full bg-accent opacity-[0.06] blur-[120px]" />
        </div>
        <div className="relative mx-auto max-w-4xl px-6 py-28 text-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-text-primary leading-tight tracking-tight">
            Your personal AI agent.<br />Self-hosted. Claude-native.
          </h1>
          <p className="mt-6 text-lg md:text-xl text-text-muted max-w-2xl mx-auto leading-relaxed">
            Send a message from your phone. Get your own AI on the other end — shaped to your role,
            connected to your tools, and getting smarter every conversation.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/docs/introduction"
              className="w-full sm:w-auto px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium transition-colors text-center"
            >
              Get Started →
            </Link>
            <a
              href="https://github.com/JjayFabor/claudhaus"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto px-6 py-3 rounded-lg border border-border hover:border-accent text-text-primary font-medium transition-colors text-center"
            >
              View on GitHub
            </a>
          </div>
          <div className="mt-10 mx-auto max-w-lg text-left">
            <pre className="bg-surface border border-border rounded-lg px-5 py-4 text-sm font-mono text-text-muted overflow-x-auto">
              <code>{`git clone https://github.com/JjayFabor/claudhaus.git
cd claudhaus
python3 scripts/setup.py`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="mx-auto max-w-5xl px-6 py-24">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-12">
          How it compares
        </h2>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface">
                <th className="px-5 py-3 text-left font-medium text-text-muted w-1/3" />
                <th className="px-5 py-3 text-left font-semibold text-accent">claudhaus</th>
                <th className="px-5 py-3 text-left font-medium text-text-muted">OpenClaw</th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((row, i) => (
                <tr
                  key={row.feature}
                  className={`border-b border-border last:border-0 ${i % 2 !== 0 ? 'bg-surface/40' : ''}`}
                >
                  <td className="px-5 py-3 font-medium text-text-muted">{row.feature}</td>
                  <td className="px-5 py-3 text-text-primary">
                    <span className="text-accent mr-1.5">✓</span>{row.claudhaus}
                  </td>
                  <td className="px-5 py-3 text-text-muted">{row.openclaw}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Feature cards */}
      <section className="mx-auto max-w-5xl px-6 py-12">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-12">
          Everything you need
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-lg border border-border bg-surface p-6">
              <div className="w-8 h-8 rounded-md bg-accent/10 flex items-center justify-center mb-4">
                <Icon size={16} className="text-accent" />
              </div>
              <h3 className="font-semibold text-text-primary mb-1 text-sm">{title}</h3>
              <p className="text-sm text-text-muted leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-4xl px-6 py-24">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-16">
          How it works
        </h2>
        <div className="flex flex-col md:flex-row items-start gap-8 md:gap-4">
          {steps.map((step, i) => (
            <div key={step.n} className="flex-1 flex flex-col items-start gap-3">
              <div className="flex items-center gap-4 w-full">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-accent text-white text-sm font-bold flex items-center justify-center">
                  {step.n}
                </span>
                {i < steps.length - 1 && (
                  <div className="hidden md:block flex-1 h-px bg-border" />
                )}
              </div>
              <h3 className="font-semibold text-text-primary text-sm">{step.title}</h3>
              <p className="text-sm text-text-muted leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
