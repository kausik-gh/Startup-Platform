import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/api'
import { EmptyState, GateNotice, PageHeader, ROW, StatusPill, TABLE, TD, TH } from '@/components/ModuleState'
import { createLead } from './actions'

export const dynamic = 'force-dynamic'

type LeadRow = {
  id: string
  display_name: string
  email: string | null
  phone: string | null
  status: string
  source: string
  assignee_identity_id: string | null
  created_at?: string
}

const STAGES = ['new', 'contacted', 'qualified', 'won', 'lost']

/** Doc 11 §10.2 Leads — pipeline board. */
export default async function LeadsPage({
  params,
  searchParams,
}: {
  params: { businessId: string }
  searchParams?: { status?: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  const qs = searchParams?.status ? `?status=${encodeURIComponent(searchParams.status)}` : ''
  const res = await apiTry<{ data: LeadRow[]; meta: { pipeline: Record<string, number> } }>(
    `/v1/platform/businesses/${params.businessId}/leads${qs}`,
    token
  )
  if (!res.ok) {
    return (
      <div>
        <PageHeader title="Leads" />
        <GateNotice error={res.error} businessId={params.businessId} moduleLabel="Leads" />
      </div>
    )
  }

  const leads = res.data.data || []
  const pipeline = res.data.meta?.pipeline || {}
  const base = `/b/${params.businessId}/leads`

  return (
    <div>
      <PageHeader
        title="Leads"
        subtitle="Enquiries from capture through to won or lost."
      />

      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        <Link
          href={base}
          style={{
            padding: '0.5rem 0.9rem',
            borderRadius: '8px',
            background: !searchParams?.status ? 'rgba(28,36,48,0.09)' : 'rgba(255,255,255,0.55)',
            border: '1px solid rgba(28,36,48,0.12)',
            textDecoration: 'none',
            color: '#1c2430',
          }}
        >
          All
        </Link>
        {STAGES.map((stage) => (
          <Link
            key={stage}
            href={`${base}?status=${stage}`}
            style={{
              padding: '0.5rem 0.9rem',
              borderRadius: '8px',
              background:
                searchParams?.status === stage ? 'rgba(28,36,48,0.09)' : 'rgba(255,255,255,0.55)',
              border: '1px solid rgba(28,36,48,0.12)',
              textDecoration: 'none',
              color: '#1c2430',
            }}
          >
            {stage}{' '}
            <strong style={{ fontVariantNumeric: 'tabular-nums' }}>{pipeline[stage] ?? 0}</strong>
          </Link>
        ))}
      </div>

      <table style={TABLE}>
        <thead>
          <tr>
            <th style={TH}>Name</th>
            <th style={TH}>Contact</th>
            <th style={TH}>Stage</th>
            <th style={TH}>Source</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr key={lead.id} style={ROW}>
              <td style={TD}>
                <Link href={`${base}/${lead.id}`}>{lead.display_name}</Link>
              </td>
              <td style={TD}>{lead.email || lead.phone || '—'}</td>
              <td style={TD}>
                <StatusPill value={lead.status} />
              </td>
              <td style={TD}>{lead.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {leads.length === 0 ? (
        <EmptyState>
          No leads {searchParams?.status ? `in ${searchParams.status}` : 'yet'}. Add one below, or
          they arrive automatically from website enquiries.
        </EmptyState>
      ) : null}

      <section style={{ marginTop: '2rem', maxWidth: '32rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>Add a lead</h2>
        <form action={createLead} style={{ display: 'grid', gap: '0.6rem' }}>
          <input type="hidden" name="businessId" value={params.businessId} />
          <input name="display_name" placeholder="Name" required style={INPUT} />
          <input name="email" type="email" placeholder="Email" style={INPUT} />
          <input name="phone" placeholder="Phone" style={INPUT} />
          <textarea name="message" placeholder="What are they asking about?" style={INPUT} />
          <button type="submit" style={BUTTON}>
            Add lead
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
  padding: '0.55rem 1rem',
  borderRadius: '6px',
  border: '1px solid rgba(28,36,48,0.25)',
  background: 'rgba(28,36,48,0.9)',
  color: '#f7f3eb',
  font: 'inherit',
  cursor: 'pointer',
  justifySelf: 'start',
}
