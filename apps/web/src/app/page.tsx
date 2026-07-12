import React from 'react'
export const dynamic = 'force-dynamic'

import { redirect } from 'next/navigation'
import { COLORS } from '@platform/ui'
import { createClient } from '@/lib/supabase/server'

async function getProfile(token: string) {
  // Use absolute URL since this is SSR
  // In a real app we'd get the API URL from environment
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
  
  const res = await fetch(`${apiUrl}/me`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  
  if (!res.ok) {
    if (res.status === 401) {
      return null
    }
    throw new Error('Failed to fetch profile')
  }
  
  return res.json()
}

export default async function Page() {
  const supabase = createClient()
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    redirect('/login')
  }

  const profile = await getProfile(session.access_token)

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        fontFamily: 'system-ui, sans-serif',
        backgroundColor: COLORS.primary,
        color: COLORS.background,
        padding: '2rem',
      }}
    >
      <div
        style={{
          maxWidth: '600px',
          textAlign: 'center',
          background: 'rgba(255, 255, 255, 0.05)',
          padding: '3rem',
          borderRadius: '16px',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        }}
      >
        <h1
          style={{
            fontSize: '2.5rem',
            marginBottom: '1rem',
            fontWeight: 800,
            background: 'linear-gradient(to right, #3B82F6, #8B5CF6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Identity Foundation
        </h1>
        
        {profile ? (
          <div style={{ textAlign: 'left', marginBottom: '2rem', backgroundColor: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
            <p><strong>ID:</strong> {profile.id}</p>
            <p><strong>Email:</strong> {profile.email}</p>
            <p><strong>Display Name:</strong> {profile.display_name}</p>
          </div>
        ) : (
          <p style={{ color: COLORS.secondary, fontSize: '1.1rem', marginBottom: '2rem' }}>
            Loading profile...
          </p>
        )}

        <form action="/auth/logout" method="post">
          <button
            type="submit"
            style={{
              display: 'inline-block',
              padding: '0.75rem 1.5rem',
              borderRadius: '8px',
              backgroundColor: '#ef4444',
              color: '#fff',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer'
            }}
          >
            Logout
          </button>
        </form>
      </div>
    </div>
  )
}
