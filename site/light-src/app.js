/* 只呈現 Python 已產生的選源、點值、座標與線段；不在此計算統計值。 */
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const assetBase = new URL('./', document.baseURI);
  const cache = new Map();
  const queryKeys = ['mode', 'profile', 'entity', 'indicator', 'q', 'series', 'from', 'to'];
  const initialQuery = new URLSearchParams(window.location.search);
  const state = {
    manifest: null, catalog: null, series: null,
    mode: initialQuery.get('mode') === 'original' ? 'original' : 'profile',
    profileId: initialQuery.get('profile') || '',
    entity: initialQuery.get('entity') || '', indicator: initialQuery.get('indicator') || '',
    search: initialQuery.get('q') || '', seriesId: initialQuery.get('series') || '',
    from: initialQuery.get('from') || '', to: initialQuery.get('to') || '',
    selection: null, selectedKeys: null, shownRecords: [], detailKey: '',
    serial: 0, controller: null, retry: null
  };
  const labels = {
    selected_original_scope: '選用原刊限定範圍',
    selected_with_limits: '已選來源・仍有條件限制',
    selected_source_fact: '選定來源・原期間事實',
    selected_source_missing: '選定來源・原值缺漏',
    selected_source_unusable: '選定來源・點值不可用',
    selected: '依既定政策選用',
    selected_source: '已選用來源',
    selected_source_bundle: '已選用來源組',
    selected_source_panel: '已選用原刊面板',
    selected_one_source_bundle: '已選用單一來源組',
    published_panel_limited: '原刊範圍內有限對照',
    source_series_only: '原來源系列・未認證跨年連線',
    range_not_covered_by_one_panel: '沒有單一原刊面板涵蓋此期間',
    no_qualified_panel: '沒有合格原刊面板',
    no_qualified_source: '沒有符合條件的來源',
    no_default_profile_for_original_scope: '此原範圍沒有預設問題',
    no_match: '沒有符合結果',
    ambiguous_priority: '同優先序未能擇一',
    unresolved: '必要條件未解', incompatible: '指定接續操作拒用',
    source_blank: '原來源空白', source_missing: '原來源缺值',
    missing: '缺值', unknown: '未知', unusable: '點值不可用',
    reported: '原報值', observed: '原報值', present: '原欄有值',
    numeric: '原欄數值', source_zero: '原來源記零', reported_zero: '原報零值',
    source_reported_zero: '原來源記零', not_applicable: '不適用',
    source_symbol: '原來源符號', source_dash: '原來源橫線符號',
    blocked_scope: '原範圍不符', blocked_period: '原期間不符',
    blocked_source_version: '來源版本未通過',
    alternative_source_version: '其他候選版本',
    unreviewed_source_version: '來源新版本待覆核'
  };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function textValue(value) {
    if (value === undefined) return '（未提供）';
    if (value === null) return 'null（未知）';
    if (value === '') return '（空字串）';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  }

  function statusLabel(value) {
    if (value === null || value === undefined || value === '') return '狀態未提供';
    if (typeof value !== 'string') return textValue(value);
    return labels[value] || value;
  }

  function officialURL(value) {
    if (typeof value !== 'string' || !/^https?:\/\//i.test(value)) return null;
    try {
      const url = new URL(value);
      return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch { return null; }
  }

  function linkURL(value) {
    if (typeof value !== 'string' || !value) return null;
    try {
      const url = new URL(value, assetBase);
      return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch { return null; }
  }

  function localAssetURL(value) {
    if (typeof value !== 'string' || !value || /^[a-z][a-z\d+.-]*:/i.test(value) || /^[\/\\]/.test(value)) {
      throw new Error('資料目錄中的檔案路徑不符合本站相對路徑規則。');
    }
    const url = new URL(value, assetBase);
    if (url.origin !== assetBase.origin || !url.pathname.startsWith(assetBase.pathname) || url.username || url.password || url.search || url.hash) {
      throw new Error('資料檔路徑超出本閱覽器的資料目錄。');
    }
    return url.href;
  }

  function externalLink(value, title, className = '', officialOnly = false) {
    const href = officialOnly ? officialURL(value) : linkURL(value);
    if (!href) return element('span', className, title);
    const link = element('a', className, title);
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    return link;
  }

  function setLink(id, value) {
    const node = $(id), href = linkURL(value);
    node.hidden = !href;
    if (href) node.href = href;
    else node.removeAttribute('href');
  }

  async function loadJSON(path, signal) {
    const url = localAssetURL(path);
    if (signal.aborted) throw new DOMException('查詢已變更', 'AbortError');
    if (cache.has(url)) return cache.get(url);
    const response = await fetch(url, { signal, credentials: 'same-origin' });
    if (!response.ok) throw new Error(`資料檔未能讀取（HTTP ${response.status}）。`);
    const data = await response.json();
    if (!data || data.schema_version !== 1) throw new Error('資料檔格式版本不符合此閱覽器。');
    if (signal.aborted) throw new DOMException('查詢已變更', 'AbortError');
    cache.set(url, data);
    return data;
  }

  function beginRequest() {
    if (state.controller) state.controller.abort();
    state.controller = new AbortController();
    state.serial += 1;
    return { serial: state.serial, signal: state.controller.signal };
  }

  function current(request) { return request.serial === state.serial && !request.signal.aborted; }

  function showStatus(message, kind = '', retry = null) {
    $('status').hidden = !message;
    $('status').className = `status-box${kind ? ` is-${kind}` : ''}`;
    $('status-message').textContent = message;
    $('retry').hidden = !retry;
    state.retry = retry;
  }

  function clearResults() {
    state.series = null;
    state.shownRecords = [];
    state.detailKey = '';
    $('result').hidden = true;
    $('record-detail').hidden = true;
    $('chart').replaceChildren();
    $('records-body').replaceChildren();
    $('series-scope').replaceChildren();
    setLink('full-data-link', null);
  }

  function catalogControls(disabled) {
    for (const id of ['entity', 'indicator', 'search', 'series', 'from', 'to', 'reset-period']) $(id).disabled = disabled;
  }

  function option(value, label) {
    const node = document.createElement('option');
    node.value = String(value);
    node.textContent = label === undefined ? String(value) : label;
    return node;
  }

  function setOptions(id, values, emptyLabel, selected, keepUnknown = false) {
    const node = $(id), fragment = document.createDocumentFragment();
    if (emptyLabel !== null) fragment.append(option('', emptyLabel));
    for (const value of values) fragment.append(option(value));
    if (keepUnknown && selected && !values.map(String).includes(String(selected))) {
      fragment.append(option(selected, `${selected}（本範圍未列）`));
    }
    node.replaceChildren(fragment);
    node.value = selected || '';
  }

  function distinct(items, key) {
    return [...new Set(items.map((item) => item[key]).filter((value) => value !== undefined && value !== null && value !== '').map(String))]
      .sort((a, b) => a.localeCompare(b, 'zh-Hant', { numeric: true }));
  }

  function updateURL() {
    const url = new URL(window.location.href);
    for (const key of queryKeys) url.searchParams.delete(key);
    const values = {
      mode: state.mode,
      profile: state.mode === 'profile' ? state.profileId : '',
      entity: state.entity, indicator: state.indicator, q: state.search,
      series: state.seriesId, from: state.from, to: state.to
    };
    for (const [key, value] of Object.entries(values)) if (value) url.searchParams.set(key, value);
    try { window.history.replaceState(null, '', url); } catch { /* 檔案模式不一定允許更新網址。 */ }
  }

  function syncControls() {
    $('mode').value = state.mode;
    $('profile').value = state.profileId;
    $('profile-field').hidden = state.mode === 'original';
    $('profile').disabled = state.mode === 'original' || !state.manifest;
    $('search').value = state.search;
  }

  function resetFilters() {
    state.entity = ''; state.indicator = ''; state.search = '';
    state.seriesId = ''; state.from = ''; state.to = '';
  }

  function rangeError() {
    if (!!state.from !== !!state.to) return '請同時選擇起年與迄年。上一個圖表已清除，尚未套用不完整的期間。';
    if (!state.from && !state.to) return '';
    if (!/^\d+$/.test(state.from) || !/^\d+$/.test(state.to)) return '指定年份格式不正確，請重新選擇起年與迄年。';
    if (Number(state.from) > Number(state.to)) return '起年晚於迄年，請調整期間。';
    const years = new Set((state.catalog.years || []).map(String));
    if (!years.has(state.from) || !years.has(state.to)) return '指定年份不在本資料目錄列出的範圍；請重新選擇起年與迄年。';
    return '';
  }

  function chosenSelection() {
    if (state.mode === 'original') return { selection: null, intervalUnavailable: false };
    if (state.from && state.to && state.catalog.intervals !== null && typeof state.catalog.intervals === 'object') {
      const selection = state.catalog.intervals[`${state.from}:${state.to}`];
      return { selection: selection || null, intervalUnavailable: !selection };
    }
    return { selection: state.catalog.default_selection || null, intervalUnavailable: false };
  }

  function renderStructured(container, value) {
    container.replaceChildren();
    if (value === null || value === undefined || typeof value !== 'object') {
      container.append(element('p', 'small', textValue(value)));
    } else {
      container.append(element('pre', '', textValue(value)));
    }
  }

  function showSelection(selection, intervalUnavailable = false) {
    const catalog = state.catalog;
    $('selection-panel').hidden = false;
    $('selection-title').textContent = catalog.title || (state.mode === 'original' ? '原刊數列範圍' : '目前問題');
    $('selection-description').textContent = catalog.description || '';
    $('selection-purpose').textContent = catalog.purpose ? `原定用途：${({'trend':'原刊範圍內趨勢','source-facts':'原來源事實'})[catalog.purpose] || textValue(catalog.purpose)}` : '';
    $('selection-explanation').replaceChildren();
    const status = state.mode === 'original' ? '原刊範圍・逐筆保留' : intervalUnavailable ? '此區間沒有預先產生的合格結果' : selection ? statusLabel(selection.status) : '沒有可用的預設選源結果';
    $('selection-status').textContent = status;
    $('selection-status').className = `status-tag${state.mode !== 'original' && (!selection || /missing|unusable|blocked|unresolved|not_covered|no_qualified|ambiguous/.test(selection.status || '')) ? ' is-caution' : ''}`;
    const explanations = state.mode === 'original'
      ? ['本方式查閱所選原刊數列的完整原紀錄，不套用問題的預設選源名單。原來源系列不等於跨年可比認證；僅畫供應的原連線。']
      : Array.isArray(selection?.explanation) ? selection.explanation : selection?.explanation ? [selection.explanation] : [];
    const reasonLabels = {
      'Source selection is not independent certification of original reporting or historical comparability.':'選定來源不代表已獨立認證原始填報正確，或所有歷年方法一致。',
      'complete original requested period coverage; qualified definition before edition for trends; never rank by value availability':'先確認單一原刊涵蓋指定期間；趨勢用途先核口徑，再依既定版次順序選源，不以數值有無選擇來源。',
      'fixed original source scope; no cross-family fallback or sums':'固定使用此原來源範圍，不跨來源替補或加總。',
      'no_single_qualified_original_panel_covers_requested_scope':'沒有單一合格原刊面板涵蓋所選範圍；不拼接其他版次補齊。'
    };
    for (const explanation of explanations) $('selection-explanation').append(element('li', '', reasonLabels[explanation] || textValue(explanation)));
    if (intervalUnavailable) $('selection-explanation').append(element('li', '', '沒有其他來源替補；請查閱資料版本說明中的完整候選、原始範圍與拒用理由。'));
    $('trend-detail').hidden = !selection?.trend_summary;
    if (selection?.trend_summary) renderStructured($('trend-content'), selection.trend_summary);
  }

  async function loadCatalog() {
    if (!state.manifest) return;
    const request = beginRequest();
    state.catalog = null;
    clearResults();
    $('selection-panel').hidden = true;
    catalogControls(true);
    syncControls();
    updateURL();
    showStatus('正在讀取此範圍的數列目錄…', 'loading');
    try {
      const profile = state.manifest.profiles.find((item) => item.id === state.profileId);
      const url = state.mode === 'original' ? state.manifest.original_catalog_url : profile?.catalog_url;
      if (!url) throw new Error('此問題尚未提供資料目錄。');
      const catalog = await loadJSON(url, request.signal);
      if (!current(request)) return;
      if (!Array.isArray(catalog.series) || !Array.isArray(catalog.years) || catalog.mode !== state.mode) {
        throw new Error('數列目錄的範圍或必要欄位不符合查詢方式。');
      }
      state.catalog = catalog;
      setOptions('from', catalog.years, '未指定', state.from, true);
      setOptions('to', catalog.years, '未指定', state.to, true);
      catalogControls(false);
      $('search').value = state.search;
      await refreshSeries();
    } catch (error) {
      if (!current(request) || error.name === 'AbortError') return;
      clearResults();
      showStatus(`無法載入資料目錄。${error.message || '請稍後重試。'}`, 'error', loadCatalog);
    }
  }

  async function refreshSeries() {
    if (!state.catalog) return;
    const request = beginRequest();
    clearResults();
    const error = rangeError();
    const { selection, intervalUnavailable } = chosenSelection();
    state.selection = selection;
    state.selectedKeys = state.mode === 'original' ? null : new Set(selection?.selected_record_keys || []);
    showSelection(selection, intervalUnavailable);
    const selectedIds = new Set(selection?.series_ids || []);
    const allowed = state.mode === 'original' ? state.catalog.series : state.catalog.series.filter((item) => selectedIds.has(item.id));
    setOptions('entity', distinct(allowed, 'entity'), '全部原對象', state.entity, true);
    setOptions('indicator', distinct(allowed, 'indicator'), '全部原指標', state.indicator, true);
    const words = state.search.trim().toLocaleLowerCase('zh-Hant').split(/\s+/).filter(Boolean);
    const available = allowed.filter((item) => {
      if (state.entity && String(item.entity ?? '') !== state.entity) return false;
      if (state.indicator && String(item.indicator ?? '') !== state.indicator) return false;
      const searchable = [item.label, item.entity, item.facility, item.indicator, item.unit, item.source_id, item.id].join(' ').toLocaleLowerCase('zh-Hant');
      return words.every((word) => searchable.includes(word));
    });
    const select = $('series');
    select.replaceChildren();
    if (error || !available.length) {
      select.append(option('', error ? '請先完成期間設定' : '沒有符合條件的數列'));
      select.disabled = true;
      state.seriesId = '';
      updateURL();
      showStatus(error || (intervalUnavailable || state.mode === 'profile' && !allowed.length
        ? '此問題與期間沒有合格原刊面板或單期事實。圖表與表格已清除，未改用其他來源；完整原始範圍仍可從資料版本與下載頁查閱。'
        : '目前條件沒有符合的數列。可清除搜尋、原對象或原指標，或改查原刊數列；這不表示官方沒有資料。'), 'empty');
      return;
    }
    for (const item of available) select.append(option(item.id, item.label || item.id));
    if (!available.some((item) => item.id === state.seriesId)) state.seriesId = available[0].id;
    select.value = state.seriesId;
    select.disabled = false;
    updateURL();
    showStatus('正在讀取所選數列的原值與來源…', 'loading');
    const entry = available.find((item) => item.id === state.seriesId);
    try {
      const series = await loadJSON(entry.url, request.signal);
      if (!current(request)) return;
      if (series.id !== entry.id || !Array.isArray(series.records) || !Array.isArray(series.lines)) {
        throw new Error('數列識別或原紀錄欄位與目錄不符。');
      }
      const records = series.records.filter((record) => {
        if (state.selectedKeys && !state.selectedKeys.has(record.record_key)) return false;
        if (!state.from && !state.to) return true;
        if (record.year === null || record.year === undefined || record.year === '') return false;
        return Number(record.year) >= Number(state.from) && Number(record.year) <= Number(state.to);
      });
      if (!records.length) {
        showStatus('所選數列在此查詢沒有符合的原紀錄。圖表與表格已清除，未補值或改用其他來源；請查閱資料版本說明中的完整原範圍。', 'empty');
        return;
      }
      state.series = series;
      state.shownRecords = records;
      renderSeries(series, records);
      showStatus('');
    } catch (error) {
      if (!current(request) || error.name === 'AbortError') return;
      clearResults();
      showStatus(`無法載入所選數列。${error.message || '請稍後重試。'}`, 'error', refreshSeries);
    }
  }

  function fact(container, label, value, className = '') {
    container.append(element('dt', '', label));
    const dd = element('dd', className);
    if (value instanceof Node) dd.append(value);
    else dd.textContent = textValue(value);
    container.append(dd);
  }

  function renderSeries(series, records) {
    $('result').hidden = false;
    $('series-title').textContent = series.label || state.seriesId;
    $('series-facts').replaceChildren();
    for (const [label, value] of [
      ['原對象', series.entity], ['原館種／類別', series.facility],
      ['原指標', series.indicator], ['顯示單位', series.unit],
      ['來源代碼', series.source_id], ['原刊版次', series.source_edition_raw]
    ]) {
      const item = element('div');
      fact(item, label, value);
      $('series-facts').append(item);
    }
    setLink('full-data-link', state.catalog.full_data_url || state.manifest.release_url);
    $('series-scope').replaceChildren();
    const notes = [...new Set([state.catalog.scope_note, series.scope_note].filter(Boolean).map(textValue))];
    for (const note of notes) $('series-scope').append(element('p', '', note));
    $('chart-unit').textContent = `單位：${textValue(series.unit)}`;
    renderChart(series, records);
    renderTable(series, records);
    showRecord(records[0]);
  }

  function percentage(value) {
    if (typeof value !== 'string' && typeof value !== 'number') return null;
    const string = String(value);
    if (!/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(string)) return null;
    const parsed = Number(string);
    return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100 ? string : null;
  }

  function pointPosition(record) {
    if (record.plot_value === null || record.plot_value === undefined || !record.plot) return null;
    const x = percentage(record.plot.x_pct), y = percentage(record.plot.y_pct);
    return x !== null && y !== null ? { x, y } : null;
  }

  function svgLine(x1, y1, x2, y2, className) {
    const line = document.createElementNS(SVG_NS, 'line');
    for (const [key, value] of Object.entries({ x1, y1, x2, y2, class: className, 'vector-effect': 'non-scaling-stroke' })) line.setAttribute(key, value);
    return line;
  }

  function xAxis(ticks, className) {
    const axis = element('div', className);
    axis.setAttribute('aria-hidden', 'true');
    for (const tick of ticks || []) {
      const position = percentage(tick.position_pct);
      if (position === null) continue;
      const edge = Number(position) === 0 ? ' is-first' : Number(position) === 100 ? ' is-last' : '';
      const label = element('span', `x-tick${edge}`, textValue(tick.label));
      label.style.left = `${position}%`;
      axis.append(label);
    }
    return axis;
  }

  function renderChart(series, records) {
    const chart = $('chart');
    chart.replaceChildren();
    const points = new Map();
    for (const record of records) {
      const position = pointPosition(record);
      if (position && officialURL(record.official_url)) points.set(record.record_key, { record, ...position });
    }
    if (!points.size) {
      chart.append(element('p', 'chart-empty', '這個範圍的原值無可畫點位。原符號、缺值與不可用狀態照留於下表，沒有改成零。'));
      return;
    }
    const yAxis = element('div', 'y-axis');
    yAxis.setAttribute('aria-hidden', 'true');
    const plot = element('div', 'plot-area');
    plot.setAttribute('role', 'group');
    plot.setAttribute('aria-label', '原報點位；每個圓點連往該筆官方來源，完整原值另見下表。');
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'plot-lines');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    for (const tick of series.y_ticks || []) {
      const position = percentage(tick.position_pct);
      if (position === null) continue;
      const label = element('span', 'y-tick', textValue(tick.label));
      label.style.top = `${position}%`;
      yAxis.append(label);
      svg.append(svgLine('0', position, '100', position, 'grid-line'));
    }
    for (const pair of series.lines) {
      const left = points.get(pair.left), right = points.get(pair.right);
      if (left && right) svg.append(svgLine(left.x, left.y, right.x, right.y, 'data-line'));
    }
    plot.append(svg);
    for (const { record, x, y } of points.values()) {
      const label = `${record.period_label || '原期間未列'}，${textValue(record.display_value)} ${record.unit ?? series.unit ?? ''}；開啟官方來源`;
      const link = externalLink(record.official_url, '', 'plot-point', true);
      link.style.left = `${x}%`;
      link.style.top = `${y}%`;
      link.setAttribute('aria-label', label);
      link.title = label;
      link.dataset.recordKey = record.record_key;
      const dot = element('span', 'point-dot');
      dot.setAttribute('aria-hidden', 'true');
      link.append(dot);
      plot.append(link);
    }
    const mobileTicks = Array.isArray(series.mobile_x_ticks) && series.mobile_x_ticks.length ? series.mobile_x_ticks : null;
    chart.append(yAxis, plot, xAxis(series.x_ticks, `x-axis${mobileTicks ? ' has-mobile' : ''}`));
    if (mobileTicks) chart.append(xAxis(mobileTicks, 'x-axis x-axis-mobile'));
  }

  function sameOriginal(left, right) {
    return textValue(left) === textValue(right);
  }

  function originalNote(label, value, unit, record) {
    const note = element('span', 'raw-note');
    note.append(document.createTextNode(`${label}：`));
    note.append(externalLink(record.official_url, textValue(value), '', true));
    if (unit !== undefined && unit !== null && unit !== '') note.append(document.createTextNode(` ${textValue(unit)}`));
    return note;
  }

  function renderTable(series, records) {
    const fragment = document.createDocumentFragment();
    for (const record of records) {
      const row = element('tr');
      row.dataset.recordKey = record.record_key;
      row.append(element('td', '', record.period_label || '原期間未列'));
      const value = element('td');
      value.append(externalLink(record.official_url, textValue(record.display_value), 'value-link', true));
      value.append(element('span', 'value-unit', textValue(record.unit ?? series.unit)));
      if (!sameOriginal(record.original_value, record.plot_value) || !sameOriginal(record.original_unit, record.unit ?? series.unit)) {
        value.append(originalNote('原刊原量', record.original_value, record.original_unit, record));
      }
      if (!sameOriginal(record.raw_value, record.original_value) && !sameOriginal(record.raw_value, record.plot_value)) {
        value.append(originalNote('原字串', record.raw_value, undefined, record));
      }
      if (!officialURL(record.official_url)) value.append(element('span', 'raw-note', '此筆官方連結未提供或格式不可用。'));
      row.append(value);
      const status = element('td');
      status.append(element('span', 'cell-status', `值狀態：${statusLabel(record.value_status)}`));
      status.append(element('span', 'cell-status', `對照範圍：${statusLabel(record.comparison_status)}`));
      if (record.plot_value === null) status.append(element('span', 'cell-status', '此筆不畫點；保留原值與原狀態。'));
      if (record.zero_interpretation) status.append(element('span', 'cell-status', `零值說明：${statusLabel(record.zero_interpretation)}`));
      row.append(status);
      const source = element('td');
      source.append(element('span', 'cell-source', series.source_id || record.source_version_id || '來源代碼未列'));
      const button = element('button', 'quiet-button record-button', '原件與表位');
      button.type = 'button';
      button.setAttribute('aria-controls', 'record-detail');
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', `查看 ${record.period_label || '此筆'} 的原件、表位與完整原值`);
      button.addEventListener('click', () => showRecord(record));
      source.append(button);
      row.append(source);
      fragment.append(row);
    }
    $('records-body').replaceChildren(fragment);
  }

  function sourceField(label, value, type = '') {
    let content = value;
    if (type === 'url' && value) content = externalLink(value, textValue(value));
    fact($('source-fields'), label, content, type === 'mono' ? 'mono' : '');
  }

  function showRecord(record) {
    state.detailKey = record.record_key;
    $('record-detail').hidden = false;
    $('detail-period').textContent = record.period_label || '原期間未列';
    $('official-link-note').hidden = !record.official_link_note;
    $('official-link-note').textContent = record.official_link_note ? textValue(record.official_link_note) : '';
    $('source-fields').replaceChildren();
    sourceField('官方入口', record.official_url, 'url');
    sourceField('原始來源網址', record.source_url, 'url');
    sourceField('原件 SHA-256', record.source_sha256, 'mono');
    sourceField('原表／頁／欄位', record.source_locator);
    sourceField('來源版本 ID', record.source_version_id, 'mono');
    sourceField('證據 ID', record.evidence_id, 'mono');
    sourceField('原紀錄鍵', record.record_key, 'mono');
    $('value-fields').replaceChildren();
    for (const [label, value] of [
      ['原期間標籤', record.period_label], ['年度', record.year], ['月份', record.month],
      ['圖表顯示值', record.display_value], ['既有繪圖點值', record.plot_value],
      ['繪圖單位', record.unit], ['原刊原量', record.original_value],
      ['原刊單位', record.original_unit], ['原欄字串', record.raw_value],
      ['值狀態（原碼）', record.value_status], ['對照狀態（原碼）', record.comparison_status],
      ['零值說明（原碼）', record.zero_interpretation]
    ]) {
      const content = ['圖表顯示值', '既有繪圖點值', '原刊原量', '原欄字串'].includes(label)
        ? externalLink(record.official_url, textValue(value), '', true) : textValue(value);
      fact($('value-fields'), label, content);
    }
    renderStructured($('record-facets'), record.facets);
    renderStructured($('record-context'), record.original_context);
    for (const row of $('records-body').children) {
      const selected = row.dataset.recordKey === record.record_key;
      row.classList.toggle('is-selected', selected);
      row.querySelector('button').setAttribute('aria-pressed', String(selected));
    }
  }

  async function initialize() {
    const request = beginRequest();
    showStatus('正在載入資料版本與問題目錄…', 'loading');
    try {
      const manifest = await loadJSON('./manifest.json', request.signal);
      if (!current(request)) return;
      if (!Array.isArray(manifest.profiles)) throw new Error('資料目錄缺少已登錄問題清單。');
      state.manifest = manifest;
      if (!manifest.profiles.some((profile) => profile.id === state.profileId)) {
        state.profileId = manifest.profiles.some((profile) => profile.id === manifest.default_profile_id)
          ? manifest.default_profile_id : manifest.profiles[0]?.id || '';
      }
      $('page-title').textContent = manifest.title || '臺灣公共圖書館資料';
      document.title = `${manifest.title || '臺灣公共圖書館資料'}｜原值與官方來源`;
      $('versions').textContent = `資料 v${manifest.data_version || '未列'} ・ 閱覽器 v${manifest.viewer_version || '未列'}`;
      $('manifest-scope').textContent = manifest.scope_note ? textValue(manifest.scope_note) : '';
      setLink('repository-link', manifest.repository_url);
      setLink('release-link', manifest.release_url);
      $('profile').replaceChildren(...manifest.profiles.map((profile) => option(profile.id, profile.title || profile.id)));
      $('mode').disabled = false;
      $('reset-query').disabled = false;
      syncControls();
      await loadCatalog();
    } catch (error) {
      if (!current(request) || error.name === 'AbortError') return;
      clearResults();
      showStatus(`無法載入資料。${error.message || '請稍後重試。'}請確認使用可提供資料檔的網站網址。`, 'error', initialize);
    }
  }

  $('query-form').addEventListener('submit', (event) => event.preventDefault());
  $('mode').addEventListener('change', () => {
    state.mode = $('mode').value;
    resetFilters();
    void loadCatalog();
  });
  $('profile').addEventListener('change', () => {
    state.profileId = $('profile').value;
    resetFilters();
    void loadCatalog();
  });
  for (const [id, key] of [['entity', 'entity'], ['indicator', 'indicator'], ['from', 'from'], ['to', 'to'], ['series', 'seriesId']]) {
    $(id).addEventListener('change', () => {
      state[key] = $(id).value;
      void refreshSeries();
    });
  }
  $('search').addEventListener('input', () => {
    state.search = $('search').value;
    void refreshSeries();
  });
  $('reset-period').addEventListener('click', () => {
    state.from = ''; state.to = '';
    $('from').value = ''; $('to').value = '';
    void refreshSeries();
  });
  $('reset-query').addEventListener('click', () => {
    resetFilters();
    state.mode = 'profile';
    state.profileId = state.manifest.default_profile_id || state.manifest.profiles[0]?.id || '';
    void loadCatalog();
  });
  $('retry').addEventListener('click', () => { if (state.retry) void state.retry(); });
  window.addEventListener('popstate', () => {
    const params = new URLSearchParams(window.location.search);
    state.mode = params.get('mode') === 'original' ? 'original' : 'profile';
    state.profileId = params.get('profile') || state.manifest?.default_profile_id || '';
    state.entity = params.get('entity') || ''; state.indicator = params.get('indicator') || '';
    state.search = params.get('q') || ''; state.seriesId = params.get('series') || '';
    state.from = params.get('from') || ''; state.to = params.get('to') || '';
    void loadCatalog();
  });

  void initialize();
})();
