import Link from 'next/link'
import { ReactNode } from 'react'

const NAV = [
  { href: '', label: 'Home', id: 'CORE-001' },
  { href: '/profile', label: 'Profile', id: 'CORE-002' },
  { href: '/brand', label: 'Brand & Media', id: 'CORE-003' },
  { href: '/website', label: 'Website', id: 'CORE-004' },
  { href: '/website/pages', label: 'Pages', id: 'CORE-005' },
  { href: '/website/theme', label: 'Theme', id: 'CORE-006' },
  { href: '/website/publish', label: 'Preview & Publish', id: 'CORE-007' },
  { href: '/marketplace', label: 'Marketplace', id: 'CORE-MP' },
  { href: '/orders', label: 'Orders', id: 'ORD-001' },
  { href: '/fulfilment', label: 'Fulfilment', id: 'FUL-001' },
  { href: '/bookings', label: 'Bookings', id: 'BK-001' },
  { href: '/workforce', label: 'Workforce', id: 'WF-001' },
]

export default function WorkspaceBusinessLayout({
  children,
  params,
}: {
  children: ReactNode
  params: { businessId: string }
}) {
  const base = `/b/${params.businessId}`
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '240px 1fr',
        minHeight: '100vh',
        fontFamily: 'Georgia, "Times New Roman", serif',
        background: 'linear-gradient(160deg, #f7f3eb 0%, #e8eef2 100%)',
        color: '#1c2430',
      }}
    >
      <aside
        style={{
          padding: '1.5rem 1rem',
          borderRight: '1px solid rgba(28,36,48,0.12)',
          background: 'rgba(255,255,255,0.55)',
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: '1.25rem', letterSpacing: '0.02em' }}>
          Workspace
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {NAV.map((item) => (
            <Link
              key={item.id}
              href={`${base}${item.href}`}
              style={{
                textDecoration: 'none',
                color: '#1c2430',
                padding: '0.45rem 0.6rem',
                borderRadius: '6px',
                fontSize: '0.95rem',
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main style={{ padding: '2rem' }}>{children}</main>
    </div>
  )
}
