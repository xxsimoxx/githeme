<?php
/**
 * Isolated social-menu checks using native hooks, KSES and the native menu walker.
 * Run: php tests/social-menu.php [--json] [--core=/path/to/classicpress].
 * No CMS bootstrap, database connection, or settings writes.
 *
 * @package githeme
 */
$core = dirname( __DIR__, 4 );
foreach ( $argv as $argument ) {
	if ( str_starts_with( $argument, '--core=' ) ) { $core = substr( $argument, 7 ); }
}
define( 'ABSPATH', rtrim( $core, '/' ) . '/' );
define( 'WPINC', 'wp-includes' );
foreach ( array( 'compat.php', 'plugin.php', 'formatting.php', 'kses.php', 'http.php', 'class-wp-walker.php', 'class-walker-nav-menu.php' ) as $file ) {
	require_once ABSPATH . WPINC . '/' . $file;
}
$theme = dirname( __DIR__ );
$checks = 0;
$mods = array();
$assigned = false;
$items = array();
$widget_html = '';
$nav_calls = 0;
$footer_calls = 0;
function __( $text, $domain = 'default' ) { return $text; }
function get_option( $name, $default = false ) { return 'blog_charset' === $name ? 'UTF-8' : $default; }
function wp_load_alloptions() { return array( 'blog_charset' => 'UTF-8' ); }
function wp_allowed_protocols() { return array( 'http', 'https', 'mailto', 'tel' ); }
function get_privacy_policy_url() { return ''; }
function get_theme_mod( $name, $default = false ) { return $GLOBALS['mods'][ $name ] ?? $default; }
function get_template_directory() { return $GLOBALS['theme']; }
function get_template_directory_uri() { return 'https://example.test/theme'; }
function get_theme_file_path( $file ) { return get_template_directory() . ( $GLOBALS['unsafe_icon'] ?? $file ); }
function has_nav_menu( $location ) { return 'social' === $location && $GLOBALS['assigned']; }
function is_front_page() { return false; }
function is_home() { return false; }
function is_active_sidebar( $id ) { return '' !== $GLOBALS['widget_html']; }
function dynamic_sidebar( $id ) { echo $GLOBALS['widget_html']; }
function wp_footer() { ++$GLOBALS['footer_calls']; }
function register_nav_menus( $menus ) { $GLOBALS['registered_menus'] = $menus; }
function load_theme_textdomain( ...$args ) {}
function add_theme_support( ...$args ) {}
function add_editor_style( ...$args ) {}
function add_query_arg( ...$args ) { return ''; }
function get_template() { return 'githeme'; }
function get_nav_menu_locations() { return $GLOBALS['assigned'] ? array( 'social' => $GLOBALS['test_menu_id'] ?? 100 ) : array(); }
function wp_get_nav_menu_items( $id, $args = array() ) { return $GLOBALS['items']; }
function current_user_can( $capability ) { return false; }
function wp_hash( $data ) { return hash_hmac( 'md5', $data, 'isolated-fixture-key' ); }
function wp_json_encode( $data ) { return json_encode( $data, JSON_THROW_ON_ERROR ); }
function wp_get_theme( ...$args ) { return new class { public function get( $key ) { return '1.0.2'; } }; }
function wp_nav_menu( $args ) {
	++$GLOBALS['nav_calls'];
	$args = apply_filters( 'wp_nav_menu_args', $args );
	$GLOBALS['last_menu_args'] = $args;
	if ( ! $GLOBALS['items'] ) { return false; }
	$walker_args = (object) array_merge( array( 'before' => '', 'after' => '', 'link_before' => '', 'link_after' => '' ), $args );
	$walker = new Walker_Nav_Menu();
	$html = $walker->walk( $GLOBALS['items'], 0, $walker_args );
	$html = '<nav class="' . esc_attr( $args['container_class'] ) . '" aria-label="' . esc_attr( $args['container_aria_label'] ) . '"><ul class="' . esc_attr( $args['menu_class'] ) . '">' . $html . '</ul></nav>';
	$html = apply_filters( 'wp_nav_menu', $html, (object) $args );
	if ( $args['echo'] ) { echo $html; }
	return $html;
}
require $theme . '/inc/settings.php';
require $theme . '/inc/setup.php';
require $theme . '/inc/social-menu.php';
function githeme_social_check( $ok, $message ) {
	if ( ! $ok ) { throw new RuntimeException( $message ); }
	++$GLOBALS['checks'];
}
function githeme_social_test_item( $id, $url, $title, $parent = 0 ) {
	return (object) array( 'ID' => $id, 'db_id' => $id, 'menu_item_parent' => $parent, 'url' => $url, 'title' => $title, 'classes' => array(), 'target' => '', 'xfn' => '', 'attr_title' => '', 'current' => false );
}
githeme_setup();
githeme_social_check( array( 'primary' => 'Primary menu', 'social' => 'Social' ) === $registered_menus, 'Register Social without changing Primary menu' );
$urls = array(
	'https://facebook.com/example' => 'facebook-f', 'https://www.instagram.com/example/' => 'instagram',
	'https://linkedin.com/in/example' => 'linkedin-in', 'https://www.youtube.com/@example' => 'youtube',
	'https://youtu.be/example' => 'youtube', 'https://x.com/example' => 'x-twitter', 'https://twitter.com/example' => 'x-twitter',
	'https://threads.net/@example' => 'threads', 'https://threads.com/@example' => 'threads', 'https://www.tiktok.com/@example' => 'tiktok',
	'https://pinterest.com/example' => 'pinterest-p', 'https://mastodon.social/@example' => 'mastodon',
	'https://wa.me/123456789' => 'whatsapp', 'https://api.whatsapp.com/send' => 'whatsapp', 'https://t.me/example' => 'telegram',
	'https://github.com/example' => 'github', 'https://wordpress.org/' => 'wordpress', 'https://example.wordpress.com/' => '',
	'https://vimeo.com/123' => 'vimeo-v', 'https://open.spotify.com/artist/example' => 'spotify', 'https://behance.net/example' => 'behance',
	'mailto:hello@example.test?subject=Example' => 'envelope', 'mailto:hello%2Bteam@example.test' => 'envelope',
	'tel:+1-202-555-0123' => 'phone', 'tel:2025550123;ext=42' => 'phone',
	'tel:7042;phone-context=example.test' => 'phone', 'TEL:%2B1%20(202)%20555-0123' => 'phone',
	'https://maps.app.goo.gl/Example' => 'location-dot', 'https://maps.google.com/?q=Example' => 'location-dot',
	'https://google.com/maps' => 'location-dot', 'https://www.google.com/maps/place/Example' => 'location-dot',
	'https://goo.gl/maps/Example' => 'location-dot', 'https://google.com/maps?query=Example#map' => 'location-dot',
	'HTTP://WWW.INSTAGRAM.COM/example' => 'instagram', '//www.github.com/example' => 'github', 'https://github.com./example' => 'github',
);
foreach ( $urls as $url => $expected ) { githeme_social_check( $expected === githeme_social_icon_name( $url ), 'Service recognition: ' . $url ); }
foreach ( array( 'https://facebook.com.evil.test/', 'https://notfacebook.com/', 'https://evil.test/facebook.com', 'https://evil.test/?url=https://github.com', 'https://github.com@evil.test/', 'https://user:password@github.com/', 'https://google.com/search?q=maps', 'https://google.com/maps-other', 'https://goo.gl/other', 'https://google.com/Maps', '/maps', '/?url=instagram.com', 'javascript:instagram.com', 'ftp://github.com/', 'mailto:not-an-email', 'mailto:hello@example.test%0D%0ABcc:other@example.test', 'https://unknown.example/@user', 'https://sub.github.com/', 'https://github_com/', 'https://[invalid', '' ) as $url ) {
	githeme_social_check( '' === githeme_social_icon_name( $url ), 'No hostname/path/scheme spoofing: ' . $url );
}
foreach ( array( 'tel:', 'tel:call-us', 'tel://user@example.test', 'tel:123%0D%0A456' ) as $url ) {
	githeme_social_check( '' === githeme_social_icon_name( $url ), 'Invalid telephone link remains text' );
}
$extension = static function ( $rules ) {
	$rules['custom-instance'] = array( 'hosts' => array( 'social.example.test' ), 'path_prefix' => '/@team', 'icon' => 'mastodon' );
	$rules['bad-icon'] = array( 'hosts' => array( 'unsafe.example.test' ), 'icon' => '../../outside' );
	return $rules;
};
add_filter( 'githeme_social_links_icons', $extension );
githeme_social_check( 'mastodon' === githeme_social_icon_name( 'https://social.example.test/@team/posts' ), 'Filter can extend instances and paths' );
githeme_social_check( '' === githeme_social_icon_name( 'https://social.example.test/@team-other' ), 'Filtered paths retain segment boundary' );
githeme_social_check( '' === githeme_social_icon_name( 'https://unsafe.example.test' ), 'Filtered SVG basename cannot traverse directories' );
remove_filter( 'githeme_social_links_icons', $extension );
$args = (object) array( 'theme_location' => 'social' );
foreach ( array_unique( array_column( githeme_social_links_icons(), 'icon' ) ) as $icon ) {
	$url = array_search( $icon, $urls, true );
	$item = githeme_social_test_item( 1, $url, 'Example &amp; team' );
	$html = githeme_social_menu_item_title( $item->title, $item, $args );
	$dom = new DOMDocument(); @$dom->loadHTML( '<meta charset="UTF-8"><a>' . $html . '</a>' );
	$svgs = $dom->getElementsByTagName( 'svg' );
	githeme_social_check( 1 === $svgs->length && 1 === $dom->getElementsByTagName( 'path' )->length, 'Local artwork renders: ' . $icon );
	githeme_social_check( 'true' === $svgs->item( 0 )->getAttribute( 'aria-hidden' ) && 'false' === $svgs->item( 0 )->getAttribute( 'focusable' ), 'Decorative, non-focusable SVG: ' . $icon );
	githeme_social_check( 'currentColor' === $svgs->item( 0 )->getAttribute( 'fill' ) && '' !== $svgs->item( 0 )->getAttribute( 'viewbox' ), 'Scalable, palette-driven SVG: ' . $icon );
	githeme_social_check( 'Example & team' === $dom->getElementsByTagName( 'span' )->item( 0 )->textContent, 'Menu title remains its accessible name: ' . $icon );
}
$item = githeme_social_test_item( 1, 'https://github.com/example', 'GitHub' );
githeme_social_check( 'GitHub' === githeme_social_menu_item_title( 'GitHub', $item, (object) array( 'theme_location' => 'primary' ) ), 'Primary menu unchanged' );
githeme_social_check( '' === githeme_social_menu_item_title( '', $item, $args ), 'No unlabeled icon for an empty title' );
$item->url = 'https://example.test/?facebook.com';
githeme_social_check( '<strong>Custom</strong>' === githeme_social_menu_item_title( '<strong>Custom</strong>', $item, $args ), 'Unknown URL preserves original title HTML' );
$missing = static function ( $rules ) { $rules['github']['icon'] = 'not-bundled'; return $rules; };
add_filter( 'githeme_social_links_icons', $missing );
$item->url = 'https://github.com/example';
githeme_social_check( 'GitHub' === githeme_social_menu_item_title( 'GitHub', $item, $args ), 'Missing local asset retains text' );
remove_filter( 'githeme_social_links_icons', $missing );
$unsafe_icon = '/tests/fixtures/social-unsafe.svg';
$html = githeme_social_menu_item_title( 'GitHub', $item, $args );
githeme_social_check( ! preg_match( '/<(script|image|a)\b|\bonload=|\bonclick=|\bhref=|\bstyle=|url\(/i', $html ), 'Unsafe asset attributes, external resources and elements stripped' );
githeme_social_check( str_contains( $html, 'aria-hidden="true" focusable="false"' ), 'Child artwork cannot opt into accessibility tree' );
unset( $unsafe_icon );
githeme_social_check( '' === githeme_get_social_links_menu() && 0 === $nav_calls, 'No assigned menu: no render and no page fallback' );
$assigned = true;
githeme_social_check( '' === githeme_get_social_links_menu(), 'Empty assigned menu stays empty' );
$items = array(
	githeme_social_test_item( 11, 'https://instagram.com/example', 'Our photographs' ),
	githeme_social_test_item( 12, 'https://example.test/info', 'Visit our information page with a longer label' ),
	githeme_social_test_item( 13, 'https://github.com/example', 'Our code', 11 ),
	githeme_social_test_item( 14, 'mailto:hello@example.test', 'Email the team' ),
);
$items[0]->target = '_blank';
$items[0]->attr_title = 'Photographs';
$items[1]->current = true;
$menu = githeme_get_social_links_menu();
githeme_social_check( false === $last_menu_args['fallback_cb'] && true === $last_menu_args['echo'], 'Native echo enables selective refresh while buffering prevents output duplication' );
ob_start(); $buffered_menu = githeme_get_social_links_menu(); $unexpected_output = ob_get_clean();
githeme_social_check( '' === $unexpected_output && $buffered_menu === $menu, 'Buffering preserves the public returned-HTML contract' );
githeme_social_check( str_contains( $menu, 'aria-label="Social"' ) && str_contains( $menu, 'target="_blank" rel="noopener"' ) && str_contains( $menu, 'title="Photographs"' ) && str_contains( $menu, 'aria-current="page"' ), 'Native link attributes and navigation label preserved' );
githeme_social_check( str_contains( $menu, 'class="sub-menu"' ) && substr_count( $menu, '<a' ) === 4, 'Native hierarchy retained without dropping children' );
githeme_social_check( strpos( $menu, 'Our photographs' ) < strpos( $menu, 'Our code' ) && strpos( $menu, 'Our code' ) < strpos( $menu, 'Visit our information' ), 'Native walker preserves hierarchical order' );
$saved_items = $items;
$items = array( githeme_social_test_item( 15, 'tel:+1-202-555-0123;ext=42', 'Call our office' ) );
$phone_menu = githeme_get_social_links_menu();
githeme_social_check( str_contains( $phone_menu, 'href="tel:+1-202-555-0123;ext=42"' ) && str_contains( $phone_menu, '<svg ' ) && str_contains( $phone_menu, '>Call our office</span>' ), 'Telephone URL and accessible name preserved by native walker' );
$items = $saved_items;
$fixtures = array();
foreach ( array( 'none', 'widgets', 'social', 'both', 'empty-social' ) as $case ) {
	$assigned = in_array( $case, array( 'social', 'both', 'empty-social' ), true );
	$widget_html = in_array( $case, array( 'widgets', 'both' ), true ) ? '<section class="widget"><h2>Footer fixture</h2><p>Optional widgets.</p></section>' : '';
	$saved_items = $items;
	if ( 'empty-social' === $case ) { $items = array(); }
	$before_calls = $footer_calls;
	ob_start(); include $theme . '/footer.php'; $html = ob_get_clean();
	githeme_social_check( ( ! in_array( $case, array( 'none', 'empty-social' ), true ) ) === str_contains( $html, '<footer class="site-footer">' ), 'No empty footer: ' . $case );
	githeme_social_check( ( '' !== $widget_html ) === str_contains( $html, 'class="footer-widgets"' ), 'Existing widget rendering: ' . $case );
	githeme_social_check( in_array( $case, array( 'social', 'both' ), true ) === str_contains( $html, 'githeme-social-navigation' ), 'Social row only when populated: ' . $case );
	githeme_social_check( $footer_calls === $before_calls + 1 && 1 === substr_count( $html, '</main>' ), 'Document closing/hooks unchanged: ' . $case );
	$fixtures[ $case ] = $html;
	$items = $saved_items;
}
$palettes = array();
foreach ( array( array( '#14569a', '#14569a', '#ffffff' ), array( '#eeeeee', '#eeeeee', '#ffffff' ), array( '#ffffff', '#ffffff', '#202833' ), array( '#999999', '#999999', '#999999' ), array( '#000000', '#000000', '#000000' ) ) as list( $link, $primary, $background ) ) {
	$mods = array( 'githeme_color_link' => $link, 'githeme_color_primary' => $primary, 'githeme_color_footer_background' => $background );
	$css = githeme_custom_properties_css();
	preg_match( '/--color-social-link:([^;]+);/', $css, $match ); $color = $match[1];
	githeme_social_check( githeme_contrast_ratio( $color, $background ) >= 4.5, 'Social text/icon contrast against footer: ' . $background );
	githeme_social_check( $color === ( githeme_contrast_ratio( $link, $background ) >= 4.5 ? $link : githeme_button_text_color( $background ) ), 'Preserve a passing configured link color' );
	preg_match( '/--color-social-focus:([^;]+);/', $css, $match );
	githeme_social_check( githeme_contrast_ratio( $match[1], $background ) >= 3, 'Social outline contrast against footer: ' . $background );
	$palettes[] = array( 'background' => $background, 'css' => $css );
}

