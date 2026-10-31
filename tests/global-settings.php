<?php
/**
 * Run: wp eval-file src/wp-content/themes/githeme/tests/global-settings.php
 * Uses the loaded ClassicPress APIs, with in-memory overrides and no DB writes.
 *
 * @package githeme
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}

$githeme_test_count = 0;
$githeme_check = static function ( $condition, $message ) use ( &$githeme_test_count ) {
	if ( ! $condition ) {
		throw new RuntimeException( esc_html( $message ) );
	}
	++$githeme_test_count;
};

wp_set_current_user( 1 );
require_once ABSPATH . WPINC . '/class-wp-customize-manager.php';
$manager = new WP_Customize_Manager( array( 'theme' => get_stylesheet() ) );
$GLOBALS['wp_customize'] = $manager;
do_action( 'customize_register', $manager );

$option_name = 'theme_mods_' . get_stylesheet();
$original    = get_option( $option_name );
$overrides   = array();
$override    = static function () use ( $original, &$overrides ) {
	return array_merge( (array) $original, $overrides );
};
add_filter( 'pre_option_' . $option_name, $override );

try {
	foreach ( githeme_defaults() as $id => $default ) {
		$setting = $manager->get_setting( $id );
		$control = $manager->get_control( $id );
		$githeme_check( $setting && $control && 'theme_mod' === $setting->type && 'refresh' === $setting->transport, 'Missing standard setting/control: ' . $id );
		$githeme_check( 1 === count( $control->settings ), 'A control has multiple settings: ' . $id );
		$githeme_check( ! is_wp_error( $setting->validate( $default ) ), 'Invalid default: ' . $id );
	}
	foreach ( array( 'colors', 'githeme_typography', 'githeme_layout', 'githeme_header' ) as $id ) {
		$githeme_check( (bool) $manager->get_section( $id ), 'Missing section: ' . $id );
	}
	$githeme_check( 21.0 === githeme_contrast_ratio( '#000', '#fff' ), 'Black/white contrast must be 21.' );
	$githeme_check( 1.0 === githeme_contrast_ratio( '#fff', '#ffffff' ), 'Equal colors must have contrast 1.' );
	$githeme_check( null === githeme_contrast_ratio( 'invalid', '#fff' ), 'Invalid color accepted by contrast calculation.' );
	$githeme_check( '#000000' === githeme_button_text_color( '#fff' ) && '#ffffff' === githeme_button_text_color( '#000' ), 'Incorrect button foreground.' );
	$githeme_check( array() === githeme_contrast_warnings( array( 'text' => '#202833', 'link' => '#14569a', 'background' => '#fff' ) ), 'Default contrast should not warn.' );
	$githeme_check( 2 === count( githeme_contrast_warnings( array( 'text' => '#fff', 'link' => '#fff', 'background' => '#fff' ) ) ), 'Low contrast should produce informational warnings.' );
	$color = $manager->get_setting( 'githeme_color_text' );
	$githeme_check( ! is_wp_error( $color->validate( '#fff' ) ), 'Low contrast must not block colors.' );
	$githeme_check( is_wp_error( $color->validate( 'red;}</style><script>' ) ), 'Invalid color syntax accepted.' );
	$githeme_check( null === $color->sanitize( array( '#fff' ) ), 'Array accepted as color.' );
	$githeme_check( $color->default === $color->sanitize( '' ), 'Clearing a color should restore its default.' );

	foreach ( array( 'githeme_font_size', 'githeme_logo_height' ) as $id ) {
		$limits  = githeme_number_limits( $id );
		$setting = $manager->get_setting( $id );
		$githeme_check( ! is_wp_error( $setting->validate( $limits[0] ) ) && ! is_wp_error( $setting->validate( $limits[1] ) ), 'Numeric endpoints rejected: ' . $id );
		foreach ( array( $limits[0] - $limits[2], $limits[1] + $limits[2], $limits[0] + $limits[2] / 2, 'abc', array(), INF, NAN ) as $invalid ) {
			$githeme_check( is_wp_error( $setting->validate( $invalid ) ), 'Invalid numeric value accepted: ' . $id );
		}
	}
	foreach ( array( array( 36, 48, 60 ), array( 60, 90, 100 ), array( 60, 60, 60 ) ) as $widths ) {
		$pending = array_combine( array( 'githeme_width_content', 'githeme_width_wide', 'githeme_width_layout' ), $widths );
		foreach ( $pending as $id => $value ) {
			$manager->set_post_value( $id, $value );
		}
		foreach ( $pending as $id => $value ) {
			$githeme_check( ! is_wp_error( $manager->get_setting( $id )->validate( $value ) ), 'Coherent simultaneous widths rejected.' );
		}
	}
	$manager->set_post_value( 'githeme_width_content', 60 );
	$manager->set_post_value( 'githeme_width_wide', 48 );
	$manager->set_post_value( 'githeme_width_layout', 60 );
	foreach ( array( 'githeme_width_content' => 60, 'githeme_width_wide' => 48, 'githeme_width_layout' => 60 ) as $id => $value ) {
		$githeme_check( is_wp_error( $manager->get_setting( $id )->validate( $value ) ), 'Inconsistent pending widths accepted.' );
	}
	foreach ( array( 'githeme_width_content', 'githeme_width_wide', 'githeme_width_layout' ) as $id ) {
		$limits = githeme_number_limits( $id );
		foreach ( array( $limits[0] - 1, $limits[1] + 1, $limits[0] + 0.5, 'invalid', array() ) as $value ) {
			$githeme_check( is_wp_error( $manager->get_setting( $id )->validate( $value ) ), 'Invalid width accepted: ' . $id );
		}
	}

	foreach ( array( 'githeme_font_family', 'githeme_heading_scale', 'githeme_header_layout' ) as $id ) {
		$setting = $manager->get_setting( $id );
		foreach ( githeme_setting_choices( $id ) as $choice ) {
			$githeme_check( ! is_wp_error( $setting->validate( $choice ) ), 'Permitted choice rejected: ' . $id );
		}
		$githeme_check( is_wp_error( $setting->validate( 'arbitrary-css' ) ) && null === $setting->sanitize( array() ), 'Unlisted choice accepted: ' . $id );
	}

	$font_report = array();
	foreach ( githeme_setting_choices( 'githeme_font_family' ) as $family ) {
		$overrides = array( 'githeme_font_family' => $family );
		$css = githeme_font_faces_css();
		preg_match_all( '/src:url\("([^"]+)"\)/', $css, $matches );
		$expected = 'system' === $family ? 0 : 2;
		$githeme_check( $expected === count( $matches[1] ), 'Unexpected font-face count: ' . $family );
		foreach ( $matches[1] as $url ) {
			$githeme_check( str_contains( $url, get_template_directory_uri() . '/assets/fonts/' . $family . '/' ), 'Unselected or remote font included.' );
			$path = get_template_directory() . '/assets/fonts/' . $family . '/' . rawurldecode( basename( $url ) );
			$githeme_check( is_file( $path ) && 'wOF2' === file_get_contents( $path, false, null, 0, 4 ), 'Missing/invalid WOFF2 asset.' );
		}
		$editor = apply_filters( 'tiny_mce_before_init', array( 'content_style' => '.existing{color:inherit;}' ), 'content' );
		$githeme_check( str_contains( $editor['content_style'], '.existing{color:inherit;}' ) && str_contains( $editor['content_style'], githeme_custom_properties_css() ), 'Editor CSS was not preserved/aligned.' );
		$font_report[ $family ] = $matches[1];
	}
	foreach ( array( 'inline', 'stacked' ) as $layout ) {
		$overrides = array( 'githeme_header_layout' => $layout );
		$githeme_check( in_array( 'githeme-header-' . $layout, githeme_header_body_class( array() ), true ), 'Header layout class missing.' );
	}
	$overrides = array( 'githeme_width_content' => 60, 'githeme_width_wide' => 48, 'githeme_width_layout' => 60 );
	$githeme_check( array( 'content' => 48, 'wide' => 48, 'layout' => 60 ) == githeme_rendered_widths(), 'Defensive width ordering failed.' );
	$githeme_check( '' !== githeme_saved_width_warning() && 60 === get_theme_mod( 'githeme_width_content' ), 'Inconsistent widths were silently changed or not reported.' );
	$overrides = array( 'githeme_color_text' => array(), 'githeme_font_size' => INF, 'githeme_font_family' => 'bad";}html{color:red}', 'githeme_header_layout' => 'bad"', 'githeme_width_content' => -1, 'githeme_width_wide' => 1000, 'githeme_width_layout' => 'NaN' );
	$githeme_check( ! str_contains( githeme_custom_properties_css(), 'NaN' ) && '' === githeme_font_faces_css(), 'Invalid stored values escaped defensive rendering.' );
	$githeme_check( 36 == githeme_rendered_widths()['content'] && 76 == githeme_rendered_widths()['wide'], 'Out-of-range widths were not bounded.' );
	$overrides = array();
} finally {
	remove_filter( 'pre_option_' . $option_name, $override );
}
$githeme_check( $original === get_option( $option_name ), 'Stored theme mods changed during tests.' );
WP_CLI::success( $githeme_test_count . ' global settings assertions passed. No settings were saved.' );
WP_CLI::log( wp_json_encode( $font_report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
