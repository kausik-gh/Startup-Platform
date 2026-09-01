'use client'

/**
 * Workspace visual preview with inline click-to-edit (Doc 09 §9.1.1).
 *
 * Renders the draft sections roughly as the public site will, and lets an
 * editor double-click any text to change it in place. Each commit is one call
 * to the existing section content-update endpoint (see ./actions.ts) — no new
 * backend, same validation.
 *
 * Image replace is intentionally NOT wired here: the platform has no media
 * upload endpoint yet (Doc 12 §15 is unbuilt). Image slots show a disabled
 * affordance rather than a broken one. This gap is flagged, not worked around.
 */

import React, { useState } from 'react'
import { saveSectionContent } from './actions'

type Section = {
  id: string
  section_type_id: string
  layout_variant?: string | null
  content: Record<string, unknown>
  is_visible: boolean
}
type Theme = Record<string, unknown>

const FIELDS: Record<string, { key: string; label: string; multiline?: boolean }[]> = {
  hero: [
    { key: 'headline', label: 'Headline' },
    { key: 'subheadline', label: 'Subheadline', multiline: true },
    { key: 'cta_label', label: 'Button label' },
  ],
  about: [
    { key: 'title', label: 'Title' },
    { key: 'body', label: 'Body', multiline: true },
  ],
  text_block: [
    { key: 'title', label: 'Title' },
    { key: 'body', label: 'Body', multiline: true },
  ],
  contact: [
    { key: 'title', label: 'Title' },
    { key: 'address', label: 'Address', multiline: true },
    { key: 'phone', label: 'Phone' },
    { key: 'email', label: 'Email' },
    { key: 'hours_summary', label: 'Hours', multiline: true },
  ],
  cta_band: [
    { key: 'headline', label: 'Headline' },
    { key: 'body', label: 'Body', multiline: true },
    { key: 'cta_label', label: 'Button label' },
  ],
  offerings_list: [
    { key: 'title', label: 'Title' },
    { key: 'subtitle', label: 'Subtitle', multiline: true },
  ],
  menu_section: [
    { key: 'title', label: 'Title' },
    { key: 'subtitle', label: 'Subtitle', multiline: true },
  ],
}
const GENERIC = [
  { key: 'title', label: 'Title' },
  { key: 'subtitle', label: 'Subtitle', multiline: true },
  { key: 'body', label: 'Body', multiline: true },
]

const IMAGE_KEYS = ['image_asset_id', 'og_image_asset_id']

function Editable({
  value,
  multiline,
  onCommit,
  placeholder,
  style,
}: {
  value: string
  multiline?: boolean
  onCommit: (next: string) => void
  placeholder: string
  style?: React.CSSProperties
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)

  if (editing) {
    const shared: React.CSSProperties = {
      font: 'inherit',
      color: 'inherit',
      width: '100%',
      background: 'rgba(255,255,255,0.9)',
      border: '2px solid #1c5f57',
      borderRadius: 4,
      padding: '0.2rem 0.35rem',
      ...style,
    }
    const commit = () => {
      setEditing(false)
      if (draft !== value) onCommit(draft)
    }
    return multiline ? (
      <textarea
        autoFocus
        rows={3}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        style={shared}
      />
    ) : (
      <input
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
          if (e.key === 'Escape') {
            setDraft(value)
            setEditing(false)
          }
        }}
        style={shared}
      />
    )
  }

  return (
    <span
      title="Double-click to edit"
      onDoubleClick={() => {
        setDraft(value)
        setEditing(true)
      }}
      style={{
        cursor: 'text',
        borderRadius: 3,
        outline: value ? 'none' : '1px dashed rgba(0,0,0,0.25)',
        outlineOffset: 2,
        color: value ? 'inherit' : 'rgba(0,0,0,0.4)',
        ...style,
      }}
    >
      {value || placeholder}
    </span>
  )
}

function ImageSlot() {
  return (
    <div
      style={{
        marginTop: '0.75rem',
        padding: '0.9rem',
        border: '1px dashed rgba(0,0,0,0.3)',
        borderRadius: 6,
        fontSize: '0.8rem',
        color: 'rgba(0,0,0,0.55)',
        fontFamily: 'system-ui, sans-serif',
        maxWidth: '22rem',
      }}
    >
      Image slot — replacing images from the preview isn&apos;t available yet
      (media upload is not built). Add images from Brand &amp; Media once that lands.
    </div>
  )
}

