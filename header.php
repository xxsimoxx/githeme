<?php
/**
 * Document and site header.
 *
 * @package githeme
 */

$githeme_static_homepage = is_front_page() && ! is_home();
?>
<!doctype html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<a class="skip-link screen-reader-text" href="#main-content"><?php esc_html_e( 'Skip to content', 'githeme' ); ?></a>
<header class="site-header">
	<div class="site-container header-inner">
		<div class="site-branding">
			<?php the_custom_logo(); ?>
			<?php if ( ! has_custom_logo() || githeme_identity_visible( 'githeme_show_title' ) ) : ?>
			<p class="site-title"><a href="<?php echo esc_url( home_url( '/' ) ); ?>"><?php echo esc_html( get_bloginfo( 'name' ) ); ?></a></p>
			<?php endif; ?>
			<?php if ( githeme_identity_visible( 'githeme_show_tagline' ) && get_bloginfo( 'description' ) ) : ?>
				<p class="site-description"><?php echo esc_html( get_bloginfo( 'description' ) ); ?></p>
			<?php endif; ?>
		</div>
		<?php if ( has_nav_menu( 'primary' ) ) : ?>
			<nav class="primary-navigation" aria-label="<?php esc_attr_e( 'Primary menu', 'githeme' ); ?>">
				<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="primary-menu" hidden><?php esc_html_e( 'Menu', 'githeme' ); ?></button>
				<?php
				wp_nav_menu(
					array(
						'theme_location' => 'primary',
						'container'      => false,
						'menu_id'        => 'primary-menu',
						'menu_class'     => 'primary-menu',
						'fallback_cb'    => false,
					)
				);
				?>
			</nav>
		<?php endif; ?>
	</div>
</header>
<main id="main-content" class="site-main <?php echo $githeme_static_homepage ? 'site-main-homepage' : 'site-container'; ?>" tabindex="-1">
<?php
if ( $githeme_static_homepage ) {
	get_template_part( 'template-parts/homepage-widgets', null, array( 'area' => 'homepage-hero' ) );
}
