<?php
/**
 * Archival images for investigation 002 and the Open Data tab. All public
 * domain (U.S. government works or Library of Congress photographs with no
 * known restrictions). Fetched once from Wikimedia Commons into this site's
 * uploads, resized to 800/1600px, served from here, and credited with every use.
 * None of these repeat the images used by investigation 001.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

function btbd_images() {
	return array(
		'senate-1850'  => array(
			'file'   => 'The United States Senate, A.D. 1850, by Peter F. Rothermel (crop1).jpg',
			'alt'    => 'Engraving of the crowded Old Senate Chamber in 1850, Henry Clay standing to speak on his compromise resolutions while senators and the gallery look on.',
			'credit' => 'After Peter F. Rothermel, The United States Senate, A.D. 1850, engraved by Robert Whitechurch, 1855. Library of Congress.',
		),
		'hearing-1939' => array(
			'file'   => 'Senate Interstate Commerce Committee opens hearings today on transportation. Washington, D.C., April 3. The Senate Interstate Commerce Committee got off today for a series of hearings on LCCN2016875365.jpg',
			'alt'    => 'A senator at the committee table during a Senate Interstate Commerce Committee hearing, with staff and witnesses seated behind him.',
			'credit' => 'Harris & Ewing, Senate Interstate Commerce Committee hearing, April 3, 1939. Library of Congress.',
		),
		'clock-1918'   => array(
			'file'   => 'Senate Sergeant at Arms Charles Higgins turns forward the Ohio Clock for the first Daylight Saving Time, while Senators William Calder (NY), William Saulsbury, Jr. (DE), and Joseph T. LOC hec.13949.jpg',
			'alt'    => 'The Senate sergeant at arms reaches up to move the hands of the tall Ohio Clock forward while three senators, a Republican and two Democrats, stand below.',
			'credit' => 'Harris & Ewing, Sergeant at Arms Charles Higgins turns the Ohio Clock forward for the first Daylight Saving Time, watched by Senators Calder, Saulsbury and Robinson, 1918. Library of Congress.',
		),
		'handshake-1937' => array(
			'file'   => 'Wallace appears before senate Agri. committee. Washington, D.C., Nov. 17. Secretary of Agriculture Henry Wallace, left; shaking hands with Senator George Norris of Neb. After Wallace LCCN2016872613.jpg',
			'alt'    => 'Secretary of Agriculture Henry Wallace shakes hands across a committee table with Senator George Norris of Nebraska.',
			'credit' => 'Harris & Ewing, Henry Wallace and Senator George Norris at the Senate Agriculture Committee, November 17, 1937. Library of Congress.',
		),
		'joint-1917'   => array(
			'file'   => 'Pres. Wilson addressing Joint Session of Congress LOC hec.13599.jpg',
			'alt'    => 'The House chamber packed for a joint session, members of both chambers seated below the rostrum as President Wilson speaks.',
			'credit' => 'Harris & Ewing, President Wilson addressing a joint session of Congress, 1917. Library of Congress.',
		),
		'atlas-1883'   => array(
			'file'   => "Scribner's statistical atlas of the United States, showing by graphic methods their present condition and their political, social and industrial development LOC a40001834-23.jpg",
			'alt'    => 'A hand-colored 1883 map of the United States from a statistical atlas, with state and county lines.',
			'credit' => "Scribner's Statistical Atlas of the United States, 1883. Library of Congress Geography and Map Division.",
		),
		'census-1939'  => array(
			'file'   => 'New machine to speed up statistics of census of 1940. Washington, D.C., Dec. 2. Back in 1870, it took 7 years to compile statistics from the facts taken by census takers, but in the next 10 LCCN2016876696.jpg',
			'alt'    => 'Two Census Bureau clerks feed long paper tabulation sheets into a new statistical machine built for the 1940 census.',
			'credit' => 'Harris & Ewing, a new tabulating machine for the 1940 census, December 2, 1939. Library of Congress.',
		),
		'cards-1910'   => array(
			'file'   => 'Card Division of the Library of Congress 3c18631u original.jpg',
			'alt'    => 'Long tables in the Library of Congress Card Division covered with stacked catalog cards, clerks working at the far end of the room.',
			'credit' => 'The Card Division of the Library of Congress, between 1900 and 1920. Library of Congress.',
		),
		'keypunch-1950' => array(
			'file'   => 'Keypunch operator 1950 census IBM 016.jpg',
			'alt'    => 'A Census Bureau keypunch operator types census answers into punch cards on an IBM 016 machine.',
			'credit' => 'Keypunch operator processing the 1950 census on an IBM 016 card punch. U.S. Census Bureau.',
		),
	);
}

function btbd_img_dir() {
	$up = wp_upload_dir( null, false );
	return trailingslashit( $up['basedir'] ) . 'btb-explore-data/img/';
}
function btbd_img_url() {
	$up = wp_upload_dir( null, false );
	return set_url_scheme( trailingslashit( $up['baseurl'] ) . 'btb-explore-data/img/' );
}
function btbd_img_manifest() {
	static $m = null;
	if ( null !== $m ) {
		return $m;
	}
	$f = btbd_img_dir() . 'manifest.json';
	$m = file_exists( $f ) ? json_decode( (string) file_get_contents( $f ), true ) : array();
	return $m = is_array( $m ) ? $m : array();
}

/** <img> for an archival image, or '' until it has been fetched. */
function btbd_img( $slug, $class = '', $sizes = '100vw', $eager = false ) {
	$man  = btbd_img_manifest();
	$list = btbd_images();
	if ( empty( $man[ $slug ] ) || empty( $list[ $slug ] ) ) {
		return '';
	}
	$e      = $man[ $slug ];
	$base   = btbd_img_url();
	$srcset = array();
	foreach ( $e['files'] as $w => $file ) {
		$srcset[] = esc_url( $base . $file ) . ' ' . (int) $w . 'w';
	}
	$widths = array_keys( $e['files'] );
	sort( $widths );
	return sprintf(
		'<img class="%s" src="%s" srcset="%s" sizes="%s" width="%d" height="%d" alt="%s" decoding="async" %s>',
		esc_attr( $class ),
		esc_url( $base . $e['files'][ end( $widths ) ] ),
		implode( ', ', $srcset ),
		esc_attr( $sizes ),
		(int) $e['w'],
		(int) $e['h'],
		esc_attr( $list[ $slug ]['alt'] ),
		$eager ? 'fetchpriority="high"' : 'loading="lazy"'
	);
}

