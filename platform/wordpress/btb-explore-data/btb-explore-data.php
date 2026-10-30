<?php
/**
 * Plugin Name: BTB Explore Data
 * Description: Explore investigation 002 (The Bipartisanship Question) and the Open Data tab: the hosted legislative record, its API, an in-browser SQL console over the full warehouse, and downloads. Reads the read-only Between the Bills data API; stores no legislative data in WordPress.
 * Version: 2.0.0
 * Author: Between the Bills
 * Requires PHP: 7.4
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'BTBD_VER', '2.0.0' );
define( 'BTBD_DIR', plugin_dir_path( __FILE__ ) );
define( 'BTBD_URL', plugin_dir_url( __FILE__ ) );
if ( ! defined( 'BTBD_API' ) ) {
	define( 'BTBD_API', 'https://nusmmbtxvphisicjoxlm.supabase.co/functions/v1/btb-open' );
}
define( 'BTBD_REPO', 'https://github.com/memereaper/btb-research-new' );
define( 'BTBD_DATA_SLUG', 'data' );

require_once BTBD_DIR . 'includes/images.php';
require_once BTBD_DIR . 'includes/data.php';

/* ---------- Investigation 002 inside Explore ---------- */

add_filter( 'btbx_collections', function ( $collections ) {
	if ( empty( $collections['congress']['items'] ) ) {
		return $collections;
	}
	foreach ( $collections['congress']['items'] as &$item ) {
		if ( 'the-bipartisanship-question' === $item['slug'] ) {
			$item['status']   = 'published';
			$item['kicker']   = 'Coalitions';
			$item['subtitle'] = 'What crossing the aisle buys a bill, gate by gate.';
			$item['dek']      = 'We followed 46,147 bills from the day they were introduced. Bills with a cosponsor from the other party got further at every step, most of all at the committee door.';
			$item['template'] = 'btbd-002';
		}
	}
	unset( $item );
	return $collections;
}, 20 );

function btbd_is_002() {
	return function_exists( 'btbx_route' ) && 'the-bipartisanship-question' === btbx_route();
}

/* ---------- The Open Data tab: /data/ ---------- */

add_action( 'init', function () {
	add_rewrite_rule( '^' . BTBD_DATA_SLUG . '/?$', 'index.php?btbd_data=1', 'top' );
	add_rewrite_rule( '^explore/open-record/?$', 'index.php?btbd_data=redirect', 'top' );
	if ( get_option( 'btbd_rewrite' ) !== BTBD_VER ) {
		flush_rewrite_rules( false );
		update_option( 'btbd_rewrite', BTBD_VER, false );
	}
} );
add_filter( 'query_vars', function ( $v ) {
	$v[] = 'btbd_data';
	return $v;
} );

function btbd_is_data() {
	return '1' === (string) get_query_var( 'btbd_data' );
}
function btbd_data_url( $frag = '' ) {
	return home_url( user_trailingslashit( BTBD_DATA_SLUG ) ) . $frag;
}

add_action( 'template_redirect', function () {
	if ( 'redirect' === get_query_var( 'btbd_data' ) ) {
		wp_safe_redirect( btbd_data_url( '#browse' ), 301 );
		exit;
	}
} );

add_action( 'parse_query', function ( $q ) {
	if ( $q->is_main_query() && $q->get( 'btbd_data' ) ) {
		$q->is_home       = false;
		$q->is_front_page = false;
		$q->is_404        = false;
	}
} );
add_filter( 'pre_handle_404', function ( $h, $q ) {
	return ( $q->is_main_query() && $q->get( 'btbd_data' ) ) ? true : $h;
}, 10, 2 );

/* Templates. btb-explore resolves its own routes at priority 99, so run after it. */
add_filter( 'template_include', function ( $t ) {
	if ( btbd_is_data() ) {
		status_header( 200 );
		return BTBD_DIR . 'templates/open-data.php';
	}
	if ( btbd_is_002() ) {
		return BTBD_DIR . 'templates/the-bipartisanship-question.php';
	}
	return $t;
}, 1000 );

add_filter( 'body_class', function ( $c ) {
	if ( btbd_is_data() ) {
		$c   = array_diff( $c, array( 'home', 'blog' ) );
		$c[] = 'btbd-data';
	}
	if ( btbd_is_002() ) {
		$c[] = 'btbd-002';
	}
	return $c;
} );

