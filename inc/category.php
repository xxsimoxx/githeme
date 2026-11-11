<?php
/** Category archive queries and card labels. @package githeme */

defined( 'ABSPATH' ) || exit;

/** Limit only the public main category archive, leaving feeds and other lists alone. */
function githeme_category_page_size( $query ) {
	if ( is_admin() || ! $query->is_main_query() || ! $query->is_category() || $query->is_feed() ) {
		return;
	}
	$query->set( 'posts_per_page', 12 );
	$query->set( 'posts_per_archive_page', 12 );
}
add_action( 'pre_get_posts', 'githeme_category_page_size' );

/** Choose the deepest assigned category, constrained to the archive branch when supplied. */
function githeme_category_card_term( $post_id, $category_id = 0 ) {
	$selected = null;
	$current = null;
	$depth = 0;
	foreach ( get_the_category( $post_id ) as $term ) {
		if ( (int) $term->term_id === (int) $category_id ) {
			$current = $term;
		}
		$ancestors = array_map( 'intval', get_ancestors( $term->term_id, 'category', 'taxonomy' ) );
		$position = array_search( (int) $category_id, $ancestors, true );
		if ( $category_id > 0 && ( (int) $term->term_id === (int) $category_id || false === $position ) ) {
			continue;
		}
		$distance = $category_id > 0 ? $position + 1 : count( $ancestors ) + 1;
		if ( $distance > $depth || ( $distance === $depth && $selected && $term->term_id < $selected->term_id ) ) {
			$selected = $term;
			$depth = $distance;
		}
	}
	if ( $selected ) {
		return $selected;
	}
	$current = $current ?: ( $category_id > 0 ? get_term( $category_id, 'category' ) : null );
	return $current instanceof WP_Term ? $current : null;
}