function btbd_img_src( $slug, $w = 1600 ) {
	$man = btbd_img_manifest();
	if ( empty( $man[ $slug ]['files'] ) ) {
		return '';
	}
	$files = $man[ $slug ]['files'];
	return btbd_img_url() . ( isset( $files[ $w ] ) ? $files[ $w ] : end( $files ) );
}

function btbd_img_credit( $slug ) {
	$list = btbd_images();
	if ( empty( $list[ $slug ] ) ) {
		return '';
	}
	return sprintf(
		'%s <a href="%s">Public domain</a>.',
		esc_html( $list[ $slug ]['credit'] ),
		esc_url( 'https://commons.wikimedia.org/wiki/File:' . str_replace( ' ', '_', $list[ $slug ]['file'] ) )
	);
}

/** Fetch one image (keeps each request short). Admins only, fixed list. */
function btbd_fetch_image( $slug ) {
	$list = btbd_images();
	if ( empty( $list[ $slug ] ) ) {
		return 'unknown';
	}
	$dir = btbd_img_dir();
	if ( ! wp_mkdir_p( $dir ) ) {
		return 'no dir';
	}
	if ( function_exists( 'set_time_limit' ) ) {
		@set_time_limit( 120 ); // phpcs:ignore
	}
	$url = 'https://commons.wikimedia.org/wiki/Special:FilePath/' . rawurlencode( str_replace( ' ', '_', $list[ $slug ]['file'] ) ) . '?width=2000';
	$tmp = $dir . $slug . '-src';
	$res = wp_remote_get( $url, array(
		'timeout'     => 90,
		'stream'      => true,
		'filename'    => $tmp,
		'redirection' => 5,
		'user-agent'  => 'BetweenTheBillsExplore/2.0 (' . home_url( '/' ) . ')',
	) );
	if ( is_wp_error( $res ) || 200 !== (int) wp_remote_retrieve_response_code( $res ) ) {
		@unlink( $tmp ); // phpcs:ignore
		return 'download failed';
	}
	$files = array();
	$dims  = null;
	foreach ( array( 800, 1600 ) as $w ) {
		$ed = wp_get_image_editor( $tmp );
		if ( is_wp_error( $ed ) ) {
			return $ed->get_error_message();
		}
		$size = $ed->get_size();
		if ( $size['width'] > $w ) {
			$ed->resize( $w, null, false );
		}
		$ed->set_quality( 78 );
		$mime  = wp_image_editor_supports( array( 'mime_type' => 'image/webp' ) ) ? 'image/webp' : 'image/jpeg';
		$ext   = 'image/webp' === $mime ? 'webp' : 'jpg';
		$saved = $ed->save( $dir . $slug . '-' . $w . '.' . $ext, $mime );
		if ( is_wp_error( $saved ) ) {
			return $saved->get_error_message();
		}
		$files[ $saved['width'] ] = basename( $saved['path'] );
		$dims                      = array( 'w' => $saved['width'], 'h' => $saved['height'] );
	}
	@unlink( $tmp ); // phpcs:ignore
	$f   = $dir . 'manifest.json';
	$man = file_exists( $f ) ? json_decode( (string) file_get_contents( $f ), true ) : array();
	$man = is_array( $man ) ? $man : array();
	$man[ $slug ] = array( 'files' => $files, 'w' => $dims['w'], 'h' => $dims['h'] );
	file_put_contents( $f, wp_json_encode( $man ) );
	return 'ok';
}

