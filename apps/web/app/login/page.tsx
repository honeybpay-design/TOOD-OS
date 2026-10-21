"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

function LoginContent() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const plan = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('plan') || '' : '';
  const planDisplayName = plan === 'professional' ? 'Professional' : plan === 'starter' ? 'Starter' : '';

  useEffect(() => {
    // The session is stored as an HttpOnly cookie, not in sessionStorage.
    // Check with /api/me: if the server returns 200 the user is already
    // authenticated and should skip the login page.
    fetch("/api/me", { credentials: "include" })
      .then((res) => { if (res.ok) router.replace("/dashboard"); })
      .catch(() => { /* no session â€” stay on login */ });
  }, [router]);

  async function handleSignIn() {
    setLoading(true);
    setError(null);
    try {
      const url = plan ? `/v1/auth/google?plan=${encodeURIComponent(plan)}` : '/v1/auth/google';
      const res = await fetch(url);
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
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg)',
        display: 'flex',
        flexDirection: 'column'
      }}
      role="main"
    >
      {/* Mobile layout - vertical stacking */}
      <div className="login-container" style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0
      }}>
        {/* Left panel (top on mobile) */}
        <div className="login-left-panel" style={{
          flex: '1',
          display: 'flex',
          flexDirection: 'column',
          padding: 'var(--space-8) var(--space-4)',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '420px',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-8)'
          }}>
            {/* Logo and branding */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                <div style={{ position: 'relative', width: '48px', height: '48px' }}>
                  <Image
                    src="/tood logo png.png"
                    alt="tood.os logo"
                    fill
                    style={{ objectFit: 'contain' }}
                    priority
                  />
                </div>
                <span style={{
                  fontFamily: 'var(--font-display)',
                  fontWeight: 800,
                  fontSize: '1.8rem',
                  letterSpacing: '-.03em',
                  color: 'var(--color-text)'
                }}>
                  tood.os
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                <h1 style={{
                  fontFamily: 'var(--font-display)',
                  fontWeight: 800,
                  fontSize: 'clamp(2rem, 1.2rem + 2vw, 3rem)',
                  letterSpacing: '-.035em',
                  color: 'var(--color-text)',
                  lineHeight: 1.1
                }}>
                  Start your 14-day free trial
                </h1>
                <p style={{
                  fontFamily: 'var(--font-body)',
                  fontSize: 'var(--text-lg)',
                  color: 'var(--color-text-muted)',
                  lineHeight: 1.6
                }}>
                  No credit card required
                </p>
              </div>

              {/* Plan notice */}
              {planDisplayName && (
                <div style={{
                  background: 'var(--color-primary-highlight)',
                  border: '1px solid var(--color-primary)',
                  borderRadius: 'var(--radius-lg)',
                  padding: 'var(--space-4) var(--space-5)',
                  color: 'var(--color-primary)',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 600
                }}>
                  You're starting the <span style={{ fontWeight: 800 }}>{planDisplayName}</span> plan â€” 14 days free
                </div>
              )}
            </div>

            {/* Google sign-in button */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
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
                  border: '2px solid var(--color-border)',
                  borderRadius: 'var(--radius-full)',
                  padding: '0 var(--space-6)',
                  minHeight: '56px',
                  fontFamily: 'var(--font-body)',
                  fontWeight: 700,
                  fontSize: 'var(--text-base)',
                  color: 'var(--color-text)',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                  transition: 'all var(--transition-interactive)',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                {loading ? (
                  <>
                    <svg
                      style={{ width: '22px', height: '22px', animation: 'spin .8s linear infinite', color: 'var(--color-primary)' }}
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                    </svg>
                    <span>Redirectingâ€¦</span>
                  </>
                ) : (
                  <>
                    <svg style={{ width: '22px', height: '22px', flexShrink: 0 }} viewBox="0 0 24 24" aria-hidden="true">
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

              <p style={{
                color: 'var(--color-text-faint)',
                fontSize: 'var(--text-xs)',
                textAlign: 'center',
                lineHeight: 1.6,
                fontFamily: 'var(--font-body)',
                paddingTop: 'var(--space-2)'
              }}>
                By continuing you agree to our Terms of Service
              </p>
            </div>

            {/* Back link */}
            <a
              href="/"
              style={{
                color: 'var(--color-text-muted)',
                fontSize: 'var(--text-sm)',
                fontFamily: 'var(--font-body)',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)'
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back to homepage
            </a>
          </div>
        </div>

        {/* Right panel (bottom on mobile) */}
        <div className="login-right-panel" style={{
          flex: '1',
          background: 'var(--ink)',
          color: 'var(--ink-text)',
          padding: 'var(--space-8) var(--space-4)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          position: 'relative',
          overflow: 'hidden'
        }}>
          {/* Background pattern */}
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: 'linear-gradient(var(--ink-line) 1px, transparent 1px), linear-gradient(90deg, var(--ink-line) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
            maskImage: 'radial-gradient(ellipse at 50% 50%, #000 10%, transparent 70%)',
            pointerEvents: 'none'
          }} />

          <div style={{
            position: 'relative',
            zIndex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-12)',
            maxWidth: '560px',
            margin: '0 auto',
            width: '100%'
          }}>
            {/* Benefits section */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              <h2 style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 800,
                fontSize: 'var(--text-xl)',
                letterSpacing: '-.03em',
                color: 'var(--ink-text)'
              }}>
                What you'll get with your trial
              </h2>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                {[
                  'Full access to AI-assisted bid writing',
                  'Compliance verification against 200+ public sector requirements',
                  'Real-time evidence matching from your knowledge base',
                  'Collaborative workspace for your entire bid team',
                  'Export-ready bid documents in DOCX and PDF formats',
                  'Priority support during your trial period'
                ].map((benefit, index) => (
                  <div key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ color: 'var(--mint)', flexShrink: 0, marginTop: '2px' }}>
                      <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span style={{ fontSize: 'var(--text-base)', lineHeight: 1.5, color: 'var(--ink-text)' }}>
                      {benefit}
                    </span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* Desktop responsive styles via CSS */}
      <style jsx>{`
        @media (min-width: 1024px) {
          .login-container {
            flex-direction: row;
          }
          .login-left-panel {
            flex: 0 0 40%;
            padding: var(--space-16) var(--space-20);
            align-items: flex-start;
          }
          .login-right-panel {
            flex: 1;
            padding: var(--space-16);
          }
        }
      `}</style>
    </div>
  );
}

export default function LoginPage() {
  return <LoginContent />;
}
