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
    <div className="min-h-screen bg-[#0F172A] flex flex-col">
      {/* Header */}
      <header className="bg-[#1E293B] border-b border-white/10 px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <span className="text-white text-xl font-bold tracking-tight">TOOD</span>

        {user && (
          <div className="flex items-center gap-4">
            <span className="text-slate-300 text-sm hidden sm:block">
              {user.org_id && (
                <span className="text-slate-500 mr-2">org</span>
              )}
              <span className="font-medium text-white">{user.role}</span>
            </span>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              aria-label="Sign out of TOOD"
              className="text-slate-400 hover:text-white text-sm font-medium transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#3B82F6] rounded"
            >
              {loggingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-4">Welcome to TOOD</h1>
          <p className="text-slate-400 mb-8">
            Your bid management dashboard is coming soon.
          </p>
          <a href="/" className="text-[#3B82F6] hover:underline text-sm">
            ← Back to homepage
          </a>
        </div>
      </main>
    </div>
  );
}