add_action( 'wp_ajax_btbd_fetch_image', function () {
	if ( ! current_user_can( 'manage_options' ) ) {
		wp_send_json_error( 'forbidden', 403 );
	}
	check_ajax_referer( 'btbd_images', 'nonce' );
	$slug = sanitize_key( wp_unslash( $_POST['slug'] ?? '' ) );
	wp_send_json_success( array( 'slug' => $slug, 'result' => btbd_fetch_image( $slug ) ) );
} );

/* A small admin notice with a one-click fetch, shown only until every image is in place. */
add_action( 'admin_notices', function () {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	$missing = array_diff( array_keys( btbd_images() ), array_keys( btbd_img_manifest() ) );
	if ( ! $missing ) {
		return;
	}
	printf(
		'<div class="notice notice-info" id="btbd-img-notice" data-nonce="%s" data-slugs="%s"><p>BTB Explore Data: %d archival images still need to be fetched from Wikimedia Commons. <button type="button" class="button" id="btbd-img-fetch">Fetch images</button> <span id="btbd-img-status"></span></p></div>',
		esc_attr( wp_create_nonce( 'btbd_images' ) ),
		esc_attr( implode( ',', $missing ) ),
		count( $missing )
	);
	?>
	<script>
	(function () {
		var n = document.getElementById('btbd-img-notice'), b = document.getElementById('btbd-img-fetch'), s = document.getElementById('btbd-img-status');
		if (!n || !b) return;
		b.addEventListener('click', async function () {
			b.disabled = true;
			var slugs = n.dataset.slugs.split(','), done = 0;
			for (var i = 0; i < slugs.length; i++) {
				s.textContent = 'Fetching ' + slugs[i] + '…';
				var fd = new FormData();
				fd.append('action', 'btbd_fetch_image'); fd.append('slug', slugs[i]); fd.append('nonce', n.dataset.nonce);
				try { var r = await (await fetch(ajaxurl, { method: 'POST', body: fd })).json(); if (r.success && r.data.result === 'ok') done++; } catch (e) {}
			}
			s.textContent = done + ' of ' + slugs.length + ' fetched.';
		});
	})();
	</script>
	<?php
} );

/** Chapter opener: a pinned plate where an archival print opens as you scroll. */
function btbd_titlecard( $num, $title, $dek, $img, $id, $label = 'Chapter' ) {
	?>
	<div class="bx-tc bpq-tc" data-bx-tc>
		<div class="bx-tc-stick">
			<div class="bx-tc-img" aria-hidden="true"><?php echo btbd_img( $img, 'bx-riso bx-riso-multiply', '100vw' ); // phpcs:ignore ?></div>
			<div class="bx-tc-copy">
				<p class="bx-tc-num"><span><?php echo esc_html( $label ); ?></span><b><?php echo esc_html( $num ); ?></b></p>
				<h2 class="bx-tc-title" id="<?php echo esc_attr( $id ); ?>"><?php echo esc_html( $title ); ?></h2>
				<?php if ( $dek ) : ?><p class="bx-tc-dek"><?php echo esc_html( $dek ); ?></p><?php endif; ?>
			</div>
			<p class="bx-credit bx-tc-credit"><?php echo btbd_img_credit( $img ); // phpcs:ignore ?></p>
		</div>
	</div>
	<?php
}

/* Share images: the cover for 002, the census machine for Open Data. */
add_filter( 'rank_math/opengraph/facebook/image', function ( $img ) {
	if ( function_exists( 'btbd_is_002' ) && btbd_is_002() && btbd_img_src( 'senate-1850' ) ) {
		return btbd_img_src( 'senate-1850' );
	}
	if ( function_exists( 'btbd_is_data' ) && btbd_is_data() && btbd_img_src( 'census-1939' ) ) {
		return btbd_img_src( 'census-1939' );
	}
	return $img;
}, 99 );
add_filter( 'rank_math/opengraph/twitter/image', function ( $img ) {
	if ( function_exists( 'btbd_is_002' ) && btbd_is_002() && btbd_img_src( 'senate-1850' ) ) {
		return btbd_img_src( 'senate-1850' );
	}
	if ( function_exists( 'btbd_is_data' ) && btbd_is_data() && btbd_img_src( 'census-1939' ) ) {
		return btbd_img_src( 'census-1939' );
	}
	return $img;
}, 99 );
