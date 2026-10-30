<?php
/**
 * /explore/the-bipartisanship-question/ – Investigation 002.
 *
 * Every figure in the prose is read from the published findings (the same
 * JSON the charts draw from), so text and graphics describe one dataset.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$inv  = function_exists( 'btbx_get_investigation' ) ? btbx_get_investigation( 'the-bipartisanship-question' ) : array( 'number' => '002', 'kicker' => 'Coalitions' );
$B    = btbd_findings( 'bipartisanship-116-118' );
$D    = btbd_findings( 'bipartisanship-deep' );
$ok   = is_array( $B ) && is_array( $D );
$fmt  = function ( $n ) { return btbd_n( $n ); };
$pct  = function ( $v, $d = 1 ) { return btbd_n( $v, $d ) . '%'; };

if ( $ok ) {
	$ex   = $B['excluding_ceremonial'];
	$bip  = btbd_pick( $ex, 'coalition', 'bipartisan' );
	$same = btbd_pick( $ex, 'coalition', 'same_party' );
	$solo = btbd_pick( $ex, 'coalition', 'solo' );
	$maj_b = btbd_pick( $B['majority_sponsor'], 'coalition', 'bipartisan' );
	$maj_s = btbd_pick( $B['majority_sponsor'], 'coalition', 'same_party' );
	$min_b = btbd_pick( $B['minority_sponsor'], 'coalition', 'bipartisan' );
	$min_s = btbd_pick( $B['minority_sponsor'], 'coalition', 'same_party' );
	$laws_b = btbd_pick( $B['laws_by_coalition'], 'coalition', 'bipartisan' );
	$laws_total = array_sum( wp_list_pluck( $B['laws_by_coalition'], 'laws' ) );
	$dose = $B['dose_response'];
	$dose_top = end( $dose );

	$field_total = array_sum( wp_list_pluck( $D['field_counts'], 'bills' ) );
	$field_bip = 0;
	foreach ( $D['field_counts'] as $r ) {
		if ( 'bipartisan' === $r['coalition'] ) {
			$field_bip += $r['bills'];
		}
	}
	$F = array();
	foreach ( $D['funnel'] as $r ) {
		$F[ $r['coalition'] ] = $r;
	}
	$door_b = 1000 * $F['bipartisan']['committee_action'] / $F['bipartisan']['n'];
	$door_s = 1000 * $F['same_party']['committee_action'] / $F['same_party']['n'];
	$conv = function ( $c, $a, $b ) use ( $F ) { return $F[ $c ][ $a ] ? 100 * $F[ $c ][ $b ] / $F[ $c ][ $a ] : 0; };

	$tl  = $D['time_to_law'];
	$med = $tl['median_days_to_law'];
	$lb  = array();
	foreach ( $D['late_bridges'] as $r ) {
		$lb[ $r['group'] ] = $r;
	}
	$snow_law = $D['snowball']['by_furthest_stage']['law']['avg_cross_party_cosponsors_by_day'];
	$comp = array();
	foreach ( $D['companions'] as $r ) {
		$comp[ $r['coalition'] ][ $r['has_identical_companion'] ? 'yes' : 'no' ] = $r;
	}
	$cm = $D['committees'];
	$sj = null;
	$hs = null;
	foreach ( $cm as $r ) {
		if ( 0 === strpos( $r['committee'], 'Judiciary' ) && 'Senate' === $r['chamber'] ) {
			$sj = $r;
		}
		if ( 0 === strpos( $r['committee'], 'Homeland Security and Governmental' ) ) {
			$hs = $r;
		}
	}
	$ty   = $D['twelve_years']['rows'];
	$ty_r = array();
	foreach ( $ty as $r ) {
		$ty_r[] = $r['pct_law_other'] > 0 ? $r['pct_law_bipartisan'] / $r['pct_law_other'] : 0;
	}
	$states = array_values( array_filter( $D['states'], function ( $s ) { return $s['bills'] >= 300 && strlen( $s['state'] ) === 2; } ) );
	usort( $states, function ( $a, $b ) { return $b['pct_bipartisan'] <=> $a['pct_bipartisan']; } );
	$st_top = array_slice( $states, 0, 3 );
	$st_low = array_slice( array_reverse( $states ), 0, 3 );
	$pairs = $D['top_pairs'];
	$updated = get_date_from_gmt( gmdate( 'Y-m-d H:i:s' ), 'F Y' );
}

get_header();
?>
<div class="bx bx-story bpq" data-bx-story data-bpq>
	<div class="bx-progress" aria-hidden="true"><span data-bx-progress></span></div>

	<nav class="bx-chapters" aria-label="Chapters">
		<ol>
			<li><a href="#field" data-bx-chapter-link="starts"><span>1</span>Day one</a></li>
			<li><a href="#door" data-bx-chapter-link="door"><span>2</span>The committee door</a></li>
			<li><a href="#hands" data-bx-chapter-link="hands"><span>3</span>More partners</a></li>
			<li><a href="#clock" data-bx-chapter-link="clock"><span>4</span>The clock</a></li>
			<li><a href="#rooms" data-bx-chapter-link="rooms"><span>5</span>Which rooms</a></li>
			<li><a href="#chambers" data-bx-chapter-link="chambers"><span>6</span>Two chambers</a></li>
			<li><a href="#map" data-bx-chapter-link="map"><span>7</span>The map</a></li>
			<li><a href="#bridges" data-bx-chapter-link="bridges"><span>8</span>Bridge builders</a></li>
			<li><a href="#evidence" data-bx-chapter-link="evidence"><span>9</span>The evidence</a></li>
			<li><a href="#method" data-bx-chapter-link="method"><span>M</span>Methods</a></li>
		</ol>
	</nav>

	<!-- Cover: the 1850 Senate, split in two inks that close as you scroll -->
	<header class="bpq-cover" id="top" data-bpq-cover>
		<div class="bpq-cover-stick">
			<div class="bpq-split" aria-hidden="true">
				<div class="bpq-split-half bpq-split-l"><?php echo btbd_img( 'senate-1850', 'bpq-split-img', '100vw', true ); // phpcs:ignore ?></div>
				<div class="bpq-split-half bpq-split-r"><?php echo btbd_img( 'senate-1850', 'bpq-split-img', '100vw', true ); // phpcs:ignore ?></div>
				<div class="bpq-seam"></div>
			</div>
			<div class="bpq-cover-copy bx-wrap">
				<p class="bx-label bx-seq" style="--seq:1"><a href="<?php echo esc_url( function_exists( 'btbx_explore_url' ) ? btbx_explore_url() : home_url( '/explore/' ) ); ?>">Explore</a><span aria-hidden="true">/</span><span>Investigation <?php echo esc_html( $inv['number'] ); ?></span><span aria-hidden="true">/</span><span><?php echo esc_html( $inv['kicker'] ); ?></span></p>
				<h1 class="bx-display bpq-title" aria-label="The Bipartisanship Question">
					<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:2">The Bipartisanship</span></span>
					<span class="bx-line" aria-hidden="true"><span class="bx-seq" style="--seq:3">Question</span></span>
				</h1>
				<p class="bpq-dek bx-seq" style="--seq:4">Washington swears by one rule: find a partner across the aisle before you file. We followed <?php echo $ok ? esc_html( $fmt( $field_total ) ) : 'every'; ?> bills from their first day to see what that partner is worth, and where.</p>
				<p class="bx-byline bpq-byline bx-seq" style="--seq:5"><span>By Between the Bills</span><span>Data: Library of Congress Bill Status records, via GovInfo</span><span>116th–118th Congresses, 2019–2024</span></p>
			</div>
			<p class="bx-credit bpq-cover-credit"><?php echo btbd_img_credit( 'senate-1850' ); // phpcs:ignore ?></p>
			<a class="bpq-cue" href="#intro"><span>Scroll</span><svg viewBox="0 0 12 28" aria-hidden="true" focusable="false"><path d="M6 0v26M1 21l5 5 5-5"/></svg></a>
		</div>
	</header>

	<?php if ( ! $ok ) : ?>
	<div class="bx-wrap bx-measure"><p class="bx-pending">The findings for this investigation could not be loaded right now. Please try again in a few minutes.</p></div>
	<?php else : ?>

	<section class="bx-plate bx-plate-cream bpq-intro" id="intro">
		<div class="bx-prose bx-wrap bx-measure">
			<p class="bx-lede" data-reveal>The engraving above shows the Senate in 1850, during the debate over Henry Clay’s compromise resolutions. Clay needed votes from both sides, and he went looking for them before the roll was called.</p>
			<p data-reveal>Members of Congress still work that way. A sponsor who wants a bill to move asks a colleague from the other party to sign on as an original cosponsor, so the bill is bipartisan from the day it is introduced. The custom is everywhere. The evidence for it is mostly anecdote.</p>
			<p data-reveal>So we checked the record. For every bill and joint resolution introduced from January 2019 to January 2025, we looked at who signed on the first day, then followed the bill through every committee referral, hearing, vote and signature in the Library of Congress’s files: <?php echo esc_html( $fmt( $field_total ) ); ?> bills, 680,906 cosponsorships, 290,617 recorded actions.</p>
		</div>

		<section class="bx-guess bx-wrap" aria-labelledby="bpq-guess-title" data-bpq-guess data-answer="<?php echo esc_attr( $laws_b['pct_of_laws'] ); ?>">
			<div class="bx-guess-card bpq-guess-card" data-reveal>
				<p class="bx-label">Before you scroll</p>
				<h2 class="bx-guess-q" id="bpq-guess-title">Of the <?php echo esc_html( $fmt( $laws_total ) ); ?> bills in this record that became law, what share had a cosponsor from the other party on day one?</h2>
				<div class="bx-guess-control">
					<label class="bx-guess-readout" for="bpq-guess-range"><span data-bpq-guess-value>50%</span><small data-bpq-guess-n>about 492 laws</small></label>
					<input type="range" id="bpq-guess-range" min="0" max="100" step="1" value="50" data-bpq-guess-range data-total="<?php echo esc_attr( $laws_total ); ?>">
					<div class="bx-guess-scale" aria-hidden="true"><span>None</span><span>All of them</span></div>
				</div>
				<div class="bx-guess-actions">
					<button type="button" class="bx-button" data-bpq-guess-lock>Lock in my guess</button>
					<a class="bx-guess-skip" href="#field">Skip</a>
				</div>
				<p class="bx-guess-result" data-bpq-guess-result aria-live="polite" hidden></p>
			</div>
		</section>
	</section>

	<!-- Chapter 1: every bill, sorted by day-one coalition -->
	<section class="bx-plate bx-plate-night bx-chapter bx-scrolly bpq-ch1" id="field" data-bx-chapter="starts" aria-labelledby="bpq-ch1-title">
		<header class="bpq-chapter-head bx-wrap">
			<p class="bx-label"><span>Chapter 1</span><span aria-hidden="true">/</span><span>Day one</span></p>
			<h2 class="bx-h2" id="bpq-ch1-title" data-reveal>Every bill starts with a coalition.</h2>
		</header>
		<div class="bx-scrolly-body">
			<div class="bx-sticky" data-bx-sticky>
				<div class="bx-sticky-inner">
					<div class="bx-counter" aria-hidden="true">
						<span class="bx-counter-n" data-bpq-counter><?php echo esc_html( $fmt( $field_total ) ); ?></span>
						<span class="bx-counter-label" data-bpq-counter-label>bills introduced</span>
					</div>
					<div class="bx-field-frame bx-field-frame-story bpq-field-frame">
						<canvas class="bx-field" data-bpq-field role="img" aria-label="<?php echo esc_attr( sprintf( 'One square for each of the %s bills introduced in the 116th to 118th Congresses. The coloring and grouping change as you scroll; the text beside the chart describes each view.', $fmt( $field_total ) ) ); ?>"></canvas>
						<div class="bx-plot-labels" data-bpq-labels aria-hidden="true"></div>
						<ul class="bpq-key" data-bpq-key aria-hidden="true">
							<li><i class="bpq-sw bpq-sw-bip"></i>Bipartisan on day one</li>
							<li><i class="bpq-sw bpq-sw-same"></i>Same party only</li>
							<li><i class="bpq-sw bpq-sw-solo"></i>No cosponsors</li>
						</ul>
					</div>
				</div>
			</div>
			<div class="bx-steps">
				<div class="bx-step" data-step="all">
					<p>Each square is one bill or joint resolution introduced in the 116th, 117th or 118th Congress: <strong><?php echo esc_html( $fmt( $field_total ) ); ?></strong> in all, in the order they were filed.</p>
				</div>
				<div class="bx-step" data-step="coalition">
					<p>Color each one by who signed on the day it was introduced. <strong class="bpq-hl-bip"><?php echo esc_html( $fmt( $field_bip ) ); ?></strong> bills, <?php echo esc_html( $pct( 100 * $field_bip / $field_total, 0 ) ); ?>, had at least one original cosponsor from the other party.</p>
					<p class="bx-step-aside">The rest either had cosponsors from the sponsor’s own party only, or no cosponsors at all.</p>
				</div>
				<div class="bx-step" data-step="plots">
					<p>Sort them into those three groups.</p>
				</div>
				<div class="bx-step" data-step="laws">
					<p>Now light up only the bills that became law. The bipartisan block glows. The other two barely flicker.</p>
				</div>
				<div class="bx-step" data-step="lawsOnly">
					<p>Pull the laws out and stack them together. <strong class="bpq-hl-bip"><?php echo esc_html( $fmt( $laws_b['laws'] ) ); ?></strong> of the <?php echo esc_html( $fmt( $laws_total ) ); ?>, <strong><?php echo esc_html( $pct( $laws_b['pct_of_laws'], 0 ) ); ?></strong>, started bipartisan, though only about a third of all bills did.</p>
					<p class="bx-step-aside" data-bpq-guess-callback hidden></p>
				</div>
				<div class="bx-step" data-step="ceremonial">
					<p>Some laws are easy for everyone: renaming a post office, a commemorative coin. Ringed squares are those ceremonial bills. Set them aside and the gap holds. <strong class="bpq-hl-bip"><?php echo esc_html( $pct( $bip['pct_became_law'] ) ); ?></strong> of bipartisan bills became law, against <strong><?php echo esc_html( $pct( $same['pct_became_law'] ) ); ?></strong> of same-party bills.</p>
					<p>That is <?php echo esc_html( btbd_x( $bip['pct_became_law'], $same['pct_became_law'] ) ); ?> times the rate. The rest of this investigation asks where that difference comes from.</p>
				</div>
			</div>
		</div>
		<details class="bx-data-table bx-wrap bx-measure">
			<summary>Show these counts as a table</summary>
			<table>
				<caption>Bills introduced in the 116th–118th Congresses by coalition on day one, ceremonial bills excluded</caption>
				<thead><tr><th scope="col">Coalition on day one</th><th scope="col">Bills</th><th scope="col">Out of committee</th><th scope="col">Passed a chamber</th><th scope="col">Became law</th></tr></thead>
				<tbody>
				<?php foreach ( array( 'bipartisan' => 'Bipartisan', 'same_party' => 'Same party only', 'solo' => 'No cosponsors' ) as $k => $label ) : $r = btbd_pick( $ex, 'coalition', $k ); ?>
					<tr><th scope="row"><?php echo esc_html( $label ); ?></th><td><?php echo esc_html( $fmt( $r['bills'] ) ); ?></td><td><?php echo esc_html( $pct( $r['pct_cleared_committee'] ) ); ?></td><td><?php echo esc_html( $pct( $r['pct_passed_one_chamber'] ) ); ?></td><td><?php echo esc_html( $pct( $r['pct_became_law'], 2 ) ); ?> (<?php echo esc_html( $fmt( $r['laws'] ) ); ?>)</td></tr>
				<?php endforeach; ?>
				</tbody>
			</table>
		</details>
	</section>

	<!-- Chapter 2: the committee door -->
	<section class="bx-plate bx-plate-cream bx-chapter bpq-door" id="door" data-bx-chapter="door" aria-labelledby="bpq-ch2-title">
		<?php btbd_titlecard( 2, 'The committee door', 'Most bills die without a hearing. The gap between bipartisan bills and the rest is widest at that first door.', 'hearing-1939', 'bpq-ch2-title' ); ?>
		<div class="bx-wrap">
			<div class="bpq-two">
				<div class="bx-prose bpq-two-text">
					<p data-reveal>A bill has to clear a series of gates: a committee has to take it up, report it, a chamber has to pass it, then the other chamber, then the president has to sign. Follow 1,000 bills from each group through those gates.</p>
					<p data-reveal>The first gate does most of the sorting. Out of every 1,000 bipartisan bills, <strong><?php echo esc_html( $fmt( round( $door_b ) ) ); ?></strong> got a hearing, a markup, a report or a discharge. Out of every 1,000 same-party bills, <strong><?php echo esc_html( $fmt( round( $door_s ) ) ); ?></strong>. That is <?php echo esc_html( btbd_x( $door_b, $door_s ) ); ?> times as many.</p>
					<p data-reveal>Past the door, the groups look more alike. Of bills that cleared committee, <?php echo esc_html( $pct( $conv( 'bipartisan', 'cleared_committee', 'passed_one' ), 0 ) ); ?> of bipartisan ones passed a chamber, against <?php echo esc_html( $pct( $conv( 'same_party', 'cleared_committee', 'passed_one' ), 0 ) ); ?> of same-party ones. Switch the chart to the share that made it through each gate to see it.</p>
				</div>
				<figure class="bpq-gates" data-bpq-gates>
					<div class="bx-seg bpq-seg" role="radiogroup" aria-label="Measure">
						<label><input type="radio" name="bpq-gate-mode" value="per1000" checked><span>Out of every 1,000</span></label>
						<label><input type="radio" name="bpq-gate-mode" value="conv"><span>Share through each gate</span></label>
					</div>
					<div class="bpq-gates-chart" data-bpq-gates-chart role="img" aria-label="Bills per 1,000 surviving each legislative gate, by coalition on day one."></div>
					<figcaption class="bpq-cap">Committee action: a recorded hearing, markup, report or discharge. Ceremonial bills excluded. Hover or focus a gate for the counts.</figcaption>
				</figure>
			</div>
		</div>
	</section>

	<!-- Chapter 3: more partners -->
	<section class="bx-plate bx-plate-blue bx-chapter bpq-hands" id="hands" data-bx-chapter="hands" aria-labelledby="bpq-ch3-title">
		<div class="bx-wrap">
			<header class="bpq-chapter-head">
				<p class="bx-label"><span>Chapter 3</span><span aria-hidden="true">/</span><span>More partners</span></p>
				<h2 class="bx-h2" id="bpq-ch3-title" data-reveal>One partner helps. Ten help more.</h2>
			</header>
			<div class="bpq-dose" data-bpq-dose>
				<div class="bpq-dose-control">
					<p class="bx-prose" data-reveal>Pick how many members of the other party signed on as original cosponsors.</p>
					<div class="bpq-dose-steps" role="radiogroup" aria-label="Original cosponsors from the other party">
						<?php foreach ( $dose as $i => $r ) : ?>
							<label><input type="radio" name="bpq-dose" value="<?php echo esc_attr( $i ); ?>" <?php checked( 1, $i ); ?>><span><?php echo esc_html( $r['original_cross_party_cosponsors'] ); ?></span></label>
						<?php endforeach; ?>
					</div>
					<p class="bpq-dose-read"><span class="bpq-dose-big" data-bpq-dose-big>–</span><span class="bpq-dose-sub" data-bpq-dose-sub>became law</span></p>
					<p class="bpq-dose-n" data-bpq-dose-n aria-live="polite"></p>
				</div>
				<figure class="bpq-dose-viz">
					<canvas class="bx-field bpq-waffle" data-bpq-waffle role="img" aria-label="1,000 squares; lit squares show how many bills per 1,000 with the selected number of cross-party original cosponsors became law."></canvas>
					<figcaption class="bpq-cap">1,000 bills. Lime squares became law; pale squares passed one chamber.</figcaption>
				</figure>
			</div>
			<div class="bpq-power" data-reveal>
				<h3 class="bx-h3">Does it only help the party in power?</h3>
				<p class="bx-prose">Bills from the majority party pass more often. Maybe the majority simply recruits more partners. So we split sponsors by whether their party controlled their chamber.</p>
				<div class="bpq-power-grid" data-bpq-power></div>
				<p class="bx-prose">A minority-party sponsor with a partner across the aisle, <?php echo esc_html( $pct( $min_b['pct_became_law'], 2 ) ); ?>, did four times better than a majority-party sponsor without one, <?php echo esc_html( $pct( $maj_s['pct_became_law'], 2 ) ); ?>.</p>
			</div>
		</div>
	</section>

	<!-- Chapter 4: the clock -->
	<section class="bx-plate bx-plate-cream bx-chapter bpq-clock" id="clock" data-bx-chapter="clock" aria-labelledby="bpq-ch4-title">
		<?php btbd_titlecard( 4, 'The clock', 'Bipartisan laws take longer to pass, and their coalitions keep growing after day one.', 'clock-1918', 'bpq-ch4-title' ); ?>
		<div class="bx-wrap">
			<div class="bpq-two">
				<div class="bx-prose bpq-two-text">
					<p data-reveal>Bipartisan bills became law more often, but not faster. The median bipartisan law took <strong><?php echo esc_html( $fmt( $med['bipartisan'] ) ); ?> days</strong> from introduction to signature. Same-party laws took <?php echo esc_html( $fmt( $med['same_party'] ) ); ?>, and bills with no cosponsors <?php echo esc_html( $fmt( $med['solo'] ) ); ?>.</p>
					<p data-reveal>Drag across the chart. In the first months the three lines run close together. The bipartisan line keeps climbing long after the others flatten.</p>
				</div>
				<figure class="bpq-curve" data-bpq-curve>
					<div class="bpq-curve-chart" data-bpq-curve-chart tabindex="0" role="img" aria-label="Cumulative share of bills that became law by days after introduction, by coalition on day one. Use left and right arrow keys to move along the chart."></div>
					<figcaption class="bpq-cap">Share of each group enacted within a given number of days of introduction. Ceremonial bills excluded.</figcaption>
				</figure>
			</div>

			<div class="bpq-two bpq-two-flip">
				<figure class="bpq-snow" data-bpq-snow>
					<div class="bpq-snow-chart" data-bpq-snow-chart role="img" aria-label="Average number of cross-party cosponsors by days after introduction, by the furthest stage each bill reached."></div>
					<figcaption class="bpq-cap">Average cosponsors from the other party, counted by the day they joined. Lines are grouped by how far the bill finally got.</figcaption>
				</figure>
				<div class="bx-prose bpq-two-text">
					<p data-reveal>Support keeps arriving. The bills that became law started with <?php echo esc_html( btbd_n( $snow_law[0], 1 ) ); ?> cross-party cosponsors on average and ended with <?php echo esc_html( btbd_n( end( $snow_law ), 1 ) ); ?>. Bills that never left committee barely moved.</p>
					<p data-reveal>That raises a fair question about our day-one rule. What about bills that found a partner later?</p>
				</div>
			</div>

			<div class="bpq-late" data-reveal>
				<h3 class="bx-h3">Late arrivals count too</h3>
				<div class="bpq-late-grid">
					<div class="bpq-late-card is-bip"><b data-bpq-count="<?php echo esc_attr( $lb['bipartisan_at_intro']['pct_became_law'] ); ?>" data-d="2"><?php echo esc_html( $pct( $lb['bipartisan_at_intro']['pct_became_law'], 2 ) ); ?></b><span>Bipartisan on day one</span><small><?php echo esc_html( $fmt( $lb['bipartisan_at_intro']['bills'] ) ); ?> bills</small></div>
					<div class="bpq-late-card is-late"><b data-bpq-count="<?php echo esc_attr( $lb['gained_cross_party_before_passage']['pct_became_law'] ); ?>" data-d="2"><?php echo esc_html( $pct( $lb['gained_cross_party_before_passage']['pct_became_law'], 2 ) ); ?></b><span>Found a partner later, before any chamber passed it</span><small><?php echo esc_html( $fmt( $lb['gained_cross_party_before_passage']['bills'] ) ); ?> bills</small></div>
					<div class="bpq-late-card is-never"><b data-bpq-count="<?php echo esc_attr( $lb['never_cross_party_before_passage']['pct_became_law'] ); ?>" data-d="2"><?php echo esc_html( $pct( $lb['never_cross_party_before_passage']['pct_became_law'], 2 ) ); ?></b><span>No cross-party cosponsor before passage</span><small><?php echo esc_html( $fmt( $lb['never_cross_party_before_passage']['bills'] ) ); ?> bills</small></div>
				</div>
				<p class="bx-prose">Bills that picked up a cross-party cosponsor after introduction, but before either chamber passed them, became law about as often as bills that started bipartisan. Timing seems to matter less than getting a partner at all. We count only cosponsors who joined before a floor vote, because support that arrives after a bill passes may follow its success instead of causing it.</p>
			</div>
		</div>
	</section>

	<!-- Chapter 5: which rooms -->
	<section class="bx-plate bx-plate-night bx-chapter bpq-rooms" id="rooms" data-bx-chapter="rooms" aria-labelledby="bpq-ch5-title">
		<div class="bx-wrap">
			<header class="bpq-chapter-head">
				<p class="bx-label"><span>Chapter 5</span><span aria-hidden="true">/</span><span>Which rooms</span></p>
				<h2 class="bx-h2" id="bpq-ch5-title" data-reveal>In some committees a partner is almost required. In others it barely registers.</h2>
			</header>
			<div class="bx-prose bx-measure">
				<?php if ( $sj ) : ?><p data-reveal>Every bill is sent to a committee first. In the Senate Judiciary Committee, <?php echo esc_html( $pct( $sj['pct_law_bipartisan'], 1 ) ); ?> of bipartisan bills became law. Of the <?php echo esc_html( $fmt( $sj['bills'] - $sj['bipartisan_bills'] ) ); ?> bills there without a cross-party cosponsor, <?php echo esc_html( $pct( $sj['pct_law_other'], 2 ) ); ?> did.<?php if ( $hs ) : ?> In Senate Homeland Security and Governmental Affairs, <?php echo esc_html( $pct( $hs['pct_cleared_bipartisan'], 0 ) ); ?> of bipartisan bills came out of committee, against <?php echo esc_html( $pct( $hs['pct_cleared_other'], 0 ) ); ?> of the rest.<?php endif; ?></p><?php endif; ?>
				<p data-reveal>Veterans’ affairs is the exception: bills from either kind of coalition do comparatively well there. Sort the chart, switch the measure, or flip to policy areas.</p>
			</div>
			<div class="bpq-rank" data-bpq-rank>
				<div class="bpq-rank-controls">
					<div class="bx-seg" role="radiogroup" aria-label="Group by">
						<span class="bx-seg-label">Group by</span>
						<label><input type="radio" name="bpq-rank-by" value="committee" checked><span>Committee</span></label>
						<label><input type="radio" name="bpq-rank-by" value="policy"><span>Policy area</span></label>
					</div>
					<div class="bx-seg" role="radiogroup" aria-label="Outcome" data-bpq-rank-metric>
						<span class="bx-seg-label">Outcome</span>
						<label><input type="radio" name="bpq-rank-m" value="law" checked><span>Became law</span></label>
						<label><input type="radio" name="bpq-rank-m" value="cleared"><span>Out of committee</span></label>
					</div>
					<div class="bx-seg" role="radiogroup" aria-label="Chamber" data-bpq-rank-chamber>
						<span class="bx-seg-label">Chamber</span>
						<label><input type="radio" name="bpq-rank-c" value="" checked><span>Both</span></label>
						<label><input type="radio" name="bpq-rank-c" value="House"><span>House</span></label>
						<label><input type="radio" name="bpq-rank-c" value="Senate"><span>Senate</span></label>
					</div>
					<label class="bx-select"><span class="bx-seg-label">Sort</span><select data-bpq-rank-sort><option value="gap">Largest gap</option><option value="bip">Highest bipartisan rate</option><option value="size">Most bills</option><option value="share">Most often bipartisan</option></select></label>
				</div>
				<div class="bpq-rank-legend" aria-hidden="true"><span><i class="bpq-dot bpq-dot-bip"></i>Bipartisan on day one</span><span><i class="bpq-dot bpq-dot-oth"></i>Everything else</span></div>
				<ol class="bpq-rank-list" data-bpq-rank-list aria-live="polite"></ol>
				<p class="bpq-cap">Committee of first referral, full committees with at least 400 bills and 100 bipartisan bills. Policy areas with at least 150 bills on each side. Ceremonial bills excluded.</p>
			</div>
		</div>
	</section>

	<!-- Chapter 6: two chambers, twelve years -->
	<section class="bx-plate bx-plate-cream bx-chapter bpq-chambers" id="chambers" data-bx-chapter="chambers" aria-labelledby="bpq-ch6-title">
		<?php btbd_titlecard( 6, 'Two chambers, twelve years', 'A bill needs both chambers. The strongest bipartisan bills arrive in both at once, and the advantage has held as Congress passes less.', 'joint-1917', 'bpq-ch6-title' ); ?>
		<div class="bx-wrap">
			<div class="bpq-two">
				<div class="bx-prose bpq-two-text">
					<p data-reveal>Sponsors often file the same bill in both chambers at once, an identical House and Senate version. Bipartisan bills with a companion like that became law <strong><?php echo esc_html( $pct( $comp['bipartisan']['yes']['pct_law'], 1 ) ); ?></strong> of the time, nearly double the <?php echo esc_html( $pct( $comp['bipartisan']['no']['pct_law'], 1 ) ); ?> for bipartisan bills without one. For same-party bills a companion added little: <?php echo esc_html( $pct( $comp['same_party']['yes']['pct_law'], 2 ) ); ?> against <?php echo esc_html( $pct( $comp['same_party']['no']['pct_law'], 2 ) ); ?>.</p>
				</div>
				<figure class="bpq-comp" data-bpq-comp>
					<div data-bpq-comp-chart role="img" aria-label="Share of bills that became law with and without an identical companion bill in the other chamber, by coalition."></div>
					<figcaption class="bpq-cap">Identical bill in the other chamber, as marked in the official record. A Congress usually enacts only one of the pair.</figcaption>
				</figure>
			</div>
			<div class="bpq-trend" data-bpq-trend>
				<h3 class="bx-h3" data-reveal>Twelve years of the same pattern</h3>
				<p class="bx-prose bx-measure" data-reveal>From the 113th Congress to the 118th, the share of bills that became law fell for everyone. The bipartisan premium did not. In every Congress since 2013, in both chambers, bipartisan bills became law at <?php echo esc_html( btbd_n( min( $ty_r ), 1 ) ); ?> to <?php echo esc_html( btbd_n( max( $ty_r ), 1 ) ); ?> times the rate of the rest.</p>
				<div class="bx-seg" role="radiogroup" aria-label="Chamber" data-bpq-trend-chamber>
					<label><input type="radio" name="bpq-trend-c" value="House" checked><span>House</span></label>
					<label><input type="radio" name="bpq-trend-c" value="Senate"><span>Senate</span></label>
				</div>
				<div class="bpq-trend-chart" data-bpq-trend-chart tabindex="0" role="img" aria-label="Share of bills that became law by Congress, 113th to 118th, bipartisan versus everything else. Use left and right arrow keys to move between Congresses."></div>
				<p class="bpq-cap">113th–118th Congresses, all bills including ceremonial, from our hosted release; the 116th–118th match this investigation’s counts exactly. The 119th Congress is still in session.</p>
			</div>
		</div>
	</section>

	<!-- Chapter 7: the map -->
	<section class="bx-plate bx-plate-lime bx-chapter bpq-mapch" id="map" data-bx-chapter="map" aria-labelledby="bpq-ch7-title">
		<?php btbd_titlecard( 7, 'The map', 'Where the sponsor comes from changes how often a bill starts with a partner.', 'atlas-1883', 'bpq-ch7-title' ); ?>
		<div class="bx-wrap">
			<div class="bx-prose bx-measure">
				<p data-reveal>Among delegations that sponsored at least 300 bills, <?php echo esc_html( implode( ', ', array_map( function ( $s ) use ( $pct ) { return $s['state'] . ' (' . $pct( $s['pct_bipartisan'], 0 ) . ')'; }, $st_top ) ) ); ?> most often started bills with a cross-party partner. <?php echo esc_html( implode( ', ', array_map( function ( $s ) use ( $pct ) { return $s['state'] . ' (' . $pct( $s['pct_bipartisan'], 0 ) . ')'; }, $st_low ) ) ); ?> did so least.</p>
			</div>
			<div class="bpq-map" data-bpq-map>
				<div class="bx-seg" role="radiogroup" aria-label="Map measure">
					<label><input type="radio" name="bpq-map-m" value="pct_bipartisan" checked><span>Started bipartisan</span></label>
					<label><input type="radio" name="bpq-map-m" value="pct_law"><span>Became law</span></label>
				</div>
				<div class="bpq-map-grid" data-bpq-map-grid role="img" aria-label="Tile map of the United States. Each state is one tile, shaded by the selected measure for bills its members sponsored."></div>
				<div class="bpq-map-scale" data-bpq-map-scale aria-hidden="true"></div>
				<p class="bpq-map-read" data-bpq-map-read aria-live="polite">Hover or tap a state.</p>
			</div>
		</div>
	</section>

	<!-- Chapter 8: bridge builders -->
	<section class="bx-plate bx-plate-night bx-chapter bpq-bridges" id="bridges" data-bx-chapter="bridges" aria-labelledby="bpq-ch8-title">
		<?php btbd_titlecard( 8, 'Bridge builders', 'Look up any member of Congress and see who they work with across the aisle.', 'handshake-1937', 'bpq-ch8-title' ); ?>
		<div class="bx-wrap">
			<div class="bpq-net" data-bpq-net>
				<div class="bpq-net-side">
					<label class="bpq-net-search"><span class="bx-seg-label">Find a member</span><input type="search" placeholder="Name or state, like Collins or PA" autocomplete="off" data-bpq-net-q aria-controls="bpq-net-sugg"></label>
					<ul class="bpq-net-sugg" id="bpq-net-sugg" data-bpq-net-sugg role="listbox" hidden></ul>
					<div class="bpq-net-card" data-bpq-net-card aria-live="polite"><p class="bx-pending">Loading…</p></div>
				</div>
				<figure class="bpq-net-viz">
					<svg class="bpq-net-svg" data-bpq-net-svg role="img" aria-label="Network of the selected member's twelve most frequent cross-party partners. Line thickness shows how many bills they shared."></svg>
					<figcaption class="bpq-cap">Top twelve cross-party partners: bills where one sponsored and the other cosponsored, 116th–119th Congresses. Click a partner to follow their network.</figcaption>
				</figure>
			</div>
			<div class="bpq-pairs" data-reveal>
				<h3 class="bx-h3">The busiest partnerships</h3>
				<ol class="bpq-pairs-list">
					<?php foreach ( array_slice( $pairs, 0, 10 ) as $p ) : ?>
						<li><span class="bpq-pair-a is-<?php echo esc_attr( strtolower( $p['party_a'] ) ); ?>"><?php echo esc_html( $p['member_a'] ); ?></span><span class="bpq-pair-x" aria-hidden="true">×</span><span class="bpq-pair-b is-<?php echo esc_attr( strtolower( $p['party_b'] ) ); ?>"><?php echo esc_html( $p['member_b'] ); ?></span><b><?php echo esc_html( $fmt( $p['shared_bills'] ) ); ?></b><small><?php echo esc_html( $fmt( $p['shared_laws'] ) ); ?> law<?php echo 1 === (int) $p['shared_laws'] ? '' : 's'; ?></small></li>
					<?php endforeach; ?>
				</ol>
			</div>
		</div>
	</section>

	<!-- Chapter 9: evidence -->
	<section class="bx-plate bx-plate-coral bx-chapter bpq-evidence" id="evidence" data-bx-chapter="evidence" aria-labelledby="bpq-ch9-title">
		<div class="bx-wrap">
			<header class="bpq-chapter-head">
				<p class="bx-label"><span>Chapter 9</span><span aria-hidden="true">/</span><span>The evidence</span></p>
				<h2 class="bx-h2" id="bpq-ch9-title" data-reveal>Check every number yourself.</h2>
			</header>
			<div class="bpq-ev-grid">
				<a class="bpq-ev" href="<?php echo esc_url( add_query_arg( array( 'coalition' => 'bipartisan', 'furthest' => 'law' ), btbd_data_url() ) . '#browse' ); ?>" data-reveal><span class="bpq-ev-k">Browse</span><span class="bpq-ev-t">Every bipartisan bill that became law</span><span class="bpq-ev-d">Filter by Congress, chamber, party or policy area. Open any bill for its full timeline.</span></a>
				<a class="bpq-ev" href="<?php echo esc_url( btbd_data_url( '#sql' ) ); ?>" data-reveal><span class="bpq-ev-k">Query</span><span class="bpq-ev-t">Run our analysis in SQL</span><span class="bpq-ev-d">680,906 cosponsorships and 1.77 million records load straight into your browser.</span></a>
				<a class="bpq-ev" href="<?php echo esc_url( BTBD_REPO . '/blob/main/scripts/build_bipartisanship_deep.py' ); ?>" data-reveal><span class="bpq-ev-k">Reproduce</span><span class="bpq-ev-t">Read the code</span><span class="bpq-ev-d">The scripts that built every chart, with the source data and checksums.</span></a>
			</div>
		</div>
	</section>

	<!-- Methods -->
	<section class="bx-plate bx-plate-cream" id="method" data-bx-chapter="method" aria-labelledby="bpq-method-title">
		<div class="bx-method bx-wrap">
			<div class="bx-method-grid">
				<header>
					<p class="bx-label">Methodology</p>
					<h2 class="bx-h2" id="bpq-method-title">How we counted</h2>
				</header>
				<div class="bx-method-body">
					<h3 class="bx-h3">The population</h3>
					<p>Every bill (H.R., S.) and joint resolution (H.J.Res., S.J.Res.) introduced in the 116th, 117th and 118th Congresses, January 3, 2019 to January 3, 2025: <?php echo esc_html( $fmt( $field_total ) ); ?> measures. Rates exclude ceremonial bills unless noted, and bills from the 11 independents and others outside the two major parties. The 119th Congress is still in session, so its bills appear only in the Open Data tab, labeled in progress.</p>
					<h3 class="bx-h3">Definitions</h3>
					<dl class="bx-defs">
						<div><dt>Bipartisan on day one</dt><dd>At least one original cosponsor, someone who joined on the day of introduction, belongs to the other major party from the sponsor.</dd></div>
						<div><dt>Same party only</dt><dd>Original cosponsors, all from the sponsor’s party (or independents).</dd></div>
						<div><dt>No cosponsors</dt><dd>No original cosponsors.</dd></div>
						<div><dt>Committee action</dt><dd>A recorded hearing, markup, committee or subcommittee report, or discharge.</dd></div>
						<div><dt>Out of committee</dt><dd>Reported (Library of Congress action codes 5000, 14000), discharged (14500, H12300), or passed a chamber.</dd></div>
						<div><dt>Passed a chamber</dt><dd>Action code 8000 (House) or 17000 (Senate).</dd></div>
						<div><dt>Became law</dt><dd>The record lists a public or private law. Days to law run from introduction to the Became Law action (36000, 41000, E40000).</dd></div>
						<div><dt>Ceremonial</dt><dd>Policy area Commemorations, or a title designating a post office facility.</dd></div>
						<div><dt>Majority sponsor</dt><dd>The sponsor’s party controlled their chamber in that Congress. The Senate of the 117th counts as Democratic, by the vice president’s tie-breaking vote.</dd></div>
						<div><dt>Late arrival</dt><dd>No cross-party original cosponsor, but at least one cross-party cosponsor joined after introduction and before the first chamber passage, if there was one.</dd></div>
						<div><dt>Committee of first referral</dt><dd>The first full committee the bill was referred to.</dd></div>
						<div><dt>Partners</dt><dd>Pairs of members from opposite parties where one sponsored a bill and the other cosponsored it, counted once per bill, 116th–119th Congresses.</dd></div>
					</dl>
					<h3 class="bx-h3">What this can and cannot show</h3>
					<ul>
						<li>These are patterns in the record. Bipartisan bills differ from other bills in many ways: leaders’ priorities, must-pass deadlines, how controversial the subject is. A higher rate among bipartisan bills does not show that adding a cosponsor would change any one bill’s fate.</li>
						<li>Text often becomes law inside a larger package. A bill whose provisions were folded into an omnibus counts as not enacted unless the record marks it as identical to the bill that passed.</li>
						<li>Cosponsor counts measure signatures, not effort. A member can work across the aisle without cosponsoring.</li>
						<li>The twelve-year trend uses our earlier hosted release for the 113th–115th Congresses; its definitions match, and its 116th–118th counts equal this investigation’s.</li>
					</ul>
					<h3 class="bx-h3">Source and reproducibility</h3>
					<p>Library of Congress Bill Status records for the 116th–119th Congresses, downloaded from GovInfo’s bulk data repository and built into a typed SQL database of 1,765,337 records with quality flags. The build, the analysis and every input are public: <a href="<?php echo esc_url( BTBD_REPO . '/blob/main/scripts/build_bipartisan_116_118.py' ); ?>">build_bipartisan_116_118.py</a>, <a href="<?php echo esc_url( BTBD_REPO . '/blob/main/scripts/build_bipartisanship_deep.py' ); ?>">build_bipartisanship_deep.py</a>, <a href="<?php echo esc_url( BTBD_REPO . '/blob/main/docs/collections/pathways-116-119-sql.md' ); ?>">database methods</a>.</p>
					<p>Bill Status data is published by the U.S. government and is in the public domain. Spotted an error? <a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>">Tell us</a>.</p>
				</div>
			</div>
		</div>
	</section>

	<?php endif; ?>

	<nav class="bx-plate bx-plate-blue" aria-label="More from Explore"><div class="bx-next bx-wrap">
		<a class="bx-next-link" href="<?php echo esc_url( btbd_data_url() ); ?>"><span class="bx-label">Next</span><span class="bx-next-title">Open Data</span><svg viewBox="0 0 28 12" aria-hidden="true" focusable="false"><path d="M0 6h26M21 1l5 5-5 5"/></svg></a>
		<a class="bx-next-link" href="<?php echo esc_url( function_exists( 'btbx_explore_url' ) ? btbx_explore_url() : home_url( '/explore/' ) ); ?>"><span class="bx-label">Back to</span><span class="bx-next-title">Explore</span><svg viewBox="0 0 28 12" aria-hidden="true" focusable="false"><path d="M0 6h26M21 1l5 5-5 5"/></svg></a>
	</div></nav>
</div>
<?php
get_footer();
