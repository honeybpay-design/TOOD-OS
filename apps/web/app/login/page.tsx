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
      className="min-h-screen bg-[#F8F6F1] flex flex-col items-center justify-center px-4"
      role="main"
    >
      <div className="w-full max-w-sm flex flex-col items-center gap-6">
        {/* Logo */}
        <div className="flex flex-col items-center gap-3">
          <img
            src="/tood logo png.png"
            alt="TOOD"
            className="h-20 w-auto"
          />
          <h1
            className="text-[28px] text-[#1C1917] leading-tight text-center"
            style={{ fontFamily: 'var(--font-dm-serif)' }}
          >
            Sign in to TOOD
          </h1>
          <p
            className="text-[15px] text-[#6B6560] text-center"
            style={{ fontFamily: 'var(--font-inter)' }}
          >
            Trusted Operations &amp; Organised Documents
          </p>
        </div>

        {/* Divider */}
        <hr className="w-full border-[#D4CFC8]" />

        {/* Google sign-in button */}
        <button
          onClick={handleSignIn}
          disabled={loading}
          aria-label="Sign in with your Google account"
          className="w-full flex items-center justify-center gap-3 bg-white hover:bg-[#EFEDE8] disabled:opacity-60 disabled:cursor-not-allowed text-[#1C1917] font-semibold px-5 py-3 rounded border border-[#D4CFC8] text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1B4FD8]"
          style={{ fontFamily: 'var(--font-inter)' }}
        >
          {loading ? (
            <>
              <svg
                className="w-5 h-5 animate-spin text-[#1B4FD8]"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              <span>Redirecting…</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" aria-hidden="true">
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
            className="text-red-600 text-sm text-center"
            style={{ fontFamily: 'var(--font-inter)' }}
          >
            {error}
          </p>
        )}

        <p
          className="text-[#6B6560] text-xs text-center leading-relaxed"
          style={{ fontFamily: 'var(--font-inter)' }}
        >
          By signing in you agree to our{' '}
          <a href="#" className="underline hover:text-[#1C1917] transition-colors">
            Terms of Service
          </a>
        </p>
      </div>

      <a
        href="/"
        className="mt-8 text-[#6B6560] hover:text-[#1C1917] text-sm transition-colors"
        style={{ fontFamily: 'var(--font-inter)' }}
      >
        &larr; Back to homepage
      </a>
    </div>
  );
}
