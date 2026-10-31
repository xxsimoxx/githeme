<?php
/**
 * Standard controls for global presentation. Content stays in the editor.
 *
 * @package githeme
 */

defined( 'ABSPATH' ) || exit;

/** Accept hex colors, or reset an empty input to its explicit default. */
function githeme_sanitize_color( $value, $setting ) {
	if ( '' === $value ) {
		return $setting->default;
	}
	return is_string( $value ) ? sanitize_hex_color( $value ) : null;
}

/** Only syntax errors block colors. Low contrast is informational. */
function githeme_validate_color( $validity, $value ) {
	if ( '' !== $value && ( ! is_string( $value ) || ! sanitize_hex_color( $value ) ) ) {
		$validity->add( 'invalid_color', __( 'Enter a hexadecimal color such as #14569a.', 'githeme' ) );
	}
	return $validity;
}

/** Sanitize fixed select values without accepting arbitrary CSS or font names. */
function githeme_sanitize_choice( $value, $setting ) {
	return is_scalar( $value ) && in_array( (string) $value, githeme_setting_choices( $setting->id ), true ) ? (string) $value : null;
}

/** Validate select values separately so the standard control reports errors. */
function githeme_validate_choice( $validity, $value, $setting ) {
	if ( null === githeme_sanitize_choice( $value, $setting ) ) {
		$validity->add( 'invalid_choice', __( 'Choose one of the available options.', 'githeme' ) );
	}
	return $validity;
}

/** Preserve valid numbers; do not silently clamp values before saving. */
function githeme_sanitize_number( $value ) {
	return is_numeric( $value ) && is_finite( (float) $value ) ? (float) $value : null;
}

/** Validate numeric range and increment on the server as well as in the input. */
function githeme_validate_number( $validity, $value, $setting ) {
	$limits = githeme_number_limits( $setting->id );
	$number = githeme_sanitize_number( $value );
	if ( null === $number || $number < $limits[0] || $number > $limits[1] ) {
		/* translators: 1: minimum value, 2: maximum value, in rem. */
		$validity->add( 'invalid_number', sprintf( __( 'Enter a number from %1$s to %2$s rem.', 'githeme' ), $limits[0], $limits[1] ) );
	} elseif ( abs( ( $number - $limits[0] ) / $limits[2] - round( ( $number - $limits[0] ) / $limits[2] ) ) > 0.000001 ) {
		/* translators: %s: allowed increment in rem. */
		$validity->add( 'invalid_step', sprintf( __( 'Use increments of %s rem.', 'githeme' ), $limits[2] ) );
	}
	return $validity;
}

/** Validate all three widths against the pending changeset, without recursion. */
function githeme_validate_width( $validity, $value, $setting ) {
	$validity = githeme_validate_number( $validity, $value, $setting );
	if ( $validity->has_errors() ) {
		return $validity;
	}
	$defaults = githeme_defaults();
	$pending  = $setting->manager->unsanitized_post_values();
	$pending[ $setting->id ] = $value;
	$widths = array();
	foreach ( array( 'githeme_width_content', 'githeme_width_wide', 'githeme_width_layout' ) as $id ) {
		$raw = array_key_exists( $id, $pending ) ? $pending[ $id ] : get_theme_mod( $id, $defaults[ $id ] );
		$widths[ $id ] = githeme_sanitize_number( $raw );
		if ( null === $widths[ $id ] ) {
			return $validity; // The corresponding setting reports its own numeric error.
		}
	}
	if ( $widths['githeme_width_content'] > $widths['githeme_width_wide'] || $widths['githeme_width_wide'] > $widths['githeme_width_layout'] ) {
		$validity->add( 'invalid_width_order', __( 'Content width must not exceed wide width, and wide width must not exceed maximum layout width.', 'githeme' ) );
	}
	return $validity;
}

