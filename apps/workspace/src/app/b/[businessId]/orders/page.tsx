import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/api'
import { GateNotice, PageHeader } from '@/components/ModuleState'

export const dynamic = 'force-dynamic'

type OrderRow = {
  id: string
  order_number: string
  status: string
  payment_status: string
  payment_method: string
  total_amount: number
  currency: string
  created_at?: string
}

/** Doc 11 §4.2 orders — board/list. */
export default async function OrdersBoardPage({
  params,
  searchParams,
}: {
  params: { businessId: string }
  searchParams?: { status?: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')
  const qs = searchParams?.status ? `?status=${encodeURIComponent(searchParams.status)}` : ''
  const res = await apiTry<{ data: OrderRow[] }>(
    `/v1/platform/businesses/${params.businessId}/orders${qs}`,
    token
  )
  if (!res.ok) {
    return (
      <div>
        <PageHeader title="Orders" />
        <GateNotice error={res.error} businessId={params.businessId} moduleLabel="Orders" />
      </div>
    )
  }
  const orders = res.data.data || []

  return (
    <div>
      <h1 style={{ fontSize: '2rem' }}>Orders</h1>
      <p style={{ opacity: 0.8 }}>Board / list — accept, prepare, complete, cancel from detail.</p>
      <div style={{ display: 'flex', gap: '0.5rem', margin: '1rem 0', flexWrap: 'wrap' }}>
        {['', 'pending', 'accepted', 'preparing', 'ready', 'completed', 'cancelled'].map((s) => (
          <Link
            key={s || 'all'}
            href={`/b/${params.businessId}/orders${s ? `?status=${s}` : ''}`}
          >
            {s || 'all'}
          </Link>
        ))}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left', opacity: 0.7 }}>
            <th style={{ padding: '0.4rem' }}>Order</th>
            <th style={{ padding: '0.4rem' }}>Status</th>
            <th style={{ padding: '0.4rem' }}>Payment</th>
            <th style={{ padding: '0.4rem' }}>Total</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} style={{ borderTop: '1px solid rgba(0,0,0,0.1)' }}>
              <td style={{ padding: '0.55rem' }}>
                <Link href={`/b/${params.businessId}/orders/${o.id}`}>{o.order_number}</Link>
              </td>
              <td style={{ padding: '0.55rem' }}>{o.status}</td>
              <td style={{ padding: '0.55rem' }}>
                {o.payment_method} / {o.payment_status}
              </td>
              <td style={{ padding: '0.55rem' }}>
                {o.currency} {o.total_amount}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {orders.length === 0 ? <p style={{ marginTop: '1rem' }}>No orders yet.</p> : null}
    </div>
  )
}
