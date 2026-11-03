<?php
/**
 * Global presentation values and CSS. No database writes or Customizer internals.
 *
 * @package githeme
 */

defined( 'ABSPATH' ) || exit;

/** Return the shared defaults, without a control/schema configuration layer. */
function githeme_defaults() {
	return array(
		'githeme_color_primary'   => '#14569a',
		'githeme_color_secondary' => '#4b5563',
		'githeme_color_text'      => '#202833',
		'githeme_color_background' => '#ffffff',
		'githeme_color_link'      => '#14569a',
		'githeme_font_family'     => 'system',
		'githeme_font_size'       => 1,
		'githeme_heading_scale'   => '1.25',
		'githeme_width_content'   => 46,
		'githeme_width_wide'      => 68,
		'githeme_width_layout'    => 76,
		'githeme_logo_height'     => 5,
		'githeme_header_layout'   => 'inline',
	);
}

/** Return the permitted values for the three select controls. */
function githeme_setting_choices( $id ) {
	switch ( $id ) {
		case 'githeme_font_family':
			return array( 'system', 'source-sans-3', 'source-serif-4', 'atkinson-hyperlegible-next' );
		case 'githeme_heading_scale':
			return array( '1.125', '1.2', '1.25', '1.333' );
		case 'githeme_header_layout':
			return array( 'inline', 'stacked' );
	}
	return array();
}

/** Return a safe choice, including when a value was written outside Customizer. */
function githeme_get_choice( $id ) {
	$defaults = githeme_defaults();
	$value    = get_theme_mod( $id, $defaults[ $id ] );
	return is_scalar( $value ) && in_array( (string) $value, githeme_setting_choices( $id ), true ) ? (string) $value : $defaults[ $id ];
}

/** Numeric bounds: minimum, maximum, step (all dimensions in rem). */
function githeme_number_limits( $id ) {
	switch ( $id ) {
		case 'githeme_font_size':
			return array( 1, 1.375, 0.0625 );
		case 'githeme_width_content':
			return array( 36, 60, 1 );
		case 'githeme_width_wide':
			return array( 48, 90, 1 );
		case 'githeme_width_layout':
			return array( 60, 100, 1 );
		case 'githeme_logo_height':
			return array( 2, 8, 0.25 );
	}
	return array();
}

/** Reject non-finite numbers; clamp only the rendered value, never stored data. */
function githeme_get_number( $id ) {
	$defaults = githeme_defaults();
	$value    = get_theme_mod( $id, $defaults[ $id ] );
	$limits   = githeme_number_limits( $id );
	if ( ! is_numeric( $value ) || ! is_finite( (float) $value ) ) {
		return (float) $defaults[ $id ];
	}
	return max( $limits[0], min( $limits[1], (float) $value ) );
}

/** Return validated hex palette values with a deterministic fallback. */
function githeme_palette() {
	$defaults = githeme_defaults();
	$colors   = array();
	foreach ( array( 'primary', 'secondary', 'text', 'background', 'link' ) as $name ) {
		$id              = 'githeme_color_' . $name;
		$value           = get_theme_mod( $id, $defaults[ $id ] );
		$colors[ $name ] = is_string( $value ) ? sanitize_hex_color( $value ) : null;
		$colors[ $name ] = null === githeme_hex_channels( $colors[ $name ] ) ? $defaults[ $id ] : $colors[ $name ];
	}
	return $colors;
}

/**
 * Single source for the sRGB/WCAG calculation constants, also sent to JS.
 *
 * @return array Calculation constants and normal-size text threshold.
 */
function githeme_contrast_rules() {
	return array(
		'channelMax'        => 255,
		'breakpoint'        => 0.04045,
		'divisor'           => 12.92,
		'offset'            => 0.055,
		'scale'             => 1.055,
		'gamma'             => 2.4,
		'weights'           => array( 0.2126, 0.7152, 0.0722 ),
		'flare'             => 0.05,
		'normalTextMinimum' => 4.5,
	);
}

/** Convert valid #RGB/#RRGGBB to RGB channels; return null for invalid input. */
function githeme_hex_channels( $color ) {
	if ( ! is_string( $color ) || ! preg_match( '/^#(?:[a-f0-9]{3}|[a-f0-9]{6})\z/i', $color ) ) {
		return null;
	}
	$hex = substr( $color, 1 );
	if ( 3 === strlen( $hex ) ) {
		$hex = $hex[0] . $hex[0] . $hex[1] . $hex[1] . $hex[2] . $hex[2];
	}
	return array( hexdec( substr( $hex, 0, 2 ) ), hexdec( substr( $hex, 2, 2 ) ), hexdec( substr( $hex, 4, 2 ) ) );
}

