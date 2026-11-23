<?php
/**
 * Site footer and document closing tags.
 *
 * @package githeme
 */

if ( is_front_page() && ! is_home() ) {
	get_template_part( 'template-parts/homepage-widgets', null, array( 'area' => 'homepage-content' ) );
}
$githeme_footer_widgets = '';
if ( is_active_sidebar( 'footer-experimental' ) ) {
	ob_start();
	dynamic_sidebar( 'footer-experimental' );
	$githeme_footer_widgets = ob_get_clean();
}
$githeme_footer_social = githeme_get_social_links_menu();
?>
</main>
<?php if ( '' !== trim( $githeme_footer_widgets ) || '' !== trim( $githeme_footer_social ) ) : ?>
<footer class="site-footer">
	<div class="site-container">
		<?php if ( '' !== trim( $githeme_footer_widgets ) ) : ?>
		<div class="footer-widgets">
			<?php echo $githeme_footer_widgets; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Preserve native widget HTML. ?>
		</div>
		<?php endif; ?>
		<?php echo $githeme_footer_social; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Preserve native menu HTML and its filtered, sanitized icons. ?>
	</div>
</footer>
<?php endif; ?>
<?php wp_footer(); ?>
</body>
</html>
