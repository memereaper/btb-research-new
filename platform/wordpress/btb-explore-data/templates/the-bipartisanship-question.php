<?php
/**
 * /explore/the-bipartisanship-question/ — Investigation 002.
 * Every figure is read from the published findings (btb-open API, route=findings),
 * built by scripts/build_bipartisan_116_118.py in the research repository.
 */
if ( ! defined( 'ABSPATH' ) ) exit;

$inv = function_exists( 'btbx_get_investigation' ) ? btbx_get_investigation( 'the-bipartisanship-question' ) : array( 'number' => '002', 'kicker' => 'Coalitions', 'title' => 'The Bipartisanship Question' );
$F   = btbd_findings();
$img = function ( $name, $cls = 'bx-riso bx-riso-multiply' ) {
	return function_exists( 'btbx_img' ) ? btbx_img( $name, $cls, '(max-width: 900px) 100vw, 60vw', true ) : '';
};

if ( $F ) {
	$all  = $F['all_bills'];
	$ex   = $F['excluding_ceremonial'];
	$bip  = btbd_row( $ex, 'bipartisan' );
	$same = btbd_row( $ex, 'same_party' );
	$solo = btbd_row( $ex, 'solo' );
	$ratio = $same['pct_became_law'] > 0 ? $bip['pct_became_law'] / $same['pct_became_law'] : 0;
	$total = 0; foreach ( $all as $r ) { $total += $r['bills']; }
	$bip_all = btbd_row( $all, 'bipartisan' );
	$share_bills = 100 * $bip_all['bills'] / max( 1, $total );
	$law_share = 0; $laws = 0;
	foreach ( $F['laws_by_coalition'] as $r ) { $laws += $r['laws']; if ( 'bipartisan' === $r['coalition'] ) $law_share = $r['pct_of_laws']; }
	$maj_b = btbd_row( $F['majority_sponsor'], 'bipartisan' ); $maj_s = btbd_row( $F['majority_sponsor'], 'same_party' );
	$min_b = btbd_row( $F['minority_sponsor'], 'bipartisan' ); $min_s = btbd_row( $F['minority_sponsor'], 'same_party' );
	$dose  = $F['dose_response']; $top = end( $dose ); reset( $dose );
	$grow  = $F['later_coalition_growth'];
	$law_g = null; foreach ( $grow as $g ) { if ( 'law' === $g['furthest'] ) $law_g = $g; }
}
get_header();
?>
<div class="bx bx-story btbd" data-btbd-page="bipartisan">

	<section class="bx-plate bx-plate-coral bx-hero-plate">
	<header class="bx-hero bx-wrap" id="top">
		<p class="bx-label bx-seq" style="--seq:1"><a href="<?php echo esc_url( btbd_url( '' ) ); ?>">Explore</a><span aria-hidden="true">/</span><span>Investigation <?php echo esc_html( $inv['number'] ); ?></span><span aria-hidden="true">/</span><span><?php echo esc_html( $inv['kicker'] ); ?></span></p>
		<h1 class="bx-display bx-hero-title" aria-label="<?php echo esc_attr( $inv['title'] ); ?>">
			<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:2">The Bipartisanship</span></span>
			<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:3">Question</span></span>
		</h1>
		<p class="bx-hero-dek bx-seq" style="--seq:4">Does reaching across the aisle on day one change a bill’s odds of becoming law?</p>
		<div class="bx-hero-img" aria-hidden="true"><?php echo $img( 'signing-1964' ); // phpcs:ignore ?></div>
		<p class="bx-byline bx-seq" style="--seq:5"><span>By Between the Bills</span><span>Data: Library of Congress Bill Status records, via GovInfo</span><span>116th–118th Congress, 2019–2024</span></p>
		<?php if ( function_exists( 'btbx_img_credit' ) ) : ?><p class="bx-credit bx-hero-credit"><?php echo btbx_img_credit( 'signing-1964' ); // phpcs:ignore ?></p><?php endif; ?>
	</header>
	</section>

	<?php if ( ! $F ) : ?>
	<div class="bx-wrap bx-measure"><p class="bx-pending">The findings are loading from the data service. Refresh in a moment.</p></div>
	<?php else : ?>

	<section class="bx-plate bx-plate-cream">
	<div class="bx-wrap bx-measure btbd-prose">
		<p class="btbd-lede">From January 2019 to January 2025, members of Congress introduced <?php echo esc_html( btbd_n( $total ) ); ?> bills and joint resolutions. <?php echo esc_html( btbd_n( $laws ) ); ?> became law. We sorted every one by a single fact recorded on the day it was introduced: did anyone from the other party sign on?</p>

		<div class="btbd-guess" data-btbd-guess data-answer="<?php echo esc_attr( round( $law_share ) ); ?>">
			<p class="btbd-kicker">Before you scroll</p>
			<p class="btbd-guess-q"><?php echo esc_html( round( $share_bills ) ); ?>% of these bills started with a cosponsor from the other party. What share of the laws did?</p>
			<p class="btbd-guess-val"><span data-btbd-guess-out>50</span>%</p>
			<input type="range" min="0" max="100" value="50" step="1" aria-label="Your guess, percent of laws" data-btbd-guess-input>
			<div class="btbd-guess-actions"><button type="button" class="btbd-btn" data-btbd-guess-go>Lock in my guess</button></div>
			<p class="btbd-guess-reveal" hidden data-btbd-guess-reveal><strong><?php echo esc_html( btbd_n( $law_share, 1 ) ); ?>%</strong> of the laws began bipartisan. <span data-btbd-guess-verdict></span></p>
		</div>
	</div>
	</section>

	<section class="bx-plate bx-plate-blue btbd-chapter" id="odds">
	<div class="bx-wrap">
		<p class="btbd-kicker btbd-on-dark">1 · The odds</p>
		<h2 class="btbd-h2 btbd-on-dark"><?php echo esc_html( btbd_n( $ratio, 1 ) ); ?> times as likely to become law</h2>
		<p class="btbd-big btbd-on-dark">Of every 1,000 bills that began with cross-party support, <strong><?php echo esc_html( btbd_n( round( $bip['pct_became_law'] * 10 ) ) ); ?></strong> became law. Of every 1,000 whose original cosponsors were all from the sponsor’s party, <strong><?php echo esc_html( btbd_n( round( $same['pct_became_law'] * 10 ) ) ); ?></strong>. Bills with no cosponsors at all: <strong><?php echo esc_html( btbd_n( round( $solo['pct_became_law'] * 10 ) ) ); ?></strong>.</p>
		<div class="btbd-chart" data-btbd-chart="ladder" role="img" aria-label="Share of bills reaching each stage, by coalition at introduction"></div>
		<p class="btbd-note btbd-on-dark">Ceremonial bills (commemorations and post-office namings) are left out here because they pass at unusual rates with home-state delegations from both parties. Including them, the rates are <?php echo esc_html( btbd_n( btbd_row( $all, 'bipartisan' )['pct_became_law'], 1 ) ); ?>% and <?php echo esc_html( btbd_n( btbd_row( $all, 'same_party' )['pct_became_law'], 1 ) ); ?>%.</p>
	</div>
	</section>

	<section class="bx-plate bx-plate-cream btbd-chapter" id="dose">
	<div class="bx-wrap bx-measure btbd-prose">
		<p class="btbd-kicker">2 · More is more</p>
		<h2 class="btbd-h2">The odds climb with every name from across the aisle</h2>
		<p>One cross-party original cosponsor already separates a bill from the pack. Ten or more, and <?php echo esc_html( btbd_n( $top['pct_became_law'], 1 ) ); ?>% became law, about <?php echo esc_html( btbd_n( $dose[0]['pct_became_law'] > 0 ? $top['pct_became_law'] / $dose[0]['pct_became_law'] : 0 ) ); ?> times the rate for bills with none.</p>
	</div>
	<div class="bx-wrap"><div class="btbd-chart" data-btbd-chart="dose" role="img" aria-label="Became-law rate by number of cross-party original cosponsors"></div></div>
	</section>

	<section class="bx-plate bx-plate-cream btbd-chapter" id="power">
	<div class="bx-wrap bx-measure btbd-prose">
		<p class="btbd-kicker">3 · Majority and minority</p>
		<h2 class="btbd-h2">It helps the party in power, and it matters more for the party out of it</h2>
		<p>A fair objection: bills from the majority party pass more often, and maybe the majority just recruits more partners. So we split sponsors by whether their party controlled their chamber. The gap holds on both sides. For majority sponsors, a bipartisan start meant <?php echo esc_html( btbd_n( $maj_b['pct_became_law'], 1 ) ); ?>% against <?php echo esc_html( btbd_n( $maj_s['pct_became_law'], 1 ) ); ?>%. For the minority, <?php echo esc_html( btbd_n( $min_b['pct_became_law'], 1 ) ); ?>% against <?php echo esc_html( btbd_n( $min_s['pct_became_law'], 1 ) ); ?>%. A minority sponsor with a cross-party partner did better than a majority sponsor without one.</p>
	</div>
	<div class="bx-wrap"><div class="btbd-chart" data-btbd-chart="power" role="img" aria-label="Became-law rate by coalition, majority versus minority sponsors"></div></div>
	</section>

	<section class="bx-plate bx-plate-night btbd-chapter" id="areas">
	<div class="bx-wrap">
		<p class="btbd-kicker btbd-on-dark">4 · Policy areas</p>
		<h2 class="btbd-h2 btbd-on-dark">Where crossing the aisle pays, and where it doesn’t</h2>
		<p class="btbd-big btbd-on-dark btbd-measure">In almost every policy area, bipartisan bills became law more often. The exception is bills on Native American issues, where both kinds passed at about the same rate. Each row shows the law rate for bills that began bipartisan (lime) and for those that did not (pink).</p>
		<div class="btbd-chart" data-btbd-chart="areas" role="img" aria-label="Became-law rate by policy area, bipartisan versus not"></div>
		<p class="btbd-note btbd-on-dark">Areas with fewer than 150 bills on either side are not shown. Where only a few laws passed, small changes move a rate a lot, so read the gap, not the ratio.</p>
	</div>
	</section>

	<section class="bx-plate bx-plate-cream btbd-chapter" id="grow">
	<div class="bx-wrap bx-measure btbd-prose">
		<p class="btbd-kicker">5 · Why day one</p>
		<h2 class="btbd-h2">Support follows success, so we measured before it could</h2>
		<p>Bills that move attract partners. The laws in this study started with <?php echo esc_html( btbd_n( $law_g['avg_original_cross'], 1 ) ); ?> cross-party cosponsors on average and finished with <?php echo esc_html( btbd_n( $law_g['avg_final_cross'], 1 ) ); ?>. Counting every cosponsor would credit bipartisanship for momentum it did not create. That is why every comparison here uses only original cosponsors, recorded on the day of introduction.</p>
	</div>
	<div class="bx-wrap"><div class="btbd-chart" data-btbd-chart="grow" role="img" aria-label="Cross-party cosponsors at introduction and at the end, by furthest stage reached"></div></div>
	</section>

	<section class="bx-plate bx-plate-cream btbd-chapter" id="people">
	<div class="bx-wrap bx-measure btbd-prose">
		<p class="btbd-kicker">6 · The bridge builders</p>
		<h2 class="btbd-h2">Who signs across the aisle most</h2>
		<p>Share of each member’s cosponsorships, 116th–119th Congress, that went to bills from the other party. Members with at least 200 cosponsorships.</p>
		<ol class="btbd-people" data-btbd-people><li class="btbd-muted">Loading…</li></ol>
	</div>
	</section>

	<section class="bx-plate bx-plate-cream btbd-chapter" id="evidence">
	<div class="bx-wrap bx-measure btbd-prose">
		<p class="btbd-kicker">7 · The evidence</p>
		<h2 class="btbd-h2">Every bill behind these numbers</h2>
		<p>Each of the bills is in <a href="<?php echo esc_url( btbd_url( 'open-record' ) ); ?>">The Open Record</a>, our searchable database. Start with the bipartisan bills that became law.</p>
		<p><a class="btbd-btn" href="<?php echo esc_url( add_query_arg( array( 'coalition' => 'bipartisan', 'furthest' => 'law' ), btbd_url( 'open-record' ) ) ); ?>">Open the bipartisan laws</a></p>
	</div>
	</section>

	<section class="bx-plate bx-plate-cream btbd-chapter" id="method">
	<div class="bx-wrap bx-measure btbd-prose btbd-method">
		<p class="btbd-kicker">Methods and limits</p>
		<h2 class="btbd-h2">How we did this</h2>
		<p><strong>Universe.</strong> <?php echo esc_html( btbd_n( $total ) ); ?> House and Senate bills and joint resolutions introduced in the 116th, 117th and 118th Congresses with a Democratic or Republican sponsor. The 119th Congress is still in session and is left out of every rate.</p>
		<p><strong>Coalition at introduction.</strong> From the original cosponsors marked in the official Bill Status record. Bipartisan means at least one original cosponsor from the other major party. Independents are not counted as cross-party.</p>
		<p><strong>Stages.</strong> From Library of Congress action codes: reported by committee, discharged, passed the House, passed the Senate; laws from the official law identifiers.</p>
		<p><strong>What this shows and does not show.</strong> This is a strong, consistent association across three Congresses, both chambers’ majorities and almost every policy area. It is not proof that adding a cosponsor causes a bill to pass. Sponsors may recruit partners for bills they already expect to move, and less contested subjects draw both parties. We reduce two obvious confounds, ceremonial bills and majority status, but cannot remove them.</p>
		<p><strong>Checks.</strong> Our 118th Congress counts match an independent earlier build of the same records for all 16,565 measures. Laws per Congress match official public-law totals for the 116th (344) and 118th (274).</p>
		<p><strong>Reproduce it.</strong> Code, data and the full findings are public in the <a href="https://github.com/memereaper/btb-research-new/tree/main/investigations/bipartisanship-116-118">research repository</a>. The numbers on this page come from the same <a href="<?php echo esc_url( add_query_arg( 'route', 'findings', BTBD_API ) ); ?>">findings file</a>.</p>
	</div>
	</section>

	<?php endif; ?>
</div>
<?php get_footer();
