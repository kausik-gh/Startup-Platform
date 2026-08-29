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
import { createCustomer } from './actions'

export const dynamic = 'force-dynamic'

type CustomerRow = {
  id: string
  display_name: string
  email: string | null
  phone: string | null
  status: string
  tags?: string[]
  created_at?: string
}

/**
 * Doc 11 §9 Customer Relationships.
 *
 * These are Business-owned customer records (Doc 05 CUS-001), which are a
 * different thing from Platform Identities — a person can be a customer of
 * this Business without holding a platform account at all.
 */
export default async function CustomersPage({
  params,
  searchParams,
}: {
  params: { businessId: string }
  searchParams?: { status?: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  const qs = searchParams?.status ? `?status=${encodeURIComponent(searchParams.status)}` : ''
  const res = await apiTry<{ data: CustomerRow[] }>(
    `/v1/platform/businesses/${params.businessId}/customers${qs}`,
    token
  )
  if (!res.ok) {
    return (
      <div>
        <PageHeader title="Customers" />
        <GateNotice error={res.error} businessId={params.businessId} moduleLabel="Customers" />
      </div>
    )
  }
  const customers = res.data.data || []
  const base = `/b/${params.businessId}/customers`

  return (
    <div>
      <PageHeader
        title="Customers"
        subtitle="This Business's own customer records — separate from platform accounts."
      />

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <Link href={base}>All</Link>
        {['active', 'blocked', 'archived'].map((status) => (
          <Link key={status} href={`${base}?status=${status}`}>
            {status}
          </Link>
        ))}
      </div>

      <table style={TABLE}>
        <thead>
          <tr>
            <th style={TH}>Name</th>
            <th style={TH}>Email</th>
            <th style={TH}>Phone</th>
            <th style={TH}>Status</th>
          </tr>
        </thead>
        <tbody>
          {customers.map((customer) => (
            <tr key={customer.id} style={ROW}>
              <td style={TD}>
                <Link href={`${base}/${customer.id}`}>{customer.display_name}</Link>
              </td>
              <td style={TD}>{customer.email || '—'}</td>
              <td style={TD}>{customer.phone || '—'}</td>
              <td style={TD}>
                <StatusPill value={customer.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {customers.length === 0 ? (
        <EmptyState>
          No customer records yet. They are created automatically the first time someone orders or
          books, or you can add one below.
        </EmptyState>
      ) : null}

      <section style={{ marginTop: '2rem', maxWidth: '32rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>Add a customer</h2>
        <form action={createCustomer} style={{ display: 'grid', gap: '0.6rem' }}>
          <input type="hidden" name="businessId" value={params.businessId} />
          <input name="display_name" placeholder="Name" required style={INPUT} />
          <input name="email" type="email" placeholder="Email" style={INPUT} />
          <input name="phone" placeholder="Phone" style={INPUT} />
          <button type="submit" style={BUTTON}>
            Add customer
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
