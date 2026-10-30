/*
 * Open Data tab. Bills page through the read-only API; the SQL console runs
 * DuckDB-WASM in the browser against Parquet files on a public CDN. Nothing
 * row-level is stored in WordPress.
 */
(function () {
	'use strict';
	var BX = window.BX, C = window.BTBD || {};
	var root = document.querySelector('[data-od]');
	if (!root || !BX) return;
	var reduced = BX.reduced();
	function $(s, el) { return (el || document).querySelector(s); }
	function $$(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }
	var esc = BX.esc;
	var TYPE = { hr: 'H.R.', s: 'S.', hjres: 'H.J.Res.', sjres: 'S.J.Res.' };
	var STAGE = { introduced: 'Introduced', cleared_committee: 'Out of committee', passed_one: 'Passed one chamber', passed_both: 'Passed both', law: 'Became law' };
	var COAL = { bipartisan: 'Bipartisan', same_party: 'Same party', solo: 'No cosponsors', other_sponsor: 'Independent sponsor', not_bipartisan: 'Not bipartisan' };
	function billNo(b) { return (TYPE[b.bill_type] || b.bill_type) + ' ' + b.bill_number; }
	function apiUrl(params) {
		var q = Object.keys(params).filter(function (k) { return params[k] !== '' && params[k] != null; }).map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]); }).join('&');
		return C.api + '?' + q;
	}
	function getJSON(url) { return fetch(url).then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status)); return j; }); }); }
	function copy(text, btn) {
		var done = function () { if (!btn) return; var t = btn.textContent; btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = t; }, 1600); };
		if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, done); else done();
	}
	function csvCell(v) { var s = v == null ? '' : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
	function download(name, text, type) {
		var blob = new Blob([text], { type: type || 'text/csv;charset=utf-8' });
		var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name;
		document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
	}

	/* ---------- Hero: punch cards that punch themselves ---------- */
	(function cards() {
		var host = $('[data-od-cards]');
		if (!host || window.innerWidth < 900) return;
		var spots = [[62, 18, -7, 0], [74, 48, 5, 1.6], [56, 66, -3, 3.1]];
		spots.forEach(function (s, k) {
			var c = document.createElement('div');
			c.className = 'od-pcard';
			c.style.setProperty('--x', s[0] + 'vw'); c.style.setProperty('--y', s[1] + 'vh'); c.style.setProperty('--r', s[2] + 'deg'); c.style.setProperty('--d', s[3] + 's');
			var cv = document.createElement('canvas'); c.appendChild(cv); host.appendChild(c);
			var dpr = Math.min(2, window.devicePixelRatio || 1), W = 230, H = 102;
			cv.width = W * dpr; cv.height = H * dpr;
			var ctx = cv.getContext('2d'); ctx.scale(dpr, dpr);
			var cols = 40, rows = 10, holes = [];
			for (var i = 0; i < cols; i++) for (var j = 0; j < rows; j++) if (((i * 7 + j * 13 + k * 29) * 2654435761 >>> 0) % 100 < 14) holes.push([i, j]);
			holes.sort(function (a, b) { return a[0] - b[0]; });
			function base() {
				ctx.clearRect(0, 0, W, H);
				ctx.fillStyle = '#F2E7C9'; ctx.fillRect(0, 0, W, H);
				ctx.fillStyle = 'rgba(18,15,46,.28)'; ctx.font = '5px monospace';
				for (var r = 0; r < rows; r++) for (var cc = 0; cc < cols; cc += 2) ctx.fillText(String(r), 8 + cc * 5.4, 12 + r * 9);
				ctx.strokeStyle = '#B0262A'; ctx.lineWidth = .6; ctx.beginPath(); ctx.moveTo(4, 4); ctx.lineTo(W - 4, 4); ctx.stroke();
			}
			base();
			var n = 0;
			function punch() {
				if (n >= holes.length) { setTimeout(function () { n = 0; base(); punch(); }, 2600); return; }
				var h = holes[n++];
				ctx.fillStyle = '#0F0C29'; ctx.fillRect(7 + h[0] * 5.4, 6 + h[1] * 9, 3, 6);
				setTimeout(punch, reduced ? 0 : 55);
			}
			if (reduced) { holes.forEach(function (h) { ctx.fillStyle = '#0F0C29'; ctx.fillRect(7 + h[0] * 5.4, 6 + h[1] * 9, 3, 6); }); }
			else setTimeout(punch, 900 + k * 500);
		});
	})();

	/* ---------- Count-up stats and the shelf deal ---------- */
	$$('[data-od-count]').forEach(function (el) {
		var to = +el.getAttribute('data-od-count');
		if (reduced) return;
		el.textContent = '0';
		setTimeout(function () { BX.countTo(el, to, 1600); }, 900);
	});
	(function shelf() {
		var s = $('[data-bx-shelf]');
		if (!s) return;
		if (reduced || !('IntersectionObserver' in window)) { s.classList.add('is-dealt'); return; }
		var io = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { s.classList.add('is-dealt'); io.disconnect(); } }, { threshold: 0.12 });
		io.observe(s);
	})();

	/* ================================================================
	   Browse
	   ================================================================ */
	(function browse() {
		var form = $('[data-od-form]');
		if (!form) return;
		var tbody = $('[data-od-rows]'), more = $('[data-od-more]'), countEl = $('[data-od-count-text]');
		var policy = $('[data-od-policy]'), apiBox = $('[data-od-apicall]');
		var FIELDS = ['q', 'congress', 'chamber', 'coalition', 'furthest', 'party', 'policy'];
		var cursor = null, rows = [], total = null, token = 0, timer = null;

		getJSON(apiUrl({ route: 'policy_areas' })).then(function (r) {
			(r.policy_areas || []).forEach(function (p) { var o = document.createElement('option'); o.value = p.policy_area; o.textContent = p.policy_area + ' (' + BX.fmt(p.bills) + ')'; policy.appendChild(o); });
			var want = new URLSearchParams(location.search).get('policy');
			if (want) policy.value = want;
		}).catch(function () {});

		var init = new URLSearchParams(location.search);
		FIELDS.forEach(function (f) { if (init.get(f) && form.elements[f]) form.elements[f].value = init.get(f); });

		function params(extra) {
			var p = { route: 'bills', limit: 50 };
			FIELDS.forEach(function (f) { var v = (form.elements[f].value || '').trim(); if (v) p[f] = v; });
			for (var k in extra) p[k] = extra[k];
			return p;
		}
		function syncUrl() {
			var u = new URL(location.href);
			FIELDS.forEach(function (f) { var v = (form.elements[f].value || '').trim(); if (v) u.searchParams.set(f, v); else u.searchParams.delete(f); });
			history.replaceState(null, '', u);
		}
		function rowHtml(b, k) {
			var party = b.sponsor_party ? '<span class="od-party is-' + esc(b.sponsor_party) + '" aria-hidden="true">' + esc(b.sponsor_party) + '</span>' : '';
			var sponsor = b.sponsor_name ? b.sponsor_name.replace(/^(Rep\.|Sen\.)\s*/, '') : (b.sponsor_id ? b.sponsor_id + (b.sponsor_state ? ' [' + b.sponsor_party + '-' + b.sponsor_state + ']' : '') : '–');
			var stage = STAGE[b.furthest] || b.furthest;
			var inProg = b.congress === 119 && b.furthest !== 'law' ? ' <small>(in session)</small>' : '';
			return '<tr class="is-new" style="--k:' + (k * 18) + 'ms" data-id="' + esc(b.bill_id) + '">' +
				'<td><button type="button" class="od-bill" data-open="' + esc(b.bill_id) + '">' + esc(billNo(b)) + '<small>' + b.congress + 'th</small></button></td>' +
				'<td class="od-title-cell">' + esc(b.title || '') + (b.policy_area ? '<small>' + esc(b.policy_area) + '</small>' : '') + '</td>' +
				'<td>' + party + esc(sponsor) + '</td>' +
				'<td><span class="od-pill is-' + esc(b.coalition_at_intro || '') + '">' + esc(COAL[b.coalition_at_intro] || '–') + '</span>' + (b.orig_cross ? '<br><small>' + b.orig_cross + ' across</small>' : '') + '</td>' +
				'<td><span class="od-stage is-' + esc(b.furthest) + '">' + esc(stage) + '</span>' + inProg + '</td>' +
				'<td>' + esc(String(b.introduced_on || '').slice(0, 10)) + '</td></tr>';
		}
		function render(append, fresh) {
			if (!append) tbody.innerHTML = '';
			tbody.insertAdjacentHTML('beforeend', fresh.map(rowHtml).join(''));
			countEl.textContent = total == null ? 'Showing ' + BX.fmt(rows.length) : 'Showing ' + BX.fmt(rows.length) + ' of ' + BX.fmt(total) + ' bills';
			if (!rows.length) tbody.innerHTML = '<tr><td colspan="6" style="padding:28px 10px">No bills match. Try fewer filters.</td></tr>';
			more.hidden = !cursor;
		}
		function run(append) {
			var my = ++token;
			var p = params(append && cursor ? { cursor: cursor } : {});
			if (!append) { rows = []; cursor = null; countEl.textContent = 'Searching…'; }
			apiBox.textContent = apiUrl(params({}));
			getJSON(apiUrl(p)).then(function (j) {
				if (my !== token) return;
				if (!append) total = j.total;
				cursor = j.next_cursor;
				rows = rows.concat(j.bills || []);
				render(append, j.bills || []);
			}).catch(function (e) { if (my === token) countEl.textContent = 'The record could not be loaded (' + e.message + '). Try again.'; });
		}
		form.addEventListener('input', function (e) { clearTimeout(timer); timer = setTimeout(function () { syncUrl(); run(false); }, e.target.name === 'q' ? 320 : 0); });
		form.addEventListener('submit', function (e) { e.preventDefault(); syncUrl(); run(false); });
		more.addEventListener('click', function () { run(true); });
		$('[data-od-reset]').addEventListener('click', function () { form.reset(); syncUrl(); run(false); });
		$('[data-od-share]').addEventListener('click', function (e) { copy(location.href, e.currentTarget); });
		$('[data-od-apiurl]').addEventListener('click', function () { apiBox.hidden = !apiBox.hidden; });
		$('[data-od-csv]').addEventListener('click', function (e) {
			var btn = e.currentTarget, cap = 2000;
			var cols = ['bill_id', 'congress', 'bill_type', 'bill_number', 'title', 'introduced_on', 'sponsor_id', 'sponsor_name', 'sponsor_party', 'sponsor_state', 'policy_area', 'chamber', 'coalition_at_intro', 'orig_cross', 'furthest', 'became_law', 'latest_action_on', 'latest_action_text', 'congress_url'];
			var out = rows.slice(), cur = cursor;
			btn.disabled = true;
			(function next() {
				if (!cur || out.length >= cap) {
					download('btb-bills.csv', [cols.join(',')].concat(out.slice(0, cap).map(function (r) { return cols.map(function (c) { return csvCell(r[c]); }).join(','); })).join('\n'));
					btn.disabled = false; btn.textContent = 'Download CSV';
					return;
				}
				btn.textContent = 'Fetching ' + BX.fmt(out.length) + '…';
				getJSON(apiUrl(params({ cursor: cur }))).then(function (j) { out = out.concat(j.bills || []); cur = j.next_cursor; next(); }).catch(function () { cur = null; next(); });
			})();
		});
		tbody.addEventListener('click', function (e) {
			var tr = e.target.closest('tr[data-id]');
			if (tr) openBill(tr.getAttribute('data-id'), e.target.closest('button') || tr);
		});
		run(false);
		if (location.hash === '#browse' && init.toString()) setTimeout(function () { $('#browse').scrollIntoView(); }, 300);
	})();

	/* ---------- Bill drawer ---------- */
	var drawer = $('[data-od-drawer]'), lastFocus = null;
	function closeDrawer() { drawer.hidden = true; document.documentElement.style.overflow = ''; if (lastFocus) lastFocus.focus(); }
	$$('[data-od-close]').forEach(function (b) { b.addEventListener('click', closeDrawer); });
	document.addEventListener('keydown', function (e) {
		if (drawer.hidden) return;
		if (e.key === 'Escape') closeDrawer();
		if (e.key === 'Tab') {
			var f = $$('button, a[href], [tabindex="0"]', drawer).filter(function (x) { return x.offsetParent; });
			if (!f.length) return;
			if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
			else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
		}
	});
	var KEY = /^(8000|17000|5000|14000|36000|41000|E40000|28000|31000|H11100|10000)$/;
	function openBill(id, from) {
		lastFocus = from;
		var body = $('[data-od-drawer-body]');
		body.innerHTML = '<p class="od-d-kicker">' + esc(id) + '</p><p>Loading the record…</p>';
		drawer.hidden = false; document.documentElement.style.overflow = 'hidden';
		$('.od-drawer-panel').focus();
		getJSON(apiUrl({ route: 'bill', id: id })).then(function (b) {
			var acts = (b.actions || []).slice();
			var seen = {}, list = [];
			acts.forEach(function (a) { var k = a.action_on + '|' + a.action_text; if (!seen[k]) { seen[k] = 1; list.push(a); } });
			body.innerHTML = '<p class="od-d-kicker">' + esc(billNo(b)) + ' · ' + b.congress + 'th Congress</p>' +
				'<h2 class="od-d-title" id="od-drawer-title">' + esc(b.title || '') + '</h2>' +
				'<dl class="od-d-meta">' +
				'<div><dt>Sponsor</dt><dd>' + esc(b.sponsor_name || b.sponsor_id || '–') + '</dd></div>' +
				'<div><dt>Introduced</dt><dd>' + esc(BX.fmtDate(b.introduced_on)) + '</dd></div>' +
				'<div><dt>Day one</dt><dd>' + esc(COAL[b.coalition_at_intro] || '–') + (b.orig_cosponsors != null ? ' · ' + b.orig_cosponsors + ' original cosponsors, ' + b.orig_cross + ' from the other party' : '') + '</dd></div>' +
				'<div><dt>Got as far as</dt><dd>' + esc(STAGE[b.furthest] || b.furthest) + '</dd></div>' +
				'<div><dt>Policy area</dt><dd>' + esc(b.policy_area || '–') + '</dd></div>' +
				'<div><dt>Recorded actions</dt><dd>' + BX.fmt(list.length) + '</dd></div>' +
				'</dl>' +
				'<p class="od-d-links"><a href="' + esc(b.congress_url || ('https://www.congress.gov/')) + '">Congress.gov</a><a href="' + esc(apiUrl({ route: 'bill', id: id })) + '">This bill as JSON</a></p>' +
				'<h3 class="bx-h3">Timeline</h3><ol class="od-timeline">' + list.map(function (a) {
					return '<li class="' + (KEY.test(a.action_code || '') ? 'is-key' : '') + '"><time datetime="' + esc(String(a.action_on).slice(0, 10)) + '">' + esc(BX.fmtDate(a.action_on)) + (a.action_code ? ' · ' + esc(a.action_code) : '') + '</time>' + esc(a.action_text) + '</li>';
				}).join('') + '</ol>';
		}).catch(function () { body.innerHTML = '<p>This bill could not be loaded.</p>'; });
	}

	/* ================================================================
	   SQL console: DuckDB-WASM over Parquet on a CDN
	   ================================================================ */
	(function sql() {
		var box = $('[data-od-console]');
		if (!box || !C.catalog) return;
		var ta = $('[data-od-sql]', box), runBtn = $('[data-od-run]', box), status = $('[data-od-sql-status]', box);
		var out = $('[data-od-result]', box), engine = $('[data-od-engine]', box), csvBtn = $('[data-od-sql-csv]', box);
		var tables = C.catalog.tables || {};
		var conn = null, starting = null, last = null;
		var SAMPLES = [
			['Laws by Congress', "SELECT congress, count(*) AS bills,\n  count(*) FILTER (WHERE coalesce(law_identifiers,'') <> '') AS laws\nFROM bills GROUP BY congress ORDER BY congress;"],
			['Most cosponsored bills', "SELECT b.congress, b.bill_type || b.bill_number AS bill, left(b.title, 80) AS title, count(*) AS cosponsors\nFROM cosponsors c JOIN bills b USING (bill_id)\nGROUP BY ALL ORDER BY cosponsors DESC LIMIT 25;"],
			['Busiest committees', "SELECT committee_name, chamber, count(DISTINCT bill_id) AS bills\nFROM committees GROUP BY ALL ORDER BY bills DESC LIMIT 20;"],
			['Top subjects', "SELECT subject, count(*) AS bills FROM subjects\nGROUP BY subject ORDER BY bills DESC LIMIT 25;"],
			['Cross-party cosponsors', "-- Share of each member's cosponsorships that cross the aisle\nSELECT c.member_name, c.party, count(*) AS cosponsorships,\n  round(100 * avg((c.party <> b.sponsor_party AND c.party IN ('D','R') AND b.sponsor_party IN ('D','R'))::INT), 1) AS pct_cross_party\nFROM cosponsors c JOIN bills b USING (bill_id)\nGROUP BY ALL HAVING count(*) >= 300 ORDER BY pct_cross_party DESC LIMIT 20;"],
			['CBO-scored bills', "SELECT bill_id, published_on, left(title, 90) AS title FROM cbo_estimates\nORDER BY published_on DESC LIMIT 25;"],
			['Roll-call votes', "SELECT chamber, congress, count(*) AS roll_calls FROM vote_references\nGROUP BY ALL ORDER BY congress, chamber;"]
		];
		var samples = $('[data-od-samples]', box);
		SAMPLES.forEach(function (s) {
			var b = document.createElement('button'); b.type = 'button'; b.textContent = s[0];
			b.addEventListener('click', function () { ta.value = s[1]; run(); });
			samples.appendChild(b);
		});
		var schema = $('[data-od-schema]', box);
		schema.innerHTML = Object.keys(tables).map(function (t) {
			return '<div><b data-t="' + esc(t) + '">' + esc(t) + ' · ' + BX.fmt(tables[t].rows) + '</b>' + tables[t].columns.filter(function (c) { return !/^source_/.test(c[0]); }).map(function (c) { return esc(c[0]) + ' <span style="opacity:.6">' + esc(c[1].toLowerCase()) + '</span>'; }).join('<br>') + '</div>';
		}).join('');
		schema.addEventListener('click', function (e) { var b = e.target.closest('[data-t]'); if (b) { ta.value = 'SELECT * FROM ' + b.getAttribute('data-t') + ' LIMIT 50;'; run(); } });

		function start() {
			if (starting) return starting;
			engine.textContent = 'Starting the engine…';
			starting = import(C.duckdb).then(function (duckdb) {
				var bundles = duckdb.getJsDelivrBundles();
				return duckdb.selectBundle(bundles).then(function (bundle) {
					var workerUrl = URL.createObjectURL(new Blob(['importScripts("' + bundle.mainWorker + '");'], { type: 'text/javascript' }));
					var worker = new Worker(workerUrl);
					var db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
					return db.instantiate(bundle.mainModule, bundle.pthreadWorker).then(function () { URL.revokeObjectURL(workerUrl); return db.connect(); });
				});
			}).then(function (c) {
				conn = c;
				var stmts = Object.keys(tables).map(function (t) {
					var urls = tables[t].files.map(function (f) { return "'" + f.url.replace(/'/g, "''") + "'"; }).join(', ');
					return 'CREATE OR REPLACE VIEW ' + t + ' AS SELECT * FROM read_parquet([' + urls + '], union_by_name = true);';
				});
				return stmts.reduce(function (p, s) { return p.then(function () { return conn.query(s); }); }, Promise.resolve());
			}).then(function () {
				engine.textContent = 'DuckDB ready · ' + Object.keys(tables).length + ' tables · ' + BX.fmt(C.catalog.total_rows) + ' rows';
				engine.classList.add('is-ready');
			}).catch(function (e) {
				starting = null;
				engine.textContent = 'The engine could not start in this browser.';
				throw e;
			});
			return starting;
		}
		function render(table, ms) {
			var fields = table.schema.fields.map(function (f) { return f.name; });
			var n = table.numRows, show = Math.min(n, 1000), rows = [];
			for (var i = 0; i < show; i++) {
				var r = table.get(i), o = r.toJSON ? r.toJSON() : r;
				rows.push(fields.map(function (f) { var v = o[f]; return typeof v === 'bigint' ? Number(v) : (v instanceof Date ? v.toISOString().slice(0, 10) : v); }));
			}
			last = { fields: fields, rows: rows };
			csvBtn.disabled = !n;
			status.textContent = BX.fmt(n) + ' row' + (n === 1 ? '' : 's') + ' in ' + (ms / 1000).toFixed(2) + 's' + (n > show ? ' · showing the first ' + BX.fmt(show) : '');
			if (!n) { out.innerHTML = '<p class="od-result-empty">The query ran and returned no rows.</p>'; return; }
			out.innerHTML = '<table><thead><tr>' + fields.map(function (f) { return '<th scope="col">' + esc(f) + '</th>'; }).join('') + '</tr></thead><tbody>' + rows.map(function (r) {
				return '<tr>' + r.map(function (v) { var num = typeof v === 'number'; return '<td' + (num ? ' class="is-num"' : '') + ' title="' + esc(v == null ? '' : String(v).slice(0, 400)) + '">' + (v == null ? '<span style="opacity:.4">null</span>' : esc(num ? (Number.isInteger(v) ? BX.fmt(v) : String(+v.toFixed(4))) : String(v))) + '</td>'; }).join('') + '</tr>';
			}).join('') + '</tbody></table>';
		}
		function run() {
			var q = ta.value.trim();
			if (!q) return;
			runBtn.disabled = true;
			status.textContent = conn ? 'Running…' : 'Loading DuckDB (about 6 MB, once)…';
			var t0;
			start().then(function () { t0 = performance.now(); status.textContent = 'Running…'; return conn.query(q); })
				.then(function (table) { render(table, performance.now() - t0); })
				.catch(function (e) { out.innerHTML = '<div class="od-result-err">' + esc(String(e && e.message || e)) + '</div>'; status.textContent = 'Error'; })
				.then(function () { runBtn.disabled = false; });
		}
		runBtn.addEventListener('click', run);
		ta.addEventListener('keydown', function (e) {
			if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); run(); }
			if (e.key === 'Tab' && !e.shiftKey && !e.ctrlKey) { e.preventDefault(); var s = ta.selectionStart; ta.setRangeText('  ', s, ta.selectionEnd, 'end'); }
		});
		csvBtn.addEventListener('click', function () {
			if (!last) return;
			download('btb-query.csv', [last.fields.join(',')].concat(last.rows.map(function (r) { return r.map(csvCell).join(','); })).join('\n'));
		});
		/* Warm the engine when the console is near, so the first query feels instant. */
		if ('IntersectionObserver' in window) {
			var io = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { io.disconnect(); start().catch(function () {}); } }, { rootMargin: '400px 0px' });
			io.observe(box);
		}
		if (location.hash === '#sql') start().catch(function () {});
	})();

	/* ================================================================
	   API tester and snippets
	   ================================================================ */
	(function apiDocs() {
		var routes = $$('.od-route'), urlEl = $('[data-od-try-url]'), outEl = $('[data-od-try-out]'), btn = $('[data-od-try]');
		if (!routes.length) return;
		var current = routes[0].getAttribute('data-q');
		function setRoute(b) {
			routes.forEach(function (r) { r.setAttribute('aria-selected', r === b ? 'true' : 'false'); });
			current = b.getAttribute('data-q');
			urlEl.textContent = C.api + '?' + current;
		}
		routes.forEach(function (b) { b.addEventListener('click', function () { setRoute(b); send(); }); });
		setRoute(routes[0]);
		function highlight(json) {
			return esc(json).replace(/(&quot;[^&]*?&quot;)(\s*:)?/g, function (m, s, colon) { return colon ? '<span class="k">' + s + '</span>' + colon : '<span class="s">' + s + '</span>'; }).replace(/\b(-?\d+(\.\d+)?)\b/g, '<span class="n">$1</span>');
		}
		function send() {
			var t0 = performance.now();
			outEl.textContent = 'Requesting…';
			fetch(C.api + '?' + current).then(function (r) { return r.text().then(function (t) { return [r, t]; }); }).then(function (x) {
				var ms = Math.round(performance.now() - t0), txt = x[1];
				try {
					var j = JSON.parse(txt);
					if (j.bills && j.bills.length > 3) { j.bills = j.bills.slice(0, 3); j._note = 'trimmed to 3 rows for display'; }
					if (j.actions && j.actions.length > 8) { j.actions = j.actions.slice(0, 8); j._note = 'trimmed to 8 actions for display'; }
					if (j.body && (j.body.dots || j.body.tables)) { j.body = { _note: 'large body trimmed for display', keys: Object.keys(j.body) }; }
					txt = JSON.stringify(j, null, 2);
				} catch (e) { /* show raw */ }
				outEl.innerHTML = '<span style="opacity:.6">HTTP ' + x[0].status + ' · ' + ms + ' ms</span>\n' + highlight(txt.length > 9000 ? txt.slice(0, 9000) + '\n…' : txt);
			}).catch(function (e) { outEl.textContent = 'Request failed: ' + e.message; });
		}
		btn.addEventListener('click', send);
		$$('[data-od-copy]').forEach(function (b) { b.addEventListener('click', function () { copy(b.getAttribute('data-od-copy'), b); }); });
		var snip = $('[data-od-snippet]');
		var S = {
			js: "const API = '" + C.api + "';\n\n// Every bipartisan bill that became law in the 118th Congress\nlet cursor = null, bills = [];\ndo {\n  const url = `${API}?route=bills&congress=118&coalition=bipartisan&furthest=law&limit=50` + (cursor ? `&cursor=${encodeURIComponent(cursor)}` : '');\n  const page = await (await fetch(url)).json();\n  bills.push(...page.bills);\n  cursor = page.next_cursor;\n} while (cursor);\nconsole.log(bills.length, 'bills');",
			py: "import requests\n\nAPI = '" + C.api + "'\nbills, cursor = [], None\nwhile True:\n    params = {'route': 'bills', 'congress': 118, 'coalition': 'bipartisan', 'furthest': 'law', 'limit': 50}\n    if cursor:\n        params['cursor'] = cursor\n    page = requests.get(API, params=params, timeout=30).json()\n    bills += page['bills']\n    cursor = page.get('next_cursor')\n    if not cursor:\n        break\nprint(len(bills), 'bills')\n\n# Or skip the API and read the full warehouse with DuckDB:\n# import duckdb; duckdb.sql(\"SELECT count(*) FROM 'https://cdn.jsdelivr.net/gh/memereaper/btb-research-new@" + (C.catalog ? C.catalog.pinned_commit : 'main') + "/datasets/pathways-2026-10-28/tables/cosponsors.parquet'\")",
			sh: "curl -s '" + C.api + "?route=bills&q=broadband&limit=5' | jq '.bills[] | {bill_id, title, furthest}'\n\ncurl -s '" + C.api + "?route=bill&id=117-hr3684' | jq '.actions | length'",
			r: "library(jsonlite)\napi <- '" + C.api + "'\npage <- fromJSON(paste0(api, '?route=bills&congress=118&furthest=law&limit=50'))\nhead(page$bills[, c('bill_id', 'title', 'coalition_at_intro')])\n\n# Full tables with arrow:\n# library(arrow); read_parquet('https://cdn.jsdelivr.net/gh/memereaper/btb-research-new@" + (C.catalog ? C.catalog.pinned_commit : 'main') + "/datasets/pathways-2026-10-28/tables/bills.parquet')"
		};
		function showSnip(k) { snip.textContent = S[k]; }
		$$('input[name="od-lang"]').forEach(function (r) { r.addEventListener('change', function () { showSnip(r.value); }); });
		showSnip('js');
		var cite = $('[data-od-cite]'), cb = $('[data-od-copy-cite]');
		if (cite && cb) cb.addEventListener('click', function () { copy(cite.textContent, cb); });
		if ('IntersectionObserver' in window) {
			var io = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { io.disconnect(); send(); } }, { rootMargin: '200px 0px' });
			io.observe(outEl);
		}
	})();
})();
