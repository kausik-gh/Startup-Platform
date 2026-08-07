import Link from 'next/link'
import { redirect } from 'next/navigation'

/** MKT-001 Marketplace Home — search-first entry (Doc 09 §3 / Doc 11 §13.1). */
export default function MarketplaceHomePage({
  searchParams,
}: {
  searchParams?: { q?: string }
}) {
  if (searchParams?.q) {
    redirect(`/search?q=${encodeURIComponent(searchParams.q)}`)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        fontFamily: 'Georgia, "Iowan Old Style", serif',
        background:
          'radial-gradient(circle at 20% 20%, #d9ebe3 0%, transparent 45%), linear-gradient(160deg, #f7f3eb, #e7eef5)',
        padding: '2rem',
      }}
    >
      <div style={{ width: 'min(36rem, 100%)', textAlign: 'center' }}>
        <p style={{ letterSpacing: '0.12em', textTransform: 'uppercase', fontSize: '0.75rem' }}>
          Marketplace
        </p>
        <h1 style={{ fontSize: '2.75rem', margin: '0.5rem 0 0.75rem' }}>Find a local business</h1>
        <p style={{ marginBottom: '1.5rem', lineHeight: 1.5 }}>
          Search joined, discoverable businesses and offerings — then visit their Website for the
          action you need.
        </p>
        <form action="/search" method="get">
          <input
            name="q"
            placeholder="Restaurants, salons, hotels…"
            style={{
              width: '100%',
              padding: '0.9rem 1rem',
              fontSize: '1.1rem',
              border: '1px solid rgba(0,0,0,0.15)',
            }}
          />
          <button type="submit" style={{ marginTop: '0.75rem', padding: '0.7rem 1.25rem' }}>
            Search
          </button>
        </form>
        <p style={{ marginTop: '1.5rem' }}>
          <Link href="/search">Browse with filters</Link>
        </p>
      </div>
    </div>
  )
}
