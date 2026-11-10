<?php
/**
 * Opt-in native gallery presentation. The original fragment is never rewritten.
 *
 * @package githeme
 */

defined( 'ABSPATH' ) || exit;

/** Supply a slider-only default; preserve explicit sizes and earlier non-default values. */
function githeme_gallery_slider_default_size( $out, $pairs, $attributes ) {
	if ( ! is_feed() && 'slider' === ( $attributes['layout'] ?? null ) && ! array_key_exists( 'size', $attributes ) && isset( $out['size'], $pairs['size'] ) && $out['size'] === $pairs['size'] ) {
		$out['size'] = 'large';
	}
	return $out;
}
// Ordinary plugin filters at priority 10 retain the final choice.
add_filter( 'shortcode_atts_gallery', 'githeme_gallery_slider_default_size', 0, 3 );

/** Inspect a native-shaped gallery without serializing or repairing its output. */
function githeme_gallery_item_count( $html, &$dimensions = null ) {
	$dimensions = null;
	if ( ! class_exists( 'DOMDocument' ) ) {
		return 0;
	}
	$document = new DOMDocument();
	if ( ! $document->loadHTML( '<!doctype html><html><head><meta charset="utf-8"></head><body>' . $html . '</body></html>', LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING ) ) {
		return 0;
	}
	$body    = $document->getElementsByTagName( 'body' )->item( 0 );
	if ( ! $body ) {
		return 0;
	}
	$gallery = null;
	$has_class = static function ( $node, $class ) {
		return $node instanceof DOMElement && in_array( $class, preg_split( '/\s+/', trim( $node->getAttribute( 'class' ) ) ), true );
	};
	foreach ( $body->childNodes as $node ) {
		if ( XML_COMMENT_NODE === $node->nodeType || ( XML_TEXT_NODE === $node->nodeType && '' === trim( $node->textContent ) ) ) {
			continue;
		}
		// The core's optional gallery_style prefix is preserved, not moved or removed.
		if ( $node instanceof DOMElement && 'style' === $node->tagName ) {
			continue;
		}
		if ( null !== $gallery || ! $has_class( $node, 'gallery' ) || 'div' !== $node->tagName ) {
			return 0;
		}
		$gallery = $node;
	}
	if ( ! $gallery ) {
		return 0;
	}
	foreach ( array( 'script', 'iframe', 'object', 'embed' ) as $tag ) {
		if ( $gallery->getElementsByTagName( $tag )->length ) {
			return 0;
		}
	}
	$count = 0;
	$minimum_height = PHP_INT_MAX;
	$maximum_ratio = 0;
	$known_dimensions = true;
	foreach ( $gallery->childNodes as $item ) {
		if ( XML_COMMENT_NODE === $item->nodeType || ( XML_TEXT_NODE === $item->nodeType && '' === trim( $item->textContent ) ) ) {
			continue;
		}
		if ( ! $has_class( $item, 'gallery-item' ) ) {
			return 0;
		}
		$icon = null;
		foreach ( $item->childNodes as $child ) {
			if ( XML_COMMENT_NODE === $child->nodeType || ( XML_TEXT_NODE === $child->nodeType && '' === trim( $child->textContent ) ) ) {
				continue;
			}
			if ( $has_class( $child, 'gallery-icon' ) && null === $icon ) {
				$icon = $child;
			} elseif ( ! $has_class( $child, 'gallery-caption' ) ) {
				return 0;
			}
		}
		if ( ! $icon || 1 !== $icon->getElementsByTagName( 'img' )->length ) {
			return 0;
		}
		$image = $icon->getElementsByTagName( 'img' )->item( 0 );
		$width = $image->getAttribute( 'width' );
		$height = $image->getAttribute( 'height' );
		if ( preg_match( '/^[1-9][0-9]{0,6}$/', $width ) && preg_match( '/^[1-9][0-9]{0,6}$/', $height ) ) {
			$minimum_height = min( $minimum_height, (int) $height );
			$maximum_ratio = max( $maximum_ratio, (int) $width / (int) $height );
		} else {
			$known_dimensions = false;
		}
		++$count;
	}
	if ( $count && $known_dimensions ) {
		$dimensions = array( 'height' => $minimum_height, 'ratio' => $maximum_ratio );
	}
	return $count;
}

/** Add only an accessible scrollport around recognizable, explicitly opted-in HTML. */
function githeme_gallery_slider( $output, $tag, $attributes ) {
	if ( 'gallery' !== $tag || ! is_array( $attributes ) || 'slider' !== ( $attributes['layout'] ?? null ) || ! is_string( $output ) || '' === trim( $output ) || is_feed() ) {
		return $output;
	}
	if ( githeme_gallery_item_count( $output, $dimensions ) < 2 ) {
		return $output;
	}
	// Rendering may happen in content or widgets, after wp_enqueue_scripts.
	wp_enqueue_script( 'githeme-gallery-slider', get_template_directory_uri() . '/assets/js/gallery-slider.js', array(), wp_get_theme( get_template() )->get( 'Version' ), true );
	if ( ! wp_scripts()->get_data( 'githeme-gallery-slider', 'data' ) ) {
		wp_localize_script( 'githeme-gallery-slider', 'githemeGalleryLabels', array(
			'previous' => __( 'Previous image', 'githeme' ),
			'next'     => __( 'Next image', 'githeme' ),
		) );
	}
	$presentation = '';
	if ( $dimensions ) {
		// Metadata only: keep the native fragment untouched, including srcset.
		$style = '--githeme-gallery-source-height:' . $dimensions['height'] . 'px;--githeme-gallery-max-ratio:' . number_format( $dimensions['ratio'], 8, '.', '' ) . ';';
		$presentation = ' data-githeme-gallery-uniform style="' . esc_attr( $style ) . '"';
	}
	$id = wp_unique_id( 'githeme-gallery-slider-' );
	return '<div class="githeme-gallery-slider"' . $presentation . '><div id="' . esc_attr( $id ) . '" class="githeme-gallery-slider__viewport" role="group" aria-label="' . esc_attr__( 'Scrollable image gallery', 'githeme' ) . '" tabindex="0">' . $output . '</div></div>';
}
add_filter( 'do_shortcode_tag', 'githeme_gallery_slider', 10, 3 );
