import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiGet } from '@/lib/api'
import { updateBookingsPolicy } from './actions'

export const dynamic = 'force-dynamic'

/** Doc 11 §4.2 Bookings — list/calendar + policies. */
export default async function BookingsPage({
  params,
  searchParams,
}: {
  params: { businessId: string }
  searchParams?: { status?: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')
  const qs = searchParams?.status ? `?status=${encodeURIComponent(searchParams.status)}` : ''
  const [listRes, policyRes] = await Promise.all([
    apiGet<{ data: Array<Record<string, unknown>> }>(
      `/v1/platform/businesses/${params.businessId}/bookings${qs}`,
      token
    ),
    apiGet<{
      data: {
        require_deposit: boolean
        deposit_amount: number | null
        cancel_window_hours: number
      }
    }>(`/v1/platform/businesses/${params.businessId}/bookings-policy`, token),
  ])
  const bookings = listRes.data || []
  const policy = policyRes.data

  async function savePolicy(formData: FormData) {
    'use server'
    await updateBookingsPolicy(params.businessId, {
      require_deposit: formData.get('require_deposit') === 'on',
      deposit_amount: formData.get('deposit_amount')
        ? Number(formData.get('deposit_amount'))
        : null,
      cancel_window_hours: Number(formData.get('cancel_window_hours') || 24),
    })
  }

  return (
    <div>
      <h1 style={{ fontSize: '2rem' }}>Bookings</h1>
      <p style={{ opacity: 0.8 }}>Calendar/list · confirmation & cancellation</p>

      <section style={{ marginTop: '1.5rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>Policies</h2>
        <form action={savePolicy} style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <label>
            <input
              type="checkbox"
              name="require_deposit"
              defaultChecked={policy.require_deposit}
            />{' '}
            Require deposit
          </label>
          <label>
            Deposit amount{' '}
            <input
              name="deposit_amount"
              type="number"
              step="0.01"
              defaultValue={policy.deposit_amount ?? ''}
            />
          </label>
          <label>
            Cancel window (hours){' '}
            <input
              name="cancel_window_hours"
              type="number"
              defaultValue={policy.cancel_window_hours}
            />
          </label>
          <button type="submit">Save policy</button>
        </form>
      </section>

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1.5rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', opacity: 0.7 }}>
            <th style={{ padding: '0.4rem' }}>Booking</th>
            <th style={{ padding: '0.4rem' }}>When</th>
            <th style={{ padding: '0.4rem' }}>Mode</th>
            <th style={{ padding: '0.4rem' }}>Status</th>
            <th style={{ padding: '0.4rem' }}>Payment</th>
          </tr>
        </thead>
        <tbody>
          {bookings.map((b) => (
            <tr key={String(b.id)} style={{ borderTop: '1px solid rgba(0,0,0,0.1)' }}>
              <td style={{ padding: '0.55rem' }}>
                <Link href={`/b/${params.businessId}/bookings/${b.id}`}>
                  {String(b.booking_number)}
                </Link>
                <div style={{ opacity: 0.7, fontSize: '0.9rem' }}>{String(b.title)}</div>
              </td>
              <td style={{ padding: '0.55rem' }}>{String(b.starts_at)}</td>
              <td style={{ padding: '0.55rem' }}>{String(b.reservation_mode)}</td>
              <td style={{ padding: '0.55rem' }}>{String(b.status)}</td>
              <td style={{ padding: '0.55rem' }}>{String(b.payment_status)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {bookings.length === 0 ? <p style={{ marginTop: '1rem' }}>No bookings yet.</p> : null}
    </div>
  )
}
