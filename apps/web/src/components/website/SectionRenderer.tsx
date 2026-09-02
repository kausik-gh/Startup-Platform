import Link from 'next/link'
import { OfferingsListSection } from './OfferingsListSection'

type Section = {
  id: string
  section_type_id: string
  layout_variant?: string | null
  content: Record<string, unknown>
  assets?: Record<string, { url: string; alt_text?: string | null }>
}

function pathHref(slug: string, path: string) {
  if (!path || path === '/') return `/${slug}`
  const cleaned = path.startsWith('/') ? path.slice(1) : path
  return `/${slug}/${cleaned}`
}

export function SectionRenderer({
  section,
  businessSlug,
  theme,
}: {
  section: Section
  businessSlug: string
  theme: Record<string, unknown>
}) {
  const primary = String(theme.primary_color || '#0F766E')
  const content = section.content || {}
  // Resolved by the API alongside content (Doc 12 §15.2 — asset indirection).
  const heroImage = section.assets?.image_asset_id

  switch (section.section_type_id) {
    case 'hero':
      return (
        <section
          style={{
            padding: '4rem 1.5rem',
            background: heroImage
              ? `linear-gradient(rgba(0,0,0,0.45), rgba(0,0,0,0.45)), url(${heroImage.url}) center/cover no-repeat`
              : primary,
            color: '#fff',
          }}
        >
          <h1 style={{ fontSize: '2.75rem', marginBottom: '0.75rem' }}>
            {String(content.headline || '')}
          </h1>
          {content.subheadline ? (
            <p style={{ fontSize: '1.15rem', maxWidth: '36rem' }}>
              {String(content.subheadline)}
            </p>
          ) : null}
          {content.cta_label && (content.cta_url || content.cta_path) ? (
            <Link
              href={pathHref(businessSlug, String(content.cta_url || content.cta_path))}
              style={{
                display: 'inline-block',
                marginTop: '1.25rem',
                padding: '0.7rem 1.1rem',
                background: '#fff',
                color: primary,
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              {String(content.cta_label)}
            </Link>
          ) : null}
        </section>
      )
    case 'about':
    case 'text_block':
      return (
        <section style={{ padding: '2.5rem 1.5rem', maxWidth: '48rem', margin: '0 auto' }}>
          {content.title ? <h2>{String(content.title)}</h2> : null}
          {heroImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={heroImage.url}
              alt={heroImage.alt_text || String(content.title || '')}
              style={{ width: '100%', height: 'auto', borderRadius: 8, margin: '0 0 1rem' }}
            />
          ) : null}
          <p style={{ lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>{String(content.body || '')}</p>
        </section>
      )
    case 'contact':
      return (
        <section style={{ padding: '2.5rem 1.5rem', maxWidth: '40rem', margin: '0 auto' }}>
          <h2>{String(content.title || 'Contact')}</h2>
          <p>{String(content.address || '')}</p>
          <p>{String(content.phone || '')}</p>
          <p>{String(content.email || '')}</p>
          <p>{String(content.hours_summary || '')}</p>
        </section>
      )
    case 'offerings_list':
      return (
        <OfferingsListSection
          businessSlug={businessSlug}
          title={String(content.title || 'Offerings')}
          subtitle={content.subtitle ? String(content.subtitle) : undefined}
        />
      )
    case 'cta_band':
      return (
        <section
          style={{
            padding: '2rem 1.5rem',
            background: String(theme.accent_color || '#F59E0B'),
            color: '#111',
            textAlign: 'center',
          }}
        >
          <h2>{String(content.headline || '')}</h2>
          {content.body ? <p>{String(content.body)}</p> : null}
          {content.cta_label && (content.cta_url || content.cta_path) ? (
            <Link href={pathHref(businessSlug, String(content.cta_url || content.cta_path))}>
              {String(content.cta_label)}
            </Link>
          ) : null}
        </section>
      )
    default:
      return (
        <section style={{ padding: '1.5rem', opacity: 0.7 }}>
          Unsupported section type: {section.section_type_id}
        </section>
      )
  }
}
