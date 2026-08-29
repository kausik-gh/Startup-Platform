import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/api'
import { GateNotice, PageHeader } from '@/components/ModuleState'

export const dynamic = 'force-dynamic'

/** Doc 11 §4.2 fulfilment — board/list. */
export default async function FulfilmentBoardPage({
  params,
  searchParams,
}: {
  params: { businessId: string }
  searchParams?: { status?: string; mode?: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')
  const qs = new URLSearchParams()
  if (searchParams?.status) qs.set('status', searchParams.status)
  if (searchParams?.mode) qs.set('mode', searchParams.mode)
  const suffix = qs.toString() ? `?${qs}` : ''
  const [jobsRes, settingsRes] = await Promise.all([
    apiTry<{ data: Array<Record<string, unknown>> }>(
      `/v1/b/${params.businessId}/fulfilment/jobs${suffix}`,
      token
    ),
    apiTry<{ data: { active_modes?: string[]; pickup_enabled: boolean; delivery_enabled: boolean } }>(
      `/v1/b/${params.businessId}/fulfilment/settings`,
      token
    ),
  ])
  if (!jobsRes.ok) {
    return (
      <div>
        <PageHeader title="Fulfilment" />
        <GateNotice error={jobsRes.error} businessId={params.businessId} moduleLabel="Fulfilment" />
      </div>
    )
  }
  const jobs = jobsRes.data.data || []
  const settings = settingsRes.ok
    ? settingsRes.data.data
    : { active_modes: [], pickup_enabled: false, delivery_enabled: false }

  return (
    <div>
      <h1 style={{ fontSize: '2rem' }}>Fulfilment</h1>
      <p style={{ opacity: 0.8 }}>
        Modes: {(settings.active_modes || []).join(', ') || 'none'} ·{' '}
        <Link href={`/b/${params.businessId}/fulfilment/zones`}>Zones & charges</Link>
      </p>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', opacity: 0.7 }}>
            <th style={{ padding: '0.4rem' }}>Job</th>
            <th style={{ padding: '0.4rem' }}>Mode</th>
            <th style={{ padding: '0.4rem' }}>Status</th>
            <th style={{ padding: '0.4rem' }}>Charge</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={String(job.id)} style={{ borderTop: '1px solid rgba(0,0,0,0.1)' }}>
              <td style={{ padding: '0.55rem' }}>
                <Link href={`/b/${params.businessId}/fulfilment/${job.id}`}>
                  {String(job.id).slice(0, 8)}…
                </Link>
              </td>
              <td style={{ padding: '0.55rem' }}>{String(job.mode)}</td>
              <td style={{ padding: '0.55rem' }}>{String(job.status)}</td>
              <td style={{ padding: '0.55rem' }}>
                {String(job.currency)} {String(job.delivery_charge)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {jobs.length === 0 ? <p style={{ marginTop: '1rem' }}>No fulfilment jobs yet.</p> : null}
    </div>
  )
}
