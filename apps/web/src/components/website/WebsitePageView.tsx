import Link from 'next/link'
import { SectionRenderer } from './SectionRenderer'
import type { PublicWebsitePayload } from '@/lib/public-website'

export function WebsitePageView({ data }: { data: PublicWebsitePayload }) {
  const theme = data.theme || {}
  const title = data.page.seo_title || `${data.page.title} | ${data.business.display_name}`

  return (
    <div
      style={{
        minHeight: '100vh',
        fontFamily: 'Georgia, "Iowan Old Style", serif',
        background: '#faf8f4',
        color: '#1a1f24',
      }}
    >
      {data.is_preview ? (
        <div
          style={{
            background: '#111827',
            color: '#fff',
            padding: '0.5rem 1rem',
            fontSize: '0.85rem',
          }}
        >
          Preview mode — not publicly cached
        </div>
      ) : null}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1rem 1.5rem',
          borderBottom: '1px solid rgba(0,0,0,0.08)',
        }}
      >
        <strong>{data.business.display_name}</strong>
        <nav style={{ display: 'flex', gap: '1rem' }}>
          {(data.navigation || []).map((item) => {
            const href =
              !item.path || item.path === '/'
                ? `/${data.business.slug}`
                : `/${data.business.slug}${item.path.startsWith('/') ? item.path : `/${item.path}`}`
            return (
              <Link key={`${item.label}-${item.path}`} href={href} style={{ textDecoration: 'none' }}>
                {item.label}
              </Link>
            )
          })}
        </nav>
      </header>
      <main>
        <title>{title}</title>
        {data.page.sections.map((section) => (
          <SectionRenderer
            key={section.id}
            section={section}
            businessSlug={data.business.slug}
            theme={theme}
          />
        ))}
      </main>
    </div>
  )
}
