<?php
/**
 * Isolated core menu-partial export diagnostic, independent of GiTheme/Social.
 * Run: php tests/customizer-menu-settings.php
 * No CMS bootstrap, database access, theme includes or settings changes.
 *
 * @package githeme
 */
define( 'ABSPATH', rtrim( getenv( 'GITHEME_TEST_CORE' ) ?: dirname( __DIR__, 4 ), '/' ) . '/' );
define( 'WPINC', 'wp-includes' );
require ABSPATH . WPINC . '/plugin.php';
require ABSPATH . WPINC . '/customize/class-wp-customize-selective-refresh.php';
require ABSPATH . WPINC . '/customize/class-wp-customize-partial.php';
require ABSPATH . WPINC . '/class-wp-customize-nav-menus.php';
function get_nav_menu_locations() { return array( 'primary' => 100 ); }
function wp_get_nav_menu_items( $id, $args = array() ) { return array( (object) array( 'ID' => 11 ), (object) array( 'ID' => 12 ) ); }
function current_user_can( $capability ) { return false; }
function wp_hash( $data ) { return hash_hmac( 'md5', $data, 'isolated-diagnostic-key' ); }
$checks = 0;
$check = static function ( $ok, $label ) use ( &$checks ) {
	if ( ! $ok ) { throw new RuntimeException( $label ); }
	++$checks;
};
// Skip the component constructor's environment hooks; use its actual PHP partial
// registration and json() methods, not a stand-in serializer.
$component = ( new ReflectionClass( 'WP_Customize_Selective_Refresh' ) )->newInstanceWithoutConstructor();
$manager = (object) array( 'selective_refresh' => $component );
$component->manager = $manager;
$menus = new WP_Customize_Nav_Menus( $manager );
$cases = array();
foreach ( array(
	'primary-location' => array( 'theme_location' => 'primary', 'menu' => 0 ),
	'explicit-menu-id' => array( 'theme_location' => '', 'menu' => 100 ),
	'native-widget-menu-object' => array( 'theme_location' => '', 'menu' => (object) array( 'term_id' => 100 ) ),
) as $name => $args ) {
	$args += array( 'echo' => true, 'container' => 'nav', 'fallback_cb' => false );
	$result = $menus->filter_wp_nav_menu_args( $args );
	$id = 'nav_menu_instance[' . $result['customize_preview_nav_menus_args']['args_hmac'] . ']';
	$partial = $component->get_partial( $id );
	$check( $partial instanceof WP_Customize_Partial, 'Actual native partial created: ' . $name );
	$export = $partial->json();
	$check( is_array( $export['settings'] ), 'PHP settings is an array: ' . $name );
	$cases[ $name ] = array( 'id' => $id, 'is_list' => array_is_list( $export['settings'] ), 'export' => $export );
}
$check( $cases['primary-location']['is_list'], 'Location-based primary menu exports a JSON list' );
$check( ! function_exists( 'githeme_get_social_links_menu' ) && ! function_exists( 'githeme_customize_register' ), 'No GiTheme code or Social menu loaded' );
$payload = array( 'checks' => $checks, 'cases' => $cases, 'theme_loaded' => false );
echo json_encode( $payload, JSON_THROW_ON_ERROR ) . "\n";
