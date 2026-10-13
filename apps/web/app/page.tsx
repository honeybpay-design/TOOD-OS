"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

// ── Workflow Demo Animation ───────────────────────────────────────────────────

const DEMO_STEPS = [
  {
    id: 0,
    tab: "Requirement",
    icon: "📄",
    title: "Requirement extracted verbatim",
  },
  {
    id: 1,
    tab: "AI Draft",
    icon: "✍️",
    title: "AI drafts from approved evidence only",
  },
  {
    id: 2,
    tab: "Verify",
    icon: "🔍",
    title: "Every claim verified against evidence",
  },
  {
    id: 3,
    tab: "Audit",
    icon: "🔗",
    title: "Audit trail — every change recorded",
  },
];

const DURATIONS = [4500, 6000, 5000, 4500];

function TypingText({ text, speed = 20 }: { text: string; speed?: number }) {
  const prefersReduced =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;
  const [displayed, setDisplayed] = useState(prefersReduced ? text : "");

  useEffect(() => {
    if (prefersReduced) {
      setDisplayed(text);
      return;
    }
    setDisplayed("");
    let i = 0;
    const id = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed, prefersReduced]);

  return (
    <span>
      {displayed}
      {displayed.length < text.length && (
        <span className="animate-pulse inline-block w-0.5 h-4 bg-[#1B4FD8] align-middle ml-0.5" />
      )}
    </span>
  );
}

function WindowChrome() {
  return (
    <div className="flex items-center gap-2 px-4 py-2.5 bg-[#EFEDE8] border-b border-[#D4CFC8] rounded-t-lg">
      <span className="w-3 h-3 rounded-full bg-[#FF5F57]" />
      <span className="w-3 h-3 rounded-full bg-[#FEBC2E]" />
      <span className="w-3 h-3 rounded-full bg-[#28C840]" />
      <div className="flex-1 mx-3 px-3 py-0.5 bg-white rounded text-xs text-[#6B6560] font-mono border border-[#D4CFC8] text-center">
        tood.uk/dashboard
      </div>
    </div>
  );
}