/** WCAG relative luminance, independent of interface, storage and hooks. */
function githeme_color_luminance( $color ) {
	$channels = githeme_hex_channels( $color );
	if ( null === $channels ) {
		return null;
	}
	$rules  = githeme_contrast_rules();
	$linear = array_map(
		static function ( $channel ) use ( $rules ) {
			$channel /= $rules['channelMax'];
			return $channel <= $rules['breakpoint'] ? $channel / $rules['divisor'] : pow( ( $channel + $rules['offset'] ) / $rules['scale'], $rules['gamma'] );
		},
		$channels
	);
	return $rules['weights'][0] * $linear[0] + $rules['weights'][1] * $linear[1] + $rules['weights'][2] * $linear[2];
}

/** WCAG contrast ratio, or null for invalid input. Never blocks saving. */
function githeme_contrast_ratio( $first, $second ) {
	$a     = githeme_color_luminance( $first );
	$b     = githeme_color_luminance( $second );
	$rules = githeme_contrast_rules();
	return null === $a || null === $b ? null : ( max( $a, $b ) + $rules['flare'] ) / ( min( $a, $b ) + $rules['flare'] );
}

/** Choose the better contrasting foreground for a solid button background. */
function githeme_button_text_color( $background ) {
	if ( null === githeme_hex_channels( $background ) ) {
		return null;
	}
	return githeme_contrast_ratio( $background, '#000000' ) >= githeme_contrast_ratio( $background, '#ffffff' ) ? '#000000' : '#ffffff';
}

/**
 * Normal-size text only: does not assess component borders, icons or logos.
 *
 * @param array $colors Palette colors; missing/invalid pairs are not assessed.
 * @return array Ratios, thresholds and states keyed by usage.
 */
function githeme_contrast_report( $colors ) {
	$rules  = githeme_contrast_rules();
	$button = githeme_button_text_color( $colors['primary'] ?? null );
	$pairs  = array(
		'text'   => array( $colors['text'] ?? null, $colors['background'] ?? null ),
		'link'   => array( $colors['link'] ?? null, $colors['background'] ?? null ),
		'button' => array( $button, $colors['primary'] ?? null ),
	);
	$report = array();
	foreach ( $pairs as $key => $pair ) {
		$ratio          = githeme_contrast_ratio( $pair[0], $pair[1] );
		$report[ $key ] = array(
			'ratio'      => $ratio,
			'minimum'    => $rules['normalTextMinimum'],
			'status'     => null === $ratio ? 'invalid' : ( $ratio >= $rules['normalTextMinimum'] ? 'pass' : 'fail' ),
			'foreground' => $pair[0],
			'background' => $pair[1],
		);
	}
	return $report;
}
/** Blend validated colors for derived theme surfaces and borders. */
function githeme_mix_colors( $first, $second, $weight ) {
	$a = githeme_hex_channels( $first );
	$b = githeme_hex_channels( $second );
	return sprintf( '#%02x%02x%02x', (int) round( $a[0] * $weight + $b[0] * ( 1 - $weight ) ), (int) round( $a[1] * $weight + $b[1] * ( 1 - $weight ) ), (int) round( $a[2] * $weight + $b[2] * ( 1 - $weight ) ) );
}

/** Informational messages, kept separate from validation errors. */
function githeme_contrast_warnings( $colors = null ) {
	$colors   = $colors ?? githeme_palette();
	$warnings = array();
	$report   = githeme_contrast_report( $colors );
	if ( 'fail' === $report['text']['status'] ) {
		/* translators: 1: contrast ratio, 2: minimum ratio for normal-size text. */
		$warnings[] = sprintf( __( 'Text/background contrast is %1$s:1, below the %2$s:1 target. Saving is allowed.', 'githeme' ), number_format_i18n( $report['text']['ratio'], 2 ), number_format_i18n( $report['text']['minimum'], 1 ) );
	}
	if ( 'fail' === $report['link']['status'] ) {
		/* translators: 1: contrast ratio, 2: minimum ratio for normal-size text. */
		$warnings[] = sprintf( __( 'Link/background contrast is %1$s:1, below the %2$s:1 target. Saving is allowed.', 'githeme' ), number_format_i18n( $report['link']['ratio'], 2 ), number_format_i18n( $report['link']['minimum'], 1 ) );
	}
	return $warnings;
}

/** Enforce width ordering only in rendering. Stored values remain untouched. */
function githeme_rendered_widths() {
	$layout  = githeme_get_number( 'githeme_width_layout' );
	$wide    = min( githeme_get_number( 'githeme_width_wide' ), $layout );
	$content = min( githeme_get_number( 'githeme_width_content' ), $wide );
	return array( 'content' => $content, 'wide' => $wide, 'layout' => $layout );
}

