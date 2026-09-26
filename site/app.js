(() => {
  'use strict';

  const DATA_URL = './data/summary.json';
  const REPO_URL = 'https://github.com/suenot/jev-bots-bench';
  const statusLabels = {
    pending: 'В очереди',
    measured: 'Измерен',
    incompatible: 'Несовместим',
    blocked: 'Заблокирован',
    error: 'Ошибка',
  };
  const methodLabels = {
    dataset: 'Данные', data: 'Данные', data_source: 'Источник данных',
    source: 'Источник данных', exchange: 'Биржа', market: 'Рынок',
    pairs: 'Пары', period: 'Период', periods: 'Периоды',
    timeframe: 'Шаг данных', interval: 'Шаг данных',
    split: 'Разделение выборки', fees: 'Комиссии', costs: 'Издержки',
    slippage: 'Проскальзывание', latency: 'Задержка',
    execution: 'Исполнение', baseline: 'Базовая модель',
    baselines: 'Базовые модели', model: 'Модель',
    model_version: 'Версия модели', currency: 'Валюта',
    seed: 'Случайное зерно', notes: 'Примечания',
    fee_bps: 'Комиссия, б.п.', slippage_bps: 'Проскальзывание, б.п.',
    funding_bps: 'Фандинг, б.п.', source_url: 'Источник',
    max_model_latency_ms: 'Предел задержки модели, мс',
    drawdown_sampling: 'Частота отметок просадки',
    limitations: 'Ограничения', protocol: 'Протокол',
  };
  let dataset = null;

  const $ = (id) => document.getElementById(id);
  const node = (tag, className, content) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined && content !== null) element.textContent = String(content);
    return element;
  };
  const number = (value) => typeof value === 'number' && Number.isFinite(value);
  const text = (value) => typeof value === 'string' && value.trim() ? value.trim() : null;
  const safeLink = (value) => {
    try {
      const url = new URL(value);
      return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  };
  const fmt = (value, digits = 1) => new Intl.NumberFormat('ru-RU', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
  const metric = (value, suffix = '', digits = 1) => number(value) ? `${fmt(value, digits)}${suffix}` : '—';
  const yearOf = (period) => {
    const years = String(period || '').match(/\b20\d{2}\b/g)?.map(Number) || [];
    return years.length && years.every((year) => year === years[0]) ? years[0] : null;
  };
  const filtered = (items) => items.filter((item) => {
    const pair = $('pair-filter').value;
    const year = $('year-filter').value;
    return (!pair || item.pair === pair) && (!year || yearOf(item.period) === Number(year));
  });

  function empty(container, title, message, compact = false) {
    container.replaceChildren();
    const box = node('div', `empty-state${compact ? ' compact' : ''}`);
    box.append(node('span', 'empty-code', 'DATA / —'), node('h3', '', title), node('p', '', message));
    container.append(box);
  }

  function renderSnapshot(data) {
    const models = Array.isArray(data.models) ? data.models : [];
    const runs = Array.isArray(data.runs) ? data.runs : [];
    $('measured-count').textContent = String(models.filter((model) => model.status === 'measured').length);
    $('run-count').textContent = String(runs.length);
    const date = data.generated_at && new Date(data.generated_at);
    $('updated-at').textContent = date && !Number.isNaN(date.getTime())
      ? new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(date) + ' UTC'
      : 'Дата не указана';
  }

  function renderFilters(data) {
    const runs = Array.isArray(data.runs) ? data.runs : [];
    const baselines = Array.isArray(data.baselines) ? data.baselines : [];
    const all = [...runs, ...baselines];
    const pairs = [...new Set(all.map((item) => text(item.pair)).filter(Boolean))].sort();
    const years = [...new Set(all.map((item) => yearOf(item.period)).filter(Boolean))].sort((a, b) => b - a);
    const pairSelect = $('pair-filter');
    const yearSelect = $('year-filter');
    pairSelect.replaceChildren(node('option', '', 'Все пары'));
    yearSelect.replaceChildren(node('option', '', 'Все годы'));
    pairSelect.firstChild.value = '';
    yearSelect.firstChild.value = '';
    for (const pair of pairs) {
      const option = node('option', '', pair);
      option.value = pair;
      pairSelect.append(option);
    }
    for (const year of years) {
      const option = node('option', '', year);
      option.value = String(year);
      yearSelect.append(option);
    }
    pairSelect.disabled = !pairs.length;
    yearSelect.disabled = !years.length;
  }

  function makeTable(headers, rows, caption) {
    const outer = node('div', 'table-wrap');
    const table = node('table', 'data-table');
    const thead = node('thead');
    const headerRow = node('tr');
    for (const heading of headers) headerRow.append(node('th', '', heading));
    thead.append(headerRow);
    const tbody = node('tbody');
    for (const row of rows) tbody.append(row);
    table.append(thead, tbody);
    outer.append(table);
    if (caption) {
      const description = node('p', 'table-caption', caption);
      return [outer, description];
    }
    return [outer];
  }

  function valueCell(value, suffix = '', digits = 1) {
    return node('td', number(value) ? 'metric' : 'dash', metric(value, suffix, digits));
  }

  function renderRuns(data) {
    const container = $('results-content');
    container.replaceChildren();
    const runs = filtered(Array.isArray(data.runs) ? data.runs : []);
    const baselines = filtered(Array.isArray(data.baselines) ? data.baselines : []);
    const modelById = new Map((Array.isArray(data.models) ? data.models : []).map((model) => [model.id, model]));
    $('filter-count').textContent = `${runs.length} ${runs.length === 1 ? 'запуск' : 'запусков'} · ${baselines.length} базовых сравнений`;
    if (!runs.length) {
      empty(container, 'Измерений пока нет', data.status === 'complete'
        ? 'Для выбранных фильтров опубликованных прогонов нет. Проверьте другие пару или год и статусы движков ниже.'
        : 'Прогоны еще выполняются или не прошли проверку. Статус и причины по каждому движку указаны ниже.');
    } else {
      const rows = runs.map((run) => {
        const row = node('tr');
        const nameCell = node('td', 'row-name', modelById.get(run.model_id)?.name || run.model_id || 'Неизвестный движок');
        nameCell.append(node('span', 'subtext', `${text(run.pair) || 'Пара не указана'} · ${text(run.period) || 'Период не указан'}`));
        row.append(nameCell, valueCell(run.return_pct, '%'), valueCell(run.max_drawdown_pct, '%'), valueCell(run.accuracy === null || run.accuracy === undefined ? null : run.accuracy <= 1 ? run.accuracy * 100 : run.accuracy, '%'), valueCell(run.brier, '', 3), valueCell(run.n_decisions, '', 0), valueCell(run.trade_count, '', 0), valueCell(run.latency_ms_p50, ' мс', 0), valueCell(run.latency_ms_p95, ' мс', 0));
        return row;
      });
      container.append(...makeTable(['Движок / рынок / период', 'P&L после издержек', 'Просадка по неделям', 'Точность', 'Brier', 'Решений', 'Сделок', 'p50', 'p95'], rows, 'P&L и просадка по недельным отметкам — в процентах. Издержки указаны в методике. Точность и Brier относятся к задачам прогноза. «—» означает, что показатель не опубликован.'));
    }
    if (baselines.length) {
      const block = node('div', 'baseline-block');
      block.append(node('h3', '', 'Базовые сравнения'));
      const rows = baselines.map((baseline) => {
        const row = node('tr');
        const nameCell = node('td', 'row-name', text(baseline.name) || 'Базовая стратегия');
        nameCell.append(node('span', 'subtext', `${text(baseline.pair) || 'Пара не указана'} · ${text(baseline.period) || 'Период не указан'}`));
        row.append(nameCell, valueCell(baseline.return_pct, '%'), valueCell(baseline.max_drawdown_pct, '%'), valueCell(baseline.trade_count, '', 0));
        return row;
      });
      block.append(...makeTable(['Стратегия / рынок / период', 'P&L', 'Просадка по неделям', 'Сделок'], rows, 'Базовые строки представлены отдельно и не образуют общий рейтинг.'));
      container.append(block);
    }
    const comparisons = runs.flatMap((run) => baselines
      .filter((baseline) => baseline.pair === run.pair && baseline.period === run.period && number(run.return_pct) && number(baseline.return_pct))
      .map((baseline) => ({ run, baseline })));
    if (comparisons.length) {
      const block = node('div', 'baseline-block');
      block.append(node('h3', '', 'Сравнение на одной паре и периоде'));
      const rows = comparisons.map(({ run, baseline }) => {
        const row = node('tr');
        const model = modelById.get(run.model_id);
        row.append(node('td', 'row-name', model?.name || run.model_id || 'Неизвестный движок'));
        row.append(node('td', '', `${run.pair} · ${run.period}`));
        row.append(node('td', '', text(baseline.name) || 'Базовая стратегия'));
        row.append(valueCell(run.return_pct, '%'), valueCell(baseline.return_pct, '%'), valueCell(run.return_pct - baseline.return_pct, ' п.п.'));
        return row;
      });
      block.append(...makeTable(['Движок', 'Пара / период', 'База', 'P&L движка', 'P&L базы', 'Разница'], rows, 'Разница вычислена только для точно совпадающих пары и периода при наличии обоих измерений.'));
      container.append(block);
    }
  }

  function renderCoverage(data) {
    const container = $('coverage-content');
    container.replaceChildren();
    const models = Array.isArray(data.models) ? data.models : [];
    if (!models.length) {
      empty(container, 'Список движков не опубликован', 'Состав эксперимента появится после публикации summary.json.', true);
      return;
    }
    const list = node('div', 'model-list');
    for (const model of models) {
      const row = node('div', 'model-row');
      row.append(node('div', 'model-name', text(model.name) || text(model.id) || 'Без названия'));
      const status = statusLabels[model.status] ? model.status : 'pending';
      const pill = node('span', `status-pill ${status}`);
      pill.append(node('i', `status-dot ${status}`), node('span', '', statusLabels[status]));
      row.append(pill);
      row.append(node('div', 'model-reason', text(model.reason) || (status === 'measured' ? 'Есть опубликованные измерения.' : 'Причина пока не указана.')));
      const links = node('div', 'model-links');
      const source = safeLink(model.source_url);
      if (source) {
        const link = node('a', '', 'Исходный код ↗');
        link.href = source;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        links.append(link);
      } else links.append(node('span', 'subtext', 'Источник не указан'));
      const sha = text(model.source_sha);
      if (sha && source) {
        const link = node('a', '', `Commit ${sha.slice(0, 8)} ↗`);
        const url = new URL(source);
        const repoPath = url.pathname.replace(/\/$/, '').replace(/\.git$/, '');
        if (url.hostname === 'github.com') link.href = `${url.origin}${repoPath}/commit/${encodeURIComponent(sha)}`;
        else if (url.hostname === 'huggingface.co') link.href = `${url.origin}${repoPath}/tree/${encodeURIComponent(sha)}`;
        else link.href = source;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        links.append(link);
      }
      const weights = safeLink(model.weights_url);
      if (weights) {
        const link = node('a', '', 'Веса модели ↗');
        const url = new URL(weights);
        const revision = text(model.weights_sha);
        link.href = revision && url.hostname === 'huggingface.co'
          ? `${url.origin}${url.pathname.replace(/\/$/, '')}/tree/${encodeURIComponent(revision)}`
          : weights;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        links.append(link);
      }
      row.append(links);
      list.append(row);
    }
    container.append(list);
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === '') return null;
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (Array.isArray(value) && value.every((item) => item === null || typeof item !== 'object')) return value.map(displayValue).filter(Boolean).join(', ') || null;
    return null;
  }

  function methodologyEntries(value, path = []) {
    if (value === null || value === undefined) return [];
    const displayed = displayValue(value);
    if (displayed !== null) return [[path.map((key) => methodLabels[key] || key.replace(/_/g, ' ')).join(' / '), displayed]];
    if (typeof value !== 'object') return [];
    return Object.entries(value).flatMap(([key, child]) => methodologyEntries(child, [...path, key]));
  }

  function renderMethodology(data) {
    const list = $('methodology-content');
    list.replaceChildren();
    const methodology = data.methodology && typeof data.methodology === 'object' && !Array.isArray(data.methodology) ? data.methodology : {};
    const entries = methodologyEntries(methodology).filter(([, value]) => value);
    if (!entries.length) entries.push(['Состояние', 'Параметры ожидают публикации']);
    for (const [label, value] of entries) {
      const item = node('div');
      item.append(node('dt', '', label));
      const description = node('dd');
      const href = safeLink(value);
      if (href) {
        const link = node('a', '', value);
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        description.append(link);
      } else description.textContent = value;
      item.append(description);
      list.append(item);
    }
    const repo = document.querySelector('.method-links a');
    if (repo) repo.href = REPO_URL + '#readme';
  }

  async function init() {
    try {
      const response = await fetch(DATA_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.schema_version !== 1 || !Array.isArray(data.models) || !Array.isArray(data.runs)) throw new Error('Неподдерживаемая схема данных');
      dataset = data;
      renderSnapshot(data);
      renderFilters(data);
      renderRuns(data);
      renderCoverage(data);
      renderMethodology(data);
      $('pair-filter').addEventListener('change', () => renderRuns(dataset));
      $('year-filter').addEventListener('change', () => renderRuns(dataset));
    } catch (error) {
      $('measured-count').textContent = '—';
      $('run-count').textContent = '—';
      $('updated-at').textContent = 'Данные недоступны';
      $('filter-count').textContent = 'Файл не загружен';
      empty($('results-content'), 'Данные недоступны', 'Не удалось загрузить опубликованный summary.json. Попробуйте обновить страницу позже или откройте файл по ссылке ниже.');
      empty($('coverage-content'), 'Список временно недоступен', 'Состав движков опубликован вместе с файлом результатов.', true);
      console.error('Benchmark data load failed:', error);
    }
  }

  init();
})();
