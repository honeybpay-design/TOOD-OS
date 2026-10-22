(function () {
  'use strict';
  var root = document.documentElement;
  var RM = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------- theme ---------------- */
  var tbtn = document.querySelector('[data-theme-toggle]');
  var mode = matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';
  var SUN = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
  var MOON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  var themeListeners = [];
  function applyTheme() {
    root.setAttribute('data-theme', mode);
    tbtn.innerHTML = mode === 'dark' ? SUN : MOON;
    tbtn.setAttribute('aria-label', 'Switch to ' + (mode === 'dark' ? 'light' : 'dark') + ' mode');
    themeListeners.forEach(function (f) { f(); });
  }
  tbtn.addEventListener('click', function () { mode = mode === 'dark' ? 'light' : 'dark'; applyTheme(); });

  /* ---------------- header ---------------- */
  var header = document.querySelector('.header');
  addEventListener('scroll', function () { header.classList.toggle('is-scrolled', scrollY > 8); }, { passive: true });

  /* ---------------- hero headline split ---------------- */
  var h = document.querySelector('.hero__h');
  if (h && !RM) {
    var d = 0;
    (function walk(node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (n) {
        if (n.nodeType === 3) {
          var frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(function (w) {
            if (!w) return;
            if (/^\s+$/.test(w)) { frag.appendChild(document.createTextNode(w)); return; }
            var s = document.createElement('span'); s.className = 'w'; s.textContent = w;
            s.style.animationDelay = (0.08 + d * 0.07) + 's'; d++; frag.appendChild(s);
          });
          n.parentNode.replaceChild(frag, n);
        } else if (n.nodeType === 1 && n.tagName !== 'BR') walk(n);
      });
    })(h);
  }

  /* ---------------- glyph field canvas ---------------- */
  var SRC = 'The Supplier must hold a valid Cyber Essentials Plus certificate at the contract start date. Responses shall not exceed 750 words. The service must ensure no loss of service during core hours. Tenders must remain valid for 90 days. Social value weighting 10%. ';
  var PCOL = ['#2c8bd6', '#d39a1c', '#14b07f', '#d0664a'];
  function glyphField(canvas, opts) {
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var dpr = Math.min(devicePixelRatio || 1, 2);
    var cw = opts.cw || 8.4, ch = opts.ch || 19, cols, rows, cells = [], W, H;
    var mx = -999, my = -999, t0 = performance.now(), visible = true, raf;
    var rgb = '20,22,26', bandCol = '#0a7a5a', base = opts.base || 0.075;
    function readColor() {
      var cs = getComputedStyle(root); rgb = opts.rgb || cs.getPropertyValue('--glyph').trim() || '20,22,26'; bandCol = opts.band || cs.getPropertyValue('--color-primary').trim() || '#0a7a5a'; base = opts.base || (root.getAttribute('data-theme') === 'dark' ? 0.12 : 0.075);
    }
    function size() {
      var r = canvas.getBoundingClientRect(); W = r.width; H = r.height;
      canvas.width = W * dpr; canvas.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cols = Math.ceil(W / cw); rows = Math.ceil(H / ch); cells = [];
      for (var y = 0; y < rows; y++) for (var x = 0; x < cols; x++) {
        var c = SRC[(y * 37 + x) % SRC.length];
        cells.push({ c: c, m: 0, col: PCOL[(x * 7 + y * 13) % 4], seed: Math.random() });
      }
      ctx.font = '500 12px "JetBrains Mono", ui-monospace, monospace';
      ctx.textBaseline = 'top';
    }
    function frame(now) {
      raf = null;
      if (!visible) return;
      var t = (now - t0) / 1000;
      ctx.clearRect(0, 0, W, H);
      var period = opts.period || 7, bandW = W * 0.16;
      var bx = ((t % period) / period) * (W + bandW * 2) - bandW;
      for (var i = 0; i < cells.length; i++) {
        var cell = cells[i]; if (cell.c === ' ') continue;
        var x = (i % cols) * cw, y = Math.floor(i / cols) * ch;
        var a = base, dx = x - bx;
        var inBand = dx > -bandW && dx < 0;
        if (inBand) {
          var k = 1 + dx / bandW; a += 0.32 * k;
          if (cell.seed > 0.965 && cell.m < 0.2) cell.m = 1;
        }
        if (mx > -900) {
          var ddx = x - mx, ddy = y - my, dist = Math.sqrt(ddx * ddx + ddy * ddy);
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
          ctx.fillStyle = inBand ? bandCol : 'rgb(' + rgb + ')';
          ctx.fillText(cell.c, x + 2, y + 3);
        }
      }
      ctx.globalAlpha = 1;
      if (!RM) raf = requestAnimationFrame(frame);
    }
    function kick() { if (!raf) raf = requestAnimationFrame(frame); }
    readColor(); size(); kick();
    addEventListener('resize', function () { size(); kick(); });
    themeListeners.push(function () { readColor(); kick(); });
    var host = opts.host || canvas.parentElement;
    host.addEventListener('pointermove', function (e) { var r = canvas.getBoundingClientRect(); mx = e.clientX - r.left; my = e.clientY - r.top; if (RM) kick(); });
    host.addEventListener('pointerleave', function () { mx = my = -999; });
    new IntersectionObserver(function (es) { visible = es[0].isIntersecting; if (visible) kick(); }).observe(canvas);
  }

  /* ---------------- pipeline loop ---------------- */
  var pipe = document.getElementById('pipe');
  function runPipe() {
    if (!pipe) return;
    var cards = pipe.querySelectorAll('.pipe__card'), links = pipe.querySelectorAll('.pipe__link');
    var hls = pipe.querySelectorAll('.page .hl'), reqs = pipe.querySelectorAll('.reqs li'), ms = pipe.querySelectorAll('.mini .m');
    function reset() {
      pipe.classList.remove('is-run', 'is-sealed');
      [].forEach.call(cards, function (c) { c.classList.remove('is-act'); });
      [].forEach.call(links, function (l) { l.classList.remove('go'); });
      [].forEach.call(hls, function (e) { e.classList.remove('on'); });
      [].forEach.call(reqs, function (e) { e.classList.remove('on'); });
      [].forEach.call(ms, function (e) { e.classList.remove('on'); });
    }
    if (RM) { [].forEach.call(hls, function (e) { e.classList.add('on'); }); [].forEach.call(reqs, function (e) { e.classList.add('on'); }); [].forEach.call(ms, function (e) { e.classList.add('on'); }); pipe.classList.add('is-sealed'); return; }
    var timers = [];
    function at(ms_, f) { timers.push(setTimeout(f, ms_)); }
    function cycle() {
      timers.forEach(clearTimeout); timers = []; reset();
      void pipe.offsetWidth;
      at(100, function () { pipe.classList.add('is-run'); cards[0].classList.add('is-act'); });
      [].forEach.call(hls, function (e, i) { at(500 + i * 420, function () { e.classList.add('on'); }); });
      at(2500, function () { cards[0].classList.remove('is-act'); links[0].classList.add('go'); });
      at(3300, function () { cards[1].classList.add('is-act'); });
      [].forEach.call(reqs, function (e, i) { at(3400 + i * 380, function () { e.classList.add('on'); }); });
      at(5600, function () { cards[1].classList.remove('is-act'); links[1].classList.add('go'); });
      at(6400, function () { cards[2].classList.add('is-act'); });
      [].forEach.call(ms, function (e, i) { at(6500 + i * 520, function () { e.classList.add('on'); }); });
      at(8800, function () { pipe.classList.add('is-sealed'); cards[2].classList.remove('is-act'); });
      at(12500, cycle);
    }
    var started = false;
    new IntersectionObserver(function (es) { if (es[0].isIntersecting && !started) { started = true; cycle(); } }, { threshold: 0.3 }).observe(pipe);
  }

  /* ---------------- live demo ---------------- */
  var API = 'port/8000'.indexOf('__') === 0 ? 'http://localhost:8000' : 'port/8000';
  var $ = function (id) { return document.getElementById(id); };
  var runBtn = $('runSample'), fileIn = $('fileIn'), drop = $('drop');
  var stagesEl = $('stages'), timerEl = $('timer');
  var emptyEl = $('empty'), resEl = $('res'), errEl = $('err');
  var busy = false, tick = null, current = null, filter = 'all';
  var TYPE = { pass_fail: ['pass/fail', 'tag--pf'], scored: ['scored', 'tag--sc'], service_level: ['service', 'tag--sl'], deadline: ['deadline', 'tag--dl'], format: ['format', 'tag--fm'] };

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function setStage(s) {
    var order = ['parse', 'extract', 'verify'], idx = order.indexOf(s);
    stagesEl.querySelectorAll('.stage').forEach(function (el) {
      var i = order.indexOf(el.dataset.s);
      el.classList.toggle('is-on', i === idx); el.classList.toggle('is-done', s === 'done' || (idx > -1 && i < idx));
    });
  }
  function startTimer() { var t = performance.now(); clearInterval(tick); tick = setInterval(function () { timerEl.textContent = ((performance.now() - t) / 1000).toFixed(1) + 's elapsed'; }, 100); }
  function stopTimer(txt) { clearInterval(tick); timerEl.textContent = txt || ''; }
  function setBusy(b) { busy = b; runBtn.disabled = b; drop.style.pointerEvents = b ? 'none' : ''; drop.style.opacity = b ? .5 : ''; }
  function showErr(m) { emptyEl.hidden = true; resEl.hidden = true; errEl.hidden = false; errEl.textContent = m; }

  function poll(jid) {
    return new Promise(function (resolve, reject) {
      (function go() {
        fetch(API + '/api/jobs/' + jid).then(function (r) { return r.json(); }).then(function (j) {
          if (j.status === 'done') { setStage('done'); resolve(j.result); }
          else if (j.status === 'error') reject(new Error(j.error || 'Analysis failed'));
          else { setStage(j.stage === 'queued' ? 'parse' : j.stage); setTimeout(go, 900); }
        }).catch(reject);
      })();
    });
  }
  function begin(promise, fallback) {
    if (busy) return;
    setBusy(true); errEl.hidden = true; setStage('parse'); startTimer();
    emptyEl.hidden = false; resEl.hidden = true;
    promise.then(function (r) { if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || 'Upload failed'); }); return r.json(); })
      .then(function (j) { return poll(j.job_id); })
      .then(function (res) { stopTimer('Completed in ' + res.seconds + 's'); render(res, false); })
      .catch(function (e) {
        if (fallback && /fetch|network|Failed|Load/i.test(String(e))) {
          fetch('./samples/riverside-result.json').then(function (r) { return r.json(); }).then(function (res) { setStage('done'); stopTimer('Recorded run'); render(res, true); });
        } else { setStage(''); stopTimer(''); showErr(e.message || 'Analysis failed. Please try again.'); }
      })
      .finally(function () { setBusy(false); });
  }
  runBtn.addEventListener('click', function () { begin(fetch(API + '/api/analyse-sample?name=riverside', { method: 'POST' }), true); });
  function upload(f) {
    if (!f) return;
    if (f.type !== 'application/pdf' && !/\.pdf$/i.test(f.name)) { showErr('Please choose a PDF file.'); return; }
    if (f.size > 10 * 1024 * 1024) { showErr('That file is over 10 MB. Try a smaller PDF.'); return; }
    var fd = new FormData(); fd.append('file', f);
    begin(fetch(API + '/api/analyse', { method: 'POST', body: fd }), false);
  }
  fileIn.addEventListener('change', function () { upload(fileIn.files[0]); fileIn.value = ''; });
  ['dragenter', 'dragover'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('is-over'); }); });
  ['dragleave', 'drop'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('is-over'); }); });
  drop.addEventListener('drop', function (e) { upload(e.dataTransfer.files[0]); });

  function countUp(el, n) {
    if (RM) { el.textContent = n; return; }
    var t0 = performance.now(), dur = 900;
    (function f(now) { var p = Math.min(1, (now - t0) / dur); el.textContent = Math.round(n * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(f); })(t0);
  }

  function render(res, recorded) {
    current = res; filter = 'all';
    document.querySelectorAll('.chip').forEach(function (c) { c.classList.toggle('is-on', c.dataset.f === 'all'); });
    emptyEl.hidden = true; errEl.hidden = true; resEl.hidden = false;
    countUp($('kFound'), res.stats.found); countUp($('kVer'), res.stats.verified); countUp($('kRej'), res.stats.rejected); countUp($('kInj'), (res.injection || []).length);
    $('docName').textContent = res.name; $('docPage').textContent = res.pages.length + (res.pages.length === 1 ? ' page' : ' pages');
    // document with highlights
    var byPage = {};
    res.requirements.forEach(function (r) { if (r.verified) (byPage[r.page] = byPage[r.page] || []).push({ s: r.start, e: r.end, id: r.id, cls: '' }); });
    (res.injection || []).forEach(function (r, i) { if (r.verified) (byPage[r.page] = byPage[r.page] || []).push({ s: r.start, e: r.end, id: 'INJ-' + (i + 1), cls: 'inj' }); });
    var html = '';
    res.pages.forEach(function (p) {
      html += '<span class="doc__pg">Page ' + p.n + '</span>';
      var rs = (byPage[p.n] || []).sort(function (a, b) { return a.s - b.s || b.e - a.e; }), pos = 0;
      rs.forEach(function (r) {
        if (r.s < pos) return;
        html += esc(p.text.slice(pos, r.s)) + '<mark data-id="' + r.id + '" class="' + r.cls + '" title="' + r.id + '">' + esc(p.text.slice(r.s, r.e)) + '</mark>';
        pos = r.e;
      });
      html += esc(p.text.slice(pos));
    });
    $('docText').innerHTML = html; $('docText').scrollTop = 0;
    renderList();
    $('resMeta').textContent = (recorded ? 'Live analysis is unavailable right now, so this is a recorded run from ' + (res.cached_at || '6 Oct 2026') + '. ' : '') + 'Model: ' + res.model + ' · ' + res.seconds + 's · Quotes checked against the PDF text layer by code, not by the model.';
    if (innerWidth < 1100) document.getElementById('out').scrollIntoView({ behavior: RM ? 'auto' : 'smooth', block: 'start' });
  }
  function renderList() {
    var res = current; if (!res) return;
    var items = res.requirements.filter(function (r) { return filter === 'all' || r.type === filter; });
    var inj = (res.injection || []).map(function (r, i) { return { id: 'INJ-' + (i + 1), inj: true, summary: 'Hidden instruction to AI detected and ignored', verified: r.verified, page: r.page }; });
    if (filter === 'all') items = items.concat(inj);
    $('rlist').innerHTML = items.length ? items.map(function (r, i) {
      var t = r.inj ? ['injection', 'tag--dl'] : (TYPE[r.type] || [r.type, '']);
      var v = r.verified ? '<span class="rl__v ok">verified p.' + r.page + '</span>' : '<span class="rl__v no">rejected</span>';
      return '<li class="rl" data-id="' + r.id + '" style="animation-delay:' + Math.min(i * 35, 900) + 'ms" tabindex="0"><span class="rl__id">' + r.id + '</span><span class="rl__s">' + esc(r.summary) + '<br><span class="tag ' + t[1] + '">' + t[0] + '</span></span>' + v + '</li>';
    }).join('') : '<li class="rl" style="opacity:1;cursor:default"><span></span><span class="rl__s">None of this type in this document.</span></li>';
  }
  function select(id, fromDoc) {
    document.querySelectorAll('.rl.is-sel, .doc__text mark.is-sel').forEach(function (e) { e.classList.remove('is-sel'); });
    var li = document.querySelector('.rl[data-id="' + id + '"]'), mk = document.querySelector('.doc__text mark[data-id="' + id + '"]');
    if (li) { li.classList.add('is-sel'); if (fromDoc) li.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
    if (mk) { mk.classList.add('is-sel'); var dt = $('docText'); dt.scrollTo({ top: mk.offsetTop - dt.offsetTop - 80, behavior: RM ? 'auto' : 'smooth' }); }
  }
  $('rlist').addEventListener('click', function (e) { var li = e.target.closest('.rl[data-id]'); if (li) select(li.dataset.id); });
  $('rlist').addEventListener('keydown', function (e) { var li = e.target.closest('.rl[data-id]'); if (li && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(li.dataset.id); } });
  $('docText').addEventListener('click', function (e) { var m = e.target.closest('mark'); if (m) select(m.dataset.id, true); });
  document.querySelectorAll('.chip').forEach(function (c) { c.addEventListener('click', function () { filter = c.dataset.f; document.querySelectorAll('.chip').forEach(function (x) { x.classList.toggle('is-on', x === c); }); renderList(); }); });

  /* ---------------- provenance demo ---------------- */
  var DATA = {
    s1: { o: 'human', label: 'Person', rows: [['Author', 'Sarah Okafor, Bid Manager'], ['Created', '14 Sep 2026, 10:31'], ['Edits', '3 revisions'], ['Approved', 'S. Okafor, 16 Sep 17:05']], quote: 'Typed directly in the editor. No model involved.' },
    s2: { o: 'tender', label: 'Tender quote', rows: [['Source', '02_Specification.pdf'], ['Location', '§4.2, page 2'], ['Match', 'Verbatim, checked by code'], ['Requirement', 'R-010 (service level)']], quote: '“The service must ensure no loss of service during core hours (08:00-18:00) throughout transition and steady state.”' },
    s3: { o: 'ai', label: 'AI draft', rows: [['Model', 'Admitted model, card v3'], ['Prompt', 'answer.draft@14'], ['Evidence', 'EV-031 case study'], ['Edited by', 'S. Okafor (2 changes)'], ['Approved', 'S. Okafor, 16 Sep 17:05']], quote: 'Supported by EV-031: “Migrated 1,400 users to the new service desk over a weekend cut-over. No unplanned downtime recorded.”' },
    s4: { o: 'evidence', label: 'Evidence quote', rows: [['Evidence', 'EV-112 ISO/IEC 27001:2022'], ['Issuer', 'UKAS-accredited body'], ['Valid to', '14 Mar 2027'], ['Inserted by', 'J. Patel, 15 Sep 09:12']], quote: 'Certificate scope covers “IT service management and end-user support”.' },
    s5: { o: 'flag', label: 'Unsupported', rows: [['Model', 'Admitted model, card v3'], ['Prompt', 'answer.draft@14'], ['Evidence', 'None found'], ['Status', 'Blocks export']], quote: 'This sentence makes a factual commitment that no item in your evidence library supports. Remove it, or attach evidence and have a person approve it.' }
  };
  var answer = $('answer'), insp = $('inspector'), toggle = $('provToggle'), exportBar = $('exportBar'), exportText = $('exportText'), exportBtn = $('exportBtn'), flagSpan = $('flagSpan'), resolved = false;
  function show(k) {
    var d = DATA[k]; if (!d) return;
    answer.querySelectorAll('.span').forEach(function (s) { s.classList.toggle('is-active', s.dataset.k === k); });
    var html = '<div class="inspector__h fade-swap"><span class="badge" data-o="' + d.o + '">' + esc(d.label) + '</span><span class="mono muted" style="font-size:11px">span ' + k.replace('s', '#') + '</span></div>';
    html += '<dl class="kv fade-swap">' + d.rows.map(function (r) { return '<dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd>'; }).join('') + '</dl>';
    html += '<p class="quote fade-swap">' + esc(d.quote) + '</p>';
    if (k === 's5' && !resolved) html += '<div class="inspector__actions"><button class="btn btn--primary btn--sm" data-act="remove">Remove claim</button><button class="btn btn--ghost btn--sm" data-act="attach">Attach evidence</button></div>';
    html += '<p class="inspector__hint">Select any highlighted sentence to inspect its origin.</p>';
    insp.innerHTML = html;
  }
  function setExport(ok, msg) { exportBar.classList.toggle('is-ok', ok); exportText.textContent = msg; exportBtn.setAttribute('aria-disabled', ok ? 'false' : 'true'); }
  answer.addEventListener('click', function (e) { var s = e.target.closest('.span'); if (s) show(s.dataset.k); });
  answer.addEventListener('keydown', function (e) { var s = e.target.closest('.span'); if (s && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); show(s.dataset.k); } });
  insp.addEventListener('click', function (e) {
    var b = e.target.closest('[data-act]'); if (!b) return; resolved = true;
    if (b.dataset.act === 'remove') { flagSpan.classList.add('is-removed'); setExport(true, 'All claims traced. Ready to export with the AI use record.'); show('s1'); }
    else {
      flagSpan.dataset.o = 'ai'; flagSpan.textContent = 'We will meet the 99.5% availability target set out in the specification.';
      var c = document.createElement('span'); c.className = 'cite'; c.textContent = 'EV-118'; flagSpan.appendChild(c);
      DATA.s5 = { o: 'ai', label: 'AI draft', rows: [['Model', 'Admitted model, card v3'], ['Prompt', 'answer.draft@14'], ['Evidence', 'EV-118 SLA report 2025'], ['Approved', 'S. Okafor, just now']], quote: 'Claim rewritten to match evidence EV-118: “Measured availability 99.71% across 2025.”' };
      setExport(true, 'All claims traced. Ready to export with the AI use record.'); show('s5');
    }
  });
  exportBtn.addEventListener('click', function () { if (exportBtn.getAttribute('aria-disabled') === 'true') { show('s5'); flagSpan.focus(); return; } exportText.textContent = 'Demo only. In the product this exports DOCX plus the AI use record.'; });
  toggle.addEventListener('change', function () { answer.classList.toggle('is-prov', toggle.checked); });
  show('s3');

  /* ---------------- reveal ---------------- */
  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } });
  }, { threshold: 0.12 }) : null;
  document.querySelectorAll('.reveal').forEach(function (el, i) {
    var sib = el.parentElement ? [].indexOf.call(el.parentElement.children, el) : 0;
    el.style.transitionDelay = Math.min(sib * 60, 360) + 'ms';
    io ? io.observe(el) : el.classList.add('is-in');
  });

  /* ---------------- form ---------------- */
  var form = $('joinForm'), msg = $('formMsg');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var fd = new FormData(form), name = (fd.get('name') || '').trim(), email = (fd.get('email') || '').trim();
    if (!name || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { msg.style.color = '#ff8c9b'; msg.textContent = 'Please add your name and a valid work email.'; return; }
    var btn = form.querySelector('button'); btn.disabled = true; btn.textContent = 'Sending…';
    fetch(API + '/api/waitlist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name, email: email, company: fd.get('company') || '', role: fd.get('role') || '' }) })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function () { msg.style.color = ''; msg.textContent = 'Thank you. Your application is recorded and we will contact you personally.'; form.reset(); })
      .catch(function () { msg.style.color = '#ff8c9b'; msg.textContent = 'We could not record your application just now. Please try again shortly.'; })
      .finally(function () { btn.disabled = false; btn.textContent = 'Apply for a founding place'; });
  });

  /* ---------------- init ---------------- */
  applyTheme();
  glyphField(document.getElementById('glyphs'), { host: document.querySelector('.hero'), period: 7.5 });
  glyphField(document.getElementById('ctaGlyphs'), { rgb: '233,231,225', base: 0.05, band: '#3fd3a0', period: 9 });
  runPipe();
})();
