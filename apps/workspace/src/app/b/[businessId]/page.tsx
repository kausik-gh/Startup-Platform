import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry, businessHeaders } from '@/lib/api'
import { PageHeader } from '@/components/ModuleState'

export const dynamic = 'force-dynamic'

type Context = {
  permissions: string[]
  entitled_modules: string[]
  module_states: Record<string, string>
  location_id: string | null
}

type Business = {
  display_name: string
  state: string
  status: string
  visibility: string
}

type Card = {
  key: string
  title: string
  detail: string
  href: string
  cta: string
  urgent?: boolean
}

const OPERATIONAL_MODULES = [
  'orders',
  'bookings',
  'leads',
  'inventory',
  'payments',
  'memberships',
  'customer-relationships',
  'offerings-catalog',
  'workforce',
  'fulfilment',
]

function isOperational(states: Record<string, string>, moduleId: string): boolean {
  const state = states[moduleId]
  return state === 'active' || state === 'ready'
}

/**
 * Doc 09 CORE-001 Workspace Home.
 *
 * Five states, chosen in priority order (Doc 09 §9.1):
 *   commercial recovery -> new -> active -> quiet, with partial/restricted
 *   layered on top of whichever applies.
 *
 * Every card is gated twice before it renders (Doc 11 §17.7 exit: "dashboard
 * cards link to operational actions and respect permission/Location"): the
 * module must be operational, and the viewer must hold the read permission.
 * A card the viewer cannot act on is not shown as an empty teaser.
 */
