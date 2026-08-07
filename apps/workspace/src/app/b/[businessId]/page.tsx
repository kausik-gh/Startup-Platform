import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiGet } from '@/lib/api'

export const dynamic = 'force-dynamic'

type WebsiteResponse = {
  data: {
    website: { status: string }
    draft: { pages: { id: string; title: string }[]; generated_by?: string | null }
  }
}

export default async function WorkspaceHomePage({
  params,
}: {
  params: { businessId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  let websiteStatus = 'draft'
  let pageCount = 0
  let generatedBy: string | null = null
  try {
    const website = await apiGet<WebsiteResponse>(
      `/v1/b/${params.businessId}/website`,
      token
    )
    websiteStatus = website.data.website.status
    pageCount = website.data.draft.pages.length
    generatedBy = website.data.draft.generated_by ?? null
  } catch {
    // Adaptive home still renders setup guidance if website fetch fails.
  }

  const base = `/b/${params.businessId}`
  return (
    <div>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Workspace Home</h1>
      <p style={{ maxWidth: '42rem', marginBottom: '1.5rem', lineHeight: 1.5 }}>
        Adaptive priorities for this Business. Resume setup, preview your draft Website, and
        publish when readiness checks pass.
      </p>
      <div style={{ display: 'grid', gap: '1rem', maxWidth: '40rem' }}>
        <section
          style={{
            padding: '1rem 1.25rem',
            background: 'rgba(255,255,255,0.7)',
            border: '1px solid rgba(28,36,48,0.1)',
          }}
        >
          <h2 style={{ fontSize: '1.1rem', marginBottom: '0.35rem' }}>Website status</h2>
          <p>
            {websiteStatus} · {pageCount} draft pages
            {generatedBy ? ` · generated via ${generatedBy}` : ''}
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem' }}>
            <Link href={`${base}/website`}>Website overview</Link>
            <Link href={`${base}/website/publish`}>Preview & publish</Link>
          </div>
        </section>
        <section
          style={{
            padding: '1rem 1.25rem',
            background: 'rgba(255,255,255,0.7)',
            border: '1px solid rgba(28,36,48,0.1)',
          }}
        >
          <h2 style={{ fontSize: '1.1rem', marginBottom: '0.35rem' }}>Next steps</h2>
          <ul style={{ margin: 0, paddingLeft: '1.2rem', lineHeight: 1.6 }}>
            <li>
              <Link href={`${base}/profile`}>Complete Business Profile</Link>
            </li>
            <li>
              <Link href={`${base}/website/pages`}>Edit structured Website pages</Link>
            </li>
            <li>
              <Link href={`${base}/brand`}>Add brand media</Link>
            </li>
          </ul>
        </section>
      </div>
    </div>
  )
}
