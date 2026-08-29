const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export async function apiGet<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function apiSend<T>(
  path: string,
  token: string,
  method: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${path} failed: ${res.status} ${text}`)
  }
  return res.json() as Promise<T>
}

export async function apiPost<T>(path: string, body: unknown, token: string): Promise<T> {
  return apiSend<T>(path, token, 'POST', body)
}

export async function apiPatch<T>(path: string, body: unknown, token: string): Promise<T> {
  return apiSend<T>(path, token, 'PATCH', body)
}

export type ApiError = {
  status: number
  code: string
  message: string
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError }

/**
 * Fetch that surfaces the gate failure instead of throwing (Doc 11 §17.7:
 * "every in-scope operational exception has a truthful recoverable state").
 *
 * Module Workspace pages are reachable for a Business that has not enabled or
 * is not entitled to the module. `apiGet` would throw and blank the page;
 * this lets the page render the real reason.
 */
export async function apiTry<T>(path: string, token: string): Promise<ApiResult<T>> {
  const res = await fetch(`${apiUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })
  if (res.ok) {
    return { ok: true, data: (await res.json()) as T }
  }
  let code = 'UNKNOWN'
  let message = `Request failed with status ${res.status}`
  try {
    const body = await res.json()
    code = body?.error?.code ?? code
    message = body?.error?.message ?? message
  } catch {
    // Non-JSON error body — keep the status-derived defaults.
  }
  return { ok: false, error: { status: res.status, code, message } }
}
