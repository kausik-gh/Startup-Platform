import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiGet } from '@/lib/api'
import { createZone, updateFulfilmentSettings } from '../actions'

export const dynamic = 'force-dynamic'

export default async function FulfilmentZonesPage({
  params,
}: {
  params: { businessId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')
  const [zonesRes, settingsRes] = await Promise.all([
    apiGet<{ data: Array<Record<string, unknown>> }>(
      `/v1/b/${params.businessId}/fulfilment/zones`,
      token
    ),
    apiGet<{ data: { pickup_enabled: boolean; delivery_enabled: boolean } }>(
      `/v1/b/${params.businessId}/fulfilment/settings`,
      token
    ),
  ])
  const zones = zonesRes.data || []
  const settings = settingsRes.data

  return (
    <div>
      <Link href={`/b/${params.businessId}/fulfilment`}>← Fulfilment</Link>
      <h1 style={{ fontSize: '1.75rem', marginTop: '0.75rem' }}>Zones & charges</h1>

      <form
        action={updateFulfilmentSettings}
        style={{ marginTop: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}
      >
        <input type="hidden" name="businessId" value={params.businessId} />
        <label>
          <input type="checkbox" name="pickup_enabled" defaultChecked={settings.pickup_enabled} />{' '}
          Pickup enabled
        </label>
        <label>
          <input
            type="checkbox"
            name="delivery_enabled"
            defaultChecked={settings.delivery_enabled}
          />{' '}
          Delivery enabled
        </label>
        <button type="submit">Save modes</button>
      </form>

      <ul style={{ marginTop: '1.5rem', lineHeight: 1.7 }}>
        {zones.map((z) => (
          <li key={String(z.id)}>
            <strong>{String(z.name)}</strong> · {String(z.match_type)} · {String(z.city || '')} ·{' '}
            {String(z.currency)} {String(z.charge_amount)}
          </li>
        ))}
      </ul>

      <form
        action={createZone}
        style={{ marginTop: '1.5rem', display: 'grid', gap: '0.5rem', maxWidth: '22rem' }}
      >
        <h2>Add city zone</h2>
        <input type="hidden" name="businessId" value={params.businessId} />
        <input name="name" placeholder="Zone name" required />
        <input name="city" placeholder="City" required />
        <input name="charge_amount" type="number" step="0.01" min="0" defaultValue="0" />
        <button type="submit">Create zone</button>
      </form>
    </div>
  )
}
