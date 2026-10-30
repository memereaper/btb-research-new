/* Between the Bills: investigation 002 charts and The Open Record search. No dependencies. */
(function () {
  'use strict';
  var C = window.BTBD || {}, d = document;
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var LABEL = { bipartisan: 'Bipartisan on day one', same_party: 'Same party only', solo: 'No cosponsors', other_sponsor: 'Independent sponsor' };
  var SHORT = { bipartisan: 'Bipartisan', same_party: 'Same party', solo: 'Solo', other_sponsor: 'Indep.' };
  var STAGE = { introduced: 'Introduced', cleared_committee: 'Out of committee', passed_one: 'Passed one chamber', passed_both: 'Passed both', law: 'Became law' };
  var COL = { bipartisan: 'var(--x-lime,#D6FF3D)', same_party: 'var(--x-pink,#FF9AD5)', solo: 'var(--x-cyan,#4FD8FF)' };
  function el(tag, cls, html) { var e = d.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmt(n, dp) { return Number(n).toLocaleString('en-US', { minimumFractionDigits: dp || 0, maximumFractionDigits: dp || 0 }); }

  /* Bars grow when they scroll into view. */
  var io = 'IntersectionObserver' in window && !reduce ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } });
  }, { threshold: .25 }) : null;
  function watch(node) { if (io) io.observe(node); else node.classList.add('is-in'); }

  /* A row of labelled horizontal bars. rows: [{label, value, color, note}] scaled to max. */
  function bars(host, rows, opts) {
    opts = opts || {};
    var max = opts.max || Math.max.apply(null, rows.map(function (r) { return r.value; })) || 1;
    var wrap = el('div', 'btbd-bars' + (opts.dark ? ' is-dark' : ''));
    rows.forEach(function (r, i) {
      var row = el('div', 'btbd-bar');
      row.innerHTML = '<span class="btbd-bar-label">' + esc(r.label) + '</span>' +
        '<span class="btbd-bar-track"><span class="btbd-bar-fill" style="--w:' + (100 * r.value / max).toFixed(2) + '%;--c:' + (r.color || 'var(--x-blue)') + ';--i:' + i + '"></span></span>' +
        '<span class="btbd-bar-val">' + esc(r.text != null ? r.text : fmt(r.value, 1) + '%') + '</span>' +
        (r.note ? '<span class="btbd-bar-note">' + esc(r.note) + '</span>' : '');
      wrap.appendChild(row);
    });
    host.appendChild(wrap); watch(wrap);
  }

  function legend(host, keys, dark) {
    var l = el('p', 'btbd-legend' + (dark ? ' is-dark' : ''));
    l.innerHTML = keys.map(function (k) { return '<span><i style="background:' + COL[k] + '"></i>' + LABEL[k] + '</span>'; }).join('');
    host.appendChild(l);
  }

  /* ---------- investigation charts ---------- */
  function investigation(F) {
    var by = function (rows, k) { return rows.filter(function (r) { return r.coalition === k; })[0]; };
    var order = ['bipartisan', 'same_party', 'solo'];

    var ladder = d.querySelector('[data-btbd-chart="ladder"]');
    if (ladder) {
      var steps = [['pct_cleared_committee', 'Out of committee'], ['pct_passed_one_chamber', 'Passed a chamber'], ['pct_passed_both', 'Passed both chambers'], ['pct_became_law', 'Became law']];
      var max = Math.max.apply(null, F.excluding_ceremonial.map(function (r) { return r.pct_cleared_committee; }));
      legend(ladder, order, true);
      var grid = el('div', 'btbd-ladder');
      steps.forEach(function (s) {
        var g = el('div', 'btbd-ladder-step'); g.appendChild(el('h3', 'btbd-ladder-h', s[1]));
        bars(g, order.map(function (k) { var r = by(F.excluding_ceremonial, k); return { label: SHORT[k], value: r[s[0]], color: COL[k] }; }), { max: max, dark: true });
        grid.appendChild(g);
      });
      ladder.appendChild(grid);
    }

    var dose = d.querySelector('[data-btbd-chart="dose"]');
    if (dose) bars(dose, F.dose_response.map(function (r) {
      var k = r.original_cross_party_cosponsors;
      return { label: (k === '0' ? 'None' : k) + (k === '1' ? ' partner' : k === '0' ? '' : ' partners'), value: r.pct_became_law, color: k === '0' ? 'var(--x-pink,#FF9AD5)' : 'var(--x-blue,#2E2BFF)', note: fmt(r.bills) + ' bills' };
    }));

    var power = d.querySelector('[data-btbd-chart="power"]');
    if (power) {
      var mx = Math.max.apply(null, F.majority_sponsor.concat(F.minority_sponsor).map(function (r) { return r.pct_became_law; }));
      legend(power, order);
      var two = el('div', 'btbd-two');
      [['majority_sponsor', 'Sponsor in the majority'], ['minority_sponsor', 'Sponsor in the minority']].forEach(function (p) {
        var g = el('div', 'btbd-two-col'); g.appendChild(el('h3', 'btbd-h3', p[1]));
        bars(g, order.map(function (k) { var r = by(F[p[0]], k); return { label: SHORT[k], value: r.pct_became_law, color: COL[k], note: fmt(r.bills) + ' bills, ' + fmt(r.laws) + ' laws' }; }), { max: mx });
        two.appendChild(g);
      });
      power.appendChild(two);
    }

    var areas = d.querySelector('[data-btbd-chart="areas"]');
    if (areas && F.policy_areas) {
      var rows = F.policy_areas.slice().sort(function (a, b) { return (b.law_bip - b.law_not) - (a.law_bip - a.law_not); });
      var amax = Math.max.apply(null, rows.map(function (r) { return Math.max(r.law_bip, r.law_not); }));
      var list = el('div', 'btbd-dumbbell');
      rows.forEach(function (r, i) {
        var a = 100 * r.law_not / amax, b = 100 * r.law_bip / amax;
        var row = el('div', 'btbd-db-row');
        row.innerHTML = '<span class="btbd-db-label">' + esc(r.policy_area) + '<small>' + fmt(r.n) + ' bills · ' + fmt(r.share_bip, 0) + '% bipartisan</small></span>' +
          '<span class="btbd-db-track"><span class="btbd-db-line" style="--a:' + Math.min(a, b).toFixed(2) + '%;--b:' + Math.max(a, b).toFixed(2) + '%;--i:' + i + '"></span>' +
          '<span class="btbd-db-dot is-not" style="--x:' + a.toFixed(2) + '%" title="Not bipartisan ' + r.law_not + '%"></span>' +
          '<span class="btbd-db-dot is-bip" style="--x:' + b.toFixed(2) + '%" title="Bipartisan ' + r.law_bip + '%"></span></span>' +
          '<span class="btbd-db-val">' + fmt(r.law_bip, 1) + '% <span>vs</span> ' + fmt(r.law_not, 1) + '%</span>';
        list.appendChild(row);
      });
      var key = el('p', 'btbd-legend is-dark', '<span><i style="background:var(--x-lime,#D6FF3D)"></i>Began bipartisan</span><span><i style="background:var(--x-pink,#FF9AD5)"></i>Did not</span>');
      areas.appendChild(key); areas.appendChild(list); watch(list);
    }

    var grow = d.querySelector('[data-btbd-chart="grow"]');
    if (grow) {
      var gmax = Math.max.apply(null, F.later_coalition_growth.map(function (r) { return r.avg_final_cross; }));
      var g2 = el('div', 'btbd-grow');
      F.later_coalition_growth.forEach(function (r) {
        var row = el('div', 'btbd-grow-row');
        row.innerHTML = '<span class="btbd-bar-label">' + esc(STAGE[r.furthest] || r.furthest) + '<small>' + fmt(r.bills) + ' bills</small></span>' +
          '<span class="btbd-grow-track"><span class="btbd-grow-end" style="--w:' + (100 * r.avg_final_cross / gmax).toFixed(2) + '%"></span><span class="btbd-grow-start" style="--w:' + (100 * r.avg_original_cross / gmax).toFixed(2) + '%"></span></span>' +
          '<span class="btbd-bar-val">' + fmt(r.avg_original_cross, 1) + ' → ' + fmt(r.avg_final_cross, 1) + '</span>';
        g2.appendChild(row);
      });
      grow.appendChild(el('p', 'btbd-legend', '<span><i style="background:var(--x-blue,#2E2BFF)"></i>Cross-party cosponsors on day one</span><span><i style="background:var(--x-cream-2,#ECE3CD);outline:1px solid var(--x-ink)"></i>By the end</span>'));
      grow.appendChild(g2); watch(g2);
    }

    var people = d.querySelector('[data-btbd-people]');
    if (people) fetch(C.api + '?route=members&min=200').then(function (r) { return r.json(); }).then(function (j) {
      people.innerHTML = '';
      (j.members || []).slice(0, 12).forEach(function (m, i) {
        var li = el('li', 'btbd-person');
        li.innerHTML = '<span class="btbd-person-rank">' + (i + 1) + '</span><span class="btbd-person-name">' + esc(m.name.replace(/^(Rep|Sen)\. /, '')) + '</span>' +
          '<span class="btbd-person-bar"><span style="--w:' + m.pct_cross_party + '%;--c:' + (m.party === 'R' ? '#E5484D' : '#2E6BFF') + '"></span></span><span class="btbd-person-val">' + fmt(m.pct_cross_party, 1) + '%<small>' + fmt(m.cosponsorships) + '</small></span>';
        people.appendChild(li);
      });
      watch(people);
    }).catch(function () { people.innerHTML = '<li class="btbd-muted">The member list could not load. Try again shortly.</li>'; });

    /* guess */
    var gq = d.querySelector('[data-btbd-guess]');
    if (gq) {
      var inp = gq.querySelector('[data-btbd-guess-input]'), out = gq.querySelector('[data-btbd-guess-out]');
      inp.addEventListener('input', function () { out.textContent = inp.value; });
      gq.querySelector('[data-btbd-guess-go]').addEventListener('click', function () {
        var ans = +gq.dataset.answer, g = +inp.value, off = Math.abs(ans - g);
        gq.querySelector('[data-btbd-guess-verdict]').textContent = off <= 5 ? 'You were within 5 points.' : 'You guessed ' + g + '%, ' + off + ' points ' + (g < ans ? 'low' : 'high') + '.';
        gq.querySelector('[data-btbd-guess-reveal]').hidden = false; inp.disabled = true; this.disabled = true; gq.classList.add('is-done');
      });
    }
  }

  /* ---------- The Open Record ---------- */
  function record() {
    var form = d.querySelector('[data-btbd-form]'); if (!form) return;
    var tbody = d.querySelector('[data-btbd-rows]'), count = d.querySelector('[data-btbd-count]'), more = d.querySelector('[data-btbd-more]');
    var state = { cursor: null, rows: [], total: null, seq: 0 };
    var params = new URLSearchParams(location.search);
    ['q', 'congress', 'coalition', 'furthest', 'party'].forEach(function (k) { if (params.get(k) && form.elements[k]) form.elements[k].value = params.get(k); });

    function query(cursor) {
      var p = new URLSearchParams({ route: 'bills', limit: '50' });
      ['q', 'congress', 'coalition', 'furthest', 'party'].forEach(function (k) { var v = form.elements[k].value.trim(); if (v) p.set(k, v); });
      if (cursor) p.set('cursor', cursor);
      return p;
    }
    function row(b) {
      var tr = el('tr');
      var id = b.bill_type.toUpperCase().replace('HJRES', 'H.J.Res.').replace('SJRES', 'S.J.Res.').replace(/^HR$/, 'H.R.').replace(/^S$/, 'S.') + ' ' + b.bill_number;
      var party = b.sponsor_party ? '<span class="btbd-party is-' + esc(b.sponsor_party) + '">' + esc(b.sponsor_party) + '</span>' : '';
      tr.innerHTML = '<td class="btbd-id"><a href="' + esc(b.congress_url) + '" target="_blank" rel="noopener">' + esc(id) + '</a><small>' + esc(b.congress) + 'th</small></td>' +
        '<td class="btbd-title">' + esc(b.title) + (b.policy_area ? '<small>' + esc(b.policy_area) + '</small>' : '') + '</td>' +
        '<td>' + party + esc((b.sponsor_name || '').replace(/^(Rep|Sen)\. /, '').replace(/ \[.*\]$/, '')) + '</td>' +
        '<td><span class="btbd-chip is-' + esc(b.coalition_at_intro) + '">' + esc(SHORT[b.coalition_at_intro] || '') + '</span>' + (b.orig_cross ? '<small>' + b.orig_cross + ' across</small>' : '') + '</td>' +
        '<td><span class="btbd-stage is-' + esc(b.furthest) + '">' + esc(STAGE[b.furthest] || '') + '</span></td>' +
        '<td class="btbd-date">' + esc((b.introduced_on || '').slice(0, 10)) + '</td>';
      return tr;
    }
    function load(reset) {
      var seq = ++state.seq;
      if (reset) { state.cursor = null; state.rows = []; tbody.innerHTML = ''; count.textContent = 'Searching…'; }
      var p = query(reset ? null : state.cursor);
      fetch(C.api + '?' + p.toString()).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); }).then(function (res) {
        if (seq !== state.seq) return;
        if (!res.ok) { count.textContent = res.j.error || 'Search failed.'; return; }
        var j = res.j; if (j.total != null) state.total = j.total;
        j.bills.forEach(function (b) { state.rows.push(b); tbody.appendChild(row(b)); });
        state.cursor = j.next_cursor; more.hidden = !j.next_cursor;
        count.textContent = state.total === 0 ? 'No bills match.' : 'Showing ' + fmt(state.rows.length) + ' of ' + fmt(state.total) + ' bills';
      }).catch(function () { if (seq === state.seq) count.textContent = 'The database could not be reached. Try again in a moment.'; });
    }
    function sync() {
      var p = query(null); p.delete('route'); p.delete('limit');
      history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p.toString() : '') + '#search');
    }
    var t; form.addEventListener('input', function (e) { clearTimeout(t); t = setTimeout(function () { sync(); load(true); }, e.target.name === 'q' ? 300 : 0); });
    form.addEventListener('submit', function (e) { e.preventDefault(); sync(); load(true); });
    more.addEventListener('click', function () { load(false); });
    d.querySelector('[data-btbd-reset]').addEventListener('click', function () { form.reset(); sync(); load(true); });
    d.querySelector('[data-btbd-share]').addEventListener('click', function () { var b = this; navigator.clipboard && navigator.clipboard.writeText(location.href).then(function () { b.textContent = 'Link copied'; setTimeout(function () { b.textContent = 'Copy link'; }, 1600); }); });
    d.querySelector('[data-btbd-csv]').addEventListener('click', function () {
      var cols = ['bill_id', 'congress', 'title', 'sponsor_name', 'sponsor_party', 'sponsor_state', 'policy_area', 'coalition_at_intro', 'orig_cosponsors', 'orig_cross', 'all_cosponsors', 'all_cross', 'furthest', 'became_law', 'introduced_on', 'latest_action_on', 'latest_action_text', 'congress_url'];
      var csv = [cols.join(',')].concat(state.rows.map(function (r) { return cols.map(function (c) { return '"' + String(r[c] == null ? '' : r[c]).replace(/"/g, '""') + '"'; }).join(','); })).join('\n');
      var a = el('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'between-the-bills-open-record.csv'; a.click();
    });
    load(true);
  }

  if (C.route === 'the-bipartisanship-question' && C.findings) investigation(C.findings);
  if (C.route === 'open-record') record();
})();
