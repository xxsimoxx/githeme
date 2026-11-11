<?php
/** Isolated native API contract tests: php tests/page-title.php. No CMS/database writes. */
define( 'ABSPATH', __DIR__ );
$meta = array(); $type = 'page'; $revision = false; $autosave = false; $allowed = true; $writes = 0; $checks = 0;
function add_action( ...$args ) {}
function get_post_type( $id ) { return $GLOBALS['type']; }
function get_post_meta( $id, $key, $single ) { return $GLOBALS['meta'][ $id ] ?? ''; }
function update_post_meta( $id, $key, $value ) { $GLOBALS['meta'][ $id ] = $value; ++$GLOBALS['writes']; }
function delete_post_meta( $id, $key ) { unset( $GLOBALS['meta'][ $id ] ); ++$GLOBALS['writes']; }
function wp_is_post_revision( $id ) { return $GLOBALS['revision']; }
function wp_is_post_autosave( $id ) { return $GLOBALS['autosave']; }
function current_user_can( ...$args ) { return $GLOBALS['allowed']; }
function wp_unslash( $value ) { return stripslashes( $value ); }
function sanitize_text_field( $value ) { return trim( strip_tags( $value ) ); }
function wp_verify_nonce( $nonce, $action ) { return 'valid' === $nonce && 'githeme_page_title_10' === $action; }
require dirname( __DIR__ ) . '/inc/page-title.php';
function check( $ok, $label ) { if ( ! $ok ) { throw new RuntimeException( $label ); } ++$GLOBALS['checks']; }
check( ! githeme_page_title_hidden( 10 ), 'Absent meta leaves title visible' );
$_POST = array( 'githeme_page_title_nonce' => 'valid', 'githeme_hide_page_title' => '1' );
githeme_save_page_title( 10 );
check( githeme_page_title_hidden( 10 ) && '1' === $meta[10], 'Explicit checkbox saved as canonical string' );
foreach ( array( 'post', 'attachment' ) as $type ) {
 check( ! githeme_page_title_hidden( 10 ), 'Other post types ignore preference' );
 $before = $writes; githeme_save_page_title( 10 ); check( $before === $writes, 'Other post types cannot save preference' );
}
$type = 'page';
foreach ( array( 'revision', 'autosave' ) as $flag ) {
 $GLOBALS[$flag] = true; $before = $writes; githeme_save_page_title( 10 );
 check( $before === $writes, 'Revision/autosave cannot update parent or revision metadata' ); $GLOBALS[$flag] = false;
}
$allowed = false; $before = $writes; githeme_save_page_title( 10 ); check( $writes === $before, 'Permission required' ); $allowed = true;
foreach ( array( null, 'invalid', array( 'valid' ) ) as $nonce ) {
 $_POST['githeme_page_title_nonce'] = $nonce; $before = $writes; githeme_save_page_title( 10 ); check( $before === $writes, 'Nonce required and scalar' );
}
$_POST['githeme_page_title_nonce'] = 'valid';
foreach ( array( '0', 'true', '<script>', array( '1' ), null ) as $value ) {
 $_POST['githeme_hide_page_title'] = $value; githeme_save_page_title( 10 ); check( ! githeme_page_title_hidden( 10 ) && ! isset( $meta[10] ), 'Only explicit canonical 1 can hide title' );
}
$_POST = array( 'githeme_page_title_nonce' => 'valid' ); githeme_save_page_title( 10 );
check( ! githeme_page_title_hidden( 10 ), 'Unchecked checkbox deletes the preference' );
echo $checks . " page title checks passed.\n";
