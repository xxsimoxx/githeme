<?php
/** WP-CLI eval-file: render existing records with runtime-only metadata overrides. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
$checks = 0;
$check = static function ( $condition, $label ) use ( &$checks ) { if ( ! $condition ) { throw new RuntimeException( $label ); } ++$checks; };
$original_query = $GLOBALS['wp_query']; $original_main = $GLOBALS['wp_the_query']; $original_post = $GLOBALS['post'] ?? null;
$override = '';
$filter = static function ( $value, $id, $key, $single ) use ( &$override ) { return '_githeme_hide_page_title' === $key ? ( $single ? $override : array( $override ) ) : $value; };
add_filter( 'get_post_metadata', $filter, 10, 4 );
try {
 foreach ( array( array( 'page_id' => (int) get_option( 'page_on_front' ) ), array( 'page_id' => 224 ), array( 'p' => 286 ) ) as $query_args ) {
  $query = new WP_Query( $query_args ); $GLOBALS['wp_query'] = $query; $GLOBALS['wp_the_query'] = $query;
  $check( $query->have_posts(), 'Existing test content available' ); $query->the_post();
  $saved_title = get_the_title(); $document_title = wp_get_document_title();
  foreach ( array( '', '0', '1' ) as $override ) {
   ob_start(); get_template_part( 'template-parts/content', 'singular' ); $html = ob_get_clean();
   $has_heading = (bool) preg_match( '/<header class="entry-header content-column">\s*<h1>/', $html );
   $check( $has_heading === ( ! is_page() || '1' !== $override ), 'Only explicit page setting removes template heading' );
   $check( str_contains( $html, 'class="entry-content"' ), 'Content wrapper retained' );
   $check( get_the_title() === $saved_title && wp_get_document_title() === $document_title, 'Post and document titles unchanged' );
  }
  ob_start(); githeme_page_title_control( get_post() ); $control = ob_get_clean();
  $check( str_contains( $control, 'for="githeme-hide-page-title"' ) && str_contains( $control, 'id="githeme-hide-page-title"' ) && str_contains( $control, 'githeme_page_title_nonce' ), 'Native checkbox label and nonce rendered' );
 }
} finally {
 remove_filter( 'get_post_metadata', $filter, 10 );
 $GLOBALS['wp_query'] = $original_query; $GLOBALS['wp_the_query'] = $original_main; $GLOBALS['post'] = $original_post;
 if ( $original_post ) { setup_postdata( $original_post ); }
}
WP_CLI::success( $checks . ' page title integration checks passed. No database writes.' );
