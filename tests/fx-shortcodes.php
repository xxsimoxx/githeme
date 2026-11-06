<?php
/** Run via WP-CLI eval-file; only stylesheet registries and filters in memory change. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
$count = 0;
$check = static function ( $ok, $message ) use ( &$count ) {
	if ( ! $ok ) { throw new RuntimeException( $message ); }
	++$count;
};
$original_styles = $GLOBALS['wp_styles'] ?? null;
$original_mods = get_option( 'theme_mods_githeme' );
$original_server_name = $_SERVER['SERVER_NAME'] ?? null;
$_SERVER['SERVER_NAME'] = wp_parse_url( home_url(), PHP_URL_HOST );
$filter = static function () use ( $original_mods ) {
	return array_merge( (array) $original_mods, array( 'githeme_color_secondary' => '#3F91A9' ) );
};
try {
	$GLOBALS['wp_styles'] = new WP_Styles();
	githeme_enqueue_fx_shortcodes_style();
	$check( ! wp_style_is( 'githeme-fx-shortcodes', 'enqueued' ), 'No integration without plugin stylesheet' );
	wp_register_style( 'fx-shortcodes', '/test-only.css' );
	githeme_enqueue_fx_shortcodes_style();
	$check( ! wp_style_is( 'githeme-fx-shortcodes', 'enqueued' ), 'Registered but inactive stylesheet is not sufficient' );
	wp_enqueue_style( 'fx-shortcodes' );
	githeme_enqueue_assets();
	githeme_enqueue_fx_shortcodes_style();
	$check( wp_style_is( 'githeme-fx-shortcodes', 'enqueued' ), 'Optional integration enqueued' );
	$style = wp_styles()->registered['githeme-fx-shortcodes'];
	$check( array( 'githeme-style', 'fx-shortcodes' ) === $style->deps, 'Explicit cascade ordering' );
	$check( wp_get_theme( get_template() )->get( 'Version' ) === $style->ver, 'Theme version cache key' );
	add_filter( 'pre_option_theme_mods_githeme', $filter );
	$css = githeme_custom_properties_css();
	$check( false !== strpos( $css, '--color-button-hover-text:#000000;' ), 'Secondary hover chooses black on the test palette' );
	$check( githeme_contrast_ratio( '#3F91A9', githeme_button_text_color( '#3F91A9' ) ) >= 4.5, 'Accessible secondary hover text' );
	foreach ( array( '#000000', '#ffffff', '#777777', '#14569a', '#3F91A9' ) as $color ) {
		$check( githeme_contrast_ratio( $color, githeme_button_text_color( $color ) ) >= 4.5, 'Automatic hover contrast: ' . $color );
	}
} finally {
	remove_filter( 'pre_option_theme_mods_githeme', $filter );
	$GLOBALS['wp_styles'] = $original_styles;
	if ( null === $original_server_name ) { unset( $_SERVER['SERVER_NAME'] ); }
	else { $_SERVER['SERVER_NAME'] = $original_server_name; }
}
$check( $original_mods === get_option( 'theme_mods_githeme' ), 'Settings unchanged' );
WP_CLI::success( $count . ' FX integration assertions passed. No options saved.' );