// Exercise the actual core PHP preview filters without bootstrapping a site or
// saving a changeset. Only menu lookup, permissions and hashing are in memory.
require_once ABSPATH . WPINC . '/class-wp-customize-nav-menus.php';
$manager = (object) array( 'selective_refresh' => new class {
	public $partials = array();
	public function add_partial( $id, $args ) { $this->partials[ $id ] = $args; }
} );
$native_menus = new WP_Customize_Nav_Menus( $manager );
$assigned = true;
$native_menus->customize_preview_init();
$preview_menu = githeme_get_social_links_menu();
githeme_social_check( true === $last_menu_args['can_partial_refresh'] && str_contains( $preview_menu, 'data-customize-partial-id=' ), 'Actual core preview filter accepts buffered echo and marks the native menu placement' );
$partial = end( $manager->selective_refresh->partials );
githeme_social_check( is_array( $partial['settings'] ) && array_is_list( $partial['settings'] ), 'Native menu partial exports settings as a JSON array, not an object/string' );
githeme_social_check( in_array( 'nav_menu_locations[social]', $partial['settings'], true ) && in_array( 'nav_menu_item[11]', $partial['settings'], true ), 'Core partial observes location assignment and existing item changes' );
$old_args = $last_menu_args;
$old_args['echo'] = false;
$old_args = $native_menus->filter_wp_nav_menu_args( $old_args );
githeme_social_check( false === $old_args['can_partial_refresh'], 'Previous echo=false behavior reproduces the theme-side exclusion' );
$context = $last_menu_args['customize_preview_nav_menus_args'];
$native_roundtrip = $native_menus->render_nav_menu_partial( null, $context );
$customizer_diagnosis = array( 'native_partial_roundtrip' => false !== $native_roundtrip );
if ( false === $native_roundtrip ) {
	// Diagnose, but do not modify the context passed to production core code.
	$unsigned = $context;
	unset( $unsigned['args_hmac'] );
	ksort( $unsigned );
	githeme_social_check( $native_menus->hash_nav_menu_args( $unsigned ) !== $context['args_hmac'], 'Local core roundtrip fails context signature verification' );
	unset( $unsigned['menu_id'] );
	githeme_social_check( $native_menus->hash_nav_menu_args( $unsigned ) === $context['args_hmac'], 'Local core adds menu_id after calculating its signature' );
	$customizer_diagnosis['core_limitation'] = 'menu_id added after args_hmac; native render callback returns false';
} else {
	githeme_social_check( str_contains( $native_roundtrip, '<svg ' ), 'Core roundtrip renders theme icons when its context is accepted' );
}
$test_menu_id = 101;
githeme_get_social_links_menu();
githeme_social_check( 101 === $last_menu_args['customize_preview_nav_menus_args']['menu_id'], 'Reassigned location resolves its current preview menu' );
$original_item = $items[0];
$items[0] = githeme_social_test_item( 11, 'tel:+1-202-555-0123', 'Call the team' );
$changed_menu = githeme_get_social_links_menu();
githeme_social_check( str_contains( $changed_menu, 'href="tel:+1-202-555-0123"' ) && str_contains( $changed_menu, '>Call the team</span>' ), 'Preview rendering recalculates icons and names after item edits' );
$items[0] = $original_item;
$assigned = false;
githeme_social_check( '' === githeme_get_social_links_menu(), 'Clearing assignment retains no-menu/no-empty-footer behavior' );
remove_filter( 'wp_nav_menu_args', array( $native_menus, 'filter_wp_nav_menu_args' ), 1000 );
remove_filter( 'wp_nav_menu', array( $native_menus, 'filter_wp_nav_menu' ), 10 );
if ( in_array( '--json', $argv, true ) ) {
	echo json_encode( array( 'checks' => $checks, 'fixtures' => $fixtures, 'palettes' => $palettes, 'customizer' => $customizer_diagnosis, 'menu_partial_settings' => $partial['settings'], 'css' => file_get_contents( $theme . '/style.css' ) ), JSON_THROW_ON_ERROR );
} else {
	echo $checks . " social menu checks passed (isolated native walker/KSES, no database).\n";
	echo json_encode( $customizer_diagnosis ) . "\n";
}
