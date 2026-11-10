<?php
/** Run via WP-CLI eval-file [json]; sidebar fixtures exist only in memory. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
$checks = 0;
$check = static function ( $ok, $label ) use ( &$checks ) {
	if ( ! $ok ) { throw new RuntimeException( $label ); }
	++$checks;
};
$original_widgets = $GLOBALS['wp_registered_widgets'];
$original_query = $GLOBALS['wp_query'];
$original_options = array();
foreach ( array( 'sidebars_widgets', 'theme_mods_githeme', 'blogname' ) as $name ) {
	$original_options[ $name ] = get_option( $name );
}
$sidebars = array();
$filter = static function () use ( &$sidebars ) { return $sidebars; };
$calls = 0;
$hook = static function () use ( &$calls ) { ++$calls; };
$fixtures = array();
$server_name = $_SERVER['SERVER_NAME'] ?? null;
$_SERVER['SERVER_NAME'] = wp_parse_url( home_url(), PHP_URL_HOST );
add_filter( 'sidebars_widgets', $filter );
add_action( 'wp_footer', $hook );
try {
	$GLOBALS['wp_query'] = new WP_Query();
	wp_register_sidebar_widget( 'githeme-footer-empty', 'Empty test widget', static function () {} );
	wp_register_sidebar_widget( 'githeme-footer-space', 'Whitespace test widget', static function () { echo " \n\t"; } );
	wp_register_sidebar_widget( 'githeme-footer-content', 'Footer test widget', static function ( $args ) {
		echo $args['before_widget'];
		echo $args['before_title'] . 'Footer fixture' . $args['after_title'];
		echo '<p>Native widget content <a href="#main-content">Back to content</a></p>';
		echo $args['after_widget'];
	} );
	foreach ( array( 'none' => array(), 'empty' => array( 'githeme-footer-empty' ), 'space' => array( 'githeme-footer-space' ), 'content' => array( 'githeme-footer-content' ) ) as $label => $ids ) {
		$sidebars = array( 'footer-experimental' => $ids );
		$before = $calls;
		ob_start(); get_template_part( 'footer' ); $html = ob_get_clean();
		$check( 1 === substr_count( $html, '</main>' ), 'Main closes once: ' . $label );
		$check( $calls === $before + 1, 'wp_footer still called once: ' . $label );
		$check( ! str_contains( $html, 'site-credits' ), 'No automatic site title: ' . $label );
		$check( ( 'content' === $label ) === str_contains( $html, '<footer class="site-footer">' ), 'Footer only for actual output: ' . $label );
		$check( ( 'content' === $label ) === str_contains( $html, 'class="footer-widgets"' ), 'No empty widget grid: ' . $label );
		if ( 'content' === $label ) {
			$check( str_contains( $html, 'Native widget content' ) && str_contains( $html, '<a href="#main-content">' ), 'Native widget markup retained' );
			preg_match( '~<footer class="site-footer">.*?</footer>~s', $html, $match );
			$fixtures['footer'] = $match[0];
		}
	}
	$check( isset( $GLOBALS['wp_registered_sidebars']['footer-experimental'] ), 'Existing footer sidebar ID retained' );
	$fixtures['css'] = file_get_contents( get_template_directory() . '/style.css' );
} finally {
	remove_filter( 'sidebars_widgets', $filter );
	remove_action( 'wp_footer', $hook );
	$GLOBALS['wp_registered_widgets'] = $original_widgets;
	$GLOBALS['wp_query'] = $original_query;
	if ( null === $server_name ) { unset( $_SERVER['SERVER_NAME'] ); }
	else { $_SERVER['SERVER_NAME'] = $server_name; }
}
foreach ( $original_options as $name => $value ) {
	$check( get_option( $name ) === $value, 'Original option unchanged: ' . $name );
}
if ( in_array( 'json', $args ?? array(), true ) ) {
	echo wp_json_encode( array( 'assertions' => $checks, 'fixtures' => $fixtures ) );
} else {
	WP_CLI::success( $checks . ' footer checks passed. No content or options saved.' );
}
