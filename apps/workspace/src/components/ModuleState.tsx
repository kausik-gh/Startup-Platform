import Link from 'next/link'
import { ReactNode } from 'react'
import type { ApiError } from '@/lib/api'

const CARD: React.CSSProperties = {
  background: 'rgba(255,255,255,0.6)',
  border: '1px solid rgba(28,36,48,0.12)',
  borderRadius: '10px',
  padding: '1.5rem',
  maxWidth: '46rem',
}

/**
 * Truthful rendering of a gate failure (Doc 12 §8.9 gates [6]/[7]/[8]).
 * Each gate has a distinct error code and a distinct recovery, so they are
 * shown as distinct states rather than one generic "something went wrong".
 */
export function GateNotice({
  error,
  businessId,
  moduleLabel,
}: {
  error: ApiError
  businessId: string
  moduleLabel: string
}) {
  const base = `/b/${businessId}`
  if (error.code === 'MODULE_NOT_ACTIVE') {
    return (
      <div style={CARD}>
        <h2 style={{ marginTop: 0 }}>{moduleLabel} is not active yet</h2>
        <p style={{ opacity: 0.85 }}>
          This Business is entitled to {moduleLabel}, but the module has not been enabled.
          Enabling it makes these pages operational — nothing is lost in the meantime.
        </p>
        <Link href={`${base}/modules`}>Open Module Catalog →</Link>
      </div>
    )
  }
  if (error.code === 'ENTITLEMENT_REQUIRED') {
    return (
      <div style={CARD}>
        <h2 style={{ marginTop: 0 }}>{moduleLabel} is not included in this plan</h2>
        <p style={{ opacity: 0.85 }}>
          {moduleLabel} needs a commercial Entitlement before it can be enabled.
        </p>
        <Link href={`${base}/modules`}>Review modules and plans →</Link>
      </div>
    )
  }
  if (error.code === 'PERMISSION_DENIED') {
    return (
      <div style={CARD}>
        <h2 style={{ marginTop: 0 }}>You do not have access to {moduleLabel}</h2>
        <p style={{ opacity: 0.85 }}>
          {moduleLabel} is active for this Business, but your role does not include
          permission to view it. An owner or manager can grant access from Team.
        </p>
        <Link href={`${base}/team`}>Open Team →</Link>
      </div>
    )
  }
  return (
    <div style={CARD}>
      <h2 style={{ marginTop: 0 }}>{moduleLabel} could not be loaded</h2>
      <p style={{ opacity: 0.85 }}>{error.message}</p>
      <p style={{ opacity: 0.6, fontSize: '0.85rem' }}>Reference: {error.code}</p>
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        gap: '1rem',
        flexWrap: 'wrap',
        marginBottom: '1.25rem',
      }}
    >
      <div>
        <h1 style={{ fontSize: '2rem', margin: 0 }}>{title}</h1>
        {subtitle ? <p style={{ opacity: 0.8, margin: '0.35rem 0 0' }}>{subtitle}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <p
      style={{
        marginTop: '1rem',
        padding: '1.25rem',
        background: 'rgba(255,255,255,0.5)',
        border: '1px dashed rgba(28,36,48,0.2)',
        borderRadius: '8px',
        opacity: 0.85,
      }}
    >
      {children}
    </p>
  )
}

export const TABLE: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' }
export const TH: React.CSSProperties = { padding: '0.4rem', textAlign: 'left', opacity: 0.7 }
export const TD: React.CSSProperties = { padding: '0.55rem' }
export const ROW: React.CSSProperties = { borderTop: '1px solid rgba(0,0,0,0.1)' }

export function StatusPill({ value }: { value: string }) {
  const tone: Record<string, string> = {
    active: '#1f7a4d',
    succeeded: '#1f7a4d',
    completed: '#1f7a4d',
    won: '#1f7a4d',
    pending: '#8a6d1f',
    draft: '#5a6270',
    paused: '#8a6d1f',
    failed: '#a33',
    cancelled: '#a33',
    lost: '#a33',
    archived: '#5a6270',
    expired: '#a33',
  }
  const color = tone[value] ?? '#1c2430'
  return (
    <span
      style={{
        color,
        border: `1px solid ${color}33`,
        background: `${color}14`,
        borderRadius: '999px',
        padding: '0.1rem 0.55rem',
        fontSize: '0.85rem',
        whiteSpace: 'nowrap',
      }}
    >
      {value}
    </span>
  )
}
