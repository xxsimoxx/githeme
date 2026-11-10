<?php
/**
 * Run with WP-CLI eval-file [json]. Existing attachments are read, never changed.
 *
 * @package githeme
 */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { return; }
$count = 0;
$check = static function ( $ok, $message ) use ( &$count ) {
	if ( ! $ok ) { throw new RuntimeException( $message ); }
	++$count;
};
$original_mods = get_option( 'theme_mods_githeme' );
$original_query = $GLOBALS['wp_query'];
$original_scripts = clone wp_scripts();
wp_dequeue_script( 'githeme-gallery-slider' );
$original_callback = $GLOBALS['shortcode_tags']['gallery'];
$captured = '';
$capture = static function ( $output, $tag ) use ( &$captured ) {
	if ( 'gallery' === $tag ) { $captured = $output; }
	return $output;
};
$replacement = '';
$replace = static function () use ( &$replacement ) { return $replacement; };
$observed = array();
$observe = static function ( $out ) use ( &$observed ) { $observed = $out; return $out; };
$fixtures = array();
$native_calls = 0;
$count_native = static function ( $output ) use ( &$native_calls ) { ++$native_calls; return $output; };
$early_size = static function ( $out ) { $out['size'] = 'plugin-early'; return $out; };
$late_size = static function ( $out ) { $out['size'] = 'plugin-late'; return $out; };
add_filter( 'do_shortcode_tag', $capture, 9, 2 );
add_filter( 'post_gallery', $count_native, -100 );
add_filter( 'shortcode_atts_gallery', $observe );
try {
	$ids = get_posts( array( 'post_type' => 'attachment', 'post_status' => 'inherit', 'post_mime_type' => 'image', 'numberposts' => 3, 'fields' => 'ids' ) );
	$check( count( $ids ) >= 2, 'Two existing image attachments required; do not create fixtures in the database' );
	$shortcode = '[gallery ids="' . implode( ',', $ids ) . '"';
	foreach ( array( '', ' layout="grid"', ' layout=""', ' layout="Slider"' ) as $layout ) {
		$html = do_shortcode( $shortcode . $layout . ']' );
		$check( $html === $captured, 'Non-opted gallery remains byte-identical' );
		$check( ! str_contains( $html, 'githeme-gallery-slider' ), 'No slider markup for other layouts' );
		$check( 'thumbnail' === $observed['size'], 'Traditional and other layouts keep native thumbnail default' );
	}
	$check( ! wp_script_is( 'githeme-gallery-slider', 'enqueued' ), 'Traditional galleries do not enqueue slider JavaScript' );
	$fixtures['nativeClassic'] = $html;
	$before = $native_calls;
	$html = do_shortcode( $shortcode . ' layout="slider"]' );
	$check( $native_calls === $before + 1, 'One native gallery callback, no second generation' );
	$check( str_contains( $html, 'class="githeme-gallery-slider"' ), 'Explicit slider enhanced' );
	$check( str_contains( $html, $captured ), 'Entire native fragment preserved byte for byte' );
	$check( 'large' === $observed['size'] && 3 === $observed['columns'], 'Only slider size default changes; columns unchanged' );
	$check( 'post__in' === $observed['orderby'] && implode( ',', $ids ) === $observed['include'] && '' === $observed['exclude'] && '' === $observed['link'], 'Selection, order and default links unchanged' );
	$check( ! isset( $observed['layout'] ), 'No new native attribute normalization' );
	$check( githeme_gallery_item_count( $captured ) === count( $ids ), 'Native gallery recognized' );
	$check( wp_script_is( 'githeme-gallery-slider', 'enqueued' ), 'Actual slider rendering enqueues focus enhancement' );
	$script = wp_scripts()->registered['githeme-gallery-slider'];
	$check( $script->ver === wp_get_theme( get_template() )->get( 'Version' ) && empty( $script->deps ) && 1 === $script->extra['group'], 'Theme version, no dependencies and footer delivery' );
	$fixtures['nativeSlider'] = $html;
	foreach ( array( 'medium', 'full', 'thumbnail', 'custom-editorial-size', '' ) as $explicit ) {
		$before = $native_calls;
		$sized = do_shortcode( $shortcode . ' layout="slider" size="' . $explicit . '"]' );
		$check( $observed['size'] === $explicit, 'Explicit size preserved, including empty/custom values' );
		$check( $native_calls === $before + 1 && str_contains( $sized, $captured ), 'One render and unchanged native HTML for explicit size' );
	}
	$pairs = array( 'size' => 'thumbnail' );
	$check( array( 320, 240 ) === shortcode_atts( $pairs, array( 'layout' => 'slider', 'size' => array( 320, 240 ) ), 'gallery' )['size'], 'Explicit PHP dimensions preserved' );
	add_filter( 'shortcode_atts_gallery', $early_size, -1 );
	do_shortcode( $shortcode . ' layout="slider"]' );
	$check( 'plugin-early' === $observed['size'], 'Earlier plugin size choice preserved' );
	remove_filter( 'shortcode_atts_gallery', $early_size, -1 );
	add_filter( 'shortcode_atts_gallery', $late_size, 5 );
	do_shortcode( $shortcode . ' layout="slider"]' );
	$check( 'plugin-late' === $observed['size'], 'Later plugin size choice preserved' );
	remove_filter( 'shortcode_atts_gallery', $late_size, 5 );
	$check( 'thumbnail' === shortcode_atts( $pairs, array(), 'gallery' )['size'], 'Default does not leak to following galleries' );
	$html2 = do_shortcode( $shortcode . ' layout="slider" size="large" columns="7" link="none" order="DESC" orderby="ID"]' );
	$check( 'large' === $observed['size'] && '7' === $observed['columns'] && 'none' === $observed['link'] && 'DESC' === $observed['order'] && 'ID' === $observed['orderby'], 'Explicit native attributes unchanged' );
	$check( str_contains( $html2, $captured ), 'Explicit native output preserved' );
	preg_match( '/id="(githeme-gallery-slider-[^"]+)"/', $html, $first );
	preg_match( '/id="(githeme-gallery-slider-[^"]+)"/', $html2, $second );
	$check( ! empty( $first[1] ) && ! empty( $second[1] ) && $first[1] !== $second[1], 'Independent unique IDs' );
	wp_dequeue_script( 'githeme-gallery-slider' );
	$single = do_shortcode( '[gallery ids="' . $ids[0] . '" layout="slider"]' );
	$check( $single === $captured, 'Single image stays static and byte-identical' );
	$check( '' === do_shortcode( '[gallery ids="2147483647" layout="slider"]' ), 'Missing images preserve empty native result' );
	foreach ( array( '', ' ', '<p>Alternative gallery</p>', '<div class="gallery"><div>Unknown contents</div></div>', '<div class="gallery"><figure class="gallery-item">Missing image</figure></div>', '<div>Prefix</div>' . $captured ) as $unknown ) {
		$check( $unknown === githeme_gallery_slider( $unknown, 'gallery', array( 'layout' => 'slider' ) ), 'Unrecognized/empty output unchanged' );
	}
	$check( ! wp_script_is( 'githeme-gallery-slider', 'enqueued' ), 'Single, missing and unknown output never enqueue the script' );
	$GLOBALS['wp_query'] = clone $original_query;
	$GLOBALS['wp_query']->is_feed = true;
	$feed = do_shortcode( $shortcode . ' layout="slider"]' );
	$check( $feed === $captured && ! str_contains( $feed, 'githeme-gallery-slider' ), 'Feed unmodified' );
	$check( 'thumbnail' === $observed['size'], 'Feed keeps native size default' );
	$check( ! wp_script_is( 'githeme-gallery-slider', 'enqueued' ), 'Feed never enqueues slider JavaScript' );
	$GLOBALS['wp_query'] = $original_query;
	add_filter( 'post_gallery', $replace );
	$replacement = '';
	$check( str_contains( do_shortcode( $shortcode . ' layout="slider"]' ), 'githeme-gallery-slider' ), 'Non-replacing post_gallery filter does not disable slider' );
	$replacement = '<div class="external-carousel"><img src="example.jpg" alt=""></div>';
	$check( $replacement === do_shortcode( $shortcode . ' layout="slider"]' ), 'Incompatible replacement untouched' );
	// Synthetic media only: preserve real captions, attributes and nested inline markup.
	$items = '';
	foreach ( array( array( 800, 400 ), array( 300, 1200 ), array( 500, 500 ), array( 900, 600 ), array( 800, 400 ) ) as $i => $size ) {
		$svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' . $size[0] . '" height="' . $size[1] . '"><rect width="100%" height="100%" fill="silver"/><text x="20" y="40">Fixture ' . ( $i + 1 ) . '</text></svg>';
		$src = 'data:image/svg+xml;base64,' . base64_encode( $svg );
		$items .= '<figure class="gallery-item"><div class="gallery-icon"><a href="#after"><img src="' . $src . '" width="' . $size[0] . '" height="' . $size[1] . '" alt="Fixture ' . ( $i + 1 ) . '" aria-describedby="fixture-caption-' . $i . '"></a></div><figcaption class="wp-caption-text gallery-caption" id="fixture-caption-' . $i . '">Caption ' . $i . ': <em>original inline text</em>. ' . str_repeat( 'Long caption preserved without truncation. ', $i * 8 ) . '</figcaption></figure>';
	}
	$replacement = '<div id="gallery-fixture" class="gallery gallery-columns-3 gallery-size-large">' . $items . '</div>';
	$synthetic = do_shortcode( $shortcode . ' layout="slider"]' );
	$check( str_contains( $synthetic, $replacement ), 'Recognizable post_gallery replacement preserved and enhanced' );
	$metadata = null;
	githeme_gallery_item_count( $replacement, $metadata );
	$check( 400 === $metadata['height'] && 2 === (int) $metadata['ratio'], 'Uniform sizing uses minimum source height and maximum ratio' );
	$check( str_contains( $synthetic, 'data-githeme-gallery-uniform' ) && str_contains( $synthetic, '--githeme-gallery-source-height:400px' ), 'Presentation metadata added only to wrapper' );
	$low_resolution = str_replace( 'width="800" height="400"', 'width="80" height="40"', $replacement );
	githeme_gallery_item_count( $low_resolution, $metadata );
	$check( 40 === $metadata['height'], 'Low-resolution source bounds the entire image row without upscaling' );
	$unknown_dimensions = str_replace( 'width="800"', 'width="100%"', $replacement );
	$check( githeme_gallery_item_count( $unknown_dimensions, $metadata ) === 5 && null === $metadata, 'Uncertain dimensions keep native recognition and safe presentation fallback' );
	$check( ! str_contains( githeme_gallery_slider( $unknown_dimensions, 'gallery', array( 'layout' => 'slider' ) ), 'data-githeme-gallery-uniform' ), 'Unknown dimensions do not invent source sizes' );
	$fixtures['syntheticSlider'] = $synthetic;
	$fixtures['syntheticSecond'] = githeme_gallery_slider( str_replace( array( 'gallery-fixture', 'fixture-caption-' ), array( 'gallery-fixture-second', 'fixture-caption-second-' ), $replacement ), 'gallery', array( 'layout' => 'slider' ) );
	$check( 1 === count( array_keys( wp_scripts()->queue, 'githeme-gallery-slider', true ) ), 'Multiple rendered galleries enqueue exactly one script' );
	$fixtures['syntheticClassic'] = $replacement;
	$fixtures['syntheticSingle'] = githeme_gallery_slider( '<div class="gallery">' . substr( $items, 0, strpos( $items, '</figure>' ) + 9 ) . '</div>', 'gallery', array( 'layout' => 'slider' ) );
	$prefixed = '<style>#gallery-fixture img {border:0}</style>' . $replacement;
	$check( str_contains( githeme_gallery_slider( $prefixed, 'gallery', array( 'layout' => 'slider' ) ), $prefixed ), 'Optional core style prefix preserved' );
	$legacy = str_replace( array( '<figure ', '</figure>', '<div class="gallery-icon">', '</a></div>', '<figcaption ', '</figcaption>' ), array( '<dl ', '</dl>', '<dt class="gallery-icon">', '</a></dt>', '<dd ', '</dd>' ), $replacement );
	$check( str_contains( githeme_gallery_slider( $legacy, 'gallery', array( 'layout' => 'slider' ) ), $legacy ), 'Legacy gallery tags preserved' );
	$active = str_replace( '</figure>', '<script>void 0;</script></figure>', $replacement );
	$check( $active === githeme_gallery_slider( $active, 'gallery', array( 'layout' => 'slider' ) ), 'Active replacement content is not enhanced' );
	$check( $replacement === githeme_gallery_slider( $replacement, 'other', array( 'layout' => 'slider' ) ), 'Other shortcode untouched' );
	$check( $replacement === githeme_gallery_slider( $replacement, 'gallery', '' ), 'Unexpected attributes safely ignored' );
	$check( $synthetic === githeme_gallery_slider( $synthetic, 'gallery', array( 'layout' => 'slider' ) ), 'No double wrapping' );
	$check( ! str_contains( $synthetic, '<button' ) && ! str_contains( $synthetic, '<script' ) && ! str_contains( $synthetic, 'aria-hidden' ), 'No controls, scripts or hidden slides' );
	$check( str_contains( $synthetic, 'tabindex="0"' ) && str_contains( $synthetic, 'role="group"' ) && str_contains( $synthetic, 'aria-label="' ), 'Named keyboard scrollport' );
	$check( $GLOBALS['shortcode_tags']['gallery'] === $original_callback, 'Native shortcode callback unchanged' );
	global $wpdb;
	$queries = $wpdb->num_queries;
	githeme_gallery_slider( $replacement, 'gallery', array( 'layout' => 'slider' ) );
	$check( $queries === $wpdb->num_queries, 'No additional attachment queries in presentation filter' );
	$localization = wp_scripts()->get_data( 'githeme-gallery-slider', 'data' );
	$check( 1 === substr_count( $localization, 'var githemeGalleryLabels' ), 'Labels localized once across multiple rendered sliders' );
	$check( str_contains( $localization, wp_json_encode( __( 'Previous image', 'githeme' ) ) ) && str_contains( $localization, wp_json_encode( __( 'Next image', 'githeme' ) ) ), 'Accessible labels use native translations' );
	$fixtures['javascript'] = $localization . "\n" . file_get_contents( get_template_directory() . '/assets/js/gallery-slider.js' );
	$fixtures['css'] = file_get_contents( get_template_directory() . '/style.css' );
} finally {
	remove_filter( 'do_shortcode_tag', $capture, 9 );
	remove_filter( 'post_gallery', $replace );
	remove_filter( 'post_gallery', $count_native, -100 );
	remove_filter( 'shortcode_atts_gallery', $observe );
	remove_filter( 'shortcode_atts_gallery', $early_size, -1 );
	remove_filter( 'shortcode_atts_gallery', $late_size, 5 );
	$GLOBALS['wp_query'] = $original_query;
	$GLOBALS['wp_scripts'] = $original_scripts;
}
$check( get_option( 'theme_mods_githeme' ) === $original_mods, 'Settings unchanged' );
if ( in_array( 'json', $args ?? array(), true ) ) {
	echo wp_json_encode( array( 'assertions' => $count, 'fixtures' => $fixtures ) );
} else {
	WP_CLI::success( $count . ' gallery checks passed; native core output plus synthetic DOM fixtures; no database writes.' );
}
