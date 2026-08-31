import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiTry } from '@/lib/platform-api'
import { OnboardingShell, Steps } from '@/components/onboarding/Shell'
import { HandOff } from './HandOff'

export const dynamic = 'force-dynamic'

const WORKSPACE_URL = process.env.NEXT_PUBLIC_WORKSPACE_URL || 'http://localhost:3001'

type Business = { id: string; slug: string; display_name: string }
type CatalogModule = { module_id: string; display_name: string; module_class: string }
type ModuleState = { module_id: string; activation_state: string }

const OPERATIONAL = new Set(['active', 'ready'])

/** Onboarding step 5 — arrival. States what is genuinely on, then hands off. */
export default async function DonePage({ params }: { params: { businessId: string } }) {
  const token = await getAccessToken()
  if (!token) redirect(`/login?destination=/start/${params.businessId}/done`)

  const [bizRes, statesRes, catalogRes] = await Promise.all([
    apiTry<{ data: Business[] }>('/v1/platform/businesses', token),
    apiTry<{ data: ModuleState[] }>(`/v1/b/${params.businessId}/modules`, token),
    apiTry<{ data: CatalogModule[] }>('/v1/platform/modules', token),
  ])

  const business = bizRes.ok
    ? (bizRes.data.data || []).find((b) => b.id === params.businessId)
    : undefined
  const names = new Map(
    (catalogRes.ok ? catalogRes.data.data || [] : []).map((m) => [
      m.module_id,
      { label: m.display_name, cls: m.module_class },
    ])
  )
  const live = (statesRes.ok ? statesRes.data.data || [] : [])
    .filter((s) => OPERATIONAL.has(s.activation_state))
    .map((s) => ({ id: s.module_id, ...(names.get(s.module_id) || { label: s.module_id, cls: '' }) }))
    .filter((m) => m.cls !== 'platform_core')
    .sort((a, b) => a.label.localeCompare(b.label))

  return (
    <OnboardingShell>
      <Steps current={4} />
      <h1 style={{ fontSize: '2rem', margin: '0 0 0.6rem' }}>
        {business?.display_name || 'Your business'} is live
      </h1>
      <p style={{ color: '#3c4855', lineHeight: 1.65, margin: '0 0 1.75rem', maxWidth: '36rem' }}>
        Your website is built and these tools are switched on. Everything below now has a real
        page in your Workspace.
      </p>

      {live.length > 0 ? (
        <ul
          style={{
            display: 'flex',
            gap: '0.5rem',
            flexWrap: 'wrap',
            listStyle: 'none',
            padding: 0,
            margin: '0 0 2rem',
          }}
        >
          {live.map((m) => (
            <li
              key={m.id}
              style={{
                padding: '0.4rem 0.85rem',
                borderRadius: '999px',
                border: '1px solid rgba(28,95,87,0.35)',
                background: 'rgba(28,95,87,0.1)',
                color: '#17544d',
                fontFamily: 'system-ui, sans-serif',
                fontSize: '0.86rem',
                fontWeight: 600,
              }}
            >
              {m.label}
            </li>
          ))}
        </ul>
      ) : null}

      <HandOff href={`${WORKSPACE_URL}/b/${params.businessId}`} />

      <p
        style={{
          marginTop: '2.25rem',
          fontFamily: 'system-ui, sans-serif',
          fontSize: '0.87rem',
          color: '#4c5967',
          lineHeight: 1.6,
        }}
      >
        Your site isn&apos;t public yet — publish it from the Workspace when you&apos;re happy
        with it.{' '}
        {business ? (
          <>
            It will live at <code>/{business.slug}</code>.
          </>
        ) : null}{' '}
        <Link href="/">Back to home</Link>
      </p>
    </OnboardingShell>
  )
}
