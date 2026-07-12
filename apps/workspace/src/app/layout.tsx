import React from 'react'

export const metadata = {
  title: 'Business Workspace',
  description: 'Multi-tenant Platform Business Operating Surface',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
