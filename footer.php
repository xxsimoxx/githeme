<?php
/**
 * Site footer and document closing tags.
 *
 * @package githeme
 */

if ( is_front_page() && ! is_home() ) {
	get_template_part( 'template-parts/homepage-widgets', null, array( 'area' => 'homepage-content' ) );
}
?>
</main>
<footer class="site-footer">
	<div class="site-container">
		<?php if ( is_active_sidebar( 'footer-experimental' ) ) : ?>
			<div class="footer-widgets">
				<?php dynamic_sidebar( 'footer-experimental' ); ?>
			</div>
		<?php endif; ?>
		<p class="site-credits"><?php echo esc_html( get_bloginfo( 'name' ) ); ?></p>
	</div>
</footer>
<?php wp_footer(); ?>
</body>
</html>
