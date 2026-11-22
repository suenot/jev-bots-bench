'use strict';
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v; else if (k === 'html') n.innerHTML = v; else n.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k != null) n.append(k);
    return n;
  };
  const SVGNS = 'http://www.w3.org/2000/svg';
  const sv = (tag, attrs = {}, text) => { const n = document.createElementNS(SVGNS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text != null) n.textContent = text; return n; };
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const store = {
    get: (k, d) => { try { return localStorage.getItem('jbb.' + k) || d; } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem('jbb.' + k, v); } catch {} },
  };

  /* ---------- language ---------- */
  let LANG = document.documentElement.lang === 'ru' ? 'ru' : 'en';
  const T = (ru, en) => LANG === 'en' ? en : ru;
  const RUS = {
    'nav.protocol': 'Протокол',
    'nav.matrix': 'Результаты',
    'nav.accuracy': 'Точность',
    'nav.catalog': 'Модели',
    'nav.method': 'Методика',
    'hero.kicker': 'проект marketmaker.cc',
    'hero.lead': 'Каждый понедельник модель видит 28 дневных свечей и отвечает одним словом: рост или падение. Мы посчитали, сколько это стоит в деньгах.',
    'hero.cta': 'Смотреть результаты',
    'pro.kicker': '01 / протокол',
    'pro.title': 'Одна неделя.<br><span class="accent">1 381 раз.</span>',
    'pro.aria': 'Анимация: свечи превращаются в ответ модели, ответ в недельную сделку, сделки в кривую капитала',
    'mx.kicker': '02 / результаты',
    'mx.title': 'Девять пар. <span class="accent">Одна таблица.</span>',
    'mx.period': 'Период',
    'mx.metric': 'Метрика',
    'mx.base': 'С чем сравнивать',
    'mx.note': 'Издержки: комиссия 0,05% и проскальзывание 0,04% на каждую сторону. Фандинг и спред не входят. Просадка считается по недельным отметкам. Годовые строки начинают капитал заново.',
    'ac.kicker': '03 / точность',
    'ac.title': 'Почти <span class="accent">монетка</span>.',
    'ac.lead': 'Доля недель, где модель угадала направление, по всем девяти парам вместе. Желтая строка не модель: она каждую неделю отвечает "вниз".',
    'ac.unit': 'Единицы задержки',
    'ac.side': 'Brier score: ошибка вероятностей, постоянные 50 на 50 дают 0,25, меньше значит лучше. Задержка: медиана по парам, у Kairos вместе с сетью до API.',
    'rk.kicker': '04 / точность и деньги',
    'rk.title': 'Точнее не значит <span class="accent">богаче</span>.',
    'rk.p': 'В подсчете точности каждая неделя весит одинаково. В портфеле итог за три года решают несколько крупных движений: модель, которая угадывает мелкие недели и пропускает большой рост, будет точной и бедной.',
    'ct.kicker': '05 / каталог',
    'ct.lead': 'Доходность появляется только после настоящего ответа модели на все задания. Ожидающие и несовместимые проекты не получают нулей и не исчезают из списка.',
    'me.kicker': '06 / методика',
    'me.title': 'Одинаково <span class="accent">для всех</span>.',
    'foot.by': 'Jev Bots Bench · проект <a href="https://marketmaker.cc" rel="noopener">marketmaker.cc</a>',
    'foot.note': 'Ретроспективное исследование. Не инвестиционный совет.',
  };
  // the HTML holds the English text; RUS holds the Russian one
  const ENS = {};
  const pick = (k) => LANG === 'ru' ? RUS[k] ?? ENS[k] : ENS[k];
  function applyStatic() {
    for (const n of $$('[data-i18n]')) { const k = n.dataset.i18n; ENS[k] ??= n.textContent; n.textContent = pick(k); }
    for (const n of $$('[data-i18n-html]')) { const k = n.dataset.i18nHtml; ENS[k] ??= n.innerHTML; n.innerHTML = pick(k); }
    for (const n of $$('[data-i18n-aria]')) { const k = n.dataset.i18nAria; ENS[k] ??= n.getAttribute('aria-label'); n.setAttribute('aria-label', pick(k)); }
    document.documentElement.lang = LANG;
    document.title = T('Jev Bots Bench: торговые модели против простого удержания', 'Jev Bots Bench: trading models against plain holding');
    $('#langBtn').textContent = LANG === 'en' ? 'RU' : 'EN';
    $('#langBtn').setAttribute('aria-label', T('Switch to English', 'Переключить на русский'));
  }

  /* ---------- theme ---------- */
  const ICON = {
    dark: '<svg viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
    light: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  };
  let PAL = {};
  function readPalette() {
    const cs = getComputedStyle(document.documentElement);
    const g = (k) => cs.getPropertyValue(k).trim();
    PAL = { bg: g('--bg'), bg2: g('--bg2'), ink: g('--ink'), ink2: g('--ink2'), dim: g('--dim'), line: g('--line'), acc: g('--acc'), hot: g('--hot'), cool: g('--cool'), amb: g('--amb'), vio: g('--vio'),
      accRgb: g('--acc-rgb'), hotRgb: g('--hot-rgb'), coolRgb: g('--cool-rgb'), fgRgb: g('--fg-rgb'), mono: g('--mono'), sans: g('--sans') };
  }
  function setTheme(t, save) {
    document.documentElement.dataset.theme = t; document.documentElement.style.colorScheme = t;
    if (save) store.set('theme', t);
    $('#themeBtn').innerHTML = ICON[t];
    $('#themeBtn').setAttribute('aria-label', t === 'dark' ? T('Светлая тема', 'Light theme') : T('Темная тема', 'Dark theme'));
    $('meta[name=theme-color]').setAttribute('content', t === 'dark' ? '#07080a' : '#f4f5f1');
    readPalette(); redrawStatic.forEach((f) => f());
  }
  const redrawStatic = [];

  /* ---------- numbers ---------- */
  const nf = (d) => new Intl.NumberFormat(LANG === 'en' ? 'en-US' : 'ru-RU', { minimumFractionDigits: d, maximumFractionDigits: d });
  let f0, f1, f2, f4;
  const setFormats = () => { f0 = nf(0); f1 = nf(1); f2 = nf(2); f4 = nf(4); };
  const signed = (v, fmt = f1) => { const s = fmt.format(Math.abs(v)); const zero = !/[1-9]/.test(s); return (zero ? '' : v > 0 ? '+' : '−') + s; };
  const pct = (v, fmt = f1) => signed(v, fmt) + '%';
  const median = (a) => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const ticker = (pair) => pair.replace(/USDT$/, '');
  const logo = (pair) => 'https://logos.marketmaker.cc/coin-logos/sm/' + ticker(pair).toLowerCase() + '.webp';
  const pp = () => T(' п.п.', ' pp');

  /* ---------- canvas helpers ---------- */
  function rng(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
  function setup(c) {
    const ctx = c.getContext('2d');
    const fit = () => { const r = c.getBoundingClientRect(); const d = Math.min(devicePixelRatio || 1, 2); c.width = Math.max(1, r.width * d); c.height = Math.max(1, r.height * d); ctx.setTransform(d, 0, 0, d, 0, 0); c._w = r.width; c._h = r.height; };
    fit(); new ResizeObserver(fit).observe(c);
    return ctx;
  }
  function loop(c, draw) {
    let on = false, raf = 0, t0 = performance.now();
    const tick = (t) => { draw((t - t0) / 1000); if (on) raf = requestAnimationFrame(tick); };
    new IntersectionObserver(([e]) => { on = e.isIntersecting && !RM; if (on) raf = requestAnimationFrame(tick); else cancelAnimationFrame(raf); }).observe(c);
    if (RM) requestAnimationFrame(() => draw(12));
  }
  const rgba = (rgb, a) => 'rgba(' + rgb + ',' + a + ')';

  /* ---------- state ---------- */
  const PERIODS = () => [['full', T('Весь период', 'Full period')], ['2023', '2023'], ['2024', '2024'], ['2025', '2025'], ['2026', '2026']];
  const METRICS = () => [['return', T('Доходность', 'Return')], ['dd', T('Просадка', 'Drawdown')], ['acc', T('Точность', 'Accuracy')]];
  const BASES = () => [['hold', T('с удержанием', 'vs hold')], ['momentum_7d', T('с импульсом', 'vs momentum')]];
  const BASE_NAMES = () => ({ hold: T('Удержание', 'Hold'), momentum_7d: T('Семидневный импульс', '7-day momentum') });
  const BASE_NOTES = () => ({ hold: T('всегда в активе', 'always in the asset'), momentum_7d: T('в активе после роста за 7 дней', 'in the asset after a 7-day gain') });
  const STATUS = () => ({
    measured: [T('Измерена', 'Measured'), T('Полный прогон на всех заданиях', 'Full run on every task')],
    pending: [T('В очереди', 'Queued'), T('Пробный запуск прошел, полный прогон впереди', 'Smoke test passed, full run ahead')],
    blocked: [T('Нет доступа', 'No access'), T('Нет весов или доступа к ним', 'Weights missing or not accessible')],
    incompatible: [T('Несовместима', 'Incompatible'), T('Модель решает другую задачу', 'The model solves a different task')],
    error: [T('Ошибка', 'Error'), T('Прогон завершился ошибкой', 'The run failed')],
  });
  const STATUS_ORDER = ['measured', 'pending', 'blocked', 'incompatible', 'error'];
  const state = { period: 'full', metric: 'return', base: 'hold', unit: store.get('latencyUnit', 'us') };
  let D, STATS;

  // per-model full-period aggregates, computed once from summary.json
  function computeStats() {
    const measured = D.models.filter((m) => m.status === 'measured');
    const full = D.runs.filter((r) => r.period === 'full');
    const hold = Object.fromEntries(D.baselines.filter((b) => b.period === 'full' && b.name === 'hold').map((b) => [b.pair, b]));
    const pairs = [...new Set(D.runs.map((r) => r.pair))].sort();
    const models = measured.map((m) => {
      const rs = full.filter((r) => r.model_id === m.id);
      const n = rs.reduce((s, r) => s + r.n_decisions, 0);
      const hit = rs.reduce((s, r) => s + r.accuracy * r.n_decisions, 0);
      const br = rs.length && rs.every((r) => r.brier != null) ? rs.reduce((s, r) => s + r.brier * r.n_decisions, 0) / n : null;
      const p50 = median(rs.map((r) => r.latency_ms_p50).filter((x) => x != null));
      const med = median(rs.map((r) => r.return_pct));
      const alwaysLong = rs.length === pairs.length && rs.every((r) => hold[r.pair] && Math.abs(r.return_pct - hold[r.pair].return_pct) < 1e-6);
      const byPair = Object.fromEntries(rs.map((r) => [r.pair, r]));
      return { m, n, hit, acc: n ? hit / n : 0, br, p50, med, alwaysLong, byPair };
    });
    // a model that is long every week has accuracy = share of up weeks, so "always down" = the rest
    const lng = models.find((x) => x.alwaysLong);
    const down = lng ? { n: lng.n, hit: lng.n - lng.hit, acc: 1 - lng.acc } : null;
    const byAcc = [...models].sort((a, b) => b.acc - a.acc);
    const byMed = [...models].sort((a, b) => b.med - a.med);
    const holdMed = median(pairs.map((p) => hold[p].return_pct));
    return { models, byAcc, byMed, down, pairs, hold, holdMed };
  }

  /* ---------- hero: endless weekly decisions over candles ---------- */
  function hero() {
    const c = $('#heroCanvas'), ctx = setup(c);
    const R = rng(7), candles = [], weeks = [];
    let price = 100;
    const ensure = (k) => {
      while (candles.length <= k) {
        const i = candles.length;
        if (i % 7 === 0) weeks.push({ long: R() > 0.42, p: 0.5 + (R() - 0.5) * 0.12 });
        const drift = (R() - 0.48) * 3.2, o = price, cl = price + drift;
        candles.push({ o, c: cl, h: Math.max(o, cl) + R() * 1.4, l: Math.min(o, cl) - R() * 1.4 });
        price = cl;
      }
    };
    let lo = 90, hi = 110;
    loop(c, (t) => {
      const W = c._w, H = c._h; ctx.clearRect(0, 0, W, H);
      const step = W < 700 ? 14 : 18, cw = step * 0.56, speed = 16;
      const off = t * speed, first = Math.floor(off / step), n = Math.ceil(W / step) + 2;
      ensure(first + n + 8);
      let mn = Infinity, mx = -Infinity;
      for (let k = first; k < first + n; k++) { mn = Math.min(mn, candles[k].l); mx = Math.max(mx, candles[k].h); }
      lo += (mn - lo) * 0.04; hi += (mx - hi) * 0.04;
      const top = H * 0.2, bot = H * 0.78, y = (v) => bot - (v - lo) / (hi - lo || 1) * (bot - top);
      const x = (k) => k * step - off;
      // weekly bands
      for (let w = Math.floor(first / 7); w * 7 < first + n; w++) {
        const wk = weeks[w]; if (!wk) continue;
        const x0 = x(w * 7) - step * 0.22, x1 = x(w * 7 + 7) - step * 0.22;
        ctx.fillStyle = wk.long ? rgba(PAL.accRgb, 0.07) : rgba(PAL.fgRgb, 0.015);
        ctx.fillRect(x0, top - 30, x1 - x0, bot - top + 60);
        ctx.strokeStyle = rgba(PAL.fgRgb, 0.07); ctx.beginPath(); ctx.moveTo(x0 + 0.5, top - 40); ctx.lineTo(x0 + 0.5, bot + 40); ctx.stroke();
        ctx.font = '11px ' + PAL.mono; ctx.fillStyle = wk.long ? PAL.acc : PAL.dim;
        ctx.fillText((wk.long ? '↑ ' : '↓ ') + (wk.long ? wk.p : 1 - wk.p).toFixed(2).replace('.', LANG === 'en' ? '.' : ','), x0 + 6, bot + 32);
      }
      for (let k = first; k < first + n; k++) {
        const cd = candles[k], up = cd.c >= cd.o, xx = x(k);
        ctx.strokeStyle = ctx.fillStyle = up ? rgba(PAL.accRgb, 0.75) : rgba(PAL.hotRgb, 0.7);
        ctx.beginPath(); ctx.moveTo(xx + cw / 2, y(cd.h)); ctx.lineTo(xx + cw / 2, y(cd.l)); ctx.stroke();
        const y0 = y(Math.max(cd.o, cd.c)); ctx.fillRect(xx, y0, cw, Math.max(1.5, y(Math.min(cd.o, cd.c)) - y0));
      }
    });
  }

  function heroTicker() {
    const tr = $('#tickerTrack');
    const items = STATS.pairs.map((p) => {
      const best = STATS.models.map((x) => [x, x.byPair[p]]).filter(([, r]) => r).sort((a, b) => b[1].return_pct - a[1].return_pct)[0];
      const h = STATS.hold[p].return_pct;
      return el('span', { class: best && best[1].return_pct < h ? 'bad' : null }, el('img', { src: logo(p), alt: '', width: '16', height: '16', loading: 'lazy' }), ticker(p),
        best ? el('span', {}, best[0].m.name, ' ', el('b', { text: pct(best[1].return_pct) })) : null,
        el('span', { class: 'dim' }, T('удержание ', 'hold ') + pct(h)));
    });
    tr.replaceChildren(...items, ...items.map((n) => n.cloneNode(true)));
    if (RM) return;
    let x = 0, last = performance.now();
    cancelAnimationFrame(tr._raf);
    const go = (t) => { x -= (t - last) * 0.035; last = t; const w = tr.scrollWidth / 2; if (-x > w) x += w; tr.style.transform = 'translateX(' + x + 'px)'; tr._raf = requestAnimationFrame(go); };
    tr._raf = requestAnimationFrame(go);
  }

  /* ---------- thesis ---------- */
  function thesis() {
    const a = STATS.byAcc[0], m = STATS.byMed[0], rank = STATS.byAcc.indexOf(m) + 1;
    const parts = [
      [T('Самая точная модель угадала', 'The most accurate model called'), false], [f2.format(a.acc * 100) + '%', true], [T('недель.', 'of weeks.'), false],
    ];
    if (STATS.down && STATS.down.hit > a.hit) parts.push([T('Ответ "вниз" каждую неделю угадал больше.', 'Answering "down" every week did better.'), false]);
    parts.push([T('Больше всего заработала', 'The most money went to'), false], [m.m.name + ',', true], [T('а по точности она ' + rank + '-я.', 'which ranks ' + ['', 'first', 'second', 'third', 'fourth', 'fifth'][rank] + ' on accuracy.'), false]);
    const host = $('#thesisText'); host.replaceChildren();
    for (const [txt, hl] of parts) for (const w of txt.split(' ')) host.append(el('span', { class: 'w' + (hl ? ' hl' : ''), text: w }), ' ');
  }

  /* ---------- pinned protocol ---------- */
  const PRO_STEPS = () => [
    [T('28 дневных свечей', '28 daily candles'), T('Понедельник, 00:00 UTC. Модель получает четыре недели закрытых дневных свечей.', 'Monday, 00:00 UTC. The model gets four weeks of closed daily candles.')],
    [T('Без имени и даты', 'No name, no date'), T('Тикер, дата и цена убраны. Остаются относительные изменения: доходность за 7 и 27 дней, волатильность, дневные шаги.', 'Ticker, date and price are removed. What remains are relative changes: 7- and 27-day returns, volatility, daily steps.')],
    [T('Один ответ', 'One answer'), T('Модель выбирает рост или падение. При ничьей бенчмарк считает ответ падением.', 'The model picks up or down. A tie counts as down.')],
    [T('Неделя в рынке', 'A week in the market'), T('Рост: держим актив с 01:00 понедельника до 01:00 следующего. Падение: стоим в деньгах. Комиссия и проскальзывание на каждой стороне.', 'Up: hold the asset from Monday 01:00 to the next Monday 01:00. Down: stay in cash. Fee and slippage on each side.')],
    [T('Три года, девять пар', 'Three years, nine pairs'), T('Так 1 381 раз. В конце сравниваем капитал модели с простым удержанием на каждой паре.', 'Repeat 1,381 times. Then compare the model capital with plain holding on each pair.')],
  ];
  function protocol() {
    const c = $('#proCanvas'), ctx = setup(c);
    const R = rng(23), cs = []; let p0 = 100;
    for (let i = 0; i < 28; i++) { const d = (R() - 0.5) * 5 - (i > 20 ? 1.5 : 0) + (i < 10 ? 0.6 : 0); const o = p0, cl = p0 * (1 + d / 100); cs.push({ o, c: cl, h: Math.max(o, cl) * (1 + R() * 0.015), l: Math.min(o, cl) * (1 - R() * 0.015) }); p0 = cl; }
    const legend = $('#proLegend'), text = $('#proText');
    let phase = -1, prog = 0;
    const setPhase = (k) => {
      if (k === phase) return; phase = k;
      const S = PRO_STEPS();
      text.textContent = S[k][1];
      legend.replaceChildren(...S.map((s, i) => el('li', { class: i === k ? 'on' : null }, el('b', { text: String(i + 1) }), s[0])));
    };
    const clamp = (v) => Math.max(0, Math.min(1, v));
    const ease = (v) => v * v * (3 - 2 * v);
    const draw = (p) => {
      prog = p; setPhase(Math.min(4, Math.floor(p * 5)));
      const W = c._w, H = c._h; ctx.clearRect(0, 0, W, H);
      const pad = Math.max(18, W * 0.06), L = pad, Rr = W - pad, top = H * 0.16, bot = H * 0.62;
      const ph = (a, b) => ease(clamp((p - a) / (b - a)));
      const appear = ph(0, 0.14), toRet = ph(0.22, 0.36), answer = ph(0.42, 0.56), trade = ph(0.62, 0.76), zoom = ph(0.8, 0.92);
      ctx.save(); ctx.globalAlpha = 1 - zoom;
      const mn = Math.min(...cs.map((x) => x.l)), mx = Math.max(...cs.map((x) => x.h));
      const cw = (Rr - L) / 28 * (trade > 0 ? 0.62 : 0.6), step = (Rr - L) * (1 - 0.32 * trade) / 28;
      const yP = (v) => bot - (v - mn) / (mx - mn) * (bot - top);
      const mid = (top + bot) / 2, yR = (r) => mid - r * (bot - top) * 6;
      ctx.font = '12px ' + PAL.mono;
      // identity labels that get struck out
      ctx.fillStyle = PAL.ink2; ctx.globalAlpha = (1 - zoom) * appear * (1 - toRet * 0.85);
      ctx.fillText(T('BCH/USDT · 6 марта 2023 · $' + cs[27].c.toFixed(1).replace('.', ','), 'BCH/USDT · 6 March 2023 · $' + cs[27].c.toFixed(1)), L, top - 26);
      if (toRet > 0) { ctx.globalAlpha = (1 - zoom) * toRet; ctx.strokeStyle = PAL.hot; ctx.lineWidth = 2; const tw = ctx.measureText(T('BCH/USDT · 6 марта 2023 · $00,0', 'BCH/USDT · 6 March 2023 · $00.0')).width; ctx.beginPath(); ctx.moveTo(L, top - 30); ctx.lineTo(L + tw * toRet, top - 30); ctx.stroke(); ctx.fillStyle = PAL.acc; ctx.fillText(T('вход модели: 28 относительных изменений', 'model input: 28 relative changes'), L, top - 8); }
      ctx.globalAlpha = 1 - zoom; ctx.lineWidth = 1.4;
      for (let i = 0; i < 28; i++) {
        const k = clamp(appear * 28 - i); if (k <= 0) break;
        const x = cs[i], up = x.c >= x.o, xx = L + i * step;
        const r = x.c / x.o - 1;
        const yo = yP(x.o) * (1 - toRet) + mid * toRet, yc = yP(x.c) * (1 - toRet) + yR(r) * toRet;
        ctx.strokeStyle = ctx.fillStyle = up ? PAL.acc : PAL.hot;
        ctx.globalAlpha = (1 - zoom) * k;
        if (toRet < 1) { ctx.globalAlpha *= 1 - toRet; ctx.beginPath(); ctx.moveTo(xx + cw / 2, yP(x.h)); ctx.lineTo(xx + cw / 2, yP(x.l)); ctx.stroke(); ctx.globalAlpha = (1 - zoom) * k; }
        const a = Math.min(yo, yc), h = Math.max(2, Math.abs(yo - yc));
        ctx.fillRect(xx, a, cw, h);
      }
      if (toRet > 0) { ctx.globalAlpha = (1 - zoom) * toRet * 0.6; ctx.strokeStyle = PAL.dim; ctx.setLineDash([4, 6]); ctx.beginPath(); ctx.moveTo(L, mid); ctx.lineTo(L + 28 * step, mid); ctx.stroke(); ctx.setLineDash([]); }
      // model answer
      const ax = L + 28 * step + 16;
      if (answer > 0) {
        ctx.globalAlpha = (1 - zoom) * answer;
        const bx = Math.min(Rr - 150, ax + 10), by = top;
        ctx.strokeStyle = PAL.amb; ctx.lineWidth = 2; roundRect(ctx, bx, by, 150, 44, 22); ctx.stroke();
        ctx.fillStyle = PAL.amb; ctx.font = '600 15px ' + PAL.mono; ctx.textAlign = 'center'; ctx.fillText('Kairos', bx + 75, by + 28); ctx.textAlign = 'left';
        const bars = [[T('рост', 'up'), 0.5, PAL.acc], [T('падение', 'down'), 0.5, PAL.hot]];
        ctx.font = '12px ' + PAL.mono;
        bars.forEach(([lab, v, col], i) => { const yy = by + 70 + i * 34; ctx.fillStyle = rgba(PAL.fgRgb, 0.06); ctx.fillRect(bx, yy, 150, 18); ctx.fillStyle = col; ctx.fillRect(bx, yy, 150 * v * answer, 18); ctx.fillStyle = PAL.ink2; ctx.fillText(lab + ' ' + (LANG === 'en' ? '0.50' : '0,50'), bx, yy - 5); });
        const ch = ph(0.5, 0.58); ctx.globalAlpha = (1 - zoom) * ch;
        ctx.fillStyle = PAL.ink; ctx.font = '600 13px ' + PAL.mono; ctx.fillText(T('ничья → вниз, в деньгах', 'tie → down, cash'), bx, by + 156);
      }
      // trade timeline below
      if (trade > 0) {
        ctx.globalAlpha = (1 - zoom) * trade;
        const ty = H * 0.78, tx0 = L, tx1 = Rr;
        ctx.strokeStyle = PAL.line; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(tx0, ty); ctx.lineTo(tx0 + (tx1 - tx0) * trade, ty); ctx.stroke();
        const marks = [[0, T('пн 00:00 решение', 'Mon 00:00 decision')], [0.06, T('01:00 вход', '01:00 entry')], [1, T('пн 01:00 выход', 'Mon 01:00 exit')]];
        ctx.font = '11px ' + PAL.mono;
        marks.forEach(([f, lab], i) => { if (f > trade) return; const xx = tx0 + (tx1 - tx0) * f; ctx.fillStyle = i === 0 ? PAL.amb : PAL.ink2; ctx.beginPath(); ctx.arc(xx, ty, 4, 0, 7); ctx.fill(); ctx.textAlign = i === 2 ? 'right' : 'left'; ctx.fillText(lab, xx + (i === 2 ? 0 : 0), ty + (i === 1 ? -12 : 22)); ctx.textAlign = 'left'; });
        const days = 7; ctx.fillStyle = PAL.dim;
        for (let d = 1; d < days; d++) { const xx = tx0 + (tx1 - tx0) * (0.06 + 0.94 * d / days); if (xx > tx0 + (tx1 - tx0) * trade) break; ctx.fillRect(xx, ty - 3, 1, 6); }
        ctx.fillStyle = PAL.ink; ctx.font = '600 13px ' + PAL.mono;
        if (trade > 0.9) ctx.fillText(T('BCH за неделю −2,05%, модель в деньгах: 0%', 'BCH over the week −2.05%, model in cash: 0%'), tx0, ty + 48);
      }
      ctx.restore();
      // zoom out: real final returns per pair
      if (zoom > 0) drawPairs(ctx, W, H, zoom, ph(0.84, 0.95));
    };
    const drawPairs = (ctx, W, H, a, grow) => {
      const k = STATS.models.find((x) => /kairos/i.test(x.m.id)) || STATS.byAcc[0];
      ctx.save(); ctx.globalAlpha = a;
      const pad = Math.max(18, W * 0.06), L = pad, Rr = W - pad, n = STATS.pairs.length, slot = (Rr - L) / n;
      const vals = STATS.pairs.flatMap((p) => [k.byPair[p]?.return_pct ?? 0, STATS.hold[p].return_pct]);
      const vmax = Math.max(...vals), vmin = Math.min(0, ...vals), top = H * 0.16, bot = H * 0.8;
      const y = (v) => top + (vmax - v) / (vmax - vmin) * (bot - top), y0 = y(0);
      ctx.font = '12px ' + PAL.mono; ctx.fillStyle = PAL.ink2;
      ctx.fillText(k.m.name + T(' и удержание, весь период', ' and hold, full period'), L, top - 30);
      ctx.fillStyle = PAL.acc; ctx.fillRect(L, top - 16, 10, 10); ctx.fillStyle = PAL.ink2; ctx.fillText(k.m.name, L + 16, top - 7);
      const lx = L + 16 + ctx.measureText(k.m.name).width + 22;
      ctx.fillStyle = rgba(PAL.coolRgb, 0.55); ctx.fillRect(lx, top - 16, 10, 10); ctx.fillStyle = PAL.ink2; ctx.fillText(T('удержание', 'hold'), lx + 16, top - 7);
      ctx.strokeStyle = PAL.line; ctx.beginPath(); ctx.moveTo(L, y0); ctx.lineTo(Rr, y0); ctx.stroke();
      const bw = Math.min(26, slot * 0.32);
      STATS.pairs.forEach((p, i) => {
        const cx = L + slot * (i + 0.5), g = clamp(grow * 1.5 - i * 0.06);
        const kv = (k.byPair[p]?.return_pct ?? 0) * g, hv = STATS.hold[p].return_pct * g;
        ctx.fillStyle = PAL.acc; ctx.fillRect(cx - bw - 2, Math.min(y0, y(kv)), bw, Math.max(1, Math.abs(y(kv) - y0)));
        ctx.fillStyle = rgba(PAL.coolRgb, 0.55); ctx.fillRect(cx + 2, Math.min(y0, y(hv)), bw, Math.max(1, Math.abs(y(hv) - y0)));
        ctx.fillStyle = PAL.ink2; ctx.textAlign = 'center'; ctx.fillText(ticker(p), cx, bot + 26);
        if (g >= 1) { const win = (k.byPair[p]?.return_pct ?? -Infinity) > STATS.hold[p].return_pct; ctx.fillStyle = win ? PAL.acc : PAL.dim; ctx.fillText(win ? '●' : '·', cx, bot + 46); }
        ctx.textAlign = 'left';
      });
      ctx.restore();
    };
    redrawStatic.push(() => draw(prog));
    if (RM || !window.ScrollTrigger) { draw(0.95); new ResizeObserver(() => draw(prog)).observe(c); return; }
    ScrollTrigger.create({ trigger: '#protocol', start: 'top top', end: 'bottom bottom', scrub: true, onUpdate: (s) => draw(s.progress), onRefresh: (s) => draw(s.progress) });
    new ResizeObserver(() => requestAnimationFrame(() => draw(prog))).observe(c);
    draw(0);
  }
  function roundRect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

  /* ---------- results matrix ---------- */
  function seg(host, options, key, onChange) {
    host.replaceChildren(...options.map(([v, label]) => {
      const b = el('button', { type: 'button', role: 'radio', 'aria-checked': String(state[key] === v), text: label });
      b.addEventListener('click', () => { state[key] = v; host.querySelectorAll('button').forEach((x) => x.setAttribute('aria-checked', String(x === b))); onChange(); });
      return b;
    }));
  }
  const value = (row, metric) => metric === 'return' ? row.return_pct : metric === 'dd' ? row.max_drawdown_pct : row.accuracy;
  const fmtValue = (v, metric) => v == null ? '—' : metric === 'return' ? pct(v) : metric === 'dd' ? f1.format(v) + '%' : f1.format(v * 100) + '%';
  const better = (a, b, metric) => metric === 'dd' ? b - a : a - b;
  function renderMatrix() {
    const { period, metric, base } = state;
    const models = D.models.filter((m) => m.status === 'measured');
    const runs = D.runs.filter((r) => r.period === period);
    const bases = D.baselines.filter((r) => r.period === period);
    const pairs = STATS.pairs;
    const get = (list, key, id, pair) => list.find((r) => r[key] === id && r.pair === pair);
    const head = el('tr', {}, el('th', { scope: 'col', class: 'rowhead' }, el('span', { class: 'sr', text: T('Модель', 'Model') })),
      pairs.map((p) => el('th', { scope: 'col' }, el('img', { src: logo(p), alt: '', width: '22', height: '22', loading: 'lazy' }), el('span', { text: ticker(p) }))),
      el('th', { scope: 'col', class: 'sum' }, metric === 'acc' ? T('Все пары', 'All pairs') : T('Медиана', 'Median')));
    const baseRow = (name) => Object.fromEntries(pairs.map((p) => [p, get(bases, 'name', name, p)]));
    const ref = baseRow(base);
    const scale = metric === 'return' ? 120 : metric === 'dd' ? 25 : 0.08;
    const cell = (row, pair, isBase) => {
      const v = row ? value(row, metric) : null, r = ref[pair], rv = r ? value(r, metric) : null;
      let delta = null;
      if (v != null && metric !== 'acc' && rv != null && isBase !== base) delta = better(v, rv, metric);
      if (v != null && metric === 'acc') delta = v - 0.5;
      const t = delta == null ? 0 : Math.max(-1, Math.min(1, delta / scale));
      const td = el('td', { class: 'c' + (delta == null ? ' flat' : delta >= 0 ? ' up' : ' down'), style: '--t:' + Math.abs(t).toFixed(3) });
      td.append(el('span', { class: 'v', text: fmtValue(v, metric) }));
      if (row && metric !== 'acc' && delta != null) td.append(el('span', { class: 'd', text: (metric === 'return' ? signed(delta, f0) : signed(delta, f1)) + pp() }));
      if (row) td.title = ticker(pair) + ': ' + T('доходность ', 'return ') + pct(row.return_pct) + T(', просадка ', ', drawdown ') + f1.format(row.max_drawdown_pct) + T('%, сделок ', '%, trades ') + row.trade_count + (row.accuracy != null ? T(', точность ', ', accuracy ') + f1.format(row.accuracy * 100) + '%' : '');
      return [td, v, delta];
    };
    const summary = (vals, deltas, list) => {
      if (metric === 'acc') {
        const n = list.reduce((s, r) => s + (r ? r.n_decisions : 0), 0), a = list.reduce((s, r) => s + (r ? r.accuracy * r.n_decisions : 0), 0);
        return el('td', { class: 'sum' }, el('span', { class: 'v', text: n ? f1.format(a / n * 100) + '%' : '—' }), n ? el('span', { class: 'd', text: f0.format(Math.round(a)) + T(' из ', ' of ') + f0.format(n) }) : null);
      }
      const vv = vals.filter((x) => x != null), dd = deltas.filter((x) => x != null);
      return el('td', { class: 'sum' }, el('span', { class: 'v', text: vv.length ? fmtValue(median(vv), metric) : '—' }),
        dd.length ? el('span', { class: 'd', text: T('лучше в ', 'better in ') + dd.filter((x) => x > 0).length + T(' из ', ' of ') + dd.length }) : null);
    };
    const rows = [];
    for (const m of models) {
      const list = pairs.map((p) => get(runs, 'model_id', m.id, p));
      const cells = list.map((r, i) => cell(r, pairs[i], false));
      rows.push(el('tr', {}, el('th', { scope: 'row', class: 'rowhead' }, el('span', { class: 'name', text: m.name })), cells.map((c) => c[0]), summary(cells.map((c) => c[1]), cells.map((c) => c[2]), list)));
    }
    if (metric !== 'acc') {
      rows.push(el('tr', { class: 'gap', 'aria-hidden': 'true' }, el('td', { colspan: String(pairs.length + 2) })));
      for (const name of ['hold', 'momentum_7d']) {
        const br = baseRow(name), cells = pairs.map((p) => cell(br[p], p, name));
        rows.push(el('tr', { class: 'base' + (name === base ? ' ref' : '') }, el('th', { scope: 'row', class: 'rowhead' }, el('span', { class: 'name', text: BASE_NAMES()[name] }), el('span', { class: 'sub', text: BASE_NOTES()[name] }), name === base ? el('span', { class: 'tag', text: T('база сравнения', 'reference') }) : null), cells.map((c) => c[0]), summary(cells.map((c) => c[1]), cells.map((c) => c[2]), [])));
      }
    }
    $('#matrix-table').replaceChildren(el('thead', {}, head), el('tbody', {}, rows));
    const PN = { '2023': T('решения с марта', 'decisions start in March'), '2026': T('только январь и февраль', 'January and February only') };
    const pn = PN[period] ? ' ' + T('В ' + period + ' году ', 'In ' + period + ', ') + PN[period] + '.' : '';
    const bn = BASE_NAMES()[base];
    $('#matrix-hint').textContent = (metric === 'acc'
      ? T('Доля верных прогнозов направления. Зеленый выше 50%, красный ниже. У простых правил точности нет, они не прогнозируют.', 'Share of correct direction calls. Green is above 50%, red below. Simple rules have no accuracy: they do not forecast.')
      : metric === 'dd'
        ? T('Наибольшее падение капитала от пика. Под значением разница со строкой "' + bn + '" в процентных пунктах: плюс значит, что просадка меньше.', 'Largest fall of capital from its peak. Below each value: difference to the "' + bn + '" row in percentage points; plus means a smaller drawdown.')
        : T('Доходность после издержек. Под значением разница со строкой "' + bn + '" в процентных пунктах. Сравнивайте внутри одного столбца: у каждой пары свой капитал.', 'Return after costs. Below each value: difference to the "' + bn + '" row in percentage points. Compare within a column: each pair has its own capital.')) + pn;
  }

  /* ---------- accuracy race ---------- */
  function renderRace() {
    const rows = STATS.byAcc.map((x) => ({ name: x.m.name, acc: x.acc, hit: x.hit, n: x.n }));
    if (STATS.down) rows.push({ name: T('Всегда "вниз"', 'Always "down"'), acc: STATS.down.acc, hit: STATS.down.hit, n: STATS.down.n, cst: true });
    rows.sort((a, b) => b.acc - a.acc);
    const lo = Math.floor((Math.min(...rows.map((r) => r.acc)) - 0.02) * 100) / 100, hi = Math.ceil((Math.max(...rows.map((r) => r.acc)) + 0.005) * 100) / 100;
    const w = (v) => (v - lo) / (hi - lo) * 100;
    const topModel = rows.find((r) => !r.cst);
    const host = $('#race');
    host.replaceChildren(...rows.map((r) => el('div', { class: 'row' + (r.cst ? ' const' : '') + (r === topModel ? ' top' : '') },
      el('span', { class: 'nm', text: r.name }),
      el('span', { class: 'track' }, el('span', { class: 'fill', style: '--w:' + w(r.acc).toFixed(2) + '%' })),
      el('span', { class: 'val' }, el('b', { text: f2.format(r.acc * 100) + '%' }), f0.format(Math.round(r.hit)) + T(' из ', ' of ') + f0.format(r.n)))));
    const track = $('.track', host);
    const coin = el('span', { class: 'coin' }, el('span', { text: T('50%, монетка', '50%, coin flip') }));
    host.append(coin, el('span', { class: 'axis', style: 'bottom:0', text: T('шкала ', 'axis ') + f0.format(lo * 100) + '–' + f0.format(hi * 100) + '%' }));
    const place = () => { const tr = track.getBoundingClientRect(), hr = host.getBoundingClientRect(); coin.style.left = (tr.left - hr.left + tr.width * w(0.5) / 100) + 'px'; $('.axis', host).style.left = (tr.left - hr.left) + 'px'; };
    place(); new ResizeObserver(place).observe(host);
    if (!RM && window.gsap) gsap.fromTo($$('.fill', host), { scaleX: 0 }, { scaleX: 1, duration: 1.4, ease: 'power3.out', stagger: 0.12, scrollTrigger: { trigger: host, start: 'top 75%' } });
  }
  function renderAccTable() {
    const lat = (v) => v == null ? '—' : state.unit === 'us' ? f0.format(Math.round(v * 1000)) + T(' мкс', ' µs') : f0.format(v) + T(' мс', ' ms');
    const head = el('tr', {}, ...[T('Модель', 'Model'), 'Brier', T('Задержка p50', 'Latency p50')].map((t) => el('th', { scope: 'col', text: t })));
    const body = STATS.byAcc.map((r) => el('tr', {}, el('th', { scope: 'row', text: r.m.name }),
      el('td', { text: r.br == null ? T('нет вероятностей', 'no probabilities') : f4.format(r.br), class: r.br == null ? 'muted' : null }),
      el('td', { text: lat(r.p50) })));
    $('#acc-table').replaceChildren(el('thead', {}, head), el('tbody', {}, body));
  }

  /* ---------- ranks slope ---------- */
  function renderRanks() {
    const host = $('#rankStage');
    const hw = host.clientWidth - 2 * parseFloat(getComputedStyle(host).paddingLeft || 0);
    const mob = hw < 640;
    const W = mob ? Math.max(280, hw) : 1000, rowH = mob ? 62 : 78, n = STATS.models.length, H = (mob ? 84 : 96) + n * rowH;
    host._w = host.clientWidth;
    const COL = [PAL.acc, PAL.amb, PAL.cool, PAL.vio, PAL.hot];
    const color = Object.fromEntries(STATS.byMed.map((x, i) => [x.m.id, COL[i % COL.length]]));
    const s = sv('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': T('Места моделей по точности и по медианной доходности', 'Model ranks by accuracy and by median return') });
    const cw = mob ? Math.floor((W - 40) / 2) : 380, xL = 0, xR = W - cw, y = (i) => (mob ? 52 : 70) + i * rowH + rowH / 2 - 8;
    s.append(sv('text', { x: xL, y: 24, class: 'lbl', style: mob ? 'font-size:11px' : null }, T('точность', 'accuracy')), sv('text', { x: W, y: 24, class: 'lbl', 'text-anchor': 'end', style: mob ? 'font-size:11px' : null }, T('медиана', 'median return')));
    const card = (x, i, name, val, col) => {
      const g = sv('g');
      if (mob) {
        g.append(sv('rect', { x: x + 1, y: y(i) - 24, width: cw - 2, height: 50, rx: 10, fill: 'none', stroke: col, 'stroke-width': 1.5 }));
        g.append(sv('text', { x: x + 10, y: y(i) - 4, 'font-size': 12.5, 'font-weight': 700 }, name));
        g.append(sv('text', { x: x + 10, y: y(i) + 15, 'font-size': 12, class: 'mono', fill: col }, val));
        return g;
      }
      g.append(sv('rect', { x, y: y(i) - 28, width: cw, height: 56, rx: 12, fill: 'none', stroke: col, 'stroke-width': 2 }));
      g.append(sv('text', { x: x + 18, y: y(i) + 7, 'font-size': 21, 'font-weight': 700 }, name));
      g.append(sv('text', { x: x + cw - 18, y: y(i) + 7, 'font-size': 17, 'text-anchor': 'end', class: 'mono', fill: col }, val));
      return g;
    };
    const right = [];
    STATS.byAcc.forEach((x, i) => s.append(card(xL, i, x.m.name, f2.format(x.acc * 100) + '%', color[x.m.id])));
    const paths = [];
    STATS.byAcc.forEach((x, i) => {
      const j = STATS.byMed.indexOf(x), x0 = xL + cw + 6, x1 = xR - 6, mx = (x0 + x1) / 2;
      const pth = sv('path', { d: 'M' + x0 + ' ' + y(i) + ' C' + mx + ' ' + y(i) + ' ' + mx + ' ' + y(j) + ' ' + x1 + ' ' + y(j), fill: 'none', stroke: color[x.m.id], 'stroke-width': mob ? 3 : 5, 'stroke-linecap': 'round' });
      s.append(pth); paths.push(pth);
    });
    STATS.byMed.forEach((x, j) => { const g = card(xR, j, x.m.name, pct(x.med), color[x.m.id]); g.classList.add('rk-r'); s.append(g); right.push(g); });
    const hm = sv('text', { x: W, y: H - 4, 'text-anchor': 'end', class: 'mono', 'font-size': mob ? 11 : 14, fill: PAL.dim }, T('удержание: медиана ', 'hold: median ') + pct(STATS.holdMed));
    s.append(hm);
    host.replaceChildren(s);
    // squeeze names that do not fit their card
    $$('g text:nth-of-type(1)', s).forEach((t) => { const max = cw - (mob ? 18 : 120); if (t.getComputedTextLength() > max) { t.setAttribute('textLength', max); t.setAttribute('lengthAdjust', 'spacingAndGlyphs'); } });
    if (RM || !window.gsap) return;
    paths.forEach((p) => { const L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; });
    const tl = gsap.timeline({ scrollTrigger: { trigger: host, start: 'top 70%' } });
    tl.from(right, { opacity: 0, x: 30, duration: 0.6, stagger: 0.15 }).to(paths, { strokeDashoffset: 0, duration: 1.1, ease: 'power2.inOut', stagger: 0.18 }, 0.2);
  }

  /* ---------- catalog ---------- */
  function renderCatalog() {
    const measured = D.models.filter((m) => m.status === 'measured').length;
    $('#catTitle').innerHTML = T(measured + ' из ' + D.models.length + ' моделей <span class="accent">измерены</span>.', measured + ' of ' + D.models.length + ' models <span class="accent">measured</span>.');
    const St = STATUS();
    const sorted = [...D.models].sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status));
    const cards = sorted.map((m) => {
      const s = STATS.models.find((x) => x.m.id === m.id);
      const c = el('article', { class: 'card ' + m.status + (m.status !== 'measured' ? ' dimmed' : '') },
        el('span', { class: 'st' }, el('i'), St[m.status]?.[0] ?? m.status),
        el('h3', {}, el('a', { href: m.source_url, rel: 'noopener', text: m.name })),
        s ? el('div', { class: 'nums' },
          el('span', {}, el('b', { class: s.med > 0 ? 'pos' : null, text: pct(s.med) }), T('медиана', 'median')),
          el('span', {}, el('b', { text: f1.format(s.acc * 100) + '%' }), T('точность', 'accuracy'))) : null,
        m.reason ? el('p', { class: 'reason', lang: 'en', text: m.reason }) : el('p', { class: 'reason', text: St[m.status]?.[1] ?? '' }),
        m.source_sha ? el('code', { title: T('Закрепленная ревизия кода', 'Pinned source revision'), text: 'src ' + m.source_sha.slice(0, 7) + (m.weights_sha ? ' · w ' + m.weights_sha.slice(0, 7) : '') }) : el('code', { text: T('API, ревизия не публикуется', 'API, revision not published') }));
      c.addEventListener('pointermove', (e) => { const r = c.getBoundingClientRect(); c.style.setProperty('--mx', (e.clientX - r.left) + 'px'); c.style.setProperty('--my', (e.clientY - r.top) + 'px'); });
      return c;
    });
    $('#cards').replaceChildren(...cards);
  }

  /* ---------- method ---------- */
  function renderMethod() {
    const M = D.methodology;
    const items = [
      [T('Задания', 'Tasks'), T(f0.format(D.provenance.event_count) + ' недельных решений на ' + STATS.pairs.length + ' парах', f0.format(D.provenance.event_count) + ' weekly decisions on ' + STATS.pairs.length + ' pairs')],
      [T('Решение', 'Decision'), T('понедельник 00:00 UTC, на следующие 7 дней', 'Monday 00:00 UTC, for the next 7 days')],
      [T('Вход модели', 'Model input'), T('28 закрытых дневных свечей в относительных изменениях, без тикера, даты и цены', '28 closed daily candles as relative changes, no ticker, date or price')],
      [T('Сделка', 'Fill'), T('по цене открытия минуты 01:00 UTC в понедельник, выход через неделю в то же время', 'at the open of the Monday 01:00 UTC minute, exit a week later at the same time')],
      [T('Издержки', 'Costs'), T(f2.format(M.fee_bps_per_side / 100) + '% комиссия и ' + f2.format(M.slippage_bps_per_side / 100) + '% проскальзывание на сторону', f2.format(M.fee_bps_per_side / 100) + '% fee and ' + f2.format(M.slippage_bps_per_side / 100) + '% slippage per side')],
      [T('Рынок', 'Market'), T('минутные свечи бессрочных USDT-фьючерсов Binance', 'minute candles of Binance USDT perpetual futures')],
      [T('Портфель', 'Portfolio'), T('у каждой пары свой капитал, вес от 0 до 1', 'each pair has its own capital, weight from 0 to 1')],
      [T('Честность', 'Caveat'), T('ретроспективная проверка: даты отсечения обучающих данных моделей неизвестны', 'retrospective test: model training cutoffs are unknown')],
    ];
    $('#params').replaceChildren(...items.map(([k, v]) => el('div', {}, el('dt', { text: k }), el('dd', { text: v }))));
    const G = 'https://github.com/suenot/jev-bots-bench/';
    const refs = [
      ['README', T('Протокол бенчмарка', 'Benchmark protocol'), T('правила, данные и проверки утечек', 'rules, data and leakage checks'), G + 'blob/main/benchmark/README.md'],
      ['summary.json', T('Итоговая таблица', 'Summary table'), T('все цифры этой страницы', 'every number on this page'), G + 'blob/main/results/summary.json'],
      ['responses/', T('Ответы моделей', 'Model responses'), T('каждый ответ на каждое задание', 'every answer to every task'), G + 'tree/main/results/responses'],
      ['provenance', T('Сведения о моделях', 'Model provenance'), T('ревизии кода, весов и условия прогона', 'code and weight revisions, run conditions'), G + 'blob/main/results/model-provenance.json'],
      ['CHANGELOG', T('История изменений', 'Changelog'), T('что и когда менялось', 'what changed and when'), G + 'blob/main/CHANGELOG.md'],
    ];
    $('#refs').replaceChildren(...refs.map(([id, b, t, href]) => el('li', {}, el('a', { href, rel: 'noopener' }, el('span', { class: 'id', text: id }), el('span', {}, el('b', { text: b }), el('span', { class: 't', text: t }))))));
  }

  /* ---------- text bits ---------- */
  function renderFacts() {
    const when = new Date(D.generated_at).toLocaleDateString(LANG === 'en' ? 'en-GB' : 'ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).replace(/ г\.$/, '');
    $('#heroFacts').textContent = T(STATS.models.length + ' модели · ' + f0.format(D.provenance.event_count) + ' недель · данные от ' + when, STATS.models.length + ' models · ' + f0.format(D.provenance.event_count) + ' weeks · data of ' + when);
  }

  /* ---------- motion ---------- */
  function motion() {
    const bar = $('#progress');
    const onScroll = () => { const h = document.documentElement; bar.style.transform = 'scaleX(' + (h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight)) + ')'; };
    addEventListener('scroll', onScroll, { passive: true }); onScroll();
    if (RM || !window.gsap) return;
    gsap.registerPlugin(ScrollTrigger);
    gsap.from('#heroTitle span', { yPercent: 110, opacity: 0, duration: 1.1, ease: 'power4.out', stagger: 0.12 });
    gsap.from(['.hero-logo', '.hero .kicker', '#heroLead', '.hero-cta'], { y: 24, opacity: 0, duration: 0.9, ease: 'power3.out', stagger: 0.08, delay: 0.25 });
    gsap.to('.hero-inner', { yPercent: -18, opacity: 0.2, ease: 'none', scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } });
    $$('main .h-big').forEach((h) => gsap.from(h, { y: 50, opacity: 0, duration: 1, ease: 'power3.out', scrollTrigger: { trigger: h, start: 'top 85%' } }));
  }
  function thesisMotion() {
    if (RM || !window.gsap) return;
    ScrollTrigger.getById('thesis')?.kill();
    gsap.to('#thesisText .w', { opacity: 1, stagger: 0.08, ease: 'none', scrollTrigger: { id: 'thesis', trigger: '#thesis', start: 'top 70%', end: 'bottom 60%', scrub: true } });
  }

  /* ---------- boot ---------- */
  function renderData() {
    setFormats();
    STATS = computeStats();
    renderFacts(); heroTicker(); thesis(); thesisMotion();
    seg($('#period-ctl'), PERIODS(), 'period', renderMatrix);
    seg($('#metric-ctl'), METRICS(), 'metric', renderMatrix);
    seg($('#base-ctl'), BASES(), 'base', renderMatrix);
    seg($('#unit-ctl'), [['us', T('мкс', 'µs')], ['ms', T('мс', 'ms')]], 'unit', () => { store.set('latencyUnit', state.unit); renderAccTable(); });
    renderMatrix(); renderRace(); renderAccTable(); renderRanks(); renderCatalog(); renderMethod();
  }
  async function boot() {
    setFormats(); applyStatic(); readPalette();
    setTheme(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark', false);
    $('#themeBtn').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true));
    $('#langBtn').addEventListener('click', () => {
      LANG = LANG === 'en' ? 'ru' : 'en'; store.set('lang', LANG); applyStatic();
      setTheme(document.documentElement.dataset.theme, false);
      if (D) { renderData(); window.ScrollTrigger && ScrollTrigger.refresh(); }
    });
    if (window.gsap) gsap.registerPlugin(ScrollTrigger);
    hero(); motion();
    try {
      const res = await fetch('./data/summary.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      D = await res.json();
    } catch (e) {
      $('#heroFacts').textContent = T('Не удалось загрузить данные (' + e.message + '). Обновите страницу.', 'Could not load the data (' + e.message + '). Reload the page.');
      return;
    }
    renderData(); protocol();
    redrawStatic.push(() => renderRanks());
    let rt = 0; new ResizeObserver(() => { const h = $('#rankStage'); if (h._w && Math.abs(h.clientWidth - h._w) > 4) { clearTimeout(rt); rt = setTimeout(renderRanks, 150); } }).observe($('#rankStage'));
    fetch('./version.txt').then((r) => r.ok ? r.text() : '').then((v) => { if (v) $('#version').textContent = 'v' + v.trim(); }).catch(() => {});
    window.ScrollTrigger && ScrollTrigger.refresh();
  }
  boot();
})();
