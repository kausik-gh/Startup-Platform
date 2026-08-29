'use server'

import { revalidatePath } from 'next/cache'
import { getAccessToken } from '@/lib/supabase/access-token'

const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

async function send(path: string, method: string, body?: unknown) {
  const token = await getAccessToken()
  if (!token) throw new Error('Unauthorized')
  const res = await fetch(`${apiUrl}${path}`, {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status} ${await res.text()}`)
  return res.json()
}

export async function recordSettlement(formData: FormData) {
  const businessId = String(formData.get('businessId'))
  const paymentId = String(formData.get('paymentId'))
  await send(
    `/v1/platform/businesses/${businessId}/payments/${paymentId}/record-settlement`,
    'POST',
    {}
  )
  revalidatePath(`/b/${businessId}/payments`)
  revalidatePath(`/b/${businessId}/payments/${paymentId}`)
}

export async function refundPayment(formData: FormData) {
  const businessId = String(formData.get('businessId'))
  const paymentId = String(formData.get('paymentId'))
  await send(`/v1/platform/businesses/${businessId}/payments/${paymentId}/refunds`, 'POST', {
    amount: Number(formData.get('amount')),
    reason: String(formData.get('reason')),
  })
  revalidatePath(`/b/${businessId}/payments`)
  revalidatePath(`/b/${businessId}/payments/${paymentId}`)
}
