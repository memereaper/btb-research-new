<?php
/**
 * /explore/open-record/ — The Open Record: searchable bills, 116th-119th Congress.
 */
if ( ! defined( 'ABSPATH' ) ) exit;
$ov = btbd_get( 'overview', HOUR_IN_SECONDS );
$bills = 0; $laws = 0;
if ( $ov && ! empty( $ov['congresses'] ) ) foreach ( $ov['congresses'] as $c ) { $bills += $c['bills']; $laws += $c['laws']; }
$repo = 'https://github.com/memereaper/btb-research-new';
get_header();
?>
<div class="bx bx-story btbd" data-btbd-page="record">

	<section class="bx-plate bx-plate-night bx-hero-plate btbd-record-hero">
	<header class="bx-hero bx-wrap" id="top">
		<p class="bx-label bx-seq" style="--seq:1"><a href="<?php echo esc_url( btbd_url( '' ) ); ?>">Explore</a><span aria-hidden="true">/</span><span>Open data</span></p>
		<h1 class="bx-display bx-hero-title" aria-label="The Open Record">
			<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:2">The Open</span></span>
			<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:3">Record</span></span>
		</h1>
		<p class="bx-hero-dek bx-seq" style="--seq:4">Every bill introduced in Congress since January 2019. Search it, filter it, take it with you.</p>
		<dl class="btbd-stats bx-seq" style="--seq:5">
			<div><dt>Bills and joint resolutions</dt><dd><?php echo esc_html( $bills ? btbd_n( $bills ) : '63,173' ); ?></dd></div>
			<div><dt>Became law</dt><dd><?php echo esc_html( $laws ? btbd_n( $laws ) : '1,122' ); ?></dd></div>
			<div><dt>Records in the full database</dt><dd>1,765,337</dd></div>
			<div><dt>Congresses</dt><dd>116th–119th</dd></div>
		</dl>
	</header>
	</section>

	<section class="bx-plate bx-plate-cream" id="search">
	<div class="bx-wrap">
		<form class="btbd-filters" data-btbd-form role="search" aria-label="Search bills">
			<label class="btbd-q"><span>Search titles, sponsors and policy areas</span><input type="search" name="q" placeholder="insulin, Fitzpatrick, broadband…" autocomplete="off" maxlength="120"></label>
			<label><span>Congress</span><select name="congress"><option value="">All</option><option>119</option><option>118</option><option>117</option><option>116</option></select></label>
			<label><span>Coalition on day one</span><select name="coalition"><option value="">Any</option><option value="bipartisan">Bipartisan</option><option value="same_party">Same party only</option><option value="solo">No cosponsors</option></select></label>
			<label><span>Got as far as</span><select name="furthest"><option value="">Any stage</option><option value="introduced">Introduced only</option><option value="cleared_committee">Out of committee</option><option value="passed_one">Passed one chamber</option><option value="passed_both">Passed both</option><option value="law">Became law</option></select></label>
			<label><span>Sponsor party</span><select name="party"><option value="">Any</option><option value="D">Democrat</option><option value="R">Republican</option><option value="I">Independent</option></select></label>
		</form>
		<div class="btbd-status" aria-live="polite"><span data-btbd-count>Loading…</span><button type="button" class="btbd-link" data-btbd-reset>Reset</button><button type="button" class="btbd-link" data-btbd-share>Copy link</button><button type="button" class="btbd-link" data-btbd-csv>Download these rows (CSV)</button></div>
		<div class="btbd-table-wrap">
			<table class="btbd-table">
				<thead><tr><th scope="col">Bill</th><th scope="col">Title</th><th scope="col">Sponsor</th><th scope="col">Day one</th><th scope="col">Got to</th><th scope="col">Introduced</th></tr></thead>
				<tbody data-btbd-rows></tbody>
			</table>
		</div>
		<p class="btbd-more"><button type="button" class="btbd-btn" data-btbd-more hidden>Show 50 more</button></p>
	</div>
	</section>

	<section class="bx-plate bx-plate-cream" id="use">
	<div class="bx-wrap bx-measure btbd-prose btbd-method">
		<p class="btbd-kicker">Use the data</p>
		<h2 class="btbd-h2">Take the whole record with you</h2>
		<p>This page searches a compact copy of every bill. The full database behind it holds 1,765,337 records of eleven kinds: bills, every recorded action, 680,906 cosponsorships with join and withdrawal dates, committee referrals and events, related bills, 332,232 subject terms, CRS summaries, text versions, CBO estimates and roll-call references. All of it comes from the Library of Congress Bill Status records published on GovInfo.</p>
		<h3 class="btbd-h3">Download</h3>
		<ul class="btbd-list">
			<li><a href="<?php echo esc_url( $repo . '/tree/main/datasets/pathways-116-117-2026-10-29' ); ?>">116th–117th Congress package</a> and <a href="<?php echo esc_url( $repo . '/tree/main/datasets/pathways-2026-10-28' ); ?>">118th–119th Congress package</a>: eleven Parquet tables each, with checksums, catalog and validation report.</li>
			<li><a href="<?php echo esc_url( $repo . '/blob/main/docs/collections/pathways-116-119-sql.md' ); ?>">How the full SQL database is built</a>: one command turns the two packages into a typed DuckDB database with quality flags and a record-grain inventory.</li>
			<li><a href="<?php echo esc_url( $repo . '/tree/main/datasets/pathways-116-119-serving' ); ?>">The compact bill table</a> this page searches, as JSON.</li>
		</ul>
		<h3 class="btbd-h3">Query it from your code</h3>
		<p>A free, read-only JSON API. No key needed. Up to 50 rows per request.</p>
		<pre class="btbd-code"><code><?php echo esc_html( BTBD_API ); ?>?route=bills&amp;congress=118&amp;coalition=bipartisan&amp;furthest=law
<?php echo esc_html( BTBD_API ); ?>?route=bills&amp;q=broadband&amp;limit=50
<?php echo esc_html( BTBD_API ); ?>?route=bill&amp;id=117-hr3684
<?php echo esc_html( BTBD_API ); ?>?route=overview
<?php echo esc_html( BTBD_API ); ?>?route=findings</code></pre>
		<p>Page with the <code>next_cursor</code> value from each response (<code>&amp;cursor=…</code>). Filters: <code>congress</code> (116–119), <code>coalition</code> (bipartisan, same_party, solo), <code>furthest</code> (introduced, cleared_committee, passed_one, passed_both, law), <code>party</code> (D, R, I), <code>q</code> (full-text search).</p>
		<h3 class="btbd-h3">What the fields mean</h3>
		<p><strong>Day one</strong> is the coalition recorded at introduction: bipartisan if an original cosponsor came from the other major party. <strong>Got to</strong> is the furthest stage reached, from Library of Congress action codes. The 119th Congress is still in session, so its bills are still moving. Known gaps are flagged, never silently fixed: 11 bills have no sponsor ID in the source, and newer bills carry fewer subject terms because the Library of Congress adds them over time.</p>
		<p class="btbd-muted">Source records are works of the U.S. government. Please credit Between the Bills and the Library of Congress when you use this compilation.</p>
	</div>
	</section>
</div>
<?php get_footer();
