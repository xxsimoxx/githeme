<?php
/**
 * Missing content.
 *
 * @package githeme
 */

get_header();
?>
<div class="content-column">
	<h1><?php esc_html_e( 'Page not found', 'githeme' ); ?></h1>
	<p><?php esc_html_e( 'Try searching the site or return to the homepage.', 'githeme' ); ?></p>
	<?php get_search_form(); ?>
	<p><a href="<?php echo esc_url( home_url( '/' ) ); ?>"><?php esc_html_e( 'Go to the homepage', 'githeme' ); ?></a></p>
</div>
<?php get_footer(); ?>
