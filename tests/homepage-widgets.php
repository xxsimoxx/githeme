<?php
/**
 * Run with WP-CLI eval-file. Only query objects and filters in memory change.
 *
 * @package githeme
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

// phpcs:disable WordPress.WP.GlobalVariablesOverride.Prohibited -- Query fixtures are restored in finally.
$githeme_checks           = 0;
$githeme_check            = static function ( $ok, $message ) use ( &$githeme_checks ) {
	if ( ! $ok ) {
		throw new RuntimeException( esc_html( $message ) );
	}
	++$githeme_checks;
};
$githeme_original_query   = $GLOBALS['wp_query'];
$githeme_original_widgets = $GLOBALS['wp_registered_widgets'];
$githeme_original_options = array();
foreach ( array( 'show_on_front', 'page_on_front', 'page_for_posts', 'sidebars_widgets', 'theme_mods_githeme' ) as $name ) {
	$githeme_original_options[ $name ] = get_option( $name );
}
$githeme_sidebars        = array();
$githeme_front_mode      = 'page';
$githeme_sidebar_filter  = static function () use ( &$githeme_sidebars ) {
	return $githeme_sidebars;
};
$githeme_front_filter    = static function () use ( &$githeme_front_mode ) {
	return $githeme_front_mode;
};
$githeme_front_id_filter = static function () {
	return 123456;
};
add_filter( 'sidebars_widgets', $githeme_sidebar_filter );
add_filter( 'pre_option_show_on_front', $githeme_front_filter );
add_filter( 'pre_option_page_on_front', $githeme_front_id_filter );

$githeme_render = static function ( $area ) {
	ob_start();
	get_template_part( 'template-parts/homepage-widgets', null, array( 'area' => $area ) );
	return ob_get_clean();
};

try {
	foreach ( array( 'homepage-hero', 'homepage-content', 'footer-experimental' ) as $githeme_sidebar_id ) {
		$githeme_check( isset( $GLOBALS['wp_registered_sidebars'][ $githeme_sidebar_id ] ), 'Missing sidebar: ' . $githeme_sidebar_id );
	}
	$githeme_check( ! file_exists( get_template_directory() . '/front-page.php' ), 'Do not override assigned page templates' );
	wp_register_sidebar_widget(
		'githeme-homepage-probe',
		'Homepage test widget',
		static function ( $sidebar ) {
			echo $sidebar['before_widget']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Test native widget HTML.
			echo $sidebar['before_title'] . 'Widget test title' . $sidebar['after_title']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Test native widget HTML.
			echo '<p>githeme-widget-test-marker</p>';
			echo $sidebar['after_widget']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Test native widget HTML.
		}
	);
	wp_register_sidebar_widget( 'githeme-homepage-empty', 'Empty test widget', '__return_null' );
	$query                    = new WP_Query();
	$query->is_page           = true;
	$query->queried_object    = new WP_Post(
		(object) array(
			'ID'         => 123456,
			'post_type'  => 'page',
			'post_title' => 'Test page',
		)
	);
	$query->queried_object_id = 123456;
	$GLOBALS['wp_query']      = $query;
	$githeme_check( is_front_page() && ! is_home(), 'Static-home query fixture failed' );

	foreach ( array( array(), array( 'homepage-hero' ), array( 'homepage-content' ), array( 'homepage-hero', 'homepage-content' ) ) as $areas ) {
		$githeme_sidebars = array_fill_keys( $areas, array( 'githeme-homepage-probe' ) );
		foreach ( array( 'homepage-hero', 'homepage-content' ) as $area ) {
			$html   = $githeme_render( $area );
			$active = in_array( $area, $areas, true );
			$githeme_check( $active ? str_contains( $html, 'id="' . $area . '"' ) : '' === trim( $html ), 'Incorrect optional area output: ' . $area );
			if ( $active ) {
				$githeme_check( 1 === substr_count( $html, 'githeme-widget-test-marker' ) && str_contains( $html, '<h2 class="widget-title">' ), 'Widget rendered twice or incorrect title level' );
				$githeme_check( ! str_contains( $html, '<main' ) && ! str_contains( $html, '<h1' ), 'Widget area must not introduce a main or h1' );
			}
		}
	}
	$githeme_sidebars = array( 'homepage-hero' => array( 'githeme-homepage-empty' ) );
	$githeme_check( '' === trim( $githeme_render( 'homepage-hero' ) ), 'Filtered/empty widget must not leave an area wrapper' );
	$githeme_check( '' === trim( $githeme_render( 'footer-experimental' ) ), 'Homepage part accepted a non-homepage area' );
	$githeme_sidebars = array_fill_keys( array( 'homepage-hero', 'homepage-content' ), array( 'githeme-homepage-probe' ) );
	foreach ( array( 'latest-posts', 'posts-page', 'internal-page', 'single-post' ) as $context ) {
		$query->is_home           = in_array( $context, array( 'latest-posts', 'posts-page' ), true );
		$query->is_page           = 'internal-page' === $context;
		$query->is_single         = 'single-post' === $context;
		$query->queried_object    = new WP_Post(
			(object) array(
				'ID'         => 123457,
				'post_type'  => 'page',
				'post_title' => 'Other page',
			)
		);
		$query->queried_object_id = 123457;
		$githeme_front_mode       = 'latest-posts' === $context ? 'posts' : 'page';
		foreach ( array( 'homepage-hero', 'homepage-content' ) as $area ) {
			$githeme_check( '' === trim( $githeme_render( $area ) ), 'Homepage widgets leaked into ' . $context );
		}
	}
} finally {
	remove_filter( 'sidebars_widgets', $githeme_sidebar_filter );
	remove_filter( 'pre_option_show_on_front', $githeme_front_filter );
	remove_filter( 'pre_option_page_on_front', $githeme_front_id_filter );
	$GLOBALS['wp_query']              = $githeme_original_query;
	$GLOBALS['wp_registered_widgets'] = $githeme_original_widgets;
}
foreach ( $githeme_original_options as $name => $value ) {
	$githeme_check( get_option( $name ) === $value, 'Stored option changed: ' . $name );
}
WP_CLI::success( $githeme_checks . ' homepage widget assertions passed. No options or content saved.' );
