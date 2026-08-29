import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/api'
import { GateNotice, PageHeader } from '@/components/ModuleState'
import { createWorkforceMember } from './actions'

export const dynamic = 'force-dynamic'

/** Doc 11 §4.2 Workforce — people/providers list (no HR/payroll depth). */
export default async function WorkforcePage({
  params,
}: {
  params: { businessId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')
  const [membersRes, locationsRes] = await Promise.all([
    apiTry<{ data: Array<Record<string, unknown>> }>(
      `/v1/platform/businesses/${params.businessId}/workforce/members`,
      token
    ),
    apiTry<{ data: Array<Record<string, unknown>> }>(
      `/v1/platform/businesses/${params.businessId}/locations`,
      token
    ),
  ])
  if (!membersRes.ok) {
    return (
      <div>
        <PageHeader title="Workforce" />
        <GateNotice error={membersRes.error} businessId={params.businessId} moduleLabel="Workforce" />
      </div>
    )
  }
  const members = membersRes.data.data || []
  const locations = locationsRes.ok ? locationsRes.data.data || [] : []
  const primary = locations.find((l) => l.is_primary) || locations[0]

  async function createMember(formData: FormData) {
    'use server'
    const locationId = String(formData.get('location_id') || primary?.id || '')
    await createWorkforceMember(params.businessId, {
      display_name: String(formData.get('display_name') || '').trim(),
      designation: String(formData.get('designation') || '') || null,
      location_ids: locationId ? [locationId] : [],
      primary_location_id: locationId || null,
    })
  }

  return (
    <div>
      <h1 style={{ fontSize: '2rem' }}>Workforce</h1>
      <p style={{ opacity: 0.8 }}>
        Providers for bookings — identity linkage never grants Workspace access.
      </p>

      <form
        action={createMember}
        style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1.25rem' }}
      >
        <input name="display_name" placeholder="Display name" required />
        <input name="designation" placeholder="Designation" />
        <select name="location_id" defaultValue={String(primary?.id || '')}>
          {locations.map((l) => (
            <option key={String(l.id)} value={String(l.id)}>
              {String(l.name)}
            </option>
          ))}
        </select>
        <button type="submit">Add provider</button>
      </form>

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1.5rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', opacity: 0.7 }}>
            <th style={{ padding: '0.4rem' }}>Name</th>
            <th style={{ padding: '0.4rem' }}>Status</th>
            <th style={{ padding: '0.4rem' }}>Identity linked</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr key={String(m.id)} style={{ borderTop: '1px solid rgba(0,0,0,0.1)' }}>
              <td style={{ padding: '0.55rem' }}>
                <Link href={`/b/${params.businessId}/workforce/${m.id}`}>
                  {String(m.display_name)}
                </Link>
              </td>
              <td style={{ padding: '0.55rem' }}>{String(m.status)}</td>
              <td style={{ padding: '0.55rem' }}>
                {m.identity_id ? 'Yes (no Workspace grant)' : 'No'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {members.length === 0 ? <p style={{ marginTop: '1rem' }}>No providers yet.</p> : null}
    </div>
  )
}
