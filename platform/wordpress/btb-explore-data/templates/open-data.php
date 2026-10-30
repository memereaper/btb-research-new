<?php
/**
 * /data/ – Open Data: the hosted legislative record, an in-browser SQL console
 * over the full warehouse, the public API, downloads and the data dictionary.
 * Row-level data is read from the API or from Parquet files on a CDN; none of
 * it is stored in WordPress.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}
$ov   = btbd_overview();
$cat  = btbd_findings( 'open-data-catalog' );
$fmt  = function ( $n ) { return btbd_n( $n ); };
$host = $ov ? $ov['hosted'] : array( 'bills' => 93893, 'actions' => 465291, 'members' => 806, 'rows' => 559990 );
$wh   = $cat ? (int) $cat['total_rows'] : 1765337;
$tables = $cat ? $cat['tables'] : array();
$sha  = $cat ? $cat['pinned_commit'] : '';
$api  = BTBD_API;
$mb   = function ( $b ) { return btbd_n( $b / 1048576, 1 ) . ' MB'; };
get_header();
?>
<div class="bx od" data-od>

	<header class="bx-plate bx-plate-night od-hero" id="top">
		<div class="od-hero-img" aria-hidden="true"><?php echo btbd_img( 'census-1939', 'od-hero-print', '(max-width: 900px) 100vw, 55vw', true ); // phpcs:ignore ?></div>
		<div class="od-cards" aria-hidden="true" data-od-cards></div>
		<div class="bx-wrap od-hero-inner">
			<p class="bx-label bx-seq" style="--seq:1"><span>Between the Bills</span><span aria-hidden="true">/</span><span>Open Data</span></p>
			<h1 class="bx-display od-title" aria-label="Open Data">
				<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:2">Open</span></span>
				<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:3">Data</span></span>
			</h1>
			<p class="od-dek bx-seq" style="--seq:4">The full record of every bill introduced in Congress since 2013. Search it here, query all 1.77 million rows with SQL in your browser, call the free API, or take the files with you.</p>
			<dl class="od-stats bx-seq" style="--seq:5">
				<div><dt>Rows in the warehouse</dt><dd data-od-count="<?php echo esc_attr( $wh ); ?>"><?php echo esc_html( $fmt( $wh ) ); ?></dd></div>
				<div><dt>Rows served live by the API</dt><dd data-od-count="<?php echo esc_attr( $host['rows'] ); ?>"><?php echo esc_html( $fmt( $host['rows'] ) ); ?></dd></div>
				<div><dt>Bills and resolutions</dt><dd data-od-count="<?php echo esc_attr( $host['bills'] ); ?>"><?php echo esc_html( $fmt( $host['bills'] ) ); ?></dd></div>
				<div><dt>Congresses</dt><dd>113th–119th</dd></div>
			</dl>
			<nav class="od-jump bx-seq" style="--seq:6" aria-label="On this page">
				<a href="#browse">Browse</a><a href="#sql">SQL console</a><a href="#api">API</a><a href="#downloads">Downloads</a><a href="#dictionary">Data dictionary</a><a href="#cite">Cite</a>
			</nav>
		</div>
		<p class="bx-credit od-hero-credit"><?php echo btbd_img_credit( 'census-1939' ); // phpcs:ignore ?></p>
	</header>

	<!-- The shelf: every table -->
	<section class="bx-plate bx-plate-cream od-shelf-plate" aria-labelledby="od-shelf-title">
		<div class="bx-wrap">
			<div class="od-head">
				<p class="bx-label">What is in it</p>
				<h2 class="bx-h2" id="od-shelf-title" data-reveal>Eleven tables, one record.</h2>
				<p class="od-sub" data-reveal>Built from the Library of Congress Bill Status files, the same records behind Congress.gov. Every row keeps a pointer to the exact source file it came from.</p>
			</div>
			<ol class="od-shelf" data-bx-shelf>
				<?php
				$live = array(
					'bills'   => array( $host['bills'], '113th–119th, live in the API' ),
					'actions' => array( $host['actions'], '113th–119th, live in the API' ),
				);
				$i = 0;
				foreach ( $tables as $name => $t ) :
					$is_live = isset( $live[ $name ] );
					?>
					<li class="od-card<?php echo $is_live ? ' is-live' : ''; ?>" style="--i:<?php echo (int) $i++; ?>">
						<span class="od-card-n"><?php echo esc_html( $fmt( $is_live ? $live[ $name ][0] : $t['rows'] ) ); ?></span>
						<span class="od-card-name"><?php echo esc_html( str_replace( '_', ' ', $name ) ); ?></span>
						<span class="od-card-d"><?php echo esc_html( $t['description'] ); ?></span>
						<span class="od-card-tags"><?php if ( $is_live ) : ?><b>API</b><?php endif; ?><b>SQL</b><b>Parquet</b></span>
						<?php if ( $is_live ) : ?><span class="od-card-note"><?php echo esc_html( $live[ $name ][1] ); ?>. <?php echo esc_html( $fmt( $t['rows'] ) ); ?> rows for the 116th–119th in the warehouse.</span><?php endif; ?>
					</li>
				<?php endforeach; ?>
				<li class="od-card is-live" style="--i:<?php echo (int) $i; ?>">
					<span class="od-card-n"><?php echo esc_html( $fmt( $host['members'] ) ); ?></span>
					<span class="od-card-name">member networks</span>
					<span class="od-card-d">Each member’s top cross-party partners, shared bills and laws, from investigation 002.</span>
					<span class="od-card-tags"><b>API</b></span>
				</li>
			</ol>
		</div>
	</section>

	<!-- Browse -->
	<section class="bx-plate bx-plate-cream od-browse" id="browse" aria-labelledby="od-browse-title">
		<div class="bx-wrap">
			<div class="od-head od-head-row">
				<div>
					<p class="bx-label">01 / Browse</p>
					<h2 class="bx-h2" id="od-browse-title">Search every bill.</h2>
				</div>
				<p class="od-sub">93,893 bills and joint resolutions from 2013 to today. Open any row for its full timeline of recorded actions.</p>
			</div>
			<form class="od-filters" data-od-form role="search" aria-label="Search bills">
				<label class="od-q"><span>Search titles and sponsors, or type a bill number</span><input type="search" name="q" placeholder="insulin, broadband, 118-hr815" autocomplete="off" maxlength="120"></label>
				<label><span>Congress</span><select name="congress"><option value="">All</option><?php for ( $c = 119; $c >= 113; $c-- ) : $y = 1787 + 2 * $c; ?><option value="<?php echo esc_attr( $c ); ?>"><?php echo esc_html( $c . 'th (' . $y . '–' . ( $y + 1 ) . ')' ); ?></option><?php endfor; ?></select></label>
				<label><span>Chamber</span><select name="chamber"><option value="">Both</option><option value="House">House</option><option value="Senate">Senate</option></select></label>
				<label><span>Day one</span><select name="coalition"><option value="">Any coalition</option><option value="bipartisan">Bipartisan</option><option value="not_bipartisan">Not bipartisan</option><option value="same_party">Same party only (116th+)</option><option value="solo">No cosponsors (116th+)</option></select></label>
				<label><span>Got as far as</span><select name="furthest"><option value="">Any stage</option><option value="introduced">Introduced only</option><option value="cleared_committee">Out of committee</option><option value="passed_one">Passed one chamber</option><option value="passed_both">Passed both</option><option value="law">Became law</option></select></label>
				<label><span>Sponsor party</span><select name="party"><option value="">Any</option><option value="D">Democrat</option><option value="R">Republican</option><option value="I">Independent</option></select></label>
				<label class="od-policy"><span>Policy area</span><select name="policy" data-od-policy><option value="">All policy areas</option></select></label>
			</form>
			<div class="od-status" aria-live="polite">
				<span class="od-count" data-od-count-text>Loading…</span>
				<span class="od-actions">
					<button type="button" class="od-link" data-od-reset>Reset</button>
					<button type="button" class="od-link" data-od-share>Copy link</button>
					<button type="button" class="od-link" data-od-csv>Download CSV</button>
					<button type="button" class="od-link" data-od-apiurl>Show API call</button>
				</span>
			</div>
			<pre class="od-apicall" data-od-apicall hidden></pre>
			<div class="od-table-wrap">
				<table class="od-table">
					<caption class="screen-reader-text">Matching bills</caption>
					<thead><tr><th scope="col">Bill</th><th scope="col">Title</th><th scope="col">Sponsor</th><th scope="col">Day one</th><th scope="col">Got to</th><th scope="col">Introduced</th></tr></thead>
					<tbody data-od-rows></tbody>
				</table>
			</div>
			<p class="od-more"><button type="button" class="bx-button bx-button-quiet" data-od-more hidden>Show 50 more</button></p>
		</div>
	</section>

	<!-- Bill drawer -->
	<div class="od-drawer" data-od-drawer hidden>
		<div class="od-drawer-scrim" data-od-close></div>
		<aside class="od-drawer-panel" role="dialog" aria-modal="true" aria-labelledby="od-drawer-title" tabindex="-1">
			<button type="button" class="od-drawer-x" data-od-close aria-label="Close">×</button>
			<div data-od-drawer-body></div>
		</aside>
	</div>

	<!-- SQL -->
	<section class="bx-plate bx-plate-night od-sql" id="sql" aria-labelledby="od-sql-title">
		<div class="od-sql-img" aria-hidden="true"><?php echo btbd_img( 'keypunch-1950', 'od-sql-print', '50vw' ); // phpcs:ignore ?></div>
		<div class="bx-wrap od-sql-inner">
			<div class="od-head od-head-row">
				<div>
					<p class="bx-label">02 / SQL console</p>
					<h2 class="bx-h2" id="od-sql-title">Query 1.77 million rows in your browser.</h2>
				</div>
				<p class="od-sub">The console runs DuckDB inside this page. It reads the Parquet files straight from a public CDN, fetching only the columns and row groups a query needs. Nothing you type is sent to our servers.</p>
			</div>
			<div class="od-console" data-od-console>
				<div class="od-console-top">
					<div class="od-samples" data-od-samples role="toolbar" aria-label="Example queries"></div>
					<span class="od-engine" data-od-engine>Engine not started</span>
				</div>
				<label class="screen-reader-text" for="od-sql-input">SQL query</label>
				<textarea id="od-sql-input" class="od-editor" data-od-sql spellcheck="false" autocomplete="off" rows="9">-- Every table is a view: bills, actions, cosponsors, committees,
-- committee_events, related_bills, subjects, summaries,
-- text_versions, cbo_estimates, vote_references
SELECT congress, count(*) AS bills, count(*) FILTER (WHERE law_identifiers IS NOT NULL AND law_identifiers <> '') AS laws
FROM bills GROUP BY congress ORDER BY congress;</textarea>
				<div class="od-console-bar">
					<button type="button" class="bx-button od-run" data-od-run>Run query <kbd>Ctrl</kbd><kbd>Enter</kbd></button>
					<button type="button" class="od-link" data-od-sql-csv disabled>Download result (CSV)</button>
					<span class="od-sql-status" data-od-sql-status aria-live="polite"></span>
				</div>
				<div class="od-result" data-od-result tabindex="0" aria-label="Query result"></div>
				<details class="od-schema">
					<summary>Tables and columns</summary>
					<div class="od-schema-grid" data-od-schema></div>
				</details>
			</div>
			<p class="bx-credit od-sql-credit"><?php echo btbd_img_credit( 'keypunch-1950' ); // phpcs:ignore ?></p>
		</div>
	</section>

	<!-- API -->
	<section class="bx-plate bx-plate-blue od-api" id="api" aria-labelledby="od-api-title">
		<div class="bx-wrap">
			<div class="od-head od-head-row">
				<div>
					<p class="bx-label">03 / API</p>
					<h2 class="bx-h2" id="od-api-title">A free, read-only JSON API.</h2>
				</div>
				<p class="od-sub">No key, no sign-up. Responses are cached at the edge and safe to call from a browser. Please keep it under a few requests per second, and cache what you can.</p>
			</div>
			<div class="od-endpoint"><span>Endpoint</span><code data-od-endpoint><?php echo esc_html( $api ); ?></code><button type="button" class="od-link" data-od-copy="<?php echo esc_attr( $api ); ?>">Copy</button></div>
			<div class="od-api-grid">
				<div class="od-routes" role="tablist" aria-label="API routes" data-od-routes>
					<?php
					$routes = array(
						'bills'        => array( 'Search and filter bills', 'route=bills&congress=118&coalition=bipartisan&furthest=law&limit=5' ),
						'bill'         => array( 'One bill with its action timeline', 'route=bill&id=117-hr3684' ),
						'members'      => array( 'Find members by name or state', 'route=members&q=collins' ),
						'member'       => array( 'A member’s cross-party partners', 'route=member&id=C001035' ),
						'overview'     => array( 'Counts for every table', 'route=overview' ),
						'policy_areas' => array( 'Policy areas with counts', 'route=policy_areas' ),
						'findings'     => array( 'Published research results', 'route=findings&key=bipartisanship-deep' ),
					);
					$first = true;
					foreach ( $routes as $r => $info ) :
						?>
						<button type="button" role="tab" class="od-route" aria-selected="<?php echo $first ? 'true' : 'false'; ?>" data-q="<?php echo esc_attr( $info[1] ); ?>"><code><?php echo esc_html( $r ); ?></code><span><?php echo esc_html( $info[0] ); ?></span></button>
						<?php
						$first = false;
					endforeach;
					?>
				</div>
				<div class="od-try">
					<div class="od-try-url"><code data-od-try-url></code><button type="button" class="bx-button" data-od-try>Send request</button></div>
					<pre class="od-try-out" data-od-try-out aria-live="polite">Pick a route, then send the request.</pre>
				</div>
			</div>
			<div class="od-params">
				<h3 class="bx-h3">Parameters for <code>bills</code></h3>
				<dl class="od-defs">
					<div><dt><code>q</code></dt><dd>Full-text search over titles, sponsors and policy areas, or a bill number such as <code>118-hr815</code>.</dd></div>
					<div><dt><code>congress</code></dt><dd>113 to 119.</dd></div>
					<div><dt><code>chamber</code></dt><dd><code>House</code> or <code>Senate</code>.</dd></div>
					<div><dt><code>coalition</code></dt><dd><code>bipartisan</code>, <code>not_bipartisan</code>; for the 116th onward also <code>same_party</code>, <code>solo</code>.</dd></div>
					<div><dt><code>furthest</code></dt><dd><code>introduced</code>, <code>cleared_committee</code>, <code>passed_one</code>, <code>passed_both</code>, <code>law</code>.</dd></div>
					<div><dt><code>party</code></dt><dd>Sponsor party: <code>D</code>, <code>R</code>, <code>I</code>.</dd></div>
					<div><dt><code>policy</code></dt><dd>Exact policy area name, from <code>route=policy_areas</code>.</dd></div>
					<div><dt><code>limit</code>, <code>cursor</code></dt><dd>Up to 50 rows per page. Pass the <code>next_cursor</code> from one response to get the next page.</dd></div>
				</dl>
			</div>
			<div class="od-snippets" data-od-snippets>
				<div class="bx-seg" role="radiogroup" aria-label="Language">
					<label><input type="radio" name="od-lang" value="js" checked><span>JavaScript</span></label>
					<label><input type="radio" name="od-lang" value="py"><span>Python</span></label>
					<label><input type="radio" name="od-lang" value="sh"><span>curl</span></label>
					<label><input type="radio" name="od-lang" value="r"><span>R</span></label>
				</div>
				<pre class="od-code" data-od-snippet></pre>
			</div>
		</div>
	</section>

	<!-- Downloads -->
	<section class="bx-plate bx-plate-cream od-dl" id="downloads" aria-labelledby="od-dl-title">
		<div class="od-dl-img" aria-hidden="true"><?php echo btbd_img( 'cards-1910', 'od-dl-print', '(max-width: 900px) 100vw, 40vw' ); // phpcs:ignore ?></div>
		<div class="bx-wrap">
			<div class="od-head">
				<p class="bx-label">04 / Downloads</p>
				<h2 class="bx-h2" id="od-dl-title" data-reveal>Take the whole thing.</h2>
				<p class="od-sub" data-reveal>Apache Parquet, readable by DuckDB, pandas, polars, R (arrow), Spark and most BI tools. Links point at a fixed version of the repository<?php echo $sha ? ' (' . esc_html( substr( $sha, 0, 7 ) ) . ')' : ''; ?>, so a script written today keeps returning the same rows.</p>
			</div>
			<div class="od-dl-table-wrap">
				<table class="od-dl-table">
					<thead><tr><th scope="col">Table</th><th scope="col">Rows</th><th scope="col">116th–117th</th><th scope="col">118th–119th</th></tr></thead>
					<tbody>
					<?php foreach ( $tables as $name => $t ) : ?>
						<tr><th scope="row"><code><?php echo esc_html( $name ); ?></code></th><td><?php echo esc_html( $fmt( $t['rows'] ) ); ?></td>
						<?php foreach ( $t['files'] as $f ) : ?><td><a href="<?php echo esc_url( $f['url'] ); ?>" download><?php echo esc_html( $mb( $f['bytes'] ) ); ?></a></td><?php endforeach; ?></tr>
					<?php endforeach; ?>
					</tbody>
				</table>
			</div>
			<div class="od-dl-more">
				<a class="od-dl-card" href="<?php echo esc_url( BTBD_REPO . '/blob/main/datasets/open-data/catalog.json' ); ?>"><b>catalog.json</b><span>Every file, row count, column and type in one machine-readable list.</span></a>
				<a class="od-dl-card" href="<?php echo esc_url( BTBD_REPO . '/blob/main/docs/collections/pathways-116-119-sql.md' ); ?>"><b>Build the SQL database</b><span>One command turns the Parquet packages into a typed DuckDB file with quality flags.</span></a>
				<a class="od-dl-card" href="<?php echo esc_url( BTBD_REPO ); ?>"><b>The repository</b><span>Source data, checksums, validation reports and every script, on GitHub.</span></a>
			</div>
			<p class="bx-credit"><?php echo btbd_img_credit( 'cards-1910' ); // phpcs:ignore ?></p>
		</div>
	</section>

	<!-- Dictionary -->
	<section class="bx-plate bx-plate-cream od-dict" id="dictionary" aria-labelledby="od-dict-title">
		<div class="bx-wrap">
			<div class="od-head">
				<p class="bx-label">05 / Data dictionary</p>
				<h2 class="bx-h2" id="od-dict-title">Every column.</h2>
			</div>
			<div class="od-dict-grid">
				<?php foreach ( $tables as $name => $t ) : ?>
					<details class="od-dict-t">
						<summary><code><?php echo esc_html( $name ); ?></code><span><?php echo esc_html( $fmt( $t['rows'] ) ); ?> rows · <?php echo esc_html( count( $t['columns'] ) ); ?> columns</span></summary>
						<p><?php echo esc_html( $t['description'] ); ?></p>
						<table><thead><tr><th scope="col">Column</th><th scope="col">Type</th></tr></thead><tbody>
						<?php foreach ( $t['columns'] as $col ) : ?><tr><td><code><?php echo esc_html( $col[0] ); ?></code></td><td><?php echo esc_html( strtolower( $col[1] ) ); ?></td></tr><?php endforeach; ?>
						</tbody></table>
					</details>
				<?php endforeach; ?>
			</div>
			<div class="od-notes">
				<h3 class="bx-h3">Things to know</h3>
				<ul>
					<li><b>Coverage.</b> The warehouse holds the 116th–119th Congresses. The API also serves the 113th–115th from our earlier release, with day-one coalition recorded as bipartisan or not.</li>
					<li><b>The 119th Congress is in session.</b> Its bills are still moving, so counts change until the record is final.</li>
					<li><b>Flags, not fixes.</b> Rows with quality problems are kept and flagged. Eleven bills have no sponsor ID in the source. Newer bills carry fewer subject terms because the Library of Congress adds them over time.</li>
					<li><b>Grain.</b> Cosponsorships are one row per bill, member and join date; vote references one row per action and roll call. See the database methods for every table’s key.</li>
				</ul>
			</div>
		</div>
	</section>

	<!-- Cite -->
	<section class="bx-plate bx-plate-night od-cite" id="cite" aria-labelledby="od-cite-title">
		<div class="bx-wrap od-cite-inner">
			<div>
				<p class="bx-label">06 / Cite</p>
				<h2 class="bx-h2" id="od-cite-title">Use it. Credit it.</h2>
				<p class="od-sub">The source records are works of the U.S. government and in the public domain. If you publish with this compilation, please credit Between the Bills and the Library of Congress.</p>
			</div>
			<div class="od-cite-box">
				<pre data-od-cite>Between the Bills. Open legislative record, 113th–119th Congresses<?php echo $sha ? ', version ' . esc_html( substr( $sha, 0, 7 ) ) : ''; ?>. Compiled from Library of Congress Bill Status records (GovInfo). <?php echo esc_html( btbd_data_url() ); ?></pre>
				<button type="button" class="bx-button" data-od-copy-cite>Copy citation</button>
			</div>
		</div>
	</section>

	<nav class="bx-plate bx-plate-coral" aria-label="Research built on this data"><div class="bx-next bx-wrap">
		<a class="bx-next-link" href="<?php echo esc_url( function_exists( 'btbx_explore_url' ) ? btbx_explore_url( 'the-bipartisanship-question' ) : home_url( '/explore/the-bipartisanship-question/' ) ); ?>"><span class="bx-label">Built on this data</span><span class="bx-next-title">The Bipartisanship Question</span><svg viewBox="0 0 28 12" aria-hidden="true" focusable="false"><path d="M0 6h26M21 1l5 5-5 5"/></svg></a>
	</div></nav>
</div>
<?php
get_footer();
