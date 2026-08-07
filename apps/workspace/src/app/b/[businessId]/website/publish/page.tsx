import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiGet } from '@/lib/api'
import { publishWebsite, generatePreviewToken } from './actions'

export const dynamic = 'force-dynamic'

type WebsiteResponse = {
  data: {
    website: { status: string }
    draft: { pages: { slug: string; title: string }[]; generated_by?: string | null }
  }
}

export default async function WebsitePublishPage({
  params,
}: {
  params: { businessId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')
  const res = await apiGet<WebsiteResponse>(`/v1/b/${params.businessId}/website`, token)

  return (
    <div>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Preview & Publish</h1>
      <p style={{ marginBottom: '1rem', maxWidth: '42rem' }}>
        CORE-007 — preview renders the draft via a short-lived token. Publish copies the draft to
        a published version after readiness validation. Generation never auto-publishes.
      </p>
      <p>
        Current status: <strong>{res.data.website.status}</strong>
      </p>
      <ul>
        {res.data.draft.pages.map((p) => (
          <li key={p.slug}>
            {p.title} /{p.slug}
          </li>
        ))}
      </ul>
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
        <form action={generatePreviewToken}>
          <input type="hidden" name="businessId" value={params.businessId} />
          <button type="submit">Get preview link</button>
        </form>
        <form action={publishWebsite}>
          <input type="hidden" name="businessId" value={params.businessId} />
          <button type="submit">Publish</button>
        </form>
        <Link href={`/b/${params.businessId}/website`}>Back to overview</Link>
      </div>
    </div>
  )
}
