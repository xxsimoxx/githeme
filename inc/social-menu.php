<?php
/**
 * Optional native social menu, matched against original menu item URLs.
 *
 * @package githeme
 */

defined( 'ABSPATH' ) || exit;

/**
 * Service rules; hosts are exact after removing a leading www. and trailing dot.
 *
 * @return array Rules keyed by service identifier.
 */
function githeme_social_links_icons() {
	$icons = array(
		'facebook'    => array( 'hosts' => array( 'facebook.com', 'm.facebook.com', 'fb.com' ), 'icon' => 'facebook-f' ),
		'instagram'   => array( 'hosts' => array( 'instagram.com' ), 'icon' => 'instagram' ),
		'linkedin'    => array( 'hosts' => array( 'linkedin.com', 'lnkd.in' ), 'icon' => 'linkedin-in' ),
		'youtube'     => array( 'hosts' => array( 'youtube.com', 'm.youtube.com', 'youtu.be' ), 'icon' => 'youtube' ),
		'x'           => array( 'hosts' => array( 'x.com', 'twitter.com', 'mobile.twitter.com' ), 'icon' => 'x-twitter' ),
		'threads'     => array( 'hosts' => array( 'threads.net', 'threads.com' ), 'icon' => 'threads' ),
		'tiktok'      => array( 'hosts' => array( 'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com' ), 'icon' => 'tiktok' ),
		'pinterest'   => array( 'hosts' => array( 'pinterest.com', 'pin.it' ), 'icon' => 'pinterest-p' ),
		'mastodon'    => array( 'hosts' => array( 'mastodon.social', 'mastodon.online', 'mstdn.social', 'mas.to', 'fosstodon.org', 'hachyderm.io' ), 'icon' => 'mastodon' ),
		'whatsapp'    => array( 'hosts' => array( 'whatsapp.com', 'api.whatsapp.com', 'web.whatsapp.com', 'wa.me' ), 'icon' => 'whatsapp' ),
		'telegram'    => array( 'hosts' => array( 'telegram.org', 'telegram.me', 't.me' ), 'icon' => 'telegram' ),
		'github'      => array( 'hosts' => array( 'github.com' ), 'icon' => 'github' ),
		'wordpress'   => array( 'hosts' => array( 'wordpress.org', 'wordpress.com' ), 'icon' => 'wordpress' ),
		'vimeo'       => array( 'hosts' => array( 'vimeo.com', 'player.vimeo.com' ), 'icon' => 'vimeo-v' ),
		'spotify'     => array( 'hosts' => array( 'spotify.com', 'open.spotify.com' ), 'icon' => 'spotify' ),
		'behance'     => array( 'hosts' => array( 'behance.net', 'be.net' ), 'icon' => 'behance' ),
		'email'       => array( 'scheme' => 'mailto', 'icon' => 'envelope' ),
		'telephone'   => array( 'scheme' => 'tel', 'icon' => 'phone' ),
		'google-maps' => array( 'hosts' => array( 'maps.app.goo.gl', 'maps.google.com' ), 'icon' => 'location-dot' ),
		'google-path' => array( 'hosts' => array( 'google.com', 'goo.gl' ), 'path_prefix' => '/maps', 'icon' => 'location-dot' ),
	);

	/**
	 * Extend service rules without inspecting or replacing rendered menu HTML.
	 *
	 * Each rule accepts hosts (exact lowercase hostnames without www.), an optional
	 * case-sensitive path_prefix (matched on a segment boundary), and icon (SVG
	 * basename in assets/icons/social/, resolved through get_theme_file_path()).
	 * A scheme of mailto or tel matches an email address or telephone URI instead.
	 * Child themes may supply additional local SVG files; unsafe markup is stripped.
	 *
	 * @param array $icons Service rules.
	 */
	return apply_filters( 'githeme_social_links_icons', $icons );
}

/**
 * Resolve a local SVG basename without fetching URLs or guessing federated hosts.
 *
 * @param string $url Original menu item URL.
 * @return string Icon basename, or an empty string for ordinary text links.
 */
