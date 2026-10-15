"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = sessionStorage.getItem('tood_session');
      if (token) router.replace('/dashboard');
    }
  }, [router]);

  async function handleSignIn() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/auth/google');
      if (!res.ok) throw new Error(`${res.status}`);
      const data = (await res.json()) as { auth_url: string };
      if (!data.auth_url) throw new Error('missing auth_url');
      window.location.href = data.auth_url;
    } catch {
      setLoading(false);
      setError('Sign-in is temporarily unavailable. Please try again.');
    }
  }

  return (
    <div
      style={{ minHeight: '100vh', background: 'var(--color-bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 var(--space-4)' }}
      role="main"
    >
      <div style={{ width: '100%', maxWidth: '360px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-6)' }}>
        {/* Logo */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-3)' }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ color: 'var(--color-text)' }}>
            <rect x="3.5" y="3.5" width="17" height="17" rx="3.5" stroke="currentColor" strokeWidth="1.8" />
            <path d="M8 9h8M8 12.5h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="16" cy="16" r="2.2" fill="var(--color-primary)" />
          </svg>
          <h1
            style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: '1.6rem', letterSpacing: '-.03em', color: 'var(--color-text)', textAlign: 'center' }}
          >
            Sign in to tood.os
          </h1>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', textAlign: 'center' }}>
            Verifiable, evidence-bound AI for UK public-sector bids
          </p>
        </div>

        {/* Divider */}
        <div style={{ width: '100%', height: '1px', background: 'var(--color-divider)' }} />

        {/* Google sign-in button */}
        <button
          onClick={handleSignIn}
          disabled={loading}
          aria-label="Sign in with your Google account"
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-3)',
            background: 'var(--color-surface-2)',
            border: '1.5px solid var(--color-border)',
            borderRadius: 'var(--radius-full)',
            padding: '0 var(--space-5)',
            minHeight: '48px',
            fontFamily: 'var(--font-body)',
            fontWeight: 600,
            fontSize: 'var(--text-sm)',
            color: 'var(--color-text)',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            transition: 'background var(--transition-interactive), border-color var(--transition-interactive)',
          }}
        >
          {loading ? (
            <>
              <svg
                style={{ width: '20px', height: '20px', animation: 'spin .8s linear infinite', color: 'var(--color-primary)' }}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              <span>Redirecting…</span>
            </>
          ) : (
            <>
              <svg style={{ width: '20px', height: '20px', flexShrink: 0 }} viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              <span>Continue with Google</span>
            </>
          )}
        </button>

        {error && (
          <p
            role="alert"
            style={{ color: 'var(--p-flag)', fontSize: 'var(--text-sm)', textAlign: 'center', fontFamily: 'var(--font-body)' }}
          >
            {error}
          </p>
        )}

        <p style={{ color: 'var(--color-text-faint)', fontSize: 'var(--text-xs)', textAlign: 'center', lineHeight: 1.6, fontFamily: 'var(--font-body)' }}>
          By signing in you agree to our{' '}
          <a href="#" style={{ textDecoration: 'underline', textUnderlineOffset: '3px' }}>
            Terms of Service
          </a>
        </p>
      </div>

      <a
        href="/"
        style={{ marginTop: 'var(--space-8)', color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', fontFamily: 'var(--font-body)', textDecoration: 'none' }}
      >
        ← Back to homepage
      </a>
    </div>
  );
}
