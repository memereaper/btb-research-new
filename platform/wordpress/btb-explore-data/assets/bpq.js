/*
 * Investigation 002: The Bipartisanship Question.
 *
 * Every chart draws from window.BTBD.base and window.BTBD.deep (the same
 * findings the prose was written from) or from the read-only API. Motion is
 * driven by scroll position or by the reader's own input, and every view has
 * a reduced-motion path and a text equivalent. Uses BX from explore-core.js.
 */
(function () {
	'use strict';
	var BX = window.BX, C = window.BTBD || {};
	var root = document.querySelector('[data-bpq]');
	if (!root || !BX) return;
	var B = C.base || {}, D = C.deep || {};
	var reduced = BX.reduced();
	var NS = 'http://www.w3.org/2000/svg';
	var COAL = ['bipartisan', 'same_party', 'solo'];
	var COAL_LABEL = { bipartisan: 'Bipartisan on day one', same_party: 'Same party only', solo: 'No cosponsors' };
	var INK = { bip: '#D6FF3D', same: '#9C97E0', solo: '#514B80', d: '#2E2BFF', r: '#FF5A36', ink: '#120F2E', pink: '#FF9AD5' };

	function $(s, el) { return (el || document).querySelector(s); }
	function $$(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }
	function svg(name, attrs, parent) {
		var e = document.createElementNS(NS, name);
		for (var k in attrs) e.setAttribute(k, attrs[k]);
		if (parent) parent.appendChild(e);
		return e;
	}
	function pct(v, d) { return (+v).toFixed(d == null ? 1 : d) + '%'; }
	function pick(rows, f, v) { for (var i = 0; i < (rows || []).length; i++) if (rows[i][f] === v) return rows[i]; return null; }
	function hash(i) { var h = (i + 1) * 2654435761 >>> 0; return (h % 1000) / 1000; }
	function onView(el, fn, margin) {
		if (!el) return;
		if (!('IntersectionObserver' in window)) { fn(); return; }
		var io = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { io.disconnect(); fn(); } }, { rootMargin: margin || '0px 0px -12% 0px' });
		io.observe(el);
	}
	function countDecimal(el, to, d, ms) {
		if (!el) return;
		var suffix = '%';
		if (reduced) { el.textContent = to.toFixed(d) + suffix; return; }
		var from = parseFloat(el.getAttribute('data-v') || '0') || 0, start = performance.now(), dur = ms || 900;
		el.setAttribute('data-v', to);
		cancelAnimationFrame(el._r);
		(function tick(now) {
			var t = Math.min(1, (now - start) / dur);
			el.textContent = (from + (to - from) * BX.easeInOut(t)).toFixed(d) + suffix;
			if (t < 1) el._r = requestAnimationFrame(tick);
		})(start);
	}
	function api(params) {
		var q = Object.keys(params).map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]); }).join('&');
		return BX.load(C.api + '?' + q);
	}
	function measure(el) { return Math.max(300, el.clientWidth || el.getBoundingClientRect().width || 600); }
	function onResize(el, fn) {
		var last = 0;
		if ('ResizeObserver' in window) new ResizeObserver(function () { var w = el.clientWidth; if (Math.abs(w - last) > 8) { last = w; fn(); } }).observe(el);
		else window.addEventListener('resize', fn);
	}

	/* ================================================================
	   Scroll-driven pieces: the split cover and chapter title cards
	   ================================================================ */
	(function scrubs() {
		var cover = $('[data-bpq-cover]');
		var cards = $$('[data-bx-tc]');
		if (reduced) { cards.forEach(function (c) { c.style.setProperty('--p', 1); }); if (cover) cover.style.setProperty('--s', 1); return; }
		var vh = window.innerHeight, live = new Set(), queued = false;
		if ('IntersectionObserver' in window) {
			var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) live.add(e.target); else live.delete(e.target); }); run(); }, { rootMargin: '120px 0px' });
			cards.forEach(function (c) { io.observe(c); });
			if (cover) io.observe(cover);
		} else { cards.forEach(function (c) { live.add(c); }); if (cover) live.add(cover); }
		function run() {
			if (queued) return;
			queued = true;
			requestAnimationFrame(function () {
				queued = false;
				var w = [];
				live.forEach(function (el) {
					var r = el.getBoundingClientRect(), span = r.height - vh;
					if (el === cover) { w.push([el, '--s', span > 0 ? Math.min(1, Math.max(0, -r.top / (span * 0.8))) : 1]); return; }
					w.push([el, '--p', span > 0 ? Math.min(1, Math.max(0, (-r.top + vh * 0.35) / (span * 0.7))) : 1]);
				});
				w.forEach(function (x) { var v = x[2].toFixed(4); if (x[0].style.getPropertyValue(x[1]) !== v) x[0].style.setProperty(x[1], v); });
			});
		}
		window.addEventListener('scroll', run, { passive: true });
		window.addEventListener('resize', function () { vh = window.innerHeight; run(); });
		run();
	})();

	/* The chapter rail switches on once the reader reaches chapter 1. */
	(function rail() {
		var r = $('.bx-chapters'), ch1 = $('#field');
		if (!r || !ch1) return;
		var tick = false;
		function up() { tick = false; r.classList.toggle('is-on', ch1.getBoundingClientRect().top < window.innerHeight * 0.5); }
		window.addEventListener('scroll', function () { if (!tick) { tick = true; requestAnimationFrame(up); } }, { passive: true });
		up();
	})();

	/* ================================================================
	   Guess
	   ================================================================ */
	var guessValue = null;
	(function guess() {
		var box = $('[data-bpq-guess]');
		if (!box) return;
		var range = $('[data-bpq-guess-range]', box), out = $('[data-bpq-guess-value]', box), n = $('[data-bpq-guess-n]', box);
		var lock = $('[data-bpq-guess-lock]', box), res = $('[data-bpq-guess-result]', box);
		var total = +range.getAttribute('data-total'), answer = +box.getAttribute('data-answer');
		function paint() {
			var v = +range.value;
			out.textContent = v + '%';
			n.textContent = 'about ' + BX.fmt(total * v / 100) + ' of ' + BX.fmt(total) + ' laws';
			range.setAttribute('aria-valuetext', v + ' percent');
		}
		range.addEventListener('input', paint);
		paint();
		lock.addEventListener('click', function () {
			var v = +range.value, diff = v - answer;
			guessValue = v;
			box.classList.add('is-locked');
			lock.disabled = true; range.disabled = true;
			var msg = Math.abs(diff) <= 5 ? '<strong>Very close.</strong> ' : diff < 0 ? '<strong>Higher than you guessed.</strong> ' : '<strong>Lower than you guessed.</strong> ';
			res.innerHTML = msg + 'The answer is <strong>' + answer.toFixed(0) + '%</strong>. About a third of all bills started with a partner across the aisle, but seven in ten laws did. Scroll on to watch it happen.';
			res.hidden = false;
			var cb = $('[data-bpq-guess-callback]');
			if (cb) { cb.textContent = 'You guessed ' + v + '%.'; cb.hidden = false; }
		});
	})();

	/* ================================================================
	   Chapter 1: every bill as a square
	   ================================================================ */
	(function chapter1() {
		var canvas = $('[data-bpq-field]');
		if (!canvas) return;
		var labelsEl = $('[data-bpq-labels]'), counter = $('[data-bpq-counter]'), counterLabel = $('[data-bpq-counter-label]'), key = $('[data-bpq-key]');
		var steps = $$('.bpq-ch1 .bx-step');
		var field = null, data = null, pending = null, stepNow = 'all';

		function load() {
			if (!pending) pending = api({ route: 'findings', key: 'bipartisanship-field' }).then(function (r) { data = decode(r.body); build(); return data; });
			return pending;
		}
		function decode(f) {
			var n = f.n, a = f.alphabet, coal = new Uint8Array(n), stage = new Uint8Array(n), cer = new Uint8Array(n);
			for (var i = 0; i < n; i++) {
				var v = a.indexOf(f.dots[i]);
				coal[i] = Math.floor(v / 10); stage[i] = Math.floor((v % 10) / 2); cer[i] = v % 2;
			}
			return { n: n, coal: coal, stage: stage, cer: cer };
		}
		/* palette: 0 neutral, 1 bip, 2 same, 3 solo, 4 indep, 5 faint, 6 white */
		var PAL = ['#5D5794', INK.bip, INK.same, INK.solo, '#7D7A90', '#231F48', '#FFFFFF'];
		var GROUPS = [{ key: 0, label: 'Bipartisan on day one' }, { key: 1, label: 'Same party only' }, { key: 2, label: 'No cosponsors' }, { key: 3, label: 'Independent sponsor' }];
		var layouts = {};

		function build() {
			var n = data.n;
			field = new BX.DotField(canvas, { n: n, fill: 0.8, palette: PAL, ringColor: '#FFFFFF', onLayout: function (f, labels) { drawLabels(labels); } });
			layouts.grid = BX.gridLayout({ pad: 2 });
			layouts.plots = BX.plotsLayout(function (i) { return data.coal[i]; }, GROUPS, { labelH: 26, gap: 14 });
			layouts.laws = function (w, h, n2, f) {
				var P = layouts.plots(w, h, n2, f);
				var idx = [];
				for (var i = 0; i < n2; i++) if (data.stage[i] === 4) idx.push(i);
				idx.sort(function (x, y) { return data.coal[x] - data.coal[y] || x - y; });
				var m = idx.length, labelH = 30;
				var cols = Math.max(10, Math.round(Math.sqrt(m * w / Math.max(1, h - labelH) * 1.0)));
				var cell = Math.min(w / cols, (h - labelH) / Math.ceil(m / cols));
				cols = Math.floor(w / cell);
				var ox = (w - cols * cell) / 2 + cell / 2, oy = labelH + cell / 2;
				var x = new Float32Array(P.x), y = new Float32Array(P.y);
				for (var k = 0; k < m; k++) { x[idx[k]] = ox + (k % cols) * cell; y[idx[k]] = oy + Math.floor(k / cols) * cell; }
				var b = 0; for (k = 0; k < m; k++) if (data.coal[idx[k]] === 0) b++;
				return { x: x, y: y, cell: cell, labels: [{ key: 'laws', label: BX.fmt(m) + ' bills became law', count: b, x: ox - cell / 2, y: 0, note: BX.pct(b, m, 0) + ' bipartisan' }] };
			};
			field.applyLayout(layouts.grid, { instant: true });
			field.applyStyle(styleFor('all'), { instant: true });
			field.draw();
			if (stepNow !== 'all') go(stepNow, true);
		}
		function styleFor(step) {
			var c = data.coal, s = data.stage, cer = data.cer;
			if (step === 'all') return function () { return [0, 0.9, 1]; };
			if (step === 'coalition' || step === 'plots') return function (i) { return [c[i] + 1, 1, 1]; };
			if (step === 'laws') return function (i) { return s[i] === 4 ? [c[i] + 1, 1, 1.25] : [5, 1, 0.9]; };
			if (step === 'lawsOnly') return function (i) { return s[i] === 4 ? [c[i] + 1, 1, 1] : [5, 0, 0.4]; };
			if (step === 'ceremonial') return function (i) { return s[i] === 4 ? (cer[i] ? [c[i] + 1, 0.3, 0.8, 1] : [c[i] + 1, 1, 1]) : [5, 0, 0.4]; };
			return function () { return [0, 1, 1]; };
		}
		function layoutFor(step) {
			if (step === 'all' || step === 'coalition') return layouts.grid;
			if (step === 'plots' || step === 'laws') return layouts.plots;
			return layouts.laws;
		}
		var labelEls = {};
		function drawLabels(labels) {
			if (!labelsEl) return;
			var keep = {};
			labels.forEach(function (L) {
				var el = labelEls[L.key];
				if (!el) { el = labelEls[L.key] = document.createElement('div'); el.className = 'bpq-plot-label'; labelsEl.appendChild(el); }
				var lawCount = 0;
				if (data && typeof L.key === 'number') for (var i = 0; i < data.n; i++) if (data.coal[i] === L.key && data.stage[i] === 4) lawCount++;
				el.innerHTML = L.key === 'laws' ? BX.esc(L.label) + ' <b>' + BX.esc(L.note) + '</b>' : BX.esc(L.label) + ' <small>' + BX.fmt(L.count) + ' bills</small>' + (stepNow === 'laws' ? ' <b>' + BX.fmt(lawCount) + ' laws</b>' : '');
				el.style.transform = 'translate(' + L.x + 'px,' + (L.y + 2) + 'px)';
				el.style.opacity = 1;
				keep[L.key] = 1;
			});
			Object.keys(labelEls).forEach(function (k) { if (!keep[k]) labelEls[k].style.opacity = 0; });
		}
		function counterFor(step) {
			if (!data) return;
			var n = data.n, laws = 0, bip = 0, lawsNC = 0;
			for (var i = 0; i < n; i++) { if (data.stage[i] === 4) { laws++; if (!data.cer[i]) lawsNC++; } if (data.coal[i] === 0) bip++; }
			var map = { all: [n, 'bills introduced'], coalition: [bip, 'bipartisan on day one'], plots: [n, 'bills, three coalitions'], laws: [laws, 'became law'], lawsOnly: [laws, 'laws'], ceremonial: [lawsNC, 'laws, not ceremonial'] };
			var m = map[step] || map.all;
			BX.countTo(counter, m[0], 700);
			counterLabel.textContent = m[1];
		}
		function go(step, instant) {
			stepNow = step;
			if (key) key.classList.toggle('is-on', step !== 'all');
			if (!field) return;
			var toLaws = step === 'lawsOnly' || step === 'ceremonial';
			field.applyLayout(layoutFor(step));
			if (step === 'plots' || step === 'laws' || toLaws) drawLabels(field.labels); else drawLabels([]);
			field.applyStyle(styleFor(step));
			field.transition({
				instant: instant,
				duration: toLaws ? 1200 : 1000,
				delay: function (i) { return step === 'coalition' ? hash(i) * 500 : toLaws ? (data.stage[i] === 4 ? hash(i) * 600 : 0) : (field.y[i] / Math.max(1, field.h)) * 420 + hash(i) * 160; }
			});
			counterFor(step);
		}
		BX.steps(steps, function (step) { go(step); });
		onView(canvas, load, '1200px 0px');
	})();

	/* ================================================================
	   Chapter 2: gates
	   ================================================================ */
	(function gates() {
		var host = $('[data-bpq-gates-chart]');
		if (!host || !D.funnel) return;
		var F = {}; D.funnel.forEach(function (r) { F[r.coalition] = r; });
		var G = [['n', 'Introduced', 'every bill'], ['committee_action', 'Committee action', 'hearing, markup, report'], ['cleared_committee', 'Out of committee', 'reported or discharged'], ['passed_one', 'Passed a chamber', ''], ['passed_both', 'Passed both', ''], ['law', 'Became law', '']];
		var mode = 'per1000', built = false;
		var keyEl = document.createElement('div'); keyEl.className = 'bpq-gates-key';
		keyEl.innerHTML = '<span><i style="background:' + INK.ink + ';box-shadow:inset 3px 0 0 ' + INK.bip + '"></i>Bipartisan on day one</span><span><i style="background:' + INK.same + '"></i>Same party only</span><span><i style="background:#C9C4E4"></i>No cosponsors</span>';
		host.appendChild(keyEl);
		var read = document.createElement('p'); read.className = 'bpq-cap'; read.setAttribute('aria-live', 'polite');
		var rows = G.map(function (g, gi) {
			var row = document.createElement('div');
			row.className = 'bpq-gate'; row.tabIndex = 0;
			row.innerHTML = '<div class="bpq-gate-name">' + g[1] + (g[2] ? '<small>' + g[2] + '</small>' : '') + '</div><div class="bpq-gate-bars">' +
				COAL.map(function (c) { return '<div class="bpq-bar is-' + (c === 'bipartisan' ? 'bip' : c === 'same_party' ? 'same' : 'solo') + '"><i></i><span></span></div>'; }).join('') + '</div><div class="bpq-gate-x"></div>';
			host.appendChild(row);
			function say() {
				if (gi === 0) { read.textContent = 'Every bill starts here: ' + COAL.map(function (c) { return BX.fmt(F[c].n) + ' ' + COAL_LABEL[c].toLowerCase(); }).join(', ') + '.'; return; }
				var prev = G[gi - 1][0];
				read.textContent = g[1] + ': ' + COAL.map(function (c) { return COAL_LABEL[c] + ' ' + BX.fmt(F[c][g[0]]) + ' of ' + BX.fmt(F[c].n) + ' (' + BX.pct(F[c][g[0]], F[c].n) + '; ' + BX.pct(F[c][g[0]], F[c][prev], 0) + ' of those at the previous gate)'; }).join('. ') + '.';
			}
			row.addEventListener('mouseenter', say); row.addEventListener('focus', say);
			return row;
		});
		host.appendChild(read);
		function val(c, gi) {
			var k = G[gi][0];
			if (mode === 'per1000') return 1000 * F[c][k] / F[c].n;
			if (gi === 0) return 100;
			return 100 * F[c][k] / Math.max(1, F[c][G[gi - 1][0]]);
		}
		function draw() {
			rows.forEach(function (row, gi) {
				var vals = COAL.map(function (c) { return val(c, gi); });
				var max = mode === 'per1000' ? Math.max.apply(null, vals) : 100;
				$$('.bpq-bar', row).forEach(function (bar, ci) {
					var w = built ? Math.max(0.6, 100 * vals[ci] / max) : 0;
					bar.querySelector('i').style.width = w + '%';
					bar.style.setProperty('--w', w + '%');
					bar.querySelector('span').textContent = mode === 'per1000' ? BX.fmt(vals[ci]) : vals[ci].toFixed(0) + '%';
				});
				var x = row.querySelector('.bpq-gate-x');
				x.innerHTML = gi === 0 ? '' : (vals[0] / Math.max(0.0001, vals[1])).toFixed(1) + '×<small>vs same party</small>';
			});
		}
		$$('input[name="bpq-gate-mode"]').forEach(function (r) { r.addEventListener('change', function () { mode = r.value; draw(); }); });
		draw();
		onView(host, function () { built = true; draw(); });
	})();

	/* ================================================================
	   Chapter 3: dose and power
	   ================================================================ */
	(function dose() {
		var host = $('[data-bpq-dose]');
		if (!host || !B.dose_response) return;
		var rows = B.dose_response, canvas = $('[data-bpq-waffle]', host);
		var big = $('[data-bpq-dose-big]', host), nEl = $('[data-bpq-dose-n]', host);
		var PAL = ['#3C39FF', '#9E9CFF', INK.bip];
		var f = new BX.DotField(canvas, { n: 1000, fill: 0.78, palette: PAL });
		f.applyLayout(BX.gridLayout({ cols: 40 }), { instant: true });
		f.applyStyle(function () { return [0, 1, 0.9]; }, { instant: true });
		f.draw();
		var order = []; for (var i = 0; i < 1000; i++) order.push(i);
		order.sort(function (a, b) { return hash(a) - hash(b); });
		var rank = new Uint16Array(1000); order.forEach(function (v, k) { rank[v] = k; });
		var seen = false;
		function show(idx) {
			var r = rows[idx], law = Math.round(r.pct_became_law * 10), one = Math.round(r.pct_passed_one_chamber * 10);
			f.applyStyle(function (j) { var k = rank[j]; return k < law ? [2, 1, 1.15] : k < one ? [1, 1, 1] : [0, 1, 0.9]; });
			f.transition({ duration: 700, delay: function (j) { return (rank[j] / 1000) * 350; } });
			countDecimal(big, r.pct_became_law, 1);
			var label = r.original_cross_party_cosponsors === '0' ? 'no original cosponsor from the other party (same-party cosponsors only)' : r.original_cross_party_cosponsors + ' original cosponsor' + (r.original_cross_party_cosponsors === '1' ? '' : 's') + ' from the other party';
			nEl.textContent = BX.fmt(r.bills) + ' bills with ' + label + '. ' + r.pct_passed_one_chamber.toFixed(1) + '% passed a chamber.';
		}
		var current = 1;
		$$('input[name="bpq-dose"]', host).forEach(function (r) { r.addEventListener('change', function () { current = +r.value; if (seen) show(current); }); });
		onView(host, function () { seen = true; show(current); });

		/* Power: majority vs minority sponsors */
		var pw = $('[data-bpq-power]');
		if (pw && B.majority_sponsor) {
			var groups = [['Majority-party sponsor', B.majority_sponsor], ['Minority-party sponsor', B.minority_sponsor]];
			var max = 0;
			groups.forEach(function (g) { g[1].forEach(function (r) { max = Math.max(max, r.pct_became_law); }); });
			pw.innerHTML = groups.map(function (g) {
				return '<div class="bpq-pw"><h4>' + g[0] + '</h4>' + COAL.map(function (c) {
					var r = pick(g[1], 'coalition', c);
					return '<div class="bpq-pw-row"><span>' + COAL_LABEL[c] + '</span><div class="bpq-bar is-' + (c === 'bipartisan' ? 'bip' : 'same') + '"><i data-w="' + (100 * r.pct_became_law / max) + '"></i></div><b>' + r.pct_became_law.toFixed(2) + '%</b></div>';
				}).join('') + '</div>';
			}).join('');
			onView(pw, function () { $$('i[data-w]', pw).forEach(function (i, k) { setTimeout(function () { i.style.width = i.getAttribute('data-w') + '%'; }, reduced ? 0 : k * 80); }); });
		}
	})();

	/* ================================================================
	   Line chart helper (time to law, snowball, trend)
	   ================================================================ */
	function lineChart(host, o) {
		var tip = document.createElement('div'); tip.className = 'bpq-chart-tip'; tip.hidden = true;
		var state = { i: null };
		function build() {
			host.innerHTML = '';
			host.appendChild(tip);
			var W = measure(host), small = W < 560, H = o.height || (small ? 300 : 380);
			var m = { l: small ? 36 : 48, r: o.right != null ? (small ? 70 : o.right) : 20, t: 18, b: 40 };
			var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', role: 'presentation' }, host);
			var iw = W - m.l - m.r, ih = H - m.t - m.b;
			var xs = o.x, x0 = o.xmin != null ? o.xmin : xs[0], x1 = o.xmax != null ? o.xmax : xs[xs.length - 1];
			var ymax = o.ymax || Math.max.apply(null, o.series.map(function (sr) { return Math.max.apply(null, sr.values); })) * 1.12;
			function X(v) { return m.l + (v - x0) / (x1 - x0) * iw; }
			function Y(v) { return m.t + ih - v / ymax * ih; }
			var g = svg('g', {}, s);
			o.yticks(ymax).forEach(function (t) {
				svg('line', { x1: m.l, x2: m.l + iw, y1: Y(t), y2: Y(t), stroke: o.grid || 'rgba(18,15,46,.12)' }, g);
				var tx = svg('text', { x: m.l - 8, y: Y(t) + 4, 'text-anchor': 'end', 'font-size': 11, fill: o.axis || '#625C80' }, g); tx.textContent = o.yfmt(t);
			});
			o.xticks.forEach(function (t) {
				var tx = svg('text', { x: X(t[0]), y: m.t + ih + 22, 'text-anchor': 'middle', 'font-size': 11, fill: o.axis || '#625C80' }, g); tx.textContent = t[1];
			});
			if (o.xlabel) { var xl = svg('text', { x: m.l + iw, y: H - 4, 'text-anchor': 'end', 'font-size': 11, fill: o.axis || '#625C80' }, g); xl.textContent = o.xlabel; }
			var rule = svg('line', { y1: m.t, y2: m.t + ih, stroke: o.ruleColor || '#120F2E', 'stroke-dasharray': '3 3', opacity: 0 }, s);
			var dots = [];
			o.series.forEach(function (sr, si) {
				var d = sr.values.map(function (v, k) { return (k ? 'L' : 'M') + X(xs[k]).toFixed(1) + ',' + Y(v).toFixed(1); }).join('');
				if (sr.under) svg('path', { d: d + 'L' + X(xs[xs.length - 1]) + ',' + Y(0) + 'L' + X(xs[0]) + ',' + Y(0) + 'Z', fill: sr.color, opacity: 0.08 }, s);
				var p = svg('path', { d: d, class: 'bpq-line bpq-draw', stroke: sr.color, 'stroke-width': sr.width || 3, 'stroke-dasharray': sr.dash || null }, s);
				if (!sr.dash) { var len = p.getTotalLength ? p.getTotalLength() : 2000; p.style.setProperty('--len', Math.ceil(len)); p.style.transitionDelay = (si * 160) + 'ms'; }
				if (sr.label) {
					var lv = sr.values[sr.values.length - 1];
					var lt = svg('text', { x: X(xs[xs.length - 1]) + 8, y: Y(lv) + 4 + (sr.labelDy || 0), 'font-size': 12, 'font-weight': 600, fill: sr.labelColor || sr.color }, s); lt.textContent = sr.label;
				}
				dots.push(svg('circle', { r: 5, fill: sr.color, stroke: o.dotStroke || '#F6F0E2', 'stroke-width': 2, opacity: 0 }, s));
			});
			function setI(i) {
				state.i = i;
				if (i == null) { tip.hidden = true; rule.setAttribute('opacity', 0); dots.forEach(function (d) { d.setAttribute('opacity', 0); }); return; }
				var px = X(xs[i]);
				rule.setAttribute('x1', px); rule.setAttribute('x2', px); rule.setAttribute('opacity', 0.6);
				o.series.forEach(function (sr, si) { dots[si].setAttribute('cx', px); dots[si].setAttribute('cy', Y(sr.values[i])); dots[si].setAttribute('opacity', 1); });
				tip.innerHTML = o.tip(i);
				tip.hidden = false;
				var scale = host.clientWidth / W;
				var top = Math.min.apply(null, o.series.map(function (sr) { return Y(sr.values[i]); }));
				tip.style.left = Math.max(80, Math.min(host.clientWidth - 80, px * scale)) + 'px';
				tip.style.top = (top * scale) + 'px';
			}
			s.addEventListener('pointermove', function (e) {
				var r = s.getBoundingClientRect(), vx = (e.clientX - r.left) / r.width * W;
				var best = 0, bd = Infinity;
				xs.forEach(function (v, k) { var d = Math.abs(X(v) - vx); if (d < bd) { bd = d; best = k; } });
				setI(best);
			});
			s.addEventListener('pointerleave', function () { setI(null); });
			host.onkeydown = function (e) {
				if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
				e.preventDefault();
				var i = state.i == null ? (e.key === 'ArrowRight' ? 0 : xs.length - 1) : Math.max(0, Math.min(xs.length - 1, state.i + (e.key === 'ArrowRight' ? 1 : -1)));
				setI(i);
			};
			host.onblur = function () { setI(null); };
			if (host._drawn) host.classList.add('is-drawn');
		}
		build();
		onResize(host, build);
		onView(host, function () { host._drawn = true; requestAnimationFrame(function () { host.classList.add('is-drawn'); }); });
		return { rebuild: build };
	}

	/* ================================================================
	   Chapter 4: time to law, snowball, late arrivals
	   ================================================================ */
	(function clock() {
		var host = $('[data-bpq-curve-chart]');
		var T = D.time_to_law;
		if (host && T) {
			var days = T.days;
			lineChart(host, {
				x: days, right: 110,
				series: [
					{ values: T.curves.solo.pct_law_by_day, color: '#B4AED8', label: 'No cosponsors', width: 2.5 },
					{ values: T.curves.same_party.pct_law_by_day, color: INK.same, label: 'Same party', labelColor: '#5E58A6', width: 2.5 },
					{ values: T.curves.bipartisan.pct_law_by_day, color: INK.ink, label: 'Bipartisan', width: 3.5, under: true }
				],
				yticks: function (m) { var out = [], step = m > 3 ? 1 : 0.5; for (var v = 0; v <= m; v += step) out.push(+v.toFixed(1)); return out; },
				yfmt: function (v) { return v + '%'; },
				xticks: [[0, 'Day 0'], [180, '6 mo'], [365, '1 yr'], [540, '18 mo'], [730, '2 yrs']],
				tip: function (i) {
					var d = days[i];
					return '<b>' + (d === 0 ? 'Day of introduction' : 'Within ' + d + ' days') + '</b><br>Bipartisan ' + T.curves.bipartisan.pct_law_by_day[i].toFixed(2) + '%<br>Same party ' + T.curves.same_party.pct_law_by_day[i].toFixed(2) + '%<br>No cosponsors ' + T.curves.solo.pct_law_by_day[i].toFixed(2) + '%';
				}
			});
		}
		var sh = $('[data-bpq-snow-chart]'), S = D.snowball;
		if (sh && S) {
			var st = S.by_furthest_stage;
			lineChart(sh, {
				x: S.days, right: 120,
				series: [
					{ values: st.introduced.avg_cross_party_cosponsors_by_day, color: '#C9C4E4', label: 'Never left committee', labelColor: '#7A74A8', width: 2 },
					{ values: st.cleared_committee.avg_cross_party_cosponsors_by_day, color: INK.same, label: 'Out of committee', labelColor: '#5E58A6', width: 2.5 },
					{ values: st.passed_one.avg_cross_party_cosponsors_by_day, color: INK.d, label: 'Passed a chamber', width: 2.5 },
					{ values: st.law.avg_cross_party_cosponsors_by_day, color: INK.ink, label: 'Became law', width: 3.5 }
				],
				yticks: function (m) { var out = []; for (var v = 0; v <= m; v += 2) out.push(v); return out; },
				yfmt: function (v) { return v; },
				xticks: [[0, 'Day 0'], [180, '6 mo'], [365, '1 yr'], [730, '2 yrs']],
				tip: function (i) {
					var d = S.days[i];
					return '<b>' + (d === 0 ? 'Day of introduction' : 'After ' + d + ' days') + '</b><br>Became law ' + st.law.avg_cross_party_cosponsors_by_day[i].toFixed(1) + '<br>Passed a chamber ' + st.passed_one.avg_cross_party_cosponsors_by_day[i].toFixed(1) + '<br>Out of committee ' + st.cleared_committee.avg_cross_party_cosponsors_by_day[i].toFixed(1) + '<br>Never left committee ' + st.introduced.avg_cross_party_cosponsors_by_day[i].toFixed(1);
				}
			});
		}
		$$('[data-bpq-count]').forEach(function (el) {
			var to = +el.getAttribute('data-bpq-count'), d = +el.getAttribute('data-d') || 1;
			el.textContent = (0).toFixed(d) + '%';
			onView(el, function () { countDecimal(el, to, d, 1100); });
		});
	})();

	/* ================================================================
	   Chapter 5: committees and policy areas, sortable
	   ================================================================ */
	(function rank() {
		var host = $('[data-bpq-rank]');
		if (!host) return;
		var list = $('[data-bpq-rank-list]', host), sortSel = $('[data-bpq-rank-sort]', host);
		var metricBox = $('[data-bpq-rank-metric]', host), chamberBox = $('[data-bpq-rank-chamber]', host);
		var by = 'committee', metric = 'law', chamber = '', sort = 'gap';
		var ROW = window.matchMedia('(max-width: 900px)').matches ? 64 : 46;
		var com = (D.committees || []).map(function (r) {
			return { id: 'c:' + r.chamber + ':' + r.committee, name: r.committee.replace(/ Committee$/, ''), sub: r.chamber + ' · ' + BX.fmt(r.bills) + ' bills · ' + r.pct_bipartisan + '% bipartisan', chamber: r.chamber, n: r.bills, share: r.pct_bipartisan, law: [r.pct_law_bipartisan, r.pct_law_other], cleared: [r.pct_cleared_bipartisan, r.pct_cleared_other] };
		});
		var pol = (B.policy_areas || []).map(function (r) {
			return { id: 'p:' + r.policy_area, name: r.policy_area, sub: BX.fmt(r.n) + ' bills · ' + r.share_bip + '% bipartisan', chamber: '', n: r.n, share: r.share_bip, law: [r.law_bip, r.law_not], cleared: null };
		});
		var els = {};
		function draw() {
			var rows = (by === 'committee' ? com : pol).filter(function (r) { return !chamber || by !== 'committee' || r.chamber === chamber; });
			var m = by === 'policy' ? 'law' : metric;
			var v = function (r) { return r[m] || r.law; };
			rows.sort(function (a, b) {
				if (sort === 'gap') return (v(b)[0] - v(b)[1]) - (v(a)[0] - v(a)[1]);
				if (sort === 'bip') return v(b)[0] - v(a)[0];
				if (sort === 'share') return b.share - a.share;
				return b.n - a.n;
			});
			var max = 0; rows.forEach(function (r) { max = Math.max(max, v(r)[0], v(r)[1]); });
			max = max <= 5 ? Math.ceil(max) : Math.ceil(max / 5) * 5;
			var keep = {};
			rows.forEach(function (r, i) {
				var el = els[r.id];
				if (!el) {
					el = els[r.id] = document.createElement('li');
					el.className = 'bpq-row';
					el.tabIndex = 0;
					el.innerHTML = '<div class="bpq-row-name"></div><div class="bpq-row-track"><span class="bpq-row-link"></span><span class="bpq-row-dot is-oth"></span><span class="bpq-row-dot is-bip"></span></div><div class="bpq-row-val"></div>';
					el.style.opacity = 0;
					el.style.transform = 'translateY(' + (i * ROW + 20) + 'px)';
					list.appendChild(el);
				}
				var a = v(r)[0], b = v(r)[1], lo = Math.min(a, b), hi = Math.max(a, b);
				el.querySelector('.bpq-row-name').innerHTML = BX.esc(r.name) + '<small>' + BX.esc(r.sub) + '</small>';
				el.querySelector('.bpq-row-val').innerHTML = '<b>' + a.toFixed(a < 1 ? 2 : 1) + '%</b> vs ' + b.toFixed(b < 1 ? 2 : 1) + '%';
				el.setAttribute('aria-label', r.name + ': ' + a + '% of bipartisan bills versus ' + b + '% of other bills ' + (m === 'law' ? 'became law' : 'came out of committee'));
				var link = el.querySelector('.bpq-row-link'), dots = el.querySelectorAll('.bpq-row-dot');
				link.style.left = (100 * lo / max) + '%'; link.style.width = (100 * (hi - lo) / max) + '%';
				dots[0].style.left = (100 * b / max) + '%'; dots[1].style.left = (100 * a / max) + '%';
				requestAnimationFrame(function () { el.style.opacity = 1; el.style.transform = 'translateY(' + (i * ROW) + 'px)'; });
				keep[r.id] = 1;
			});
			Object.keys(els).forEach(function (k) { if (!keep[k]) { els[k].remove(); delete els[k]; } });
			list.style.height = (rows.length * ROW) + 'px';
			metricBox.style.opacity = by === 'policy' ? 0.4 : 1;
			$$('input', metricBox).forEach(function (i) { i.disabled = by === 'policy'; });
			chamberBox.style.opacity = by === 'policy' ? 0.4 : 1;
			$$('input', chamberBox).forEach(function (i) { i.disabled = by === 'policy'; });
		}
		$$('input[name="bpq-rank-by"]', host).forEach(function (r) { r.addEventListener('change', function () { by = r.value; draw(); }); });
		$$('input[name="bpq-rank-m"]', host).forEach(function (r) { r.addEventListener('change', function () { metric = r.value; draw(); }); });
		$$('input[name="bpq-rank-c"]', host).forEach(function (r) { r.addEventListener('change', function () { chamber = r.value; draw(); }); });
		sortSel.addEventListener('change', function () { sort = sortSel.value; draw(); });
		onView(host, draw, '200px 0px');
	})();

	/* ================================================================
	   Chapter 6: companions and twelve years
	   ================================================================ */
	(function chambers() {
		var ch = $('[data-bpq-comp-chart]');
		if (ch && D.companions) {
			var max = 0; D.companions.forEach(function (r) { max = Math.max(max, r.pct_law); });
			ch.innerHTML = COAL.map(function (c) {
				var y = pick(D.companions.filter(function (r) { return r.coalition === c; }), 'has_identical_companion', true);
				var n = pick(D.companions.filter(function (r) { return r.coalition === c; }), 'has_identical_companion', false);
				return '<div class="bpq-comp-row"><h4>' + COAL_LABEL[c] + '</h4><div class="bpq-comp-bars">' +
					'<div class="bpq-bar is-yes"><i data-w="' + (100 * y.pct_law / max) + '"></i><span style="--w:' + (100 * y.pct_law / max) + '%">' + y.pct_law.toFixed(2) + '% with a companion</span></div>' +
					'<div class="bpq-bar is-no"><i data-w="' + (100 * n.pct_law / max) + '"></i><span style="--w:' + (100 * n.pct_law / max) + '%">' + n.pct_law.toFixed(2) + '% without</span></div></div></div>';
			}).join('');
			onView(ch, function () { $$('i[data-w]', ch).forEach(function (i, k) { setTimeout(function () { i.style.width = i.getAttribute('data-w') + '%'; }, reduced ? 0 : k * 90); }); });
		}
		var th = $('[data-bpq-trend-chart]'), TY = D.twelve_years;
		if (th && TY) {
			var chamber = 'House', chart = null;
			function rows() { return TY.rows.filter(function (r) { return r.chamber === chamber; }); }
			function draw() {
				var R = rows();
				var opts = {
					x: R.map(function (r) { return r.congress; }), right: 120, ymax: 8,
					series: [
						{ values: R.map(function (r) { return r.pct_law_other; }), color: '#B4AED8', label: 'Everything else', labelColor: '#7A74A8', width: 2.5 },
						{ values: R.map(function (r) { return r.pct_law_bipartisan; }), color: INK.ink, label: 'Bipartisan', width: 3.5, under: true }
					],
					yticks: function () { return [0, 2, 4, 6, 8]; },
					yfmt: function (v) { return v + '%'; },
					xticks: R.map(function (r) { return [r.congress, r.congress + 'th']; }),
					tip: function (i) {
						var r = R[i], y0 = 1787 + 2 * r.congress;
						return '<b>' + r.congress + 'th Congress, ' + y0 + '–' + (y0 + 1) + '</b><br>' + chamber + ' bills: ' + BX.fmt(r.bills) + ', ' + r.pct_bipartisan + '% bipartisan<br>Became law: bipartisan ' + r.pct_law_bipartisan.toFixed(2) + '%, others ' + r.pct_law_other.toFixed(2) + '%<br><b>' + (r.pct_law_bipartisan / r.pct_law_other).toFixed(1) + '× the rate</b>';
					}
				};
				if (!chart) chart = lineChart(th, opts);
				else { th._drawn = false; th.classList.remove('is-drawn'); chart = lineChart(th, opts); th._drawn = true; requestAnimationFrame(function () { requestAnimationFrame(function () { th.classList.add('is-drawn'); }); }); }
			}
			$$('input[name="bpq-trend-c"]').forEach(function (r) { r.addEventListener('change', function () { chamber = r.value; draw(); }); });
			draw();
		}
	})();

	/* ================================================================
	   Chapter 7: tile map
	   ================================================================ */
	(function map() {
		var grid = $('[data-bpq-map-grid]');
		if (!grid || !D.states) return;
		var POS = { AK: [0, 0], ME: [11, 0], VT: [10, 1], NH: [11, 1], WA: [1, 2], ID: [2, 2], MT: [3, 2], ND: [4, 2], MN: [5, 2], IL: [6, 2], WI: [7, 2], MI: [8, 2], NY: [9, 2], RI: [10, 2], MA: [11, 2], OR: [1, 3], NV: [2, 3], WY: [3, 3], SD: [4, 3], IA: [5, 3], IN: [6, 3], OH: [7, 3], PA: [8, 3], NJ: [9, 3], CT: [10, 3], CA: [1, 4], UT: [2, 4], CO: [3, 4], NE: [4, 4], MO: [5, 4], KY: [6, 4], WV: [7, 4], VA: [8, 4], MD: [9, 4], DE: [10, 4], AZ: [2, 5], NM: [3, 5], KS: [4, 5], AR: [5, 5], TN: [6, 5], NC: [7, 5], SC: [8, 5], DC: [9, 5], OK: [4, 6], LA: [5, 6], MS: [6, 6], AL: [7, 6], GA: [8, 6], HI: [0, 7], TX: [4, 7], FL: [9, 7], PR: [11, 7] };
		var NAMES = { AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California', CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', DC: 'District of Columbia', FL: 'Florida', GA: 'Georgia', HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa', KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico', NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina', SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont', VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming', PR: 'Puerto Rico' };
		var S = {}; D.states.forEach(function (s) { S[s.state] = s; });
		var read = $('[data-bpq-map-read]'), scaleEl = $('[data-bpq-map-scale]');
		var metric = 'pct_bipartisan';
		var tiles = {};
		for (var row = 0; row < 8; row++) for (var col = 0; col < 12; col++) {
			var code = null;
			for (var k in POS) if (POS[k][0] === col && POS[k][1] === row) code = k;
			var b = document.createElement(code ? 'button' : 'span');
			b.className = 'bpq-tile' + (code ? '' : ' is-empty');
			if (code) { b.type = 'button'; b.textContent = code; b.setAttribute('data-st', code); tiles[code] = b; }
			grid.appendChild(b);
		}
		function lerp(a, b, t) { return Math.round(a + (b - a) * t); }
		function color(t) {
			var c0 = [255, 253, 246], c1 = [46, 43, 255], c2 = [18, 15, 46];
			var c = t < 0.6 ? [lerp(c0[0], c1[0], t / 0.6), lerp(c0[1], c1[1], t / 0.6), lerp(c0[2], c1[2], t / 0.6)] : [lerp(c1[0], c2[0], (t - 0.6) / 0.4), lerp(c1[1], c2[1], (t - 0.6) / 0.4), lerp(c1[2], c2[2], (t - 0.6) / 0.4)];
			return 'rgb(' + c.join(',') + ')';
		}
		function domain() {
			var vals = Object.keys(tiles).map(function (k) { return S[k] && S[k].bills >= 100 ? S[k][metric] : null; }).filter(function (v) { return v != null; });
			return [Math.min.apply(null, vals), Math.max.apply(null, vals)];
		}
		function describe(code) {
			var s = S[code];
			if (!s) return (NAMES[code] || code) + ': no bills in this range.';
			return (NAMES[code] || code) + ': ' + BX.fmt(s.bills) + ' bills sponsored, ' + s.pct_bipartisan + '% started bipartisan, ' + s.pct_law.toFixed(2) + '% became law (' + BX.fmt(s.laws) + ').' + (s.bills < 100 ? ' Small delegation; read with care.' : '');
		}
		function paint() {
			var d = domain();
			Object.keys(tiles).forEach(function (code, i) {
				var s = S[code], t = s ? Math.max(0, Math.min(1, (s[metric] - d[0]) / Math.max(0.0001, d[1] - d[0]))) : 0;
				var el = tiles[code];
				setTimeout(function () {
					el.style.setProperty('--c', s ? color(t) : 'rgba(18,15,46,.08)');
					el.style.setProperty('--t', t > 0.45 ? '#F6F0E2' : '#120F2E');
				}, reduced ? 0 : (POS[code][0] + POS[code][1]) * 28);
				el.setAttribute('aria-label', describe(code));
			});
			var fmtv = function (v) { return metric === 'pct_law' ? v.toFixed(1) + '%' : v.toFixed(0) + '%'; };
			scaleEl.innerHTML = '<span>' + fmtv(d[0]) + '</span><i style="background:linear-gradient(90deg,' + color(0) + ',' + color(0.6) + ',' + color(1) + ')"></i><span>' + fmtv(d[1]) + '</span>';
		}
		grid.addEventListener('mouseover', function (e) { var t = e.target.closest('[data-st]'); if (t) read.textContent = describe(t.getAttribute('data-st')); });
		grid.addEventListener('focusin', function (e) { var t = e.target.closest('[data-st]'); if (t) read.textContent = describe(t.getAttribute('data-st')); });
		grid.addEventListener('click', function (e) {
			var t = e.target.closest('[data-st]'); if (!t) return;
			Object.keys(tiles).forEach(function (k) { tiles[k].classList.toggle('is-on', tiles[k] === t); });
			read.textContent = describe(t.getAttribute('data-st'));
		});
		$$('input[name="bpq-map-m"]').forEach(function (r) { r.addEventListener('change', function () { metric = r.value; paint(); }); });
		onView(grid, paint, '100px 0px');
	})();

	/* ================================================================
	   Chapter 8: bridge builders network
	   ================================================================ */
	(function network() {
		var host = $('[data-bpq-net]');
		if (!host || !C.api) return;
		var svgEl = $('[data-bpq-net-svg]', host), card = $('[data-bpq-net-card]', host);
		var q = $('[data-bpq-net-q]', host), sugg = $('[data-bpq-net-sugg]', host);
		var W = 800, H = 656, cx = W / 2, cy = H / 2;
		svgEl.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
		var gE = svg('g', {}, svgEl), gN = svg('g', {}, svgEl);
		var nodes = {};
		var PC = { D: '#8F8DFF', R: '#FF7B5E', I: '#C9C4E4' };
		function short(name) { return String(name || '').replace(/^(Rep\.|Sen\.)\s*/, '').replace(/\s*\[.*$/, ''); }
		function tag(name) { var m = /\[([^\]]+)\]/.exec(name || ''); return m ? m[1] : ''; }
		function render(m) {
			var P = m.partners || [];
			var maxB = Math.max.apply(null, P.map(function (p) { return p.bills; }).concat([1]));
			var R = Math.min(W, H) * 0.38;
			var want = {};
			want[m.member_id] = { x: cx, y: cy, r: 34, name: m.name, party: m.party, center: true };
			P.forEach(function (p, i) {
				var a = -Math.PI / 2 + i / P.length * Math.PI * 2;
				var rr = R * (0.82 + 0.18 * (1 - p.bills / maxB));
				want[p.id] = { x: cx + Math.cos(a) * rr, y: cy + Math.sin(a) * rr, r: 8 + 14 * Math.sqrt(p.bills / maxB), name: p.name, party: p.party, bills: p.bills, laws: p.laws, a: a };
			});
			gE.innerHTML = '';
			P.forEach(function (p) {
				var w = want[p.id];
				var ln = svg('line', { class: 'bpq-edge', x1: cx, y1: cy, x2: reduced ? w.x : cx, y2: reduced ? w.y : cy, stroke: PC[p.party] || '#fff', 'stroke-width': 1.5 + 12 * p.bills / maxB }, gE);
				if (!reduced) requestAnimationFrame(function () { ln.style.transition = 'all .9s cubic-bezier(.22,.9,.24,1)'; requestAnimationFrame(function () { ln.setAttribute('x2', w.x); ln.setAttribute('y2', w.y); }); });
				var mx = (cx + w.x) / 2, my = (cy + w.y) / 2;
				var t = svg('text', { x: mx, y: my, 'text-anchor': 'middle', 'font-size': 11, fill: '#F4F0FF', 'paint-order': 'stroke', stroke: '#0F0C29', 'stroke-width': 4, opacity: 0 }, gE);
				t.textContent = p.bills;
				setTimeout(function () { t.setAttribute('opacity', 1); }, reduced ? 0 : 700);
			});
			Object.keys(nodes).forEach(function (id) { if (!want[id]) { var n = nodes[id]; n.style.opacity = 0; setTimeout(function () { n.remove(); }, 400); delete nodes[id]; } });
			Object.keys(want).forEach(function (id) {
				var w = want[id], n = nodes[id];
				if (!n) {
					n = nodes[id] = svg('g', { class: 'bpq-node', tabindex: 0, role: 'button' }, gN);
					svg('circle', { r: w.r }, n);
					svg('text', { class: 'bpq-node-label', 'text-anchor': 'middle' }, n);
					svg('text', { class: 'bpq-node-sub', 'text-anchor': 'middle' }, n);
					n.style.transform = 'translate(' + cx + 'px,' + cy + 'px)';
					n.style.transition = reduced ? 'none' : 'transform .9s cubic-bezier(.22,.9,.24,1), opacity .4s ease';
					n.addEventListener('click', function () { if (!nodes[id]._center) load(id); });
					n.addEventListener('keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && !nodes[id]._center) { e.preventDefault(); load(id); } });
				}
				n._center = !!w.center;
				var c = n.querySelector('circle');
				c.setAttribute('r', w.r);
				c.setAttribute('fill', w.center ? '#D6FF3D' : (PC[w.party] || '#fff'));
				c.setAttribute('stroke', w.center ? '#0F0C29' : 'none');
				c.setAttribute('stroke-width', w.center ? 3 : 0);
				var lab = n.querySelector('.bpq-node-label'), sub = n.querySelector('.bpq-node-sub');
				var below = w.center || Math.sin(w.a || 0) > -0.3;
				lab.textContent = short(w.name);
				lab.setAttribute('y', w.center ? w.r + 22 : (below ? w.r + 16 : -w.r - 18));
				sub.textContent = w.center ? tag(w.name) : tag(w.name) + ' · ' + w.bills + ' bills';
				sub.setAttribute('y', w.center ? w.r + 38 : (below ? w.r + 30 : -w.r - 5));
				n.setAttribute('aria-label', w.center ? short(w.name) + ', selected' : short(w.name) + ', ' + w.bills + ' shared bills, ' + w.laws + ' became law. Show their network.');
				requestAnimationFrame(function () { n.style.opacity = 1; n.style.transform = 'translate(' + w.x + 'px,' + w.y + 'px)'; });
			});
			var party = m.party === 'D' ? 'Democrat' : m.party === 'R' ? 'Republican' : 'Independent';
			card.innerHTML = '<h3>' + BX.esc(short(m.name)) + '</h3><span class="bpq-party">' + party + ', ' + BX.esc(m.state || '') + ' · ' + BX.esc(m.chamber || '') + '</span>' +
				'<dl class="bpq-net-stats">' +
				'<div><dt>Cross-party partners</dt><dd>' + BX.fmt(m.cross_party_partners) + '</dd></div>' +
				'<div><dt>Shared bills</dt><dd>' + BX.fmt(m.cross_party_ties) + '</dd></div>' +
				'<div><dt>Bills sponsored, 2019–24</dt><dd>' + BX.fmt(m.sponsored_116_118 || 0) + '</dd></div>' +
				'<div><dt>Started bipartisan</dt><dd>' + (m.pct_sponsored_bipartisan != null ? Math.round(m.pct_sponsored_bipartisan) + '%' : '–') + '</dd></div>' +
				'</dl><a class="bpq-net-link" href="' + C.data + '?q=' + encodeURIComponent(short(m.name).split(',')[0]) + '#browse">See their bills in Open Data →</a>';
		}
		function load(id) {
			card.setAttribute('aria-busy', 'true');
			api({ route: 'member', id: id }).then(function (m) { card.setAttribute('aria-busy', 'false'); render(m); }).catch(function () { card.innerHTML = '<p class="bx-pending">That member could not be loaded.</p>'; });
		}
		var timer = null, items = [], sel = -1;
		function close() { sugg.hidden = true; sel = -1; q.setAttribute('aria-expanded', 'false'); }
		function showSugg(list) {
			items = list;
			sugg.innerHTML = list.map(function (m, i) { return '<li role="option" id="bpq-sg-' + i + '" data-id="' + m.member_id + '">' + BX.esc(m.name) + '</li>'; }).join('') || '<li aria-disabled="true">No matches</li>';
			sugg.hidden = false; q.setAttribute('aria-expanded', 'true');
		}
		q.setAttribute('role', 'combobox'); q.setAttribute('aria-autocomplete', 'list'); q.setAttribute('aria-expanded', 'false');
		q.addEventListener('input', function () {
			clearTimeout(timer);
			var v = q.value.trim();
			if (v.length < 2) { close(); return; }
			timer = setTimeout(function () { api({ route: 'members', q: v, limit: 8 }).then(function (r) { showSugg(r.members || []); }); }, 220);
		});
		q.addEventListener('keydown', function (e) {
			if (sugg.hidden) return;
			var lis = $$('li[data-id]', sugg);
			if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
				e.preventDefault();
				sel = Math.max(0, Math.min(lis.length - 1, sel + (e.key === 'ArrowDown' ? 1 : -1)));
				lis.forEach(function (li, i) { li.setAttribute('aria-selected', i === sel ? 'true' : 'false'); });
				q.setAttribute('aria-activedescendant', 'bpq-sg-' + sel);
			} else if (e.key === 'Enter' && lis[sel >= 0 ? sel : 0]) { e.preventDefault(); load(lis[sel >= 0 ? sel : 0].getAttribute('data-id')); close(); }
			else if (e.key === 'Escape') close();
		});
		sugg.addEventListener('click', function (e) { var li = e.target.closest('li[data-id]'); if (li) { load(li.getAttribute('data-id')); q.value = li.textContent; close(); } });
		document.addEventListener('click', function (e) { if (!host.contains(e.target)) close(); });
		onView(host, function () { load('F000466'); }, '600px 0px');
	})();
})();
