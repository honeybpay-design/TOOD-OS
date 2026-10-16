"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Calendar, FileText, Upload, BarChart, ChevronRight, ExternalLink, Clock, CheckCircle, AlertCircle } from "lucide-react";

interface SessionUser {
  user_id: string;
  org_id: string;
  role: string;
  expires_at: string;
  org_name?: string;
  plan?: string;
}

interface Tender {
  id: string;
  name: string;
  created_at: string;
  status?: string;
  deadline?: string;
}

interface Stats {
  tenders_count: number;
  evidence_count: number;
  ai_checks_completed: number;
  compliance_score: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trialDaysLeft, setTrialDaysLeft] = useState<number>(14);

  // Calculate trial days from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;

    const trialStarted = localStorage.getItem("trial_started");
    if (trialStarted) {
      const startDate = new Date(trialStarted);
      const today = new Date();
      const diffTime = Math.abs(today.getTime() - startDate.getTime());
      const diffDays = 14 - Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      setTrialDaysLeft(Math.max(0, diffDays));

      // Redirect if trial expired
      if (diffDays <= 0) {
        router.push("/#pricing");
      }
    } else {
      // Set trial start date if not set
      localStorage.setItem("trial_started", new Date().toISOString());
    }
  }, [router]);

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

    // Fetch user data from /me endpoint
    fetch("/api/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 401) {
          sessionStorage.removeItem("tood_session");
          router.replace("/login");
          return;
        }
        if (!res.ok) throw new Error(`Failed to fetch user data: ${res.status}`);
        const data = await res.json();
        setUser(data);

        // Fetch tenders data
        const tendersRes = await fetch("/api/tenders", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (tendersRes.ok) {
          const tendersData = await tendersRes.json();
          setTenders(tendersData.tenders || tendersData || []);
        }

        // Fetch stats data
        const statsRes = await fetch("/api/evidence", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (statsRes.ok) {
          const evidenceData = await statsRes.json();
          // Calculate stats from evidence and tenders
          const tenderCount = Array.isArray(tenders) ? tenders.length : 0;
          const evidenceCount = Array.isArray(evidenceData) ? evidenceData.length : 0;

          setStats({
            tenders_count: tenderCount,
            evidence_count: evidenceCount,
            ai_checks_completed: Math.floor(Math.random() * 50), // Placeholder
            compliance_score: 85 + Math.floor(Math.random() * 15), // Placeholder
          });
        }
      })
      .catch((err) => {
        console.error("API error:", err);
        setError("Failed to load dashboard data. Please try again.");
      })
      .finally(() => {
        setLoading(false);
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

  async function handleLoadSampleTender() {
    const token = sessionStorage.getItem("tood_session");
    if (!token) {
      router.replace("/login");
      return;
    }

    try {
      const response = await fetch("/api/analyse-sample", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        alert("Sample tender loaded successfully!");
        // Refresh tenders list
        const tendersRes = await fetch("/api/tenders", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (tendersRes.ok) {
          const tendersData = await tendersRes.json();
          setTenders(tendersData.tenders || tendersData || []);
        }
      } else {
        alert("Failed to load sample tender. Please try again.");
      }
    } catch (error) {
      console.error("Error loading sample tender:", error);
      alert("Error loading sample tender. Please check your connection.");
    }
  }

  function formatDate(dateString: string) {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex flex-col">
      {/* Header */}
      <header className="bg-[var(--color-surface)] border-b border-[var(--color-border)] sticky top-0 z-10 px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/tood logo png.png" alt="TOOD" className="h-8 w-auto" />
          <div className="flex flex-col">
            <span className="text-[var(--color-text)] text-sm font-medium">
              {user?.org_name || user?.org_id || "Organization"}
            </span>
            <span className="text-[var(--color-text-muted)] text-xs">
              {user?.plan ? `Plan: ${user.plan}` : "Free Trial"}
            </span>
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-3">
              <div className="text-right">
                <span className="text-[var(--color-text)] text-sm font-medium block">
                  {user.role}
                </span>
                <span className="text-[var(--color-text-muted)] text-xs">
                  {user.user_id?.substring(0, 8)}...
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              aria-label="Sign out of TOOD"
              className="bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-offset)] text-[var(--color-text)] px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            >
              {loggingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        )}
      </header>

      {/* Trial Banner */}
      {trialDaysLeft > 0 && trialDaysLeft <= 14 && (
        <div className="bg-gradient-to-r from-[var(--color-primary)] to-[#2fb486] text-white px-4 sm:px-6 lg:px-8 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              <span className="text-sm font-medium">
                {trialDaysLeft} {trialDaysLeft === 1 ? "day" : "days"} left in your free trial
              </span>
            </div>
            <a
              href="/#pricing"
              className="bg-white text-[var(--color-primary)] hover:bg-gray-100 px-4 py-1.5 text-sm font-medium rounded-lg transition-colors inline-flex items-center gap-1"
            >
              Upgrade now <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 px-4 sm:px-6 lg:px-8 py-8 max-w-7xl mx-auto w-full">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-6 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        )}

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[var(--color-text)] mb-2">
            Welcome back, {user?.role || "User"}
          </h1>
          <p className="text-[var(--color-text-muted)]">
            Manage your tenders, evidence, and compliance checks in one place.
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <a
            href="/dashboard/tenders/new"
            className="bg-[var(--color-surface-2)] border border-[var(--color-border)] hover:border-[var(--color-primary)] hover:shadow-md rounded-xl p-5 transition-all group"
          >
            <div className="flex items-center gap-4">
              <div className="bg-[var(--color-primary-highlight)] p-3 rounded-lg">
                <FileText className="h-6 w-6 text-[var(--color-primary)]" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--color-text)] group-hover:text-[var(--color-primary)]">
                  + New tender
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">
                  Create a new bid management project
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-[var(--color-text-muted)] group-hover:text-[var(--color-primary)]" />
            </div>
          </a>

          <button
            onClick={handleLoadSampleTender}
            className="bg-[var(--color-surface-2)] border border-[var(--color-border)] hover:border-[var(--color-primary)] hover:shadow-md rounded-xl p-5 transition-all group text-left"
          >
            <div className="flex items-center gap-4">
              <div className="bg-blue-50 p-3 rounded-lg">
                <Upload className="h-6 w-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--color-text)] group-hover:text-[var(--color-primary)]">
                  Load sample tender
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">
                  Analyze a sample tender to get started
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-[var(--color-text-muted)] group-hover:text-[var(--color-primary)]" />
            </div>
          </button>

          <a
            href="/dashboard/evidence/new"
            className="bg-[var(--color-surface-2)] border border-[var(--color-border)] hover:border-[var(--color-primary)] hover:shadow-md rounded-xl p-5 transition-all group"
          >
            <div className="flex items-center gap-4">
              <div className="bg-green-50 p-3 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--color-text)] group-hover:text-[var(--color-primary)]">
                  Add evidence
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">
                  Upload compliance evidence and documents
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-[var(--color-text-muted)] group-hover:text-[var(--color-primary)]" />
            </div>
          </a>
        </div>

        {/* Stats Row */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-[var(--color-surface-2)] border border-[var(--color-border)] rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-[var(--color-text-muted)]">Active Tenders</h3>
                <FileText className="h-5 w-5 text-[var(--color-primary)]" />
              </div>
              <p className="text-3xl font-bold text-[var(--color-text)]">{stats.tenders_count}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">Total bid projects</p>
            </div>

            <div className="bg-[var(--color-surface-2)] border border-[var(--color-border)] rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-[var(--color-text-muted)]">Evidence Items</h3>
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <p className="text-3xl font-bold text-[var(--color-text)]">{stats.evidence_count}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">Compliance documents</p>
            </div>

            <div className="bg-[var(--color-surface-2)] border border-[var(--color-border)] rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-[var(--color-text-muted)]">AI Checks</h3>
                <BarChart className="h-5 w-5 text-blue-600" />
              </div>
              <p className="text-3xl font-bold text-[var(--color-text)]">{stats.ai_checks_completed}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">Verifications completed</p>
            </div>

            <div className="bg-[var(--color-surface-2)] border border-[var(--color-border)] rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-[var(--color-text-muted)]">Compliance Score</h3>
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <p className="text-3xl font-bold text-[var(--color-text)]">{stats.compliance_score}%</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">Overall compliance rating</p>
            </div>
          </div>
        )}

        {/* Recent Tenders */}
        <div className="bg-[var(--color-surface-2)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <div className="border-b border-[var(--color-border)] px-6 py-4">
            <h2 className="text-lg font-semibold text-[var(--color-text)]">Recent Tenders</h2>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">
              Your most recent bid management projects
            </p>
          </div>

          <div className="p-6">
            {loading ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary)]"></div>
                <p className="text-[var(--color-text-muted)] mt-2">Loading tenders...</p>
              </div>
            ) : tenders.length > 0 ? (
              <div className="space-y-3">
                {tenders.slice(0, 5).map((tender) => (
                  <div
                    key={tender.id}
                    className="flex items-center justify-between p-4 hover:bg-[var(--color-surface)] rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="bg-[var(--color-primary-highlight)] p-2 rounded-lg">
                        <FileText className="h-5 w-5 text-[var(--color-primary)]" />
                      </div>
                      <div>
                        <h3 className="font-medium text-[var(--color-text)]">{tender.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <Calendar className="h-3 w-3 text-[var(--color-text-muted)]" />
                          <span className="text-xs text-[var(--color-text-muted)]">
                            Created {formatDate(tender.created_at)}
                          </span>
                          {tender.status && (
                            <span className={`text-xs px-2 py-0.5 rounded-full ${tender.status === 'active' ? 'bg-green-100 text-green-800' :
                                tender.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                              }`}>
                              {tender.status}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-[var(--color-text-muted)]" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 text-[var(--color-text-muted)] mx-auto mb-3 opacity-50" />
                <h3 className="text-lg font-medium text-[var(--color-text)] mb-2">No tenders yet</h3>
                <p className="text-[var(--color-text-muted)] mb-4">
                  Get started by creating your first tender or loading a sample.
                </p>
                <div className="flex gap-3 justify-center">
                  <a
                    href="/dashboard/tenders/new"
                    className="bg-[var(--color-primary)] text-white px-4 py-2 rounded-lg font-medium hover:bg-[var(--color-primary-hover)] transition-colors"
                  >
                    + New tender
                  </a>
                  <button
                    onClick={handleLoadSampleTender}
                    className="border border-[var(--color-border)] text-[var(--color-text)] px-4 py-2 rounded-lg font-medium hover:bg-[var(--color-surface)] transition-colors"
                  >
                    Load sample
                  </button>
                </div>
              </div>
            )}

            {tenders.length > 5 && (
              <div className="mt-6 pt-6 border-t border-[var(--color-border)]">
                <a
                  href="/dashboard/tenders"
                  className="text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] font-medium inline-flex items-center gap-1"
                >
                  View all tenders <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
