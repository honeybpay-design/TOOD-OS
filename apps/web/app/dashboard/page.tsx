"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface SessionUser {
  user_id: string;
  org_id: string;
  role: string;
  expires_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Capture token from URL query param (OAuth callback redirect)
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("session_token");
    if (urlToken) {
      sessionStorage.setItem("tood_session", urlToken);
      // Remove token from URL without triggering a navigation
      const clean =
        window.location.pathname +
        (params.toString().replace(`session_token=${urlToken}`, "").replace(/^&|&$/, "")
          ? "?" + params.toString().replace(`session_token=${urlToken}`, "").replace(/^&|&$/, "")
          : "");
      history.replaceState(null, "", clean);
    }

    const token = sessionStorage.getItem("tood_session");
    if (!token) {
      router.replace("/login");
      return;
    }

    // Validate session with the API
    fetch("/api/auth/session", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401) {
          sessionStorage.removeItem("tood_session");
          router.replace("/login");
          return;
        }
        if (!res.ok) throw new Error(`${res.status}`);
        const data = (await res.json()) as SessionUser;
        setUser(data);
      })
      .catch(() => {
        // Network error — keep them on the page; they can retry
      });
  }, [router]);

  async function handleLogout() {
    setLoggingOut(true);
    const token = sessionStorage.getItem("tood_session");
    try {
      if (token) {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } finally {
      sessionStorage.removeItem("tood_session");
      router.replace("/login");
    }
  }

  return (
    <div className="min-h-screen bg-[#F8F6F1] flex flex-col">
      {/* Header */}
      <header className="bg-[#F8F6F1] border-b border-[#D4CFC8] px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/tood logo png.png" alt="TOOD" className="h-8 w-auto" />
          <span
            className="text-[#6B6560] text-sm ml-3"
            style={{ fontFamily: 'var(--font-inter)' }}
          >
            Dashboard
          </span>
        </div>

        {user && (
          <div className="flex items-center gap-4">
            <span
              className="text-[#6B6560] text-sm hidden sm:block"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              {user.org_id && (
                <span className="text-[#6B6560] mr-2">org</span>
              )}
              <span className="font-medium text-[#1C1917]">{user.role}</span>
            </span>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              aria-label="Sign out of TOOD"
              className="text-[#6B6560] hover:text-[#1C1917] text-sm font-medium transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1B4FD8] rounded"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              {loggingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center px-4">
        <div>
          <h1
            className="text-[28px] text-[#1C1917] mb-3"
            style={{ fontFamily: 'var(--font-dm-serif)' }}
          >
            Welcome to TOOD
          </h1>
          <p
            className="text-[#6B6560] mb-8"
            style={{ fontFamily: 'var(--font-inter)' }}
          >
            Your bid management dashboard is coming soon.
          </p>
          <a
            href="/"
            className="text-[#1B4FD8] hover:text-[#1541B0] text-sm transition-colors"
            style={{ fontFamily: 'var(--font-inter)' }}
          >
            &larr; Back to homepage
          </a>
        </div>
      </main>
    </div>
  );
}
