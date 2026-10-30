<?php
/**
 * Reads from the Between the Bills data API. WordPress keeps only small cached
 * copies of aggregate results (transients), plus the last good copy so pages
 * still render if the API is unreachable. Row-level data never lands here:
 * browsers page through it directly from the API.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

function btbd_get( $args, $ttl = 6 * HOUR_IN_SECONDS ) {
	$args = (array) $args;
	ksort( $args );
	$key = 'btbd2_' . md5( wp_json_encode( $args ) );
	$hit = get_transient( $key );
	if ( false !== $hit ) {
		return $hit;
	}
	$res  = wp_remote_get( add_query_arg( array_map( 'rawurlencode', $args ), BTBD_API ), array( 'timeout' => 10 ) );
	$ok   = ! is_wp_error( $res ) && 200 === (int) wp_remote_retrieve_response_code( $res );
	$data = $ok ? json_decode( wp_remote_retrieve_body( $res ), true ) : null;
	if ( is_array( $data ) ) {
		set_transient( $key, $data, $ttl );
		update_option( $key . '_last', $data, false );
		$keys = (array) get_option( 'btbd_cache_keys', array() );
		if ( ! in_array( $key, $keys, true ) ) {
			$keys[] = $key;
			update_option( 'btbd_cache_keys', $keys, false );
		}
		return $data;
	}
	/* API down: serve the last good copy for a short while, then try again. */
	$last = get_option( $key . '_last', null );
	if ( $last ) {
		set_transient( $key, $last, 10 * MINUTE_IN_SECONDS );
	}
	return $last;
}

function btbd_flush_cache() {
	foreach ( (array) get_option( 'btbd_cache_keys', array() ) as $k ) {
		delete_transient( $k );
	}
}

function btbd_findings( $key ) {
	$f = btbd_get( array( 'route' => 'findings', 'key' => $key ) );
	return is_array( $f ) && isset( $f['body'] ) ? $f['body'] : null;
}

function btbd_overview() {
	return btbd_get( array( 'route' => 'overview' ), HOUR_IN_SECONDS );
}

function btbd_n( $n, $d = 0 ) {
	return number_format_i18n( (float) $n, $d );
}

/** Find one row in a list of assoc arrays. */
function btbd_pick( $rows, $field, $value ) {
	foreach ( (array) $rows as $r ) {
		if ( isset( $r[ $field ] ) && $r[ $field ] === $value ) {
			return $r;
		}
	}
	return null;
}

/** Ratio, one decimal, e.g. 5.6 */
function btbd_x( $a, $b ) {
	return $b > 0 ? number_format_i18n( $a / $b, 1 ) : '–';
}
