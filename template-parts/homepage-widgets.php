<?php
/**
 * Optional static-homepage widget areas, shared by header and footer.
 *
 * @package githeme
 */

$githeme_area = $args['area'] ?? '';
if ( ! is_front_page() || is_home() || ! in_array( $githeme_area, array( 'homepage-hero', 'homepage-content' ), true ) || ! is_active_sidebar( $githeme_area ) ) {
	return;
}

// An active widget may decline to render. Do not leave an empty area wrapper.
ob_start();
dynamic_sidebar( $githeme_area );
$githeme_widgets = ob_get_clean();
if ( '' === trim( $githeme_widgets ) ) {
	return;
}
?>
<div id="<?php echo esc_attr( $githeme_area ); ?>" class="homepage-widget-area <?php echo esc_attr( $githeme_area ); ?>">
	<?php echo $githeme_widgets; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Native widget HTML must retain its own markup. ?>
</div>
