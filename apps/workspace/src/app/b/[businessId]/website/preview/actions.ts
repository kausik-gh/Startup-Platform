'use server'

import { revalidatePath } from 'next/cache'
import { getAccessToken } from '@/lib/supabase/access-token'

/**
 * Inline click-to-edit (Doc 09 §9.1.1) — additive UI over the EXISTING
 * section content-update endpoint. No new backend: this is exactly the same
 * `PATCH /v1/b/{id}/website/sections/{id}` the structured editor uses, so the
 * same schema validation and content-safety checks apply on the server.
 *
 * The whole (merged) content object is sent, because that endpoint validates
 * the complete section content against its SectionType schema.
 */
export async function saveSectionContent(
  businessId: string,
  sectionId: string,
  content: Record<string, unknown>
): Promise<{ ok: boolean; error?: string }> {
  const token = await getAccessToken()
  if (!token) return { ok: false, error: 'Your session expired — sign in again.' }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
  const res = await fetch(`${apiUrl}/v1/b/${businessId}/website/sections/${sectionId}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    cache: 'no-store',
  })
  if (!res.ok) {
    let message = `Save failed (${res.status})`
    try {
      const body = (await res.json()) as { error?: { message?: string } }
      if (body?.error?.message) message = body.error.message
    } catch {
      /* keep status message */
    }
    return { ok: false, error: message }
  }
  revalidatePath(`/b/${businessId}/website/preview`)
  return { ok: true }
}
