import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <p className="text-5xl font-bold text-accent mb-4">404</p>
      <h2 className="text-xl font-semibold text-text-primary mb-2">Page not found</h2>
      <p className="text-sm text-text-muted mb-6">This page doesn&apos;t exist or has been moved.</p>
      <Link
        href="/"
        className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
      >
        Back to home
      </Link>
    </div>
  )
}
