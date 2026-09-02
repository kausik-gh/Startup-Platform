import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/api'
import { DataTable, EmptyState, FilterTabs, GateNotice, PageHeader, StatusPill } from '@/components/ui'

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
  const base = `/b/${params.businessId}`
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
      <PageHeader title="Orders" subtitle="Accept, prepare, complete, or cancel each order from its detail page." />
      <FilterTabs
        current={searchParams?.status}
        hrefFor={(v) => `${base}/orders${v ? `?status=${v}` : ''}`}
        options={[
          { value: '', label: 'All' },
          { value: 'pending', label: 'Pending' },
          { value: 'accepted', label: 'Accepted' },
          { value: 'preparing', label: 'Preparing' },
          { value: 'ready', label: 'Ready' },
          { value: 'completed', label: 'Completed' },
          { value: 'cancelled', label: 'Cancelled' },
        ]}
      />
      <DataTable
        rows={orders}
        rowKey={(o) => o.id}
        columns={[
          {
            key: 'order_number',
            header: 'Order',
            render: (o) => <Link href={`${base}/orders/${o.id}`}>{o.order_number}</Link>,
          },
          { key: 'status', header: 'Status', render: (o) => <StatusPill value={o.status} /> },
          {
            key: 'payment',
            header: 'Payment',
            render: (o) => (
              <span style={{ color: 'var(--color-muted)' }}>
                {o.payment_method} · {o.payment_status}
              </span>
            ),
          },
          {
            key: 'total',
            header: 'Total',
            align: 'num',
            render: (o) => `${o.currency} ${o.total_amount}`,
          },
        ]}
        empty={
          <EmptyState title="No orders here">
            {searchParams?.status
              ? `Nothing with status "${searchParams.status}" right now.`
              : 'Orders placed on your website land here for you to accept.'}
          </EmptyState>
        }
      />
    </div>
  )
}
