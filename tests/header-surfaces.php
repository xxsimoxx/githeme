<?php
/** Focused in-memory checks; no settings, site text or imported content saved. */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
$count = 0;
$check = static function ( $ok, $message ) use ( &$count ) {
	if ( ! $ok ) { throw new RuntimeException( $message ); }
	++$count;
};
$original = get_option( 'theme_mods_githeme' );
$original_name = get_option( 'blogname' );
$original_description = get_option( 'blogdescription' );
$overrides = array();
$omit_visibility = true;
$server_name = $_SERVER['SERVER_NAME'] ?? null;
$_SERVER['SERVER_NAME'] = wp_parse_url( home_url(), PHP_URL_HOST );
$description = 'Test motto <sample> & original';
$mods_filter = static function () use ( $original, &$overrides, &$omit_visibility ) { $mods = (array) $original; if ( $omit_visibility ) { unset( $mods['githeme_show_title'], $mods['githeme_show_tagline'] ); } return array_merge( $mods, $overrides ); };
$description_filter = static function () use ( &$description ) { return $description; };
add_filter( 'pre_option_theme_mods_githeme', $mods_filter );
add_filter( 'pre_option_blogdescription', $description_filter );
try {
	wp_set_current_user( 1 );
	require_once ABSPATH . WPINC . '/class-wp-customize-manager.php';
	$manager = new WP_Customize_Manager();
	do_action( 'customize_register', $manager );
	$check( false === githeme_initial_tagline_visibility( array(), 'Existing text', true ) && true === githeme_initial_tagline_visibility( array( 'githeme_font_family' => 'system' ), 'Existing text', true ), 'Fresh activation hidden, existing configuration preserved' );
	$check( true === githeme_initial_tagline_visibility( array(), 'Existing text' ) && false === githeme_initial_tagline_visibility( array(), '' ), 'Active legacy tagline preserved without changing its text' );
	$check( false === githeme_defaults()['githeme_show_tagline'] && true === githeme_defaults()['githeme_show_title'], 'Fresh defaults' );
	$check( true === $manager->get_setting( 'githeme_show_tagline' )->default, 'Existing nonempty tagline keeps its visible compatibility default' );
	foreach ( array( 'header_background', 'footer_background' ) as $key ) {
		$id = 'githeme_color_' . $key;
		$setting = $manager->get_setting( $id );
		$check( '#ffffff' === $setting->default && 'theme_mod' === $setting->type && 'refresh' === $setting->transport, 'White standard color defaults' );
		$check( 'colors' === $manager->get_control( $id )->section, 'Color section' );
		$check( is_wp_error( $setting->validate( 'red;display:none' ) ) && null === $setting->sanitize( array() ), 'Reject unsafe color' );
		$overrides[ $id ] = '#112233';
		$check( str_contains( githeme_custom_properties_css(), '--color-' . str_replace( '_', '-', $key ) . ':#112233;' ), 'Independent CSS variable' );
		$overrides[ $id ] = '<invalid>';
		$check( '#ffffff' === githeme_palette()[ $key ], 'Defensive white fallback' );
		unset( $overrides[ $id ] );
	}
	foreach ( array( 'githeme_show_title', 'githeme_show_tagline' ) as $id ) {
		$setting = $manager->get_setting( $id );
		$control = $manager->get_control( $id );
		$check( 'title_tagline' === $control->section && 'checkbox' === $control->type && count( $control->settings ) === 1, 'Native identity checkbox binding' );
		foreach ( array( false, true, '', '1', '0', 0, 1 ) as $value ) {
			$check( ! is_wp_error( $setting->validate( $value ) ) && is_bool( $setting->sanitize( $value ) ), 'Allowed checkbox serialization' );
		}
		foreach ( array( array(), 'false', 'unexpected', 2 ) as $value ) {
			$check( is_wp_error( $setting->validate( $value ) ) && null === $setting->sanitize( $value ), 'Invalid checkbox rejected' );
		}
		$overrides[ $id ] = false;
		ob_start(); $control->render_content(); $markup = ob_get_clean();
		$check( str_contains( $markup, 'class="customize-inside-control-row"' ) && str_contains( $markup, '<label for="_customize-input-' . $id . '"' ), 'Native checkbox layout wrapper and explicit label' );
		$check( str_contains( $markup, 'value="1"' ) && str_contains( $markup, 'data-customize-setting-link="' . $id . '"' ) && ! str_contains( $markup, 'checked=' ), 'Unchecked control still submits 1 when checked' );
		unset( $overrides[ $id ] );
	}
	$logo = (int) get_theme_mod( 'custom_logo' );
	$check( $logo > 0 && wp_attachment_is_image( $logo ), 'Existing local logo required for focused combinations' );
	$cases = array();
	foreach ( array( false, true ) as $has_logo ) {
		foreach ( array( false, true ) as $title ) {
			foreach ( array( false, true ) as $tagline ) {
				$overrides = array( 'custom_logo' => $has_logo ? $logo : 0, 'githeme_show_title' => $title, 'githeme_show_tagline' => $tagline );
				ob_start(); get_template_part( 'header' ); $html = ob_get_clean();
				preg_match( '~<div class="site-branding">(.*?)</div>~s', $html, $match );
				$branding = $match[1] ?? '';
				$check( str_contains( $branding, 'class="site-title"' ) === ( ! $has_logo || $title ), 'Title/logo combination' );
				$check( str_contains( $branding, 'class="site-description"' ) === $tagline, 'Independent tagline' );
				$check( ! str_contains( $branding, '<sample>' ), 'Tagline escaping' );
				if ( $has_logo ) { $check( preg_match( '/alt="[^"]+"/', $branding ), 'Logo homepage link has a name' ); }
				else { $check( str_contains( $branding, esc_html( $original_name ) ), 'Title fallback keeps homepage link named' ); }
				$cases[] = array( 'logo' => $has_logo, 'title' => $title, 'tagline' => $tagline );
			}
		}
	}
	$description = '';
	$overrides = array( 'githeme_show_tagline' => true );
	ob_start(); get_template_part( 'header' ); $html = ob_get_clean();
	$check( ! str_contains( $html, 'class="site-description"' ), 'No empty tagline wrapper' );
	$overrides = array();
	$check( false === githeme_identity_default( 'githeme_show_tagline' ), 'Empty/new tagline default hidden' );
	$report = githeme_contrast_report( array( 'text' => '#111111', 'link' => '#111111', 'primary' => '#111111', 'background' => '#ffffff', 'header_background' => '#111111', 'footer_background' => '#ffffff' ) );
	$check( 'fail' === $report['header_text']['status'] && 'fail' === $report['header_link']['status'] && 'pass' === $report['footer_text']['status'] && 'pass' === $report['footer_link']['status'], 'Independent surface contrast' );
	$minimum = githeme_contrast_rules()['normalTextMinimum'];
	foreach ( array(
		array( '#202833', '#ffffff', '#ffffff' ),
		array( '#202833', '#999999', '#ffffff' ), // Audit regression: old motto was only 3.24:1.
		array( '#202833', '#E3F2F6', '#ffffff' ),
		array( '#ffffff', '#202833', '#ffffff' ),
		array( '#767676', '#ffffff', '#ffffff' ), // Text barely passes; muted text does not.
		array( '#000000', '#757575', '#ffffff' ),
		array( '#999999', '#999999', '#ffffff' ), // An insufficient user choice must still fail.
		array( '#202833', '#ffffff', '#000000' ), // Header derivation is independent of the body.
	) as list( $text, $header, $background ) ) {
		$overrides = array( 'githeme_color_text' => $text, 'githeme_color_link' => $text, 'githeme_color_primary' => '#14569a', 'githeme_color_header_background' => $header, 'githeme_color_background' => $background, 'githeme_color_footer_background' => '#ffffff' );
		$css = githeme_custom_properties_css();
		$check( 1 === preg_match( '/--color-header-muted:(#[a-f0-9]{6});/i', $css, $match ), 'Header motto CSS variable emitted' );
		$motto = $match[1];
		$candidate = githeme_mix_colors( $text, $header, 0.85 );
		$expected = githeme_contrast_ratio( $candidate, $header ) >= $minimum ? $candidate : $text;
		$check( $expected === $motto, 'Preserve muted header appearance only where contrast permits' );
		$report = githeme_contrast_report( githeme_palette() );
		$motto_passes = githeme_contrast_ratio( $motto, $header ) >= $minimum;
		$check( ( 'pass' === $report['header_text']['status'] ) === $motto_passes, 'Header checker pass agrees with actual motto contrast' );
		$body_muted = githeme_mix_colors( $text, $background, 0.85 );
		if ( githeme_contrast_ratio( $body_muted, $background ) < $minimum ) { $body_muted = $text; }
		$check( str_contains( $css, '--color-muted:' . $body_muted . ';' ), 'Existing body muted color unchanged' );
		if ( '#999999' === $header && '#202833' === $text ) {
			$check( '#202833' === $motto && $motto_passes, 'Reported medium-gray header keeps motto above 4.5:1' );
			$check( ! in_array( 'fail', array_column( $report, 'status' ), true ), 'All seven checks can pass without hiding the reported motto failure' );
		}
	}
	$check( (bool) preg_match( '/\.site-description\s*\{[^}]*color:\s*var\(--color-header-muted\)/', file_get_contents( get_template_directory() . '/style.css' ) ), 'Motto consumes the header-specific color' );
} finally {
	remove_filter( 'pre_option_theme_mods_githeme', $mods_filter );
	remove_filter( 'pre_option_blogdescription', $description_filter );
	if ( null === $server_name ) { unset( $_SERVER['SERVER_NAME'] ); } else { $_SERVER['SERVER_NAME'] = $server_name; }
}
$check( $original === get_option( 'theme_mods_githeme' ) && $original_name === get_option( 'blogname' ) && $original_description === get_option( 'blogdescription' ), 'Exact persistence unchanged after memory tests' );
WP_CLI::success( $count . ' focused header/surface checks passed; eight combinations; no settings or site text saved.' );