function githeme_social_icon_name( $url ) {
	if ( ! is_string( $url ) ) {
		return '';
	}
	$parts = wp_parse_url( $url );
	if ( ! is_array( $parts ) || isset( $parts['user'] ) || isset( $parts['pass'] ) ) {
		return '';
	}
	$scheme = strtolower( $parts['scheme'] ?? '' );
	$is_mail = 'mailto' === $scheme && is_email( rawurldecode( $parts['path'] ?? '' ) );
	$telephone = rawurldecode( $parts['path'] ?? '' );
	$is_tel = 'tel' === $scheme && preg_match( '/\d/', $telephone ) && preg_match( '/\A\+?[0-9().*# -]+(?:;[a-z0-9-]+=[a-z0-9.+-]+)*\z/i', $telephone );
	$host = '';
	if ( ! $is_mail && ! $is_tel ) {
		if ( ! in_array( $scheme, array( 'http', 'https' ), true ) && ! ( '' === $scheme && str_starts_with( $url, '//' ) ) ) {
			return '';
		}
		$host = strtolower( $parts['host'] ?? '' );
		if ( ! filter_var( $host, FILTER_VALIDATE_DOMAIN, FILTER_FLAG_HOSTNAME ) ) {
			return '';
		}
		$host = rtrim( $host, '.' );
		if ( str_starts_with( $host, 'www.' ) ) {
			$host = substr( $host, 4 );
		}
	}
	foreach ( (array) githeme_social_links_icons() as $rule ) {
		if ( ! is_array( $rule ) || ! isset( $rule['icon'] ) || ! is_string( $rule['icon'] ) || ! preg_match( '/\A[a-z0-9-]+\z/', $rule['icon'] ) ) {
			continue;
		}
		if ( isset( $rule['scheme'] ) ) {
			if ( ( 'mailto' === $rule['scheme'] && $is_mail ) || ( 'tel' === $rule['scheme'] && $is_tel ) ) {
				return $rule['icon'];
			}
			continue;
		}
		if ( $is_mail || $is_tel || ! in_array( $host, (array) ( $rule['hosts'] ?? array() ), true ) ) {
			continue;
		}
		if ( isset( $rule['path_prefix'] ) ) {
			$prefix = $rule['path_prefix'];
			$path   = $parts['path'] ?? '/';
			if ( ! is_string( $prefix ) || '' === $prefix || ( $path !== $prefix && ! str_starts_with( $path, rtrim( $prefix, '/' ) . '/' ) ) ) {
				continue;
			}
		}
		return $rule['icon'];
	}
	return '';
}

/**
 * Replace only recognized Social item titles; leave the native walker intact.
 *
 * @param string   $title Native filtered menu title.
 * @param WP_Post  $item  Menu item with its original URL.
 * @param stdClass $args  Native menu arguments.
 * @return string Title HTML, preserving an accessible textual name.
 */
function githeme_social_menu_item_title( $title, $item, $args ) {
	if ( 'social' !== ( $args->theme_location ?? '' ) || '' === trim( wp_strip_all_tags( $title ) ) ) {
		return $title;
	}
	$icon = githeme_social_icon_name( $item->url );
	if ( '' === $icon ) {
		return $title;
	}
	$file = get_theme_file_path( '/assets/icons/social/' . $icon . '.svg' );
	if ( ! is_readable( $file ) ) {
		return $title;
	}
	$svg = wp_kses(
		file_get_contents( $file ), // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Read a validated local theme asset, never a URL.
		array(
			'svg'  => array( 'xmlns' => true, 'viewbox' => true, 'width' => true, 'height' => true, 'fill' => true, 'class' => true, 'aria-hidden' => true, 'focusable' => true ),
			'path' => array( 'd' => true ),
		)
	);
	if ( ! str_contains( $svg, '<svg ' ) || ! str_contains( $svg, '<path ' ) ) {
		return $title;
	}
	// Enforce decorative semantics for filtered/child-theme icons too.
	$svg = preg_replace( '/<svg\b[^>]*>/', '<svg class="githeme-social-icon" width="24" height="24" fill="currentColor" aria-hidden="true" focusable="false"' . ( preg_match( '/\bviewBox=([\'"])([0-9.\s-]+)\1/i', $svg, $viewbox ) ? ' viewBox="' . esc_attr( $viewbox[2] ) . '"' : '' ) . '>', $svg, 1 );
	return $svg . '<span class="screen-reader-text">' . esc_html( wp_strip_all_tags( $title ) ) . '</span>';
}
add_filter( 'nav_menu_item_title', 'githeme_social_menu_item_title', 10, 3 );

/** Render only an assigned native menu; never fall back to a list of pages. */
function githeme_get_social_links_menu() {
	if ( ! has_nav_menu( 'social' ) ) {
		return '';
	}
	// Native menu selective refresh requires echo=true. Capture it unchanged for
	// the footer's existing empty-content check instead of disabling that API.
	ob_start();
	wp_nav_menu(
		array(
			'theme_location'       => 'social',
			'container'            => 'nav',
			'container_class'      => 'githeme-social-navigation',
			'container_aria_label' => __( 'Social', 'githeme' ),
			'menu_class'           => 'githeme-social-links',
			'fallback_cb'          => false,
			'echo'                 => true,
		)
	);
	return ob_get_clean();
}
