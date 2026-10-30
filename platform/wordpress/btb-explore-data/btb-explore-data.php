<?php
/**
 * Plugin Name: BTB Explore Data
 * Description: Publishes Explore investigation 002 (The Bipartisanship Question) and The Open Record, a searchable database of every bill in the 116th-119th Congress. Reads the read-only Between the Bills data API.
 * Version: 1.0.0
 * Author: Between the Bills
 * Requires PHP: 7.4
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'BTBD_VER', '1.0.0' );
define( 'BTBD_DIR', plugin_dir_path( __FILE__ ) );
define( 'BTBD_URL', plugin_dir_url( __FILE__ ) );
if ( ! defined( 'BTBD_API' ) ) {
	define( 'BTBD_API', 'https://nusmmbtxvphisicjoxlm.supabase.co/functions/v1/btb-open' );
}
const BTBD_ROUTES = array( 'the-bipartisanship-question', 'open-record' );

/* Publish 002 and add The Open Record to the Congress collection. */
add_filter( 'btbx_collections', function ( $collections ) {
	if ( empty( $collections['congress']['items'] ) ) {
		return $collections;
	}
	foreach ( $collections['congress']['items'] as &$item ) {
		if ( 'the-bipartisanship-question' === $item['slug'] ) {
			$item['status']   = 'published';
			$item['subtitle'] = 'Three Congresses, 45,863 bills, one question.';
			$item['dek']      = 'Bills that crossed the aisle on day one became law far more often. We followed every bill introduced from 2019 to 2024 to see how much, for whom, and in which policy areas.';
			$item['template'] = 'btbd';
		}
	}
	unset( $item );
	$collections['congress']['items'][] = array(
		'number'   => 'DB',
		'slug'     => 'open-record',
		'status'   => 'published',
		'kicker'   => 'Open data',
		'title'    => 'The Open Record',
		'subtitle' => 'Search every bill introduced since 2019.',
		'dek'      => 'Every bill in the 116th through 119th Congress, with its sponsor, its coalition and how far it got. Search it, filter it, download it, or query it from your own code.',
		'template' => 'btbd',
		'image'    => 'dome-1861',
	);
	return $collections;
}, 20 );

function btbd_route() {
	$r = function_exists( 'btbx_route' ) ? btbx_route() : '';
	return in_array( $r, BTBD_ROUTES, true ) ? $r : '';
}

add_filter( 'template_include', function ( $template ) {
	$r = btbd_route();
	return $r ? BTBD_DIR . 'templates/' . $r . '.php' : $template;
}, 1000 ); // after btb-explore's own template_include

add_action( 'wp_enqueue_scripts', function () {
	$r = btbd_route();
	if ( ! $r ) {
		return;
	}
	// The 001 investigation script loads that investigation's large data file; not needed here.
	wp_dequeue_script( 'btbx-investigation' );
	wp_enqueue_style( 'btbd', BTBD_URL . 'assets/btbd.css', array( 'btbx' ), BTBD_VER );
	wp_enqueue_script( 'btbd', BTBD_URL . 'assets/btbd.js', array(), BTBD_VER, true );
	wp_add_inline_script( 'btbd', 'window.BTBD=' . wp_json_encode( array(
		'api'      => BTBD_API,
		'route'    => $r,
		'findings' => 'the-bipartisanship-question' === $r ? btbd_findings() : null,
		'record'   => btbd_url( 'open-record' ),
	) ) . ';', 'before' );
}, 20 );

function btbd_url( $slug ) {
	return function_exists( 'btbx_explore_url' ) ? btbx_explore_url( $slug ) : home_url( '/explore/' . $slug . '/' );
}

/** Fetch a fixed API route server-side, cached; keeps the last good copy if the API is down. */
function btbd_get( $route, $ttl = 6 * HOUR_IN_SECONDS ) {
	$key = 'btbd_' . md5( $route );
	$hit = get_transient( $key );
	if ( false !== $hit ) {
		return $hit;
	}
	$res = wp_remote_get( add_query_arg( 'route', $route, BTBD_API ), array( 'timeout' => 8 ) );
	$ok  = ! is_wp_error( $res ) && 200 === wp_remote_retrieve_response_code( $res );
	$data = $ok ? json_decode( wp_remote_retrieve_body( $res ), true ) : null;
	if ( is_array( $data ) ) {
		set_transient( $key, $data, $ttl );
		update_option( $key . '_last', $data, false );
		return $data;
	}
	return get_option( $key . '_last', null );
}

function btbd_findings() {
	$f = btbd_get( 'findings' );
	return is_array( $f ) && isset( $f['body'] ) ? $f['body'] : null;
}

/** Rate for one coalition from a findings table. */
function btbd_row( $rows, $coalition ) {
	foreach ( (array) $rows as $r ) {
		if ( $r['coalition'] === $coalition ) {
			return $r;
		}
	}
	return null;
}

function btbd_n( $n, $d = 0 ) {
	return number_format_i18n( (float) $n, $d );
}
