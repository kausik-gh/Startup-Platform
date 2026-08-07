import { notFound } from 'next/navigation'
import { RESERVED_SLUGS } from '@/lib/reserved-slugs'
import { fetchPublicWebsite } from '@/lib/public-website'
import { WebsitePageView } from '@/components/website/WebsitePageView'

export const revalidate = 60

export default async function BusinessWebsitePage({
  params,
  searchParams,
}: {
  params: { slug: string; pageSlug: string }
  searchParams?: { preview_token?: string }
}) {
  if (RESERVED_SLUGS.has(params.slug)) notFound()
  const data = await fetchPublicWebsite(
    params.slug,
    params.pageSlug,
    searchParams?.preview_token
  )
  if (!data) notFound()
  return <WebsitePageView data={data} />
}
