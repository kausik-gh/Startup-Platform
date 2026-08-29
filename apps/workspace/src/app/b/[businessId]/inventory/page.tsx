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
import { adjustStock, setOpeningStock } from './actions'

export const dynamic = 'force-dynamic'

type InventoryRow = {
  id: string
  offering_id: string
  location_id: string
  product_title: string
  product_sku: string | null
  quantity_on_hand: number
  quantity_reserved: number
  quantity_available: number
  low_stock_threshold: number | null
  stock_status: string
}

type LocationRow = { id: string; name: string; is_primary: boolean }

const STOCK_FILTERS = ['in_stock', 'low_stock', 'out_of_stock']

/** Doc 11 §7 Inventory — stock levels per Offering per Location. */
export default async function InventoryPage({
  params,
  searchParams,
}: {
  params: { businessId: string }
  searchParams?: { stock_status?: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  const qs = searchParams?.stock_status
    ? `?stock_status=${encodeURIComponent(searchParams.stock_status)}`
    : ''
  const res = await apiTry<{ data: InventoryRow[] }>(
    `/v1/platform/businesses/${params.businessId}/inventory${qs}`,
    token
  )
  if (!res.ok) {
    return (
      <div>
        <PageHeader title="Inventory" />
        <GateNotice error={res.error} businessId={params.businessId} moduleLabel="Inventory" />
      </div>
    )
  }
  const records = res.data.data || []

  const locRes = await apiTry<{ data: LocationRow[] }>(
    `/v1/platform/businesses/${params.businessId}/locations`,
    token
  )
  const locations = locRes.ok ? locRes.data.data || [] : []
  const lowCount = records.filter((r) => r.stock_status !== 'in_stock').length
  const base = `/b/${params.businessId}/inventory`

  return (
    <div>
      <PageHeader
        title="Inventory"
        subtitle="Stock on hand, reserved, and available for each tracked offering."
      />

      {lowCount > 0 ? (
        <p
          style={{
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            background: 'rgba(163,51,51,0.08)',
            border: '1px solid rgba(163,51,51,0.25)',
            marginBottom: '1.25rem',
          }}
        >
          {lowCount} {lowCount === 1 ? 'item needs' : 'items need'} restocking.
        </p>
      ) : null}

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <Link href={base}>All</Link>
        {STOCK_FILTERS.map((status) => (
          <Link key={status} href={`${base}?stock_status=${status}`}>
            {status.replace(/_/g, ' ')}
          </Link>
        ))}
      </div>

      <table style={TABLE}>
        <thead>
          <tr>
            <th style={TH}>Offering</th>
            <th style={TH}>SKU</th>
            <th style={TH}>On hand</th>
            <th style={TH}>Reserved</th>
            <th style={TH}>Available</th>
            <th style={TH}>Status</th>
          </tr>
        </thead>
        <tbody>
          {records.map((row) => (
            <tr key={row.id} style={ROW}>
              <td style={TD}>{row.product_title}</td>
              <td style={TD}>{row.product_sku || '—'}</td>
              <td style={{ ...TD, fontVariantNumeric: 'tabular-nums' }}>{row.quantity_on_hand}</td>
              <td style={{ ...TD, fontVariantNumeric: 'tabular-nums' }}>{row.quantity_reserved}</td>
              <td style={{ ...TD, fontVariantNumeric: 'tabular-nums' }}>
                {row.quantity_available}
              </td>
              <td style={TD}>
                <StatusPill value={row.stock_status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {records.length === 0 ? (
        <EmptyState>
          No tracked stock yet. Inventory appears here once an offering has stock tracking turned
          on and an opening count set.
        </EmptyState>
      ) : null}

      <div style={{ display: 'flex', gap: '2.5rem', flexWrap: 'wrap', marginTop: '2rem' }}>
        <section style={{ minWidth: '20rem' }}>
          <h2 style={{ fontSize: '1.15rem' }}>Set opening stock</h2>
          <form action={setOpeningStock} style={{ display: 'grid', gap: '0.6rem' }}>
            <input type="hidden" name="businessId" value={params.businessId} />
            <input name="offering_id" placeholder="Offering ID" required style={INPUT} />
            <select name="location_id" required style={INPUT}>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                  {loc.is_primary ? ' (primary)' : ''}
                </option>
              ))}
            </select>
            <input name="quantity" type="number" min="0" placeholder="Quantity" required style={INPUT} />
            <button type="submit" style={BUTTON}>
              Set opening stock
            </button>
          </form>
        </section>

        <section style={{ minWidth: '20rem' }}>
          <h2 style={{ fontSize: '1.15rem' }}>Adjust stock</h2>
          <form action={adjustStock} style={{ display: 'grid', gap: '0.6rem' }}>
            <input type="hidden" name="businessId" value={params.businessId} />
            <input name="offering_id" placeholder="Offering ID" required style={INPUT} />
            <select name="location_id" required style={INPUT}>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                  {loc.is_primary ? ' (primary)' : ''}
                </option>
              ))}
            </select>
            <input
              name="quantity_delta"
              type="number"
              placeholder="Change (+ or −)"
              required
              style={INPUT}
            />
            <input name="reason" placeholder="Reason" required style={INPUT} />
            <button type="submit" style={BUTTON}>
              Adjust
            </button>
          </form>
        </section>
      </div>
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
