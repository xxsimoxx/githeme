<?php
/**
 * Run: wp eval-file src/wp-content/themes/githeme/tests/contrast.php [json]
 * No database writes. JSON mode is consumed by the dependency-free Node test.
 *
 * @package githeme
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	return;
}
$cases = json_decode( file_get_contents( __DIR__ . '/contrast-cases.json' ), true, 512, JSON_THROW_ON_ERROR );
$original_option = get_option( 'theme_mods_githeme' );
$count = 0;
$check = static function ( $ok, $message ) use ( &$count ) {
	if ( ! $ok ) {
		throw new RuntimeException( $message );
	}
	++$count;
};
foreach ( $cases as &$case ) {
	$ratio = githeme_contrast_ratio( $case['first'], $case['second'] );
	$check( null === $case['ratio'] ? null === $ratio : abs( $ratio - $case['ratio'] ) < 1e-10, $case['name'] );
	$check( githeme_contrast_ratio( $case['second'], $case['first'] ) === $ratio, 'Symmetry: ' . $case['name'] );
	$case['phpRatio'] = $ratio;
}
unset( $case );
$reports = array();
foreach ( array( '#000000', '#ffffff', '#eaf5af', '#777777', '#767676', '#14569a', null, 'invalid' ) as $color ) {
	$colors = array(
		'text'       => $color,
		'link'       => $color,
		'primary'    => $color,
		'background' => '#ffffff',
	);
	$report = githeme_contrast_report( $colors );
	$button = githeme_button_text_color( $color );
	$check( null === githeme_hex_channels( $color ) ? null === $button : $report['button']['ratio'] >= githeme_contrast_rules()['normalTextMinimum'], 'Button text contrast' );
	$check( null === githeme_hex_channels( $color ) ? 'invalid' === $report['text']['status'] : 'invalid' !== $report['text']['status'], 'Invalid status' );
	$reports[] = array(
		'colors'     => $colors,
		'report'     => $report,
		'buttonText' => $button,
	);
}
$check(
	'fail' === githeme_contrast_report(
		array(
			'text'       => '#777777',
			'background' => '#fff',
		)
	)['text']['status'],
	'Do not round before comparison'
);
$check( '#ffffff' === githeme_button_text_color( '#000' ) && '#000000' === githeme_button_text_color( '#fff' ), 'Button inversion' );
require_once ABSPATH . WPINC . '/class-wp-customize-manager.php';
$manager = new WP_Customize_Manager();
do_action( 'customize_register', $manager );
$control = $manager->get_control( 'githeme_contrast' );
$check( $control instanceof Githeme_Contrast_Control && array() === $control->settings, 'Advice must have no setting to save or validate' );
$check( is_wp_error( $manager->get_setting( 'githeme_color_text' )->validate( "#fff\n" ) ), 'Validation must use the same strict color syntax as the calculation' );
$override_primary = static function () {
	return "#fff\n";
};
add_filter( 'theme_mod_githeme_color_primary', $override_primary );
try {
	$palette = githeme_palette();
	$check( githeme_defaults()['githeme_color_primary'] === $palette['primary'], 'Invalid stored palette values must render with a safe fallback' );
	$check( null !== githeme_button_text_color( $palette['primary'] ), 'Defensive rendering must not create an empty button foreground' );
} finally {
	remove_filter( 'theme_mod_githeme_color_primary', $override_primary );
}
ob_start();
$control->render_content();
$markup = ob_get_clean();
$check( str_contains( $markup, 'role="status"' ) && str_contains( $markup, 'data-githeme-contrast-row="button"' ), 'Server fallback markup' );
$check( ! str_contains( $markup, '<input' ), 'Advice must not create form values' );
$color_control = $manager->get_control( 'githeme_color_text' );
foreach ( array( array( '#fff' ), '<script>bad</script>' ) as $invalid ) {
	$override = static function () use ( $invalid ) {
		return $invalid;
	};
	add_filter( 'theme_mod_githeme_color_text', $override );
	try {
		ob_start();
		$color_control->render_content();
		$markup = ob_get_clean();
		$check( is_array( $invalid ) ? str_contains( $markup, $color_control->setting->default ) : ( ! str_contains( $markup, '<script>' ) && str_contains( $markup, '&lt;script&gt;' ) ), 'Invalid stored input must remain safe in markup' );
	} finally {
		remove_filter( 'theme_mod_githeme_color_text', $override );
	}
}
$check( get_option( 'theme_mods_githeme' ) === $original_option, 'Contrast tests must not save settings' );
if ( isset( $args[0] ) && 'json' === $args[0] ) {
	WP_CLI::log(
		wp_json_encode(
			array(
				'rules'         => githeme_contrast_rules(),
				'cases'         => $cases,
				'reports'       => $reports,
				'phpAssertions' => $count,
			)
		)
	);
} else {
	WP_CLI::success( $count . ' PHP contrast assertions passed. No settings saved.' );
}
