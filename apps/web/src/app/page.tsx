import Link from 'next/link'
import { getAccessToken } from '@/lib/supabase/access-token'
import { listMyBusinesses, type BusinessSummary } from '@/lib/platform-api'

export const dynamic = 'force-dynamic'

const WORKSPACE_URL = process.env.NEXT_PUBLIC_WORKSPACE_URL || 'http://localhost:3001'

const PAGE: React.CSSProperties = {
  minHeight: '100vh',
  fontFamily: 'Georgia, "Iowan Old Style", serif',
  background:
    'radial-gradient(circle at 15% 10%, #dbeae2 0%, transparent 42%), linear-gradient(160deg, #f8f4ec, #e8eef5)',
  color: '#1c2430',
  padding: '2rem 1.5rem 4rem',
}
const SHELL: React.CSSProperties = { maxWidth: '58rem', margin: '0 auto' }
const CARD: React.CSSProperties = {
  display: 'block',
  padding: '1.5rem 1.6rem',
  borderRadius: '12px',
  border: '1px solid rgba(28,36,48,0.14)',
  background: 'rgba(255,255,255,0.72)',
  textDecoration: 'none',
  color: 'inherit',
}
const PRIMARY_BTN: React.CSSProperties = {
  display: 'inline-block',
  padding: '0.7rem 1.4rem',
  borderRadius: '8px',
  background: '#1c5f57',
  color: '#fff',
  textDecoration: 'none',
  fontWeight: 600,
  fontFamily: 'system-ui, sans-serif',
  fontSize: '0.95rem',
}

function Masthead({ signedIn = false }: { signedIn?: boolean }) {
  return (
    <header
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '1rem',
        flexWrap: 'wrap',
        marginBottom: '3rem',
      }}
    >
      <span style={{ fontSize: '1.15rem', fontWeight: 600 }}>Platform</span>
      <nav
        style={{
          display: 'flex',
          gap: '1.25rem',
          alignItems: 'center',
          fontFamily: 'system-ui, sans-serif',
          fontSize: '0.9rem',
        }}
      >
        <Link href="/marketplace">Marketplace</Link>
        <Link href="/activity">My activity</Link>
        {signedIn ? (
          <form action="/auth/logout" method="post" style={{ margin: 0 }}>
            <button
              type="submit"
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                font: 'inherit',
                color: '#1c5f57',
                textDecoration: 'underline',
                cursor: 'pointer',
              }}
            >
              Sign out
            </button>
          </form>
        ) : (
          <Link href="/login">Sign in</Link>
        )}
      </nav>
    </header>
  )
}

/** Signed in, and they already run at least one Business. */
function OwnerHome({ businesses }: { businesses: BusinessSummary[] }) {
  return (
    <div style={PAGE}>
      <div style={SHELL}>
        <Masthead signedIn />
        <h1 style={{ fontSize: '2.1rem', margin: '0 0 0.4rem' }}>Your businesses</h1>
        <p style={{ color: '#4c5967', margin: '0 0 2rem', lineHeight: 1.6 }}>
          Open a Workspace to manage your website, offerings, orders and bookings.
        </p>

        <div style={{ display: 'grid', gap: '0.9rem' }}>
          {businesses.map((b) => (
            <a key={b.id} href={`${WORKSPACE_URL}/b/${b.id}`} style={CARD}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>{b.display_name}</div>
                  <div
                    style={{
                      fontFamily: 'system-ui, sans-serif',
                      fontSize: '0.85rem',
                      color: '#4c5967',
                      marginTop: '0.2rem',
                    }}
                  >
                    /{b.slug}
                    {b.business_type ? ` · ${b.business_type.replace(/_/g, ' ')}` : ''}
                    {b.state && b.state !== 'active' ? ` · ${b.state}` : ''}
                  </div>
                </div>
                <span style={{ alignSelf: 'center', fontFamily: 'system-ui, sans-serif', fontWeight: 600 }}>
                  Open Workspace →
                </span>
              </div>
            </a>
          ))}
        </div>

        <div
          style={{
            marginTop: '2.5rem',
            display: 'flex',
            gap: '1.5rem',
            flexWrap: 'wrap',
            fontFamily: 'system-ui, sans-serif',
            fontSize: '0.92rem',
          }}
        >
          <Link href="/start">+ Add another business</Link>
          <Link href="/marketplace">Browse the marketplace</Link>
        </div>
      </div>
    </div>
  )
}

/** Everyone else: the actual front door. */
function LandingHome() {
  return (
    <div style={PAGE}>
      <div style={SHELL}>
        <Masthead />

        <h1 style={{ fontSize: 'clamp(2rem, 5vw, 2.9rem)', lineHeight: 1.15, margin: '0 0 1rem' }}>
          Everything a local business needs to be found and to sell — in one place.
        </h1>
        <p
          style={{
            fontSize: '1.15rem',
            lineHeight: 1.65,
            color: '#3c4855',
            maxWidth: '42rem',
            margin: '0 0 2.75rem',
          }}
        >
          Set up your business and you get a real website, a listing customers can find you
          through, and working orders, bookings and payments. No separate tools to stitch
          together.
        </p>

        <div
          style={{
            display: 'grid',
            gap: '1.1rem',
            gridTemplateColumns: 'repeat(auto-fit, minmax(17rem, 1fr))',
          }}
        >
          <Link href="/start" style={{ ...CARD, borderColor: '#1c5f57', borderWidth: '2px' }}>
            <h2 style={{ fontSize: '1.3rem', margin: '0 0 0.5rem' }}>I run a business</h2>
            <p
              style={{
                fontFamily: 'system-ui, sans-serif',
                fontSize: '0.94rem',
                lineHeight: 1.6,
                color: '#3c4855',
                margin: '0 0 1.1rem',
              }}
            >
              Tell us what you do. We build your website, then recommend the tools that fit
              your kind of business so you can start taking orders or bookings.
            </p>
            <span style={PRIMARY_BTN}>Set up my business</span>
          </Link>

          <Link href="/marketplace" style={CARD}>
            <h2 style={{ fontSize: '1.3rem', margin: '0 0 0.5rem' }}>Browse businesses</h2>
            <p
              style={{
                fontFamily: 'system-ui, sans-serif',
                fontSize: '0.94rem',
                lineHeight: 1.6,
                color: '#3c4855',
                margin: '0 0 1.1rem',
              }}
            >
              Find local businesses, see what they offer, and order or book directly — no
              account needed to look around.
            </p>
            <span
              style={{
                ...PRIMARY_BTN,
                background: 'transparent',
                color: '#1c5f57',
                border: '1px solid #1c5f57',
              }}
            >
              Open the marketplace
            </span>
          </Link>
        </div>

        <p
          style={{
            marginTop: '2.5rem',
            fontFamily: 'system-ui, sans-serif',
            fontSize: '0.9rem',
            color: '#4c5967',
          }}
        >
          Already set up? <Link href="/login">Sign in</Link>.
        </p>
      </div>
    </div>
  )
}

export default async function HomePage() {
  const token = await getAccessToken()
  if (!token) return <LandingHome />

  // Signed in: send owners to something useful rather than the generic pitch.
  // A failed lookup falls back to the landing page rather than erroring.
  const businesses = await listMyBusinesses(token)
  const open = businesses.filter((b) => b.state !== 'closed')
  if (open.length > 0) return <OwnerHome businesses={open} />
  return <LandingHome />
}
