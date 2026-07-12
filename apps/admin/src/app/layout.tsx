import React from 'react'

export const metadata = {
  title: 'Platform Admin',
  description: 'Multi-tenant Platform Super Admin dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
