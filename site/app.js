'use strict';
(() => {
  const $ = (s) => document.querySelector(s);
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v; else n.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k != null) n.append(k);
    return n;
  };

  const PERIODS = [['full', 'Весь период'], ['2023', '2023'], ['2024', '2024'], ['2025', '2025'], ['2026', '2026']];
  const METRICS = [['return', 'Доходность'], ['dd', 'Просадка'], ['acc', 'Точность']];
  const BASES = [['hold', 'с удержанием'], ['momentum_7d', 'с импульсом']];
  const BASE_NAMES = { hold: 'Удержание', momentum_7d: 'Семидневный импульс' };
  const BASE_NOTES = { hold: 'всегда в активе', momentum_7d: 'в активе после роста за 7 дней' };
  const PERIOD_NOTES = { '2023': 'решения с марта', '2026': 'только январь и февраль' };
  const STATUS = {
    measured: ['Измерена', 'Полный прогон на всех заданиях'],
    pending: ['В очереди', 'Пробный запуск прошел, полный прогон впереди'],
    blocked: ['Нет доступа', 'Нет весов или доступа к ним'],
    incompatible: ['Несовместима', 'Модель решает другую задачу'],
    error: ['Ошибка', 'Прогон завершился ошибкой'],
  };
  const STATUS_ORDER = ['measured', 'pending', 'blocked', 'incompatible', 'error'];

  const nf = (d) => new Intl.NumberFormat('ru-RU', { minimumFractionDigits: d, maximumFractionDigits: d });
  const f0 = nf(0), f1 = nf(1), f2 = nf(2), f4 = nf(4);
  const signed = (v, fmt = f1) => { const s = fmt.format(Math.abs(v)); const zero = !/[1-9]/.test(s); return (zero ? '' : v > 0 ? '+' : '−') + s; };
  const pct = (v, fmt = f1) => signed(v, fmt) + '%';
  const median = (a) => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const ticker = (pair) => pair.replace(/USDT$/, '');

  const store = {
    get: (k, d) => { try { return localStorage.getItem('jbb.' + k) || d; } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem('jbb.' + k, v); } catch {} },
  };
  const state = { period: 'full', metric: 'return', base: 'hold', unit: store.get('latencyUnit', 'us') };
  let D;

  function seg(host, options, key, onChange) {
    host.replaceChildren(...options.map(([v, label]) => {
      const b = el('button', { type: 'button', role: 'radio', 'aria-checked': String(state[key] === v), text: label });
      b.addEventListener('click', () => { state[key] = v; host.querySelectorAll('button').forEach((x) => x.setAttribute('aria-checked', String(x === b))); onChange(); });
      return b;
    }));
  }

  // value of a metric for a run or baseline row; higher is better after orient()
  const value = (row, metric) => metric === 'return' ? row.return_pct : metric === 'dd' ? row.max_drawdown_pct : row.accuracy;
  const fmtValue = (v, metric) => v == null ? '—' : metric === 'return' ? pct(v) : metric === 'dd' ? f1.format(v) + '%' : f1.format(v * 100) + '%';
  const better = (a, b, metric) => metric === 'dd' ? b - a : a - b;

  function renderMatrix() {
    const { period, metric, base } = state;
    const models = D.models.filter((m) => m.status === 'measured');
    const runs = D.runs.filter((r) => r.period === period);
    const bases = D.baselines.filter((r) => r.period === period);
    const pairs = [...new Set(D.runs.map((r) => r.pair))].sort();
    const get = (list, key, id, pair) => list.find((r) => r[key] === id && r.pair === pair);

    const head = el('tr', {}, el('th', { scope: 'col', class: 'rowhead' }, el('span', { class: 'sr', text: 'Модель' })),
      pairs.map((p) => el('th', { scope: 'col' }, el('img', { src: 'https://logos.marketmaker.cc/coin-logos/sm/' + ticker(p).toLowerCase() + '.webp', alt: '', width: '22', height: '22', loading: 'lazy' }), el('span', { text: ticker(p) }))),
      el('th', { scope: 'col', class: 'sum' }, metric === 'acc' ? 'Все пары' : 'Медиана'));

    const baseRow = (name) => Object.fromEntries(pairs.map((p) => [p, get(bases, 'name', name, p)]));
    const ref = baseRow(base);
    const rows = [];
    const scale = metric === 'return' ? 120 : metric === 'dd' ? 25 : 0.08;

    const cell = (row, pair, isBase) => {
      const v = row ? value(row, metric) : null;
      const r = ref[pair];
      const rv = r ? value(r, metric) : null;
      let delta = null;
      if (v != null && metric !== 'acc' && rv != null && !(isBase === base)) delta = better(v, rv, metric);
      if (v != null && metric === 'acc') delta = v - 0.5;
      const t = delta == null ? 0 : Math.max(-1, Math.min(1, delta / scale));
      const td = el('td', { class: 'c' + (delta == null ? ' flat' : delta >= 0 ? ' up' : ' down'), style: '--t:' + Math.abs(t).toFixed(3) });
      td.append(el('span', { class: 'v', text: fmtValue(v, metric) }));
      if (row && metric !== 'acc' && delta != null) td.append(el('span', { class: 'd', text: (metric === 'return' ? signed(delta, f0) : signed(delta, f1)) + ' п.п.' }));
      if (row) td.title = ticker(pair) + ': доходность ' + pct(row.return_pct) + ', просадка ' + f1.format(row.max_drawdown_pct) + '%, сделок ' + row.trade_count + (row.accuracy != null ? ', точность ' + f1.format(row.accuracy * 100) + '%' : '');
      return [td, v, delta];
    };

    const summary = (vals, deltas, list) => {
      if (metric === 'acc') {
        const n = list.reduce((s, r) => s + (r ? r.n_decisions : 0), 0);
        const a = list.reduce((s, r) => s + (r ? r.accuracy * r.n_decisions : 0), 0);
        return el('td', { class: 'sum' }, el('span', { class: 'v', text: n ? f1.format(a / n * 100) + '%' : '—' }), n ? el('span', { class: 'd', text: f0.format(Math.round(a)) + ' из ' + f0.format(n) }) : null);
      }
      const vv = vals.filter((x) => x != null), dd = deltas.filter((x) => x != null);
      return el('td', { class: 'sum' }, el('span', { class: 'v', text: vv.length ? fmtValue(median(vv), metric) : '—' }),
        dd.length ? el('span', { class: 'd', text: 'лучше в ' + dd.filter((x) => x > 0).length + ' из ' + dd.length }) : null);
    };

    for (const m of models) {
      const list = pairs.map((p) => get(runs, 'model_id', m.id, p));
      const cells = list.map((r, i) => cell(r, pairs[i], false));
      rows.push(el('tr', {}, el('th', { scope: 'row', class: 'rowhead' }, el('span', { class: 'name', text: m.name })), cells.map((c) => c[0]), summary(cells.map((c) => c[1]), cells.map((c) => c[2]), list)));
    }
    if (metric !== 'acc') {
      rows.push(el('tr', { class: 'gap', 'aria-hidden': 'true' }, el('td', { colspan: String(pairs.length + 2) })));
      for (const name of ['hold', 'momentum_7d']) {
        const br = baseRow(name);
        const cells = pairs.map((p) => cell(br[p], p, name));
        rows.push(el('tr', { class: 'base' + (name === base ? ' ref' : '') }, el('th', { scope: 'row', class: 'rowhead' }, el('span', { class: 'name', text: BASE_NAMES[name] }), el('span', { class: 'sub', text: BASE_NOTES[name] }), name === base ? el('span', { class: 'tag', text: 'база сравнения' }) : null), cells.map((c) => c[0]), summary(cells.map((c) => c[1]), cells.map((c) => c[2]), [])));
      }
    }
    $('#matrix-table').replaceChildren(el('thead', {}, head), el('tbody', {}, rows));

    const pn = PERIOD_NOTES[period] ? ' В ' + period + ' году ' + PERIOD_NOTES[period] + '.' : '';
    $('#matrix-hint').textContent = (metric === 'acc'
      ? 'Доля верных прогнозов направления. Зеленый выше 50%, красный ниже. У простых правил точности нет, они не прогнозируют.'
      : metric === 'dd'
        ? 'Наибольшее падение капитала от пика. Под значением разница со строкой "' + BASE_NAMES[base] + '" в процентных пунктах: плюс значит, что просадка меньше.'
        : 'Доходность после издержек. Под значением разница со строкой "' + BASE_NAMES[base] + '" в процентных пунктах. Сравнивайте внутри одного столбца: у каждой пары свой капитал.') + pn;
  }

  function renderAccuracy() {
    const models = D.models.filter((m) => m.status === 'measured');
    const lat = (v) => v == null ? '—' : state.unit === 'us' ? f0.format(Math.round(v * 1000)) + ' мкс' : f0.format(v) + ' мс';
    const rows = models.map((m) => {
      const rs = D.runs.filter((r) => r.model_id === m.id && r.period === 'full');
      const n = rs.reduce((s, r) => s + r.n_decisions, 0);
      const hit = rs.reduce((s, r) => s + r.accuracy * r.n_decisions, 0);
      const br = rs.every((r) => r.brier != null) ? rs.reduce((s, r) => s + r.brier * r.n_decisions, 0) / n : null;
      const p50 = median(rs.map((r) => r.latency_ms_p50).filter((x) => x != null));
      return { m, n, hit, acc: hit / n, br, p50 };
    }).sort((a, b) => b.acc - a.acc);
    const head = el('tr', {}, el('th', { scope: 'col', text: 'Модель' }), el('th', { scope: 'col', text: 'Верных' }), el('th', { scope: 'col', text: 'Точность' }), el('th', { scope: 'col', text: 'Brier' }), el('th', { scope: 'col', text: 'Задержка p50' }));
    const body = rows.map((r) => el('tr', {},
      el('th', { scope: 'row', text: r.m.name }),
      el('td', { text: f0.format(Math.round(r.hit)) + ' из ' + f0.format(r.n) }),
      el('td', {}, el('span', { class: 'bar', style: '--w:' + (r.acc * 100).toFixed(2) + '%' }), el('span', { text: f2.format(r.acc * 100) + '%' })),
      el('td', { text: r.br == null ? 'нет вероятностей' : f4.format(r.br), class: r.br == null ? 'muted' : null }),
      el('td', { text: lat(r.p50) })));
    $('#acc-table').replaceChildren(el('thead', {}, head), el('tbody', {}, body), el('caption', { text: 'Задержка: медиана по девяти парам за весь период.' }));
  }

  function renderEngines() {
    const groups = STATUS_ORDER.map((s) => [s, D.models.filter((m) => m.status === s)]).filter(([, l]) => l.length);
    $('#engine-list').replaceChildren(...groups.map(([s, list]) => el('div', { class: 'group' },
      el('h3', {}, el('i', { class: 'dot ' + s }), STATUS[s][0], el('span', { class: 'count', text: String(list.length) })),
      el('p', { class: 'group-note', text: STATUS[s][1] }),
      el('ul', {}, list.map((m) => el('li', {},
        el('a', { href: m.source_url, rel: 'noopener', text: m.name }),
        m.source_sha ? el('code', { title: 'Закрепленная ревизия кода', text: m.source_sha.slice(0, 7) }) : el('code', { title: 'Ревизия не опубликована', text: 'API' }),
        m.reason ? el('p', { class: 'reason', lang: 'en', text: m.reason }) : null))))));
  }

  function renderParams() {
    const M = D.methodology;
    const items = [
      ['Задания', f0.format(D.provenance.event_count) + ' недельных решений на девяти парах'],
      ['Решение', 'понедельник 00:00 UTC, на следующие 7 дней'],
      ['Вход модели', '28 закрытых дневных свечей в относительных изменениях, без тикера, даты и цены'],
      ['Сделка', 'по цене открытия минуты 01:00 UTC в понедельник, выход через неделю в то же время'],
      ['Издержки', f2.format(M.fee_bps_per_side / 100) + '% комиссия и ' + f2.format(M.slippage_bps_per_side / 100) + '% проскальзывание на сторону'],
      ['Рынок', 'минутные свечи бессрочных USDT-фьючерсов Binance'],
      ['Портфель', 'у каждой пары свой капитал, вес от 0 до 1'],
    ];
    $('#params').replaceChildren(...items.map(([k, v]) => el('div', {}, el('dt', { text: k }), el('dd', { text: v }))));
  }

  function renderFacts() {
    const measured = D.models.filter((m) => m.status === 'measured').length;
    const when = new Date(D.generated_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
    $('#facts').textContent = 'Измерено ' + measured + ' модели из ' + D.models.length + ' в каталоге, ' + f0.format(D.provenance.event_count) + ' недельных заданий. Данные обновлены ' + when.replace(/ г\.$/, '') + '.';
  }

  async function boot() {
    try {
      const res = await fetch('./data/summary.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      D = await res.json();
    } catch (e) {
      $('#facts').textContent = 'Не удалось загрузить ./data/summary.json (' + e.message + '). Обновите страницу или откройте сводку на GitHub.';
      $('#matrix-table').replaceChildren(el('tbody', {}, el('tr', {}, el('td', { class: 'loading', text: 'Нет данных' }))));
      return;
    }
    renderFacts();
    seg($('#period-ctl'), PERIODS, 'period', renderMatrix);
    seg($('#metric-ctl'), METRICS, 'metric', renderMatrix);
    seg($('#base-ctl'), BASES, 'base', renderMatrix);
    seg($('#unit-ctl'), [['us', 'мкс'], ['ms', 'мс']], 'unit', () => { store.set('latencyUnit', state.unit); renderAccuracy(); });
    renderMatrix();
    document.body.classList.add('ready');
    renderAccuracy();
    renderEngines();
    renderParams();
    fetch('./version.txt').then((r) => r.ok ? r.text() : '').then((v) => { if (v) $('#version').textContent = 'Версия ' + v.trim(); }).catch(() => {});
  }
  boot();
})();
