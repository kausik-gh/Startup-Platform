import { z } from 'zod'

// Common validator primitives
export const uuidSchema = z.string().uuid()

export const emailSchema = z.string().email()

export const supportedBusinessTypes = [
  'retail',
  'restaurant',
  'cafe',
  'hotel',
  'homestay',
  'salon',
  'spa',
  'gym',
  'studio',
  'clinic',
  'professional_service',
  'education',
  'other',
  'not_sure',
] as const

export const supportedCurrencies = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'AUD'] as const
export const supportedCountries = ['IN', 'US', 'GB', 'AE', 'SG', 'AU', 'CA'] as const
export const supportedLanguages = ['en', 'hi', 'ta', 'te', 'kn', 'ml', 'mr', 'bn', 'gu'] as const
export const supportedTimezones = [
  'UTC',
  'Asia/Kolkata',
  'Asia/Dubai',
  'Asia/Singapore',
  'Europe/London',
  'America/New_York',
  'America/Los_Angeles',
  'Australia/Sydney',
] as const

/** Aligns with POST /v1/platform/businesses (Stage 2A). */
export const businessCreationSchema = z.object({
  display_name: z.string().trim().min(2).max(100),
  business_type: z.enum(supportedBusinessTypes).optional().default('not_sure'),
  slug: z
    .string()
    .trim()
    .min(2)
    .max(50)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)
    .optional(),
  logo_asset_id: uuidSchema.optional(),
  timezone: z.enum(supportedTimezones).optional(),
  currency: z.enum(supportedCurrencies).optional(),
  country: z.enum(supportedCountries).optional(),
  language: z.enum(supportedLanguages).optional(),
})

export type BusinessCreationInput = z.infer<typeof businessCreationSchema>
