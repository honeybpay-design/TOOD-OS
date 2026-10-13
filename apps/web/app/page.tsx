"use client";

import Link from "next/link";
import { useState } from "react";

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
              AI-assisted tender writing for UK public sector
            </p>
            <h1
              className="hero-headline text-[#1C1917] max-w-[580px] mb-6 leading-[1.1]"
              style={{
                fontFamily: 'var(--font-dm-serif)',
                fontSize: '56px',
              }}
            >
              Tender writing that holds up to scrutiny.
            </h1>
            <p
              className="text-[17px] text-[#6B6560] max-w-[520px] leading-relaxed mb-8"
              style={{ fontFamily: 'var(--font-inter)' }}
            >
              Extract requirements verbatim, draft grounded answers, and export only when every response is approved.
            </p>
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

          {/* Right column — 42% — Tender requirement card mockup */}
          <div className="lg:w-[42%] w-full">
            <div
              className="bg-white border border-[#D4CFC8] rounded-lg p-6 shadow-sm"
              aria-label="Tender requirement card example"
              aria-hidden="true"
            >
              <p
                className="text-[13px] text-[#6B6560] mb-3"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                Requirement 3.2
              </p>

              {/* Highlighted clause */}
              <div className="bg-[#00C2A8]/15 border-l-2 border-[#00C2A8] px-3 py-2 rounded-r mb-3">
                <p
                  className="text-[14px] text-[#1C1917] leading-relaxed"
                  style={{ fontFamily: 'var(--font-inter)' }}
                >
                  The supplier must demonstrate a minimum of three years&rsquo; experience delivering similar contracts to public sector bodies.
                </p>
              </div>

              {/* Badge */}
              <div className="flex items-center gap-3 mb-4">
                <span
                  className="inline-flex items-center text-[#00C2A8] bg-[#00C2A8]/10 rounded-full px-3 py-1 text-xs font-medium"
                  style={{ fontFamily: 'var(--font-inter)' }}
                >
                  Requirement extracted
                </span>
              </div>

              {/* Word count */}
              <p
                className="text-[13px] text-[#6B6560] mb-3"
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                Word count: 247 / 500
              </p>

              {/* Draft answer placeholder */}
              <textarea
                className="w-full border border-[#D4CFC8] rounded px-3 py-2 text-[13px] text-[#6B6560] bg-[#F8F6F1] resize-none focus:outline-none"
                rows={3}
                placeholder="Draft answer…"
                readOnly
                aria-label="Draft answer field"
                style={{ fontFamily: 'var(--font-inter)' }}
              />
            </div>
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
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <Pricing />
        <Testimonials />
        <CTASection />
      </main>
      <Footer />
    </>
  );
}
