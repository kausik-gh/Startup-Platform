'use client'

import { useFormState, useFormStatus } from 'react-dom'
import { createBusinessAction, type CreateBusinessState } from './actions'

export type BusinessType = { type_id: string; display_name: string; category: string }

const INITIAL: CreateBusinessState = { error: null }

function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      style={{
        padding: '0.75rem 1.5rem',
        borderRadius: '8px',
        border: 'none',
        background: pending ? '#7d9c96' : '#1c5f57',
        color: '#fff',
        fontWeight: 600,
        fontSize: '0.98rem',
        cursor: pending ? 'progress' : 'pointer',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      {pending ? 'Creating your business…' : 'Create business & build my website'}
    </button>
  )
}

export function StartForm({ types }: { types: BusinessType[] }) {
  const [state, formAction] = useFormState(createBusinessAction, INITIAL)

  return (
    <form action={formAction} style={{ display: 'grid', gap: '1.6rem', maxWidth: '34rem' }}>
      {state.error ? (
        <p
          role="alert"
          style={{
            margin: 0,
            padding: '0.8rem 1rem',
            borderRadius: '8px',
            border: '1px solid #c9776f',
            background: '#f8e9e7',
            color: '#8d2f24',
            fontFamily: 'system-ui, sans-serif',
            fontSize: '0.92rem',
          }}
        >
          {state.error}
        </p>
      ) : null}

      <label style={{ display: 'grid', gap: '0.4rem' }}>
        <span style={{ fontWeight: 600 }}>What is your business called?</span>
        <input
          name="display_name"
          required
          maxLength={200}
          autoFocus
          placeholder="e.g. Corner Coffee House"
          style={{
            padding: '0.65rem 0.8rem',
            borderRadius: '8px',
            border: '1px solid rgba(28,36,48,0.28)',
            fontSize: '1rem',
            fontFamily: 'system-ui, sans-serif',
          }}
        />
        <span
          style={{ fontSize: '0.83rem', color: '#4c5967', fontFamily: 'system-ui, sans-serif' }}
        >
          This is the name customers will see on your website and marketplace listing.
        </span>
      </label>

      <label style={{ display: 'grid', gap: '0.4rem' }}>
        <span style={{ fontWeight: 600 }}>Describe it in one line</span>
        <input
          name="tagline"
          maxLength={200}
          placeholder="e.g. Small-batch roastery and neighbourhood café"
          style={{
            padding: '0.65rem 0.8rem',
            borderRadius: '8px',
            border: '1px solid rgba(28,36,48,0.28)',
            fontSize: '1rem',
            fontFamily: 'system-ui, sans-serif',
          }}
        />
        <span
          style={{ fontSize: '0.83rem', color: '#4c5967', fontFamily: 'system-ui, sans-serif' }}
        >
          Shown on your website and marketplace listing. You need this before customers can
          find you in the marketplace.
        </span>
      </label>

      <label style={{ display: 'grid', gap: '0.4rem' }}>
        <span style={{ fontWeight: 600 }}>What kind of business is it?</span>
        <select
          name="business_type"
          required
          defaultValue=""
          style={{
            padding: '0.65rem 0.8rem',
            borderRadius: '8px',
            border: '1px solid rgba(28,36,48,0.28)',
            fontSize: '1rem',
            fontFamily: 'system-ui, sans-serif',
            background: '#fff',
          }}
        >
          <option value="" disabled>
            Choose one…
          </option>
          {types.map((t) => (
            <option key={t.type_id} value={t.type_id}>
              {t.display_name}
            </option>
          ))}
        </select>
        <span
          style={{ fontSize: '0.83rem', color: '#4c5967', fontFamily: 'system-ui, sans-serif' }}
        >
          This decides which tools we recommend next. You can change it later.
        </span>
      </label>

      <SubmitButton />
    </form>
  )
}
