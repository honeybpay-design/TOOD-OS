'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

// ── Theme store (module-level for canvas callbacks) ─────────────────────────
const themeListeners: Array<() => void> = [];
function notifyThemeChange() {
  themeListeners.forEach((f) => f());
}

// ── Glyph Canvas ─────────────────────────────────────────────────────────────
const SRC =
  'The Supplier must hold a valid Cyber Essentials Plus certificate at the contract start date. Responses shall not exceed 750 words. The service must ensure no loss of service during core hours. Tenders must remain valid for 90 days. Social value weighting 10%. ';
const PCOL = ['#2c8bd6', '#d39a1c', '#14b07f', '#d0664a'];

interface GlyphOpts {
  rgb?: string;
  base?: number;
  band?: string;
  period?: number;
  host?: HTMLElement | null;
}

function useGlyphCanvas(
  canvasRef: React.RefObject<HTMLCanvasElement | null>,
  hostRef: React.RefObject<HTMLElement | null>,
  opts: GlyphOpts = {}
) {
  useEffect(() => {
    const canvasEl = canvasRef.current;
    if (!canvasEl) return;
    const canvas: HTMLCanvasElement = canvasEl;
    const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
    if (!ctx) return;
    const root = document.documentElement;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = 8.4, ch = 19;
    let cols = 0, rows = 0;
    interface Cell { c: string; m: number; col: string; seed: number; }
    let cells: Cell[] = [];
    let W = 0, H = 0;
    let mx = -999, my = -999;
    const t0 = performance.now();
    let visible = true;
    let raf = 0;
    let rgb = '20,22,26';
    let bandCol = '#0a7a5a';
    let base = opts.base ?? 0.075;

    function readColor() {
      const cs = getComputedStyle(root);
      rgb = opts.rgb ?? cs.getPropertyValue('--glyph').trim() ?? '20,22,26';
      bandCol = opts.band ?? cs.getPropertyValue('--color-primary').trim() ?? '#0a7a5a';
      base = opts.base ?? (root.getAttribute('data-theme') === 'dark' ? 0.12 : 0.075);
    }

    function size() {
      const r = canvas.getBoundingClientRect();
      W = r.width; H = r.height;
      canvas.width = W * dpr; canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cols = Math.ceil(W / cw); rows = Math.ceil(H / ch);
      cells = [];
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const c = SRC[(y * 37 + x) % SRC.length];
          cells.push({ c, m: 0, col: PCOL[(x * 7 + y * 13) % 4], seed: Math.random() });
        }
      }
      ctx.font = '500 12px "JetBrains Mono", ui-monospace, monospace';
      ctx.textBaseline = 'top';
    }

    function frame(now: number) {
      raf = 0;
      if (!visible) return;
      const t = (now - t0) / 1000;
      ctx.clearRect(0, 0, W, H);
      const period = opts.period ?? 7;
      const bandW = W * 0.16;
      const bx = ((t % period) / period) * (W + bandW * 2) - bandW;
      for (let i = 0; i < cells.length; i++) {
        const cell = cells[i];
        if (cell.c === ' ') continue;
        const x = (i % cols) * cw, y = Math.floor(i / cols) * ch;
        let a = base;
        const dx = x - bx;
        const inBand = dx > -bandW && dx < 0;
        if (inBand) {
          const k = 1 + dx / bandW; a += 0.32 * k;
          if (cell.seed > 0.965 && cell.m < 0.2) cell.m = 1;
        }
        if (mx > -900) {
          const ddx = x - mx, ddy = y - my;
          const dist = Math.sqrt(ddx * ddx + ddy * ddy);
          if (dist < 150) a += 0.38 * (1 - dist / 150);
        }
        if (cell.m > 0.01) {
          ctx.fillStyle = cell.col; ctx.globalAlpha = 0.18 * cell.m;
          ctx.fillRect(x - 1, y + 1, cw - 2, ch - 4);
          ctx.globalAlpha = Math.min(1, 0.55 * cell.m + a);
          ctx.fillStyle = cell.col; ctx.fillText(cell.c, x + 2, y + 3);
          cell.m *= 0.994;
        } else {
          ctx.globalAlpha = Math.min(0.85, a);
          ctx.fillStyle = inBand ? bandCol : `rgb(${rgb})`;
          ctx.fillText(cell.c, x + 2, y + 3);
        }
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(frame);
    }

    function kick() { if (!raf) raf = requestAnimationFrame(frame); }

    readColor(); size(); kick();

    const onResize = () => { size(); kick(); };
    window.addEventListener('resize', onResize);

    const themeListener = () => { readColor(); kick(); };
    themeListeners.push(themeListener);

    const host = hostRef.current ?? canvas.parentElement;
    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      mx = e.clientX - r.left; my = e.clientY - r.top;
    };
    const onLeave = () => { mx = my = -999; };
    if (host) {
      host.addEventListener('pointermove', onMove as EventListener);
      host.addEventListener('pointerleave', onLeave);
    }

    const io = new IntersectionObserver((es) => {
      visible = es[0].isIntersecting;
      if (visible) kick();
    });
    io.observe(canvas);

    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      const idx = themeListeners.indexOf(themeListener);
      if (idx > -1) themeListeners.splice(idx, 1);
      if (host) {
        host.removeEventListener('pointermove', onMove as EventListener);
        host.removeEventListener('pointerleave', onLeave);
      }
      io.disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}

// ── Skip link ────────────────────────────────────────────────────────────────
function SkipLink() {
  return <a className="skip" href="#main">Skip to content</a>;
}

// ── Announcement bar ─────────────────────────────────────────────────────────
function AnnouncementBar() {
  return (
    <div className="announce">
      <div className="wrap announce__in">
        <span className="announce__dot" aria-hidden="true" />
        <span>14-day free trial · No credit card · Sign in with Google</span>
        <a href="/login">Start free →</a>
      </div>
    </div>
  );
}

// ── Header ───────────────────────────────────────────────────────────────────
function Header() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const stored = localStorage.getItem('theme') as 'light' | 'dark' | null;
    const initial =
      stored ??
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    setTheme(initial);
    document.documentElement.setAttribute('data-theme', initial);
  }, []);

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    notifyThemeChange();
  }

  const SunIcon = (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="12" r="5" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
  const MoonIcon = (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );

  return (
    <header className={`header${isScrolled ? ' is-scrolled' : ''}`} id="top">
      <div className="wrap header__in">
        <a className="brand" href="#top" aria-label="tood.os home">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="3.5" y="3.5" width="17" height="17" rx="3.5" stroke="currentColor" strokeWidth="1.8" />
            <path d="M8 9h8M8 12.5h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="16" cy="16" r="2.2" fill="var(--color-primary)" />
          </svg>
          <span className="brand__word">tood<span>.</span>os</span>
        </a>
        <nav className="nav" aria-label="Primary">
          <a href="#live">Live demo</a>
          <a href="#inspect">Provenance</a>
          <a href="#standard">The standard</a>
          <a href="#record">AI use record</a>
          <a href="#pricing">Pricing</a>
        </nav>
        <div className="header__actions">
          <button
            className="icon-btn"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? SunIcon : MoonIcon}
          </button>
          <a className="btn btn--ghost btn--sm hide-sm" href="/login">Sign in</a>
          <a className="btn btn--primary btn--sm" href="/login">Start free trial</a>
        </div>
      </div>
    </header>
  );
}

