import Link from 'next/link'

export default function AdminHomePage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        background: '#0f1419',
        color: '#e8eef4',
        padding: '2rem',
      }}
    >
      <div style={{ maxWidth: '28rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>Platform Super Admin</h1>
        <p style={{ opacity: 0.8, marginBottom: '1.25rem' }}>
          Platform recovery and indexing operations.
        </p>
        <Link href="/marketplace/indexing" style={{ color: '#9fd0ff' }}>
          Marketplace indexing health
        </Link>
      </div>
    </div>
  )
}
