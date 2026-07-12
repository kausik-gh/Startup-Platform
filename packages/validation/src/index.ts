import { z } from 'zod'

// Common validator primitives
export const uuidSchema = z.string().uuid()

export const emailSchema = z.string().email()

// Example Business Profile common validation
export const businessCreationSchema = z.object({
  displayName: z.string().min(2).max(100),
  slug: z.string().min(2).max(50).regex(/^[a-z0-9-]+$/),
  businessType: z.string().min(1),
})

export type BusinessCreationInput = z.infer<typeof businessCreationSchema>
