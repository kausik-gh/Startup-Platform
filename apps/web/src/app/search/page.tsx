import Link from 'next/link'
import { fetchSearch } from '@/lib/marketplace-api'

export const dynamic = 'force-dynamic'

export default async function SearchPage({
  searchParams,
}: {
  searchParams?: { q?: string; location?: string; type?: string }
}) {
  const q = searchParams?.q || ''
  const location = searchParams?.location || ''
  const type = searchParams?.type || ''
  const data = await fetchSearch({
    q: q || undefined,
    location: location || undefined,
    type: type || undefined,
  })

  return (
    <div
      style={{
        minHeight: '100vh',
        fontFamily: 'Georgia, "Iowan Old Style", serif',
        background: 'linear-gradient(165deg, #f4f7f2 0%, #eef2f7 100%)',
        color: '#152028',
        padding: '2rem 1.25rem 4rem',
      }}
    >
      <div style={{ maxWidth: '52rem', margin: '0 auto' }}>
        <p style={{ letterSpacing: '0.08em', textTransform: 'uppercase', fontSize: '0.75rem' }}>
          Marketplace · MKT-002 / MKT-004 / MKT-005
        </p>
        <h1 style={{ fontSize: '2.4rem', margin: '0.4rem 0 1rem' }}>Search</h1>
        <form method="get" style={{ display: 'grid', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <input
            name="q"
            defaultValue={q}
            placeholder="Search businesses and offerings"
            style={{ padding: '0.75rem 0.9rem', fontSize: '1.05rem' }}
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '0.5rem' }}>
            <input
              name="location"
              defaultValue={location}
              placeholder="Location / city"
              style={{ padding: '0.6rem 0.8rem' }}
            />
            <input
              name="type"
              defaultValue={type}
              placeholder="Type (retail, restaurant…)"
              style={{ padding: '0.6rem 0.8rem' }}
            />
            <button type="submit" style={{ padding: '0.6rem 1rem' }}>
              Search
            </button>
          </div>
        </form>

        {data.state === 'sparse_market' ? (
          <section>
            <h2>Marketplace is just getting started</h2>
            <p>Few or no businesses are discoverable yet. Try again soon.</p>
          </section>
        ) : null}

        {data.state === 'no_results' ? (
          <section>
            <h2>No results</h2>
            <p>Try a different query, location, or business type.</p>
          </section>
        ) : null}

        {data.businesses.length > 0 ? (
          <section style={{ marginBottom: '2rem' }}>
            <h2>Businesses</h2>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '0.75rem' }}>
              {data.businesses.map((b) => (
                <li
                  key={b.business_id}
                  style={{
                    background: 'rgba(255,255,255,0.75)',
                    border: '1px solid rgba(21,32,40,0.1)',
                    padding: '1rem',
                  }}
                >
                  <Link href={`/marketplace/${b.slug}`} style={{ fontWeight: 700, fontSize: '1.15rem' }}>
                    {b.display_name}
                  </Link>
                  <div style={{ opacity: 0.75, marginTop: '0.25rem' }}>
                    {[b.business_type, b.city].filter(Boolean).join(' · ')}
                  </div>
                  {b.description ? <p style={{ marginTop: '0.5rem' }}>{b.description}</p> : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {data.offerings.length > 0 ? (
          <section>
            <h2>Offerings</h2>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '0.75rem' }}>
              {data.offerings.map((o) => (
                <li
                  key={o.id}
                  style={{
                    background: 'rgba(255,255,255,0.75)',
                    border: '1px solid rgba(21,32,40,0.1)',
                    padding: '1rem',
                  }}
                >
                  <div style={{ fontWeight: 700 }}>{o.title}</div>
                  <div style={{ opacity: 0.75 }}>
                    {o.offering_type}
                    {o.price_from != null ? ` · ${o.currency || ''} ${o.price_from}` : ''}
                  </div>
                  {o.business_slug ? (
                    <Link href={`/marketplace/${o.business_slug}?offering_id=${o.id}&intent=offering`}>
                      View business
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  )
}
