/* Bounded client for versioned investigation data; no bulk-data fallback. */
(function () {
  'use strict';
  function mount(root) {
    var base = root.dataset.api.replace(/\/$/, ''), release = root.dataset.release;
    if (!/^btb-v1-[0-9a-f]{24}$/.test(release)) return;
    var form = root.querySelector('form'), body = root.querySelector('[data-rows]');
    var status = root.querySelector('[data-status]'), more = root.querySelector('[data-more]');
    var summary = root.querySelector('[data-summary]'), evidence = root.querySelector('[data-evidence]');
    var cursor = null, controller = null, generation = 0, shown = 0, total = 0, debounce;
    function params() {
      var p = new URLSearchParams({ release: release });
      ['q', 'congress', 'chamber', 'policy_area', 'bipartisan'].forEach(function (key) {
        var value = form.elements[key].value.trim(); if (value) p.set(key, value);
      });
      return p;
    }
    function get(path, signal) {
      return fetch(base + path, { signal: signal, credentials: 'omit', headers: { Accept: 'application/json' } }).then(function (r) {
        if (!r.ok) throw new Error(r.status === 429 ? 'Please wait a moment before searching again.' : 'The record is temporarily unavailable. Try Search again.');
        return r.json();
      }).then(function (data) { if (data.release_id !== release) throw new Error('The data version did not match this investigation.'); return data; });
    }
    function textCell(row, value) { var td = document.createElement('td'); td.textContent = value || '—'; row.appendChild(td); return td; }
    function append(items) {
      items.forEach(function (b) {
        var row = document.createElement('tr'), cell = textCell(row, ''), button = document.createElement('button');
        button.type = 'button'; button.textContent = b.bill_type.toUpperCase() + ' ' + b.bill_number;
        button.setAttribute('aria-label', 'View evidence for ' + button.textContent);
        button.addEventListener('click', function () {
          evidence.textContent = 'Loading evidence…';
          get('/v1/bills/' + encodeURIComponent(b.bill_id) + '?release=' + release).then(function (data) {
            evidence.textContent = ''; var link = document.createElement('a');
            if (!/^https:\/\/www\.govinfo\.gov\//.test(data.bill.source_url)) throw new Error('Source link could not be verified.');
            link.href = data.bill.source_url; link.textContent = 'Official source record for ' + b.bill_id;
            link.target = '_blank'; link.rel = 'noopener'; evidence.appendChild(link);
            evidence.appendChild(document.createTextNode(' · Source file: ' + data.bill.source_id + ' · Record: ' + data.bill.source_record_id));
          }).catch(function (e) { evidence.textContent = e.message; });
        });
        cell.textContent = ''; cell.appendChild(button); textCell(row, b.title); textCell(row, b.introduced_date); textCell(row, b.outcome); body.appendChild(row);
      });
      shown += items.length;
    }
    function load(appendPage) {
      if (controller) controller.abort(); controller = new AbortController(); var signal = controller.signal, current = ++generation;
      var p = params(), summaryParams = new URLSearchParams(p); if (appendPage && cursor) p.set('cursor', cursor); p.set('limit', '50');
      root.setAttribute('aria-busy', 'true'); status.textContent = 'Loading records…'; more.disabled = true;
      Promise.all([get('/v1/bills?' + p, signal), appendPage ? Promise.resolve(null) : get('/v1/summary?' + summaryParams, signal)]).then(function (results) {
        if (current !== generation) return;
        var page = results[0], totals = results[1];
        if (!appendPage) { body.textContent = ''; shown = 0; evidence.textContent = ''; total = totals.total; summary.textContent = '';
          totals.outcomes.forEach(function (o) { var line = document.createElement('p'); line.textContent = o.outcome + ': ' + o.bill_count.toLocaleString(); summary.appendChild(line); }); }
        append(page.items); cursor = page.next_cursor; more.hidden = !cursor;
        status.textContent = total.toLocaleString() + ' measures match. Showing ' + shown.toLocaleString() + '.';
      }).catch(function (e) { if (e.name !== 'AbortError' && current === generation) status.textContent = e.message; }).finally(function () {
        if (current === generation) { root.setAttribute('aria-busy', 'false'); more.disabled = false; }
      });
    }
    form.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(debounce); load(false); });
    form.addEventListener('change', function () { clearTimeout(debounce); load(false); });
    form.elements.q.addEventListener('input', function () { clearTimeout(debounce); debounce = setTimeout(function () { load(false); }, 300); });
    form.addEventListener('reset', function () { clearTimeout(debounce); setTimeout(function () { load(false); }, 0); });
    more.addEventListener('click', function () { if (cursor) load(true); });
    get('/v1/investigations/where-bills-go-to-die?release=' + release).then(function (data) {
      data.policy_areas.forEach(function (p) { if (!p.policy_area) return; var o = document.createElement('option'); o.value = p.policy_area; o.textContent = p.policy_area; form.elements.policy_area.appendChild(o); });
      load(false);
    }).catch(function (e) { status.textContent = e.message; });
  }
  document.querySelectorAll('[data-btb-explorer]').forEach(mount);
}());