export default async function WorkspaceHomePage({
  params,
}: {
  params: { businessId: string }
}) {
  const token = await getAccessToken()
  if (!token) redirect('/login')

  const base = `/b/${params.businessId}`
  const bh = businessHeaders(params.businessId)
  const [contextRes, businessRes] = await Promise.all([
    // Business-scoped: without the headers this returns empty permissions /
    // module_states (personal context), which left every card gate false and
    // the page permanently stuck on the "new business" checklist.
    apiTry<{ data: Context }>('/v1/me/context', token, bh),
    apiTry<{ data: Business }>(`/v1/b/${params.businessId}`, token),
  ])

  const context = contextRes.ok ? contextRes.data.data : null
  const business = businessRes.ok ? businessRes.data.data : null
  const permissions = new Set(context?.permissions ?? [])
  const moduleStates = context?.module_states ?? {}
  const can = (permission: string) => permissions.has(permission)
  const active = (moduleId: string) => isOperational(moduleStates, moduleId)

  // ---------------------------------------------------------------
  // STATE 1 — Commercial recovery (Doc 03 §1.6 `status`, the standing axis)
  // ---------------------------------------------------------------
  if (business && business.status && business.status !== 'in_good_standing') {
    const suspended = business.status === 'suspended'
    return (
      <div>
        <PageHeader title={business.display_name} />
        <div
          style={{
            padding: '1.5rem',
            borderRadius: '10px',
            border: '1px solid rgba(163,51,51,0.35)',
            background: 'rgba(163,51,51,0.08)',
            maxWidth: '46rem',
          }}
        >
          <h2 style={{ marginTop: 0 }}>
            {suspended ? 'This business is suspended' : 'This business is under review'}
          </h2>
          <p style={{ lineHeight: 1.6 }}>
            {suspended
              ? 'New orders, bookings and payments are not being accepted right now. Your data is safe and nothing has been deleted.'
              : 'Your account is being reviewed. Everything keeps working normally while that happens.'}
          </p>
          <p style={{ lineHeight: 1.6 }}>
            Contact support to resolve this. They can tell you exactly what is needed.
          </p>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap' }}>
            <Link href={`${base}/settings`}>Business settings</Link>
            <Link href={`${base}/modules`}>Modules and plan</Link>
          </div>
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------
  // Gather what this viewer is actually allowed to see.
  // ---------------------------------------------------------------
  const cards: Card[] = []
  let pendingWork = 0

  const bp = `/v1/platform/businesses/${params.businessId}`
  const wants = {
    orders: active('orders') && can('orders.read'),
    bookings: active('bookings') && can('bookings.read'),
    leads: active('leads') && can('leads.read'),
    inventory: active('inventory') && can('inventory.read'),
  }

  // Everything this page needs beyond context+business, in one parallel round
  // instead of a six-deep await waterfall (each hop is a full round-trip to the
  // API and on to the hosted DB).
  const [ordersR, bookingsR, leadsR, inventoryR, notifR, websiteR] = await Promise.all([
    wants.orders
      ? apiTry<{ data: unknown[] }>(`${bp}/orders?status=pending`, token)
      : null,
    wants.bookings
      ? apiTry<{ data: unknown[] }>(`${bp}/bookings?status=pending`, token)
      : null,
    wants.leads
      ? apiTry<{ data: unknown[] }>(`${bp}/leads?status=new`, token)
      : null,
    wants.inventory
      ? apiTry<{ data: Array<{ stock_status: string }> }>(`${bp}/inventory`, token)
      : null,
    apiTry<{ data: { unread_count: number } }>(`${bp}/notifications/unread-count`, token),
    apiTry<{ data: { website: { status: string }; draft: { pages: unknown[] } } }>(
      `/v1/b/${params.businessId}/website`,
      token
    ),
  ])

  if (wants.orders) {
    const count = ordersR?.ok ? (ordersR.data.data || []).length : 0
    pendingWork += count
    cards.push({
      key: 'orders',
      title: 'Orders',
      detail: count > 0 ? `${count} waiting to be accepted` : 'Nothing waiting',
      href: `${base}/orders`,
      cta: count > 0 ? 'Review orders' : 'Open orders',
      urgent: count > 0,
    })
  }

  if (wants.bookings) {
    const count = bookingsR?.ok ? (bookingsR.data.data || []).length : 0
    pendingWork += count
    cards.push({
      key: 'bookings',
      title: 'Bookings',
      detail: count > 0 ? `${count} to confirm` : 'Nothing to confirm',
      href: `${base}/bookings`,
      cta: count > 0 ? 'Confirm bookings' : 'Open bookings',
      urgent: count > 0,
    })
  }

  if (wants.leads) {
    const count = leadsR?.ok ? (leadsR.data.data || []).length : 0
    pendingWork += count
    cards.push({
      key: 'leads',
      title: 'Leads',
      detail: count > 0 ? `${count} new enquiry${count === 1 ? '' : 's'}` : 'No new enquiries',
      href: `${base}/leads`,
      cta: count > 0 ? 'Follow up' : 'Open leads',
      urgent: count > 0,
    })
  }

  if (wants.inventory) {
    const low = inventoryR?.ok
      ? (inventoryR.data.data || []).filter((row) => row.stock_status !== 'in_stock').length
      : 0
    pendingWork += low
    cards.push({
      key: 'inventory',
      title: 'Stock',
      detail: low > 0 ? `${low} item${low === 1 ? '' : 's'} need restocking` : 'Stock levels fine',
      href: `${base}/inventory`,
      cta: low > 0 ? 'Restock' : 'Open inventory',
      urgent: low > 0,
    })
  }

  // Notifications are Platform Core: no module gate, membership is enough.
  const unread = notifR.ok ? notifR.data.data.unread_count : 0
  if (unread > 0) {
    cards.push({
      key: 'notifications',
      title: 'Notifications',
      detail: `${unread} unread`,
      href: `${base}/notifications`,
      cta: 'Read them',
      urgent: false,
    })
  }

  // Website / public presence health.
  const websiteStatus = websiteR.ok ? websiteR.data.data.website.status : null
  const websiteUnpublished = websiteStatus !== null && websiteStatus !== 'published'

  const activeModuleCount = OPERATIONAL_MODULES.filter(active).length

  // ---------------------------------------------------------------
  // STATE 2 — New: still being set up
  // ---------------------------------------------------------------
  const isNew =
    (business && (business.state === 'draft' || business.state === 'onboarding')) ||
    activeModuleCount === 0

  if (isNew) {
    const steps = [
      {
        label: 'Add what you sell or offer',
        href: `${base}/offerings`,
        done: active('offerings-catalog'),
      },
      { label: 'Turn on the modules you need', href: `${base}/modules`, done: activeModuleCount > 0 },
      { label: 'Complete your business profile', href: `${base}/profile`, done: false },
      { label: 'Publish your website', href: `${base}/website/publish`, done: !websiteUnpublished },
    ]
    return (
      <div>
        <PageHeader
          title={business?.display_name ?? 'Your business'}
          subtitle="Let's get you set up. Each step here unlocks something real."
        />
        <div style={{ display: 'grid', gap: '0.75rem', maxWidth: '40rem' }}>
          {steps.map((step) => (
            <div key={step.label} style={{ ...CARD, opacity: step.done ? 0.6 : 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                <span>
                  {step.done ? '✓ ' : ''}
                  {step.label}
                </span>
                <Link href={step.href}>{step.done ? 'Review' : 'Start'}</Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------
  // Partial / restricted — layered onto active or quiet below.
  // ---------------------------------------------------------------
  const entitledButOff = OPERATIONAL_MODULES.filter(
    (moduleId) =>
      !active(moduleId) &&
      (context?.entitled_modules ?? []).includes(moduleId)
  )
  const restrictedNotice =
    cards.length === 0 && activeModuleCount > 0 ? (
      <div style={{ ...CARD, maxWidth: '46rem' }}>
        <h2 style={{ marginTop: 0, fontSize: '1.15rem' }}>Not much to show you here</h2>
        <p style={{ lineHeight: 1.6, marginBottom: 0 }}>
          This business is running, but your role does not include access to the areas that would
          appear on this page. Someone with owner or manager access can change that from Team.
        </p>
        <Link href={`${base}/team`}>Open Team →</Link>
      </div>
    ) : null

  const locationNotice = context?.location_id ? (
    <p style={{ opacity: 0.75, marginBottom: '1.25rem' }}>
      Showing one location only. Numbers below exclude your other locations.
    </p>
  ) : null

  // ---------------------------------------------------------------
  // STATE 3 — Active (work waiting) / STATE 4 — Quiet (nothing waiting)
  // ---------------------------------------------------------------
  const quiet = pendingWork === 0 && cards.every((card) => !card.urgent)

  return (
    <div>
      <PageHeader
        title={business?.display_name ?? 'Workspace'}
        subtitle={
          quiet
            ? 'Nothing needs you right now.'
            : `${pendingWork} thing${pendingWork === 1 ? '' : 's'} need your attention.`
        }
      />

      {locationNotice}
      {restrictedNotice}

      {cards.length > 0 ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(16rem, 1fr))',
            gap: '0.9rem',
          }}
        >
          {[...cards]
            .sort((a, b) => Number(b.urgent ?? false) - Number(a.urgent ?? false))
            .map((card) => (
              <div
                key={card.key}
                style={{
                  ...CARD,
                  borderColor: card.urgent ? 'rgba(138,109,31,0.45)' : 'rgba(28,36,48,0.12)',
                }}
              >
                <h2 style={{ margin: '0 0 0.3rem', fontSize: '1.05rem' }}>{card.title}</h2>
                <p style={{ margin: '0 0 0.75rem', opacity: 0.85 }}>{card.detail}</p>
                <Link href={card.href}>{card.cta} →</Link>
              </div>
            ))}
        </div>
      ) : null}

      {quiet && cards.length > 0 ? (
        <p style={{ marginTop: '1.5rem', opacity: 0.8, maxWidth: '40rem', lineHeight: 1.6 }}>
          Everything is up to date. This is a good time to look at what is not urgent — your
          website, your offerings, or the modules you have not turned on yet.
        </p>
      ) : null}

      {websiteUnpublished && can('website.publish') ? (
        <div style={{ ...CARD, marginTop: '1.5rem', maxWidth: '40rem' }}>
          <h2 style={{ margin: '0 0 0.3rem', fontSize: '1.05rem' }}>Your website is not live</h2>
          <p style={{ margin: '0 0 0.75rem', opacity: 0.85 }}>
            Customers cannot find you until you publish it.
          </p>
          <Link href={`${base}/website/publish`}>Preview and publish →</Link>
        </div>
      ) : null}

      {entitledButOff.length > 0 && can('modules.enable') ? (
        <div style={{ ...CARD, marginTop: '1.5rem', maxWidth: '40rem' }}>
          <h2 style={{ margin: '0 0 0.3rem', fontSize: '1.05rem' }}>
            Included in your plan, not turned on
          </h2>
          <p style={{ margin: '0 0 0.75rem', opacity: 0.85 }}>
            {entitledButOff.slice(0, 4).join(', ')}
            {entitledButOff.length > 4 ? `, and ${entitledButOff.length - 4} more` : ''}.
          </p>
          <Link href={`${base}/modules`}>See what they do →</Link>
        </div>
      ) : null}
    </div>
  )
}

const CARD: React.CSSProperties = {
  padding: '1rem 1.15rem',
  borderRadius: '10px',
  border: '1px solid rgba(28,36,48,0.12)',
  background: 'rgba(255,255,255,0.6)',
}
