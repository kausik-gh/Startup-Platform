'use server'

import { revalidatePath } from 'next/cache'
import { getAccessToken } from '@/lib/supabase/access-token'

export async function saveSectionContent(formData: FormData) {
  const token = await getAccessToken()
  if (!token) {
    return { ok: false as const, error: 'Not authenticated' }
  }
  const businessId = String(formData.get('businessId') || '')
  const sectionId = String(formData.get('sectionId') || '')
  const sectionTypeId = String(formData.get('sectionTypeId') || '')
  const headline = String(formData.get('headline') || '')
  const body = String(formData.get('body') || '')
  const rawInitial = String(formData.get('initialContent') || '{}')
  let content: Record<string, unknown> = {}
  try {
    content = JSON.parse(rawInitial) as Record<string, unknown>
  } catch {
    content = {}
  }
  if (sectionTypeId === 'hero' || sectionTypeId === 'cta_band' || 'headline' in content) {
    content.headline = headline
  }
  if ('subheadline' in content) content.subheadline = body
  if ('body' in content || sectionTypeId === 'about' || sectionTypeId === 'text_block') {
    content.body = body
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
  const res = await fetch(`${apiUrl}/v1/b/${businessId}/website/sections/${sectionId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) {
    return { ok: false as const, error: await res.text() }
  }
  revalidatePath(`/b/${businessId}/website/pages`)
  return { ok: true as const }
}