/* Titles and descriptions for /data/ (Explore handles its own routes). */
function btbd_data_meta() {
	return array(
		'title' => 'Open Data: the legislative record',
		'desc'  => 'Every bill introduced in Congress since 2013, 465,291 recorded actions, and a 1.77 million row warehouse. Search it, query it with SQL in your browser, call the free API, or download it.',
		'url'   => btbd_data_url(),
	);
}
add_filter( 'pre_get_document_title', function ( $t ) {
	return btbd_is_data() ? btbd_data_meta()['title'] . ' | ' . get_bloginfo( 'name' ) : $t;
}, 99 );
foreach ( array( 'rank_math/frontend/title', 'rank_math/opengraph/facebook/og_title', 'rank_math/opengraph/twitter/twitter_title' ) as $hook ) {
	add_filter( $hook, function ( $v ) {
		return btbd_is_data() ? btbd_data_meta()['title'] . ' | ' . get_bloginfo( 'name' ) : $v;
	}, 99 );
}
foreach ( array( 'rank_math/frontend/description', 'rank_math/opengraph/facebook/og_description', 'rank_math/opengraph/twitter/twitter_description' ) as $hook ) {
	add_filter( $hook, function ( $v ) {
		return btbd_is_data() ? btbd_data_meta()['desc'] : $v;
	}, 99 );
}
foreach ( array( 'rank_math/frontend/canonical', 'rank_math/opengraph/facebook/og_url' ) as $hook ) {
	add_filter( $hook, function ( $v ) {
		return btbd_is_data() ? btbd_data_meta()['url'] : $v;
	}, 99 );
}
add_filter( 'rank_math/frontend/robots', function ( $r ) {
	if ( btbd_is_data() ) {
		$r['index'] = 'index';
		$r['follow'] = 'follow';
	}
	return $r;
}, 99 );
add_action( 'wp_head', function () {
	if ( ! btbd_is_data() ) {
		return;
	}
	if ( ! defined( 'RANK_MATH_VERSION' ) ) {
		$m = btbd_data_meta();
		printf( "<meta name=\"description\" content=\"%s\">\n<link rel=\"canonical\" href=\"%s\">\n", esc_attr( $m['desc'] ), esc_url( $m['url'] ) );
	}
	/* Dataset structured data, so search engines can list the record as a dataset. */
	$ov = btbd_overview();
	$ld = array(
		'@context'              => 'https://schema.org',
		'@type'                 => 'Dataset',
		'name'                  => 'Between the Bills open legislative record',
		'description'           => 'Bills and joint resolutions introduced in the U.S. Congress (113th-119th), their recorded actions, cosponsorships, committee activity, subjects, summaries, text versions, CBO estimates and roll-call references, compiled from Library of Congress Bill Status records.',
		'url'                   => btbd_data_url(),
		'license'               => 'https://creativecommons.org/publicdomain/mark/1.0/',
		'isAccessibleForFree'   => true,
		'creator'               => array( '@type' => 'Organization', 'name' => 'Between the Bills', 'url' => home_url( '/' ) ),
		'temporalCoverage'      => '2013-01-03/..',
		'spatialCoverage'       => 'United States',
		'variableMeasured'      => array( 'bill', 'action', 'cosponsor', 'committee referral', 'subject', 'summary' ),
		'distribution'          => array(
			array( '@type' => 'DataDownload', 'encodingFormat' => 'application/vnd.apache.parquet', 'contentUrl' => BTBD_REPO . '/tree/main/datasets' ),
			array( '@type' => 'DataDownload', 'encodingFormat' => 'application/json', 'contentUrl' => BTBD_API . '?route=bills' ),
		),
	);
	if ( $ov && ! empty( $ov['warehouse']['rows'] ) ) {
		$ld['size'] = number_format( (int) $ov['warehouse']['rows'] ) . ' rows';
	}
	echo '<script type="application/ld+json">' . wp_json_encode( $ld, JSON_UNESCAPED_SLASHES ) . "</script>\n";
}, 3 );

