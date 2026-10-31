<?php
/**
 * Site footer and document closing tags.
 *
 * @package githeme
 */
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
