"use client";

import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ChevronRight,
  FilePlus2,
  FileText,
  FolderKanban,
  Library,
  LogOut,
  Menu,
  Plus,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type SessionUser = {
  org: { id: string; name: string };
  user: { id: string; email: string };
  role: string;
  ai_provider: string;
};

type Tender = {
  id: string;
  title: string;
  stage: string;
  requirements: number;
  questions: number;
};

type EvidenceItem = {
  id: string;
  kind: string;
  title: string;
  status: string;
  preview: string;
};

type BillingStatus = {
  plan: string;
  status: string;
  limits: { max_tenders: number; max_users: number; ai_provider: string };
  usage: { tenders: number; users: number };
};

type Composer = "tender" | "evidence" | null;

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [composer, setComposer] = useState<Composer>(null);
  const [saving, setSaving] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const loadWorkspace = useCallback(async () => {
    // All API calls go through Next.js route handlers that read the HttpOnly
    // `tood_session` cookie server-side and attach it to the upstream request,
    // so the client never handles the token and no auth header is needed here.
    const responses = await Promise.all([
      fetch("/api/me", { credentials: "include" }),
      fetch("/api/tenders", { credentials: "include" }),
      fetch("/api/evidence", { credentials: "include" }),
      fetch("/api/billing/status", { credentials: "include" }),
    ]);

    if (responses.some((response) => response.status === 401)) {
      router.replace("/login");
      return;
    }

    const failed = responses.find((response) => !response.ok);
    if (failed) throw new Error(`Workspace request failed (${failed.status})`);

    const [meData, tenderData, evidenceData, billingData] = await Promise.all(
      responses.map((response) => response.json()),
    );
    setUser(meData as SessionUser);
    setTenders(tenderData as Tender[]);
    setEvidence(evidenceData as EvidenceItem[]);
    setBilling(billingData as BillingStatus);
  }, [router]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadWorkspace()
        .catch(() => setError("We could not load your workspace. Check your connection and try again."))
        .finally(() => setLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadWorkspace, router]);

  const totals = useMemo(() => ({
    requirements: tenders.reduce((sum, tender) => sum + tender.requirements, 0),
    questions: tenders.reduce((sum, tender) => sum + tender.questions, 0),
    approvedEvidence: evidence.filter((item) => item.status === "approved").length,
  }), [evidence, tenders]);

  async function refreshWorkspace() {
    await loadWorkspace();
  }

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } finally {
      router.replace("/login");
    }
  }

  async function createTender(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(null);
    try {
      const response = await fetch("/api/tenders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ title: form.get("title") }),
      });
      if (response.status === 401) {
        router.replace("/login");
        return;
      }
      if (!response.ok) throw new Error(String(response.status));
      await refreshWorkspace();
      setComposer(null);
      setNotice("Tender created. Add the tender documents when you are ready.");
    } catch {
      setError("The tender could not be created. Bid manager access is required.");
    } finally {
      setSaving(false);
    }
  }

  async function createEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(null);
    try {
      const response = await fetch("/api/evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          kind: form.get("kind"),
          title: form.get("title"),
          body: form.get("body"),
          approved: false,
        }),
      });
      if (response.status === 401) {
        router.replace("/login");
        return;
      }
      if (!response.ok) throw new Error(String(response.status));
      await refreshWorkspace();
      setComposer(null);
      setNotice("Evidence saved as a draft. A bid manager can review and approve it.");
    } catch {
      setError("The evidence item could not be saved. Contributor access is required.");
    } finally {
      setSaving(false);
    }
  }

  const nav = [
    { label: "Overview", icon: FolderKanban, href: "#overview" },
    { label: "Tenders", icon: FileText, href: "#tenders" },
    { label: "Evidence", icon: Library, href: "#evidence" },
    { label: "Assurance", icon: ShieldCheck, href: "#assurance" },
  ];

  return (
    <div className="min-h-screen bg-[#08090b] text-[#eef2f5]">
      <a href="#workspace-main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-[#4cc4ea] focus:px-4 focus:py-2 focus:text-[#031219]">
        Skip to workspace
      </a>

      <aside className={`fixed inset-y-0 left-0 z-40 w-72 border-r border-white/10 bg-[#0b0d10] p-5 transition-transform lg:translate-x-0 ${mobileNavOpen ? "translate-x-0" : "-translate-x-full"}`} aria-label="Workspace navigation">
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 text-lg font-semibold tracking-tight">
              <span className="grid h-9 w-9 place-items-center rounded-xl border border-[#4cc4ea]/35 bg-[#4cc4ea]/10 text-[#8fdcf5]">
                <BookOpenCheck size={19} strokeWidth={1.8} />
              </span>
              tood.os
            </Link>
            <button className="rounded-lg p-2 text-[#a9b3bc] hover:bg-white/5 lg:hidden" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation">
              <X size={20} />
            </button>
          </div>

          <p className="mt-8 font-mono text-[11px] uppercase tracking-[0.16em] text-[#78838d]">Workspace</p>
          <nav className="mt-3 space-y-1">
            {nav.map(({ label, icon: Icon, href }, index) => (
              <a key={label} href={href} onClick={() => setMobileNavOpen(false)} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${index === 0 ? "border border-[#4cc4ea]/25 bg-[#4cc4ea]/10 text-[#eef2f5]" : "text-[#a9b3bc] hover:bg-white/5 hover:text-[#eef2f5]"}`}>
                <Icon size={18} strokeWidth={1.7} />
                {label}
              </a>
            ))}
          </nav>

          <div className="mt-auto rounded-2xl border border-white/10 bg-white/[0.025] p-4">
            <p className="truncate text-sm font-medium">{user?.org.name ?? "Loading workspace"}</p>
            <p className="mt-1 truncate text-xs text-[#78838d]">{user?.user.email ?? "Secure session"}</p>
            <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
              <span className="rounded-full bg-[#4cc4ea]/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-[#8fdcf5]">
                {billing ? titleCase(billing.plan) : "Workspace"}
              </span>
              <button onClick={handleLogout} disabled={loggingOut} className="rounded-lg p-2 text-[#a9b3bc] hover:bg-white/5 hover:text-white disabled:opacity-50" aria-label="Sign out">
                <LogOut size={17} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {mobileNavOpen && <button className="fixed inset-0 z-30 bg-black/70 lg:hidden" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation overlay" />}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-[#08090b]/90 px-4 backdrop-blur-xl sm:px-8">
          <button className="rounded-lg p-2 text-[#a9b3bc] hover:bg-white/5 lg:hidden" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation">
            <Menu size={21} />
          </button>
          <div className="hidden items-center gap-2 text-sm text-[#78838d] sm:flex">
            <span>{user?.org.name ?? "Workspace"}</span>
            <ChevronRight size={14} />
            <span className="text-[#eef2f5]">Overview</span>
          </div>
          <button onClick={() => setComposer("tender")} className="inline-flex h-10 items-center gap-2 rounded-[10px] bg-[#4cc4ea] px-4 text-sm font-semibold text-[#031219] shadow-[0_10px_30px_rgba(76,196,234,.18)] transition hover:bg-[#6fd2f1] active:scale-[.97]">
            <Plus size={17} strokeWidth={2} /> New tender
          </button>
        </header>

        <main id="workspace-main" className="mx-auto max-w-[1240px] px-4 py-10 sm:px-8 sm:py-14">
          <section id="overview" className="scroll-mt-24">
            <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-[#8fdcf5]">Document intelligence workspace</p>
            <div className="mt-4 flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <div>
                <h1 className="max-w-3xl bg-gradient-to-b from-[#88939d] via-[#d6dde2] to-[#f3f6f8] bg-clip-text text-4xl font-semibold leading-[1.05] tracking-[-0.045em] text-transparent sm:text-6xl">
                  Every bid, grounded in its source.
                </h1>
                <p className="mt-5 max-w-2xl text-base leading-7 text-[#a9b3bc] sm:text-lg">
                  Review tenders, approved evidence and export blockers from one accountable workspace.
                </p>
              </div>
              <div className="flex items-center gap-2 text-sm text-[#a9b3bc]">
                <span className="h-2 w-2 rounded-full bg-[#6cc59a]" aria-hidden="true" />
                {billing ? `${titleCase(billing.status)} ${titleCase(billing.plan)} plan` : "Loading plan status"}
              </div>
            </div>
          </section>

          {(error || notice) && (
            <div className={`mt-8 flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${error ? "border-[#df8080]/35 bg-[#df8080]/10 text-[#f1b1b1]" : "border-[#6cc59a]/30 bg-[#6cc59a]/10 text-[#a8dfc2]"}`} role={error ? "alert" : "status"}>
              {error ? <ShieldCheck className="mt-0.5 shrink-0" size={18} /> : <CheckCircle2 className="mt-0.5 shrink-0" size={18} />}
              <span>{error ?? notice}</span>
            </div>
          )}

          {composer && (
            <section className="mt-8 rounded-[22px] border border-[#4cc4ea]/25 bg-gradient-to-b from-[#0f151a] to-[#0b0d10] p-5 shadow-2xl sm:p-7" aria-labelledby="composer-title">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#8fdcf5]">New workspace record</p>
                  <h2 id="composer-title" className="mt-2 text-2xl font-semibold tracking-tight">{composer === "tender" ? "Create a tender" : "Add evidence"}</h2>
                </div>
                <button onClick={() => setComposer(null)} className="rounded-lg p-2 text-[#a9b3bc] hover:bg-white/5 hover:text-white" aria-label="Close form"><X size={20} /></button>
              </div>

              {composer === "tender" ? (
                <form onSubmit={createTender} className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-end">
                  <label className="flex-1 text-sm text-[#a9b3bc]">Tender title
                    <input required minLength={2} maxLength={300} name="title" className="mt-2 h-12 w-full rounded-[10px] border border-white/15 bg-[#14181d] px-4 text-[#eef2f5] outline-none transition placeholder:text-[#65707a] focus:border-[#4cc4ea] focus:ring-2 focus:ring-[#4cc4ea]/20" placeholder="e.g. Council service desk procurement" />
                  </label>
                  <button disabled={saving} className="h-12 rounded-[10px] bg-[#4cc4ea] px-5 font-semibold text-[#031219] hover:bg-[#6fd2f1] disabled:opacity-50">{saving ? "Creating..." : "Create tender"}</button>
                </form>
              ) : (
                <form onSubmit={createEvidence} className="mt-6 grid gap-4 md:grid-cols-2">
                  <label className="text-sm text-[#a9b3bc]">Evidence type
                    <select name="kind" className="mt-2 h-12 w-full rounded-[10px] border border-white/15 bg-[#14181d] px-4 text-[#eef2f5] outline-none focus:border-[#4cc4ea]">
                      <option value="case_study">Case study</option><option value="policy">Policy</option><option value="cv">CV</option><option value="method">Method</option><option value="financial">Financial</option><option value="company_fact">Company fact</option>
                    </select>
                  </label>
                  <label className="text-sm text-[#a9b3bc]">Title
                    <input required minLength={2} maxLength={200} name="title" className="mt-2 h-12 w-full rounded-[10px] border border-white/15 bg-[#14181d] px-4 text-[#eef2f5] outline-none focus:border-[#4cc4ea]" placeholder="Evidence title" />
                  </label>
                  <label className="text-sm text-[#a9b3bc] md:col-span-2">Evidence text
                    <textarea required minLength={10} maxLength={20000} name="body" rows={5} className="mt-2 w-full rounded-[10px] border border-white/15 bg-[#14181d] px-4 py-3 text-[#eef2f5] outline-none focus:border-[#4cc4ea]" placeholder="Paste the approved source text. It will be saved as a draft until reviewed." />
                  </label>
                  <div className="md:col-span-2 flex justify-end"><button disabled={saving} className="h-12 rounded-[10px] bg-[#4cc4ea] px-5 font-semibold text-[#031219] hover:bg-[#6fd2f1] disabled:opacity-50">{saving ? "Saving..." : "Save evidence draft"}</button></div>
                </form>
              )}
            </section>
          )}

          <section className="mt-10 grid gap-px overflow-hidden rounded-[18px] border border-white/10 bg-white/10 sm:grid-cols-2 xl:grid-cols-4" aria-label="Workspace totals">
            {[
              ["Tenders", tenders.length, "Active bid workspaces"],
              ["Requirements", totals.requirements, "Source-linked requirements"],
              ["Questions", totals.questions, "Drafting work items"],
              ["Approved evidence", totals.approvedEvidence, `${evidence.length} total evidence items`],
            ].map(([label, value, detail]) => (
              <div key={label} className="bg-[#0f1216] p-5 sm:p-6">
                <p className="text-sm text-[#78838d]">{label}</p>
                <p className="mt-3 text-3xl font-semibold tabular-nums">{loading ? "–" : value}</p>
                <p className="mt-2 text-xs text-[#78838d]">{detail}</p>
              </div>
            ))}
          </section>

          <section className="mt-10 grid gap-6 xl:grid-cols-[1.55fr_.85fr]">
            <div id="tenders" className="scroll-mt-24 overflow-hidden rounded-[18px] border border-white/10 bg-[#0f1216]">
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-5 sm:px-6">
                <div><h2 className="text-lg font-semibold">Tender workspaces</h2><p className="mt-1 text-sm text-[#78838d]">Requirements and questions grouped by tender.</p></div>
                <button onClick={() => setComposer("tender")} className="rounded-lg p-2 text-[#8fdcf5] hover:bg-[#4cc4ea]/10" aria-label="Create a tender"><FilePlus2 size={20} /></button>
              </div>
              <div className="divide-y divide-white/10">
                {loading ? <p className="p-6 text-sm text-[#78838d]">Loading tenders...</p> : tenders.length ? tenders.slice(0, 6).map((tender) => (
                  <article key={tender.id} className="group flex items-center gap-4 px-5 py-4 transition hover:bg-white/[0.025] sm:px-6">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#4cc4ea]/10 text-[#8fdcf5]"><FileText size={19} /></span>
                    <div className="min-w-0 flex-1"><h3 className="truncate text-sm font-medium">{tender.title}</h3><p className="mt-1 text-xs text-[#78838d]">{tender.requirements} requirements · {tender.questions} questions</p></div>
                    <span className="rounded-full border border-white/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-[#a9b3bc]">{titleCase(tender.stage)}</span>
                  </article>
                )) : (
                  <div className="px-6 py-12 text-center"><FileText className="mx-auto text-[#4d5861]" size={34} strokeWidth={1.4} /><h3 className="mt-4 font-medium">No tenders yet</h3><p className="mx-auto mt-2 max-w-sm text-sm text-[#78838d]">Create a tender workspace, then add source documents through the secured document flow.</p><button onClick={() => setComposer("tender")} className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-[#8fdcf5]">Create your first tender <ArrowRight size={16} /></button></div>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <section id="evidence" className="scroll-mt-24 rounded-[18px] border border-white/10 bg-[#0f1216] p-6">
                <div className="flex items-start justify-between gap-4"><div><h2 className="text-lg font-semibold">Evidence library</h2><p className="mt-1 text-sm text-[#78838d]">Only approved evidence can support factual claims.</p></div><Library className="text-[#8fdcf5]" size={22} /></div>
                <div className="mt-6 flex items-end justify-between"><div><p className="text-3xl font-semibold tabular-nums">{loading ? "–" : evidence.length}</p><p className="mt-1 text-xs text-[#78838d]">{totals.approvedEvidence} approved</p></div><button onClick={() => setComposer("evidence")} className="inline-flex h-10 items-center gap-2 rounded-[10px] border border-white/15 bg-white/[0.035] px-3 text-sm font-medium hover:border-[#4cc4ea]/45 hover:bg-[#4cc4ea]/10"><Plus size={16} /> Add evidence</button></div>
              </section>

              <section id="assurance" className="scroll-mt-24 rounded-[18px] border border-white/10 bg-gradient-to-b from-[#101820] to-[#0f1216] p-6">
                <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl border border-[#4cc4ea]/25 bg-[#4cc4ea]/10 text-[#8fdcf5]"><ShieldCheck size={20} /></span><div><h2 className="font-semibold">Assurance controls</h2><p className="text-xs text-[#78838d]">Enforced before export</p></div></div>
                <ul className="mt-6 space-y-3 text-sm text-[#a9b3bc]">
                  {["Verbatim requirement checks", "Evidence-linked factual claims", "Named human approval", "Revision hash chain"].map((item) => <li key={item} className="flex items-center gap-3"><CheckCircle2 size={16} className="shrink-0 text-[#6cc59a]" />{item}</li>)}
                </ul>
                <div className="mt-6 flex items-center gap-2 border-t border-white/10 pt-5 text-xs text-[#78838d]"><Sparkles size={15} className="text-[#8fdcf5]" /> AI provider: {user ? titleCase(user.ai_provider) : "Loading"}</div>
              </section>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
