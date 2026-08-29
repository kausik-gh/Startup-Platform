import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/api'
import {
  EmptyState,
  GateNotice,
  PageHeader,
  ROW,
  StatusPill,
  TABLE,
  TD,
  TH,
} from '@/components/ModuleState'
import { changeMemberRole, grantPermissions, memberLifecycle, removeMember } from './actions'

export const dynamic = 'force-dynamic'

type Member = {
  id: string
  identity_id: string
  role: string
  status: string
  location_scope: string[] | null
  activated_at: string | null
}

const ROLES = ['primary_owner', 'manager', 'member']

/** Doc 09 CORE-010 Team Members. */
export default async function TeamPage({ params }: { params: { businessId: string } }) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  const res = await apiTry<{ data: Member[] }>(
    `/v1/platform/businesses/${params.businessId}/members`,
    token
  )
  if (!res.ok) {
    return (
      <div>
        <PageHeader title="Team" />
        <GateNotice error={res.error} businessId={params.businessId} moduleLabel="Team" />
      </div>
    )
  }
  const members = res.data.data || []

  return (
    <div>
      <PageHeader
        title="Team"
        subtitle="Who can work in this Business, and what each of them can do."
        action={<Link href={`/b/${params.businessId}/team/invitations`}>Invitations →</Link>}
      />

      <p
        style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          background: 'rgba(138,109,31,0.1)',
          border: '1px solid rgba(138,109,31,0.3)',
          marginBottom: '1.25rem',
        }}
      >
        Managers and members start with no permissions until you grant them. Until default role
        permissions are decided, use the grant box on each member below to give them access.
      </p>

      <table style={TABLE}>
        <thead>
          <tr>
            <th style={TH}>Member</th>
            <th style={TH}>Role</th>
            <th style={TH}>Status</th>
            <th style={TH}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.id} style={ROW}>
              <td style={{ ...TD, fontFamily: 'ui-monospace, monospace', fontSize: '0.82rem' }}>
                {member.identity_id}
              </td>
              <td style={TD}>
                {member.role === 'primary_owner' ? (
                  member.role
                ) : (
                  <form action={changeMemberRole} style={{ display: 'flex', gap: '0.35rem' }}>
                    <input type="hidden" name="businessId" value={params.businessId} />
                    <input type="hidden" name="membershipId" value={member.id} />
                    <select name="role" defaultValue={member.role} style={SELECT}>
                      {ROLES.filter((r) => r !== 'primary_owner').map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                    <button type="submit" style={LINK_BUTTON}>
                      Save
                    </button>
                  </form>
                )}
              </td>
              <td style={TD}>
                <StatusPill value={member.status} />
              </td>
              <td style={{ ...TD, display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                {member.role !== 'primary_owner' ? (
                  <>
                    <form action={memberLifecycle}>
                      <input type="hidden" name="businessId" value={params.businessId} />
                      <input type="hidden" name="membershipId" value={member.id} />
                      <input
                        type="hidden"
                        name="action"
                        value={member.status === 'active' ? 'suspend' : 'reactivate'}
                      />
                      <button type="submit" style={LINK_BUTTON}>
                        {member.status === 'active' ? 'Suspend' : 'Reactivate'}
                      </button>
                    </form>
                    <form action={removeMember}>
                      <input type="hidden" name="businessId" value={params.businessId} />
                      <input type="hidden" name="membershipId" value={member.id} />
                      <button type="submit" style={LINK_BUTTON}>
                        Remove
                      </button>
                    </form>
                  </>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {members.length === 0 ? <EmptyState>No team members yet.</EmptyState> : null}

      <section style={{ marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>Grant permissions</h2>
        <p style={{ opacity: 0.8 }}>
          Space- or comma-separated permission ids, for example{' '}
          <code>orders.read bookings.read</code>.
        </p>
        {members
          .filter((member) => member.role !== 'primary_owner')
          .map((member) => (
            <form
              key={member.id}
              action={grantPermissions}
              style={{
                display: 'flex',
                gap: '0.5rem',
                marginBottom: '0.6rem',
                flexWrap: 'wrap',
                alignItems: 'center',
              }}
            >
              <input type="hidden" name="businessId" value={params.businessId} />
              <input type="hidden" name="membershipId" value={member.id} />
              <span
                style={{ fontFamily: 'ui-monospace, monospace', fontSize: '0.78rem', opacity: 0.8 }}
              >
                {member.identity_id.slice(0, 8)}…
              </span>
              <input
                name="permissions"
                placeholder="orders.read bookings.read"
                required
                style={{ ...INPUT, minWidth: '22rem' }}
              />
              <button type="submit" style={BUTTON}>
                Grant
              </button>
            </form>
          ))}
      </section>
    </div>
  )
}

const INPUT: React.CSSProperties = {
  padding: '0.5rem 0.6rem',
  borderRadius: '6px',
  border: '1px solid rgba(28,36,48,0.2)',
  font: 'inherit',
  background: 'rgba(255,255,255,0.75)',
}
const SELECT: React.CSSProperties = { ...INPUT, padding: '0.3rem 0.4rem' }
const BUTTON: React.CSSProperties = {
  padding: '0.5rem 0.9rem',
  borderRadius: '6px',
  border: '1px solid rgba(28,36,48,0.25)',
  background: 'rgba(28,36,48,0.9)',
  color: '#f7f3eb',
  font: 'inherit',
  cursor: 'pointer',
}
const LINK_BUTTON: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#1c2430',
  textDecoration: 'underline',
  cursor: 'pointer',
  font: 'inherit',
  padding: 0,
}
