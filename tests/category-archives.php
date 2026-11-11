<?php
/** Run via WP-CLI eval-file [json]. Runtime fixtures only; no database writes. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
$checks = 0;
$check = static function ( $ok, $label ) use ( &$checks ) {
	if ( ! $ok ) { throw new RuntimeException( $label ); }
	++$checks;
};
$globals = array();
foreach ( array( 'wp_query', 'wp_the_query', 'post', 'current_screen', 'id', 'authordata', 'currentday', 'currentmonth', 'page', 'pages', 'multipage', 'more', 'numpages' ) as $key ) {
	$globals[ $key ] = array( array_key_exists( $key, $GLOBALS ), $GLOBALS[ $key ] ?? null );
}
$original_size = get_option( 'posts_per_page' );
$original_mods = get_option( 'theme_mods_githeme' );
$terms = array();
$parents = array();
$term_filter = static function () use ( &$terms ) { return $terms; };
$ancestor_filter = static function ( $value, $id ) use ( &$parents ) { return $parents[ $id ] ?? $value; };
$no_image = static function () { return false; };
$empty_thumbnail = static function () { return ""; };
$fixture = array();
try {
	foreach ( array( 'category', 'tag', 'home', 'search', 'author', 'feed', 'secondary', 'admin' ) as $kind ) {
		$query = new WP_Query();
		$query->set( 'posts_per_page', 7 ); $query->set( 'posts_per_archive_page', 9 );
		$query->is_category = in_array( $kind, array( 'category', 'feed', 'secondary', 'admin' ), true );
		$query->is_feed = 'feed' === $kind;
		$GLOBALS['wp_the_query'] = 'secondary' === $kind ? new WP_Query() : $query;
		if ( 'admin' === $kind ) {
			$GLOBALS['current_screen'] = new class { public function in_admin() { return true; } };
		}
		githeme_category_page_size( $query );
		$check( $query->get( 'posts_per_page' ) === ( 'category' === $kind ? 12 : 7 ), 'Query scope and page size: ' . $kind );
		$check( $query->get( 'posts_per_archive_page' ) === ( 'category' === $kind ? 12 : 9 ), 'Archive override scope: ' . $kind );
		unset( $GLOBALS['current_screen'] );
	}
	add_filter( 'get_the_categories', $term_filter );
	add_filter( 'get_ancestors', $ancestor_filter, 10, 2 );
	$make = static function ( $id, $name ) { return new WP_Term( (object) array( 'term_id' => $id, 'name' => $name, 'slug' => 'fixture-' . $id, 'taxonomy' => 'category', 'parent' => 0, 'term_taxonomy_id' => $id ) ); };
	$current = $make( 900001, 'Current' ); $child = $make( 900002, 'Child' );
	$leaf = $make( 900003, '<unsafe>& Leaf' ); $other = $make( 900004, 'Unrelated' );
	$parents = array( 900001 => array(), 900002 => array( 900001 ), 900003 => array( 900002, 900001 ), 900004 => array( 900005 ) );
	$terms = array( $current, $other );
	$check( 900001 === githeme_category_card_term( 0, 900001 )->term_id, 'Current category is the fallback despite unrelated assignments' );
	$terms = array( $leaf, $current, $child );
	$check( 900003 === githeme_category_card_term( 0, 900001 )->term_id, 'Deepest assigned descendant selected' );
	$check( 900003 === githeme_category_card_term( 0, 900002 )->term_id, 'Nested category context respected' );
	$check( 900003 === githeme_category_card_term( 0, 900003 )->term_id, 'Leaf archive uses its own category when no descendant is assigned' );
	$parents[900004] = array( 900002, 900001 ); $terms = array( $other, $leaf );
	$check( 900003 === githeme_category_card_term( 0, 900001 )->term_id, 'Equal depths use stable term ID tie-break' );

	$ids = get_posts( array( 'post_type' => 'post', 'post_status' => 'publish', 'numberposts' => 1, 'fields' => 'ids', 'meta_key' => '_thumbnail_id', 'meta_compare' => '>', 'meta_value' => 0, 'meta_type' => 'NUMERIC' ) );
	$check( ! empty( $ids ), 'Existing featured-image post available for read-only tests' );
	$post = clone get_post( $ids[0] ); $post->post_excerpt = 'Manual excerpt retained verbatim.';
	$GLOBALS['post'] = $post; setup_postdata( $post );
	$terms = array( $current, $child, $leaf );
	ob_start(); get_template_part( 'template-parts/content', 'category-card', array( 'category_id' => 900001 ) ); $image_card = ob_get_clean();
	$check( str_contains( $image_card, 'category-card__media' ) && str_contains( $image_card, '<img' ), 'Native thumbnail rendered' );
	$check( str_contains( $image_card, '&lt;unsafe&gt;&amp; Leaf' ) && ! str_contains( $image_card, '<unsafe>' ), 'Term text escaped and deepest category displayed' );
	$check( str_contains( $image_card, 'Manual excerpt retained verbatim.' ), 'Manual excerpt preferred' );
	$check( 1 === substr_count( $image_card, '<a ' ) && str_contains( $image_card, 'aria-labelledby=' ), 'One named card link without nested category links' );
	$fixture['image'] = $image_card;
	add_filter( 'has_post_thumbnail', $no_image );
	ob_start(); get_template_part( 'template-parts/content', 'category-card', array( 'category_id' => 900001 ) ); $plain = ob_get_clean();
	$check( ! str_contains( $plain, '<img' ) && ! str_contains( $plain, 'category-card__media' ), 'No artificial placeholder or empty media area' );
	$check( str_contains( $plain, 'category-card__term-plain' ) && str_contains( $plain, 'Manual excerpt retained verbatim.' ), 'No-image card retains category and content' );
	$fixture['plain'] = $plain;
	remove_filter( 'has_post_thumbnail', $no_image );
	add_filter( 'post_thumbnail_html', $empty_thumbnail );
	ob_start(); get_template_part( 'template-parts/content', 'category-card', array( 'category_id' => 900001 ) ); $missing = ob_get_clean();
	$check( ! str_contains( $missing, 'category-card__media' ), 'Empty native thumbnail output does not reserve an image placeholder' );
	remove_filter( 'post_thumbnail_html', $empty_thumbnail );
	$post->post_excerpt = ''; $post->post_content = 'Automatic fallback editorial paragraph for testing.';
	$check( str_contains( get_the_excerpt( $post ), 'Automatic fallback editorial paragraph' ), 'Automatic excerpt fallback remains native' );
	$check( githeme_contrast_ratio( '#ffffff', '#404040' ) > 4.5, 'Neutral overlay worst-case text contrast exceeds AA threshold' );
	remove_filter( 'get_the_categories', $term_filter ); remove_filter( 'get_ancestors', $ancestor_filter, 10 );
	remove_filter( 'has_post_thumbnail', $no_image );

	$pages = array();
	for ( $number = 1; $number <= 2; ++$number ) {
		$query = new WP_Query(); $GLOBALS['wp_the_query'] = $query;
		$query->query( array( 'category_name' => 'news', 'paged' => $number, 'post_status' => 'publish' ) );
		$check( 12 === (int) $query->get( 'posts_per_page' ), 'Real main category query uses 12: page ' . $number );
		$check( count( $query->posts ) === min( 12, max( 0, $query->found_posts - ( $number - 1 ) * 12 ) ), 'Real page length: ' . $number );
		$pages[] = array( 'page' => $number, 'ids' => wp_list_pluck( $query->posts, 'ID' ), 'total' => (int) $query->found_posts, 'max_pages' => (int) $query->max_num_pages );
	}
	$check( ! array_intersect( $pages[0]['ids'], $pages[1]['ids'] ), 'Pagination pages have disjoint article IDs' );
	$fixture['css'] = file_get_contents( get_template_directory() . '/style.css' ) . githeme_font_faces_css() . githeme_custom_properties_css();
	$parent = get_category_by_slug( 'news' );
	$children = get_categories( array( 'parent' => $parent->term_id, 'number' => 1 ) );
	$fixture['child_url'] = $children ? get_category_link( $children[0] ) : null;
} finally {
	remove_filter( 'post_thumbnail_html', $empty_thumbnail );
	remove_filter( 'get_the_categories', $term_filter ); remove_filter( 'get_ancestors', $ancestor_filter, 10 ); remove_filter( 'has_post_thumbnail', $no_image );
	foreach ( $globals as $key => $value ) {
		if ( $value[0] ) { $GLOBALS[ $key ] = $value[1]; } else { unset( $GLOBALS[ $key ] ); }
	}
}
$check( $original_size === get_option( 'posts_per_page' ) && $original_mods === get_option( 'theme_mods_githeme' ), 'Persistent reading/theme options unchanged' );
if ( in_array( 'json', $args ?? array(), true ) ) {
	echo wp_json_encode( array( 'checks' => $checks, 'fixtures' => $fixture, 'pages' => $pages ) );
} else { WP_CLI::success( $checks . ' category archive checks passed. No database writes.' ); }
