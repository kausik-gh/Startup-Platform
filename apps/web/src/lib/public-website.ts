const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export type PublicWebsitePayload = {
  business: { id: string; slug: string; display_name: string; business_type?: string | null }
  website: { status: string }
  page: {
    title: string
    slug: string
    seo_title?: string | null
    seo_description?: string | null
    sections: {
      id: string
      section_type_id: string
      layout_variant?: string | null
      content: Record<string, unknown>
      is_visible: boolean
    }[]
  }
  navigation: { label: string; path: string }[]
  theme: Record<string, unknown>
  is_preview: boolean
}

export async function fetchPublicWebsite(
  slug: string,
  pageSlug?: string,
  previewToken?: string
): Promise<PublicWebsitePayload | null> {
  const path = pageSlug
    ? `/v1/public/websites/${slug}/pages/${pageSlug}`
    : `/v1/public/websites/${slug}`
  const qs = previewToken ? `?preview_token=${encodeURIComponent(previewToken)}` : ''
  const res = await fetch(`${apiUrl}${path}${qs}`, {
    cache: previewToken ? 'no-store' : 'force-cache',
    next: previewToken ? undefined : { revalidate: 60, tags: [`website:${slug}`] },
  })
  if (!res.ok) return null
  const json = (await res.json()) as { data: PublicWebsitePayload }
  return json.data
}
