import React from 'react'
import { COLORS } from '@platform/ui'

export default function Page() {
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
            background: 'linear-gradient(to right, #EF4444, #F59E0B)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Platform Super Admin
        </h1>
        <p style={{ color: COLORS.secondary, fontSize: '1.1rem', marginBottom: '2rem' }}>
          Restricted access. Platform-wide operations, Entitlements management, and support panel.
        </p>
        <div
          style={{
            display: 'inline-block',
            padding: '0.75rem 1.5rem',
            borderRadius: '8px',
            backgroundColor: '#EF4444',
            color: '#fff',
            fontWeight: 600,
          }}
        >
          apps/admin (Active)
        </div>
      </div>
    </div>
  )
}
