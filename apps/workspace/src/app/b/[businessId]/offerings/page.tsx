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
import { archiveOffering, createOffering, restoreOffering } from './actions'

export const dynamic = 'force-dynamic'

type Offering = {
  id: string
  title: string
  offering_type: string
  status: string
  price_amount: number | null
  currency: string
  track_inventory: boolean
}

type Category = { id: string; name: string; status: string }

/** Doc 11 §7 Offerings Catalog — what the Business sells. */
export default async function OfferingsPage({ params }: { params: { businessId: string } }) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  const res = await apiTry<{ data: Offering[] }>(
    `/v1/platform/businesses/${params.businessId}/products`,
    token
  )
  if (!res.ok) {
    return (
      <div>
        <PageHeader title="Offerings" />
        <GateNotice
          error={res.error}
          businessId={params.businessId}
          moduleLabel="the Offerings Catalog"
        />
      </div>
    )
  }
  const offerings = res.data.data || []

  const catRes = await apiTry<{ data: Category[] }>(
    `/v1/platform/businesses/${params.businessId}/product-categories`,
    token
  )
  const categories = catRes.ok ? catRes.data.data || [] : []

  return (
    <div>
      <PageHeader
        title="Offerings"
        subtitle="Everything this Business sells or provides — products, services, and classes."
      />

      <table style={TABLE}>
        <thead>
          <tr>
            <th style={TH}>Title</th>
            <th style={TH}>Type</th>
            <th style={TH}>Status</th>
            <th style={TH}>Price</th>
            <th style={TH}>Stock tracked</th>
            <th style={TH} />
          </tr>
        </thead>
        <tbody>
          {offerings.map((item) => (
            <tr key={item.id} style={ROW}>
              <td style={TD}>{item.title}</td>
              <td style={TD}>{item.offering_type}</td>
              <td style={TD}>
                <StatusPill value={item.status} />
              </td>
              <td style={{ ...TD, fontVariantNumeric: 'tabular-nums' }}>
                {item.price_amount === null ? '—' : `${item.currency} ${item.price_amount}`}
              </td>
              <td style={TD}>{item.track_inventory ? 'Yes' : 'No'}</td>
              <td style={TD}>
                <form action={item.status === 'archived' ? restoreOffering : archiveOffering}>
                  <input type="hidden" name="businessId" value={params.businessId} />
                  <input type="hidden" name="offeringId" value={item.id} />
                  <button type="submit" style={LINK_BUTTON}>
                    {item.status === 'archived' ? 'Restore' : 'Archive'}
                  </button>
                </form>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {offerings.length === 0 ? (
        <EmptyState>
          Nothing in the catalog yet. Add your first offering below — it stays a draft until you
          mark it active, so nothing goes public before you are ready.
        </EmptyState>
      ) : null}

      {categories.length > 0 ? (
        <section style={{ marginTop: '2rem' }}>
          <h2 style={{ fontSize: '1.15rem' }}>Categories</h2>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {categories.map((category) => (
              <span
                key={category.id}
                style={{
                  padding: '0.3rem 0.7rem',
                  borderRadius: '999px',
                  border: '1px solid rgba(28,36,48,0.18)',
                  background: 'rgba(255,255,255,0.6)',
                }}
              >
                {category.name}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <section style={{ marginTop: '2rem', maxWidth: '32rem' }}>
        <h2 style={{ fontSize: '1.15rem' }}>Add an offering</h2>
        <form action={createOffering} style={{ display: 'grid', gap: '0.6rem' }}>
          <input type="hidden" name="businessId" value={params.businessId} />
          <input name="title" placeholder="Title" required style={INPUT} />
          <textarea name="description" placeholder="Description" style={INPUT} />
          <select name="offering_type" style={INPUT} defaultValue="product">
            <option value="product">Product</option>
            <option value="service">Service</option>
            <option value="class_session">Class or session</option>
          </select>
          <input name="price_amount" type="number" step="0.01" placeholder="Price" style={INPUT} />
          <select name="status" style={INPUT} defaultValue="draft">
            <option value="draft">Save as draft</option>
            <option value="active">Publish as active</option>
          </select>
          <button type="submit" style={BUTTON}>
            Add offering
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
const LINK_BUTTON: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#1c2430',
  textDecoration: 'underline',
  cursor: 'pointer',
  font: 'inherit',
  padding: 0,
}
