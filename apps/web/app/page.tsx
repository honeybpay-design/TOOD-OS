"use client";

import Link from "next/link";
import { useState } from "react";

// ── Navbar ──────────────────────────────────────────────────────────────────
function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <nav className="fixed top-0 inset-x-0 z-50 bg-[#0F172A]/95 backdrop-blur border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <span className="text-white text-xl font-bold tracking-tight">
            TOOD
          </span>
          <div className="hidden md:flex items-center gap-8">
            {["Features", "Pricing", "About"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-slate-300 hover:text-white text-sm font-medium transition-colors"
              >
                {item}
              </a>
            ))}
          </div>
          <div className="hidden md:flex items-center gap-3">
            <Link
              href="/login"
              className="text-slate-300 hover:text-white text-sm font-medium transition-colors px-3 py-1.5"
            >
              Sign in
            </Link>
            <Link
              href="/api/billing/checkout?plan=professional"
              className="bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              Start free trial
            </Link>
          </div>
          <button
            className="md:hidden text-slate-300 hover:text-white p-2"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d={open ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
            </svg>
          </button>
        </div>
        {open && (
          <div className="md:hidden py-3 border-t border-white/10 flex flex-col gap-3">
            {["Features", "Pricing", "About"].map((item) => (
              <a key={item} href={`#${item.toLowerCase()}`}
                className="text-slate-300 hover:text-white text-sm font-medium py-1"
                onClick={() => setOpen(false)}>
                {item}
              </a>
            ))}
            <Link href="/login" className="text-slate-300 hover:text-white text-sm font-medium py-1">Sign in</Link>
            <Link href="/api/billing/checkout?plan=professional"
              className="bg-[#3B82F6] text-white text-sm font-semibold px-4 py-2 rounded-lg text-center">
              Start free trial
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}

// ── Hero ─────────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section className="bg-[#0F172A] pt-32 pb-24 px-4" id="hero">
      <div className="max-w-7xl mx-auto">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 bg-[#3B82F6]/10 border border-[#3B82F6]/30 rounded-full px-4 py-1.5 mb-8">
            <span className="w-2 h-2 rounded-full bg-[#3B82F6] animate-pulse" />
            <span className="text-[#93C5FD] text-sm font-medium">Trusted by UK Public Sector</span>
          </div>
          <h1 className="text-5xl sm:text-6xl font-extrabold text-white leading-tight mb-6 animate-slide-up">
            Win More Tenders.<br />
            <span className="text-[#3B82F6]">Write Better Bids.</span>
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mb-10 leading-relaxed">
            TOOD-OS automates requirement extraction, draft generation, and compliance checking —
            so your team focuses on strategy, not paperwork.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              href="/api/billing/checkout?plan=professional"
              className="inline-flex items-center justify-center bg-[#3B82F6] hover:bg-[#2563EB] text-white font-semibold px-8 py-3.5 rounded-xl text-base transition-all hover:shadow-lg hover:shadow-blue-500/25"
            >
              Start free trial
            </Link>
            <button
              className="inline-flex items-center justify-center gap-2 border border-white/20 hover:border-white/40 text-white font-semibold px-8 py-3.5 rounded-xl text-base transition-colors"
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
              Watch demo
            </button>
          </div>
        </div>
        {/* Abstract dashboard wireframe SVG */}
        <div className="mt-16 relative">
          <div className="bg-[#1E293B] rounded-2xl border border-white/10 overflow-hidden shadow-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <div className="ml-4 text-slate-500 text-xs font-mono">tood.uk/dashboard</div>
            </div>
            <div className="grid grid-cols-3 gap-4 mb-6">
              {[{ "label": "Active Tenders", "val": "12" }, { "label": "Requirements Extracted", "val": "847" }, { "label": "Win Rate", "val": "94%" }].map((c) => (
                <div key={c.label} className="bg-[#0F172A] rounded-xl p-4">
                  <div className="text-slate-400 text-xs mb-1">{c.label}</div>
                  <div className="text-white text-2xl font-bold">{c.val}</div>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              {[85, 60, 40, 90, 55].map((w, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-32 text-slate-500 text-xs truncate">Requirement {i + 1}</div>
                  <div className="flex-1 bg-[#0F172A] rounded-full h-2">
                    <div className="bg-[#3B82F6] h-2 rounded-full transition-all" style={{ width: `${w}%` }} />
                  </div>
                  <div className="text-slate-400 text-xs w-8">{w}%</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Stats Bar ────────────────────────────────────────────────────────────────
function StatsBar() {
  const stats = [
    { value: "£2.3B+", label: "Tenders processed" },
    { value: "340+", label: "Organisations" },
    { value: "94%", label: "Win rate improvement" },
    { value: "ISO 27001", label: "Compliant" },
  ];
  return (
    <section className="bg-[#1E293B] border-y border-white/10 py-8 px-4">
      <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
        {stats.map((s) => (
          <div key={s.label}>
            <div className="text-2xl font-extrabold text-white">{s.value}</div>
            <div className="text-slate-400 text-sm mt-1">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Features ─────────────────────────────────────────────────────────────────
function Features() {
  const features = [
    {
      icon: "🔍",
      title: "Requirement Extraction",
      desc: "Auto-extract every scored question with verbatim precision. Zero manual copy-paste.",
    },
    {
      icon: "✍️",
      title: "AI-Assisted Drafting",
      desc: "Gemini-powered responses grounded in your approved evidence library.",
    },
    {
      icon: "🔒",
      title: "Provenance & Compliance",
      desc: "Hash-chained audit trail, forced RLS, gated export — built for public sector scrutiny.",
    },
  ];
  return (
    <section id="features" className="bg-white py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-extrabold text-[#0F172A] mb-4">Built for the way bids actually work</h2>
          <p className="text-slate-500 text-lg max-w-2xl mx-auto">
            Every feature is designed around the reality of public sector procurement — not generic AI demos.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {features.map((f) => (
            <div key={f.title} className="bg-slate-50 rounded-2xl p-8 border border-slate-100 hover:border-[#3B82F6]/40 hover:shadow-lg transition-all">
              <div className="text-4xl mb-4">{f.icon}</div>
              <h3 className="text-xl font-bold text-[#0F172A] mb-3">{f.title}</h3>
              <p className="text-slate-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── How it Works ──────────────────────────────────────────────────────────────
function HowItWorks() {
  const steps = [
    { n: "01", title: "Upload Tender", desc: "Upload PDF or DOCX tender documents. TOOD parses every page." },
    { n: "02", title: "Extract Requirements", desc: "AI identifies every scored question, weighting, and word limit automatically." },
    { n: "03", title: "Draft & Export", desc: "Generate compliant drafts, approve them, and export a gated submission pack." },
  ];
  return (
    <section className="bg-slate-50 py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-extrabold text-[#0F172A] mb-4">How it works</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((s) => (
            <div key={s.n} className="relative">
              <div className="text-6xl font-black text-[#3B82F6]/15 mb-4">{s.n}</div>
              <h3 className="text-xl font-bold text-[#0F172A] mb-3">{s.title}</h3>
              <p className="text-slate-500 leading-relaxed">{s.desc}</p>
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
      period: "/month",
      desc: "For small teams getting started with bid automation.",
      features: ["3 active tenders", "2 user seats", "Template AI drafting", "Requirement extraction", "Audit trail"],
      cta: "Start free trial",
      href: "/api/billing/checkout?plan=starter",
      highlighted: false,
    },
    {
      name: "Professional",
      price: "£299",
      period: "/month",
      desc: "For established bid teams winning complex contracts.",
      features: ["20 active tenders", "10 user seats", "Gemini AI drafting", "Advanced requirement extraction", "Priority support", "Compliance reports"],
      cta: "Start free trial",
      href: "/api/billing/checkout?plan=professional",
      highlighted: true,
    },
    {
      name: "Enterprise",
      price: "£799",
      period: "/month",
      desc: "For large organisations with enterprise compliance needs.",
      features: ["Unlimited tenders", "Unlimited users", "Gemini AI drafting", "SSO / SAML", "Custom data residency", "Dedicated SLA", "On-premise option"],
      cta: "Contact sales",
      href: "/api/billing/checkout?plan=enterprise",
      highlighted: false,
    },
  ];
  return (
    <section id="pricing" className="bg-white py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-extrabold text-[#0F172A] mb-4">Simple, transparent pricing</h2>
          <p className="text-slate-500 text-lg">No hidden fees. Cancel any time. VAT not included.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {plans.map((p) => (
            <div
              key={p.name}
              className={`rounded-2xl p-8 border flex flex-col ${p.highlighted
                ? "bg-[#0F172A] border-[#3B82F6] shadow-2xl shadow-blue-500/20 relative"
                : "bg-white border-slate-200"
                }`}
            >
              {p.highlighted && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[#3B82F6] text-white text-xs font-bold px-4 py-1.5 rounded-full">
                  Most Popular
                </div>
              )}
              <div className={`text-sm font-semibold mb-2 ${p.highlighted ? "text-[#93C5FD]" : "text-[#3B82F6]"}`}>
                {p.name}
              </div>
              <div className="flex items-end gap-1 mb-2">
                <span className={`text-5xl font-extrabold ${p.highlighted ? "text-white" : "text-[#0F172A]"}`}>
                  {p.price}
                </span>
                <span className={`text-sm mb-2 ${p.highlighted ? "text-slate-400" : "text-slate-500"}`}>{p.period}</span>
              </div>
              <p className={`text-sm mb-6 ${p.highlighted ? "text-slate-400" : "text-slate-500"}`}>{p.desc}</p>
              <ul className="space-y-3 mb-8 flex-1">
                {p.features.map((f) => (
                  <li key={f} className="flex items-center gap-3">
                    <svg className="w-5 h-5 flex-shrink-0 text-[#3B82F6]" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className={`text-sm ${p.highlighted ? "text-slate-300" : "text-slate-600"}`}>{f}</span>
                  </li>
                ))}
              </ul>
              <a
                href={p.href}
                className={`block text-center font-semibold px-6 py-3 rounded-xl text-sm transition-all ${p.highlighted
                  ? "bg-[#3B82F6] hover:bg-[#2563EB] text-white hover:shadow-lg hover:shadow-blue-500/30"
                  : "border border-[#3B82F6] text-[#3B82F6] hover:bg-[#3B82F6] hover:text-white"
                  }`}
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
    <section className="bg-slate-50 py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-extrabold text-[#0F172A] mb-4">What our customers say</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((t) => (
            <div key={t.name} className="bg-white rounded-2xl p-8 border border-slate-100 shadow-sm">
              <svg className="w-8 h-8 text-[#3B82F6] mb-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" />
              </svg>
              <p className="text-slate-600 leading-relaxed mb-6 italic">&ldquo;{t.quote}&rdquo;</p>
              <div>
                <div className="font-semibold text-[#0F172A]">{t.name}</div>
                <div className="text-slate-500 text-sm">{t.role}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── CTA Banner ────────────────────────────────────────────────────────────────
function CTABanner() {
  return (
    <section className="bg-[#0F172A] py-24 px-4">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-4xl font-extrabold text-white mb-6">
          Ready to win your next tender?
        </h2>
        <p className="text-slate-400 text-lg mb-10">
          Join 340+ organisations using TOOD-OS to write better bids, faster.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/api/billing/checkout?plan=professional"
            className="inline-flex items-center justify-center bg-[#3B82F6] hover:bg-[#2563EB] text-white font-semibold px-8 py-4 rounded-xl text-base transition-all hover:shadow-lg hover:shadow-blue-500/30"
          >
            Start free trial — 14 days free
          </Link>
          <a
            href="mailto:hello@tood.uk"
            className="inline-flex items-center justify-center border border-white/20 hover:border-white/40 text-white font-semibold px-8 py-4 rounded-xl text-base transition-colors"
          >
            Talk to sales
          </a>
        </div>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer id="about" className="bg-[#0F172A] border-t border-white/10 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between gap-8 mb-8">
          <div>
            <span className="text-white text-xl font-bold">TOOD</span>
            <p className="text-slate-500 text-sm mt-2 max-w-xs">
              AI-powered tender management for UK public sector organisations.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-8 text-sm">
            <div>
              <div className="text-white font-semibold mb-3">Product</div>
              {["Features", "Pricing", "Security", "Compliance"].map((l) => (
                <a key={l} href="#" className="block text-slate-400 hover:text-white py-1 transition-colors">{l}</a>
              ))}
            </div>
            <div>
              <div className="text-white font-semibold mb-3">Company</div>
              {["About", "Blog", "Careers", "Contact"].map((l) => (
                <a key={l} href="#" className="block text-slate-400 hover:text-white py-1 transition-colors">{l}</a>
              ))}
            </div>
          </div>
        </div>
        <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-slate-500 text-sm">
            &copy; 2026 Honey B2024 Ltd. Registered in England. All rights reserved.
          </p>
          <div className="flex gap-6">
            {["Privacy Policy", "Terms of Service", "Cookie Policy"].map((l) => (
              <a key={l} href="#" className="text-slate-500 hover:text-white text-sm transition-colors">{l}</a>
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
        <StatsBar />
        <Features />
        <HowItWorks />
        <Pricing />
        <Testimonials />
        <CTABanner />
      </main>
      <Footer />
    </>
  );
}