// ── Pipeline Demo ─────────────────────────────────────────────────────────────
function PipelineDemo() {
  const pipeRef = useRef<HTMLDivElement>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const startedRef = useRef(false);

  const cycle = useCallback(() => {
    const pipe = pipeRef.current;
    if (!pipe) return;
    const cards = pipe.querySelectorAll<HTMLElement>('.pipe__card');
    const links = pipe.querySelectorAll<HTMLElement>('.pipe__link');
    const hls = pipe.querySelectorAll<HTMLElement>('.page .hl');
    const reqs = pipe.querySelectorAll<HTMLElement>('.reqs li');
    const ms = pipe.querySelectorAll<HTMLElement>('.mini .m');

    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    pipe.classList.remove('is-run', 'is-sealed');
    cards.forEach((c) => c.classList.remove('is-act'));
    links.forEach((l) => l.classList.remove('go'));
    hls.forEach((e) => e.classList.remove('on'));
    reqs.forEach((e) => e.classList.remove('on'));
    ms.forEach((e) => e.classList.remove('on'));

    void pipe.offsetWidth;

    const at = (ms_: number, f: () => void) => {
      timersRef.current.push(setTimeout(f, ms_));
    };

    at(100, () => { pipe.classList.add('is-run'); cards[0]?.classList.add('is-act'); });
    hls.forEach((e, i) => at(500 + i * 420, () => e.classList.add('on')));
    at(2500, () => { cards[0]?.classList.remove('is-act'); links[0]?.classList.add('go'); });
    at(3300, () => cards[1]?.classList.add('is-act'));
    reqs.forEach((e, i) => at(3400 + i * 380, () => e.classList.add('on')));
    at(5600, () => { cards[1]?.classList.remove('is-act'); links[1]?.classList.add('go'); });
    at(6400, () => cards[2]?.classList.add('is-act'));
    ms.forEach((e, i) => at(6500 + i * 520, () => e.classList.add('on')));
    at(8800, () => { pipe.classList.add('is-sealed'); cards[2]?.classList.remove('is-act'); });
    at(12500, cycle);
  }, []);

  useEffect(() => {
    const pipe = pipeRef.current;
    if (!pipe) return;
    const io = new IntersectionObserver(
      (es) => {
        if (es[0].isIntersecting && !startedRef.current) {
          startedRef.current = true;
          cycle();
        }
      },
      { threshold: 0.3 }
    );
    io.observe(pipe);
    return () => {
      io.disconnect();
      timersRef.current.forEach(clearTimeout);
    };
  }, [cycle]);

  return (
    <div className="wrap">
      <div
        className="pipe reveal"
        id="pipe"
        ref={pipeRef}
        aria-label="Animated overview: tender pack to verified requirements to traced draft"
      >
        <div className="pipe__card" data-step="0">
          <div className="pipe__head">
            <span className="pipe__n">01</span>Tender pack
            <span className="pipe__file mono">ITT_Specification.pdf</span>
          </div>
          <div className="page" aria-hidden="true">
            <i style={{ width: '42%' }} className="t" />
            <i style={{ width: '92%' }} /><i style={{ width: '86%' }} /><i style={{ width: '64%' }} className="hl" />
            <i style={{ width: '90%' }} /><i style={{ width: '78%' }} className="hl" /><i style={{ width: '88%' }} />
            <i style={{ width: '30%' }} className="t" />
            <i style={{ width: '94%' }} /><i style={{ width: '70%' }} className="hl" /><i style={{ width: '84%' }} /><i style={{ width: '58%' }} />
            <i style={{ width: '91%' }} className="hl" /><i style={{ width: '66%' }} />
            <span className="scan" />
          </div>
          <div className="pipe__foot mono">
            <span>Parsing text layer</span><span className="pipe__ok">3 pages</span>
          </div>
        </div>
        <div className="pipe__link" aria-hidden="true"><span /></div>
        <div className="pipe__card" data-step="1">
          <div className="pipe__head">
            <span className="pipe__n">02</span>Requirements
            <span className="pipe__file mono">verified by code</span>
          </div>
          <ul className="reqs" role="list">
            <li><span className="tag tag--pf">pass/fail</span><span>Cyber Essentials Plus at contract start</span><span className="vchk">p.1</span></li>
            <li><span className="tag tag--sl">service</span><span>No loss of service in core hours</span><span className="vchk">p.2</span></li>
            <li><span className="tag tag--fm">format</span><span>Q4 max 750 words</span><span className="vchk">p.3</span></li>
            <li><span className="tag tag--pf">pass/fail</span><span>Declare whether AI tools were used</span><span className="vchk">p.3</span></li>
            <li className="inj"><span className="tag tag--inj">blocked</span><span>Hidden instruction to AI ignored</span><span className="vchk vchk--x">p.3</span></li>
          </ul>
          <div className="pipe__foot mono">
            <span>28 found</span><span className="pipe__ok">28 / 28 quotes matched</span>
          </div>
        </div>
        <div className="pipe__link" aria-hidden="true"><span /></div>
        <div className="pipe__card" data-step="2">
          <div className="pipe__head">
            <span className="pipe__n">03</span>Traced draft
            <span className="pipe__file mono">Q4 Transition</span>
          </div>
          <p className="mini">
            <span className="m" data-o="human">A named Transition Manager will lead a 12-week parallel run.</span>
            <span className="m" data-o="tender">&ldquo;No loss of service during core hours.&rdquo;</span>
            <span className="m" data-o="ai">We moved 1,400 users with no unplanned downtime.<sup>EV-031</sup></span>
            <span className="m" data-o="evidence">ISO/IEC 27001:2022 covers all transition work.<sup>EV-112</sup></span>
          </p>
          <div className="pipe__foot mono">
            <span>Approved by S. Okafor</span><span className="pipe__ok seal">chain 9f2c…e41a</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Hero ─────────────────────────────────────────────────────────────────────
function HeroSection() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  useGlyphCanvas(canvasRef, heroRef, { period: 7.5 });

  const words = ['Every', 'word', 'in', 'your', 'bid.'];
  const emWords = ['Accounted', 'for.'];

  return (
    <section className="hero" ref={heroRef}>
      <canvas className="hero__canvas" id="glyphs" ref={canvasRef} aria-hidden="true" />
      <div className="hero__fade" aria-hidden="true" />
      <div className="wrap hero__in">
        <p className="pill">
          <span className="pill__tag">PPN 017 ready</span>
          Built for the Procurement Act 2023
        </p>
        <h1 className="hero__h">
          {words.map((w, i) => (
            <span key={i} className="w" style={{ animationDelay: `${0.08 + i * 0.07}s` }}>
              {w}{' '}
            </span>
          ))}
          <br />
          <em>
            {emWords.map((w, i) => (
              <span key={i} className="w" style={{ animationDelay: `${0.08 + (words.length + i) * 0.07}s` }}>
                {w}{' '}
              </span>
            ))}
          </em>
        </h1>
        <p className="hero__lede">
          tood.os reads the whole tender pack, verifies every requirement against its source{' '}
          <b>by code</b>, and drafts answers where each sentence records who wrote it, which
          model, what evidence and who approved it.
        </p>
        <div className="hero__cta">
          <a className="btn btn--primary btn--lg" href="/login">
            Start free trial — 14 days free{' '}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </a>
          <a className="btn btn--ghost btn--lg" href="#standard">See how it works</a>
        </div>
        <p className="hero__note">No credit card required · Cancel any time · Google sign-in</p>
      </div>
      <PipelineDemo />
    </section>
  );
}

// ── Stats Bar ────────────────────────────────────────────────────────────────
function StatsBar() {
  return (
    <div className="stats-bar">
      <div className="wrap stats-bar__in">
        <div className="stat">
          <span className="stat__value">56+</span>
          <span className="stat__label">Requirements extracted</span>
        </div>
        <div className="stat">
          <span className="stat__value">1+</span>
          <span className="stat__label">Tender documents processed</span>
        </div>
        <div className="stat">
          <span className="stat__value">3</span>
          <span className="stat__label">UK procurement regulations</span>
        </div>
        <div className="stat">
          <span className="stat__value">100%</span>
          <span className="stat__label">Export accuracy</span>
        </div>
      </div>
    </div>
  );
}

// ── Marquee ──────────────────────────────────────────────────────────────────
const MARQUEE_ITEMS = [
  'Invitation to tender', 'Specification', 'Procurement Specific Questionnaire',
  'Pricing schedule', 'Social value', 'Clarifications', 'Contract terms',
  'Framework call-off', 'Dynamic market', 'Cyber Essentials', 'Service levels', 'Word limits',
];

function MarqueeSet({ hidden }: { hidden?: boolean }) {
  return (
    <div className="marquee__set" aria-hidden={hidden ? 'true' : undefined}>
      {MARQUEE_ITEMS.map((item) => <span key={item}>{item}</span>)}
    </div>
  );
}

function MarqueeSection() {
  return (
    <section className="marquee" aria-label="Documents and requirements tood.os handles">
      <div className="marquee__track">
        <MarqueeSet />
        <MarqueeSet hidden />
      </div>
    </section>
  );
}

// ── Problem ───────────────────────────────────────────────────────────────────
function ProblemSection() {
  return (
    <section className="sec">
      <div className="wrap problem">
        <div className="problem__quote reveal">
          <p className="eyebrow">The problem</p>
          <blockquote>
            &ldquo;Statements, facts or references that appear plausible, but are in fact false.&rdquo;
          </blockquote>
          <p className="src">
            How UK government guidance describes the risk of AI-written tenders.{' '}
            <a
              href="https://www.gov.uk/government/publications/ppn-017-improving-transparency-of-ai-use-in-procurement/ppn-017-improving-transparency-of-ai-use-in-procurement-html"
              target="_blank"
              rel="noopener noreferrer"
            >
              PPN 017, Cabinet Office
            </a>
          </p>
        </div>
        <div className="problem__facts">
          <div className="fact reveal">
            <span className="fact__k">Allowed</span>
            <p>Suppliers&rsquo; use of AI in bids is <b>not prohibited</b>.</p>
          </div>
          <div className="fact reveal">
            <span className="fact__k">Asked</span>
            <p>Buyers <b>may ask you to disclose</b> where AI was used in your tender.</p>
          </div>
          <div className="fact reveal">
            <span className="fact__k">Checked</span>
            <p>And to confirm the output was <b>checked and verified for accuracy</b>.</p>
          </div>
          <p className="problem__close reveal">
            Most AI bid tools sell speed. <b>tood.os sells the audit trail.</b> Speed is a side effect.
          </p>
        </div>
      </div>
    </section>
  );
}

// ── Live Demo ─────────────────────────────────────────────────────────────────
interface Requirement {
  id: string;
  type: string;
  summary: string;
  verified: boolean;
  page: number;
  start: number;
  end: number;
}
interface PageData { n: number; text: string; }
interface AnalysisResult {
  name: string;
  pages: PageData[];
  requirements: Requirement[];
  injection?: Requirement[];
  stats: { found: number; verified: number; rejected: number; };
  model: string;
  seconds: number;
  cached_at?: string;
}

type Stage = 'idle' | 'parse' | 'extract' | 'verify' | 'done';
const TYPE_LABELS: Record<string, [string, string]> = {
  pass_fail: ['pass/fail', 'tag--pf'],
  scored: ['scored', 'tag--sc'],
  service_level: ['service', 'tag--sl'],
  deadline: ['deadline', 'tag--dl'],
  format: ['format', 'tag--fm'],
};

function esc(s: string) {
  return s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] ?? c));
}

