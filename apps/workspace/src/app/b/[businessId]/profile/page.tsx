import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiGet } from '@/lib/api'

export const dynamic = 'force-dynamic'

type ProfileResponse = {
  data: {
    display_name?: string
    tagline?: string | null
    description?: string | null
    contact?: Record<string, unknown>
  }
}

export default async function BusinessProfilePage({
  params,
}: {
  params: { businessId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  let profile: ProfileResponse['data'] | null = null
  try {
    const res = await apiGet<ProfileResponse>(
      `/v1/platform/businesses/${params.businessId}/profile`,
      token
    )
    profile = res.data
  } catch {
    profile = null
  }

  return (
    <div>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Business Profile</h1>
      <p style={{ marginBottom: '1.25rem' }}>
        Canonical public facts for your Business (CORE-002).
      </p>
      {profile ? (
        <dl style={{ maxWidth: '36rem', lineHeight: 1.6 }}>
          <dt style={{ fontWeight: 700 }}>Display name</dt>
          <dd>{profile.display_name || '—'}</dd>
          <dt style={{ fontWeight: 700, marginTop: '0.75rem' }}>Tagline</dt>
          <dd>{profile.tagline || '—'}</dd>
          <dt style={{ fontWeight: 700, marginTop: '0.75rem' }}>Description</dt>
          <dd>{profile.description || '—'}</dd>
        </dl>
      ) : (
        <p>Profile could not be loaded.</p>
      )}
    </div>
  )
}
