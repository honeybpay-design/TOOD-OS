"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Metrics {
  mrr_gbp: number;
  active_subscriptions: number;
  total_orgs: number;
  churn_rate_30d_pct: number;
}

interface Tenant {
  id: string;
  name: string;
  plan: string;
  tender_count: number;
  user_count: number;
}

interface Health {
  overall: string;
  database: { ok: boolean; error?: string };
  ai_provider: { name: string; status: string };
}

export default function AdminPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("tood_token") : null;
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

    Promise.all([
      fetch("/api/admin/metrics", { headers }).then((r) => r.json()),
      fetch("/api/admin/tenants", { headers }).then((r) => r.json()),
      fetch("/api/admin/health", { headers }).then((r) => r.json()),
    ])
      .then(([m, t, h]) => {
        setMetrics(m as Metrics);
        setTenants(Array.isArray(t) ? (t as Tenant[]) : []);
        setHealth(h as Health);
      })
      .catch((e: unknown) => setError(String(e)));
  }, []);

  return (
    <div className="min-h-screen bg-slate-100">
      <nav className="bg-[#0F172A] px-6 py-4 flex items-center justify-between">
        <span className="text-white font-bold text-lg">TOOD Admin</span>
        <Link href="/" className="text-slate-400 hover:text-white text-sm transition-colors">← Back to site</Link>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            Error loading dashboard: {error}
          </div>
        )}

        {/* Health */}
        {health && (
          <div className={`mb-6 px-4 py-3 rounded-lg border text-sm font-medium ${
            health.overall === "healthy"
              ? "bg-green-50 border-green-200 text-green-700"
              : "bg-yellow-50 border-yellow-200 text-yellow-700"
          }`}>
            System: {health.overall.toUpperCase()} — DB: {health.database.ok ? "✓ OK" : `✗ ${health.database.error}`}
            {" | "}AI: {health.ai_provider.name} ({health.ai_provider.status})
          </div>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "MRR", value: metrics ? `£${metrics.mrr_gbp.toLocaleString()}` : "—" },
            { label: "Active Subscriptions", value: metrics?.active_subscriptions ?? "—" },
            { label: "Total Organisations", value: metrics?.total_orgs ?? "—" },
            { label: "30-day Churn", value: metrics ? `${metrics.churn_rate_30d_pct}%` : "—" },
          ].map((m) => (
            <div key={m.label} className="bg-white rounded-xl p-5 border border-slate-200">
              <div className="text-slate-500 text-xs mb-1">{m.label}</div>
              <div className="text-2xl font-bold text-[#0F172A]">{String(m.value)}</div>
            </div>
          ))}
        </div>

        {/* Tenants table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="font-semibold text-[#0F172A]">Organisations</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Name", "Plan", "Tenders", "Users"].map((h) => (
                    <th key={h} className="text-left px-6 py-3 text-slate-500 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tenants.length === 0 ? (
                  <tr><td colSpan={4} className="px-6 py-4 text-slate-400 text-center">No organisations yet.</td></tr>
                ) : (
                  tenants.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-[#0F172A]">{t.name}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${
                          t.plan === "enterprise" ? "bg-purple-100 text-purple-700" :
                          t.plan === "professional" ? "bg-blue-100 text-blue-700" :
                          "bg-slate-100 text-slate-600"
                        }`}>{t.plan}</span>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{t.tender_count}</td>
                      <td className="px-6 py-4 text-slate-600">{t.user_count}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