function LiveDemoSection() {
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<Stage>('idle');
  const [timer, setTimer] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isDrop, setIsDrop] = useState(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const STAGES: Array<{ key: Stage; label: string }> = [
    { key: 'parse', label: 'Parse text layer' },
    { key: 'extract', label: 'Extract requirements (model)' },
    { key: 'verify', label: 'Verify every quote (code)' },
  ];

  function startTimer() {
    const t0 = performance.now();
    if (tickRef.current) clearInterval(tickRef.current);
    tickRef.current = setInterval(() => {
      setTimer(((performance.now() - t0) / 1000).toFixed(1) + 's elapsed');
    }, 100);
  }
  function stopTimer(txt: string) {
    if (tickRef.current) clearInterval(tickRef.current);
    setTimer(txt);
  }

  async function poll(jid: string): Promise<AnalysisResult> {
    return new Promise((resolve, reject) => {
      const go = () => {
        fetch(`/api/jobs/${jid}`)
          .then((r) => r.json())
          .then((j: { status: string; result?: AnalysisResult; error?: string; stage?: string }) => {
            if (j.status === 'done') { setStage('done'); resolve(j.result!); }
            else if (j.status === 'error') reject(new Error(j.error ?? 'Analysis failed'));
            else { setStage(j.stage === 'queued' ? 'parse' : (j.stage as Stage) ?? 'parse'); setTimeout(go, 900); }
          })
          .catch(reject);
      };
      go();
    });
  }

  async function begin(promise: Promise<Response>, fallback: boolean) {
    if (busy) return;
    setBusy(true); setError(null); setResult(null); setStage('parse'); startTimer();
    try {
      const r = await promise;
      if (!r.ok) { const j = await r.json(); throw new Error(j.detail ?? 'Upload failed'); }
      const j = await r.json();
      const res = await poll(j.job_id);
      stopTimer(`Completed in ${res.seconds}s`);
      setResult(res);
    } catch (e) {
      const msg = (e as Error).message ?? '';
      if (fallback && /fetch|network|Failed|Load/i.test(msg)) {
        try {
          const r = await fetch('/samples/riverside-result.json');
          const res: AnalysisResult = await r.json();
          setStage('done');
          stopTimer('Recorded run');
          setResult(res);
        } catch {
          setStage('idle'); stopTimer(''); setError('Analysis failed. Please try again.');
        }
      } else {
        setStage('idle'); stopTimer(''); setError(msg || 'Analysis failed. Please try again.');
      }
    } finally {
      setBusy(false);
    }
  }

  function runSample() {
    begin(fetch('/api/analyse-sample?name=riverside', { method: 'POST' }), true);
  }

  function upload(f: File | null) {
    if (!f) return;
    if (f.type !== 'application/pdf' && !/\.pdf$/i.test(f.name)) { setError('Please choose a PDF file.'); return; }
    if (f.size > 10 * 1024 * 1024) { setError('That file is over 10 MB. Try a smaller PDF.'); return; }
    const fd = new FormData(); fd.append('file', f);
    begin(fetch('/api/analyse', { method: 'POST', body: fd }), false);
  }

  function selectReq(id: string) {
    setSelectedId(id);
  }

  const filteredItems = result
    ? [
      ...result.requirements.filter((r) => filter === 'all' || r.type === filter),
      ...(filter === 'all' ? (result.injection ?? []).map((r, i) => ({ ...r, id: `INJ-${i + 1}`, _inj: true })) : []),
    ]
    : [];

  function buildDocHtml(): string {
    if (!result) return '';
    const byPage: Record<number, Array<{ s: number; e: number; id: string; cls: string }>> = {};
    result.requirements.forEach((r) => {
      if (r.verified) (byPage[r.page] = byPage[r.page] ?? []).push({ s: r.start, e: r.end, id: r.id, cls: '' });
    });
    (result.injection ?? []).forEach((r, i) => {
      if (r.verified) (byPage[r.page] = byPage[r.page] ?? []).push({ s: r.start, e: r.end, id: `INJ-${i + 1}`, cls: 'inj' });
    });
    let html = '';
    result.pages.forEach((p) => {
      html += `<span class="doc__pg">Page ${p.n}</span>`;
      const rs = (byPage[p.n] ?? []).sort((a, b) => a.s - b.s || b.e - a.e);
      let pos = 0;
      rs.forEach((r) => {
        if (r.s < pos) return;
        html += esc(p.text.slice(pos, r.s)) +
          `<mark data-id="${r.id}" class="${r.cls}" title="${r.id}">` +
          esc(p.text.slice(r.s, r.e)) + '</mark>';
        pos = r.e;
      });
      html += esc(p.text.slice(pos));
    });
    return html;
  }

  return (
    <section className="live" id="live">
      <div className="wrap">
        <div className="live__head">
          <div>
            <p className="eyebrow eyebrow--inv">Live demo · real model, real verification</p>
            <h2 className="h2 h2--inv">
              Run it on a tender. <em>Right now.</em>
            </h2>
          </div>
          <p className="live__lede">
            Pick the sample or drop your own PDF. A model extracts every requirement with a
            verbatim quote. Then plain code checks each quote against the document. Anything it
            cannot find is rejected, not trusted.
          </p>
        </div>

        <div className="live__grid">
          <aside className="live__side">
            <p className="side__label">Sample document</p>
            <button className="sample" type="button" onClick={runSample} disabled={busy}>
              <span className="sample__icon" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
                  <path d="M14 3v5h5" />
                </svg>
              </span>
              <span className="sample__t">
                <b>riverside-itt-sample.pdf</b>
                <small>Fictional council ITT · 3 pages · includes a hidden prompt-injection test</small>
              </span>
              <span className="sample__go" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </span>
            </button>
            <a className="side__dl" href="/samples/riverside-itt-sample.pdf" target="_blank" rel="noopener noreferrer">
              Open the sample PDF
            </a>

            <p className="side__label" style={{ marginTop: 'var(--space-6)' }}>Your own tender</p>
            <label
              className={`drop${isDrop ? ' is-over' : ''}`}
              id="drop"
              htmlFor="fileIn"
              onDragEnter={(e) => { e.preventDefault(); setIsDrop(true); }}
              onDragOver={(e) => { e.preventDefault(); setIsDrop(true); }}
              onDragLeave={() => setIsDrop(false)}
              onDrop={(e) => { e.preventDefault(); setIsDrop(false); upload(e.dataTransfer.files[0] ?? null); }}
            >
              <input
                type="file"
                id="fileIn"
                accept="application/pdf"
                className="sr-only"
                onChange={(e) => { upload(e.target.files?.[0] ?? null); (e.target as HTMLInputElement).value = ''; }}
              />
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
                <path d="M12 16V4M7 9l5-5 5 5" />
                <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
              </svg>
              <b>Drop a PDF here</b>
              <small>or click to choose · text-based PDF · up to 30 pages, 10 MB</small>
            </label>
            <p className="side__fine">
              Processed in memory for this demo and not stored. Do not upload confidential
              documents to a public demo. Scanned PDFs are not supported here yet.
            </p>

            <div className="stages" aria-live="polite">
              {STAGES.map((s) => {
                const order = ['parse', 'extract', 'verify'];
                const idx = order.indexOf(stage);
                const sIdx = order.indexOf(s.key);
                const isOn = sIdx === idx;
                const isDone = stage === 'done' || (idx > -1 && sIdx < idx);
                return (
                  <div key={s.key} className={`stage${isOn ? ' is-on' : ''}${isDone ? ' is-done' : ''}`}>
                    <span className="stage__d" />
                    {s.label}
                  </div>
                );
              })}
              <p className="stages__t mono">{timer}</p>
            </div>
          </aside>

          <div className="live__out" id="out">
            {!result && !error && (
              <div className="empty" id="empty">
                <div className="empty__art" aria-hidden="true">
                  <span /><span /><span /><span /><span />
                </div>
                <p><b>Results appear here.</b> Each requirement links to the exact sentence it came from, highlighted in the document.</p>
              </div>
            )}

            {result && (
              <div className="res" id="res">
                <div className="kpis">
                  <div className="kpi"><span className="kpi__n">{result.stats.found}</span><span className="kpi__l">requirements found</span></div>
                  <div className="kpi"><span className="kpi__n kpi__n--ok">{result.stats.verified}</span><span className="kpi__l">quotes verified by code</span></div>
                  <div className="kpi"><span className="kpi__n kpi__n--bad">{result.stats.rejected}</span><span className="kpi__l">rejected, quote not found</span></div>
                  <div className="kpi"><span className="kpi__n kpi__n--warn">{(result.injection ?? []).length}</span><span className="kpi__l">hidden AI instructions ignored</span></div>
                </div>
                <div className="res__body">
                  <div className="res__list">
                    <div className="filters" role="group" aria-label="Filter by type">
                      {['all', 'pass_fail', 'scored', 'service_level', 'deadline', 'format'].map((f) => (
                        <button key={f} className={`chip${filter === f ? ' is-on' : ''}`} onClick={() => setFilter(f)}>
                          {f === 'all' ? 'All' : f === 'pass_fail' ? 'Pass/fail' : f === 'scored' ? 'Scored' : f === 'service_level' ? 'Service' : f === 'deadline' ? 'Deadlines' : 'Format'}
                        </button>
                      ))}
                    </div>
                    <ul className="rlist" role="list">
                      {filteredItems.map((r, i) => {
                        const inj = !!(r as Requirement & { _inj?: boolean })._inj;
                        const [tlabel, tcls] = inj ? ['injection', 'tag--dl'] : (TYPE_LABELS[r.type] ?? [r.type, '']);
                        return (
                          <li
                            key={r.id}
                            className={`rl${selectedId === r.id ? ' is-sel' : ''}`}
                            style={{ animationDelay: `${Math.min(i * 35, 900)}ms` }}
                            onClick={() => selectReq(r.id)}
                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectReq(r.id); } }}
                            tabIndex={0}
                          >
                            <span className="rl__id">{r.id}</span>
                            <span className="rl__s">
                              {inj ? 'Hidden instruction to AI detected and ignored' : r.summary}
                              <br />
                              <span className={`tag ${tcls}`}>{tlabel}</span>
                            </span>
                            {r.verified
                              ? <span className="rl__v ok">verified p.{r.page}</span>
                              : <span className="rl__v no">rejected</span>
                            }
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                  <div className="res__doc">
                    <div className="doc__bar mono">
                      <span>{result.name}</span>
                      <span>{result.pages.length} {result.pages.length === 1 ? 'page' : 'pages'}</span>
                    </div>
                    <div
                      className="doc__text"
                      tabIndex={0}
                      aria-label="Document text"
                      dangerouslySetInnerHTML={{ __html: buildDocHtml() }}
                      onClick={(e) => {
                        const m = (e.target as HTMLElement).closest('mark');
                        if (m) selectReq(m.dataset.id ?? '');
                      }}
                    />
                  </div>
                </div>
                <p className="res__meta mono">
                  {result.cached_at
                    ? `Live analysis is unavailable right now, so this is a recorded run from ${result.cached_at}. `
                    : ''}
                  Model: {result.model} · {result.seconds}s · Quotes checked against the PDF text layer by code, not by the model.
                </p>
              </div>
            )}

            {error && <div className="err">{error}</div>}
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Provenance Demo ───────────────────────────────────────────────────────────
interface SpanData {
  o: string;
  label: string;
  rows: [string, string][];
  quote: string;
}

const PROV_DATA: Record<string, SpanData> = {
  s1: { o: 'human', label: 'Person', rows: [['Author', 'Sarah Okafor, Bid Manager'], ['Created', '14 Sep 2026, 10:31'], ['Edits', '3 revisions'], ['Approved', 'S. Okafor, 16 Sep 17:05']], quote: 'Typed directly in the editor. No model involved.' },
  s2: { o: 'tender', label: 'Tender quote', rows: [['Source', '02_Specification.pdf'], ['Location', '§4.2, page 2'], ['Match', 'Verbatim, checked by code'], ['Requirement', 'R-010 (service level)']], quote: '"The service must ensure no loss of service during core hours (08:00-18:00) throughout transition and steady state."' },
  s3: { o: 'ai', label: 'AI draft', rows: [['Model', 'Admitted model, card v3'], ['Prompt', 'answer.draft@14'], ['Evidence', 'EV-031 case study'], ['Edited by', 'S. Okafor (2 changes)'], ['Approved', 'S. Okafor, 16 Sep 17:05']], quote: 'Supported by EV-031: "Migrated 1,400 users to the new service desk over a weekend cut-over. No unplanned downtime recorded."' },
  s4: { o: 'evidence', label: 'Evidence quote', rows: [['Evidence', 'EV-112 ISO/IEC 27001:2022'], ['Issuer', 'UKAS-accredited body'], ['Valid to', '14 Mar 2027'], ['Inserted by', 'J. Patel, 15 Sep 09:12']], quote: 'Certificate scope covers "IT service management and end-user support".' },
  s5: { o: 'flag', label: 'Unsupported', rows: [['Model', 'Admitted model, card v3'], ['Prompt', 'answer.draft@14'], ['Evidence', 'None found'], ['Status', 'Blocks export']], quote: 'This sentence makes a factual commitment that no item in your evidence library supports. Remove it, or attach evidence and have a person approve it.' },
};

function ProvenanceDemoSection() {
  const [activeKey, setActiveKey] = useState('s3');
  const [provOn, setProvOn] = useState(true);
  const [resolved, setResolved] = useState(false);
  const [exportOk, setExportOk] = useState(false);
  const [s5Rewritten, setS5Rewritten] = useState(false);
  const [s5Removed, setS5Removed] = useState(false);

  const d = PROV_DATA[activeKey];

  function handleAction(act: string) {
    setResolved(true);
    if (act === 'remove') {
      setS5Removed(true);
      setExportOk(true);
      setActiveKey('s1');
    } else {
      setS5Rewritten(true);
      setExportOk(true);
    }
  }

  return (
    <section className="sec" id="inspect">
      <div className="wrap">
        <div className="sec__head">
          <p className="eyebrow">Provenance view</p>
          <h2 className="h2">Click any sentence. See exactly where it came from.</h2>
          <p className="sec__lede">
            Person, model, evidence or tender. Unsupported claims block export until someone
            removes them or attaches proof.
          </p>
        </div>

        <div className="demo reveal" aria-label="Interactive demo: provenance view of a tender answer">
          <div className="demo__bar">
            <div className="demo__crumbs">
              <span>Service Desk &amp; End-User Support</span>
              <span aria-hidden="true">/</span>
              <b>Q4 Transition plan</b>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={provOn}
                onChange={(e) => setProvOn(e.target.checked)}
              />
              Provenance view
            </label>
          </div>
          <div className="demo__body">
            <div className="editor">
              <div className="q">
                <span className="q__id">Q4</span>
                <span className="q__t">Describe how you will maintain continuity of service during transition.</span>
              </div>
              <p className="q__meta">Weighting 20% · 750 words max · Sample answer by Northgate Digital Ltd (fictional)</p>
              <p className={`answer${provOn ? ' is-prov' : ''}`}>
                <span
                  className={`span${activeKey === 's1' ? ' is-active' : ''}`}
                  data-o="human"
                  tabIndex={0}
                  role="button"
                  onClick={() => setActiveKey('s1')}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveKey('s1'); } }}
                >
                  We will run a 12-week parallel transition, led by a named Transition Manager who reports weekly to the Authority&rsquo;s contract lead.
                </span>{' '}
                <span
                  className={`span${activeKey === 's2' ? ' is-active' : ''}`}
                  data-o="tender"
                  tabIndex={0}
                  role="button"
                  onClick={() => setActiveKey('s2')}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveKey('s2'); } }}
                >
                  This directly addresses the Authority&rsquo;s requirement for &ldquo;no loss of service during core hours (08:00–18:00)&rdquo;.
                </span>{' '}
                <span
                  className={`span${activeKey === 's3' ? ' is-active' : ''}`}
                  data-o="ai"
                  tabIndex={0}
                  role="button"
                  onClick={() => setActiveKey('s3')}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveKey('s3'); } }}
                >
                  In our 2024 migration for a regional housing association, we moved 1,400 users to a new service desk with no unplanned downtime.<span className="cite">EV-031</span>
                </span>{' '}
                <span
                  className={`span${activeKey === 's4' ? ' is-active' : ''}`}
                  data-o="evidence"
                  tabIndex={0}
                  role="button"
                  onClick={() => setActiveKey('s4')}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveKey('s4'); } }}
                >
                  Our ISO/IEC 27001:2022 certification covers all transition activities.<span className="cite">EV-112</span>
                </span>{' '}
                {!s5Removed && (
                  <span
                    className={`span${activeKey === 's5' ? ' is-active' : ''}`}
                    data-o={s5Rewritten ? 'ai' : 'flag'}
                    tabIndex={0}
                    role="button"
                    onClick={() => setActiveKey('s5')}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveKey('s5'); } }}
                  >
                    {s5Rewritten
                      ? <>We will meet the 99.5% availability target set out in the specification.<span className="cite">EV-118</span></>
                      : 'We guarantee 99.99% availability throughout the contract.'
                    }
                  </span>
                )}
              </p>
              <div className="legend" aria-label="Legend">
                <span><i style={{ background: 'var(--p-human)' }} />Written by a person</span>
                <span><i style={{ background: 'var(--p-ai)' }} />Drafted by AI, evidence-bound</span>
                <span><i style={{ background: 'var(--p-evidence)' }} />Quoted from your evidence</span>
                <span><i style={{ background: 'var(--p-tender)' }} />Quoted from the tender</span>
                <span><i style={{ background: 'var(--p-flag)' }} />Unsupported claim</span>
              </div>
              <div className={`export${exportOk ? ' is-ok' : ''}`}>
                <div className="export__status">
                  <span className="dot" aria-hidden="true" />
                  <span>
                    {exportOk
                      ? 'All claims traced. Ready to export with the AI use record.'
                      : '1 unsupported claim. Export is blocked until it is resolved.'}
                  </span>
                </div>
                <button
                  className="btn btn--primary btn--sm"
                  aria-disabled={exportOk ? 'false' : 'true'}
                  onClick={() => {
                    if (!exportOk) { setActiveKey('s5'); } else {
                      alert('Demo only. In the product this exports DOCX plus the AI use record.');
                    }
                  }}
                >
                  Export to DOCX
                </button>
              </div>
            </div>
            <aside className="inspector" aria-live="polite">
              {d && (
                <>
                  <div className="inspector__h fade-swap">
                    <span className="badge" data-o={d.o}>{d.label}</span>
                    <span className="mono muted" style={{ fontSize: '11px' }}>
                      span #{activeKey.replace('s', '')}
                    </span>
                  </div>
                  <dl className="kv fade-swap">
                    {(activeKey === 's5' && s5Rewritten
                      ? [['Model', 'Admitted model, card v3'], ['Prompt', 'answer.draft@14'], ['Evidence', 'EV-118 SLA report 2025'], ['Approved', 'S. Okafor, just now']] as [string, string][]
                      : d.rows
                    ).map(([dt, dd]) => (
                      <><dt key={`dt-${dt}`}>{dt}</dt><dd key={`dd-${dt}`}>{dd}</dd></>
                    ))}
                  </dl>
                  <p className="quote fade-swap">
                    {activeKey === 's5' && s5Rewritten
                      ? 'Claim rewritten to match evidence EV-118: "Measured availability 99.71% across 2025."'
                      : d.quote}
                  </p>
                  {activeKey === 's5' && !resolved && (
                    <div className="inspector__actions">
                      <button className="btn btn--primary btn--sm" onClick={() => handleAction('remove')}>Remove claim</button>
                      <button className="btn btn--ghost btn--sm" onClick={() => handleAction('attach')}>Attach evidence</button>
                    </div>
                  )}
                  <p className="inspector__hint">Select any highlighted sentence to inspect its origin.</p>
                </>
              )}
            </aside>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Standard (9 rules) ────────────────────────────────────────────────────────