function StepContent({ step }: { step: number }) {
  switch (step) {
    case 0:
      return (
        <div key={0} className="p-5 space-y-4">
          <div className="text-xs font-medium text-[#6B6560] uppercase tracking-wide">
            Source document
          </div>
          <div className="bg-[#EFEDE8] rounded-lg p-4 text-sm text-[#1C1917] leading-relaxed border border-[#D4CFC8]">
            <span>The supplier must </span>
            <span className="bg-[#00C2A8]/20 text-[#1C1917] px-0.5 rounded highlight-pulse">
              demonstrate a minimum of three years&rsquo; experience
            </span>
            <span>
              {" "}
              in delivering public sector contracts of similar scope and
              complexity.
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs bg-[#F8F6F1] border border-[#D4CFC8] rounded px-2 py-1 text-[#6B6560]">
              §3.2 · page 7 · 500 word limit
            </span>
          </div>
          <div className="flex items-center gap-2 bg-[#00C2A8]/10 border border-[#00C2A8]/30 rounded-lg px-3 py-2">
            <span className="text-[#00C2A8] text-sm font-medium">
              ✓ Verbatim match confirmed
            </span>
            <span className="ml-auto text-xs text-[#6B6560]">
              Extracted from §3.2, page 7
            </span>
          </div>
        </div>
      );

    case 1: {
      const draftText =
        "Our organisation has delivered 14 public sector contracts [EV: case-study-1.pdf] across infrastructure and digital transformation, meeting all ISO 9001 quality standards [EV: iso-cert.pdf] renewed annually since 2019. References available from Lancashire CC on request.";
      return (
        <div key={1} className="p-5 space-y-4">
          <div className="text-xs font-medium text-[#6B6560] uppercase tracking-wide">
            Generating draft response
          </div>
          <div className="bg-[#F8F6F1] rounded-lg p-4 text-sm text-[#1C1917] leading-relaxed border border-[#D4CFC8] min-h-[80px]">
            <TypingText text={draftText} speed={18} />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-[#6B6560]">
              <span className="w-2 h-2 rounded-full bg-[#00C2A8]"></span>
              2 evidence items used
            </div>
            <span className="text-xs text-[#6B6560] italic">
              No hallucinated facts
            </span>
          </div>
        </div>
      );
    }

    case 2: {
      const claims = [
        {
          text: '"14 public sector contracts"',
          source: "case-study-1.pdf",
          ok: true,
        },
        { text: '"ISO 9001, renewed 2019"', source: "iso-cert.pdf", ok: true },
        { text: '"£2M contract value"', source: null, ok: false },
      ];
      return (
        <div key={2} className="p-5 space-y-3">
          <div className="text-xs font-medium text-[#6B6560] uppercase tracking-wide">
            Claim verification
          </div>
          <div className="space-y-2">
            {claims.map((c, i) => (
              <div
                key={i}
                className={`flex items-start gap-3 rounded-lg px-3 py-2.5 border text-sm ${c.ok
                  ? "bg-[#F0FDF4] border-green-200 text-[#1C1917]"
                  : "bg-red-50 border-red-200 text-[#1C1917]"
                  }`}
              >
                <span
                  className={c.ok ? "text-green-600 mt-0.5" : "text-red-500 mt-0.5"}
                >
                  {c.ok ? "✓" : "✗"}
                </span>
                <div className="flex-1">
                  <span className="font-medium">{c.text}</span>
                  {c.ok ? (
                    <span className="text-[#6B6560] text-xs ml-2">
                      → matched in {c.source}
                    </span>
                  ) : (
                    <span className="text-red-500 text-xs ml-2">
                      → NOT FOUND in evidence
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="text-xs bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-red-600">
            ⚠ Action required: Acknowledge or remove this claim before export
          </div>
        </div>
      );
    }

    case 3: {
      const auditLog = [
        {
          time: "14:32",
          user: "Sarah M.",
          action: "Draft generated",
          detail: "Gemini 2.5 Pro",
        },
        {
          time: "14:45",
          user: "James O.",
          action: "Edited",
          detail: "word count 312→287",
        },
        { time: "15:01", user: "James O.", action: "Approved", detail: "" },
        {
          time: "15:02",
          user: "System",
          action: "Hash recorded",
          detail: "a3f9c2e1...",
        },
      ];
      return (
        <div key={3} className="p-5 space-y-3">
          <div className="text-xs font-medium text-[#6B6560] uppercase tracking-wide">
            Audit log · 2026-10-13
          </div>
          <div className="space-y-1 font-mono text-xs">
            {auditLog.map((e, i) => (
              <div
                key={i}
                className="flex items-center gap-3 py-1.5 border-b border-[#D4CFC8] last:border-0"
              >
                <span className="text-[#6B6560] w-10">{e.time}</span>
                <span className="text-[#1B4FD8] w-16 shrink-0">{e.user}</span>
                <span className="text-[#1C1917] flex-1">
                  {e.action}
                  {e.detail ? ` — ${e.detail}` : ""}
                </span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 bg-[#EFEDE8] rounded-lg px-3 py-2">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6B6560"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            <span className="text-xs text-[#6B6560]">
              Tamper-evident — cannot be altered retroactively
            </span>
          </div>
        </div>
      );
    }

    default:
      return null;
  }
}

function WorkflowDemo() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setStep((s) => (s + 1) % 4), DURATIONS[step]);
    return () => clearTimeout(t);
  }, [step]);

  return (
    <div className="w-full border border-[#D4CFC8] rounded-lg shadow-sm overflow-hidden bg-white">
      <WindowChrome />
      {/* Step tabs */}
      <div className="flex border-b border-[#D4CFC8] bg-[#F8F6F1]">
        {DEMO_STEPS.map((s) => (
          <button
            key={s.id}
            onClick={() => setStep(s.id)}
            className={`flex-1 px-2 py-2.5 text-xs font-medium transition-colors ${step === s.id
              ? "bg-white border-b-2 border-[#1B4FD8] text-[#1B4FD8]"
              : "text-[#6B6560] hover:text-[#1C1917]"
              }`}
            aria-pressed={step === s.id}
          >
            <span className="mr-1">{s.icon}</span>
            <span className="hidden sm:inline">{s.tab}</span>
          </button>
        ))}
      </div>
      {/* Step title */}
      <div className="px-5 pt-4 pb-1">
        <h3
          className="text-sm font-semibold text-[#1C1917]"
          style={{ fontFamily: "var(--font-dm-serif)" }}
        >
          {DEMO_STEPS[step].title}
        </h3>
      </div>
      {/* Step content */}
      <div aria-live="polite" aria-atomic="true">
        <StepContent step={step} />
      </div>
      {/* Progress dots */}
      <div className="flex justify-center gap-2 py-3 bg-[#F8F6F1] border-t border-[#D4CFC8]">
        {DEMO_STEPS.map((s) => (
          <button
            key={s.id}
            onClick={() => setStep(s.id)}
            aria-label={`Go to step ${s.id + 1}: ${s.tab}`}
            className={`w-2 h-2 rounded-full transition-colors ${step === s.id ? "bg-[#1B4FD8]" : "bg-[#D4CFC8]"
              }`}
          />
        ))}
      </div>
    </div>
  );
}

// ── PPN Compliance ──────────────────────────────────────────────────────────
function PPNCompliance() {
  const items = [
    {
      ref: "Procurement Act 2023",
      title: "New UK public contracts framework",
      body: "Replaces PCR 2015. TOOD helps suppliers structure responses to meet the updated evaluation and transparency requirements.",
    },
    {
      ref: "PPN 01/17 — Social Value",
      title: "Evidence-backed social value responses",
      body: "Policy note requiring social value to be weighted in procurement. TOOD's evidence library ensures claims are sourced and verifiable.",
    },
    {
      ref: "PPN 02/24 — AI in Procurement",
      title: "Human approval required, audit trail mandatory",
      body: "Requires AI use to be transparent, human-supervised, and auditable. TOOD enforces named approval and hash-chained audit logs on every submission.",
    },
  ];
  return (
    <section className="py-20 px-4 bg-[#1C1917]" id="compliance">
      <div className="max-w-7xl mx-auto">
        <p className="text-[#00C2A8] text-[13px] font-semibold mb-4" style={{ fontFamily: "var(--font-inter)" }}>
          Built to comply with
        </p>
        <h2 className="text-white mb-12" style={{ fontFamily: "var(--font-dm-serif)", fontSize: "40px" }}>
          UK procurement regulations, by design.
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {items.map((item) => (
            <div key={item.ref} className="border-t border-white/10 pt-6">
              <p className="text-[#00C2A8] text-[12px] font-semibold mb-2" style={{ fontFamily: "var(--font-inter)" }}>
                {item.ref}
              </p>
              <h3 className="text-white text-[17px] font-semibold mb-3" style={{ fontFamily: "var(--font-inter)" }}>
                {item.title}
              </h3>
              <p className="text-white/60 text-[14px] leading-relaxed" style={{ fontFamily: "var(--font-inter)" }}>
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Compliance Strip ─────────────────────────────────────────────────────────
function ComplianceStrip() {
  const items = [
    { label: "AI Top-tier Agent", highlight: true },
    { label: "Procurement Act 2023" },
    { label: "PPN 01/17 Social Value" },
    { label: "PPN 02/24 AI in Procurement" },
    { label: "UK Public Sector" },
  ];
  return (
    <div className="bg-[#1C1917] px-4 py-2 flex items-center gap-3 flex-wrap" role="banner" aria-label="Compliance certifications">
      {items.map((item, i) => (
        <span key={item.label} className="flex items-center gap-3">
          {item.highlight ? (
            <span className="inline-flex items-center gap-1.5 border border-[#00C2A8] text-[#00C2A8] rounded px-2 py-0.5 text-[11px] font-semibold" style={{ fontFamily: "var(--font-inter)" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-[#00C2A8] animate-pulse" />
              {item.label}
            </span>
          ) : (
            <span className="text-[11px] text-white/60" style={{ fontFamily: "var(--font-inter)" }}>{item.label}</span>
          )}
          {i < items.length - 1 && <span className="text-white/20 text-[11px]">·</span>}
        </span>
      ))}
    </div>
  );
}

// ── Navbar ──────────────────────────────────────────────────────────────────
function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <nav
      className="fixed top-0 inset-x-0 z-50 bg-[#F8F6F1] border-b border-[#D4CFC8]"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <a href="/" className="flex items-center gap-2" aria-label="TOOD home">
            <img src="/tood logo png.png" alt="TOOD" className="h-8 w-auto" />
            <span
              className="text-[#1C1917] font-bold text-base"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              TOOD
            </span>
          </a>

          {/* Desktop nav links */}
          <div className="hidden md:flex items-center gap-8">
            {["Features", "Pricing", "About"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-[#6B6560] text-sm hover:text-[#1C1917] transition-colors"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {item}
              </a>
            ))}
          </div>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="/login"
              className="text-[#1B4FD8] text-sm font-medium hover:text-[#1541B0] transition-colors"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              Sign in
            </Link>
            <Link
              href="/api/billing/checkout?plan=professional"
              className="bg-[#1B4FD8] hover:bg-[#1541B0] text-[#F8F6F1] text-sm font-semibold px-4 py-2 rounded transition-colors"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              Start free trial
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden text-[#6B6560] hover:text-[#1C1917] p-2"
            onClick={() => setOpen(!open)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={open ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"}
              />
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden py-3 border-t border-[#D4CFC8] flex flex-col gap-3">
            {["Features", "Pricing", "About"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-[#6B6560] hover:text-[#1C1917] text-sm py-1 transition-colors"
                onClick={() => setOpen(false)}
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {item}
              </a>
            ))}
            <Link
              href="/login"
              className="text-[#1B4FD8] text-sm py-1"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              Sign in
            </Link>
            <Link
              href="/api/billing/checkout?plan=professional"
              className="bg-[#1B4FD8] text-[#F8F6F1] text-sm font-semibold px-4 py-2 rounded text-center"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              Start free trial
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section className="pt-32 pb-20 px-4 bg-[#F8F6F1]" id="hero">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row gap-12 lg:gap-16 items-start">
          {/* Left column — 58% */}
          <div className="lg:w-[58%]">
            <p
              className="text-[15px] text-[#6B6560] mb-4"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              Trusted Operations &amp; Organised Documents
            </p>
            <h1
              className="hero-headline text-[#1C1917] max-w-[580px] mb-6 leading-[1.1]"
              style={{
                fontFamily: 'var(--font-dm-serif)',
                fontSize: '56px',
              }}
            >
              Tender writing built for the Procurement Act 2023.
            </h1>
            <p
              className="text-[17px] text-[#6B6560] max-w-[520px] leading-relaxed mb-6"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              Extract requirements verbatim, draft grounded answers, and export only when every response is approved — compliant with PPN 02/24 on AI use in procurement.
            </p>
            {/* Compliance tags */}
            <div className="flex flex-wrap gap-2 mb-8">
              {[
                { label: "Procurement Act 2023", active: true },
                { label: "PPN 01/17 Social Value", active: true },
                { label: "PPN 02/24 AI Transparency", active: true },
                { label: "ISO 27001 aligned", active: false },
              ].map((tag) => (
                <span
                  key={tag.label}
                  className={`border rounded px-2.5 py-1 text-[11px] font-semibold ${tag.active
                    ? "border-[#1B4FD8] text-[#1B4FD8] bg-[#1B4FD8]/5"
                    : "border-[#D4CFC8] text-[#6B6560] bg-[#EFEDE8]"
                    }`}
                  style={{ fontFamily: "var(--font-inter)" }}
                >
                  {tag.label}
                </span>
              ))}
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <Link
                href="/api/billing/checkout?plan=professional"
                className="inline-flex items-center justify-center bg-[#1B4FD8] hover:bg-[#1541B0] text-[#F8F6F1] px-6 py-3 rounded font-semibold text-base transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1B4FD8]"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                Start free trial
              </Link>
              <button
                onClick={() =>
                  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
                }
                className="inline-flex items-center justify-center border border-[#1C1917] text-[#1C1917] px-6 py-3 rounded font-semibold text-base hover:bg-[#EFEDE8] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1B4FD8]"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                See how it works
              </button>
            </div>
          </div>

          {/* Right column — 42% — Animated workflow demo */}
          <div className="lg:w-[42%] w-full">
            <WorkflowDemo />
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Features ──────────────────────────────────────────────────────────────────
function Features() {
  const features = [
    {
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12C3.75 7.5 7.5 4.5 12 4.5s8.25 3 9.75 7.5c-1.5 4.5-5.25 7.5-9.75 7.5S3.75 16.5 2.25 12z" />
          <circle cx="12" cy="12" r="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ),
      title: "Requirements extracted verbatim",
      body: "Pulls exact wording from tender documents, nothing paraphrased. Quoted page and clause references included.",
    },
    {
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      ),
      title: "Every draft grounded in evidence",
      body: "Gemini writes only from your approved evidence library. No hallucinated capabilities, no invented past contracts.",
    },
    {
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.75}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
        </svg>
      ),
      title: "Export only when every answer is approved",
      body: "The gate exists for compliance, not as an upsell. Unapproved responses cannot be included in an export.",
    },
  ];

  return (
    <section id="features" className="py-20 px-4 bg-[#F8F6F1]">
      <div className="max-w-7xl mx-auto">
        <h2
          className="text-[#1C1917] mb-14"
          style={{ fontFamily: 'var(--font-dm-serif)', fontSize: '40px' }}
        >
          What makes it different
        </h2>
        <div className="flex flex-col gap-12">
          {features.map((f) => (
            <div key={f.title} className="flex gap-6 items-start max-w-2xl">
              <div className="text-[#00C2A8] flex-shrink-0 mt-0.5">{f.icon}</div>
              <div>
                <h3
                  className="text-[21px] font-semibold text-[#1C1917] mb-2"
                  style={{ fontFamily: 'var(--font-inter)' }}
                >
                  {f.title}
                </h3>
                <p
                  className="text-[15px] text-[#6B6560] leading-relaxed"
                  style={{ fontFamily: 'var(--font-inter)' }}
                >
                  {f.body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── How it works ──────────────────────────────────────────────────────────────
function HowItWorks() {
  const steps = [
    {
      n: "1",
      title: "Upload the tender document",
      body: "Upload a PDF or DOCX. TOOD reads every page and preserves the original structure.",
    },
    {
      n: "2",
      title: "Review extracted requirements",
      body: "Check the requirements TOOD found. Add, remove, or reorder before any drafting begins.",
    },
    {
      n: "3",
      title: "Draft, approve, and export",
      body: "Write or generate draft answers, approve each one, then export a clean submission pack.",
    },
  ];

  return (
    <section className="py-20 px-4 bg-[#EFEDE8]">
      <div className="max-w-7xl mx-auto">
        <h2
          className="text-[#1C1917] mb-14"
          style={{ fontFamily: 'var(--font-dm-serif)', fontSize: '40px' }}
        >
          How it works
        </h2>
        <div className="grid md:grid-cols-3 gap-10">
          {steps.map((s) => (
            <div key={s.n}>
              <div
                className="leading-none text-[#D4CFC8] mb-3"
                style={{
                  fontFamily: 'var(--font-dm-serif)',
                  fontSize: '64px',
                  lineHeight: 1,
                }}
                aria-hidden="true"
              >
                {s.n}
              </div>
              <h3
                className="text-[21px] font-semibold text-[#1C1917] mb-2"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {s.title}
              </h3>
              <p
                className="text-[15px] text-[#6B6560] leading-relaxed"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Pricing ───────────────────────────────────────────────────────────────────
function Pricing() {
  const plans = [
    {
      name: "Starter",
      price: "£99",
      period: "/mo",
      features: [
        "3 active tenders",
        "2 user seats",
        "Template AI drafting",
        "Requirement extraction",
        "Audit trail",
      ],
      cta: "Start free trial",
      href: "/api/billing/checkout?plan=starter",
      highlighted: false,
    },
    {
      name: "Professional",
      price: "£299",
      period: "/mo",
      features: [
        "20 active tenders",
        "10 user seats",
        "Gemini AI drafting",
        "Advanced extraction",
        "Priority support",
        "Compliance reports",
      ],
      cta: "Start free trial",
      href: "/api/billing/checkout?plan=professional",
      highlighted: true,
    },
    {
      name: "Enterprise",
      price: "£799",
      period: "/mo",
      features: [
        "Unlimited tenders",
        "Unlimited users",
        "Gemini AI drafting",
        "SSO/SAML",
        "Custom data residency",
        "Dedicated SLA",
      ],
      cta: "Contact sales",
      href: "mailto:hello@tood.uk",
      highlighted: false,
    },
  ];

  const CheckIcon = () => (
    <svg
      className="w-4 h-4 text-[#00C2A8] flex-shrink-0 mt-0.5"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );

  return (
    <section id="pricing" className="py-20 px-4 bg-[#EFEDE8]">
      <div className="max-w-7xl mx-auto">
        <h2
          className="text-[#1C1917] mb-14"
          style={{ fontFamily: 'var(--font-dm-serif)', fontSize: '40px' }}
        >
          Simple, transparent pricing
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`flex flex-col p-8 ${p.highlighted
                ? "border-2 border-[#1B4FD8] bg-[#F8F6F1]"
                : "border border-[#D4CFC8] bg-[#F8F6F1]"
                }`}
            >
              <div
                className="text-[15px] font-semibold text-[#1C1917] mb-4"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {p.name}
              </div>
              <div className="flex items-end gap-1 mb-6">
                <span
                  className="text-[#1C1917]"
                  style={{
                    fontFamily: 'var(--font-dm-serif)',
                    fontSize: '40px',
                    lineHeight: 1,
                  }}
                >
                  {p.price}
                </span>
                <span
                  className="text-[#6B6560] text-sm mb-1"
                  style={{ fontFamily: 'var(--font-inter)' }}
                >
                  {p.period}
                </span>
              </div>
              <ul className="flex flex-col gap-3 mb-8 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <CheckIcon />
                    <span
                      className="text-[14px] text-[#1C1917]"
                      style={{ fontFamily: 'var(--font-inter)' }}
                    >
                      {f}
                    </span>
                  </li>
                ))}
              </ul>
              <a
                href={p.href}
                className={`block text-center font-semibold px-5 py-2.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1B4FD8] ${p.highlighted
                  ? "bg-[#1B4FD8] hover:bg-[#1541B0] text-[#F8F6F1]"
                  : "border border-[#1B4FD8] text-[#1B4FD8] hover:bg-[#1B4FD8] hover:text-[#F8F6F1]"
                  }`}
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {p.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Testimonials ──────────────────────────────────────────────────────────────
function Testimonials() {
  const testimonials = [
    {
      quote: "TOOD cut our bid preparation time by 60%. We can now respond to twice as many opportunities.",
      name: "Sarah Mitchell",
      role: "Head of Business Development, Nexus Consulting",
    },
    {
      quote: "The compliance audit trail alone is worth every penny. Auditors love it.",
      name: "James Okafor",
      role: "Procurement Director, Citywide Services Ltd",
    },
    {
      quote: "Finally, an AI tool that respects the verbatim requirement — no hallucinated questions.",
      name: "Priya Sharma",
      role: "Senior Bid Writer, PublicFirst Group",
    },
  ];

  return (
    <section className="py-20 px-4 bg-[#F8F6F1]">
      <div className="max-w-7xl mx-auto">
        <div className="grid md:grid-cols-3 gap-10">
          {testimonials.map((t) => (
            <div key={t.name}>
              <div
                className="leading-none text-[#D4CFC8] mb-2 select-none"
                style={{
                  fontFamily: 'var(--font-dm-serif)',
                  fontSize: '80px',
                  lineHeight: 1,
                }}
                aria-hidden="true"
              >
                &ldquo;
              </div>
              <p
                className="text-[21px] text-[#1C1917] italic leading-snug mb-4"
                style={{ fontFamily: 'var(--font-dm-serif)' }}
              >
                {t.quote}
              </p>
              <p
                className="text-[13px] text-[#6B6560]"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {t.name} &mdash; {t.role}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── CTA section ───────────────────────────────────────────────────────────────
function CTASection() {
  return (
    <section className="bg-[#1B4FD8] py-24 px-4">
      <div className="max-w-3xl mx-auto">
        <h2
          className="text-white mb-8 leading-tight"
          style={{ fontFamily: 'var(--font-dm-serif)', fontSize: '40px' }}
        >
          Start your first tender today.
        </h2>
        <Link
          href="/api/billing/checkout?plan=professional"
          className="inline-flex items-center justify-center bg-[#F8F6F1] hover:bg-[#EFEDE8] text-[#1B4FD8] font-semibold px-8 py-4 rounded text-base transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          style={{ fontFamily: 'var(--font-inter)' }}
        >
          Start your first tender
        </Link>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer id="about" className="bg-[#1C1917] py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <img
            src="/tood logo png.png"
            className="h-8 w-auto"
            style={{ filter: 'brightness(0) invert(1)' }}
            alt="TOOD"
          />
        </div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-t border-white/10 pt-8">
          <p
            className="text-white/60 text-sm"
            style={{ fontFamily: 'var(--font-inter)' }}
          >
            &copy; 2026 Honey B2024 Ltd &mdash; Trusted Operations &amp; Organised Documents
          </p>
          <div className="flex gap-6">
            {["Privacy Policy", "Terms of Service", "Contact"].map((l) => (
              <a
                key={l}
                href="#"
                className="text-white/60 hover:text-white text-sm transition-colors"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {l}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function Home() {
  return (
    <>
      <ComplianceStrip />
      <Navbar />
      <main>
        <Hero />
        <Features />
        <PPNCompliance />
        <HowItWorks />
        <Pricing />
        <Testimonials />
        <CTASection />
      </main>
      <Footer />
    </>
  );
}
