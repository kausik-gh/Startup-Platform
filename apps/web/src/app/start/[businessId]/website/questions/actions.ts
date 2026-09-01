'use server'

import { redirect } from 'next/navigation'
import { getAccessToken } from '@/lib/supabase/access-token'
import { apiPost } from '@/lib/platform-api'

/**
 * Onboarding step 2a — submit the website questionnaire.
 *
 * The answered fields become ONE `POST /v1/b/{id}/website/generate` with an
 * `intake` body (Doc 12 §12.7). Skipped fields are absent; the backend fills
 * them deterministically. A failure here is non-fatal: business creation
 * already produced a draft, so we still move the owner forward to see it.
 */
export async function submitQuestionnaireAction(
  businessId: string,
  intakeJson: string
): Promise<void> {
  const token = await getAccessToken()
  if (!token) redirect(`/login?destination=/start/${businessId}/website/questions`)

  let intake: unknown = {}
  try {
    intake = JSON.parse(intakeJson || '{}')
  } catch {
    intake = {}
  }

  await apiPost(`/v1/b/${businessId}/website/generate`, token, { intake })
  redirect(`/start/${businessId}/website`)
}