function StandardSection() {
  return (
    <section className="sec sec--alt" id="standard">
      <div className="wrap">
        <div className="sec__head">
          <p className="eyebrow">The tood.os standard</p>
          <h2 className="h2">Nine rules the product enforces. <em>Not a slogan.</em></h2>
          <p className="sec__lede">
            They apply whoever writes the text, a person or any AI model, and they apply to
            our own engineering as well.
          </p>
        </div>
        <div className="rules">
          <article className="rule rule--big reveal">
            <span className="rule__n">V1</span>
            <h3>Provenance for every character</h3>
            <p>Each span records its origin when it is created: a named person, a model and prompt version, a quoted evidence item, the tender itself, or &ldquo;pasted, origin unknown&rdquo;. Never guessed afterwards.</p>
            <div className="rule__viz" aria-hidden="true">
              <span data-o="human">person</span>
              <span data-o="ai">model</span>
              <span data-o="evidence">evidence</span>
              <span data-o="tender">tender</span>
              <span data-o="unknown">unknown</span>
            </div>
          </article>
          <article className="rule reveal">
            <span className="rule__n">V2</span>
            <h3>Requirements tied to the source</h3>
            <p>Every requirement carries a verbatim quote, located in the original by code. You just watched it happen.</p>
          </article>
          <article className="rule reveal">
            <span className="rule__n">V3</span>
            <h3>Claims tied to evidence</h3>
            <p>Figures, clients, certifications and past results must link to your evidence library or they are flagged.</p>
          </article>
          <article className="rule reveal">
            <span className="rule__n">V4</span>
            <h3>A person is always accountable</h3>
            <p>A model can draft. It can never approve. Every answer needs a named approver.</p>
          </article>
          <article className="rule reveal">
            <span className="rule__n">V5</span>
            <h3>Tamper-evident history</h3>
            <p>Append-only, hash-chained revisions. Rewriting history is detectable.</p>
          </article>
          <article className="rule reveal">
            <span className="rule__n">V6</span>
            <h3>Disclosure-ready</h3>
            <p>The AI use record is generated from the ledger, never written by a model.</p>
          </article>
          <article className="rule reveal">
            <span className="rule__n">V7</span>
            <h3>Models earn their place</h3>
            <p>No model is used until it passes admission tests, re-run on every version change.</p>
          </article>
          <article className="rule reveal">
            <span className="rule__n">V8</span>
            <h3>Stays within bounds</h3>
            <p>Only your tender and your evidence. No pricing commitments, no legal advice. When it does not know, it says so.</p>
          </article>
          <article className="rule rule--wide reveal">
            <span className="rule__n">V9</span>
            <h3>We are auditable too</h3>
            <p>A public trust centre will list the models we use, their latest test results, any fabrication incident that reached a customer, and every sub-processor that touches your data.</p>
          </article>
        </div>
      </div>
    </section>
  );
}

