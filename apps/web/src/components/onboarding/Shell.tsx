import Link from 'next/link'
import React from 'react'

const STEPS = ['Your business', 'Your website', 'Your tools', 'Done'] as const

/** Shared chrome for the /start onboarding sequence. */
export function OnboardingShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        fontFamily: 'Georgia, "Iowan Old Style", serif',
        background:
          'radial-gradient(circle at 15% 10%, #dbeae2 0%, transparent 42%), linear-gradient(160deg, #f8f4ec, #e8eef5)',
        color: '#1c2430',
        padding: '2rem 1.5rem 4rem',
      }}
    >
      <div style={{ maxWidth: '52rem', margin: '0 auto' }}>
        <header style={{ marginBottom: '2.5rem' }}>
          <Link href="/" style={{ fontSize: '1.05rem', fontWeight: 600, textDecoration: 'none', color: 'inherit' }}>
            Platform
          </Link>
        </header>
        {children}
      </div>
    </div>
  )
}

/** Where the owner is in the sequence. `current` is 1-based. */
export function Steps({ current }: { current: number }) {
  return (
    <ol
      style={{
        display: 'flex',
        gap: '0.5rem',
        listStyle: 'none',
        padding: 0,
        margin: '0 0 1.75rem',
        flexWrap: 'wrap',
        fontFamily: 'system-ui, sans-serif',
        fontSize: '0.82rem',
      }}
    >
      {STEPS.map((label, i) => {
        const n = i + 1
        const done = n < current
        const active = n === current
        return (
          <li
            key={label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '0.35rem 0.8rem 0.35rem 0.5rem',
              borderRadius: '999px',
              border: `1px solid ${active ? '#1c5f57' : 'rgba(28,36,48,0.18)'}`,
              background: active ? '#1c5f57' : done ? 'rgba(28,95,87,0.1)' : 'transparent',
              color: active ? '#fff' : done ? '#1c5f57' : '#67727f',
              fontWeight: active ? 600 : 400,
            }}
          >
            <span
              aria-hidden
              style={{
                width: '1.25rem',
                height: '1.25rem',
                borderRadius: '50%',
                display: 'grid',
                placeItems: 'center',
                fontSize: '0.72rem',
                background: active ? 'rgba(255,255,255,0.22)' : 'rgba(28,36,48,0.08)',
              }}
            >
              {done ? '✓' : n}
            </span>
            {label}
          </li>
        )
      })}
    </ol>
  )
}

/** A recoverable failure inside onboarding, stated plainly. */
export function OnboardingError({
  title,
  code,
  message,
  children,
}: {
  title: string
  code?: string
  message: string
  children?: React.ReactNode
}) {
  return (
    <div
      role="alert"
      style={{
        padding: '1.2rem 1.4rem',
        borderRadius: '10px',
        border: '1px solid #c9776f',
        background: '#f8e9e7',
        maxWidth: '38rem',
      }}
    >
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.15rem', color: '#8d2f24' }}>{title}</h2>
      <p
        style={{
          margin: 0,
          fontFamily: 'system-ui, sans-serif',
          fontSize: '0.93rem',
          lineHeight: 1.6,
          color: '#6f2a21',
        }}
      >
        {message}
        {code ? ` (${code})` : ''}
      </p>
      {children ? <div style={{ marginTop: '0.9rem' }}>{children}</div> : null}
    </div>
  )
}
