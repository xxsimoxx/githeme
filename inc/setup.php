<?php
/**
 * Theme features, assets and widget areas.
 *
 * @package githeme
 */

defined( 'ABSPATH' ) || exit;

function githeme_setup() {
	load_theme_textdomain( 'githeme', get_template_directory() . '/languages' );
	add_theme_support( 'title-tag' );
	add_theme_support( 'automatic-feed-links' );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'custom-logo', array( 'flex-width' => true, 'flex-height' => true ) );
	register_nav_menus( array( 'primary' => __( 'Primary menu', 'githeme' ) ) );
	add_editor_style( add_query_arg( 'ver', wp_get_theme( get_template() )->get( 'Version' ), get_template_directory_uri() . '/assets/css/editor.css' ) );
}
add_action( 'after_setup_theme', 'githeme_setup' );

function githeme_enqueue_assets() {
	$version = wp_get_theme( get_template() )->get( 'Version' );
	wp_enqueue_style( 'githeme-style', get_stylesheet_uri(), array(), $version );
	wp_add_inline_style( 'githeme-style', githeme_font_faces_css() . githeme_custom_properties_css() );
	wp_enqueue_script( 'githeme-navigation', get_template_directory_uri() . '/assets/js/navigation.js', array(), $version, true );
	if ( is_singular() && comments_open() && get_option( 'thread_comments' ) ) {
		wp_enqueue_script( 'comment-reply' );
	}
}
add_action( 'wp_enqueue_scripts', 'githeme_enqueue_assets' );

function githeme_register_widget_areas() {
	register_sidebar(
		array(
			'name'          => __( 'Footer — experimental', 'githeme' ),
			'id'            => 'footer-experimental',
			'description'   => __( 'Optional widgets displayed before the site footer credits.', 'githeme' ),
			'before_widget' => '<section id="%1$s" class="widget %2$s">',
			'after_widget'  => '</section>',
			'before_title'  => '<h2 class="widget-title">',
			'after_title'   => '</h2>',
		)
	);
}
add_action( 'widgets_init', 'githeme_register_widget_areas' );