// ── AI Use Record ─────────────────────────────────────────────────────────────
function AIUseRecordSection() {
  const rows = [
    { q: 'Q1 Understanding', ai: false, pct: '0%', pctN: 0, by: 'J. Patel', date: '15 Sep' },
    { q: 'Q2 Methodology', ai: true, pct: '38%', pctN: 38, by: 'S. Okafor', date: '16 Sep' },
    { q: 'Q3 Team & CVs', ai: true, pct: '12%', pctN: 12, by: 'J. Patel', date: '16 Sep' },
    { q: 'Q4 Transition', ai: true, pct: '27%', pctN: 27, by: 'S. Okafor', date: '16 Sep' },
    { q: 'Q5 Social value', ai: false, pct: '0%', pctN: 0, by: 'M. Reyes', date: '17 Sep' },
  ];
  return (
    <section className="sec" id="record">
      <div className="wrap record">
        <div className="record__copy reveal">
          <p className="eyebrow">AI use &amp; verification record</p>
          <h2 className="h2">When the buyer asks, you already have the answer.</h2>
          <p>
            Contracting authorities may ask whether AI helped write your tender and whether it was
            checked. tood.os answers from the revision ledger, question by question, assembled by
            code from what actually happened.
          </p>
          <ul>
            <li>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
              Which questions used AI, and which did not
            </li>
            <li>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
              How much AI-originated text survived human editing
            </li>
            <li>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
              Who verified each answer, and when
            </li>
            <li>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
              A chain-head hash tying the record to the exported file
            </li>
          </ul>
        </div>
        <div className="paper reveal" aria-label="Sample AI use and verification record">
          <div className="paper__h">
            <div>
              <p className="eyebrow">Sample record · fictional</p>
              <h3>AI Use &amp; Verification Record</h3>
            </div>
            <div className="mono muted" style={{ textAlign: 'right' }}>
              Northgate Digital Ltd<br />Service Desk &amp; EUS
            </div>
          </div>
          <table>
            <thead>
              <tr><th>Question</th><th>AI used</th><th>AI text kept</th><th>Verified by</th><th>Date</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.q}>
                  <td>{r.q}</td>
                  <td className={r.ai ? 'yes' : 'no'}>{r.ai ? 'Yes' : 'No'}</td>
                  <td className="mono"><span className="bar" style={{ '--w': r.pct } as React.CSSProperties} />{r.pct}</td>
                  <td>{r.by}</td>
                  <td className="mono">{r.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="chain" aria-label="Revision hash chain">
            <div className="block"><b>rev 40</b>a71d…03be</div>
            <span className="arrow" aria-hidden="true" />
            <div className="block"><b>rev 41</b>c0e8…9a12</div>
            <span className="arrow" aria-hidden="true" />
            <div className="block"><b>rev 42</b>5b3f…d7c0</div>
            <span className="arrow" aria-hidden="true" />
            <div className="block is-head"><b>rev 43</b>9f2c…e41a</div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Model Admission ───────────────────────────────────────────────────────────
function ModelAdmissionBand() {
  const tests = [
    { t: 'Fabrication bait', d: 'Asked to cite certificates that are not in the library', v: 'refuse or flag 100%' },
    { t: 'Prompt injection', d: 'Hidden instructions inside tender documents', v: 'ignore 100%' },
    { t: 'Honest gaps', d: 'Questions the evidence cannot answer', v: 'says so ≥ 95%' },
    { t: 'Requirement recall', d: 'Expert-annotated public tender packs', v: '≥ 95%, pass/fail ≥ 98%' },
    { t: 'Scope', d: 'Pricing, legal advice, outside facts', v: 'refuse or label ≥ 98%' },
    { t: 'Consistency', d: 'Same input, five runs', v: '≥ 95% overlap' },
  ];
  return (
    <section className="band">
      <div className="wrap admit">
        <div>
          <p className="eyebrow eyebrow--inv">Model admission</p>
          <h2 className="h2 h2--inv">No model works here <em>until it passes.</em></h2>
          <p className="band__lede">
            Results are kept as a model card per version. Production pins the admitted version; a
            provider update does not reach your bids until it is re-tested. These are launch
            targets; measured results will be published.
          </p>
        </div>
        <div className="tests">
          {tests.map((t) => (
            <div key={t.t} className="test reveal">
              <span className="test__t">{t.t}</span>
              <span className="test__d">{t.d}</span>
              <span className="test__v">{t.v}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Limits ────────────────────────────────────────────────────────────────────
function LimitsSection() {
  const limits = [
    { title: 'We do not guarantee your evidence is true.', body: 'We show a claim is traced and supported. If a case study is wrong, the approver is accountable.' },
    { title: 'We do not guarantee you will win.', body: 'We help you submit something complete, compliant and defensible.' },
    { title: 'We do not use AI detectors.', body: 'They guess. We record origin when text is created, and label pasted text as unknown.' },
    { title: 'We do not submit on your behalf.', body: 'A person in your company submits. Always.' },
  ];
  return (
    <section className="sec sec--tight">
      <div className="wrap limits">
        <div>
          <p className="eyebrow">What we do not promise</p>
          <h2 className="h2">Honesty about the limits is part of the standard.</h2>
        </div>
        <ul className="limits__list" role="list">
          {limits.map((l) => (
            <li key={l.title}><b>{l.title}</b>{l.body}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// ── Pricing ───────────────────────────────────────────────────────────────────
function PricingSection() {
  return (
    <section className="sec sec--alt" id="pricing">
      <div className="wrap">
        <div className="sec__head sec__head--c">
          <p className="eyebrow">Pricing</p>
          <h2 className="h2">We do not compete on price. <em>We price for being right.</em></h2>
          <p className="sec__lede">
            Founding pricing for the first 30 companies, locked for 12 months, in exchange for
            honest feedback.
          </p>
        </div>
        <div className="plans">
          <div className="plan reveal">
            <h3>Starter</h3>
            <p className="plan__price">£99<small> / month, excl. VAT</small></p>
            <p className="plan__d">One tender pack, full requirement matrix with verified source quotes.</p>
            <ul role="list">
              <li>3 active tenders</li>
              <li>2 user seats</li>
              <li>Requirement matrix</li>
              <li>Audit trail</li>
            </ul>
            <a className="btn btn--ghost" href="/login?plan=starter">Start 14-day free trial</a>
          </div>
          <div className="plan plan--feat reveal">
            <div className="plan__badge">Most popular</div>
            <p className="seats"><span>30</span> founding places</p>
            <h3>Professional</h3>
            <p className="plan__price">£299<small> / month, excl. VAT</small></p>
            <p className="plan__d">The full workspace for one company, with provenance and the AI use record on every bid.</p>
            <ul role="list">
              <li>20 active tenders</li>
              <li>10 user seats</li>
              <li>Gemini AI drafting</li>
              <li>Provenance view and export gate</li>
              <li>AI use &amp; verification record</li>
              <li>Price locked for 12 months</li>
            </ul>
            <a className="btn btn--primary" href="/login?plan=professional">Start 14-day free trial</a>
          </div>
          <div className="plan reveal">
            <h3>Enterprise</h3>
            <p className="plan__price">£799<small> / month, excl. VAT</small></p>
            <p className="plan__d">For large organisations with unlimited tenders, SSO, and custom data residency.</p>
            <ul role="list">
              <li>Unlimited tenders &amp; users</li>
              <li>SSO / SAML</li>
              <li>Custom data residency</li>
              <li>Dedicated SLA</li>
            </ul>
            <a className="btn btn--ghost" href="/login?plan=enterprise">Start 14-day free trial</a>
          </div>
        </div>
        <p className="plans__note">
          Beta pricing. Plans may change before general availability; founding members keep their
          price for 12 months.
        </p>
      </div>
    </section>
  );
}

// ── Trial How It Works ─────────────────────────────────────────────────────────
function TrialHowItWorks() {
  return (
    <section className="sec sec--alt">
      <div className="wrap">
        <div className="sec__head sec__head--c">
          <p className="eyebrow">How the 14‑day trial works</p>
          <h2 className="h2">Experience the full platform, zero risk.</h2>
          <p className="sec__lede">
            Try every feature with your own tender documents. No payment details required.
          </p>
        </div>
        <div className="trial-steps">
          <div className="trial-step reveal">
            <div className="trial-step__number">1</div>
            <h3>Sign up in 30 seconds</h3>
            <p>Use your Google account. No credit card required. Start immediately.</p>
          </div>
          <div className="trial-step reveal">
            <div className="trial-step__number">2</div>
            <h3>Upload your first tender</h3>
            <p>Drop any PDF tender pack. The system parses requirements in minutes.</p>
          </div>
          <div className="trial-step reveal">
            <div className="trial-step__number">3</div>
            <h3>Explore the workspace</h3>
            <p>Try AI drafting, audit trails, verification, and export.</p>
          </div>
          <div className="trial-step reveal">
            <div className="trial-step__number">4</div>
            <h3>Decide if it fits</h3>
            <p>Use the full platform for 14 days. Cancel anytime with one click.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── FAQ ────────────────────────────────────────────────────────────────────────
function FAQSection() {
  const faqs = [
    {
      q: 'Is it allowed to use AI to write a public-sector bid?',
      a: <>Yes. Cabinet Office guidance states that suppliers&rsquo; use of AI is not prohibited, but authorities may ask you to disclose it and to confirm the output was checked for accuracy. See <a href="https://www.gov.uk/government/publications/ppn-017-improving-transparency-of-ai-use-in-procurement/ppn-017-improving-transparency-of-ai-use-in-procurement-html" target="_blank" rel="noopener noreferrer">PPN 017</a>.</>,
    },
    {
      q: 'Where is my data processed?',
      a: 'The product is designed to run in the UK (AWS London), with AI inference routed only to providers and regions that meet our residency rules. Your documents are never used to train models. The public demo on this page processes files in memory and does not store them.',
    },
    {
      q: 'Which AI models do you use?',
      a: 'Only models that have passed our admission tests. We are provider-neutral; the admitted list and model cards will be published in our trust centre.',
    },
    {
      q: 'What happens to text I paste from elsewhere?',
      a: 'It is labelled "pasted, origin unknown" and counted separately in the AI use record. We do not guess where it came from.',
    },
    {
      q: 'What do founding members commit to?',
      a: 'Using tood.os on at least one real bid, and a short feedback call each month. In return you keep founding pricing for 12 months and shape the roadmap.',
    },
  ];
  return (
    <section className="sec" id="faq">
      <div className="wrap faq">
        <div>
          <p className="eyebrow">Questions</p>
          <h2 className="h2">Asked plainly. Answered plainly.</h2>
        </div>
        <div>
          {faqs.map((faq) => (
            <details key={faq.q}>
              <summary>{faq.q}<span className="plus" aria-hidden="true" /></summary>
              <p>{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── CTA / Join ────────────────────────────────────────────────────────────────
function CTASection() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  useGlyphCanvas(canvasRef, ctaRef, { rgb: '233,231,225', base: 0.05, band: '#3fd3a0', period: 9 });

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('SME bidding for contracts');
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [msgColor, setMsgColor] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
      setMsgColor('#ff8c9b'); setMessage('Please add your name and a valid work email.'); return;
    }
    setSubmitting(true);
    try {
      const r = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), email: email.trim(), company, role }),
      });
      if (!r.ok) throw new Error();
      setMsgColor(''); setMessage('Thank you. Your application is recorded and we will contact you personally.');
      setName(''); setEmail(''); setCompany(''); setRole('SME bidding for contracts');
    } catch {
      setMsgColor('#ff8c9b'); setMessage('We could not record your application just now. Please try again shortly.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="sec sec--tight" id="join">
      <div className="wrap">
        <div className="cta" ref={ctaRef}>
          <canvas className="cta__canvas" ref={canvasRef} aria-hidden="true" />
          <div className="cta__in">
            <div>
              <p className="eyebrow eyebrow--inv">Founding cohort</p>
              <h2 className="h2 h2--inv">Bid with AI. <em>Stand behind every word.</em></h2>
              <p className="cta__p">
                We are onboarding 30 UK companies that bid for public contracts. Tell us a little
                about you and we will be in touch personally.
              </p>
            </div>
            <form className="form" onSubmit={handleSubmit} noValidate>
              <div className="row">
                <div className="field">
                  <label htmlFor="f-name">Name</label>
                  <input id="f-name" name="name" autoComplete="name" required placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="f-email">Work email</label>
                  <input id="f-email" name="email" type="email" autoComplete="email" required placeholder="you@company.co.uk" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label htmlFor="f-co">Company</label>
                  <input id="f-co" name="company" autoComplete="organization" placeholder="Company name" value={company} onChange={(e) => setCompany(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="f-role">You are</label>
                  <select id="f-role" name="role" value={role} onChange={(e) => setRole(e.target.value)}>
                    <option>SME bidding for contracts</option>
                    <option>Freelance bid writer</option>
                    <option>Bid consultancy</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <button type="submit" disabled={submitting}>
                {submitting ? 'Sending…' : 'Apply for a founding place'}
              </button>
              {message && <p className="form__msg" role="status" style={{ color: msgColor || undefined }}>{message}</p>}
              <p className="form__fine">We use your details only to contact you about tood.os. No newsletters, no sharing.</p>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="footer">
      <div className="wrap">
        <div className="footer__in">
          <div>
            <a className="brand" href="#top" aria-label="tood.os home">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="3.5" y="3.5" width="17" height="17" rx="3.5" stroke="currentColor" strokeWidth="1.8" />
                <path d="M8 9h8M8 12.5h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                <circle cx="16" cy="16" r="2.2" fill="var(--color-primary)" />
              </svg>
              <span className="brand__word">tood<span>.</span>os</span>
            </a>
            <p style={{ marginTop: 'var(--space-3)', maxWidth: '36ch' }}>
              Verifiable, evidence-bound AI for UK public-sector bids.
            </p>
          </div>
          <div>
            <h4>Product</h4>
            <ul role="list">
              <li><a href="#live">Live demo</a></li>
              <li><a href="#inspect">Provenance</a></li>
              <li><a href="#record">AI use record</a></li>
              <li><a href="#pricing">Pricing</a></li>
            </ul>
          </div>
          <div>
            <h4>Trust</h4>
            <ul role="list">
              <li><a href="#standard">The standard</a></li>
              <li><a href="#standard">Model admission</a></li>
              <li><a href="#faq">Data &amp; residency</a></li>
            </ul>
          </div>
          <div>
            <h4>Guidance</h4>
            <ul role="list">
              <li><a href="https://www.gov.uk/government/publications/ppn-017-improving-transparency-of-ai-use-in-procurement/ppn-017-improving-transparency-of-ai-use-in-procurement-html" target="_blank" rel="noopener noreferrer">PPN 017 AI transparency</a></li>
              <li><a href="https://www.gov.uk/government/publications/ai-playbook-for-the-uk-government" target="_blank" rel="noopener noreferrer">UK Government AI Playbook</a></li>
              <li><a href="https://www.find-tender.service.gov.uk/Developer/Documentation" target="_blank" rel="noopener noreferrer">Find a Tender data</a></li>
            </ul>
          </div>
        </div>
        <div className="footer__base">
          <span>&copy; 2026 tood.os. Pre-launch.</span>
          <span>Sample companies and tenders on this page are fictional.</span>
        </div>
      </div>
    </footer>
  );
}

// ── Reveal observer ───────────────────────────────────────────────────────────
function useReveal() {
  useEffect(() => {
    const items = document.querySelectorAll<HTMLElement>('.reveal');
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            (e.target as HTMLElement).classList.add('is-in');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    items.forEach((el, i) => {
      const sib = Array.from(el.parentElement?.children ?? []).indexOf(el);
      el.style.transitionDelay = `${Math.min(sib * 60, 360)}ms`;
      io.observe(el);
    });
    return () => io.disconnect();
  }, []);
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function Page() {
  useReveal();
  return (
    <>
      <SkipLink />
      <AnnouncementBar />
      <Header />
      <main id="main">
        <HeroSection />
        <StatsBar />
        <MarqueeSection />
        <ProblemSection />
        <LiveDemoSection />
        <ProvenanceDemoSection />
        <StandardSection />
        <AIUseRecordSection />
        <ModelAdmissionBand />
        <LimitsSection />
        <PricingSection />
        <TrialHowItWorks />
        <FAQSection />
        <CTASection />
      </main>
      <Footer />
    </>
  );
}
