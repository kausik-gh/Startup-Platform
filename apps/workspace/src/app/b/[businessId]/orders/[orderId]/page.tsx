import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiGet } from '@/lib/api'
import { advanceOrderStatus, cancelOrder } from '../actions'

export const dynamic = 'force-dynamic'

/** Doc 11 §4.2 order detail — state actions, cancel coordination. */
export default async function OrderDetailPage({
  params,
}: {
  params: { businessId: string; orderId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')
  const res = await apiGet<{
    data: {
      id: string
      order_number: string
      status: string
      payment_status: string
      payment_method: string
      total_amount: number
      currency: string
      items?: Array<{ title: string; quantity: number; line_total: number }>
    }
  }>(`/v1/platform/businesses/${params.businessId}/orders/${params.orderId}`, token)
  const order = res.data
  const nextByStatus: Record<string, string[]> = {
    pending: ['accepted', 'rejected'],
    accepted: ['preparing'],
    preparing: ['ready'],
    ready: ['completed'],
  }
  const next = nextByStatus[order.status] || []

  return (
    <div>
      <Link href={`/b/${params.businessId}/orders`}>← Orders</Link>
      <h1 style={{ fontSize: '2rem', marginTop: '0.75rem' }}>{order.order_number}</h1>
      <p>
        Status: <strong>{order.status}</strong> · Payment: {order.payment_method} /{' '}
        {order.payment_status}
      </p>
      <p>
        Total: {order.currency} {order.total_amount}
      </p>
      <section style={{ marginTop: '1.25rem' }}>
        <h2>Items</h2>
        <ul>
          {(order.items || []).map((item, idx) => (
            <li key={idx}>
              {item.title} × {item.quantity} — {item.line_total}
            </li>
          ))}
        </ul>
      </section>
      <section style={{ marginTop: '1.25rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {next.map((status) => (
          <form key={status} action={advanceOrderStatus}>
            <input type="hidden" name="businessId" value={params.businessId} />
            <input type="hidden" name="orderId" value={params.orderId} />
            <input type="hidden" name="status" value={status} />
            {status === 'rejected' ? (
              <input type="hidden" name="reason" value="Rejected by Business" />
            ) : null}
            <button type="submit">{status}</button>
          </form>
        ))}
        {['pending', 'accepted', 'preparing', 'ready'].includes(order.status) ? (
          <form action={cancelOrder}>
            <input type="hidden" name="businessId" value={params.businessId} />
            <input type="hidden" name="orderId" value={params.orderId} />
            <input type="hidden" name="reason" value="Cancelled from Workspace" />
            <button type="submit">Cancel order</button>
          </form>
        ) : null}
      </section>
      <p style={{ marginTop: '1.5rem', opacity: 0.75 }}>
        Refunds: use Payments module transaction detail when a payment attempt exists.
      </p>
    </div>
  )
}
