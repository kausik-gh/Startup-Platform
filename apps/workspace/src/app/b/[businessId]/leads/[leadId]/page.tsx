import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/api'
import { GateNotice, PageHeader, StatusPill } from '@/components/ModuleState'
import { addLeadNote, moveLeadStage } from '../actions'

export const dynamic = 'force-dynamic'

type LeadDetail = {
  id: string
  display_name: string
  email: string | null
  phone: string | null
  message: string | null
  status: string
  source: string
  lost_reason: string | null
  customer_contact_id: string | null
  status_history: Array<{ from_status: string | null; to_status: string; created_at: string }>
  notes: Array<{ id: string; body: string; created_at: string }>
}

// Doc 11 §10.2: won is terminal; lost can reopen.
const NEXT_STAGE: Record<string, string[]> = {
  new: ['contacted', 'qualified', 'won', 'lost'],
  contacted: ['qualified', 'won', 'lost'],
  qualified: ['won', 'lost'],
  lost: ['new', 'contacted', 'qualified'],
  won: [],
}

export default async function LeadDetailPage({
  params,
}: {
  params: { businessId: string; leadId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  const res = await apiTry<{ data: LeadDetail }>(
    `/v1/platform/businesses/${params.businessId}/leads/${params.leadId}`,
    token
  )
  if (!res.ok) {
    return (
      <div>
        <Link href={`/b/${params.businessId}/leads`}>← Leads</Link>
        <PageHeader title="Lead" />
        <GateNotice error={res.error} businessId={params.businessId} moduleLabel="Leads" />
      </div>
    )
  }

  const lead = res.data.data
  const next = NEXT_STAGE[lead.status] ?? []

  return (
    <div>
      <Link href={`/b/${params.businessId}/leads`}>← Leads</Link>
      <PageHeader
        title={lead.display_name}
        subtitle={[lead.email, lead.phone].filter(Boolean).join(' · ') || undefined}
      />

      <p>
        Stage: <StatusPill value={lead.status} /> · Source: {lead.source}
      </p>
      {lead.lost_reason ? <p>Lost because: {lead.lost_reason}</p> : null}
      {lead.message ? <p style={{ opacity: 0.85 }}>“{lead.message}”</p> : null}
      {lead.customer_contact_id ? (
        <p>
          Converted to{' '}
          <Link href={`/b/${params.businessId}/customers/${lead.customer_contact_id}`}>
            a customer record
          </Link>
          .
        </p>
      ) : null}

      <section style={{ marginTop: '1.5rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>Move stage</h2>
        {next.length === 0 ? (
          <p style={{ opacity: 0.8 }}>
            Won is the final stage — this lead stays on record as history.
          </p>
        ) : (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {next.map((stage) => (
              <form key={stage} action={moveLeadStage}>
                <input type="hidden" name="businessId" value={params.businessId} />
                <input type="hidden" name="leadId" value={params.leadId} />
                <input type="hidden" name="status" value={stage} />
                {stage === 'lost' ? (
                  <input
                    name="reason"
                    placeholder="Reason (required)"
                    required
                    style={{ ...INPUT, marginRight: '0.35rem' }}
                  />
                ) : null}
                <button type="submit" style={BUTTON}>
                  {stage}
                </button>
              </form>
            ))}
          </div>
        )}
      </section>

      <section style={{ marginTop: '1.75rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>History</h2>
        <ol style={{ paddingLeft: '1.1rem' }}>
          {lead.status_history.map((event, idx) => (
            <li key={idx} style={{ marginBottom: '0.3rem' }}>
              {event.from_status ? `${event.from_status} → ` : 'created as '}
              <strong>{event.to_status}</strong>
              <span style={{ opacity: 0.6 }}> · {new Date(event.created_at).toLocaleString()}</span>
            </li>
          ))}
        </ol>
      </section>

      <section style={{ marginTop: '1.75rem', maxWidth: '32rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>Notes</h2>
        {lead.notes.length === 0 ? <p style={{ opacity: 0.8 }}>No notes yet.</p> : null}
        <ul style={{ paddingLeft: '1.1rem' }}>
          {lead.notes.map((note) => (
            <li key={note.id} style={{ marginBottom: '0.4rem' }}>
              {note.body}
              <span style={{ opacity: 0.6 }}> · {new Date(note.created_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
        <form action={addLeadNote} style={{ display: 'grid', gap: '0.5rem', marginTop: '0.75rem' }}>
          <input type="hidden" name="businessId" value={params.businessId} />
          <input type="hidden" name="leadId" value={params.leadId} />
          <textarea name="body" placeholder="Add a note" required style={INPUT} />
          <button type="submit" style={BUTTON}>
            Add note
          </button>
        </form>
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

const BUTTON: React.CSSProperties = {
  padding: '0.5rem 0.9rem',
  borderRadius: '6px',
  border: '1px solid rgba(28,36,48,0.25)',
  background: 'rgba(28,36,48,0.9)',
  color: '#f7f3eb',
  font: 'inherit',
  cursor: 'pointer',
  justifySelf: 'start',
}
