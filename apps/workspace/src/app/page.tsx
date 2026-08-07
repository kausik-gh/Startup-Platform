import Link from 'next/link'

export default function WorkspaceIndexPage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        fontFamily: 'Georgia, serif',
        background: 'linear-gradient(160deg, #f7f3eb 0%, #e8eef2 100%)',
        padding: '2rem',
      }}
    >
      <div style={{ maxWidth: '32rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>Business Workspace</h1>
        <p style={{ lineHeight: 1.5, marginBottom: '1.25rem' }}>
          Open a Business context at <code>/b/&#123;businessId&#125;</code> for Home, Profile, and
          Website management (CORE-001–CORE-007).
        </p>
        <Link href="/login">Sign in to continue</Link>
      </div>
    </div>
  )
}