/* Nav: Open Data as its own tab, right after Explore. */
add_filter( 'wp_nav_menu_objects', function ( $items, $args ) {
	if ( empty( $args->theme_location ) || 'primary' !== $args->theme_location ) {
		return $items;
	}
	foreach ( $items as $it ) {
		if ( false !== strpos( (string) $it->url, '/' . BTBD_DATA_SLUG . '/' ) ) {
			return $items;
		}
	}
	$items = array_values( $items );
	$after = null;
	foreach ( $items as $i => $it ) {
		if ( 0 === (int) $it->menu_item_parent && false !== strpos( (string) $it->url, '/explore' ) ) {
			$after = $i;
		}
	}
	$item                        = new stdClass();
	$item->ID                    = 990002;
	$item->db_id                 = 990002;
	$item->menu_item_parent      = 0;
	$item->object_id             = 0;
	$item->object                = 'custom';
	$item->type                  = 'custom';
	$item->type_label            = 'Custom Link';
	$item->title                 = 'Open Data';
	$item->url                   = btbd_data_url();
	$item->target                = '';
	$item->attr_title            = '';
	$item->description           = '';
	$item->xfn                   = '';
	$item->status                = 'publish';
	$item->classes               = array( 'menu-item', 'menu-item-type-custom', 'menu-item-btbd' );
	$item->current               = false;
	$item->current_item_ancestor = false;
	$item->current_item_parent   = false;
	$item->menu_order            = 0;
	if ( btbd_is_data() ) {
		$item->current   = true;
		$item->classes[] = 'current-menu-item';
		foreach ( $items as $it ) {
			$it->current = false;
			$it->classes = array_diff( (array) $it->classes, array( 'current-menu-item', 'current_page_item', 'current-menu-ancestor', 'current_page_parent' ) );
		}
	}
	if ( null === $after ) {
		$items[] = $item;
	} else {
		array_splice( $items, $after + 1, 0, array( $item ) );
	}
	foreach ( $items as $i => $it ) {
		$it->menu_order = $i + 1;
	}
	return $items;
}, 20, 2 );

/* ---------- Assets ---------- */

add_action( 'wp_enqueue_scripts', function () {
	$data = btbd_is_data();
	$inv  = btbd_is_002();
	if ( ! $data && ! $inv ) {
		return;
	}
	if ( $data && defined( 'BTBX_URL' ) ) {
		/* Same design system as Explore. */
		$v = defined( 'BTBX_VERSION' ) ? BTBX_VERSION : BTBD_VER;
		wp_enqueue_style( 'btbx-base', BTBX_URL . 'assets/explore-base.css', array( 'btb-style' ), $v );
		wp_enqueue_style( 'btbx', BTBX_URL . 'assets/explore.css', array( 'btbx-base' ), $v );
		wp_enqueue_script( 'btbx-core', BTBX_URL . 'assets/explore-core.js', array(), $v . '-perf4', true );
	}
	if ( $inv ) {
		/* 001's script and data are not needed on this page. */
		wp_dequeue_script( 'btbx-investigation' );
		wp_enqueue_style( 'btbd-002', BTBD_URL . 'assets/bpq.css', array( 'btbx' ), BTBD_VER );
		wp_enqueue_script( 'btbd-002', BTBD_URL . 'assets/bpq.js', array( 'btbx-core' ), BTBD_VER, true );
		wp_add_inline_script( 'btbd-002', 'window.BTBD=' . wp_json_encode( array(
			'api'     => BTBD_API,
			'data'    => btbd_data_url(),
			'base'    => btbd_findings( 'bipartisanship-116-118' ),
			'deep'    => btbd_findings( 'bipartisanship-deep' ),
		) ) . ';', 'before' );
	}
	if ( $data ) {
		wp_enqueue_style( 'btbd-data', BTBD_URL . 'assets/od.css', array( 'btbx' ), BTBD_VER );
		wp_enqueue_script( 'btbd-data', BTBD_URL . 'assets/od.js', array( 'btbx-core' ), BTBD_VER, true );
		$cat = btbd_findings( 'open-data-catalog' );
		wp_add_inline_script( 'btbd-data', 'window.BTBD=' . wp_json_encode( array(
			'api'     => BTBD_API,
			'catalog' => $cat,
			'duckdb'  => 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm',
		) ) . ';', 'before' );
	}
}, 40 );

/* /data/ is not an Explore route, so mark it scripted the same way Explore does. */
add_action( 'wp_head', function () {
	if ( btbd_is_data() ) {
		echo "<script>(function(d){d.classList.add('bx-js');setTimeout(function(){d.classList.add('bx-go')},2500)})(document.documentElement);</script>\n";
		echo '<link rel="preconnect" href="' . esc_url( preg_replace( '#^(https://[^/]+).*$#', '$1', BTBD_API ) ) . '" crossorigin>' . "\n";
	}
	if ( btbd_is_002() ) {
		echo '<link rel="preconnect" href="' . esc_url( preg_replace( '#^(https://[^/]+).*$#', '$1', BTBD_API ) ) . '" crossorigin>' . "\n";
	}
}, 1 );

/* Cached HTML can carry the inline findings; refresh it when the plugin version changes. */
add_action( 'admin_init', function () {
	if ( get_option( 'btbd_ver' ) !== BTBD_VER ) {
		btbd_flush_cache();
		update_option( 'btbd_ver', BTBD_VER, false );
	}
} );
