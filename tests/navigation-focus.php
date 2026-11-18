<?php
/** Focus-color regressions with in-memory theme mods; no database writes. @package githeme */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
$count = 0;
$check = static function ( $ok, $message ) use ( &$count ) {
	if ( ! $ok ) { throw new RuntimeException( $message ); }
	++$count;
};
$original = get_option( 'theme_mods_githeme' );
$overrides = array();
$filter = static function () use ( &$overrides ) { return array_merge( githeme_defaults(), $overrides ); };
add_filter( 'pre_option_theme_mods_githeme', $filter );
$cases = array(
	array( 'teal/light-blue', '#103d4c', '#e3f2f6', '#ffffff' ),
	array( 'green/white', '#479300', '#ffffff', '#ffffff' ),
	array( 'amber/white', '#ffaa02', '#ffffff', '#ffffff' ),
	array( 'red/white', '#891f1f', '#ffffff', '#ffffff' ),
	array( 'white/dark-header', '#ffffff', '#202833', '#ffffff' ),
	array( 'black/dark-dropdown', '#000000', '#ffffff', '#202833' ),
	array( 'gray/gray', '#999999', '#999999', '#999999' ),
	array( 'above-threshold', '#949494', '#ffffff', '#ffffff' ),
	array( 'below-threshold', '#959595', '#ffffff', '#ffffff' ),
);
$fixtures = array();
try {
	foreach ( $cases as list( $name, $primary, $header, $background ) ) {
		$overrides = array( 'githeme_color_primary' => $primary, 'githeme_color_header_background' => $header, 'githeme_color_background' => $background );
		$css = githeme_custom_properties_css();
		$fixture = array( 'name' => $name, 'css' => $css, 'primary' => $primary, 'header' => $header, 'background' => $background );
		foreach ( array( 'color-navigation-focus' => $header, 'color-navigation-submenu-focus' => $background ) as $property => $surface ) {
			preg_match( '/--' . $property . ':(#[a-fA-F0-9]{6});/', $css, $match );
			$color = $match[1] ?? null;
			$check( null !== $color, 'Generated focus variable: ' . $name );
			$check( githeme_contrast_ratio( $color, $surface ) >= 3, 'Non-text contrast: ' . $name );
			$expected = githeme_contrast_ratio( $primary, $surface ) >= 3 ? $primary : githeme_button_text_color( $surface );
			$check( $color === $expected, 'Preserve a passing primary, otherwise use existing contrast helper: ' . $name );
			$fixture[ $property ] = $color;
		}
		$fixtures[] = $fixture;
	}
	$check( githeme_contrast_ratio( '#ffaa02', '#ffffff' ) < 3 && '#000000' === githeme_navigation_focus_color( '#ffaa02', '#ffffff' ), 'Reported amber outline regression' );
} finally {
	remove_filter( 'pre_option_theme_mods_githeme', $filter );
}
$check( get_option( 'theme_mods_githeme' ) === $original, 'Stored settings preserved' );
echo wp_json_encode( array( 'checks' => $count, 'fixtures' => $fixtures ) ) . "\n";