/** Detect invalid saved widths for an informational notice, without changing them. */
function githeme_saved_width_warning() {
	$defaults = githeme_defaults();
	$values   = array();
	foreach ( array( 'githeme_width_content', 'githeme_width_wide', 'githeme_width_layout' ) as $id ) {
		$raw    = get_theme_mod( $id, $defaults[ $id ] );
		$number = githeme_sanitize_number( $raw );
		$limits = githeme_number_limits( $id );
		if ( null === $number || $number < $limits[0] || $number > $limits[1] || floor( $number ) !== $number ) {
			return __( 'Saved widths are invalid. Safe limits are applied only when rendering; saved values have not been changed.', 'githeme' );
		}
		$values[] = $number;
	}
	return $values[0] > $values[1] || $values[1] > $values[2] ? __( 'Saved widths are inconsistent. Safe limits are applied only when rendering; saved values have not been changed.', 'githeme' ) : '';
}

/** Register explicit controls using only public PHP APIs and refresh transport. */
function githeme_customize_register( $manager ) {
	$defaults = githeme_defaults();
	$color_description = __( 'These colors apply to theme elements. Contrast advice is informational and does not prevent saving. Advice is recalculated when this screen is loaded.', 'githeme' );
	foreach ( githeme_contrast_warnings() as $warning ) {
		$color_description .= '<p>' . esc_html( $warning ) . '</p>';
	}
	$manager->add_section( 'colors', array( 'title' => __( 'Colors', 'githeme' ), 'description' => $color_description, 'priority' => 40 ) );
	foreach ( array(
		'primary'    => __( 'Primary color', 'githeme' ),
		'secondary'  => __( 'Secondary color', 'githeme' ),
		'text'       => __( 'Text color', 'githeme' ),
		'background' => __( 'Background color', 'githeme' ),
		'link'       => __( 'Link color', 'githeme' ),
	) as $name => $label ) {
		$id = 'githeme_color_' . $name;
		$manager->add_setting( $id, array( 'type' => 'theme_mod', 'default' => $defaults[ $id ], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_color', 'validate_callback' => 'githeme_validate_color' ) );
		$manager->add_control( new WP_Customize_Color_Control( $manager, $id, array( 'label' => $label, 'section' => 'colors' ) ) );
	}

	$manager->add_section( 'githeme_typography', array( 'title' => __( 'Typography', 'githeme' ), 'priority' => 41 ) );
	$manager->add_setting( 'githeme_font_family', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_font_family'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_choice', 'validate_callback' => 'githeme_validate_choice' ) );
	$manager->add_control( 'githeme_font_family', array(
		'type' => 'select', 'section' => 'githeme_typography', 'label' => __( 'Font family', 'githeme' ),
		'choices' => array( 'system' => __( 'System font stack', 'githeme' ), 'source-sans-3' => 'Source Sans 3', 'source-serif-4' => 'Source Serif 4', 'atkinson-hyperlegible-next' => 'Atkinson Hyperlegible Next' ),
		'description' => __( 'Included fonts are served locally. Only the selected family is used.', 'githeme' ),
	) );
	$manager->add_setting( 'githeme_font_size', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_font_size'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_number', 'validate_callback' => 'githeme_validate_number' ) );
	$manager->add_control( 'githeme_font_size', array( 'type' => 'number', 'section' => 'githeme_typography', 'label' => __( 'Base text size (rem)', 'githeme' ), 'description' => __( '1 rem follows the browser default, usually 16 px. Browser zoom and user font preferences remain available.', 'githeme' ), 'input_attrs' => array( 'min' => 1, 'max' => 1.375, 'step' => 0.0625 ) ) );
	$manager->add_setting( 'githeme_heading_scale', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_heading_scale'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_choice', 'validate_callback' => 'githeme_validate_choice' ) );
	$manager->add_control( 'githeme_heading_scale', array( 'type' => 'select', 'section' => 'githeme_typography', 'label' => __( 'Heading scale', 'githeme' ), 'choices' => array( '1.125' => '1.125', '1.2' => '1.2', '1.25' => '1.25', '1.333' => '1.333' ) ) );

	$width_description = __( 'Dimensions are maximums in rem; all containers shrink to the available space. Required order: content ≤ wide ≤ layout.', 'githeme' );
	if ( githeme_saved_width_warning() ) {
		$width_description .= '<p>' . esc_html( githeme_saved_width_warning() ) . '</p>';
	}
	$manager->add_section( 'githeme_layout', array( 'title' => __( 'Widths and layout', 'githeme' ), 'description' => $width_description, 'priority' => 42 ) );
	$manager->add_setting( 'githeme_width_content', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_width_content'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_number', 'validate_callback' => 'githeme_validate_width' ) );
	$manager->add_control( 'githeme_width_content', array( 'type' => 'number', 'section' => 'githeme_layout', 'label' => __( 'Content width (rem)', 'githeme' ), 'input_attrs' => array( 'min' => 36, 'max' => 60, 'step' => 1 ) ) );
	$manager->add_setting( 'githeme_width_wide', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_width_wide'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_number', 'validate_callback' => 'githeme_validate_width' ) );
	$manager->add_control( 'githeme_width_wide', array( 'type' => 'number', 'section' => 'githeme_layout', 'label' => __( 'Wide width (rem)', 'githeme' ), 'input_attrs' => array( 'min' => 48, 'max' => 90, 'step' => 1 ) ) );
	$manager->add_setting( 'githeme_width_layout', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_width_layout'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_number', 'validate_callback' => 'githeme_validate_width' ) );
	$manager->add_control( 'githeme_width_layout', array( 'type' => 'number', 'section' => 'githeme_layout', 'label' => __( 'Maximum layout width (rem)', 'githeme' ), 'input_attrs' => array( 'min' => 60, 'max' => 100, 'step' => 1 ) ) );

	$manager->add_section( 'githeme_header', array( 'title' => __( 'Header', 'githeme' ), 'priority' => 43 ) );
	$manager->add_setting( 'githeme_logo_height', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_logo_height'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_number', 'validate_callback' => 'githeme_validate_number' ) );
	$manager->add_control( 'githeme_logo_height', array( 'type' => 'number', 'section' => 'githeme_header', 'label' => __( 'Maximum logo height (rem)', 'githeme' ), 'description' => __( 'Original proportions are preserved. Width is limited by the available space.', 'githeme' ), 'input_attrs' => array( 'min' => 2, 'max' => 8, 'step' => 0.25 ) ) );
	$manager->add_setting( 'githeme_header_layout', array( 'type' => 'theme_mod', 'default' => $defaults['githeme_header_layout'], 'transport' => 'refresh', 'sanitize_callback' => 'githeme_sanitize_choice', 'validate_callback' => 'githeme_validate_choice' ) );
	$manager->add_control( 'githeme_header_layout', array( 'type' => 'select', 'section' => 'githeme_header', 'label' => __( 'Header arrangement', 'githeme' ), 'choices' => array( 'inline' => __( 'Identity left, navigation right', 'githeme' ), 'stacked' => __( 'Identity centered, navigation below', 'githeme' ) ) ) );
}
add_action( 'customize_register', 'githeme_customize_register' );

/** Server-rendered advice after saving, without blocking notices or custom JS. */
function githeme_settings_notices() {
	$screen = get_current_screen();
	if ( ! $screen || 'themes' !== $screen->id || ! current_user_can( 'edit_theme_options' ) ) {
		return;
	}
	$warnings = githeme_contrast_warnings();
	if ( githeme_saved_width_warning() ) {
		$warnings[] = githeme_saved_width_warning();
	}
	foreach ( $warnings as $warning ) {
		echo '<div class="notice notice-info"><p>' . esc_html( $warning ) . '</p></div>';
	}
}
add_action( 'admin_notices', 'githeme_settings_notices' );