/** Resolve a font stack from the fixed set; CSS never contains a user string. */
function githeme_font_stack() {
	switch ( githeme_get_choice( 'githeme_font_family' ) ) {
		case 'source-sans-3':
			return '"Source Sans 3", system-ui, sans-serif';
		case 'source-serif-4':
			return '"Source Serif 4", Georgia, serif';
		case 'atkinson-hyperlegible-next':
			return '"Atkinson Hyperlegible Next", system-ui, sans-serif';
	}
	return 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
}

/** Only declare the selected family's two faces; the browser fetches on use. */
function githeme_font_faces_css() {
	$family = githeme_get_choice( 'githeme_font_family' );
	switch ( $family ) {
		case 'source-sans-3':
			$name = 'Source Sans 3';
			$files = array( 'SourceSans3VF-Upright.ttf.woff2', 'SourceSans3VF-Italic.ttf.woff2' );
			$weight = '200 900';
			break;
		case 'source-serif-4':
			$name = 'Source Serif 4';
			$files = array( 'SourceSerif4Variable-Roman.ttf.woff2', 'SourceSerif4Variable-Italic.ttf.woff2' );
			$weight = '200 900';
			break;
		case 'atkinson-hyperlegible-next':
			$name = 'Atkinson Hyperlegible Next';
			$files = array( 'AtkinsonHyperlegibleNext[wght].woff2', 'AtkinsonHyperlegibleNext-Italic[wght].woff2' );
			$weight = '200 800';
			break;
		default:
			return '';
	}
	$css = '';
	foreach ( $files as $index => $file ) {
		$url = esc_url_raw( get_template_directory_uri() . '/assets/fonts/' . $family . '/' . rawurlencode( $file ) );
		$css .= '@font-face{font-family:"' . $name . '";font-style:' . ( $index ? 'italic' : 'normal' ) . ';font-weight:' . $weight . ';font-display:swap;src:url("' . $url . '") format("woff2");}';
	}
	return $css;
}

/** Generate CSS exclusively from validated values and fixed property names. */
function githeme_custom_properties_css() {
	$colors = githeme_palette();
	$widths = githeme_rendered_widths();
	$muted  = githeme_mix_colors( $colors['text'], $colors['background'], 0.85 );
	if ( githeme_contrast_ratio( $muted, $colors['background'] ) < githeme_contrast_rules()['normalTextMinimum'] ) {
		$muted = $colors['text'];
	}
	$properties = array(
		'color-primary'    => $colors['primary'],
		'color-secondary'  => $colors['secondary'],
		'color-text'       => $colors['text'],
		'color-background' => $colors['background'],
		'color-link'       => $colors['link'],
		'color-button-text' => githeme_button_text_color( $colors['primary'] ),
		'color-surface'    => githeme_mix_colors( $colors['secondary'], $colors['background'], 0.06 ),
		'color-muted'      => $muted,
		'color-border'     => githeme_mix_colors( $colors['text'], $colors['background'], 0.6 ),
		'font-body'        => githeme_font_stack(),
		'font-size-base'   => githeme_get_number( 'githeme_font_size' ) . 'rem',
		'heading-scale'    => githeme_get_choice( 'githeme_heading_scale' ),
		'width-content'    => $widths['content'] . 'rem',
		'width-wide'       => $widths['wide'] . 'rem',
		'width-layout'     => $widths['layout'] . 'rem',
		'logo-max-height'  => githeme_get_number( 'githeme_logo_height' ) . 'rem',
	);
	for ( $level = 1; $level <= 6; $level++ ) {
		$properties[ 'heading-' . $level ] = (string) round( pow( (float) $properties['heading-scale'], 6 - $level ), 6 );
	}
	$css = ':root{';
	foreach ( $properties as $property => $value ) {
		$css .= '--' . $property . ':' . $value . ';';
	}
	return $css . '}';
}

/** Add one fixed layout class; navigation markup remains shared. */
function githeme_header_body_class( $classes ) {
	$classes[] = 'githeme-header-' . githeme_get_choice( 'githeme_header_layout' );
	return $classes;
}
add_filter( 'body_class', 'githeme_header_body_class' );

/** TinyMCE's public content_style setting supports CSS inside its iframe. */
function githeme_editor_settings( $settings ) {
    $css = githeme_font_faces_css() . githeme_custom_properties_css();

    // Avoid double quotes inside the TinyMCE initialization string.
    $css = str_replace( '"', "'", $css );

    $settings['content_style'] = ( $settings['content_style'] ?? '' ) . $css;

    return $settings;
}
add_filter( 'tiny_mce_before_init', 'githeme_editor_settings' );
add_filter( 'teeny_mce_before_init', 'githeme_editor_settings' );