export function PreviewCanvas({
  businessId,
  pages,
  theme,
}: {
  businessId: string
  pages: { id: string; title: string; slug: string; sections: Section[] }[]
  theme: Theme
}) {
  const primary = String(theme.primary_color || '#0F766E')
  const accent = String(theme.accent_color || '#F59E0B')
  const [sections, setSections] = useState<Record<string, Record<string, unknown>>>(() =>
    Object.fromEntries(pages.flatMap((p) => p.sections.map((s) => [s.id, s.content || {}])))
  )
  const [status, setStatus] = useState<{ id: string; msg: string; error: boolean } | null>(null)

  const commit = async (section: Section, key: string, next: string) => {
    const merged = { ...(sections[section.id] || {}), [key]: next }
    setSections((prev) => ({ ...prev, [section.id]: merged }))
    setStatus({ id: section.id, msg: 'Saving…', error: false })
    const res = await saveSectionContent(businessId, section.id, merged)
    setStatus(
      res.ok
        ? { id: section.id, msg: 'Saved', error: false }
        : { id: section.id, msg: res.error || 'Save failed', error: true }
    )
    if (res.ok) setTimeout(() => setStatus((s) => (s?.id === section.id ? null : s)), 1500)
  }

  return (
    <div style={{ display: 'grid', gap: '2rem' }}>
      {pages.map((page) => (
        <div key={page.id}>
          <div
            style={{
              fontFamily: 'system-ui, sans-serif',
              fontSize: '0.78rem',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: '#67727f',
              marginBottom: '0.5rem',
            }}
          >
            {page.title} — /{page.slug}
          </div>
          <div style={{ border: '1px solid rgba(28,36,48,0.14)', borderRadius: 10, overflow: 'hidden', background: '#faf8f4' }}>
            {page.sections.map((section) => {
              const c = sections[section.id] || {}
              const fields = FIELDS[section.section_type_id] || GENERIC
              const hasImage = IMAGE_KEYS.some((k) => k in (section.content || {}))
              const isHero = section.section_type_id === 'hero'
              const isBand = section.section_type_id === 'cta_band'
              return (
                <section
                  key={section.id}
                  style={{
                    position: 'relative',
                    padding: '2rem 1.5rem',
                    background: isHero ? primary : isBand ? accent : 'transparent',
                    color: isHero ? '#fff' : '#1a1f24',
                    borderBottom: '1px solid rgba(0,0,0,0.06)',
                    fontFamily: 'Georgia, serif',
                    opacity: section.is_visible ? 1 : 0.5,
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      top: 6,
                      right: 8,
                      fontFamily: 'system-ui, sans-serif',
                      fontSize: '0.68rem',
                      color: isHero ? 'rgba(255,255,255,0.7)' : '#8a94a0',
                    }}
                  >
                    {section.section_type_id}
                    {status?.id === section.id ? (
                      <span style={{ marginLeft: 8, color: status.error ? '#c0392b' : 'inherit' }}>
                        · {status.msg}
                      </span>
                    ) : null}
                  </div>
                  <div style={{ display: 'grid', gap: '0.6rem', maxWidth: '44rem' }}>
                    {fields.map((f) => (
                      <div
                        key={f.key}
                        style={{
                          fontSize:
                            f.key === 'headline' ? (isHero ? '2rem' : '1.4rem') : f.key === 'body' ? '1rem' : '1.05rem',
                          fontWeight: f.key === 'headline' || f.key === 'title' ? 700 : 400,
                          lineHeight: 1.5,
                        }}
                      >
                        <Editable
                          value={String(c[f.key] ?? '')}
                          multiline={f.multiline}
                          placeholder={`${f.label}…`}
                          onCommit={(next) => commit(section, f.key, next)}
                        />
                      </div>
                    ))}
                    {hasImage ? <ImageSlot /> : null}
                  </div>
                </section>
              )
            })}
            {page.sections.length === 0 ? (
              <div style={{ padding: '1.5rem', fontFamily: 'system-ui, sans-serif', color: '#8a94a0' }}>
                No sections on this page yet.
              </div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  )
}
